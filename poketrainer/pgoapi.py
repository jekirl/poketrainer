"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>
Modifications Copyright (c) 2016 j-e-k <https://github.com/j-e-k>
Modifications Copyright (c) 2016 Brad Smith <https://github.com/infinitewarp>

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
Modifications by: Brad Smith <https://github.com/infinitewarp>
"""

from __future__ import absolute_import

import copy
import hashlib
import json
import logging
import os
import pickle
import sys
from collections import defaultdict
from itertools import chain
from time import time

import gevent
import six
from cachetools import TTLCache
from gevent.coros import BoundedSemaphore

from pgoapi.exceptions import (AuthException, AuthTokenExpiredException,
                               NotLoggedInException,
                               ServerApiEndpointRedirectException,
                               ServerBusyOrOfflineException,
                               UnexpectedResponseException)
from .inventory import Inventory as Player_Inventory
from .location import (distance_in_meters, filtered_forts,
                       get_increments, get_neighbors, get_route)
from .player import Player as Player
from .player_stats import PlayerStats as PlayerStats
from .poke_utils import (create_capture_probability, get_inventory_data,
                         get_item_name, get_pokemon_by_long_id)
from .pokedex import pokedex
from .pokemon import POKEMON_NAMES, Pokemon
from .release.base import ReleaseMethodFactory
from pgoapi.rpc_api import RpcApi

from pgoapi.pgoapi import PGoApi as basePGoApi

from .utilities import parse_api_endpoint


if six.PY3:
    from builtins import map as imap
elif six.PY2:
    from itertools import imap

logger = logging.getLogger(__name__)

class PGoApi(basePGoApi):
    API_ENTRY = 'https://pgorelease.nianticlabs.com/plfe/rpc'

    def __init__(self, config):

        basePGoApi.__init__(self)


        self.config = config
        self.releaseMethodFactory = ReleaseMethodFactory(self.config)
        self._position_lat = 0  # int cooords
        self._position_lng = 0
        self._position_alt = 0
        self._error_counter = 0
        self._error_threshold = 10
        self._posf = (0, 0, 0)  # this is floats
        self._origPosF = (0, 0, 0)  # this is original position in floats
        self._req_method_list = {}
        self._heartbeat_number = 5
        self._firstRun = True
        self._last_egg_use_time = 0
        self._farm_mode_triggered = False
        self._orig_step_size = config.get("BEHAVIOR", {}).get("STEP_SIZE", 200)
        self.wander_steps = config.get("BEHAVIOR", {}).get("WANDER_STEPS", 0)
        pokeball_percent = config.get("CAPTURE", {}).get("USE_POKEBALL_IF_PERCENT", 50)
        greatball_percent = config.get("CAPTURE", {}).get("USE_GREATBALL_IF_PERCENT", 50)
        ultraball_percent = config.get("CAPTURE", {}).get("USE_ULTRABALL_IF_PERCENT", 50)
        use_masterball = config.get("CAPTURE", {}).get("USE_MASTERBALL", False)
        self.percentages = [pokeball_percent, greatball_percent, ultraball_percent, use_masterball]

        self.pokemon_caught = 0
        self.player = Player({})
        self.player_stats = PlayerStats({})
        self.inventory = Player_Inventory(self.percentages, [])

        self._last_got_map_objects = 0
        self._map_objects_rate_limit = 5.0
        self.map_objects = {}
        self.encountered_pokemons = TTLCache(maxsize=120, ttl=self._map_objects_rate_limit * 2)

        self.start_time = time()
        self.exp_start = None
        self.exp_current = None
        self.sem = BoundedSemaphore(1)
        self.persist_lock = False
        self.sleep_mult = self.config.get("BEHAVIOR", {}).get("SLEEP_MULT", 1.5)
        self.MIN_ITEMS = {}
        for k, v in config.get("MIN_ITEMS", {}).items():
            self.MIN_ITEMS[getattr(Inventory, k)] = v

        self.POKEMON_EVOLUTION = {}
        self.POKEMON_EVOLUTION_FAMILY = {}
        for k, v in config.get("POKEMON_EVOLUTION", {}).items():
            self.POKEMON_EVOLUTION[getattr(Enums_pb2, k)] = v
            self.POKEMON_EVOLUTION_FAMILY[getattr(Enums_pb2, k)] = getattr(Enums_pb2, "FAMILY_" + k)

        self.experimental = config.get("BEHAVIOR", {}).get("EXPERIMENTAL", False)

        self.STEP_SIZE = self._orig_step_size

        self.MIN_SIMILAR_POKEMON = config.get("POKEMON_CLEANUP", {}).get("MIN_SIMILAR_POKEMON", 1)  # Keep atleast one of everything.
        self.MAX_SIMILAR_POKEMON = config.get("POKEMON_CLEANUP", {}).get("MAX_SIMILAR_POKEMON", 999)  # Stop keeping them at some amount
        self.keep_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("POKEMON_CLEANUP", {}).get("KEEP_POKEMON_NAMES", []))
        self.throw_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("POKEMON_CLEANUP", {}).get("THROW_POKEMON_NAMES", []))

        self.RELEASE_METHOD = config.get("POKEMON_CLEANUP", {}).get("RELEASE_METHOD", "CLASSIC")
        self.RELEASE_METHOD_CONF = config.get("POKEMON_CLEANUP", {}).get("RELEASE_METHOD_" + self.RELEASE_METHOD, {})

        # though we get RELEASE_METHOD_CONF, we still get the options for the classic method individually,
        # because it is the fallback method (will be used if RELEASE_METHOD is configured incorrectly)
        self.KEEP_CP_OVER = config.get("POKEMON_CLEANUP", {}).get("RELEASE_METHOD_CLASSIC", {})\
            .get("KEEP_CP_OVER", 0)  # release anything under this
        self.KEEP_IV_OVER = config.get("POKEMON_CLEANUP", {}).get("RELEASE_METHOD_CLASSIC", {})\
            .get("KEEP_IV_OVER", 0)  # release anything under this

        self.SCORE_METHOD = config.get("POKEMON_CLEANUP", {}).get("SCORE_METHOD", "CP")
        self.SCORE_SETTINGS = config.get("POKEMON_CLEANUP", {}).get("SCORE_METHOD_" + self.SCORE_METHOD, {})

        self.EGG_INCUBATION_ENABLED = config.get("EGG_INCUBATION", {}).get("ENABLE", True)
        self.USE_DISPOSABLE_INCUBATORS = config.get("EGG_INCUBATION", {}).get("USE_DISPOSABLE_INCUBATORS", False)
        self.INCUBATE_BIG_EGGS_FIRST = config.get("EGG_INCUBATION", {}).get("BIG_EGGS_FIRST", True)

        self.FARM_ITEMS_ENABLED = config.get("NEEDY_ITEM_FARMING", {}).get("ENABLE",
                                                                           True and self.experimental)  # be concious of pokeball/item limits
        self.POKEBALL_CONTINUE_THRESHOLD = config.get("NEEDY_ITEM_FARMING", {}).get("POKEBALL_CONTINUE_THRESHOLD",
                                                                                    50)  # keep at least 10 pokeballs of any assortment, otherwise go farming
        self.POKEBALL_FARM_THRESHOLD = config.get("NEEDY_ITEM_FARMING", {}).get("POKEBALL_FARM_THRESHOLD",
                                                                                10)  # at this point, go collect pokeballs
        self.FARM_IGNORE_POKEBALL_COUNT = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_POKEBALL_COUNT",
                                                                                   False)  # ignore pokeballs in the continue tally
        self.FARM_IGNORE_GREATBALL_COUNT = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_GREATBALL_COUNT",
                                                                                    False)  # ignore greatballs in the continue tally
        self.FARM_IGNORE_ULTRABALL_COUNT = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_ULTRABALL_COUNT",
                                                                                    False)  # ignore ultraballs in the continue tally
        self.FARM_IGNORE_MASTERBALL_COUNT = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_MASTERBALL_COUNT",
                                                                                     True)  # ignore masterballs in the continue tally
        self.FARM_OVERRIDE_STEP_SIZE = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_OVERRIDE_STEP_SIZE",
                                                                                -1)  # should the step size be overriden when looking for more inventory, -1 to disable
        self.LIST_POKEMON_BEFORE_CLEANUP = config.get("CONSOLE_OUTPUT", {}).get("LIST_POKEMON_BEFORE_CLEANUP", True)  # list pokemon in console
        self.LIST_INVENTORY_BEFORE_CLEANUP = config.get("CONSOLE_OUTPUT", {}).get("LIST_INVENTORY_BEFORE_CLEANUP", True)  # list inventory in console

        self.visited_forts = TTLCache(maxsize=120, ttl=config.get("BEHAVIOR", {}).get("SKIP_VISITED_FORT_DURATION", 600))
        self.spin_all_forts = config.get("BEHAVIOR", {}).get("SPIN_ALL_FORTS", False)
        self.STAY_WITHIN_PROXIMITY = config.get("BEHAVIOR", {}).get("STAY_WITHIN_PROXIMITY", 9999999)  # Stay within proximity
        self.should_catch_pokemon = config.get("CAPTURE", {}).get("CATCH_POKEMON", True)
        self.max_catch_attempts = config.get("CAPTURE", {}).get("MAX_CATCH_ATTEMPTS", 10)

        # Sanity checking
        self.FARM_ITEMS_ENABLED = self.FARM_ITEMS_ENABLED and self.experimental and self.should_catch_pokemon  # Experimental, and we needn't do this if we're farming anyway
        if (
            self.FARM_ITEMS_ENABLED and
            self.FARM_IGNORE_POKEBALL_COUNT and
            self.FARM_IGNORE_GREATBALL_COUNT and
            self.FARM_IGNORE_ULTRABALL_COUNT and
            self.FARM_IGNORE_MASTERBALL_COUNT
        ):
            self.FARM_ITEMS_ENABLED = False
            self.log.warn("FARM_ITEMS has been disabled due to all Pokeball counts being ignored.")
        elif self.FARM_ITEMS_ENABLED and not (self.POKEBALL_FARM_THRESHOLD < self.POKEBALL_CONTINUE_THRESHOLD):
            self.FARM_ITEMS_ENABLED = False
            self.log.warn(
                "FARM_ITEMS has been disabled due to farming threshold being below the continue. Set 'CATCH_POKEMON' to 'false' to enable captureless traveling.")

        self.new_forts = []
        self.cache_filename = './cache/cache ' + (hashlib.md5(config.get("location", "unavailable").encode())).hexdigest() + str(self.STAY_WITHIN_PROXIMITY)
        self.all_cached_forts = []
        self.spinnable_cached_forts = []
        self.use_cache = self.config.get("BEHAVIOR", {}).get("USE_CACHED_FORTS", False)
        self.cache_is_sorted = self.config.get("BEHAVIOR", {}).get("CACHED_FORTS_SORTED", False)
        self.enable_caching = self.config.get("BEHAVIOR", {}).get("ENABLE_CACHING", False)

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

    def gsleep(self, t):
        gevent.sleep(t * self.sleep_mult)

    def activate_signature(self, lib_path):
        self._signature_lib = lib_path

    def get_signature_lib(self):
        return self._signature_lib

    def get_api_endpoint(self):
        return self._api_endpoint

    def set_api_endpoint(self, api_url):
        if api_url.startswith("https"):
            self._api_endpoint = api_url
        else:
            self._api_endpoint = parse_api_endpoint(api_url)

    def call(self):
        self.cond_lock()
        self.gsleep(self.config.get("BEHAVIOR", {}).get("EXTRA_WAIT", 0.3))
        try:
            if not self._req_method_list.get(id(gevent.getcurrent()), []):
                return False

            if self._auth_provider is None or not self._auth_provider.is_login():
                self.log.info('Not logged in')
                return False

            player_position = self.get_position()

            request = RpcApi(self._auth_provider)

            if self.get_signature_lib() is not None:
                request.activate_signature(self.get_signature_lib())

            self.log.debug('Execution of RPC')
            response = None
            execute = True

            while execute:
                execute = False

                try:
                    response = request.request(self.get_api_endpoint(), self._req_method_list[id(gevent.getcurrent())], player_position)
                except AuthTokenExpiredException as e:
                    """
                    This exception only occures if the OAUTH service provider (google/ptc) didn't send any expiration date
                    so that we are assuming, that the access_token is always valid until the API server states differently.
                    """
                    try:
                        self.log.info('Access Token rejected! Requesting new one...')
                        self._auth_provider.get_access_token(force_refresh=True)
                    except:
                        error = 'Request for new Access Token failed! Logged out...'
                        self.log.error(error)
                        raise NotLoggedInException(error)

                    """ reexecute the call"""
                    execute = True
                except ServerApiEndpointRedirectException as e:
                    self.log.info('API Endpoint redirect... re-execution of call')
                    new_api_endpoint = e.get_redirected_endpoint()

                    self._api_endpoint = parse_api_endpoint(new_api_endpoint)
                    self.set_api_endpoint(self._api_endpoint)

                    """ reexecute the call"""
                    execute = True
                except ServerBusyOrOfflineException as e:
                    """ no execute = True here, as API retries on HTTP level should be done on a lower level, e.g. in rpc_api """
                    self.log.info('Server seems to be busy or offline - try again!')
                    self.log.debug('ServerBusyOrOfflineException details: %s', e)
                except UnexpectedResponseException as e:
                    self.log.error('Unexpected server response!')
                    raise

            # cleanup after call execution
            self.log.debug('Cleanup of request!')
            self._req_method_list[id(gevent.getcurrent())] = []

            return response
            # request = self.create_request()
            # return request.call()
        finally:
            self.cond_release()

    def list_curr_methods(self):
        for i in self._req_method_list.get(id(gevent.getcurrent()), []):
            print("{} ({})".format(RequestType.Name(i), i))

    def get_position(self):
        return (self._position_lat, self._position_lng, self._position_alt)

    def set_position(self, lat, lng, alt):
        self.log.debug('Set Position - Lat: %s Long: %s Alt: %s', lat, lng, alt)
        self._posf = (lat, lng, alt)
        if self._firstRun:
            self._firstRun = False
            self._origPosF = self._posf
        self._position_lat = lat
        self._position_lng = lng
        self._position_alt = alt

    def __getattr__(self, func):
        def function(**kwargs):

            if not self._req_method_list.get(id(gevent.getcurrent()), []):
                self.log.debug('Create new request...')
                self._req_method_list[id(gevent.getcurrent())] = []

            name = func.upper()
            if kwargs:
                self._req_method_list[id(gevent.getcurrent())].append({RequestType.Value(name): kwargs})
                self.log.debug("Adding '%s' to RPC request including arguments", name)
                self.log.debug("Arguments of '%s': \n\r%s", name, kwargs)
            else:
                self._req_method_list[id(gevent.getcurrent())].append(RequestType.Value(name))
                self.log.debug("Adding '%s' to RPC request", name)
            return self
        if func.upper() in RequestType.keys():
            return function
        else:
            raise AttributeError

    # instead of a full heartbeat, just update position.
    # useful for sniping for example
    def send_update_pos(self):
        self.get_player()
        self.gsleep(0.2)
        res = self.call()
        if not res or res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Can't snipe!", res)
            return False
        return True

    def snipe_pokemon(self, lat, lng):
        self.cond_lock(persist=True)
        try:
            self.gsleep(2) # might not be needed, used to prevent main thread from issuing a waiting-for-lock server query too quickly
            curr_lat = self._posf[0]
            curr_lng = self._posf[1]

            self.log.info("Sniping pokemon at %f, %f", lat, lng)
            self.log.info("Waiting for API limit timer ...")
            while time() - self._last_got_map_objects < self._map_objects_rate_limit:
                self.gsleep(0.1)

            # move to snipe location
            self.set_position(lat, lng, 0.0)
            if not self.send_update_pos():
                return False

            self.log.debug("Teleported to sniping location %f, %f", lat, lng)

            # find pokemons in dest
            map_cells = self.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
            pokemons = PGoApi.flatmap(lambda c: c.get('catchable_pokemons', []), map_cells)

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
            self.set_position(curr_lat, curr_lng, 0.0)
            self.send_update_pos()
            self.log.debug("Teleported back to origin at %f, %f", self._posf[0], self._posf[1])
            # self.gsleep(2) # might not be needed, used to prevent main thread from issuing a waiting-for-lock server query too quickly
            self.persist_lock = False
            self.cond_release()

    def hourly_exp(self, exp):
        # This check is to prevent a bug with the exp not always coming in corretly on the first response
        # (it often comes in as 0 initially, thereby messing up the whole XP/hour stat)
        # This still works fine on a brand new trainer with no XP, just that the XP/hour calculation
        # will be delayed until they earn their first XP.
        if exp <= 0:
            return

        if self.exp_start is None:
            self.exp_start = exp
        self.exp_current = exp

        run_time = time() - self.start_time
        run_time_hours = float(run_time / 3600.00)
        exp_earned = float(self.exp_current - self.exp_start)
        exp_hour = float(exp_earned / run_time_hours)

        self.log.info("=== Running Time (hours): %s, Exp/Hour: %s ===", round(run_time_hours, 2), round(exp_hour))

        return exp_hour

    def update_player_inventory(self):
        self.get_inventory()
        self.gsleep(0.2)
        res = self.call()
        if 'GET_INVENTORY' in res.get('responses', {}):
            inventory_items = res.get('responses', {})\
                .get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
            self.inventory = Player_Inventory(self.percentages, inventory_items)
        return res

    def get_player_inventory(self, as_json=True):
        return self.inventory.to_json()

    def heartbeat(self):
        # making a standard call to update position, etc
        self.get_player()
        if self._heartbeat_number % 10 == 0:
            self.check_awarded_badges()
            self.get_inventory()
        # self.download_settings(hash="4a2e9bc330dae60e7b74fc85b98868ab4700802e")
        self.gsleep(0.2)
        res = self.call()
        if not res or res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Restarting!!!", res)
            raise AuthException("Token probably expired?")
        self.log.debug('Heartbeat dictionary: \n\r{}'.format(json.dumps(res, indent=2, default=lambda obj: obj.decode('utf8'))))

        responses = res.get('responses', {})
        if 'GET_PLAYER' in responses:
            self.player = Player(responses.get('GET_PLAYER', {}).get('player_data', {}))
            self.log.info("Player Info: {0}, Pokemon Caught in this run: {1}".format(self.player, self.pokemon_caught))

        if 'GET_INVENTORY' in res.get('responses', {}):
            with open("data_dumps/%s.json" % self.config['username'], "w") as f:
                responses['lat'] = self._posf[0]
                responses['lng'] = self._posf[1]
                responses['hourly_exp'] = self.hourly_exp(self.player_stats.experience)
                f.write(json.dumps(responses, indent=2, default=lambda obj: obj.decode('utf8')))

            inventory_items = responses.get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
            self.inventory = Player_Inventory(self.percentages, inventory_items)
            for inventory_item in self.inventory.inventory_items:
                if "player_stats" in inventory_item['inventory_item_data']:
                    self.player_stats = PlayerStats(inventory_item['inventory_item_data']['player_stats'])
                    self.log.info("Player Stats: {}".format(self.player_stats))
                    self.hourly_exp(self.player_stats.experience)
            if self.LIST_INVENTORY_BEFORE_CLEANUP:
                self.log.info("Player Items Before Cleanup: %s", self.inventory)
            self.log.debug(self.cleanup_inventory(self.inventory.inventory_items))
            self.log.info("Player Inventory after cleanup: %s", self.inventory)
            if self.LIST_POKEMON_BEFORE_CLEANUP:
                self.log.info(get_inventory_data(res, self.player_stats.level, self.SCORE_METHOD, self.SCORE_SETTINGS))
            self.incubate_eggs()
            # Auto-use lucky-egg if applicable
            self.use_lucky_egg()
            self.attempt_evolve(self.inventory.inventory_items)
            self.cleanup_pokemon(self.inventory.inventory_items)

            # Farm precon
            if self.FARM_ITEMS_ENABLED:
                pokeball_count = 0
                if not self.FARM_IGNORE_POKEBALL_COUNT:
                    pokeball_count += self.inventory.poke_balls
                if not self.FARM_IGNORE_GREATBALL_COUNT:
                    pokeball_count += self.inventory.great_balls
                if not self.FARM_IGNORE_ULTRABALL_COUNT:
                    pokeball_count += self.inventory.ultra_balls
                if not self.FARM_IGNORE_MASTERBALL_COUNT:
                    pokeball_count += self.inventory.master_balls
                if self.POKEBALL_FARM_THRESHOLD > pokeball_count and not self._farm_mode_triggered:
                    self.should_catch_pokemon = False
                    self._farm_mode_triggered = True
                    self.log.info("Player only has %s Pokeballs, farming for more...", pokeball_count)
                    if self.FARM_OVERRIDE_STEP_SIZE != -1:
                        self.STEP_SIZE = self.FARM_OVERRIDE_STEP_SIZE
                        self.log.info("Player has changed speed to %s", self.STEP_SIZE)
                elif self.POKEBALL_CONTINUE_THRESHOLD <= pokeball_count and self._farm_mode_triggered:
                    self.should_catch_pokemon = self.config.get("CAPTURE", {}).get("CATCH_POKEMON", True) # Restore catch pokemon setting from config file
                    self._farm_mode_triggered = False
                    self.log.info("Player has %s Pokeballs, continuing to catch more!", pokeball_count)
                    if self.FARM_OVERRIDE_STEP_SIZE != -1:
                        self.STEP_SIZE = self._orig_step_size
                        self.log.info("Player has returned to normal speed of %s", self.STEP_SIZE)
        self._heartbeat_number += 1
        return res

    def use_lucky_egg(self):
        if self.config.get("BEHAVIOR", {}).get("AUTO_USE_LUCKY_EGG", False) and \
                self.inventory.has_lucky_egg() and time() - self._last_egg_use_time > 30 * 60:
            self.use_item_xp_boost(item_id=Inventory.ITEM_LUCKY_EGG)
            self.gsleep(0.2)
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
        # If we are going directly we don't want to follow a google maps
        # walkable route.
        use_google = self.config.get("BEHAVIOR", {}).get("USE_GOOGLE", False)

        if directly is True:
            use_google = False

        step_size = self.STEP_SIZE
        route_data = get_route(
            self._posf, loc, use_google, self.config.get("GMAPS_API_KEY", ""),
            self.experimental and self.spin_all_forts, waypoints,
            step_size=step_size
        )
        catch_attempt = 0
        base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (self._posf[0], self._posf[1])
        total_distance_traveled = 0
        total_distance = route_data['total_distance']
        self.log.info('===============================================')
        self.log.info("Total trip distance will be: {0:.2f} meters".format(total_distance))

        for step_data in route_data['steps']:
            step = (step_data['lat'], step_data['long'])
            step_increments = get_increments(self._posf, step, step_size)

            for i, next_point in enumerate(step_increments):
                distance_to_point = distance_in_meters(self._posf, next_point)
                total_distance_traveled += distance_to_point
                travel_link = '%s%s,%s' % (base_travel_link, next_point[0], next_point[1])
                self.log.info("Travel Link: %s", travel_link)
                self.set_position(*next_point)
                self.heartbeat()

                if directly is False:
                    if self.experimental and self.spin_all_forts:
                        self.spin_nearest_fort()

                # self.gsleep(1)
                while self.catch_near_pokemon() and catch_attempt <= self.max_catch_attempts:
                    self.gsleep(1)
                    catch_attempt += 1
                catch_attempt = 0

            self.log.info('Traveled %.2f meters of %.2f of the trip', total_distance_traveled, total_distance)
        self.log.info('===============================================')

    def walk_back_to_origin(self):
        self.walk_to(self._origPosF)

    def spin_nearest_fort(self):
        map_cells = self.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts)

        if destinations:
            self.new_forts = destinations
            nearest_fort = destinations[0][0]
            nearest_fort_dis = destinations[0][1]
            self.log.info("Nearest fort distance is {0:.2f} meters".format(nearest_fort_dis))

            # Fort is close enough to change our route and walk to
            if self.wander_steps > 0 and nearest_fort_dis > 40.00 and nearest_fort_dis <= self.wander_steps:
                    self.walk_to_fort(destinations[0], directly=True)
            elif nearest_fort_dis <= 40.00:
                self.fort_search_pgoapi(nearest_fort, player_postion=self.get_position(),
                                        fort_distance=nearest_fort_dis)
                if 'lure_info' in nearest_fort and self.should_catch_pokemon:
                    self.disk_encounter_pokemon(nearest_fort['lure_info'])

        else:
            self.log.info('No spinnable forts within proximity. Or server returned no map objects.')
            self._error_counter += 1

    def fort_search_pgoapi(self, fort, player_postion, fort_distance):
        self.gsleep(0.2)
        res = self.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'],
                               fort_longitude=fort['longitude'],
                               player_latitude=player_postion[0],
                               player_longitude=player_postion[1]).call()
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
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Still on cooldown", fort['latitude'],
                          fort['longitude'])
        else:
            self.log.debug("Could not spin fort %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Error id: %s", fort['latitude'],
                          fort['longitude'], result)
            return False
        return True

    def spin_all_forts_visible(self):
        res = self.nearby_map_objects()
        self.log.debug("nearyby_map_objects: %s", res)
        map_cells = res.get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts)
        if not destinations:
            self.log.debug("No fort to walk to! %s", res)
            self.log.info('No more spinnable forts within proximity. Or server error')
            self._error_counter += 1
            self.walk_back_to_origin()
            return False
        self.new_forts = destinations
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
        self.log.info(
            "Walking to fort at  http://maps.google.com/maps?q=%s,%s",
            fort['latitude'], fort['longitude'])
        self.walk_to((fort['latitude'], fort['longitude']), directly=directly)
        self.fort_search_pgoapi(fort, self.get_position(), fort_data[1])
        if 'lure_info' in fort and self.should_catch_pokemon:
            self.disk_encounter_pokemon(fort['lure_info'])

    def spin_near_fort(self):
        res = self.nearby_map_objects()
        self.log.debug("nearyby_map_objects: %s", res)
        map_cells = res.get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self._origPosF, self._posf, forts, self.STAY_WITHIN_PROXIMITY, self.visited_forts)

        if not destinations:
            self.log.debug("No fort to walk to! %s", res)
            self.log.info('No more spinnable forts within proximity. Returning back to origin')
            self.walk_back_to_origin()
            return False
        self.new_forts = destinations
        for fort_data in destinations:
            self.walk_to_fort(fort_data)

        return True

    def catch_near_pokemon(self):
        if self.should_catch_pokemon is False:
            return False

        map_cells = self.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        pokemons = PGoApi.flatmap(lambda c: c.get('catchable_pokemons', []), map_cells)
        pokemons = filter(lambda p: (p['encounter_id'] not in self.encountered_pokemons), pokemons)

        # catch first pokemon:
        origin = (self._posf[0], self._posf[1])
        pokemon_distances = [(pokemon, distance_in_meters(origin, (pokemon['latitude'], pokemon['longitude']))) for
                             pokemon
                             in pokemons]
        if pokemons:
            self.log.debug("Nearby pokemon: : %s", pokemon_distances)
            self.log.info("Nearby Pokemon: %s",
                          ", ".join(map(lambda x: POKEMON_NAMES[str(x['pokemon_id'])], pokemons)))
        else:
            self.log.info("No nearby pokemon")
        catches_successful = False
        for pokemon_distance in pokemon_distances:
            target = pokemon_distance
            self.log.debug("Catching pokemon: : %s, distance: %f meters", target[0], target[1])
            catches_successful &= self.encounter_pokemon(target[0])
            # self.gsleep(random.randrange(4, 8))
        return catches_successful

    def nearby_map_objects(self):
        if time() - self._last_got_map_objects > self._map_objects_rate_limit:
            position = self.get_position()
            neighbors = get_neighbors(self._posf)
            gevent.sleep(1.0)
            self.map_objects = self.get_map_objects(
                latitude=position[0], longitude=position[1],
                since_timestamp_ms=[0, ] * len(neighbors),
                cell_id=neighbors).call()
            self._last_got_map_objects = time()
        return self.map_objects

    def attempt_catch(self, encounter_id, spawn_point_id, capture_probability=None):
        catch_status = -1
        catch_attempts = 1
        ret = {}
        if not capture_probability:
            capture_probability = {}
        # Max 4 attempts to catch pokemon
        while catch_status != 1 and self.inventory.can_attempt_catch() and catch_attempts <= self.max_catch_attempts:
            item_capture_mult = 1.0

            # Try to use a berry to increase the chance of catching the pokemon when we have failed enough attempts
            if catch_attempts > self.config.get("CAPTURE", {}).get("MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY", 3) \
                    and self.inventory.has_berry():
                self.log.info("Feeding da razz berry!")
                self.gsleep(0.2)
                r = self.use_item_capture(item_id=self.inventory.take_berry(), encounter_id=encounter_id,
                                          spawn_point_id=spawn_point_id).call()\
                    .get('responses', {}).get('USE_ITEM_CAPTURE', {})
                if r.get("success", False):
                    item_capture_mult = r.get("item_capture_mult", 1.0)
                else:
                    self.log.info("Could not feed the Pokemon. (%s)", r)

            pokeball = self.inventory.take_next_ball(capture_probability)
            self.log.info("Attempting catch with {0} at {1:.2f}% chance. Try Number: {2}".format(get_item_name(
                          pokeball), item_capture_mult * capture_probability.get(pokeball, 0.0) * 100, catch_attempts))
            self.gsleep(0.5)
            r = self.catch_pokemon(
                normalized_reticle_size=1.950,
                pokeball=pokeball,
                spin_modifier=0.850,
                hit_pokemon=True,
                normalized_hit_position=1,
                encounter_id=encounter_id,
                spawn_point_id=spawn_point_id,
            ).call().get('responses', {}).get('CATCH_POKEMON', {})
            catch_attempts += 1
            if "status" in r:
                catch_status = r['status']
                # fleed or error
                if catch_status == 3 or catch_status == 0:
                    break
            ret = r
            # Sleep between catch attempts
            # self.gsleep(3)
        # Sleep after the catch (the pokemon animation time)
        # self.gsleep(4)
        return ret

    def cleanup_inventory(self, inventory_items=None):
        if not inventory_items:
            self.gsleep(0.2)
            inventory_items = self.get_inventory().call()\
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        item_count = 0
        for inventory_item in inventory_items:
            if "item" in inventory_item['inventory_item_data']:
                item = inventory_item['inventory_item_data']['item']
                if (
                    item['item_id'] in self.MIN_ITEMS and
                    "count" in item and
                    item['count'] > self.MIN_ITEMS[item['item_id']]
                ):
                    recycle_count = item['count'] - self.MIN_ITEMS[item['item_id']]
                    item_count += item['count'] - recycle_count
                    self.log.info("Recycling {0} {1}(s)".format(recycle_count, get_item_name(item['item_id'])))
                    self.gsleep(0.2)
                    res = self.recycle_inventory_item(item_id=item['item_id'], count=recycle_count).call()\
                        .get('responses', {}).get('RECYCLE_INVENTORY_ITEM', {})
                    response_code = res.get('result', -1)
                    if response_code == 1:
                        self.log.info("{0}(s) recycled successfully. New count: {1}".format(get_item_name(
                                      item['item_id']), res.get('new_count', 0)))
                    else:
                        self.log.info("Failed to recycle {0}, Code: {1}".format(get_item_name(item['item_id']),
                                                                                response_code))
                    self.gsleep(1)
                elif "count" in item:
                    item_count += item['count']
        if item_count > 0:
            self.log.info("Inventory has {0}/{1} items".format(item_count, self.player.max_item_storage))
        return self.update_player_inventory()

    def get_caught_pokemons(self, inventory_items=None, as_json=False):
        if not inventory_items:
            self.gsleep(0.2)
            inventory_items = self.get_inventory().call()\
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = defaultdict(list)
        for inventory_item in inventory_items:
            if "pokemon_data" in inventory_item['inventory_item_data'] and not inventory_item['inventory_item_data']['pokemon_data'].get("is_egg", False):
                # is a pokemon:
                pokemon_data = inventory_item['inventory_item_data']['pokemon_data']
                pokemon = Pokemon(pokemon_data, self.player_stats.level, self.SCORE_METHOD, self.SCORE_SETTINGS)

                if not pokemon.is_egg:
                    caught_pokemon[pokemon.pokemon_id].append(pokemon)
        if as_json:
            return json.dumps(caught_pokemon, default=lambda p: p.__dict__)  # reduce the data sent?
        return caught_pokemon

    def get_player_info(self, as_json=True):
        return self.player.to_json()

    def do_release_pokemon_by_id(self, p_id):
        self.release_pokemon(pokemon_id=int(p_id))
        self.gsleep(0.2)
        release_res = self.call().get('responses', {}).get('RELEASE_POKEMON', {})
        status = release_res.get('result', -1)
        return status

    def do_release_pokemon(self, pokemon):
        self.log.info("Releasing pokemon: %s", pokemon)
        if self.do_release_pokemon_by_id(pokemon.id):
            self.log.info("Successfully Released Pokemon %s", pokemon)
        else:
            # self.log.debug("Failed to release pokemon %s, %s", pokemon, release_res)  # FIXME release_res is not in scope!
            self.log.info("Failed to release Pokemon %s", pokemon)
        self.gsleep(1.0)

    def get_pokemon_stats(self, inventory_items=None):
        if not inventory_items:
            self.gsleep(0.2)
            inventory_items = self.get_inventory().call()\
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        for pokemons in caught_pokemon.values():
            for pokemon in pokemons:
                self.log.info("%s", pokemon)

    def cleanup_pokemon(self, inventory_items=None):
        if not inventory_items:
            self.gsleep(0.2)
            inventory_items = self.get_inventory().call()\
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        release_method = self.releaseMethodFactory.getReleaseMethod()
        for pokemonId, pokemons in six.iteritems(caught_pokemon):
            pokemonsToRelease, pokemonsToKeep = release_method.getPokemonToRelease(pokemonId, pokemons)

            if self.config.get('POKEMON_CLEANUP', {}).get('TESTING_MODE', False):
                for pokemon in pokemonsToRelease:
                    self.log.info("(TESTING) Would release pokemon: %s", pokemon)
                for pokemon in pokemonsToKeep:
                    self.log.info("(TESTING) Would keep pokemon: %s", pokemon)
            else:
                for pokemon in pokemonsToRelease:
                    self.do_release_pokemon(pokemon)

    def attempt_evolve(self, inventory_items=None):
        if not inventory_items:
            self.gsleep(0.2)
            inventory_items = self.get_inventory().call()\
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.get_caught_pokemons(inventory_items)
        self.inventory = Player_Inventory(self.percentages, inventory_items)
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
            self.gsleep(0.2)
            evo_res = self.evolve_pokemon(pokemon_id=pokemon.id).call().get('responses', {}).get('EVOLVE_POKEMON', {})
            status = evo_res.get('result', -1)
            # self.gsleep(3)
            if status == 1:
                evolved_pokemon = Pokemon(evo_res.get('evolved_pokemon_data', {}),
                                          self.player_stats.level, self.SCORE_METHOD, self.SCORE_SETTINGS)
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
        candy_have = self.inventory.pokemon_candy.get(self.POKEMON_EVOLUTION_FAMILY.get(pokemon.pokemon_id, None), -1)
        candy_needed = self.POKEMON_EVOLUTION.get(pokemon.pokemon_id, None)
        return candy_needed and candy_have > candy_needed and \
            pokemon.pokemon_id not in self.keep_pokemon_ids \
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
                          POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            self.gsleep(0.2)
            resp = self.disk_encounter(encounter_id=encounter_id, fort_id=fort_id, player_latitude=position[0],
                                       player_longitude=position[1]).call()\
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

    def encounter_pokemon(self, pokemon_data, retry=False, new_loc=None):  # take in a MapPokemon from MapCell.catchable_pokemons
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
            pokemon = Pokemon(pokemon_data)
            self.log.info("Trying initiate catching Pokemon: %s", pokemon)
            self.gsleep(0.2)
            encounter = self.encounter(encounter_id=encounter_id,
                                       spawn_point_id=spawn_point_id,
                                       player_latitude=position[0],
                                       player_longitude=position[1]).call()\
                .get('responses', {}).get('ENCOUNTER', {})
            self.log.debug("Attempting to Start Encounter: %s", encounter)
            result = encounter.get('status', -1)
            if result == 1 and 'wild_pokemon' in encounter and 'capture_probability' in encounter:
                pokemon = Pokemon(encounter.get('wild_pokemon', {}).get('pokemon_data', {}))
                capture_probability = create_capture_probability(encounter.get('capture_probability', {}))
                self.log.debug("Attempt Encounter Capture Probability: %s", json.dumps(encounter, indent=4, sort_keys=True))

                if new_loc:
                    # change loc for sniping
                    self.log.info("Teleporting to %f, %f before catching", new_loc[0], new_loc[1])
                    self.set_position(new_loc[0], new_loc[1], 0.0)
                    self.send_update_pos()
                    # self.gsleep(2)

                self.encountered_pokemons[encounter_id] = pokemon_data
                return self.do_catch_pokemon(encounter_id, spawn_point_id, capture_probability, pokemon)
            elif result == 7:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try", pokemon.pokemon_type)
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
        if not self.EGG_INCUBATION_ENABLED:
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
        self.gsleep(0.2)
        incubate_res = self.use_item_egg_incubator(item_id=incubator['id'], pokemon_id=egg['id']).call()\
            .get('responses', {}).get('USE_ITEM_EGG_INCUBATOR', {})
        status = incubate_res.get('result', -1)
        # self.gsleep(3)
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
        self.gsleep(0.2)
        hatch_res = self.get_hatched_eggs().call().get('responses', {}).get('GET_HATCHED_EGGS', {})
        status = hatch_res.get('success', -1)
        # self.gsleep(3)
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

    def cache_forts(self, forts):
        if not self.all_cached_forts:
            with open(self.cache_filename, 'wb') as handle:
                pickle.dump(forts, handle)

            with open(self.cache_filename, 'rb') as handle:
                self.all_cached_forts = pickle.load(handle)

            self.log.info("Cache was empty... Dumping in new forts and initializing all_cached_forts")

        else:
            for fort in forts:
                if not any(fort[0]['id'] == x[0]['id'] for x in self.all_cached_forts):
                    self.all_cached_forts.insert(0, fort)
                    self.log.info("Added new fort to cache")

            with open(self.cache_filename, 'wb') as handle:
                pickle.dump(self.all_cached_forts, handle)

        self.log.info("Cached forts %s: ", len(self.all_cached_forts))

    def setup_cache(self):
        try:
            self.log.debug("Opening cache file...")
            with open(self.cache_filename, 'rb') as handle:
                self.all_cached_forts = pickle.load(handle)

        except Exception as e:
            self.log.debug("Could not find or open cache, making new cache... %s", e)
            if not os.path.exists('./cache'):
                os.makedirs('./cache')
            try:
                os.remove(self.cache_filename)
            except OSError:
                pass
            with open(self.cache_filename, 'wb') as handle:
                pickle.dump(self.all_cached_forts, handle)

    def sort_cached_forts(self):
        if len(self.all_cached_forts) > 0:
            if not self.cache_is_sorted:
                self.log.info("Cache is unsorted, sorting now...")
                tempallcached = copy.deepcopy(self.all_cached_forts) # copy over original
                tempsorted = [copy.deepcopy(tempallcached[0])] # the final list to copy to cache
                tempelement = copy.deepcopy(tempallcached[0]) # cur element
                tempbool = True

                while (len(tempsorted) < len(self.all_cached_forts)): # sort all elements
                    templastelement = copy.deepcopy(tempsorted[-1])
                    tempelement = copy.deepcopy(tempsorted[0])
                    tempmaxfloat = sys.float_info.max # start with max float to find min distance

                    if(tempbool):
                        for fort in tempallcached:
                            if distance_in_meters((self._origPosF[0], self._origPosF[1]), (fort[0]['latitude'], fort[0]['longitude'])) <= tempmaxfloat:
                                tempelement = copy.deepcopy(fort)
                                tempmaxfloat = distance_in_meters((self._origPosF[0], self._origPosF[1]), (fort[0]['latitude'], fort[0]['longitude']))

                        tempsorted.pop(0)
                        tempsorted.append(tempelement)
                        tempallcached.remove(tempelement)
                        tempbool = False
                    else:
                        for fort in tempallcached:
                            if ((distance_in_meters((templastelement[0]['latitude'], templastelement[0]['longitude']),
                                                    (fort[0]['latitude'], fort[0]['longitude'])) <= tempmaxfloat) and (not any(fort[0]['id'] == x[0]['id'] for x in tempsorted))):
                                tempelement = copy.deepcopy(fort)
                                tempmaxfloat = distance_in_meters((templastelement[0]['latitude'], templastelement[0]['longitude']),
                                                                  (fort[0]['latitude'], fort[0]['longitude']))
                        tempallcached.remove(tempelement)
                        tempsorted.append(tempelement)

                self.spinnable_cached_forts = copy.deepcopy(tempsorted)
                self.cache_is_sorted = True

                with open(self.cache_filename, 'wb') as handle:
                    pickle.dump(self.spinnable_cached_forts, handle)

            if not self.spinnable_cached_forts:
                self.spinnable_cached_forts = copy.deepcopy(self.all_cached_forts)
            return self.spinnable_cached_forts
        else:
            self.log.info("Cache is empty! Switching mode to cache forts")
            return False

    def spin_all_cached_forts(self):
        destinations = self.sort_cached_forts()

        if not destinations:
            self.log.info('Turning on caching mode')
            self.walk_back_to_origin()
            self.use_cache = False
            self.cache_is_sorted = False
            return False

        for fort_data in destinations:
            fort = fort_data[0]
            self.log.info(
                "Walking to fort at  http://maps.google.com/maps?q=%s,%s",
                fort['latitude'], fort['longitude'])
            self.walk_to((fort['latitude'], fort['longitude']), directly=False)
            self.fort_search_pgoapi(fort, self.get_position(), distance_in_meters((fort['latitude'], fort['longitude']),
                                                                                  (self._posf[0], self._posf[1])))

        return True

    def main_loop(self):
        catch_attempt = 0
        self.heartbeat()
        if self.enable_caching and self.experimental:
            if not self.use_cache:
                self.log.info('==== CACHING MODE: CACHE FORTS ====')
            else:
                self.log.info('==== CACHING MODE: ROUTE+SPIN CACHED FORTS ====')
            self.setup_cache()
        while True:
            self.heartbeat()
            # self.gsleep(1)

            if self.use_cache and self.experimental and self.enable_caching:
                self.spin_all_cached_forts()
            else:
<<<<<<< 6fbcaf5465630f3d1464420da2721b7e92c9f36a
                if self.experimental and self.spin_all_forts:
                    self.spin_all_forts_visible()
                else:
                    self.spin_near_fort()
                if self.enable_caching and self.experimental and not self.use_cache:
                    self.cache_forts(forts=self.new_forts)
                # if catching fails 10 times, maybe you are sofbanned.
                # We can't actually use this as a basis for being softbanned. Pokemon Flee if you are softbanned (~stolencatkarma)
                while self.catch_near_pokemon() and catch_attempt <= self.max_catch_attempts:
                    # self.gsleep(4)
                    catch_attempt += 1
                    pass
=======
                self.spin_near_fort()
            # if catching fails 10 times, maybe you are sofbanned.
            # We can't actually use this as a basis for being softbanned. Pokemon Flee if you are softbanned (~stolencatkarma)
            while self.catch_near_pokemon() and catch_attempt <= self.max_catch_attempts:
                # self.gsleep(4)
                catch_attempt += 1
>>>>>>> ran autoflake and cleaned up errors
            if catch_attempt > self.max_catch_attempts:
                self.log.warn("You have reached the maximum amount of catch attempts. Giving up after %s times",
                              catch_attempt)
            catch_attempt = 0

            if self._error_counter >= self._error_threshold:
                raise RuntimeError('Too many errors in this run!!!')

    @staticmethod
    def flatmap(f, items):
        return list(chain.from_iterable(imap(f, items)))
