# DISCLAIMER: This is jank
from flask import Flask, render_template, flash, redirect, url_for, abort
import json
import csv
from math import floor
from collections import defaultdict
import re
import argparse

from pgoapi.poke_utils import *
from pgoapi.utilities import *
from pgoapi.game_master import PokemonData, GAME_MASTER
from pgoapi.pokemon import Pokemon
from flask_socketio import SocketIO
import tempfile
import zerorpc
import os

app = Flask(__name__, template_folder="templates")
app.secret_key = ".t\x86\xcb3Lm\x0e\x8c:\x86\xe8FD\x13Z\x08\xe1\x04(\x01s\x9a\xae"

options = {}
attacks = {}
with open ("GAME_ATTACKS_v0_1.tsv") as tsv:
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        attacks[int(row["Num"])] = row["Move"]

def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load['accounts'][0].keys()
    parser.add_argument("-i", "--config_index", help="Index of account in config.json", default=0, type=int)
    config = parser.parse_args()
    load = load['accounts'][config.__dict__['config_index']]
    # Passed in arguments shoud trump
    for key,value in load.iteritems():
        if key not in config.__dict__ or not config.__dict__[key]:
            config.__dict__[key] = value

    return config.__dict__
config = init_config()

def setColumnsToIgnore(columnsToIgnore):
    options['ignore_recent'] = ''
    options['ignore_#'] = ''
    options['ignore_name'] = ''
    options['ignore_lvl'] = ''
    options['ignore_score'] = ''
    options['ignore_IV'] = ''
    options['ignore_CP'] = ''
    options['ignore_max_CP'] = ''
    options['ignore_candies'] = ''
    options['ignore_candy_needed'] = ''
    options['ignore_dust_needed'] = ''
    options['ignore_power_up'] = ''
    options['ignore_stamina'] = ''
    options['ignore_attkIV'] = ''
    options['ignore_staIV'] = ''
    options['ignore_defIV'] = ''
    options['ignore_move1'] = ''
    options['ignore_move2'] = ''

    for column in columnsToIgnore:
        if column.lower() == 'recent':
            options['ignore_recent'] = 'display: none;'
        elif column.lower() == '#':
            options['ignore_id'] = 'display: none;'
        elif column.lower() == 'name':
            options['ignore_name'] = 'display: none;'
        elif column.lower() == 'lvl':
            options['ignore_lvl'] = 'display: none;'
        elif column.lower() == 'score':
            options['ignore_score'] = 'display: none;'
        elif column.lower() == 'iv':
            options['ignore_IV'] = 'display: none;'
        elif column.lower() == 'cp':
            options['ignore_CP'] = 'display: none;'
        elif column.lower() == 'max cp':
            options['ignore_max_CP'] = 'display: none;'
        elif column.lower() == 'candies':
            options['ignore_candies'] = 'display: none;'
        elif column.lower() == 'candy needed':
            options['ignore_candy_needed'] = 'display: none;'
        elif column.lower() == 'dust needed':
            options['ignore_dust_needed'] = 'display: none;'
        elif column.lower() == 'power up':
            options['ignore_power_up'] = 'display: none;'
        elif column.lower() == 'stamina':
            options['ignore_stamina'] = 'display: none;'
        elif column.lower() == 'att iv':
            options['ignore_attkIV'] = 'display: none;'
        elif column.lower() == 'sta iv':
            options['ignore_staIV'] = 'display: none;'
        elif column.lower() == 'def iv':
            options['ignore_defIV'] = 'display: none;'
        elif column.lower() == 'move 1':
            options['ignore_move1'] = 'display: none;'
        elif column.lower() == 'move 2':
            options['ignore_move2'] = 'display: none;'

@app.route("/<username>/pokemon")
def inventory(username):
    c = get_api_rpc(username)
    if c is None:
        return("There is no bot running with the input username!")
    options['DEFINE_POKEMON_LV'] = config.get("DEFINE_POKEMON_LV", "CP")
    options['IGNORE_COLUMNS'] = config.get("IGNORE_COLUMNS", [])
    setColumnsToIgnore(options['IGNORE_COLUMNS'])
    with open("data_dumps/%s.json"%username) as f:
        data = f.read()
        data = json.loads(data.encode())
        currency = data['GET_PLAYER']['player_data']['currencies'][1]['amount']
        latlng = c.current_location()
        latlng = "%f,%f" % (latlng[0],latlng[1])
        items = data['GET_INVENTORY']['inventory_delta']['inventory_items']
        pokemonsData = []
        candy = defaultdict(int)
        for item in items:
            item = item['inventory_item_data']
            pokemon = item.get("pokemon_data",{})
            if "pokemon_id" in pokemon:
                pokemonsData.append(pokemon)
            if 'player_stats' in item:
                player = item['player_stats']
            if "pokemon_family" in item:
                filled_family = str(item['pokemon_family']['family_id']).zfill(4)
                candy[filled_family] += item['pokemon_family'].get("candy",0)
        # add candy back into pokemon json
        pokemons = []
        for pokemon in pokemonsData:
            pkmn = Pokemon(pokemon, player['level'], options['DEFINE_POKEMON_LV'])            
            family_id = re.match("HoloPokemonFamilyId.V([0-9]*).*", pkmn.pokemon_additional_data.FamilyId).group(1)
            pkmn.candy = candy[family_id]
            setMaxCP(pkmn, tcmpVals[int(player['level']*2 + 1)], GAME_MASTER)
            pokemons.append(pkmn)           
        pokemons = sorted(pokemons, lambda x,y: cmp(x.iv, y.iv),reverse=True)             
        player['username'] = data['GET_PLAYER']['player_data']['username']
        player['level_xp'] = player.get('experience',0)-player.get('prev_level_xp',0)
        player['hourly_exp'] = data.get("hourly_exp",0)
        player['goal_xp'] = player.get('next_level_xp',0)-player.get('prev_level_xp',0)
        return render_template('pokemon.html', pokemons=pokemons, player=player, currency="{:,d}".format(currency), candy=candy, latlng=latlng, attacks=attacks, options=options)


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
if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True)
