#!/usr/bin/python
# -*- coding: utf-8 -*-

# DISCLAIMER: This is jank

from __future__ import print_function

import csv
import json
import os
import re
from collections import defaultdict
import argparse

import six
from six import PY2, iteritems
import zerorpc
from flask import Flask, flash, jsonify, redirect, render_template, \
    url_for

from pgoapi.poke_utils import pokemon_iv_percentage

if six.PY3:
    from past.builtins import cmp

app = Flask(__name__, template_folder='templates')
app.secret_key = \
    '.t\x86\xcb3Lm\x0e\x8c:\x86\xe8FD\x13Z\x08\xe1\x04(\x01s\x9a\xae'
app.debug = True

pokemon_names = json.load(open('pokemon.en.json'))
pokemon_details = {}

with open('GAME_MASTER_POKEMON_v0_2.tsv') as tsv:
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        family_id = re.match('HoloPokemonFamilyId.V([0-9]*).*',
                             row['FamilyId']).group(1)
        pokemon_details[row['PkMn']] = {
            'BaseStamina': float(row['BaseStamina']),
            'BaseAttack': float(row['BaseAttack']),
            'BaseDefense': float(row['BaseDefense']),
            'family_id': family_id,
            }

attacks = {}

with open('GAME_ATTACKS_v0_1.tsv') as tsv:
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        attacks[int(row['Num'])] = row['Move']


def get_api_rpc(username):
    desc_file = \
        os.path.join(os.path.dirname(os.path.realpath(__file__)),
                     '.listeners')
    sock_port = 0
    with open(desc_file) as f:
        data = f.read()
        data = json.loads((data.encode() if len(data) > 0 else '{}'))
        if username not in data:
            print('There is no bot running with the input username!')
            return None
        sock_port = int(data[username])

    c = zerorpc.Client()
    c.connect('tcp://127.0.0.1:%i' % sock_port)
    return c


def dict_merge(dct, merge_dct):
    for (k, v) in iteritems(merge_dct):
        if k in dct and isinstance(dct[k], dict) \
            and isinstance(merge_dct[k], collections.Mapping):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]
    return dct


def init_config():
    parser = argparse.ArgumentParser()
    config_file = 'config.json'

    # If config file exists, load variables from json

    load = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments

    parser.add_argument('-i', '--config_index',
                        help='Index of account in config.json',
                        default=0, type=int)
    parser.add_argument('-l', '--location', help='Location')
    parser.add_argument('-d', '--debug', help='Debug Mode',
                        action='store_true', default=False)
    config = parser.parse_args()
    defaults = load.get('defaults', {})
    account = load['accounts'][config.__dict__['config_index']]
    load = dict_merge(defaults, account)

    # Passed in arguments shoud trump

    for (key, value) in iteritems(load):
        if key not in config.__dict__ or not config.__dict__[key]:
            config.__dict__[key] = value
    if config.auth_service not in ['ptc', 'google']:
        logger.error("Invalid Auth service specified! ('ptc' or 'google')"
                     )
        return None

    return config.__dict__


@app.route('/<username>')
@app.route('/<username>/status')
def status(username):
    c = get_api_rpc(username)
    config = init_config()
    if not config:
        return

    if c is None:
        return 'There is no bot running with the input username!'

    with open('data_dumps/%s.json' % username) as f:
        data = f.read()
        data = json.loads(data.encode())
        gmaps_api_key = config.get('GMAPS_API_KEY', '')
        currency = data['GET_PLAYER']['player_data']['currencies'
                ][1]['amount']
        latlng = c.current_location()
        latlng = '%f,%f' % (latlng[0], latlng[1])
        items = data['GET_INVENTORY']['inventory_delta'
                ]['inventory_items']
        pokemons = []
        candy = defaultdict(int)
        for item in items:
            item = item['inventory_item_data']
            pokemon = item.get('pokemon_data', {})
            if 'pokemon_id' in pokemon:
                pokemon['name'] = pokemon_names[str(pokemon['pokemon_id'
                        ])]
                pokemon.update(pokemon_details[str(pokemon['pokemon_id'
                               ])])
                pokemon['iv'] = pokemon_iv_percentage(pokemon)
                pokemons.append(pokemon)
            if 'player_stats' in item:
                player = item['player_stats']
            if 'pokemon_family' in item:
                filled_family = str(item['pokemon_family']['family_id'
                                    ]).zfill(4)
                candy[filled_family] += item['pokemon_family'
                        ].get('candy', 0)
        pokemons = sorted(pokemons, lambda x, y: cmp(x['iv'], y['iv']),
                          reverse=True)

        # add candy back into pokemon json

        for pokemon in pokemons:
            pokemon['candy'] = candy[pokemon['family_id']]
        player['level_xp'] = player.get('experience', 0) \
            - player.get('prev_level_xp', 0)
        player['hourly_exp'] = data.get('hourly_exp', 0)
        player['goal_xp'] = player.get('next_level_xp', 0) \
            - player.get('prev_level_xp', 0)
        return render_template(
            'status.html',
            pokemons=pokemons,
            player=player,
            currency='{:,d}'.format(currency),
            candy=candy,
            latlng=latlng,
            gmaps_api_key=gmaps_api_key,
            attacks=attacks,
            username=username,
            )


@app.route('/<username>/pokemon')
def pokemon(username):
    s = get_api_rpc(username)
    try:
        pokemons = json.loads(s.get_caught_pokemons())
    except ValueError:

        # FIXME Use logger instead of print statements!

        print('Not valid Json')

    return render_template('pokemon.html', pokemons=pokemons,
                           username=username)


@app.route('/<username>/inventory')
def inventory(username):
    s = get_api_rpc(username)
    try:
        inventory = json.loads(s.get_inventory())
    except ValueError:

        # FIXME Use logger instead of print statements!

        print('Not valid Json')

    return render_template('inventory.html',
                           inventory=json.dumps(inventory, indent=2),
                           username=username)


@app.route('/<username>/transfer/<p_id>')
def transfer(username, p_id):
    c = get_api_rpc(username)
    if c and c.release_pokemon_by_id(p_id) == 1:
        flash('Released')
    else:
        flash('Failed!')
    return redirect(url_for('inventory', username=username))


@app.route('/<username>/snipe/<latlng>')
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
        msg = 'Sniped!'
        status = 0
    else:
        msg = 'Failed sniping!'
        status = 1
    return jsonify(status=status, result=msg)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
