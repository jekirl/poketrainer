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
from time import sleep
from Queue import *
from expiringdict import ExpiringDict

from pgoapi.auth_google import AuthGoogle
from pgoapi.auth_ptc import AuthPtc
from pgoapi.exceptions import AuthException, ServerBusyOrOfflineException
from pgoapi.inventory import Inventory as Player_Inventory
from pgoapi.location import *
from pgoapi.poke_utils import *
from pgoapi.protos.POGOProtos import Enums_pb2
from pgoapi.protos.POGOProtos import Inventory_pb2 as Inventory
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

        self.pokemon_caught = 0
        self.inventory = Player_Inventory([])

        self.pokemon_names = pokemon_names

        self.MIN_ITEMS = {}
        for k, v in config.get("MIN_ITEMS", {}).items():
            self.MIN_ITEMS[getattr(Inventory, k)] = v

        self.POKEMON_EVOLUTION = {}
        self.POKEMON_EVOLUTION_FAMILY = {}
        for k, v in config.get("POKEMON_EVOLUTION", {}).items():
            self.POKEMON_EVOLUTION[getattr(Enums_pb2, k)] = v
            self.POKEMON_EVOLUTION_FAMILY[getattr(Enums_pb2, k)] = getattr(Enums_pb2, "FAMILY_" + k)

        self.MIN_KEEP_IV = config.get("MIN_KEEP_IV", 0)  # release anything under this if we don't have it already
        self.KEEP_CP_OVER = config.get("KEEP_CP_OVER", 0)  # release anything under this if we don't have it already
        self.MIN_SIMILAR_POKEMON = config.get("MIN_SIMILAR_POKEMON", 1)  # Keep atleast one of everything.
        self.STAY_WITHIN_PROXIMITY = config.get("STAY_WITHIN_PROXIMITY", False)  # Stay within proximity

        self.visited_forts = ExpiringDict(max_len=120, max_age_seconds=config.get("SKIP_VISITED_FORT_DURATION", 600))
        self.experimental = config.get("EXPERIMENTAL", False)
        self.spin_all_forts = config.get("SPIN_ALL_FORTS", False)
        self.keep_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("KEEP_POKEMON_NAMES", []))
        self.throw_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("THROW_POKEMON_NAMES", []))
        self.max_catch_attempts = config.get("MAX_CATCH_ATTEMPTS", 10)
        self.game_master = parse_game_master()

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

    def update_player_inventory(self):
        self.get_inventory()
        res = self.call()
        if 'GET_INVENTORY' in res['responses']:
            self.inventory = Player_Inventory(res['responses']['GET_INVENTORY']['inventory_delta']['inventory_items'])
        self.log.info("Player Items: %s", self.inventory)

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
            player_data = res['responses'].get('GET_PLAYER', {}).get('player_data', {})
            currencies = player_data.get('currencies', [])
            currency_data = ",".join(
                map(lambda x: "{0}: {1}".format(x.get('name', 'NA'), x.get('amount', 'NA')), currencies))
            self.log.info("Username: %s, Currencies: %s, Pokemon Caught in this run: %s",
                          player_data.get('username', 'NA'), currency_data, self.pokemon_caught)

        if 'GET_INVENTORY' in res['responses']:
            with open("data_dumps/%s.json" % self.config['username'], "w") as f:
                res['responses']['lat'] = self._posf[0]
                res['responses']['lng'] = self._posf[1]
                f.write(json.dumps(res['responses'], indent=2))
            self.log.info(get_inventory_data(res, self.pokemon_names))
            self.log.info("Player Items: %s", self.inventory)
            self.inventory = Player_Inventory(res['responses']['GET_INVENTORY']['inventory_delta']['inventory_items'])
            self.log.debug(self.cleanup_inventory(self.inventory.inventory_items))
            self.attempt_evolve(self.inventory.inventory_items)
            self.cleanup_pokemon(self.inventory.inventory_items)

        self._heartbeat_number += 1
        return res

    def walk_to(self, loc, waypoints=[]):  # location in floats of course...
        steps = get_route(self._posf, loc, self.config.get("USE_GOOGLE", False), self.config.get("GMAPS_API_KEY", ""),
                          self.experimental and self.spin_all_forts, waypoints)
        catch_attempt = 0
        for step in steps:
            for i, next_point in enumerate(get_increments(self._posf, step, self.config.get("STEP_SIZE", 200))):
                self.set_position(*next_point)
                self.heartbeat()
                if self.experimental and self.spin_all_forts:
                    self.spin_nearest_fort()
                self.log.info("On my way to the next fort! :)")
                sleep(1)
                while self.catch_near_pokemon() and catch_attempt <= self.max_catch_attempts:
                    sleep(1)
                    catch_attempt += 1
                catch_attempt = 0

    def walk_back_to_origin(self):
        self.walk_to(self._origPosF)

    def spin_nearest_fort(self):
        map_cells = self.nearby_map_objects()['responses'].get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts)
        if destinations:
            nearest_fort = destinations[0][0]
            nearest_fort_dis = destinations[0][1]
            if nearest_fort_dis <= 40.00:
                self.fort_search_pgoapi(nearest_fort, player_postion=self.get_position(),
                                        fort_distance=nearest_fort_dis)
                if 'lure_info' in nearest_fort:
                    self.disk_encounter_pokemon(nearest_fort['lure_info'])
        else:
            self.log.info('No spinnable forts within proximity. Or server returned no map objects.')

    def fort_search_pgoapi(self, fort, player_postion, fort_distance):
        res = self.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'],
                               fort_longitude=fort['longitude'],
                               player_latitude=player_postion[0],
                               player_longitude=player_postion[1]).call()['responses']['FORT_SEARCH']
        if res['result'] == 1:
            self.log.debug("Fort spinned: %s", res)
            self.log.info("Fort Spinned: http://maps.google.com/maps?q=%s,%s", fort['latitude'], fort['longitude'])
            self.visited_forts[fort['id']] = fort
        elif res['result'] == 4:
            self.log.debug("For spinned but Your inventory is full : %s", res)
            self.log.info("For spinned but Your inventory is full.")
            self.visited_forts[fort['id']] = fort
        elif res['result'] == 2:
            self.log.debug("Could not spin fort -  fort not in range %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Not in Range %s", fort['latitude'],
                          fort['longitude'], fort_distance)
        else:
            self.log.debug("Could not spin fort %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Error id: %s", fort['latitude'],
                          fort['longitude'], res['result'])
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
            fort = fort_data[0]
            self.log.info("Walking to fort at  http://maps.google.com/maps?q=%s,%s", fort['latitude'],
                          fort['longitude'])
            self.walk_to((fort['latitude'], fort['longitude']))
            self.fort_search_pgoapi(fort, self.get_position(), fort_data[1])
            if 'lure_info' in fort:
                self.disk_encounter_pokemon(fort['lure_info'])
        return True

    def catch_near_pokemon(self):
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
            self.log.info("Catching Pokemon: %s", self.pokemon_names[str(target[0]['pokemon_id'])])
            catches_successful &= self.encounter_pokemon(target[0])
            sleep(random.randrange(4, 8))
        return catches_successful

    def nearby_map_objects(self):
        position = self.get_position()
        neighbors = getNeighbors(self._posf)
        return self.get_map_objects(latitude=position[0], longitude=position[1],
                                    since_timestamp_ms=[0] * len(neighbors),
                                    cell_id=neighbors).call()

    def attempt_catch(self, encounter_id, spawn_point_id):
        catch_status = -1
        catch_attempts = 0
        ret = {}
        # Max 4 attempts to catch pokemon
        while catch_status != 1 and self.inventory.can_attempt_catch() and catch_attempts < 5:
            pokeball = self.inventory.take_next_ball()
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
        if 'status' in ret:
            return ret
        return {}

    def cleanup_inventory(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.get_inventory().call()['responses']['GET_INVENTORY']['inventory_delta'][
                'inventory_items']
        for inventory_item in inventory_items:
            if "item" in inventory_item['inventory_item_data']:
                item = inventory_item['inventory_item_data']['item']
                if item['item_id'] in self.MIN_ITEMS and "count" in item and item['count'] > self.MIN_ITEMS[
                    item['item_id']]:
                    recycle_count = item['count'] - self.MIN_ITEMS[item['item_id']]
                    self.log.info("Recycling Item_ID {0}, item count {1}".format(item['item_id'], recycle_count))
                    res = self.recycle_inventory_item(item_id=item['item_id'], count=recycle_count).call()['responses'][
                        'RECYCLE_INVENTORY_ITEM']
                    response_code = res['result']
                    if response_code == 1:
                        self.log.info("Recycled Item %s, New Count: %s", item['item_id'], res.get('new_count', 0))
                    else:
                        self.log.info("Failed to recycle Item %s, Code: %s", item['item_id'], response_code)
                    sleep(2)
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

    def cleanup_pokemon(self, inventory_items=None):
        if not inventory_items:
                inventory_items = self.get_inventory().call()['responses']['GET_INVENTORY']['inventory_delta'][
                    'inventory_items']
        caught_pokemon = self.get_caught_pokemons(inventory_items)

        for pokemons in caught_pokemon.values():
            # Only if we have more than MIN_SIMILAR_POKEMON
            if len(pokemons) > self.MIN_SIMILAR_POKEMON:
                pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)
                # keep the first pokemon....
                for pokemon in pokemons[self.MIN_SIMILAR_POKEMON:]:
                    if self.is_pokemon_eligible_for_transfer(pokemon):
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

    def is_pokemon_eligible_for_transfer(self, pokemon):
        return (pokemon.pokemon_id in self.throw_pokemon_ids and not pokemon.is_favorite) \
               or (not pokemon.is_favorite and
                   pokemon.iv < self.MIN_KEEP_IV and
                   pokemon.cp < self.KEEP_CP_OVER and
                   pokemon.is_valid_pokemon() and
                   pokemon.pokemon_id not in self.keep_pokemon_ids)

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

        return False

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
            self.log.debug("At Fort with lure %s".encode('ascii', 'ignore'), lureinfo)
            self.log.info("At Fort with Lure AND Active Pokemon %s",
                          self.pokemon_names.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            resp = self.disk_encounter(encounter_id=encounter_id, fort_id=fort_id, player_latitude=position[0],
                                       player_longitude=position[1]).call()['responses']['DISK_ENCOUNTER']
            if resp['result'] == 1:
                capture_status = -1
                while capture_status != 0 and capture_status != 3:
                    catch_attempt = self.attempt_catch(encounter_id, fort_id)
                    capture_status = catch_attempt['status']
                    if capture_status == 1:
                        self.log.debug("(LURE) Caught Pokemon: : %s", catch_attempt)
                        self.log.info("(LURE) Caught Pokemon:  %s",
                                      self.pokemon_names.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
                        self.pokemon_caught += 1
                        sleep(2)
                        return True
                    elif capture_status != 2:
                        self.log.debug("(LURE) Failed Catch: : %s", catch_attempt)
                        self.log.info("(LURE) Failed to catch Pokemon:  %s",
                                      self.pokemon_names.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
                        return False
                    sleep(2)
            elif resp['result'] == 5:
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

    def encounter_pokemon(self, pokemon, retry=False):  # take in a MapPokemon from MapCell.catchable_pokemons
        # Update Inventory to make sure we can catch this mon
        self.update_player_inventory()
        if not self.inventory.can_attempt_catch():
            self.log.info("No balls to catch %s, exiting encounter", self.inventory)
            return False
        encounter_id = pokemon['encounter_id']
        spawn_point_id = pokemon['spawn_point_id']
        # begin encounter_id
        position = self.get_position()
        encounter = self.encounter(encounter_id=encounter_id,
                                   spawn_point_id=spawn_point_id,
                                   player_latitude=position[0],
                                   player_longitude=position[1]).call()['responses']['ENCOUNTER']
        self.log.debug("Attempting to Start Encounter: %s", encounter)
        if encounter['status'] == 1:
            capture_status = -1
            # while capture_status != RpcEnum.CATCH_ERROR and capture_status != RpcEnum.CATCH_FLEE:
            while capture_status != 0 and capture_status != 3:
                catch_attempt = self.attempt_catch(encounter_id, spawn_point_id)
                capture_status = catch_attempt.get('status', -1)
                # if status == RpcEnum.CATCH_SUCCESS:
                if capture_status == 1:
                    self.log.debug("Caught Pokemon: : %s", catch_attempt)
                    self.log.info("Caught Pokemon:  %s", self.pokemon_names.get(str(pokemon['pokemon_id']), "NA"))
                    self.pokemon_caught += 1
                    sleep(2)
                    return True
                elif capture_status != 2:
                    self.log.debug("Failed Catch: : %s", catch_attempt)
                    self.log.info("Failed to Catch Pokemon:  %s",
                                  self.pokemon_names.get(str(pokemon['pokemon_id']), "NA"))
                    return False
                sleep(2)
        elif encounter['status'] == 7:
            self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try",
                          self.pokemon_names.get(str(pokemon['pokemon_id']), "NA"))
            self.cleanup_pokemon()
            if not retry:
                return self.encounter_pokemon(pokemon, retry=True)
        else:
            self.log.info("Could not start encounter for pokemon: %s",
                          self.pokemon_names.get(str(pokemon['pokemon_id']), "NA"))
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

    def main_loop(self,queue):
        catch_attempt = 0
        self.heartbeat()
        # self.cleanup_inventory()
        while True:
            try:
                (function,args,kwargs) = queue.get_nowait()
                getattr(self,function)(*args,**kwargs)
                queue.task_done()
            except Empty:
                pass
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
