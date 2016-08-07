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
import zerorpc
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
from helper.utilities import dict_merge, flatmap
from .location import (distance_in_meters, filtered_forts,
                       get_increments, get_location, get_neighbors, get_route)
from .player import Player as Player
from .pokemon import POKEMON_NAMES, Pokemon
from .release.base import ReleaseMethodFactory
from .config import Config
from .fort_walker import FortWalker
from .catcher import Catcher
from .poketrainer import Poketrainer

if six.PY3:
    from builtins import map as imap
elif six.PY2:
    from itertools import imap

logger = logging.getLogger(__name__)


class PoketrainerWrapper:
    """ Public functions (without _**) are callable by the webservice! """

    def __init__(self, args):

        self.trainer = None
        self.thread = None
        self.socket = None
        self.thread_pool = eventlet.GreenPool()
        self.cli_args = args
        self.force_debug = args['debug']

        self.log = logging.getLogger(__name__)

        # timers, counters and triggers
        self.pokemon_caught = 0
        self._last_got_map_objects = 0
        self._map_objects_rate_limit = 10.0
        self._error_counter = 0
        self._error_threshold = 10
        self._last_egg_use_time = 0
        self.start_time = time()
        self.exp_start = None

        # objects
        self.config = None
        self._load_config()
        self._open_socket()

        self._origPosF = (0, 0, 0)
        self.api = None
        self._load_api()

        self.releaseMethodFactory = None
        self.player = None
        self.player_stats = None
        self.inventory = None
        self.fort_walker = None
        self.catcher = None

        # config values that might be changed during runtime
        self.step_size = self.config.step_size
        self.should_catch_pokemon = self.config.should_catch_pokemon

        # caches
        self.map_objects = {}

        # threading / locking
        self.sem = BoundedSemaphore(1)
        self.persist_lock = False

        self.setup()

    def setup(self):
        self.releaseMethodFactory = ReleaseMethodFactory(self.config.config_data)
        self.player = Player({})
        self.player_stats = PlayerStats({})
        self.inventory = Player_Inventory(self.config.ball_priorities, [])
        self.fort_walker = FortWalker(self)
        self.catcher = Catcher(self)


    def sleep(self, t):
        #eventlet.sleep(t * self.config.sleep_mult)
        gevent.sleep(t * self.config.sleep_mult)

    def get_api_rate_limit(self):
        return self._map_objects_rate_limit

    def _open_socket(self):
        desc_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), ".listeners")
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
        data[self.config.username] = sock_port
        with open(desc_file, "w+") as f:
            f.write(json.dumps(data, indent=2))

        s = zerorpc.Server(self)
        s.bind("tcp://127.0.0.1:%i" % sock_port)  # the free port should still be the same
        self.socket = gevent.spawn(s.run)
        #self.socket = self.thread_pool.spawn(wsgi.server, eventlet.listen(('127.0.0.1', sock_port)), self)

    def _load_config(self):
        if self.config is None:
            config_file = "config.json"

            # If config file exists, load variables from json
            load = {}
            if os.path.isfile(config_file):
                with open(config_file) as data:
                    load.update(json.load(data))

            defaults = load.get('defaults', {})
            config = load.get('accounts', [])[self.cli_args['config_index']]

            if self.cli_args['debug'] or config.get('debug', False):
                logging.getLogger("requests").setLevel(logging.DEBUG)
                logging.getLogger("pgoapi").setLevel(logging.DEBUG)
                logging.getLogger("poketrainer").setLevel(logging.DEBUG)
                logging.getLogger("rpc_api").setLevel(logging.DEBUG)

            if config.get('auth_service', '') not in ['ptc', 'google']:
                logger.error("Invalid Auth service specified for account %s! ('ptc' or 'google')", config.get('username', 'NA'))
                return False

                # merge account section with defaults
            self.config = Config(dict_merge(defaults, config))
        return True

    def reload_config(self):
        self.config = None
        return self._load_config()

    def _load_api(self, prev_location=None):
        if self.api is None:
            self.api = PGoApi()
            # set signature!
            self.api.activate_signature(
                os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), self.cli_args['encrypt_lib'])
            )

            # get position and set it in the API
            if self.cli_args['location']:
                position = get_location(self.cli_args['location'])
            else:
                position = get_location(self.config.location)
            self._origPosF = position
            if prev_location:
                position = prev_location
            self.api.set_position(*position)

            # retry login every 30 seconds if any errors
            self.log.info('Starting Login process...')
            login = False
            while not login:
                login = self.api.login(self.config.auth_service, self.config.username, self.config.get_password())
                if not login:
                    logger.error('Login error, retrying Login in 30 seconds')
                    self.sleep(30)
            self.log.info('Login successful')
            self.parse_heartbeat_response(login)
        return True

    def reload_api(self, prev_location=None):
        self.api = None
        return self._load_api(prev_location)

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

    def _callback(self, gt):
        try:
            #result = gt.wait()
            if gt.exception:
                raise gt.exception
            result = gt.value
            logger.info('Thread finished with result: %s', result)
        except Exception as e:
            logger.exception('Error in main loop %s, restarting at location: %s',
                             e, self.get_position())
            # restart after sleep
            eventlet.sleep(5)
            self.reload_config()
            self.reload_api(self.get_position())
            self.start()

    def start(self):
        self.trainer = Poketrainer(self)

        #self.thread = self.thread_pool.spawn(self.main_loop)
        self.thread = gevent.spawn(self.trainer.main_loop)

        self.thread.link(self._callback)

    def stop(self):
        if self.thread:
            self.thread.kill()

    def parse_heartbeat_response(self, res):
        self.log.debug(
            'Response dictionary: \n\r{}'.format(json.dumps(res, indent=2, default=lambda obj: obj.decode('utf8'))))

        responses = res.get('responses', {})
        if 'GET_PLAYER' in responses:
            self.player = Player(responses.get('GET_PLAYER', {}).get('player_data', {}))
            self.log.info("Player Info: {0}, Pokemon Caught in this run: {1}".format(self.player, self.pokemon_caught))

        if 'GET_INVENTORY' in responses:

            # update objects
            inventory_items = responses.get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
            self.inventory = Player_Inventory(self.config.ball_priorities, inventory_items)
            for inventory_item in self.inventory.inventory_items:
                if "player_stats" in inventory_item['inventory_item_data']:
                    self.player_stats = PlayerStats(
                        inventory_item['inventory_item_data']['player_stats'],
                        self.pokemon_caught, self.start_time, self.exp_start
                    )
                    if self.exp_start is None:
                        self.exp_start = self.player_stats.run_exp_start
                    self.log.info("Player Stats: {}".format(self.player_stats))
            if self.config.list_inventory_before_cleanup:
                self.log.info("Player Inventory: %s", self.inventory)
            if self.config.list_pokemon_before_cleanup:
                self.log.info(get_inventory_data(res, self.player_stats.level, self.config.score_method,
                                                 self.config.score_settings))

            # save data dump
            with open("data_dumps/%s.json" % self.config.username, "w") as f:
                posf = self.get_position()
                responses['lat'] = posf[0]
                responses['lng'] = posf[1]
                responses['hourly_exp'] = self.player_stats.run_hourly_exp
                f.write(json.dumps(responses, indent=2, default=lambda obj: obj.decode('utf8')))

        if 'DOWNLOAD_SETTINGS' in responses:
            settings = responses.get('DOWNLOAD_SETTINGS', {}).get('settings', {})
            if settings.get('minimum_client_version', '0.0.0') > '0.31.0':
                self.log.error("Minimum client version has changed... the bot needs to be updated! Will now stop!")
                exit(0)
            fort_settings = settings.get('fort_settings', {})
            inventory_settings = settings.get('inventory_settings', {})
            map_settings = settings.get('map_settings', {})

            get_map_objects_max_refresh_seconds = map_settings.get('get_map_objects_max_refresh_seconds', 30.0)
            get_map_objects_min_distance_meters = map_settings.get('get_map_objects_min_distance_meters', 10.0)
            encounter_range_meters = map_settings.get('encounter_range_meters', 50.0)
            poke_nav_range_meters = map_settings.get('poke_nav_range_meters', 201.0)
            pokemon_visible_range = map_settings.get('pokemon_visible_range', 70.0)
            get_map_objects_min_refresh_seconds = map_settings.get('get_map_objects_min_refresh_seconds', 5.0)
            google_maps_api_key = map_settings.get('google_maps_api_key', '')
            self.log.info('get_map_objects_min_refresh_seconds: %s', str(get_map_objects_min_refresh_seconds))
            self.log.info('get_map_objects_max_refresh_seconds: %s', str(get_map_objects_max_refresh_seconds))
            self.log.info('get_map_objects_min_distance_meters: %s', str(get_map_objects_min_distance_meters))
            self.log.info('encounter_range_meters: %s', str(encounter_range_meters))

        return res

    def set_position(self, *pos):
        return self.api.set_position(*pos)

    def get_position(self):
        return self.api.get_position()

    def get_orig_position(self):
        return self._origPosF

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
        posf = self.get_position()
        curr_lat = posf[0]
        curr_lng = posf[1]

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
            pokemons = flatmap(lambda c: c.get('catchable_pokemons', []), map_cells)

            # catch first pokemon:
            pokemon_rarity_and_dist = [
                (
                    pokemon, pokedex.get_rarity_by_id(pokemon['pokemon_id']),
                    distance_in_meters(self.get_position(), (pokemon['latitude'], pokemon['longitude']))
                )
                for pokemon in pokemons]
            pokemon_rarity_and_dist.sort(key=lambda x: x[1], reverse=True)

            if pokemon_rarity_and_dist:
                self.log.info("Rarest pokemon: : %s", POKEMON_NAMES[str(pokemon_rarity_and_dist[0][0]['pokemon_id'])])
                return self.catcher.encounter_pokemon(pokemon_rarity_and_dist[0][0], new_loc=(curr_lat, curr_lng))
            else:
                self.log.info("No nearby pokemon. Can't snipe!")
                return False

        finally:
            self.api.set_position(curr_lat, curr_lng, 0.0)
            self.send_update_pos()
            posf = self.get_position()
            self.log.debug("Teleported back to origin at %f, %f", posf[0], posf[1])
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

    def nearby_map_objects(self):
        if time() - self._last_got_map_objects > self._map_objects_rate_limit:
            position = self.api.get_position()
            neighbors = get_neighbors(self.get_position())
            gevent.sleep(1.0)
            self.map_objects = self.api.get_map_objects(
                latitude=position[0], longitude=position[1],
                since_timestamp_ms=[0, ] * len(neighbors),
                cell_id=neighbors)
            self._last_got_map_objects = time()
        return self.map_objects

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
            self.sleep(1.0)
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

    def cleanup_inventory(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        item_count = 0
        for inventory_item in inventory_items:
            if "item" in inventory_item['inventory_item_data']:
                item = inventory_item['inventory_item_data']['item']
                if (
                                    item['item_id'] in self.config.min_items and
                                    "count" in item and
                                item['count'] > self.config.min_items[item['item_id']]
                ):
                    recycle_count = item['count'] - self.config.min_items[item['item_id']]
                    item_count += item['count'] - recycle_count
                    self.log.info("Recycling {0} {1}(s)".format(recycle_count, get_item_name(item['item_id'])))
                    self.sleep(1.0)
                    res = self.api.recycle_inventory_item(item_id=item['item_id'], count=recycle_count) \
                        .get('responses', {}).get('RECYCLE_INVENTORY_ITEM', {})
                    response_code = res.get('result', -1)
                    if response_code == 1:
                        self.log.info("{0}(s) recycled successfully. New count: {1}".format(get_item_name(
                            item['item_id']), res.get('new_count', 0)))
                    else:
                        self.log.info("Failed to recycle {0}, Code: {1}".format(get_item_name(item['item_id']),
                                                                                response_code))
                    self.sleep(1)
                elif "count" in item:
                    item_count += item['count']
        if item_count > 0:
            self.log.info("Inventory has {0}/{1} items".format(item_count, self.player.max_item_storage))
        return self.update_player_inventory()
