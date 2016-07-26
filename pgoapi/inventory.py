from __future__ import absolute_import

from collections import defaultdict

from pgoapi.protos.POGOProtos import Inventory_pb2 as Inventory_Enum


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
        self.pokemon_candy = defaultdict()
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
            pokemon_family = inventory_item['inventory_item_data'].get('pokemon_family', {})
            self.pokemon_candy[pokemon_family.get('family_id', -1)] = pokemon_family.get('candy', -1)


    def can_attempt_catch(self):
        return self.poke_balls + self.great_balls + self.ultra_balls + self.master_balls > 0

    def take_pokeball(self):
        self.poke_balls -= 1

    def take_greatball(self):
        self.poke_balls -= 1

    def take_masterball(self):
        self.master_balls -= 1

    def take_ultraball(self):
        self.ultra_balls -= 1

    def take_next_ball(self):
        if self.poke_balls > 0:
            self.take_pokeball()
            return Inventory_Enum.ITEM_POKE_BALL
        elif self.great_balls > 0:
            self.take_greatball()
            return Inventory_Enum.ITEM_GREAT_BALL
        elif self.ultra_balls > 0:
            self.take_ultraball()
            return Inventory_Enum.ITEM_ULTRA_BALL
        elif self.master_balls > 0:
            self.take_masterball()
            return Inventory_Enum.ITEM_MASTER_BALL
        else:
            return -1

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

    def take_ball(self, ball_id):
        if ball_id == Inventory_Enum.ITEM_POKE_BALL:
            self.poke_balls -= 1
        elif ball_id == Inventory_Enum.ITEM_GREAT_BALL:
            self.great_balls -= 1
        elif ball_id == Inventory_Enum.ITEM_ULTRA_BALL:
            self.ultra_balls -= 1
        elif ball_id == Inventory_Enum.ITEM_MASTER_BALL:
            self.master_balls -= 1

    def __str__(self):
        return "PokeBalls: {0}, GreatBalls: {1}, MasterBalls: {2}, UltraBalls: {3} \n " \
               "Potion: {4}, Super Potion: {5}, Max Potion {6}, Hyper Potion {7}, Lucky Eggs {8}".format(self.poke_balls,
                                                                                        self.great_balls,
                                                                                        self.master_balls,
                                                                                        self.ultra_balls,
                                                                                        self.potion,
                                                                                        self.super_potion,
                                                                                        self.max_potion,
                                                                                        self.hyper_potion,
                                                                                        self.lucky_eggs)

    def __repr__(self):
        return self.__str__()
