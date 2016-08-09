from __future__ import absolute_import

import json
from collections import defaultdict
from time import time

from helper.colorlogger import create_logger
from library.api.pgoapi.protos.POGOProtos.Inventory import \
    Item_pb2 as Item_Enums

from .poke_utils import get_item_name
from .pokemon import Pokemon


class Inventory:
    def __init__(self, parent, inventory_items):
        self._parent = parent
        self.inventory_items = inventory_items
        self._log = create_logger(__name__, 'purple')
        self._last_egg_use_time = 0

        self.ultra_balls = 0
        self.great_balls = 0
        self.poke_balls = 0
        self.master_balls = 0
        self.potion = 0
        self.hyper_potion = 0
        self.super_potion = 0
        self.max_potion = 0
        self.lucky_eggs = 0
        self.razz_berries = 0
        self.pokeball_percent = self._parent.config.ball_priorities[0] / 100.0
        self.greatball_percent = self._parent.config.ball_priorities[1] / 100.0
        self.ultraball_percent = self._parent.config.ball_priorities[2] / 100.0
        self.use_masterball = self._parent.config.ball_priorities[3]

        self.pokemon_candy = defaultdict()
        self.eggs_available = []
        self.incubators_available = []
        self.incubators_busy = []
        self.setup_inventory()

    def setup_inventory(self):
        for inventory_item in self.inventory_items:
            item = inventory_item['inventory_item_data'].get('item', {})
            item_id = item.get('item_id', -1)
            item_count = item.get('count', 0)
            if item_id == Item_Enums.ITEM_POTION:
                self.potion = item_count
            elif item_id == Item_Enums.ITEM_SUPER_POTION:
                self.super_potion = item_count
            elif item_id == Item_Enums.ITEM_MAX_POTION:
                self.max_potion = item_count
            elif item_id == Item_Enums.ITEM_HYPER_POTION:
                self.hyper_potion = item_count
            elif item_id == Item_Enums.ITEM_POKE_BALL:
                self.poke_balls = item_count
            elif item_id == Item_Enums.ITEM_GREAT_BALL:
                self.great_balls = item_count
            elif item_id == Item_Enums.ITEM_MASTER_BALL:
                self.master_balls = item_count
            elif item_id == Item_Enums.ITEM_ULTRA_BALL:
                self.ultra_balls = item_count
            elif item_id == Item_Enums.ITEM_LUCKY_EGG:
                self.lucky_eggs = item_count
            elif item_id == Item_Enums.ITEM_RAZZ_BERRY:
                self.razz_berries = item_count
            candy = inventory_item['inventory_item_data'].get('candy', {})
            self.pokemon_candy[candy.get('family_id', -1)] = candy.get('candy', -1)
            self.eggs_available = []
            pokemon_data = inventory_item['inventory_item_data'].get('pokemon_data', {})
            if pokemon_data.get('is_egg', False) and not pokemon_data.get('egg_incubator_id', False):
                self.eggs_available.append(pokemon_data)
            egg_incubators = inventory_item['inventory_item_data'].get('egg_incubators', {}).get('egg_incubator', [])
            self.incubators_available = []
            self.incubators_busy = []
            for incubator in egg_incubators:
                if "pokemon_id" in incubator:
                    self.incubators_busy.append(incubator)
                else:
                    self.incubators_available.append(incubator)

    def can_attempt_catch(self):
        return self.poke_balls + self.great_balls + self.ultra_balls + self.master_balls > 0

    def take_pokeball(self):
        self.poke_balls -= 1

    def take_greatball(self):
        self.great_balls -= 1

    def take_masterball(self):
        self.master_balls -= 1

    def take_ultraball(self):
        self.ultra_balls -= 1

    def best_ball(self):
        if self.use_masterball and self.master_balls:
            return Item_Enums.ITEM_MASTER_BALL
        elif self.ultra_balls:
            return Item_Enums.ITEM_ULTRA_BALL
        elif self.great_balls:
            return Item_Enums.ITEM_GREAT_BALL
        else:
            return Item_Enums.ITEM_POKE_BALL

    def take_next_ball(self, capture_probability):
        if self.can_attempt_catch():
            if capture_probability.get(Item_Enums.ITEM_POKE_BALL, 0) > self.pokeball_percent and self.poke_balls:
                self.take_pokeball()
                return Item_Enums.ITEM_POKE_BALL
            elif capture_probability.get(Item_Enums.ITEM_GREAT_BALL, 0) > self.greatball_percent and self.great_balls:
                self.take_greatball()
                return Item_Enums.ITEM_GREAT_BALL
            elif capture_probability.get(Item_Enums.ITEM_ULTRA_BALL, 0) > self.ultraball_percent and self.ultra_balls:
                self.take_ultraball()
                return Item_Enums.ITEM_ULTRA_BALL
            else:
                best_ball = self.best_ball()
                self.take_ball(self.best_ball())
                return best_ball
        else:
            return -1

    def take_ball(self, ball_id):
        if ball_id == Item_Enums.ITEM_POKE_BALL:
            self.poke_balls -= 1
        elif ball_id == Item_Enums.ITEM_GREAT_BALL:
            self.great_balls -= 1
        elif ball_id == Item_Enums.ITEM_ULTRA_BALL:
            self.ultra_balls -= 1
        elif ball_id == Item_Enums.ITEM_MASTER_BALL:
            self.master_balls -= 1

    def has_lucky_egg(self):
        for inventory_item in self.inventory_items:
            item = inventory_item['inventory_item_data'].get('item', {})
            item_id = item.get('item_id', -1)
            if item_id == Item_Enums.ITEM_LUCKY_EGG:
                return True
        return False

    def take_lucky_egg(self):
        self.lucky_eggs -= 1
        return Item_Enums.ITEM_LUCKY_EGG

    def has_berry(self):
        # Only Razz berries are in the game at the moment
        for inventory_item in self.inventory_items:
            item = inventory_item['inventory_item_data'].get('item', {})
            item_id = item.get('item_id', -1)
            if item_id == Item_Enums.ITEM_RAZZ_BERRY:
                return True
        return False

    def take_berry(self):
        self.razz_berries -= 1
        return Item_Enums.ITEM_RAZZ_BERRY

    def cleanup_inventory(self):
        item_count = 0
        for inventory_item in self.inventory_items:
            if "item" in inventory_item['inventory_item_data']:
                item = inventory_item['inventory_item_data']['item']
                if (
                        item['item_id'] in self._parent.config.min_items and
                        "count" in item and
                        item['count'] > self._parent.config.min_items[item['item_id']]
                ):
                    recycle_count = item['count'] - self._parent.config.min_items[item['item_id']]
                    item_count += item['count'] - recycle_count
                    self._log.info("Recycling {0} {1}(s)".format(recycle_count, get_item_name(item['item_id'])))
                    self._parent.sleep(0.2 + self._parent.config.extra_wait)
                    res = self._parent.api.recycle_inventory_item(item_id=item['item_id'], count=recycle_count) \
                        .get('responses', {}).get('RECYCLE_INVENTORY_ITEM', {})
                    response_code = res.get('result', -1)
                    if response_code == 1:
                        self._log.info("{0}(s) recycled successfully. New count: {1}".format(get_item_name(
                            item['item_id']), res.get('new_count', 0)))
                    else:
                        self._log.info("Failed to recycle {0}, Code: {1}".format(get_item_name(item['item_id']),
                                                                                 response_code))
                elif "count" in item:
                    item_count += item['count']
        if item_count > 0:
            self._log.info("Inventory has {0}/{1} items".format(item_count, self._parent.player.max_item_storage))
        return self.update_player_inventory()

    def get_caught_pokemon(self, as_json=False):
        pokemon_list = sorted(map(lambda x: Pokemon(x['pokemon_data'], self._parent.player_stats.level,
                                                    self._parent.config.score_method,
                                                    self._parent.config.score_settings),
                                  filter(lambda x: 'pokemon_data' in x and not x['pokemon_data'].get("is_egg", False),
                                         map(lambda x: x.get('inventory_item_data', {}), self.inventory_items))),
                              key=lambda x: x.score, reverse=True)
        pokemon_list = filter(lambda x: not x.is_egg, pokemon_list)
        if as_json:
            return json.dumps(pokemon_list, default=lambda p: p.__dict__)  # reduce the data sent?
        return pokemon_list

    def get_caught_pokemon_by_family(self, as_json=False):
        pokemon_list = defaultdict(list)
        for pokemon in self.get_caught_pokemon():
            pokemon_list[pokemon.pokemon_id].append(pokemon)
        if as_json:
            return json.dumps(pokemon_list, default=lambda p: p.__dict__)  # reduce the data sent?
        return pokemon_list

    def update_player_inventory(self):
        res = self._parent.api.get_inventory()
        if 'GET_INVENTORY' in res.get('responses', {}):
            self.inventory_items = res.get('responses', {}) \
                .get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
            self.setup_inventory()
        return res

    def use_lucky_egg(self):
        if self._parent.config.use_lucky_egg and \
                self.has_lucky_egg() and time() - self._last_egg_use_time > 30 * 60:
            response = self._parent.api.use_item_xp_boost(item_id=Item_Enums.ITEM_LUCKY_EGG)
            result = response.get('responses', {}).get('USE_ITEM_XP_BOOST', {}).get('result', -1)
            if result == 1:
                self._log.info("Ate a lucky egg! Yummy! :)")
                self.take_lucky_egg()
                self._last_egg_use_time = time()
                return True
            elif result == 3:
                self._log.info("Lucky egg already active")
                return False
            else:
                self._log.info("Lucky Egg couldn't be used, status code %s", result)
                return False
        else:
            return False

    def __str__(self):
        str_ = "PokeBalls: {0}, GreatBalls: {1}, MasterBalls: {2}, UltraBalls: {3} \n " \
               "Potion: {4}, Super Potion: {5}, Max Potion {6}, Hyper Potion {7}, Lucky Eggs {8}, Razz Berries {9}"
        return str_.format(self.poke_balls,
                           self.great_balls,
                           self.master_balls,
                           self.ultra_balls,
                           self.potion,
                           self.super_potion,
                           self.max_potion,
                           self.hyper_potion,
                           self.lucky_eggs,
                           self.razz_berries)

    def __repr__(self):
        return self.__str__()

    def to_json(self):
        return json.dumps(
            dict((att, val) for att, val in self.__dict__.iteritems() if not att.startswith('_')),
            default=lambda o: o.__dict__
        )
