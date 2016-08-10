# DISCLAIMER: This is jank
from __future__ import print_function

import argparse
import csv
import json
import logging
import os
from collections import defaultdict

import gevent
import socket
import zerorpc
from flask import Flask, flash, jsonify, redirect, render_template, url_for, request, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from six import PY2

from poketrainer.poke_lvl_data import TCPM_VALS
from poketrainer.pokemon import Pokemon

logger = logging.getLogger(__name__)
logging.getLogger("zerorpc").setLevel(logging.WARNING)


# we can remove this class and the use of it if we really don't create URLs with flask anymore
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


class RpcSocket:
    def __init__(self):
        desc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".listeners")
        s = socket.socket()
        s.bind(("", 0))  # let the kernel find a free port
        sock_port = s.getsockname()[1]
        s.close()
        data = {}

        if os.path.isfile(desc_file):
            with open(desc_file, 'r+') as f:
                data = f.read()
                if PY2:
                    data = json.loads(data.encode() if len(data) > 0 else '{}')
                else:
                    data = json.loads(data if len(data) > 0 else '{}')
        data['web'] = sock_port
        with open(desc_file, "w+") as f:
            f.write(json.dumps(data, indent=2))

        s = zerorpc.Server(self)
        s.bind("tcp://127.0.0.1:%i" % sock_port)  # the free port should still be the same
        self.rpc_sock = gevent.spawn(s.run)
        self.rpc_sock.link(self._callback)
        print("Socket for bots started on: tcp://127.0.0.1:%i" % sock_port)

    def _callback(self, gt):
        try:
            if not gt.exception:
                result = gt.value
                print('Scoket thread finished with result: %s', result)
        except KeyboardInterrupt:
            return

        print('Error in socket thread %s', gt.exception)

    def push(self, username, event, action, data):
        # calling emit with socketio.emit() will broadcast messages when we're outside of an http request scope
        print('received data from bot: ', username, ', ', event, ':', action, ', omitting data')

        push_template = dict()
        push_template['room'] = ''
        push_template['username'] = username
        push_template['event'] = event
        push_template['action'] = action
        push_template['data'] = data

        push_template['room'] = 'global'
        socketio.emit('push', push_template, namespace='/poketrainer', room='global')
        push_template['room'] = username
        socketio.emit('push', push_template, namespace='/poketrainer', room=username)


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


def _thread_callback(gt):
    if not gt.exception:
        result = gt.value
        print('Connected to bot and enabled pushing with result: %s', result)
    else:
        print('Error connecting to bot %s', gt.exception)


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

app = Flask(__name__, static_folder='web-ui/dist', static_url_path='')
app.wsgi_app = ReverseProxied(app.wsgi_app)
app.secret_key = ".t\x86\xcb3Lm\x0e\x8c:\x86\xe8FD\x13Z\x08\xe1\x04(\x01s\x9a\xae"
app.debug = True
socketio = SocketIO(app, async_mode="gevent")

options = {}
attacks = {}

with open("resources" + os.sep + "GAME_ATTACKS_v0_1.tsv") as tsv:
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        attacks[int(row["Num"])] = row["Move"]


@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/<path:filename>')
def static_proxy(filename):
    # send_static_file will guess the correct MIME type
    return send_from_directory('', filename)


@app.route("/api/player")
def users():
    users = []

    desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
    with open(desc_file) as f:
        live_users = f.read()
        live_users = json.loads(live_users.encode() if len(live_users) > 0 else '{}')

        threads = {}
        for username in live_users:
            if username == 'web':
                continue
            c = get_api_rpc(username)
            if c is None:
                continue

            print("try to enable web pushing in a background 'thread' for %s", username)
            threads[username] = gevent.spawn(c.enable_web_pushing)
            threads[username].link(_thread_callback)
            print("continue...")
            user = {'username': username}
            users.append(user)
    print("got all users")
    return jsonify(users)


@socketio.on('status', namespace='/poketrainer')
def get_status(message):
    username = message['username']
    c = get_api_rpc(username)
    config = init_config()
    options['SCORE_METHOD'] = config.get('POKEMON_CLEANUP', {}).get("SCORE_METHOD", "CP")
    player_json = {}
    status = 0
    try:
        player_json = json.loads(c.get_player_info())
    except:
        status = 1
    currency = player_json['player_data']['currencies'][1]['amount']
    latlng = c.current_location()

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
        seriPoke = json.loads(pkmn.to_json()) # this makes the pokemon class serializable although its kinda hacky
        pokemons.append(seriPoke)
    player['username'] = player_json['player_data']['username']
    player['level_xp'] = player.get('experience', 0) - player.get('prev_level_xp', 0)
    player['hourly_exp'] = player.get("hourly_exp", 0)  # Not showing up in inv or player data
    player['goal_xp'] = player.get('next_level_xp', 0) - player.get('prev_level_xp', 0)
    player['pokemon'] = pokemons
    player['attacks'] = attacks
    player['latitude'] = latlng[0]
    player['longitude'] = latlng[1]
    player['candy'] = candy
    player['stardust'] = currency
    player['item_capacity'] = player_json['player_data']['max_item_storage']
    player['pokemon_capacity'] = player_json['player_data']['max_pokemon_storage']
    emit('status', {'data': json.dumps(player), 'status': status})


@socketio.on('connect', namespace='/poketrainer')
def connect():
    users = []

    desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
    with open(desc_file) as f:
        live_users = f.read()
        live_users = json.loads(live_users.encode() if len(live_users) > 0 else '{}')

        threads = {}
        for username in live_users:
            if username == 'web':
                continue
            c = get_api_rpc(username)
            if c is None:
                continue

            threads[username] = gevent.spawn(c.enable_web_pushing)
            threads[username].link(_thread_callback)
            user = {'username': username}
            users.append(user)
    print('Client connected', request.sid)
    emit('connect', {'success': True, 'users': users})


@socketio.on('disconnect', namespace='/poketrainer')
def disconnect():
    print('Client disconnected', request.sid)


# TODO: this is not used yet, but we need something like this to 'pull' actual data from a bot
@socketio.on('get', namespace='/poketrainer')
def get(message):
    s = get_api_rpc(message['username'])
    response = {}
    response = json.loads(s.get_caught_pokemons())
    emit('get', {'success': True, 'data': response})


@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    print(request.sid + ' has joined room ' + room)
    emit('leave', {'success': True, 'message': 'successfully joined room ' + room})


@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    print(request.sid + ' has left room ' + room)
    emit('leave', {'success': True, 'message': 'successfully left room ' + room})


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
    return load


def main():
    web_config = init_web_config()

    rpc_socket_thread = RpcSocket()

    # for some reason when we're using gevent, flask does not output a lot... we'll just notify here
    print('Starting Webserver on ' + str(web_config["hostname"]) + ':' + str(web_config["port"]))
    # Debug mode will not use gevent and thus breaks the socket
    socketio.run(app, host=web_config["hostname"], port=web_config["port"], log_output=web_config["debug"], debug=False)


if __name__ == '__main__':
    main()
