from __future__ import absolute_import
import os
from pgoapi.pokemon import Pokemon
from pgoapi.game_master import PokemonData
from pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Enum_Items
import csv


def get_item_name(s_item_id):
    available_items = Enum_Items.ItemId.DESCRIPTOR.values_by_number.items()
    for (item_id, item) in available_items:
        if item_id == s_item_id:
            return item.name.replace('ITEM_', '', 1)
    return 'Unknown'

def parse_game_master():
    line_count = 0
    game_master = {}
    with open("GAME_MASTER_POKEMON_v0_2.tsv") as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter="\t")
        attributes = []
        for line in tsvreader:
            if line_count == 0:
                attributes = line
                line_count += 1
                continue
            pokemon_data = PokemonData()
            for x in range(0, len(line)):
                setattr(pokemon_data, attributes[x], line[x])
            game_master[int(line[0])] = pokemon_data
    return game_master


def pokemonIVPercentage(pokemon):
    return ((pokemon.get('individual_attack', 0) + pokemon.get('individual_stamina', 0) + pokemon.get(
        'individual_defense', 0) + 0.0) / 45.0) * 100.0


def pokemonDataList(pokemon):
    #Family ID, Pokemon #, Pokemon Name, Is Fave,CP Level, iATK, iDEF, iSTA, IV%, HP
    data_pokemon_str = str(pokemon.pokemon_additional_data.FamilyId[21:][:4]) + "," #Family ID
    data_pokemon_str += str(pokemon.pokemon_id) + ',' #Pokemon Number
    data_pokemon_str += str(pokemon.pokemon_type) + ',' #Pokemon Name
    data_pokemon_str += str(pokemon.is_favorite) + ',' #Is Favorite
    data_pokemon_str += str(pokemon.cp) + ',' #CP Level
    data_pokemon_str += str(pokemon.individual_attack) + ',' #ATK
    data_pokemon_str += str(pokemon.individual_defense) + ',' #DEF
    data_pokemon_str += str(pokemon.individual_stamina) + ',' #STA
    data_pokemon_str += str(pokemon.iv) + ',' #IV
    data_pokemon_str += str(pokemon.stamina) #HP
    data_pokemon_str += '\n'

    return data_pokemon_str


def get_inventory_data(res, poke_names):
    inventory_delta = res['responses']['GET_INVENTORY'].get('inventory_delta', {})
    inventory_items = inventory_delta.get('inventory_items', [])
    pokemons = sorted(map(lambda x: Pokemon(x['pokemon_data'], poke_names),
                          filter(lambda x: 'pokemon_data' in x,
                          map(lambda x: x.get('inventory_item_data', {}), inventory_items))), key=lambda x: x.cp, reverse=True)
    inventory_items_pokemon_list = filter(lambda x: not x.is_egg, pokemons)
    return os.linesep.join(map(str, inventory_items_pokemon_list))


def create_capture_probability(capture_probability):
    capture_balls = capture_probability.get('pokeball_type', [])
    capture_rate = capture_probability.get('capture_probability', [])
    if not capture_probability or not capture_rate or len(capture_balls) != len(capture_rate):
        return None
    else:
        return dict(zip(capture_balls, capture_rate))


def get_pokemon_by_long_id(pokemon_id, res, poke_names):
    for inventory_item in res:
        pokemon_data = inventory_item['inventory_item_data'].get('pokemon_data', {})
        if not pokemon_data.get('is_egg', False) and pokemon_data.get('id', 'NA') == pokemon_id:
            return Pokemon(pokemon_data, poke_names)
    return None

DISK_ENCOUNTER = {0: "UNKNOWN",
                  1: "SUCCESS",
                  2: "NOT_AVAILABLE",
                  3: "NOT_IN_RANGE",
                  4: "ENCOUNTER_ALREADY_FINISHED"}


def get_inventory_candy(res, poke_names):
    inventory_delta = res['responses']['GET_INVENTORY'].get('inventory_delta', {})
    inventory_items = inventory_delta.get('inventory_items', [])
    inventory_items_dict_list = map(lambda x: x.get('inventory_item_data', {}), inventory_items)
    inventory_items_family_list = filter(lambda x: 'pokemon_family' in x, inventory_items_dict_list)

    return (os.linesep.join(map(lambda x: "{0},{1},{2}".format(
        x['pokemon_family']['family_id'],
        poke_names[str(x['pokemon_family']['family_id'])].encode('ascii', 'ignore'),
        x['pokemon_family']['candy']), inventory_items_family_list)))

def write_data_files(data_items, data_player, data_pokemon, data_candies):
    #self.log.info("[Data]\t\t- Writing Data Files...")
    file = open("exports/items.csv", "w")
    file.write(data_items)
    file.close()

    file = open("exports/player.csv", "w")
    file.write(data_player)
    file.close()

    file = open("exports/pkmn.csv", "w")
    file.write("Family,Pokedex,Name,Favorite,CP,ATK,DEF,STA,IV,HP\n")
    file.write(data_pokemon)
    file.close()

    file = open("exports/candy.csv", "w")
    file.write("Family,Pokemon,Candy\n")
    file.write(data_candies)
    file.close()
