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

import json
import logging
from collections import defaultdict
from itertools import chain
from time import time

import eventlet
import gevent
import six
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

if six.PY3:
    from builtins import map as imap
elif six.PY2:
    from itertools import imap

logger = logging.getLogger(__name__)


class Poketrainer:
    def __init__(self, wrapper):

        self.log = logging.getLogger(__name__)

        # objects
        self.wrapper = wrapper
        self.config = wrapper.config

        self.api = wrapper.api

        # timers, counters and triggers
        self._heartbeat_number = 5
        self._farm_mode_triggered = False
        self.wrapper.start_time = time()
        self.wrapper.exp_start = None

        # Sanity checking
        self.farm_items_enabled = self.config.farm_items_enabled and self.config.experimental and self.wrapper.should_catch_pokemon  # Experimental, and we needn't do this if we're farming anyway
        if (
                                self.farm_items_enabled and
                                self.config.farm_ignore_pokeball_count and
                            self.config.farm_ignore_greatball_count and
                        self.config.farm_ignore_ultraball_count and
                    self.config.farm_ignore_masterball_count
        ):
            self.farm_items_enabled = False
            self.log.warn("FARM_ITEMS has been disabled due to all Pokeball counts being ignored.")
        elif self.farm_items_enabled and not (
                    self.config.pokeball_farm_threshold < self.config.pokeball_continue_threshold):
            self.farm_items_enabled = False
            self.log.warn(
                "FARM_ITEMS has been disabled due to farming threshold being below the continue. Set 'CATCH_POKEMON' to 'false' to enable captureless traveling.")

    def sleep(self, t):
        self.wrapper.sleep(t)

    def heartbeat(self):
        # making a standard call to update position, etc
        req = self.api.create_request()
        req.get_player()
        if self._heartbeat_number % 10 == 0:
            req.check_awarded_badges()
            req.get_inventory()
        res = req.call()
        if not res or res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Restarting!!!", res)
            raise AuthException("Token probably expired?")

        self.wrapper.parse_heartbeat_response(res)

        responses = res.get('responses', {})

        if 'GET_INVENTORY' in res.get('responses', {}):
            self.log.debug(self.wrapper.cleanup_inventory(self.wrapper.inventory.inventory_items))
            self.log.info("Player Inventory after cleanup: %s", self.wrapper.inventory)

            # maintenance
            self.wrapper.incubate_eggs()
            self.wrapper.use_lucky_egg()
            self.wrapper.attempt_evolve(self.wrapper.inventory.inventory_items)
            self.wrapper.cleanup_pokemon(self.wrapper.inventory.inventory_items)

            # Farm precon
            if self.farm_items_enabled:
                pokeball_count = 0
                if not self.config.farm_ignore_pokeball_count:
                    pokeball_count += self.wrapper.inventory.poke_balls
                if not self.config.farm_ignore_greatball_count:
                    pokeball_count += self.wrapper.inventory.great_balls
                if not self.config.farm_ignore_ultraball_count:
                    pokeball_count += self.wrapper.inventory.ultra_balls
                if not self.config.farm_ignore_masterball_count:
                    pokeball_count += self.wrapper.inventory.master_balls
                if self.config.pokeball_farm_threshold > pokeball_count and not self._farm_mode_triggered:
                    self.wrapper.should_catch_pokemon = False
                    self._farm_mode_triggered = True
                    self.log.info("Player only has %s Pokeballs, farming for more...", pokeball_count)
                    if self.config.farm_override_step_size != -1:
                        self.wrapper.step_size = self.config.farm_override_step_size
                        self.log.info("Player has changed speed to %s", self.wrapper.step_size)
                elif self.config.pokeball_continue_threshold <= pokeball_count and self._farm_mode_triggered:
                    self.wrapper.should_catch_pokemon = self.config.should_catch_pokemon  # Restore catch pokemon setting from config file
                    self._farm_mode_triggered = False
                    self.log.info("Player has %s Pokeballs, continuing to catch more!", pokeball_count)
                    if self.config.farm_override_step_size != -1:
                        self.wrapper.step_size = self.config.step_size
                        self.log.info("Player has returned to normal speed of %s", self.wrapper.step_size)
        self._heartbeat_number += 1
        return res

    def main_loop(self):
        while True:
            self.heartbeat()
            # self.sleep(1)

            self.wrapper.catcher.catch_all()
            self.wrapper.fort_walker.loop()
            self.wrapper.fort_walker.spin_nearest_fort()
            self.sleep(1.0)

