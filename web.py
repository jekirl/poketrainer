# DISCLAIMER: This is jank
from flask import Flask, render_template, flash, redirect, url_for, abort
import json
import csv
from math import floor
from collections import defaultdict
from datetime import datetime
import re
from pgoapi.poke_utils import *
from pgoapi.inventory import *
import tempfile
import zerorpc
import os
from flask_socketio import SocketIO

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

@app.route("/<username>/pokemon")
def inventory(username):
    c = get_api_rpc(username)
    if c is None:
        return("There is no bot running with the input username!")
    with open("data_dumps/%s.json"%username) as f:
        data = f.read()
        data = json.loads(data.encode())
        currency = data['GET_PLAYER']['player_data']['currencies'][1]['amount']
        latlng = c.current_location()
        latlng = "%f,%f" % (latlng[0],latlng[1])
        items = data['GET_INVENTORY']['inventory_delta']['inventory_items']
        pokemons = []
        candy = defaultdict(int)
        last_caught_timestamp = 0
        inventory_items = Inventory(items)
        player = {}
        inventory = {}
        for item in items:
            item = item['inventory_item_data']
            pokemon = item.get("pokemon_data",{})
            if "pokemon_id" in pokemon:
                pokemon['name'] = pokemon_names[str(pokemon['pokemon_id'])]
                pokemon.update(pokemon_details[str(pokemon['pokemon_id'])])
                pokemon['iv'] = pokemonIVPercentage(pokemon)
                pokemons.append(pokemon)
                if pokemon['creation_time_ms'] > last_caught_timestamp:
                    last_caught_timestamp = pokemon['creation_time_ms']
            if 'player_stats' in item:
                player = item['player_stats']
            if "pokemon_family" in item:
                filled_family = str(item['pokemon_family']['family_id']).zfill(4)
                candy[filled_family] += item['pokemon_family'].get("candy",0)
        pokemons = sorted(pokemons, lambda x,y: cmp(x["iv"],y["iv"]),reverse=True)
        # add candy back into pokemon json
        for pokemon in pokemons:
            pokemon['candy'] = candy[pokemon['family_id']]
        inventory['poke_balls'] = inventory_items.poke_balls
        inventory['ultra_balls'] = inventory_items.ultra_balls
        inventory['great_balls'] = inventory_items.great_balls
        inventory['master_balls'] = inventory_items.master_balls
        inventory['potion'] = inventory_items.potion
        inventory['hyper_potion'] = inventory_items.hyper_potion
        inventory['super_potion'] = inventory_items.super_potion
        inventory['max_potion'] = inventory_items.max_potion
        inventory['lucky_eggs'] = inventory_items.lucky_eggs
        inventory['razz_berries'] = inventory_items.razz_berries
        inventory['revive'] = inventory_items.revive
        inventory['max_revive'] = inventory_items.max_revive
        inventory['incenses'] = inventory_items.incenses
        inventory['lures'] = inventory_items.lures
        inventory['total'] = inventory_items.item_count()
        player['level_xp'] = player.get('experience',0)-player.get('prev_level_xp',0)
        player['hourly_exp'] = data.get("hourly_exp",0)
        player['goal_xp'] = player.get('next_level_xp',0)-player.get('prev_level_xp',0)
        player['username'] = username
        player['max_item_storage'] = data['GET_PLAYER']['player_data']['max_item_storage']
        player['max_pokemon_storage'] = data['GET_PLAYER']['player_data']['max_pokemon_storage']
        return render_template('pokemon.html', pokemons=pokemons, player=player, inventory=inventory, currency="{:,d}".format(currency), candy=candy, latlng=latlng, attacks=attacks, last_caught_timestamp=last_caught_timestamp)

def get_api_rpc(username):
    desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
    sock_port = 0
    with open(desc_file) as f:
        data = f.read()
        data = json.loads(data.encode() if len(data) > 0 else '{}')
        if username not in data:
            print("There is no bot running with the input username!")
            return None
        sock_port = int(data[username])

    c = zerorpc.Client()
    c.connect("tcp://127.0.0.1:%i"%sock_port)
    return c

@app.route("/<username>/transfer/<p_id>")
def transfer(username, p_id):
    c = get_api_rpc(username)
    if c and c.releasePokemonById(p_id) == 1:
        flash("Released")
    else:
        flash("Failed!")
    return redirect(url_for('inventory', username = username))

# filter epoch to readable date like: {{ pokemon["creation_time_ms"]|epochToDate }}
@app.template_filter('epochToDate')
def _jinja2_filter_datetime(pokeEpochTime, fmt=None):
    return datetime.fromtimestamp(pokeEpochTime/1000).strftime('%Y-%m-%d %H:%M:%S')    

if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True)
