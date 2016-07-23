import os

def pokemonIVPercentage(pokemon):
    return ((pokemon.get('individual_attack', 0) + pokemon.get('individual_stamina', 0) + pokemon.get(
        'individual_defense', 0) + 0.0) / 45.0) * 100.0


def get_inventory_data(res, poke_names):
    inventory_delta = res['responses']['GET_INVENTORY'].get('inventory_delta', {})
    inventory_items = inventory_delta.get('inventory_items', [])
    inventory_items_dict_list = map(lambda x: x.get('inventory_item_data', {}), inventory_items)
    inventory_items_pokemon_list = filter(lambda x: 'pokemon_data' in x and 'is_egg' not in x['pokemon_data'],
                                          inventory_items_dict_list)

    return (os.linesep.join(map(lambda x: "{0}, CP {1}, IV {2:.2f}".format(
        poke_names[str(x['pokemon_data']['pokemon_id'])].encode('ascii', 'ignore'),
        x['pokemon_data']['cp'],
        pokemonIVPercentage(x['pokemon_data'])), inventory_items_pokemon_list)))
