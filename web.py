# DISCLAIMER: This is jank
from flask import Flask, render_template, flash, redirect, url_for
import json
import csv
from math import floor
from collections import defaultdict
import re
from pgoapi.poke_utils import *
import tempfile
import zerorpc
import os

app = Flask(__name__, template_folder="templates")
app.secret_key = ".t\x86\xcb3Lm\x0e\x8c:\x86\xe8FD\x13Z\x08\xe1\x04(\x01s\x9a\xae"

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

def get_player_data(username):
    player = {}
    with open("data_dumps/%s.json"%username) as f:
        data = f.read()
        data = json.loads(data.encode())

        items = data['GET_INVENTORY']['inventory_delta']['inventory_items']

        for item in items:
            item = item['inventory_item_data']
            if 'player_stats' in item:
                player = item['player_stats']

        # add candy back into pokemon json
        player['level_xp'] = player.get('experience',0)-player.get('prev_level_xp',0)
        player['hourly_exp'] = data.get("hourly_exp",0)
        player['goal_xp'] = player.get('next_level_xp',0)-player.get('prev_level_xp',0)
        player['username'] = username

    return player

@app.route("/")
def users():
   import glob
   data_files = glob.glob("data_dumps/*.json")
   users = []
   
   for file_path in data_files:
       match = re.search('\/([^\.]+)\.', file_path)
       if match:
           user_data = get_player_data(match.group()[1:-1])
           users.append(user_data)

   return render_template('users.html', users=users)

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
        player['level_xp'] = player.get('experience',0)-player.get('prev_level_xp',0)
        player['hourly_exp'] = data.get("hourly_exp",0)
        player['goal_xp'] = player.get('next_level_xp',0)-player.get('prev_level_xp',0)
        player['username'] = username
        return render_template('pokemon.html', pokemons=pokemons, player=player, currency="{:,d}".format(currency), candy=candy, latlng=latlng, attacks=attacks)

@app.route("/<username>/transfer/<p_id>")
def transfer(username, p_id):
    desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
    sock_port = 0
    with open(desc_file) as f:
        data = f.read()
        data = json.loads(data.encode() if len(data) > 0 else '{}')
        if username not in data:
            flash("There is not such username!")
            return redirect(url_for('inventory', username = username))#will also fail?
        sock_port = int(data[username])

    c = zerorpc.Client()
    c.connect("tcp://127.0.0.1:%i"%sock_port)
    if c.releasePokemonById(p_id) == 1:
        flash("Released")
    else:
        flash("Failed!")
    return redirect(url_for('inventory', username = username))
    
if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True)
