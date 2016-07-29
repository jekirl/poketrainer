"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>
Modifications Copyright (c) 2016 j-e-k <https://github.com/j-e-k>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
Modifications by: j-e-k <https://github.com/j-e-k>
"""

from __future__ import absolute_import

import json
import logging
import os.path
import pickle
import random
from collections import defaultdict
from itertools import chain, imap
from Queue import *
from time import time, sleep

from expiringdict import ExpiringDict

from pgoapi.auth_google import AuthGoogle
from pgoapi.auth_ptc import AuthPtc
from pgoapi.exceptions import AuthException, ServerBusyOrOfflineException
from pgoapi.player import Player as Player
from pgoapi.player_stats import PlayerStats as PlayerStats
from pgoapi.inventory import Inventory as Player_Inventory
from pgoapi.location import *
from pgoapi.poke_utils import *
from pgoapi.protos.POGOProtos import Enums_pb2
from pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Inventory
from pgoapi.protos.POGOProtos.Networking.Requests_pb2 import RequestType
from pgoapi.rpc_api import RpcApi
from .utilities import f2i

logger = logging.getLogger(__name__)


class PGoApi:
    API_ENTRY = 'https://pgorelease.nianticlabs.com/plfe/rpc'

    def __init__(self, config, pokemon_names):

        self.log = logging.getLogger(__name__)

        self._auth_provider = None
        self._api_endpoint = None
        self.config = config
        self._position_lat = 0  # int cooords
        self._position_lng = 0
        self._position_alt = 0
        self._posf = (0, 0, 0)  # this is floats
        self._origPosF = (0, 0, 0)  # this is original position in floats
        self._req_method_list = []
        self._heartbeat_number = 5
        self._firstRun = True
        self._last_egg_use_time = 0

        self.pokemon_caught = 0
        self.player = Player({})
        self.player_stats = PlayerStats({})
        self.inventory = Player_Inventory([])

        self.pokemon_names = pokemon_names

        self.start_time = time()
        self.exp_start = None
        self.exp_current = None

        self.MIN_ITEMS = {}
        for k, v in config.get("MIN_ITEMS", {}).items():
            self.MIN_ITEMS[getattr(Inventory, k)] = v

        self.POKEMON_EVOLUTION = {}
        self.POKEMON_EVOLUTION_FAMILY = {}
        for k, v in config.get("POKEMON_EVOLUTION", {}).items():
            self.POKEMON_EVOLUTION[getattr(Enums_pb2, k)] = v
            self.POKEMON_EVOLUTION_FAMILY[getattr(Enums_pb2, k)] = getattr(Enums_pb2, "FAMILY_" + k)

        self.KEEP_IV_OVER = config.get("KEEP_IV_OVER", 0)  # release anything under this
        self.KEEP_CP_OVER = config.get("KEEP_CP_OVER", 0)  # release anything under this

        self.MIN_SIMILAR_POKEMON = config.get("MIN_SIMILAR_POKEMON", 1)  # Keep atleast one of everything.
        self.STAY_WITHIN_PROXIMITY = config.get("STAY_WITHIN_PROXIMITY", 9999999)  # Stay within proximity

        self.LIST_POKEMON_BEFORE_CLEANUP = config.get("LIST_POKEMON_BEFORE_CLEANUP", True)  # list pokemon in console
        self.LIST_INVENTORY_BEFORE_CLEANUP = config.get("LIST_INVENTORY_BEFORE_CLEANUP", True)  # list inventory in console

        self.EGG_INCUBATION_ENABLED = config.get("EGG_INCUBATION", {}).get("ENABLE", True)
        self.USE_DISPOSABLE_INCUBATORS = config.get("EGG_INCUBATION", {}).get("USE_DISPOSABLE_INCUBATORS", False)
        self.INCUBATE_BIG_EGGS_FIRST = config.get("EGG_INCUBATION", {}).get("BIG_EGGS_FIRST", True)

        self.visited_forts = ExpiringDict(max_len=120, max_age_seconds=config.get("SKIP_VISITED_FORT_DURATION", 600))
        self.experimental = config.get("EXPERIMENTAL", False)
        self.spin_all_forts = config.get("SPIN_ALL_FORTS", False)
        self.keep_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("KEEP_POKEMON_NAMES", []))
        self.throw_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("THROW_POKEMON_NAMES", []))
        self.max_catch_attempts = config.get("MAX_CATCH_ATTEMPTS", 10)
        self.game_master = parse_game_master()
        self.should_catch_pokemon = config.get("CATCH_POKEMON", True)
        self.RELEASE_DUPLICATES = config.get("RELEASE_DUPLICATES", False)
        self.RELEASE_DUPLICATES_MAX_LV = config.get("RELEASE_DUPLICATES_MAX_LV", 0) # only release duplicates up to this lvl
        self.RELEASE_DUPLICATES_SCALER = config.get("RELEAES_DUPLICATES_SCALER", 1.0) # when comparing two pokemon's lvl, multiply larger by this
        self.DEFINE_POKEMON_LV = config.get("DEFINE_POKEMON_LV", "CP") # define a pokemon's lvl, options are CP, IV, CP*IV, CP+IV

    def call(self):
        if not self._req_method_list:
            return False

        if self._auth_provider is None or not self._auth_provider.is_login():
            self.log.info('Not logged in')
            return False

        player_position = self.get_position()

        request = RpcApi(self._auth_provider)

        if self._api_endpoint:
            api_endpoint = self._api_endpoint
        else:
            api_endpoint = self.API_ENTRY

        self.log.debug('Execution of RPC')
        response = None
        try:
            response = request.request(api_endpoint, self._req_method_list, player_position)
        except ServerBusyOrOfflineException as e:
            self.log.info('Server seems to be busy or offline - try again!')

        # cleanup after call execution
        self.log.debug('Cleanup of request!')
        self._req_method_list = []

        return response

    def list_curr_methods(self):
        for i in self._req_method_list:
            print("{} ({})".format(RequestType.Name(i), i))

    def set_logger(self, logger):
        self._ = logger or logging.getLogger(__name__)

    def get_position(self):
        return (self._position_lat, self._position_lng, self._position_alt)

    def set_position(self, lat, lng, alt):
        self.log.debug('Set Position - Lat: %s Long: %s Alt: %s', lat, lng, alt)
        self._posf = (lat, lng, alt)
        if self._firstRun:
            self._firstRun = False
            self._origPosF = self._posf
        self._position_lat = f2i(lat)
        self._position_lng = f2i(lng)
        self._position_alt = f2i(alt)

    def __getattr__(self, func):
        def function(**kwargs):

            if not self._req_method_list:
                self.log.debug('Create new request...')

            name = func.upper()
            if kwargs:
                self._req_method_list.append({RequestType.Value(name): kwargs})
                self.log.debug("Adding '%s' to RPC request including arguments", name)
                self.log.debug("Arguments of '%s': \n\r%s", name, kwargs)
            else:
                self._req_method_list.append(RequestType.Value(name))
                self.log.debug("Adding '%s' to RPC request", name)

            return self

        if func.upper() in RequestType.keys():
            return function
        else:
            raise AttributeError

    def hourly_exp(self, exp):
        if self.exp_start is None:
            self.exp_start = exp
        self.exp_current = exp

        run_time = time() - self.start_time
        run_time_hours = float(run_time/3600.00)
        exp_earned = float(self.exp_current - self.exp_start)
        exp_hour = float(exp_earned/run_time_hours)

        self.log.info("=== Exp/Hour: %s ===", round(exp_hour,2))

        return exp_hour

    def update_player_inventory(self):
        self.get_inventory()
        res = self.call()
        if 'GET_INVENTORY' in res['responses']:
            self.inventory = Player_Inventory(res['responses']['GET_INVENTORY']['inventory_delta']['inventory_items'])
        return res

    def heartbeat(self):
        # making a standard call to update position, etc
        self.get_player()
        if self._heartbeat_number % 10 == 0:
            self.check_awarded_badges()
            self.get_inventory()
        # self.download_settings(hash="4a2e9bc330dae60e7b74fc85b98868ab4700802e")
        res = self.call()
        if not res or res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Restarting!!!", res)
            raise AuthException("Token probably expired?")
        self.log.debug('Heartbeat dictionary: \n\r{}'.format(json.dumps(res, indent=2)))

        if 'GET_PLAYER' in res['responses']:
            self.player = Player(res['responses'].get('GET_PLAYER', {}).get('player_data', {}))
            self.log.info("Player Info: %s, Pokemon Caught in this run: %s", self.player, self.pokemon_caught)

        if 'GET_INVENTORY' in res['responses']:
            with open("data_dumps/%s.json" % self.config['username'], "w") as f:
                res['responses']['lat'] = self._posf[0]
                res['responses']['lng'] = self._posf[1]
                f.write(json.dumps(res['responses'], indent=2))

            self.inventory = Player_Inventory(res['responses']['GET_INVENTORY']['inventory_delta']['inventory_items'])
            for inventory_item in self.inventory.inventory_items:
                if "player_stats" in inventory_item['inventory_item_data']:
                    self.player_stats = PlayerStats(inventory_item['inventory_item_data']['player_stats'])
                    self.log.info("Player Stats: %s", self.player_stats)
                    self.hourly_exp(self.player_stats.experience)
            if self.LIST_INVENTORY_BEFORE_CLEANUP:
                self.log.info("Player Items Before Cleanup: %s", self.inventory)
            self.log.debug(self.cleanup_inventory(self.inventory.inventory_items))
            self.log.info("Player Inventory after cleanup: %s", self.inventory)
            if self.LIST_POKEMON_BEFORE_CLEANUP:
                self.log.info(get_inventory_data(res, self.pokemon_names))
            self.incubate_eggs()
            self.attempt_evolve(self.inventory.inventory_items)
            self.cleanup_pokemon(self.inventory.inventory_items)
        # Auto-use lucky-egg if applicable
            self.use_lucky_egg()
        self._heartbeat_number += 1
        return res

    def use_lucky_egg(self):
        if self.config.get("AUTO_USE_LUCKY_EGG", False) and self.inventory.has_lucky_egg() and time() - self._last_egg_use_time > 30*60:
            self.use_item_xp_boost(item_id=Inventory.ITEM_LUCKY_EGG)
            response = self.call()
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

    def walk_to(self, loc, waypoints=[], directly=False):  # location in floats of course...
        steps = get_route(self._posf, loc, self.config.get("USE_GOOGLE", False), self.config.get("GMAPS_API_KEY", ""),
                          self.experimental and self.spin_all_forts, waypoints)
        catch_attempt = 0
        base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (self._posf[0], self._posf[1])
        step_size = self.config.get("STEP_SIZE", 200)
        total_distance_traveled = 0
        total_distance = distance_in_meters(self._posf, loc)
        new_loc = (loc[0], loc[1], 0)

        for step in steps:
            for i, next_point in enumerate(get_increments(self._posf, step, step_size)):
                # we are less than a step away, lets just go there!
                travel_remaining = total_distance - total_distance_traveled
                distance_to_point = distance_in_meters(self._posf, next_point)

                if travel_remaining < step_size or distance_to_point + total_distance_traveled > total_distance:
                    next_point = new_loc
                    distance_to_point = distance_in_meters(self._posf, next_point)

                total_distance_traveled += distance_to_point
                self.log.info('=================================')
                self.log.info(
                    "On my way to the next fort! :) Traveled %.2f meters of %.2f ",
                    total_distance_traveled,
                    total_distance,
                )

                travel_link = '%s%s,%s' % (base_travel_link, next_point[0], next_point[1])
                self.log.info("Travel Link: %s", travel_link)
                self.set_position(*next_point)
                self.heartbeat()

                if directly is False:
                    if self.experimental and self.spin_all_forts:
                        self.spin_nearest_fort()

                sleep(1)
                while self.catch_near_pokemon() and catch_attempt <= self.max_catch_attempts:
                    sleep(1)
                    catch_attempt += 1
                catch_attempt = 0

                # Don't continue with the steps if we've reached our location
                if next_point == new_loc:
                    self.log.info('=================================')
                    return

        self.log.info('=================================')

    def walk_back_to_origin(self):
        self.walk_to(self._origPosF)

    def spin_nearest_fort(self):
        map_cells = self.nearby_map_objects()['responses'].get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts)
        if destinations:
            nearest_fort = destinations[0][0]
            nearest_fort_dis = destinations[0][1]
            self.log.info('Nearest fort distance is %s', nearest_fort_dis)

            # Fort is close enough to change our route and walk to
            if nearest_fort_dis > 40.00 and nearest_fort_dis <= 100:
                lat = nearest_fort['latitude']
                long = nearest_fort['longitude']
                self.walk_to_fort(destinations[0], directly=True)
                self.fort_search_pgoapi(nearest_fort, player_postion=self.get_position(),
                                        fort_distance=nearest_fort_dis)
            if nearest_fort_dis <= 40.00:
                self.fort_search_pgoapi(nearest_fort, player_postion=self.get_position(),
                                        fort_distance=nearest_fort_dis)
            if 'lure_info' in nearest_fort and self.should_catch_pokemon:
                self.disk_encounter_pokemon(nearest_fort['lure_info'])

        else:
            self.log.info('No spinnable forts within proximity. Or server returned no map objects.')

    def fort_search_pgoapi(self, fort, player_postion, fort_distance):
        res = self.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'],
                               fort_longitude=fort['longitude'],
                               player_latitude=player_postion[0],
                               player_longitude=player_postion[1]).call()['responses']['FORT_SEARCH']
        result = res.pop('result', -1)
        if result == 1 and res:
            items = defaultdict(int)
            for item in res['items_awarded']:
                items[item['item_id']] += item['item_count']
            reward = 'XP +' + str(res['experience_awarded'])
            for item_id, amount in items.iteritems():
                reward += ', ' + str(amount) + 'x ' + get_item_name(item_id)
            self.log.debug("Fort spinned: %s", res)
            self.log.info("Fort Spinned, %s (http://maps.google.com/maps?q=%s,%s)",
                          reward, fort['latitude'], fort['longitude'])
            self.visited_forts[fort['id']] = fort
        elif result == 4:
            self.log.debug("For spinned but Your inventory is full : %s", res)
            self.log.info("For spinned but Your inventory is full.")
            self.visited_forts[fort['id']] = fort
        elif result == 2:
            self.log.debug("Could not spin fort -  fort not in range %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Not in Range %s", fort['latitude'],
                          fort['longitude'], fort_distance)
        else:
            self.log.debug("Could not spin fort %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Error id: %s", fort['latitude'],
                          fort['longitude'], result)
            return False
        return True

    def spin_all_forts_visible(self):
        res = self.nearby_map_objects()
        map_cells = res['responses'].get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts,
                                      self.experimental)
        if not destinations:
            self.log.info("No fort to walk to! %s", res)
            self.log.info('No more spinnable forts within proximity. Or server error')
            self.walk_back_to_origin()
            return False
        if len(destinations) >= 20:
            destinations = destinations[:20]
        furthest_fort = destinations[0][0]
        self.log.info("Walking to fort at  http://maps.google.com/maps?q=%s,%s", furthest_fort['latitude'],
                      furthest_fort['longitude'])
        self.walk_to((furthest_fort['latitude'], furthest_fort['longitude']),
                     map(lambda x: "via:%f,%f" % (x[0]['latitude'], x[0]['longitude']), destinations[1:]))
        return True

    def return_to_start(self):
        self.set_position(*self._origPosF)

    def walk_to_fort(self, fort_data, directly=False):
        fort = fort_data[0]
        self.log.info("Walking to fort at  http://maps.google.com/maps?q=%s,%s", fort['latitude'],
                        fort['longitude'])
        self.walk_to((fort['latitude'], fort['longitude']), directly=directly)
        self.fort_search_pgoapi(fort, self.get_position(), fort_data[1])
        if 'lure_info' in fort:
            self.disk_encounter_pokemon(fort['lure_info'])

    def spin_near_fort(self):
        res = self.nearby_map_objects()
        map_cells = res['responses'].get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts,
                                      self.experimental)
        if not destinations:
            self.log.debug("No fort to walk to! %s", res)
            self.log.info('No more spinnable forts within proximity. Returning back to origin')
            self.walk_back_to_origin()
            return False

        for fort_data in destinations:
            self.walk_to_fort(fort_data)

        return True

    def catch_near_pokemon(self):
        if self.should_catch_pokemon is False:
            return False

        map_cells = self.nearby_map_objects()['responses']['GET_MAP_OBJECTS']['map_cells']
        pokemons = PGoApi.flatmap(lambda c: c.get('catchable_pokemons', []), map_cells)

        # catch first pokemon:
        origin = (self._posf[0], self._posf[1])
        pokemon_distances = [(pokemon, distance_in_meters(origin, (pokemon['latitude'], pokemon['longitude']))) for
                             pokemon
                             in pokemons]
        if pokemons:
            self.log.debug("Nearby pokemon: : %s", pokemon_distances)
            self.log.info("Nearby Pokemon: %s",
                          ", ".join(map(lambda x: self.pokemon_names[str(x['pokemon_id'])], pokemons)))
        else:
            self.log.info("No nearby pokemon")
        catches_successful = False
        for pokemon_distance in pokemon_distances:
            target = pokemon_distance
            self.log.debug("Catching pokemon: : %s, distance: %f meters", target[0], target[1])
            catches_successful &= self.encounter_pokemon(target[0])
            sleep(random.randrange(4, 8))
        return catches_successful

    def nearby_map_objects(self):
        position = self.get_position()
        neighbors = getNeighbors(self._posf)
        return self.get_map_objects(latitude=position[0], longitude=position[1],
                                    since_timestamp_ms=[0] * len(neighbors),
                                    cell_id=neighbors).call()

    def attempt_catch(self, encounter_id, spawn_point_id, capture_probability=None):
        catch_status = -1
        catch_attempts = 1
        ret = {}
        if not capture_probability:
            capture_probability = {}
        # Max 4 attempts to catch pokemon
        while catch_status != 1 and self.inventory.can_attempt_catch() and catch_attempts < 11:
            pokeball = self.inventory.take_next_ball(capture_probability)
            self.log.info("Attempting catch with ball type {0}  at {1:.2f} % chance. Try Number: {2}".format(pokeball,
                          capture_probability.get(pokeball, 0.0) * 100, catch_attempts))
            r = self.catch_pokemon(
                normalized_reticle_size=1.950,
                pokeball=pokeball,
                spin_modifier=0.850,
                hit_pokemon=True,
                normalized_hit_position=1,
                encounter_id=encounter_id,
                spawn_point_id=spawn_point_id,
            ).call()['responses']['CATCH_POKEMON']
            catch_attempts += 1
            if "status" in r:
                catch_status = r['status']
                # fleed or error
                if catch_status == 3 or catch_status == 0:
                    break
            ret = r
            # Sleep between catch attempts
            sleep(3)
        # Sleep after the catch (the pokemon animation time)
        sleep(4)
        return ret

    def cleanup_inventory(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.get_inventory().call()['responses']['GET_INVENTORY']['inventory_delta'][
                'inventory_items']
        item_count = 0
        for inventory_item in inventory_items:
            if "item" in inventory_item['inventory_item_data']:
                item = inventory_item['inventory_item_data']['item']
                if item['item_id'] in self.MIN_ITEMS and "count" in item and item['count'] > self.MIN_ITEMS[
                    item['item_id']]:
                    recycle_count = item['count'] - self.MIN_ITEMS[item['item_id']]
                    item_count += item['count'] - recycle_count
                    self.log.info("Recycling Item_ID {0}, item count {1}".format(item['item_id'], recycle_count))
                    res = self.recycle_inventory_item(item_id=item['item_id'], count=recycle_count).call()['responses'][
                        'RECYCLE_INVENTORY_ITEM']
                    response_code = res['result']
                    if response_code == 1:
                        self.log.info("Recycled Item %s, New Count: %s", item['item_id'], res.get('new_count', 0))
                    else:
                        self.log.info("Failed to recycle Item %s, Code: %s", item['item_id'], response_code)
                    sleep(2)
                elif "count" in item:
                    item_count += item['count']
        if item_count > 0:
            self.log.info('Intentory has %s/%s items', item_count, self.player.max_item_storage)
        return self.update_player_inventory()

    def get_caught_pokemons(self, inventory_items):
        caught_pokemon = defaultdict(list)
        for inventory_item in inventory_items:
            if "pokemon_data" in inventory_item['inventory_item_data']:
                # is a pokemon:
                pokemon = Pokemon(inventory_item['inventory_item_data']['pokemon_data'], self.pokemon_names)
                pokemon.pokemon_additional_data = self.game_master.get(pokemon.pokemon_id, PokemonData())
                if not pokemon.is_egg:
                    caught_pokemon[pokemon.pokemon_id].append(pokemon)
        return caught_pokemon

    def do_release_pokemon(self, pokemon):
        self.log.info("Releasing pokemon: %s", pokemon)
        self.release_pokemon(pokemon_id=pokemon.id)
        release_res = self.call()['responses']['RELEASE_POKEMON']
        status = release_res.get('result', -1)
        if status == 1:
            self.log.info("Successfully Released Pokemon %s", pokemon)
        else:
            self.log.debug("Failed to release pokemon %s, %s", pokemon, release_res)
            self.log.info("Failed to release Pokemon %s", pokemon)
        sleep(3)

    def cleanup_pokemon(self, inventory_items=None):
        if not inventory_items:
                inventory_items = self.get_inventory().call()['responses']['GET_INVENTORY']['inventory_delta'][
                    'inventory_items']
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        for pokemons in caught_pokemon.values():
            if len(pokemons) > self.MIN_SIMILAR_POKEMON:
                # highest lvl pokemon first
                sorted_pokemons = sorted(pokemons, key=self.pokemon_lvl, reverse=True)
                for pokemon in sorted_pokemons[self.MIN_SIMILAR_POKEMON:]:
                    if self.is_pokemon_eligible_for_transfer(pokemon, sorted_pokemons[0]):
                        self.do_release_pokemon(pokemon)

    def is_pokemon_eligible_for_transfer(self, pokemon, best_pokemon):
        # never release favorites and other defined pokemons
        if pokemon.is_favorite or pokemon.pokemon_id in self.keep_pokemon_ids:
            return False
        elif self.RELEASE_DUPLICATES and (
                    self.pokemon_lvl(best_pokemon) * self.RELEASE_DUPLICATES_SCALER > self.pokemon_lvl(
                    pokemon) and self.pokemon_lvl(pokemon) < self.RELEASE_DUPLICATES_MAX_LV):
            return True
        # release defined throwaway pokemons  but make sure we have kept at least 1 (dont throw away all of them)
        elif pokemon.pokemon_id in self.throw_pokemon_ids:
            return True
        # keep high-cp pokemons
        elif pokemon.cp > self.KEEP_CP_OVER or pokemon.iv > self.KEEP_IV_OVER:
            return False
        # if we haven't found a reason to keep it, transfer it
        else:
            return True

    def pokemon_lvl(self, pokemon):
        if self.DEFINE_POKEMON_LV == "CP":
            return pokemon.cp
        elif self.DEFINE_POKEMON_LV == "IV":
            return pokemon.iv
        elif self.DEFINE_POKEMON_LV == "CP*IV":
            return pokemon.cp * pokemon.iv
        elif self.DEFINE_POKEMON_LV == "CP+IV":
            return pokemon.cp + pokemon.iv

    def attempt_evolve(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.get_inventory().call()['responses']['GET_INVENTORY']['inventory_delta'][
                'inventory_items']
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        self.inventory = Player_Inventory(inventory_items)
        for pokemons in caught_pokemon.values():
            if len(pokemons) > self.MIN_SIMILAR_POKEMON:
                pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)
                for pokemon in pokemons[self.MIN_SIMILAR_POKEMON:]:
                    # If we can't evolve this type of pokemon anymore, don't check others.
                    if not self.attempt_evolve_pokemon(pokemon):
                        break

    def attempt_evolve_pokemon(self, pokemon):
        if self.is_pokemon_eligible_for_evolution(pokemon=pokemon):
            self.log.info("Evolving pokemon: %s", pokemon)
            evo_res = self.evolve_pokemon(pokemon_id=pokemon.id).call()['responses']['EVOLVE_POKEMON']
            status = evo_res.get('result', -1)
            sleep(3)
            if status == 1:
                evolved_pokemon = Pokemon(evo_res.get('evolved_pokemon_data', {}), self.pokemon_names,
                                          self.game_master.get(str(pokemon.pokemon_id), PokemonData()))
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
        return self.inventory.pokemon_candy.get(self.POKEMON_EVOLUTION_FAMILY.get(pokemon.pokemon_id, None),
                                                -1) > self.POKEMON_EVOLUTION.get(pokemon.pokemon_id, None) \
               and pokemon.pokemon_id not in self.keep_pokemon_ids \
               and not pokemon.is_favorite \
               and pokemon.pokemon_id in self.POKEMON_EVOLUTION

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
                          self.pokemon_names.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            resp = self.disk_encounter(encounter_id=encounter_id, fort_id=fort_id, player_latitude=position[0],
                                       player_longitude=position[1]).call()['responses']['DISK_ENCOUNTER']
            pokemon = Pokemon(resp.get('pokemon_data', {}), self.pokemon_names)
            result = resp.get('result', -1)
            capture_probability = create_capture_probability(resp.get('capture_probability', {}))
            self.log.debug("Attempt Encounter: %s", json.dumps(resp, indent=4, sort_keys=True))
            if result == 1:
                return self.do_catch_pokemon(encounter_id, fort_id, capture_probability, pokemon)
            elif result == 5:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try",
                              self.pokemon_names.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
                self.cleanup_pokemon()
                if not retry:
                    return self.disk_encounter_pokemon(lureinfo, retry=True)
            else:
                self.log.info("Could not start Disk (lure) encounter for pokemon: %s",
                              self.pokemon_names.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
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

    def encounter_pokemon(self, pokemon_data, retry=False):  # take in a MapPokemon from MapCell.catchable_pokemons
        # Update Inventory to make sure we can catch this mon
        try:
            self.update_player_inventory()
            if not self.inventory.can_attempt_catch():
                self.log.info("No balls to catch %s, exiting encounter", self.inventory)
                return False
            encounter_id = pokemon_data['encounter_id']
            spawn_point_id = pokemon_data['spawn_point_id']
            # begin encounter_id
            position = self.get_position()
            self.log.info("Trying initiate catching Pokemon: %s", Pokemon(pokemon_data, self.pokemon_names))
            encounter = self.encounter(encounter_id=encounter_id,
                                       spawn_point_id=spawn_point_id,
                                       player_latitude=position[0],
                                       player_longitude=position[1]).call()['responses']['ENCOUNTER']
            self.log.debug("Attempting to Start Encounter: %s", encounter)
            pokemon = Pokemon(encounter.get('wild_pokemon', {}).get('pokemon_data', {}), self.pokemon_names)
            result = encounter.get('status', -1)
            capture_probability = create_capture_probability(encounter.get('capture_probability', {}))
            self.log.debug("Attempt Encounter Capture Probability: %s", json.dumps(encounter, indent=4, sort_keys=True))
            if result == 1:
                return self.do_catch_pokemon(encounter_id, spawn_point_id, capture_probability, pokemon)
            elif result == 7:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try", pokemon)
                self.cleanup_pokemon()
                if not retry:
                    return self.encounter_pokemon(pokemon, retry=True)
            else:
                self.log.info("Could not start encounter for pokemon: %s", pokemon)
            return False
        except Exception as e:
            self.log.error("Error in pokemon encounter %s", e)
            return False

    def incubate_eggs(self):
        if not self.EGG_INCUBATION_ENABLED:
            return
        if self.player_stats.km_walked > 0:
	    incubator_start_km_walked = self.player_stats.km_walked

            for incubator in self.inventory.incubators_busy:
		if 'start_km_walked' in incubator:
		    incubator_start_km_walked = incubator['start_km_walked']

                incubator_egg_distance = incubator['target_km_walked'] - incubator_start_km_walked
                incubator_distance_done = self.player_stats.km_walked - incubator_start_km_walked

                if incubator_distance_done > incubator_egg_distance:
                    self.attempt_finish_incubation()
                    break
            for incubator in self.inventory.incubators_busy:
		if 'start_km_walked' in incubator:
                    incubator_start_km_walked = incubator['start_km_walked']

                incubator_egg_distance = incubator['target_km_walked'] - incubator_start_km_walked
                incubator_distance_done = self.player_stats.km_walked - incubator_start_km_walked
                self.log.info('Incubating %skm egg, %skm done', incubator_egg_distance, round(incubator_distance_done, 2))
        for incubator in self.inventory.incubators_available:
            if incubator['item_id'] == 901:  # unlimited use
                pass
            elif self.USE_DISPOSABLE_INCUBATORS and incubator['item_id'] == 902:  # limited use
                pass
            else:
                continue
            eggs_available = self.inventory.eggs_available
            eggs_available = sorted(eggs_available, key=lambda egg: egg['creation_time_ms'],
                                    reverse=False)  # oldest first
            eggs_available = sorted(eggs_available, key=lambda egg: egg['egg_km_walked_target'],
                                    reverse=self.INCUBATE_BIG_EGGS_FIRST)  # now sort as defined
            if not len(eggs_available) > 0 or not self.attempt_start_incubation(eggs_available[0], incubator):
                break

    def attempt_start_incubation(self, egg, incubator):
        self.log.info("Start incubating %skm egg", egg['egg_km_walked_target'])
        incubate_res = self.use_item_egg_incubator(item_id=incubator['id'], pokemon_id=egg['id']).call()['responses']['USE_ITEM_EGG_INCUBATOR']
        status = incubate_res.get('result', -1)
        sleep(3)
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
        hatch_res = self.get_hatched_eggs().call()['responses']['GET_HATCHED_EGGS']
        status = hatch_res.get('success', -1)
        sleep(3)
        if status == 1:
            self.update_player_inventory()
            i = 0
            for pokemon_id in hatch_res['pokemon_id']:
                pokemon = get_pokemon_by_long_id(pokemon_id, self.inventory.inventory_items,
                                                    self.pokemon_names)
                self.log.info("Egg Hatched! XP +%s, Candy +%s, Stardust +%s, %s",
                              hatch_res['experience_awarded'][i],
                              hatch_res['candy_awarded'][i],
                              hatch_res['stardust_awarded'][i],
                              pokemon)
                i += 1
            return True
        else:
            self.log.debug("Could not get hatched eggs %s", hatch_res)
            self.log.info("Could not get hatched eggs Status %s", status)
            self.update_player_inventory()
            return False

    def login(self, provider, username, password, cached=False):
        if not isinstance(username, basestring) or not isinstance(password, basestring):
            raise AuthException("Username/password not correctly specified")

        if provider == 'ptc':
            self._auth_provider = AuthPtc()
        elif provider == 'google':
            self._auth_provider = AuthGoogle()
        else:
            raise AuthException("Invalid authentication provider - only ptc/google available.")

        self.log.debug('Auth provider: %s', provider)

        if not self._auth_provider.login(username, password):
            self.log.info('Login process failed')
            return False

        self.log.info('Starting RPC login sequence (app simulation)')
        # making a standard call, like it is also done by the client
        self.get_player()
        self.get_hatched_eggs()
        self.get_inventory()
        self.check_awarded_badges()
        self.download_settings(hash="05daf51635c82611d1aac95c0b051d3ec088a930")

        response = self.call()

        if not response:
            self.log.info('Login failed!')
        if os.path.isfile("auth_cache") and cached:
            response = pickle.load(open("auth_cache"))
        fname = "auth_cache_%s" % username
        if os.path.isfile(fname) and cached:
            response = pickle.load(open(fname))
        else:
            response = self.heartbeat()
            f = open(fname, "w")
            pickle.dump(response, f)
        if not response:
            self.log.info('Login failed!')
            return False

        if 'api_url' in response:
            self._api_endpoint = ('https://{}/rpc'.format(response['api_url']))
            self.log.debug('Setting API endpoint to: %s', self._api_endpoint)
        else:
            self.log.error('Login failed - unexpected server response!')
            return False

        if 'auth_ticket' in response:
            self._auth_provider.set_ticket(response['auth_ticket'].values())

        self.log.info('Finished RPC login sequence (app simulation)')
        self.log.info('Login process completed')

        return True

    def main_loop(self):
        catch_attempt = 0
        self.heartbeat()
        while True:
            self.heartbeat()
            sleep(1)

            if self.experimental and self.spin_all_forts:
                self.spin_all_forts_visible()
            else:
                self.spin_near_fort()
            # if catching fails 10 times, maybe you are sofbanned.
            while self.catch_near_pokemon() and catch_attempt <= self.max_catch_attempts:
                sleep(4)
                catch_attempt += 1
                pass
            if catch_attempt > self.max_catch_attempts:
                self.log.warn("Your account may be softbaned Or no Pokeballs. Failed to catch pokemon %s times",
                              catch_attempt)
            catch_attempt = 0

    @staticmethod
    def flatmap(f, items):
        return list(chain.from_iterable(imap(f, items)))
