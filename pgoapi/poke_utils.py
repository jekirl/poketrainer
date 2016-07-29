from __future__ import absolute_import
import os
import json
from pgoapi.game_master import PokemonData, GAME_MASTER
from pgoapi.utilities import *
from pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Enum_Items
from math import floor, sqrt
from collections import defaultdict
import csv
import re

POKEMON_NAMES = json.load(open("pokemon.en.json"))
pokemon_lvls = {}
tcpm_vals = []
with open ("PoGoPokeLvl.tsv") as tsv: #data gathered from here: https://www.reddit.com/r/TheSilphRoad/comments/4sa4p5/stardust_costs_increase_every_4_power_ups/
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        pokemon_lvls[float(row["TotalCpMultiplier"])] = {
            "DustSoFar": int(row["Stardust to this level"]),
            "CandySoFar": int(row["Candies to this level"]),
            "PokemonLvl": int(row["Pokemon level"]),
            "PowerUpResult": float(row["Delta(TCpM^2)"]),
            "TCPMDif": float(row["TCPM Difference"])
        }
        tcpm_vals.append(float(row["TotalCpMultiplier"]))

def set_max_cp(pokemon, max_tcpm):
    poke_game_data = GAME_MASTER.get(pokemon.pokemon_id, PokemonData())
    if int(poke_game_data.PkMn) == 0 or not all_in(['cp', 'cp_multiplier'], pokemon.pokemon_data):
        return

    candy_to_evolve = int(poke_game_data.CandyToEvolve)

    pokemon.candy_needed_to_max_evolve = pokemon_lvls[max_tcpm]['CandySoFar'] - pokemon_lvls[pokemon.cpm_total]['CandySoFar'] + candy_to_evolve
    pokemon.dust_needed_to_max_evolve = pokemon_lvls[max_tcpm]['DustSoFar'] - pokemon_lvls[pokemon.cpm_total]['DustSoFar']

    i = 0
    if pokemon.pokemon_id == 133: #is an Eevee
        if pokemon.nickname is 'Sparky':
            i = 2
        elif pokemon.nickname is 'Pyro':
            i = 3
        else: #Rainer or Vaporean is the default
            i = 1
    else:
        while GAME_MASTER.get(pokemon.pokemon_id + i + 1, PokemonData()).FamilyId == poke_game_data.FamilyId and candy_to_evolve > 0:
            candy_to_evolve = int(GAME_MASTER.get(pokemon.pokemon_id + i + 1, PokemonData()).CandyToEvolve)
            pokemon.candy_needed_to_max_evolve += candy_to_evolve
            i+=1

    if(i == 0):
        pokemon.max_evolve_cp = calc_cp(pokemon.pokemon_data, max_tcpm, poke_game_data)
    else:
        evolved_poke_data = GAME_MASTER.get(pokemon.pokemon_id + i , PokemonData())
        pokemon.max_evolve_cp = calc_cp(pokemon.pokemon_data, max_tcpm, evolved_poke_data)

    pokeLvl = pokemon_lvls[pokemon.cpm_total]['PokemonLvl']
    pokemon.power_up_result = calc_cp(pokemon.pokemon_data, tcpm_vals[pokeLvl], poke_game_data) - pokemon.cp

#TCPM = CPM + ACPM
#Stamina =  (BaseStamina + IndividualStamina) * TCPM
#Attack = (BaseAttack + IndividualAttack) * TCPM
#Defense = (BaseDefense + IndividualDefense) * TCPM
#CP = MAX(10, FLOOR(Stamina0.5 * Attack * Def0.5 / 10))
def calc_acpm(pokemon, pokemon_details):
    if not all_in(['cp', 'cp_multiplier'], pokemon.pokemon_data):
        return 0    

    baseAttk = int(pokemon_details.BaseAttack)
    baseDef = int(pokemon_details.BaseDefense)
    baseStamina = int(pokemon_details.BaseStamina)
    cpm = pokemon.cp_multiplier
    return max(0, sqrt(sqrt( (100*pow(pokemon.cp, 2)) / ( pow((baseAttk + pokemon.individual_attack), 2) * (baseDef + pokemon.individual_defense) * (baseStamina + pokemon.individual_stamina)  ) )) - cpm)

def calc_cp(pokemon, tcpm, pokemon_details):
    baseAttk = int(pokemon_details.BaseAttack)
    baseDef = int(pokemon_details.BaseDefense)
    baseStamina = int(pokemon_details.BaseStamina)

    attk = (baseAttk + pokemon.get('individual_attack', 0)) * tcpm
    defense = (baseDef + pokemon.get('individual_defense', 0)) * tcpm
    stamina = (baseStamina + pokemon.get('individual_stamina', 0)) * tcpm

    return int(max(10, floor(sqrt(stamina) * attk * sqrt(defense) / 10)))

def get_tcpm(tcpm):
    return take_closest(tcpm, tcpm_vals)

def get_item_name(s_item_id):
    available_items = Enum_Items.ItemId.DESCRIPTOR.values_by_number.items()
    for (item_id, item) in available_items:
        if item_id == s_item_id:
            return item.name.replace('ITEM_', '', 1)
    return 'Unknown'


def pokemonIVPercentage(pokemon):
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
            return Pokemon(pokemon_data, POKEMON_NAMES)
    return None

DISK_ENCOUNTER = {0: "UNKNOWN",
                  1: "SUCCESS",
                  2: "NOT_AVAILABLE",
                  3: "NOT_IN_RANGE",
                  4: "ENCOUNTER_ALREADY_FINISHED"}
