from __future__ import absolute_import

import json
import logging
import os
import os.path
import socket
from collections import defaultdict
from itertools import chain
from time import time

import six
import eventlet
from eventlet import wsgi
from six import PY2, iteritems
import gevent
from cachetools import TTLCache
from gevent.coros import BoundedSemaphore

from library import api
from pgoapi.pgoapi import PGoApi
# from library.api.pgoapi import protos
from library.api.pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Item_Enums

from .inventory import Inventory as Player_Inventory
from .player_stats import PlayerStats as PlayerStats
from .poke_utils import (create_capture_probability, get_inventory_data,
                         get_item_name, get_pokemon_by_long_id)
from .pokedex import pokedex

from helper.exceptions import (AuthException, TooManyEmptyResponses)
from helper.utilities import dict_merge
from .location import (distance_in_meters, filtered_forts,
                       get_increments, get_location, get_neighbors, get_route)
from .player import Player as Player
from .pokemon import POKEMON_NAMES, Pokemon
from .release.base import ReleaseMethodFactory
from .config import Config
from .poketrainer import Poketrainer

if six.PY3:
    from builtins import map as imap
elif six.PY2:
    from itertools import imap

logger = logging.getLogger(__name__)


class ApiWrapper:
    def __init__(self, config_index, thread_pool, force_debug=False):

        self.trainer = None
        self.thread = None
        self.socket = None
        self.thread_pool = thread_pool
        self.config_index = config_index
        self.force_debug = force_debug

        self.log = logging.getLogger(__name__)

        # objects
        self.config = None
        self.releaseMethodFactory = ReleaseMethodFactory(config)
        self.player = Player({})
        self.player_stats = PlayerStats({})
        self.inventory = Player_Inventory(self.config.ball_priorities, [])

        self.api = None
        self._origPosF = (0, 0, 0)
        self._posf = (0, 0, 0)
        self.load_api(prev_location)

        # config values that might be changed during runtime
        self.step_size = self.config.step_size
        self.should_catch_pokemon = self.config.should_catch_pokemon

        # timers, counters and triggers
        self.pokemon_caught = 0
        self._last_got_map_objects = 0
        self._map_objects_rate_limit = 10.0
        self._error_counter = 0
        self._error_threshold = 10
        self._heartbeat_number = 5
        self._last_egg_use_time = 0
        self._farm_mode_triggered = False
        self.start_time = time()
        self.exp_start = None

        # caches
        self.encountered_pokemons = TTLCache(maxsize=120, ttl=self._map_objects_rate_limit * 2)
        self.visited_forts = TTLCache(maxsize=120, ttl=self.config.skip_visited_fort_duration)
        self.map_objects = {}

        # threading / locking
        self.sem = BoundedSemaphore(1)
        self.persist_lock = False

        # Sanity checking
        self.config.farm_items_enabled = self.config.farm_items_enabled and self.config.experimental and self.should_catch_pokemon  # Experimental, and we needn't do this if we're farming anyway
        if (
                                self.config.farm_items_enabled and
                                self.config.farm_ignore_pokeball_count and
                            self.config.farm_ignore_greatball_count and
                        self.config.farm_ignore_ultraball_count and
                    self.config.farm_ignore_masterball_count
        ):
            self.config.farm_items_enabled = False
            self.log.warn("FARM_ITEMS has been disabled due to all Pokeball counts being ignored.")
        elif self.config.farm_items_enabled and not (
                    self.config.pokeball_farm_threshold < self.config.pokeball_continue_threshold):
            self.config.farm_items_enabled = False
            self.log.warn(
                "FARM_ITEMS has been disabled due to farming threshold being below the continue. Set 'CATCH_POKEMON' to 'false' to enable captureless traveling.")

    def sleep(self, t):
        eventlet.sleep(t * self.config.sleep_mult)
        #gevent.sleep(t * self.config.sleep_mult)

    def open_socket(self):
        desc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".listeners")
        s = socket.socket()
        s.bind(("", 0))  # let the kernel find a free port
        sock_port = s.getsockname()[1]
        s.close()
        data = {}

        if os.path.isfile(desc_file):
            with open(desc_file, 'r+') as f:
                data = f.read()
                if PY2:
                    data = json.loads(data.encode() if len(data) > 0 else '{}')
                else:
                    data = json.loads(data if len(data) > 0 else '{}')
        data[self.config["username"]] = sock_port
        with open(desc_file, "w+") as f:
            f.write(json.dumps(data, indent=2))

        self.socket = self.thread_pool.spawn(wsgi.server, eventlet.listen(('127.0.0.1', sock_port)), self)

    def load_api(self, prev_location=None):
        self.log.info('login process')
        return
        self.api = PGoApi()
        # set signature!
        self.api.activate_signature("libencrypt.so")

        # get position and set it in the API
        position = get_location(self.config.location)
        self._origPosF = position
        if prev_location:
            position = prev_location
        self._posf = position
        self.api.set_position(*position)

        # retry login every 30 seconds if any errors
        self.log.info('Starting Login process...')
        while not self.api.login(self.config.auth_service, self.config.username, self.config.get_password()):
            logger.error('Login error, retrying Login in 30 seconds')
            self.sleep(30)
        self.log.info('Login successful')

    '''
    Blocking lock
        - only locks if current thread (greenlet) doesn't own the lock
        - persist=True will ensure the lock will not be released until the user
          explicitly sets self.persist_lock=False.
    '''
    def cond_lock(self, persist=False):
        if self.sem.locked():
            if self.locker == id(gevent.getcurrent()):
                self.log.debug("Locker is -- %s. No need to re-lock", id(gevent.getcurrent()))
                return
            else:
                self.log.debug("Already locked by %s. Greenlet %s will wait...", self.locker, id(gevent.getcurrent()))
        self.sem.acquire()
        self.persist_lock = persist
        self.log.debug("%s acquired lock (persist=%s)!", id(gevent.getcurrent()), persist)
        self.locker = id(gevent.getcurrent())

    '''
    Releases the lock if needed and the user didn't persist it
    '''
    def cond_release(self):
        if self.sem.locked() and \
                        self.locker == id(gevent.getcurrent()) and not self.persist_lock:
            self.log.debug("%s is now releasing lock", id(gevent.getcurrent()))
            self.sem.release()

    # newest event always locks all previous events, no matter where they are, right?
    # that's not cool
    def call_old(self):
        # before doing stuff
        self.cond_lock()
        try:
            # getting id of current event
            gevent_id = id(gevent.getcurrent())
        finally:
            # after we're done
            self.cond_release()

    # instead of a full heartbeat, just update position.
    # useful for sniping for example
    def send_update_pos(self):
        res = self.api.get_player()
        if not res or res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Can't snipe!", res)
            return False
        return True

    def snipe_pokemon(self, lat, lng):
        self.cond_lock(persist=True)

        self.sleep(
            2)  # might not be needed, used to prevent main thread from issuing a waiting-for-lock server query too quickly
        curr_lat = self._posf[0]
        curr_lng = self._posf[1]

        try:
            self.log.info("Sniping pokemon at %f, %f", lat, lng)
            self.log.info("Waiting for API limit timer ...")
            while time() - self._last_got_map_objects < self._map_objects_rate_limit:
                self.sleep(0.1)

            # move to snipe location
            self.api.set_position(lat, lng, 0.0)
            if not self.send_update_pos():
                return False

            self.log.debug("Teleported to sniping location %f, %f", lat, lng)

            # find pokemons in dest
            map_cells = self.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
            pokemons = self.flatmap(lambda c: c.get('catchable_pokemons', []), map_cells)

            # catch first pokemon:
            origin = (self._posf[0], self._posf[1])
            pokemon_rarity_and_dist = [
                (
                    pokemon, pokedex.get_rarity_by_id(pokemon['pokemon_id']),
                    distance_in_meters(origin, (pokemon['latitude'], pokemon['longitude']))
                )
                for pokemon in pokemons]
            pokemon_rarity_and_dist.sort(key=lambda x: x[1], reverse=True)

            if pokemon_rarity_and_dist:
                self.log.info("Rarest pokemon: : %s", POKEMON_NAMES[str(pokemon_rarity_and_dist[0][0]['pokemon_id'])])
                return self.encounter_pokemon(pokemon_rarity_and_dist[0][0], new_loc=(curr_lat, curr_lng))
            else:
                self.log.info("No nearby pokemon. Can't snipe!")
                return False

        finally:
            self.api.set_position(curr_lat, curr_lng, 0.0)
            self.send_update_pos()
            self.log.debug("Teleported back to origin at %f, %f", self._posf[0], self._posf[1])
            # self.sleep(2) # might not be needed, used to prevent main thread from issuing a waiting-for-lock server query too quickly
            self.persist_lock = False
            self.cond_release()

    def update_player_inventory(self):
        res = self.api.get_inventory()
        if 'GET_INVENTORY' in res.get('responses', {}):
            inventory_items = res.get('responses', {}) \
                .get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
            self.inventory = Player_Inventory(self.config.ball_priorities, inventory_items)
        return res

    def get_player_inventory(self, as_json=True):
        return self.inventory.to_json()

    def use_lucky_egg(self):
        if self.config.use_lucky_egg and \
                self.inventory.has_lucky_egg() and time() - self._last_egg_use_time > 30 * 60:
            response = self.api.use_item_xp_boost(item_id=Item_Enums.ITEM_LUCKY_EGG)
            result = response.get('responses', {}).get('USE_ITEM_XP_BOOST', {}).get('result', -1)
            if result == 1:
                self.log.info("Ate a lucky egg! Yummy! :)")
                self.inventory.take_lucky_egg()
                self._last_egg_use_time = time()
                return True
            elif result == 3:
                self.log.info("Lucky egg already active")
                return False
            else:
                self.log.info("Lucky Egg couldn't be used, status code %s", result)
                return False
        else:
            return False

    def fort_search_pgoapi(self, fort, player_postion, fort_distance):
        self.sleep(0.2)
        res = self.api.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'],
                                   fort_longitude=fort['longitude'],
                                   player_latitude=player_postion[0],
                                   player_longitude=player_postion[1])
        result = -1
        if res:
            res = res.get('responses', {}).get('FORT_SEARCH', {})
            result = res.pop('result', -1)
        if result == 1:
            self.log.info("Visiting fort... (http://maps.google.com/maps?q=%s,%s)", fort['latitude'], fort['longitude'])
            if "items_awarded" in res:
                items = defaultdict(int)
                for item in res['items_awarded']:
                    items[item['item_id']] += item['item_count']
                reward = 'XP +' + str(res['experience_awarded'])
                for item_id, amount in six.iteritems(items):
                    reward += ', ' + str(amount) + 'x ' + get_item_name(item_id)
                self.log.info("Fort spun, yielding: %s",
                              reward)
            else:
                self.log.info("Fort spun, but did not yield any rewards. Possible soft ban?")
            self.visited_forts[fort['id']] = fort
        elif result == 4:
            self.log.debug("For spinned but Your inventory is full : %s", res)
            self.log.info("For spinned but Your inventory is full.")
            self.visited_forts[fort['id']] = fort
        elif result == 2:
            self.log.debug("Could not spin fort -  fort not in range %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Not in Range %s", fort['latitude'],
                          fort['longitude'], fort_distance)
        elif result == 3:
            self.log.debug("Could not spin fort -  still on cooldown %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Still on cooldown",
                          fort['latitude'],
                          fort['longitude'])
        else:
            self.log.debug("Could not spin fort %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Error id: %s", fort['latitude'],
                          fort['longitude'], result)
            return False
        return True

    def nearby_map_objects(self):
        if time() - self._last_got_map_objects > self._map_objects_rate_limit:
            position = self.api.get_position()
            neighbors = get_neighbors(self._posf)
            gevent.sleep(1.0)
            self.map_objects = self.api.get_map_objects(
                latitude=position[0], longitude=position[1],
                since_timestamp_ms=[0, ] * len(neighbors),
                cell_id=neighbors)
            self._last_got_map_objects = time()
            print(self.map_objects)
            exit()
        return self.map_objects

    def attempt_catch(self, encounter_id, spawn_point_id, capture_probability=None):
        catch_status = -1
        catch_attempts = 1
        ret = {}
        if not capture_probability:
            capture_probability = {}
        # Max 4 attempts to catch pokemon
        while catch_status != 1 and self.inventory.can_attempt_catch() and catch_attempts <= self.config.max_catch_attempts:
            item_capture_mult = 1.0

            # Try to use a berry to increase the chance of catching the pokemon when we have failed enough attempts
            if catch_attempts > self.config.min_failed_attempts_before_using_berry \
                    and self.inventory.has_berry():
                self.log.info("Feeding da razz berry!")
                self.sleep(0.2)
                r = self.api.use_item_capture(item_id=self.inventory.take_berry(), encounter_id=encounter_id,
                                              spawn_point_id=spawn_point_id) \
                    .get('responses', {}).get('USE_ITEM_CAPTURE', {})
                if r.get("success", False):
                    item_capture_mult = r.get("item_capture_mult", 1.0)
                else:
                    self.log.info("Could not feed the Pokemon. (%s)", r)

            pokeball = self.inventory.take_next_ball(capture_probability)
            self.log.info("Attempting catch with {0} at {1:.2f}% chance. Try Number: {2}".format(get_item_name(
                pokeball), item_capture_mult * capture_probability.get(pokeball, 0.0) * 100, catch_attempts))
            self.sleep(0.5)
            r = self.api.catch_pokemon(
                normalized_reticle_size=1.950,
                pokeball=pokeball,
                spin_modifier=0.850,
                hit_pokemon=True,
                normalized_hit_position=1,
                encounter_id=encounter_id,
                spawn_point_id=spawn_point_id,
            ).get('responses', {}).get('CATCH_POKEMON', {})
            catch_attempts += 1
            if "status" in r:
                catch_status = r['status']
                # fleed or error
                if catch_status == 3 or catch_status == 0:
                    break
            ret = r
            # Sleep between catch attempts
            # self.sleep(3)
        # Sleep after the catch (the pokemon animation time)
        # self.sleep(4)
        return ret

    def get_caught_pokemons(self, inventory_items=None, as_json=False):
        if not inventory_items:
            self.sleep(0.2)
            inventory_items = self.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = defaultdict(list)
        for inventory_item in inventory_items:
            if "pokemon_data" in inventory_item['inventory_item_data'] and not inventory_item['inventory_item_data'][
                'pokemon_data'].get("is_egg", False):
                # is a pokemon:
                pokemon_data = inventory_item['inventory_item_data']['pokemon_data']
                pokemon = Pokemon(pokemon_data, self.player_stats.level, self.config.score_method,
                                  self.config.score_settings)

                if not pokemon.is_egg:
                    caught_pokemon[pokemon.pokemon_id].append(pokemon)
        if as_json:
            return json.dumps(caught_pokemon, default=lambda p: p.__dict__)  # reduce the data sent?
        return caught_pokemon

    def get_player_info(self, as_json=True):
        return self.player.to_json()

    def do_release_pokemon_by_id(self, p_id):
        release_res = self.api.release_pokemon(pokemon_id=int(p_id)).get('responses', {}).get('RELEASE_POKEMON', {})
        status = release_res.get('result', -1)
        return status

    def do_release_pokemon(self, pokemon):
        self.log.info("Releasing pokemon: %s", pokemon)
        if self.do_release_pokemon_by_id(pokemon.id):
            self.log.info("Successfully Released Pokemon %s", pokemon)
        else:
            # self.log.debug("Failed to release pokemon %s, %s", pokemon, release_res)  # FIXME release_res is not in scope!
            self.log.info("Failed to release Pokemon %s", pokemon)
        self.sleep(1.0)

    def get_pokemon_stats(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        for pokemons in caught_pokemon.values():
            for pokemon in pokemons:
                self.log.info("%s", pokemon)

    def cleanup_pokemon(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        releaseMethod = self.releaseMethodFactory.getReleaseMethod()
        for pokemonId, pokemons in caught_pokemon.iteritems():
            pokemonsToRelease, pokemonsToKeep = releaseMethod.getPokemonToRelease(pokemonId, pokemons)

            if self.config.pokemon_cleanup_testing_mode:
                for pokemon in pokemonsToRelease:
                    self.log.info("(TESTING) Would release pokemon: %s", pokemon)
                for pokemon in pokemonsToKeep:
                    self.log.info("(TESTING) Would keep pokemon: %s", pokemon)
            else:
                for pokemon in pokemonsToRelease:
                    self.do_release_pokemon(pokemon)

    def attempt_evolve(self, inventory_items=None):
        if not inventory_items:
            self.sleep(0.2)
            inventory_items = self.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        self.inventory = Player_Inventory(self.config.ball_priorities, inventory_items)
        for pokemons in caught_pokemon.values():
            if len(pokemons) > self.config.min_similar_pokemon:
                pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)
                for pokemon in pokemons[self.config.min_similar_pokemon:]:
                    # If we can't evolve this type of pokemon anymore, don't check others.
                    if not self.attempt_evolve_pokemon(pokemon):
                        break

    def attempt_evolve_pokemon(self, pokemon):
        if self.is_pokemon_eligible_for_evolution(pokemon=pokemon):
            self.log.info("Evolving pokemon: %s", pokemon)
            self.sleep(0.2)
            evo_res = self.api.evolve_pokemon(pokemon_id=pokemon.id).get('responses', {}).get('EVOLVE_POKEMON', {})
            status = evo_res.get('result', -1)
            # self.sleep(3)
            if status == 1:
                evolved_pokemon = Pokemon(evo_res.get('evolved_pokemon_data', {}),
                                          self.player_stats.level, self.config.score_method, self.config.score_settings)
                # I don' think we need additional stats for evolved pokemon. Since we do not do anything with it.
                # evolved_pokemon.pokemon_additional_data = self.game_master.get(pokemon.pokemon_id, PokemonData())
                self.log.info("Evolved to %s", evolved_pokemon)
                self.update_player_inventory()
                return True
            else:
                self.log.debug("Could not evolve Pokemon %s", evo_res)
                self.log.info("Could not evolve pokemon %s | Status %s", pokemon, status)
                self.update_player_inventory()
                return False
        else:
            return False

    def is_pokemon_eligible_for_evolution(self, pokemon):
        candy_have = self.inventory.pokemon_candy.get(
            self.config.pokemon_evolution_family.get(pokemon.pokemon_id, None), -1)
        candy_needed = self.config.pokemon_evolution.get(pokemon.pokemon_id, None)
        return candy_have > candy_needed and \
               pokemon.pokemon_id not in self.config.keep_pokemon_ids \
               and not pokemon.is_favorite \
               and pokemon.pokemon_id in self.config.pokemon_evolution

    def disk_encounter_pokemon(self, lureinfo, retry=False):
        try:
            self.update_player_inventory()
            if not self.inventory.can_attempt_catch():
                self.log.info("No balls to catch %s, exiting disk encounter", self.inventory)
                return False
            encounter_id = lureinfo['encounter_id']
            fort_id = lureinfo['fort_id']
            position = self._posf
            self.log.debug("At Fort with lure %s".encode('utf-8', 'ignore'), lureinfo)
            self.log.info("At Fort with Lure AND Active Pokemon %s",
                          POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            resp = self.api.disk_encounter(encounter_id=encounter_id, fort_id=fort_id, player_latitude=position[0],
                                           player_longitude=position[1]) \
                .get('responses', {}).get('DISK_ENCOUNTER', {})
            result = resp.get('result', -1)
            if result == 1 and 'pokemon_data' in resp and 'capture_probability' in resp:
                pokemon = Pokemon(resp.get('pokemon_data', {}))
                capture_probability = create_capture_probability(resp.get('capture_probability', {}))
                self.log.debug("Attempt Encounter: %s", json.dumps(resp, indent=4, sort_keys=True))
                return self.do_catch_pokemon(encounter_id, fort_id, capture_probability, pokemon)
            elif result == 5:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try",
                              POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
                self.cleanup_pokemon()
                if not retry:
                    return self.disk_encounter_pokemon(lureinfo, retry=True)
            elif result == 2:
                self.log.info("Could not start Disk (lure) encounter for pokemon: %s, not available",
                              POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            else:
                self.log.info("Could not start Disk (lure) encounter for pokemon: %s, Result: %s",
                              POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"),
                              result)
        except Exception as e:
            self.log.error("Error in disk encounter %s", e)
            return False

    def do_catch_pokemon(self, encounter_id, spawn_point_id, capture_probability, pokemon):
        self.log.info("Catching Pokemon: %s", pokemon)
        catch_attempt = self.attempt_catch(encounter_id, spawn_point_id, capture_probability)
        capture_status = catch_attempt.get('status', -1)
        if capture_status == 1:
            self.log.debug("Caught Pokemon: : %s", catch_attempt)
            self.log.info("Caught Pokemon:  %s", pokemon)
            self.pokemon_caught += 1
            return True
        elif capture_status == 3:
            self.log.debug("Pokemon fleed : %s", catch_attempt)
            self.log.info("Pokemon fleed:  %s", pokemon)
            return False
        elif capture_status == 2:
            self.log.debug("Pokemon escaped: : %s", catch_attempt)
            self.log.info("Pokemon escaped:  %s", pokemon)
            return False
        elif capture_status == 4:
            self.log.debug("Catch Missed: : %s", catch_attempt)
            self.log.info("Catch Missed:  %s", pokemon)
            return False
        else:
            self.log.debug("Could not catch pokemon: %s", catch_attempt)
            self.log.info("Could not catch pokemon:  %s", pokemon)
            self.log.info("Could not catch pokemon:  %s, status: %s", pokemon, capture_status)
            return False

    def encounter_pokemon(self, pokemon_data, retry=False,
                          new_loc=None):  # take in a MapPokemon from MapCell.catchable_pokemons
        # Update Inventory to make sure we can catch this mon
        try:
            self.update_player_inventory()
            if not self.inventory.can_attempt_catch():
                self.log.info("No balls to catch %s, exiting encounter", self.inventory)
                return False
            encounter_id = pokemon_data['encounter_id']
            spawn_point_id = pokemon_data['spawn_point_id']
            # begin encounter_id
            position = self.api.get_position()
            pokemon = Pokemon(pokemon_data)
            self.log.info("Trying initiate catching Pokemon: %s", pokemon)
            encounter = self.api.encounter(encounter_id=encounter_id,
                                           spawn_point_id=spawn_point_id,
                                           player_latitude=position[0],
                                           player_longitude=position[1]) \
                .get('responses', {}).get('ENCOUNTER', {})
            self.log.debug("Attempting to Start Encounter: %s", encounter)
            result = encounter.get('status', -1)
            if result == 1 and 'wild_pokemon' in encounter and 'capture_probability' in encounter:
                pokemon = Pokemon(encounter.get('wild_pokemon', {}).get('pokemon_data', {}))
                capture_probability = create_capture_probability(encounter.get('capture_probability', {}))
                self.log.debug("Attempt Encounter Capture Probability: %s",
                               json.dumps(encounter, indent=4, sort_keys=True))

                if new_loc:
                    # change loc for sniping
                    self.log.info("Teleporting to %f, %f before catching", new_loc[0], new_loc[1])
                    self.api.set_position(new_loc[0], new_loc[1], 0.0)
                    self.send_update_pos()
                    # self.sleep(2)

                self.encountered_pokemons[encounter_id] = pokemon_data
                return self.do_catch_pokemon(encounter_id, spawn_point_id, capture_probability, pokemon)
            elif result == 7:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try",
                              pokemon.pokemon_type)
                self.cleanup_pokemon()
                if not retry:
                    return self.encounter_pokemon(pokemon_data, retry=True, new_loc=new_loc)
            else:
                self.log.info("Could not start encounter for pokemon: %s, status %s", pokemon.pokemon_type, result)
            return False
        except Exception as e:
            self.log.error("Error in pokemon encounter %s", e)
            return False

    def incubate_eggs(self):
        if not self.config.egg_incubation_enabled:
            return
        if self.player_stats.km_walked > 0:
            for incubator in self.inventory.incubators_busy:
                incubator_start_km_walked = incubator.get('start_km_walked', self.player_stats.km_walked)

                incubator_egg_distance = incubator['target_km_walked'] - incubator_start_km_walked
                incubator_distance_done = self.player_stats.km_walked - incubator_start_km_walked
                if incubator_distance_done > incubator_egg_distance:
                    self.attempt_finish_incubation()
                    break
            for incubator in self.inventory.incubators_busy:
                incubator_start_km_walked = incubator.get('start_km_walked', self.player_stats.km_walked)

                incubator_egg_distance = incubator['target_km_walked'] - incubator_start_km_walked
                incubator_distance_done = self.player_stats.km_walked - incubator_start_km_walked
                self.log.info('Incubating %skm egg, %skm done', incubator_egg_distance,
                              round(incubator_distance_done, 2))
        for incubator in self.inventory.incubators_available:
            if incubator['item_id'] == 901:  # unlimited use
                pass
            elif self.config.use_disposable_incubators and incubator['item_id'] == 902:  # limited use
                pass
            else:
                continue
            eggs_available = self.inventory.eggs_available
            eggs_available = sorted(eggs_available, key=lambda egg: egg['creation_time_ms'],
                                    reverse=False)  # oldest first
            eggs_available = sorted(eggs_available, key=lambda egg: egg['egg_km_walked_target'],
                                    reverse=self.config.incubate_big_eggs_first)  # now sort as defined
            if not len(eggs_available) > 0 or not self.attempt_start_incubation(eggs_available[0], incubator):
                break

    def attempt_start_incubation(self, egg, incubator):
        self.log.info("Start incubating %skm egg", egg['egg_km_walked_target'])
        incubate_res = self.api.use_item_egg_incubator(item_id=incubator['id'], pokemon_id=egg['id']) \
            .get('responses', {}).get('USE_ITEM_EGG_INCUBATOR', {})
        status = incubate_res.get('result', -1)
        # self.sleep(3)
        if status == 1:
            self.log.info("Incubation started with %skm egg !", egg['egg_km_walked_target'])
            self.update_player_inventory()
            return True
        else:
            self.log.debug("Could not start incubating %s", incubate_res)
            self.log.info("Could not start incubating %s egg | Status %s", egg['egg_km_walked_target'], status)
            self.update_player_inventory()
            return False

    def attempt_finish_incubation(self):
        self.log.info("Checking for hatched eggs")
        self.sleep(0.2)
        hatch_res = self.api.get_hatched_eggs().get('responses', {}).get('GET_HATCHED_EGGS', {})
        status = hatch_res.get('success', -1)
        # self.sleep(3)
        if status == 1:
            self.update_player_inventory()
            for i, pokemon_id in enumerate(hatch_res['pokemon_id']):
                pokemon = get_pokemon_by_long_id(pokemon_id, self.inventory.inventory_items)
                self.log.info("Egg Hatched! XP +%s, Candy +%s, Stardust +%s, %s",
                              hatch_res['experience_awarded'][i],
                              hatch_res['candy_awarded'][i],
                              hatch_res['stardust_awarded'][i],
                              pokemon)
            return True
        else:
            self.log.debug("Could not get hatched eggs %s", hatch_res)
            self.log.info("Could not get hatched eggs Status %s", status)
            self.update_player_inventory()
            return False

    def load_config(self):
        config_file = "config.json"

        # If config file exists, load variables from json
        load = {}
        if os.path.isfile(config_file):
            with open(config_file) as data:
                load.update(json.load(data))

        defaults = load.get('defaults', {})
        config = load.get('accounts', [])[self.config_index]

        if self.force_debug or config.get('debug', False):
            logging.getLogger("requests").setLevel(logging.DEBUG)
            logging.getLogger("pgoapi").setLevel(logging.DEBUG)
            logging.getLogger("poketrainer").setLevel(logging.DEBUG)
            logging.getLogger("rpc_api").setLevel(logging.DEBUG)

        if config.get('auth_service', '') not in ['ptc', 'google']:
            logger.error("Invalid Auth service specified for account %s! ('ptc' or 'google')", i)
            return False

            # merge account section with defaults
        self.config = Config(dict_merge(defaults, config))
        return True

    def callback(self, gt):
        try:
            result = gt.wait()
            logger.info('Thread finished with result: %s', result)
        except Exception as e:
            logger.exception('Error in main loop %s, restarting at location: %s',
                             e, self._posf)
            # restart after sleep
            eventlet.sleep(5)
            self.start()

    def start(self):
        if self.load_config():

            self.trainer = Poketrainer(self)
            self.thread = self.thread_pool.spawn(self.trainer.main_loop)
            self.thread.link(self.callback)

    def stop(self):
        self.thread.kill()
        self.trainer = None

    @staticmethod
    def flatmap(f, items):
        return list(chain.from_iterable(imap(f, items)))
