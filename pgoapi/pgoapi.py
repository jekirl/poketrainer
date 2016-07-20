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

import logging
import re
import requests
from .utilities import f2i, h2f
from pgoapi.rpc_api import RpcApi
from pgoapi.auth_ptc import AuthPtc
from pgoapi.auth_google import AuthGoogle
from pgoapi.exceptions import AuthException, NotLoggedInException, ServerBusyOrOfflineException
from . import protos
from POGOProtos.Networking.Requests_pb2 import RequestType
import pickle
import random
import json
from pgoapi.location import *
import POGOProtos.Enums_pb2 as RpcEnum
from time import sleep
from collections import defaultdict
import os.path
CP_CUTOFF = 75 # release anything under this if we don't have it already
logger = logging.getLogger(__name__)

class PGoApi:

    API_ENTRY = 'https://pgorelease.nianticlabs.com/plfe/rpc'

    def __init__(self):

        self.log = logging.getLogger(__name__)

        self._auth_provider = None
        self._api_endpoint = None

        self._position_lat = 0 #int cooords
        self._position_lng = 0
        self._position_alt = 0
        self._posf = (0,0,0) # this is floats

        self._req_method_list = []

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

        self.log.info('Execution of RPC')
        response = None
        try:
            response = request.request(api_endpoint, self._req_method_list, player_position)
        except ServerBusyOrOfflineException as e:
            self.log.info('Server seems to be busy or offline - try again!')

        # cleanup after call execution
        self.log.info('Cleanup of request!')
        self._req_method_list = []

        return response

    def list_curr_methods(self):
        for i in self._req_method_list:
            print("{} ({})".format(RequestType.Name(i),i))
    def set_logger(self, logger):
        self._ = logger or logging.getLogger(__name__)

    def get_position(self):
        return (self._position_lat, self._position_lng, self._position_alt)
    def set_position(self, lat, lng, alt):
        self.log.debug('Set Position - Lat: %s Long: %s Alt: %s', lat, lng, alt)
        self._posf = (lat,lng,alt)
        self._position_lat = f2i(lat)
        self._position_lng = f2i(lng)
        self._position_alt = f2i(alt)

    def __getattr__(self, func):
        def function(**kwargs):

            if not self._req_method_list:
                self.log.info('Create new request...')

            name = func.upper()
            if kwargs:
                self._req_method_list.append( { RequestType.Value(name): kwargs } )
                self.log.info("Adding '%s' to RPC request including arguments", name)
                self.log.debug("Arguments of '%s': \n\r%s", name, kwargs)
            else:
                self._req_method_list.append( RequestType.Value(name) )
                self.log.info("Adding '%s' to RPC request", name)

            return self

        if func.upper() in RequestType.keys():
            return function
        else:
            raise AttributeError
    def heartbeat(self):
        # making a standard call, like it is also done by the client
        self.get_player()
        self.get_hatched_eggs()
        self.get_inventory()
        self.check_awarded_badges()
        # self.download_settings(hash="4a2e9bc330dae60e7b74fc85b98868ab4700802e")
        res = self.call()
        print('Response dictionary: \n\r{}'.format(json.dumps(res, indent=2)))
        if 'GET_INVENTORY' in res['responses']:
            print(self.cleanup_inventory(res['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']))
        return res
    def walk_to(self,loc): #location in floats of course...
        steps = get_route(self._posf, loc)
        for step in steps:
            for i,next_point in enumerate(get_increments(self._posf,step)):
                self.set_position(*next_point)
                self.heartbeat()
                self.log.info("sleeping before next heartbeat")
                sleep(1)
                while self.catch_near_pokemon():
                    sleep(0.25)

    def spin_near_fort(self):
        map_cells = self.nearby_map_objects()['responses']['GET_MAP_OBJECTS']['map_cells']
        forts = sum([cell.get('forts',[]) for cell in map_cells],[]) #supper ghetto lol
        destinations = filtered_forts(self._posf,forts)
        if destinations:
            fort = destinations[0]
            self.log.info("Walking to fort: %s", fort)
            self.walk_to((fort['latitude'], fort['longitude']))
            position = self._posf # FIXME ?
            res = self.fort_search(fort_id = fort['id'], fort_latitude=fort['latitude'],fort_longitude=fort['longitude'],player_latitude=position[0],player_longitude=position[1]).call()['responses']['FORT_SEARCH']
            self.log.info("Fort spinned: %s", res)
            return True
        else:
            self.log.error("No fort to walk to!")
            return False

    def catch_near_pokemon(self):
        map_cells = self.nearby_map_objects()['responses']['GET_MAP_OBJECTS']['map_cells']
        pokemons = sum([cell.get('catchable_pokemons',[]) for cell in map_cells],[]) #supper ghetto lol

        # catch first pokemon:
        origin = (self._posf[0],self._posf[1])
        pokemon_distances = [(pokemon, distance_in_meters(origin,(pokemon['latitude'], pokemon['longitude']))) for pokemon in pokemons]
        self.log.info("Nearby pokemon: : %s", pokemon_distances)
        if pokemons:
            target = pokemon_distances[0]
            self.log.info("Catching pokemon: : %s, distance: %f meters", target[0], target[1])
            return self.encounter_pokemon(target[0])
        return False

    def nearby_map_objects(self):
        position = self.get_position()
        neighbors = getNeighbors(self._posf)
        return self.get_map_objects(latitude=position[0], longitude=position[1], since_timestamp_ms=[0]*len(neighbors), cell_id=neighbors).call()
    def attempt_catch(self,encounter_id,spawn_point_id):
        return self.catch_pokemon(
            normalized_reticle_size= 1.950,
            pokeball = 1,
            spin_modifier= 0.850,
            hit_pokemon=True,
            NormalizedHitPosition=1,
            encounter_id=encounter_id,
            spawn_point_guid=spawn_point_id,
            ).call()['responses']['CATCH_POKEMON']

    def cleanup_inventory(self, inventroy_items=None):
        if not inventroy_items:
            inventroy_items = self.get_inventory().call()['GET_INVENTORY']['inventory_delta']['inventory_items']
        caught_pokemon = defaultdict(list)
        for inventory_item in inventroy_items:
            if "pokemon" in  inventory_item['inventory_item_data']:
                # is a pokemon:
                pokemon = inventory_item['inventory_item_data']['pokemon']
                caught_pokemon["pokemon_id"].append(pokemon)
        for pokemons in caught_pokemon.values():
            if len(pokemons) > 1:
                #release crappy ones:
                for pokemon in pokemons:
                    if 'cp' in pokemon and pokemon['cp'] < CP_CUTOFF:
                        self.release_pokemon(pokemon_id = pokemon["id"])

        return self.call()




    def encounter_pokemon(self,pokemon): #take in a MapPokemon from MapCell.catchable_pokemons
        encounter_id = pokemon['encounter_id']
        spawn_point_id = pokemon['spawnpoint_id']
        # begin encounter_id
        position = self._posf # FIXME ?
        resp = self.encounter(encounter_id=encounter_id,spawnpoint_id=spawn_point_id,player_latitude=position[0],player_longitude=position[1]).call()['responses']['ENCOUNTER']
        self.log.info("Started Encounter: %s", resp)
        if resp['status'] == 1:
            capture_status = -1
            # while capture_status != RpcEnum.CATCH_ERROR and capture_status != RpcEnum.CATCH_FLEE:
            while capture_status != 0 and capture_status != 3:
                capture_status = self.attempt_catch(encounter_id,spawn_point_id)
                print(capture_status)
                status = capture_status['status']
                # if status == RpcEnum.CATCH_SUCCESS:
                if status == 1:
                    self.log.info("Caught Pokemon: : %s", catch_attempt)
                    sleep(2)
                    return catch_attempt
                elif status != 2:
                    self.log.info("Failed Catch: : %s", catch_attempt)
                    return False
                sleep(2)
        return False



    def login(self, provider, username, password,cached=False):
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
            f = open(fname,"w")
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
        self.heartbeat() # always heartbeat to start...
        while True:

            try:
                self.heartbeat()
                sleep(1)
                self.spin_near_fort()
                while self.catch_near_pokemon():
                    sleep(4)
                    pass
            except Exception as e:
                self.log.error("Error in main loop: %s", e)
                sleep(60)
                pass
