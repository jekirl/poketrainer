from __future__ import absolute_import
import json
from collections import defaultdict
from pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Inventory_Enum


class Inventory:
    def __init__(self, inventory_items):
        self.inventory_items = inventory_items
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
            if item_id == Inventory_Enum.ITEM_POTION:
                self.potion = item_count
            elif item_id == Inventory_Enum.ITEM_SUPER_POTION:
                self.super_potion = item_count
            elif item_id == Inventory_Enum.ITEM_MAX_POTION:
                self.max_potion = item_count
            elif item_id == Inventory_Enum.ITEM_HYPER_POTION:
                self.hyper_potion = item_count
            elif item_id == Inventory_Enum.ITEM_POKE_BALL:
                self.poke_balls = item_count
            elif item_id == Inventory_Enum.ITEM_GREAT_BALL:
                self.great_balls = item_count
            elif item_id == Inventory_Enum.ITEM_MASTER_BALL:
                self.master_balls = item_count
            elif item_id == Inventory_Enum.ITEM_ULTRA_BALL:
                self.ultra_balls = item_count
            elif item_id == Inventory_Enum.ITEM_LUCKY_EGG:
                self.lucky_eggs = item_count
            elif item_id == Inventory_Enum.ITEM_RAZZ_BERRY:
                self.razz_berries = item_count
            pokemon_family = inventory_item['inventory_item_data'].get('pokemon_family', {})
            self.pokemon_candy[pokemon_family.get('family_id', -1)] = pokemon_family.get('candy', -1)
            pokemon_data = inventory_item['inventory_item_data'].get('pokemon_data', {})
            if pokemon_data.get('is_egg', False) and not pokemon_data.get('egg_incubator_id', False):
                self.eggs_available.append(pokemon_data)
            egg_incubators = inventory_item['inventory_item_data'].get('egg_incubators', {}).get('egg_incubator', [])
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
        if self.master_balls:
            return Inventory_Enum.ITEM_MASTER_BALL
        elif self.ultra_balls:
            return Inventory_Enum.ITEM_ULTRA_BALL
        elif self.great_balls:
            return Inventory_Enum.ITEM_GREAT_BALL
        else:
            return Inventory_Enum.ITEM_POKE_BALL

    # FIXME make not bad, this should be configurable
    def take_next_ball(self, capture_probability):
        if self.can_attempt_catch():
            if capture_probability.get(Inventory_Enum.ITEM_POKE_BALL, 0) > 0.15 and self.poke_balls:
                self.take_pokeball()
                return Inventory_Enum.ITEM_POKE_BALL
            elif capture_probability.get(Inventory_Enum.ITEM_GREAT_BALL, 0) > 0.15 and self.great_balls:
                self.take_greatball()
                return Inventory_Enum.ITEM_GREAT_BALL
            elif capture_probability.get(Inventory_Enum.ITEM_ULTRA_BALL, 0) > 0.15 and self.ultra_balls:
                self.take_ultraball()
                return Inventory_Enum.ITEM_ULTRA_BALL
            elif capture_probability.get(Inventory_Enum.ITEM_MASTER_BALL, 0) > 0.15 and self.master_balls:
                self.take_masterball()
                return Inventory_Enum.ITEM_MASTER_BALL
            else:
                best_ball = self.best_ball()
                self.take_ball(self.best_ball())
                return best_ball
        else:
            return -1

    def take_ball(self, ball_id):
        if ball_id == Inventory_Enum.ITEM_POKE_BALL:
            self.poke_balls -= 1
        elif ball_id == Inventory_Enum.ITEM_GREAT_BALL:
            self.great_balls -= 1
        elif ball_id == Inventory_Enum.ITEM_ULTRA_BALL:
            self.ultra_balls -= 1
        elif ball_id == Inventory_Enum.ITEM_MASTER_BALL:
            self.master_balls -= 1

    def has_lucky_egg(self):
        for inventory_item in self.inventory_items:
            item = inventory_item['inventory_item_data'].get('item', {})
            item_id = item.get('item_id', -1)
            if item_id == Inventory_Enum.ITEM_LUCKY_EGG:
                return True
        return False

    def take_lucky_egg(self):
        self.lucky_eggs -= 1
        return Inventory_Enum.ITEM_LUCKY_EGG

    def has_berry(self):
        # Only Razz berries are in the game at the moment
        for inventory_item in self.inventory_items:
            item = inventory_item['inventory_item_data'].get('item', {})
            item_id = item.get('item_id', -1)
            if item_id == Inventory_Enum.ITEM_RAZZ_BERRY:
                return True
        return False

    def take_berry(self):
        self.razz_berries -= 1
        return Inventory_Enum.ITEM_RAZZ_BERRY

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
        return json.dumps(self, default=lambda o: o.__dict__)
