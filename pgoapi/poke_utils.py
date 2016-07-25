from __future__ import absolute_import
import os
from pgoapi.pokemon import Pokemon


def pokemonIVPercentage(pokemon):
    return ((pokemon.get('individual_attack', 0) + pokemon.get('individual_stamina', 0) + pokemon.get(
        'individual_defense', 0) + 0.0) / 45.0) * 100.0


def get_inventory_data(res, poke_names):
    inventory_delta = res['responses']['GET_INVENTORY'].get('inventory_delta', {})
    inventory_items = inventory_delta.get('inventory_items', [])
    pokemons = map(lambda x: Pokemon(x['pokemon_data'], poke_names),
                   filter(lambda x: 'pokemon_data' in x,
                          map(lambda x: x.get('inventory_item_data', {}), inventory_items)))
    inventory_items_pokemon_list = filter(lambda x: not x.is_egg, pokemons)

    return os.linesep.join(map(str, inventory_items_pokemon_list))


DISK_ENCOUNTER = {0: "UNKNOWN",
                  1: "SUCCESS",
                  2: "NOT_AVAILABLE",
                  3: "NOT_IN_RANGE",
                  4: "ENCOUNTER_ALREADY_FINISHED"}
