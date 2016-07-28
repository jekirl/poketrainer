# DISCLAIMER: This is jank
from flask import Flask, render_template
import json
import csv
import argparse
from math import floor
from collections import defaultdict
import re
from pgoapi.poke_utils import *
app = Flask(__name__, template_folder="templates")

pokemon_names = json.load(open("pokemon.en.json"))
pokemon_details = {}
with open ("GAME_MASTER_POKEMON_v0_2.tsv") as tsv:
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        family_id = re.match("HoloPokemonFamilyId.V([0-9]*).*",row["FamilyId"]).group(1)
        pokemon_details[row["PkMn"]] = {
            "BaseStamina": float(row["BaseStamina"]),
            "BaseAttack": float(row["BaseAttack"]),
            "BaseDefense": float(row["BaseDefense"]),
            "family_id": family_id
        }

attacks = {}
with open ("GAME_ATTACKS_v0_1.tsv") as tsv:
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        attacks[int(row["Num"])] = row["Move"]

@app.route("/<username>/pokemon")
def inventory(username):
    with open("data_dumps/%s.json"%username) as f:
        data = f.read()
        data = json.loads(data.encode())
        currency = data['GET_PLAYER']['player_data']['currencies'][1]['amount']
        latlng = "%f,%f" % (data["lat"],data["lng"])
        items = data['GET_INVENTORY']['inventory_delta']['inventory_items']
        pokemons = []
        candy = defaultdict(int)
        player = {}
        for item in items:
            item = item['inventory_item_data']
            pokemon = item.get("pokemon_data",{})
            if "pokemon_id" in pokemon:
                pokemon['name'] = pokemon_names[str(pokemon['pokemon_id'])]
                pokemon.update(pokemon_details[str(pokemon['pokemon_id'])])
                pokemon['iv'] = pokemonIVPercentage(pokemon)
                pokemons.append(pokemon)
            if 'player_stats' in item:
                player = item['player_stats']
            if "pokemon_family" in item:
                filled_family = str(item['pokemon_family']['family_id']).zfill(4)
                candy[filled_family] += item['pokemon_family'].get("candy",0)
        pokemons = sorted(pokemons, lambda x,y: cmp(x["iv"],y["iv"]),reverse=True)
        # add candy back into pokemon json
        for pokemon in pokemons:
            pokemon['candy'] = candy[pokemon['family_id']]
        player['level_xp'] = player['experience']-player['prev_level_xp']
        player['goal_xp'] = player['next_level_xp']-player['prev_level_xp']
        return render_template('pokemon.html', pokemons=pokemons, player=player, currency="{:,d}".format(currency), candy=candy, latlng=latlng, attacks=attacks)

def init_config():
    parser = argparse.ArgumentParser()
    config_file = "web_config.json"

    # If config file exists, load variables from json
    load = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    parser.add_argument("-s", "--hostname", help="Server hostname/IP")
    parser.add_argument("-p", "--port", help="Server TCP port number")
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=False)
    config = parser.parse_args()
    # Passed in arguments shoud trump
    for key,value in load.iteritems():
      if key not in config.__dict__ or not config.__dict__[key]:
        config.__dict__[key] = value

    return config.__dict__


if __name__ == "__main__":
    config = init_config()
    app.run(host=config["hostname"],port=config["port"],debug=config["debug"])
