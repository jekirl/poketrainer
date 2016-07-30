from __future__ import absolute_import

import os

from pgoapi.pokemon import Pokemon
from pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Enum_Items


def get_item_name(s_item_id):
    available_items = Enum_Items.ItemId.DESCRIPTOR.values_by_number.items()
    for (item_id, item) in available_items:
        if item_id == s_item_id:
            return item.name.replace('ITEM_', '', 1)
    return 'Unknown'


def pokemon_iv_percentage(pokemon):
    return ((pokemon.get('individual_attack', 0) + pokemon.get('individual_stamina', 0) + pokemon.get(
        'individual_defense', 0) + 0.0) / 45.0) * 100.0


def get_inventory_data(res, player_level, score_method="CP", score_settings=dict()):
    inventory_delta = res['responses']['GET_INVENTORY'].get('inventory_delta', {})
    inventory_items = inventory_delta.get('inventory_items', [])
    pokemons = sorted(map(lambda x: Pokemon(x['pokemon_data'], player_level, score_method, score_settings),
                          filter(lambda x: 'pokemon_data' in x and not x['pokemon_data'].get("is_egg", False),
                          map(lambda x: x.get('inventory_item_data', {}), inventory_items))),
                      key=lambda x: x.score, reverse=True)
    inventory_items_pokemon_list = filter(lambda x: not x.is_egg, pokemons)
    return os.linesep.join(map(str, inventory_items_pokemon_list))


def create_capture_probability(capture_probability):
    capture_balls = capture_probability.get('pokeball_type', [])
    capture_rate = capture_probability.get('capture_probability', [])
    if not capture_probability or not capture_rate or len(capture_balls) != len(capture_rate):
        return None
    else:
        return dict(zip(capture_balls, capture_rate))


def get_pokemon_by_long_id(pokemon_id, res):
    for inventory_item in res:
        pokemon_data = inventory_item['inventory_item_data'].get('pokemon_data', {})
        if not pokemon_data.get('is_egg', False) and pokemon_data.get('id', 'NA') == pokemon_id:
            return Pokemon(pokemon_data)
    return None

DISK_ENCOUNTER = {0: "UNKNOWN",
                  1: "SUCCESS",
                  2: "NOT_AVAILABLE",
                  3: "NOT_IN_RANGE",
                  4: "ENCOUNTER_ALREADY_FINISHED"}
