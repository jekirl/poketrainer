# DISCLAIMER: This is jank
from __future__ import print_function

import argparse
import csv
import json
import os
import time
from collections import defaultdict

import zerorpc
from flask import Flask, flash, jsonify, redirect, render_template, url_for

from pgoapi.poke_lvl_data import TCPM_VALS
from pgoapi.pokemon import Pokemon


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

app = Flask(__name__, template_folder="templates")
app.wsgi_app = ReverseProxied(app.wsgi_app)
app.secret_key = ".t\x86\xcb3Lm\x0e\x8c:\x86\xe8FD\x13Z\x08\xe1\x04(\x01s\x9a\xae"
app.debug = True

options = {}
attacks = {}

with open("GAME_ATTACKS_v0_1.tsv") as tsv:
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
    def required(x):
        return x not in load['accounts'][0].keys()
    parser.add_argument("-i", "--config_index", help="Index of account in config.json", default=0, type=int)
    config = parser.parse_args()
    load = load['accounts'][config.__dict__['config_index']]
    # Passed in arguments shoud trump
    for key, value in load.iteritems():
        if key not in config.__dict__ or not config.__dict__[key]:
            config.__dict__[key] = value

    return config.__dict__


def set_columns_to_ignore(columns_to_ignore):
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
    options['ignore_transfer'] = ''

    for column in columns_to_ignore:
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
        elif column.lower() == 'transfer':
            options['ignore_transfer'] = 'display: none;'


def get_api_rpc(username):
    desc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".listeners")
    sock_port = 0
    with open(desc_file) as f:
        data = f.read()
        data = json.loads(data if len(data) > 0 else '{}')
        if username not in data:
            print("There is no bot running with the input username!")
            return None
        sock_port = int(data[username])

    c = zerorpc.Client()
    c.connect("tcp://127.0.0.1:%i" % sock_port)
    return c


@app.route("/<username>")
@app.route("/<username>/status")
def status(username):
    c = get_api_rpc(username)
    if c is None:
        return("There is no bot running with the input username!")
    config = init_config()
    options['SCORE_METHOD'] = config.get('POKEMON_CLEANUP', {}).get("SCORE_METHOD", "CP")
    options['IGNORE_COLUMNS'] = config.get("IGNORE_COLUMNS", [])
    set_columns_to_ignore(options['IGNORE_COLUMNS'])
    player_json = json.loads(c.get_player_info())
    currency = player_json['player_data']['currencies'][1]['amount']
    latlng = c.current_location()
    latlng = "%f,%f" % (latlng[0], latlng[1])

    items = json.loads(c.get_inventory())['inventory_items']
    pokemons_data = []
    candy = defaultdict(int)
    for item in items:
        item = item['inventory_item_data']
        pokemon = item.get("pokemon_data", {})
        if "pokemon_id" in pokemon:
            pokemons_data.append(pokemon)
        if 'player_stats' in item:
            player = item['player_stats']
        if "pokemon_family" in item:
            filled_family = str(item['pokemon_family']['family_id']).zfill(4)
            candy[filled_family] += item['pokemon_family'].get("candy", 0)
    # add candy back into pokemon json
    pokemons = []
    for pokemon in pokemons_data:
        pkmn = Pokemon(pokemon, player['level'], options['SCORE_METHOD'])
        pkmn.candy = candy[pkmn.family_id]
        pkmn.set_max_cp(TCPM_VALS[int(player['level'] * 2 + 1)])
        pkmn.score = format(pkmn.score, '.2f').rstrip('0').rstrip('.')  # makes the value more presentable to the user
        pokemons.append(pkmn)
    player['username'] = player_json['player_data']['username']
    player['level_xp'] = player.get('experience', 0) - player.get('prev_level_xp', 0)
    player['hourly_exp'] = player.get("hourly_exp", 0)  # Not showing up in inv or player data
    player['goal_xp'] = player.get('next_level_xp', 0) - player.get('prev_level_xp', 0)
    return render_template('status.html', pokemons=pokemons, player=player, currency="{:,d}".format(currency), candy=candy, latlng=latlng, attacks=attacks, username=username, options=options)


@app.route("/<username>/pokemon")
def pokemon(username):
    s = get_api_rpc(username)
    try:
        pokemons = json.loads(s.get_caught_pokemons())
    except ValueError:
        # FIXME Use logger instead of print statements!
        print("Not valid Json")

    return render_template('pokemon.html', pokemons=pokemons, username=username)


@app.route("/<username>/inventory")
def inventory(username):
    s = get_api_rpc(username)
    try:
        inventory = json.loads(s.get_inventory())
    except ValueError:
        # FIXME Use logger instead of print statements!
        print("Not valid Json")

    return render_template('inventory.html', inventory=json.dumps(inventory, indent=2), username=username)


@app.route("/<username>/transfer/<p_id>")
def transfer(username, p_id):
    c = get_api_rpc(username)
    if c and c.release_pokemon_by_id(p_id) == 1:
        flash("Released")
    else:
        flash("Failed!")
    time.sleep(2)
    return redirect(url_for('status', username=username))


@app.route("/<username>/evolve/<p_id>")
def evolve(username, p_id):
    c = get_api_rpc(username)
    if c and c.evolve_pokemon_by_id(p_id) == 1:
        flash("Evolved")
    else:
        flash("Failed!")
    return redirect(url_for('pokemon', username=username))


@app.route("/<username>/snipe/<latlng>")
def snipe(username, latlng):
    c = get_api_rpc(username)

    try:
        if len(latlng.split(',')) == 2:
            l = latlng.split(',')
            lat = float(l[0])
            lng = float(l[1])
        else:
            l = latlng.split(' ')
            lat = float(l[0])
            lng = float(l[1])
    except:
        return jsonify(status=1, result='Error parsing coordinates.')

    if c.snipe_pokemon(lat, lng):
        msg = "Sniped!"
        status = 0
    else:
        msg = "Failed sniping!"
        status = 1
    return jsonify(status=status, result=msg)


def init_web_config():
    load = {
        "hostname": "0.0.0.0",
        "port": 5000,
        "debug": True
    }
    config_file = "web_config.json"
    # If config file exists, load variables from json
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))
    # Read passed in Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--hostname", help="Server hostname/IP")
    parser.add_argument("-p", "--port", help="Server TCP port number", type=int)
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    web_config = parser.parse_args()
    # Passed in arguments should trump
    for key, value in load.iteritems():
        if key not in web_config.__dict__ or not web_config.__dict__[key]:
            web_config.__dict__[key] = value
    return web_config.__dict__


def main():
    web_config = init_web_config()
    app.run(host=web_config["hostname"], port=web_config["port"], debug=web_config["debug"])

if __name__ == "__main__":
    main()
