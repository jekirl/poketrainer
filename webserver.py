from __future__ import print_function

import argparse
import csv
import json
import logging
import os
import socket

import gevent
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from six import PY2

import zerorpc

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


class RpcSocket(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)

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
                f.close()
        data['web'] = sock_port
        with open(desc_file, "w+") as f:
            f.write(json.dumps(data, indent=2))
            f.close()

        s = zerorpc.Server(self)
        s.bind("tcp://127.0.0.1:%i" % sock_port)  # the free port should still be the same
        self.rpc_sock = gevent.spawn(s.run)
        self.rpc_sock.link(self._callback)
        self.log.debug("Socket for push started on: tcp://127.0.0.1:%i", sock_port)

    def _callback(self, gt):
        try:
            if not gt.exception:
                result = gt.value
                self.log.debug('Scoket thread finished with result: %s', result)
        except KeyboardInterrupt:
            return

        self.log.error('Error in socket thread %s', gt.exception)

    def push(self, username, event, action, data):
        # calling emit with socketio.emit() will broadcast messages when we're outside of an http request scope
        self.log.debug('received data from bot: %s, %s, %s, (omitting data)', username, event, action)

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


class BotUsers(object):
    def __init__(self):
        self.users = []
        self.load()

    def get(self, username):
        for user in self.users:
            if user.username == username:
                return user
        return {}
        # return self.users.get(username, {})

    def load(self):
        desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
        with open(desc_file) as f:
            live_users = f.read()
            live_users = json.loads(live_users.encode() if len(live_users) > 0 else '{}')
            for username in live_users:
                if username == 'web':
                    continue
                user = BotConnection(username)
                self.users.append(user)
            f.close()

    def __iter__(self):
        return self.users.__iter__()

    def to_list(self):
        return [user.to_dict() for user in self.users]


class BotConnection(object):
    def __init__(self, username):
        self.username = username
        self.status = 'unknown'
        self.sock_port = 0
        self._bot_rpc = None

    def get_api_rpc(self):
        if not self._bot_rpc:
            desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
            with open(desc_file) as f:
                sockets = f.read()
                sockets = json.loads(sockets if len(sockets) > 0 else '{}')
                if self.username not in sockets:
                    logger.error(self.username + ' not found for pushing')
                    return None
                self.sock_port = int(sockets[self.username])
                f.close()
            self._bot_rpc = zerorpc.Client()
            self._bot_rpc.connect("tcp://127.0.0.1:%i" % self.sock_port)
        return self._bot_rpc

    def test_connection(self, retry=False):
        c = self.get_api_rpc()
        try:
            running = c('enable_web_pushing', timeout=1.5)
            logger.info('Enabled pushing in bot %s', self.username)
        except Exception as e:
            if self._bot_rpc and not retry:
                self._bot_rpc.close()
                self._bot_rpc = None
                logger.debug('Error connecting to bot %s, retrying', self.username)
                return self.test_connection(retry=True)
            else:
                running = False
                logger.error('Error connecting to bot %s: %s', self.username, e)
        if running:
            self.status = 'online'
        else:
            self.status = 'offline'
        socketio.emit('user_status', {'username': self.username, 'status': self.status}, namespace='/poketrainer')

    def __str__(self):
        return self.username

    def to_dict(self):
        return dict((att, val) for att, val in self.__dict__.iteritems() if not att.startswith('_'))


def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    parser.add_argument("-i", "--config_index", help="Index of account in config.json", default=0, type=int)
    config = parser.parse_args()
    load = load['accounts'][config.__dict__['config_index']]
    # Passed in arguments shoud trump
    for key, value in load.iteritems():
        if key not in config.__dict__ or not config.__dict__[key]:
            config.__dict__[key] = value

    return config.__dict__

app = Flask(__name__, static_folder='web-ui/dist', static_url_path='')
app.wsgi_app = ReverseProxied(app.wsgi_app)
app.secret_key = ".t\x86\xcb3Lm\x0e\x8c:\x86\xe8FD\x13Z\x08\xe1\x04(\x01s\x9a\xae"
app.debug = True
socketio = SocketIO(app, async_mode="gevent")
bot_users = BotUsers()

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


@socketio.on('connect', namespace='/poketrainer')
def connect():
    logger.debug('Client connected %s', request.sid)
    emit('connect', {'success': True})


@socketio.on('users', namespace='/poketrainer')
def users():
    for user in bot_users.__iter__():
        logger.debug("Trying to enable web pushing in a background 'thread' for %s", user.username)
        socketio.start_background_task(user.test_connection)
    logger.debug('%s requested users, gave: %s', request.sid, bot_users.to_list())
    emit('users', {'success': True, 'users': bot_users.to_list()})


@socketio.on('disconnect', namespace='/poketrainer')
def disconnect():
    logger.debug('Client disconnected %s', request.sid)


@socketio.on('pull', namespace='/poketrainer')
def get(message):
    username = message['username']
    types = message['types']
    user = bot_users.get(username)
    if not user:
        logger.error("could not find bot '%s', will not get %s", username, types)
        return
    c = user.get_api_rpc()
    if 'location' in types:
        response = c.current_location()
        logger.debug('emitting location')
        emit('pull', {'success': True, 'type': 'location', 'data': response})
    if 'player' in types:
        response = c.get_player()
        logger.debug('emitting player')
        emit('pull', {'success': True, 'type': 'player', 'data': response})
    if 'player_stats' in types:
        response = c.get_player_stats()
        logger.debug('emitting player_stats')
        emit('pull', {'success': True, 'type': 'player_stats', 'data': response})
    if 'inventory' in types:
        response = c.get_inventory()
        logger.debug('emitting inventory')
        emit('pull', {'success': True, 'type': 'inventory', 'data': response})
    if 'pokemon' in types:
        response = c.get_caught_pokemons()
        logger.debug('emitting pokemon')
        emit('pull', {'success': True, 'type': 'pokemon', 'data': response})
    if 'attacks' in types:
        logger.debug('emitting attacks')
        emit('pull', {'success': True, 'type': 'attacks', 'data': attacks})


@socketio.on('join', namespace='/poketrainer')
def on_join(data):
    room = data['room']
    join_room(room)
    logger.debug('%s has joined room %s', request.sid, room)
    emit('join', {'success': True, 'message': 'successfully joined room ' + room})


@socketio.on('leave', namespace='/poketrainer')
def on_leave(data):
    room = data['room']
    leave_room(room)
    logger.debug('%s has left room %s', request.sid, room)
    emit('leave', {'success': True, 'message': 'successfully left room ' + room})


@socketio.on('transfer', namespace='/poketrainer')
def transfer(data):
    username = data['username']
    p_id = data['p_id']
    user = bot_users.get(username)
    if not user:
        logger.error("Could not find bot '%s', will not transfer %s", username, p_id)
        emit('transfer', {'success': False, 'message': "Could not find bot '%s', will not transfer" % username})
        return
    c = user.get_api_rpc()
    if c and c.release_pokemon_by_id(p_id) == 1:
        emit('transfer', {'success': True, 'message': 'Released successfully'})
    else:
        emit('transfer', {'success': False, 'message': 'Transfer failed!'})


@socketio.on('snipe', namespace='/poketrainer')
def snipe(data):
    username = data['username']
    latlng = data['latlng']
    user = bot_users.get(username)
    if not user:
        logger.error("Could not find bot '%s', will not snipe %s", username, latlng)
        emit('snipe', {'success': False, 'message': "Could not find bot '%s', will not snipe %s" % (username, latlng)})
        return
    c = user.get_api_rpc()
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
        emit('snipe', {'success': False, 'message': 'Error parsing coordinates.'})
        return

    if c and c.snipe_pokemon(lat, lng):
        msg = "Sniped!"
        success = False
    else:
        msg = "Failed sniping!"
        success = True
    emit('snipe', {'success': success, 'message': msg})


def init_web_config():
    load = {
        "hostname": "0.0.0.0",
        "port": 5000,
        "debug": False
    }
    config_file = "web_config.json"
    # If config file exists, load variables from json
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))
    return load


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s: [%(levelname)5s] %(message)s')

    web_config = init_web_config()

    if not web_config["debug"]:
        logging.getLogger(__name__).setLevel(logging.INFO)

    # launch rpc socket
    RpcSocket()

    # for some reason when we're using gevent, flask does not output a lot... we'll just notify here
    logger.info('Starting Webserver on %s:%s', str(web_config["hostname"]), str(web_config["port"]))
    # Debug mode will not use gevent and thus breaks the socket
    socketio.run(app, host=web_config["hostname"], port=web_config["port"], log_output=web_config["debug"], debug=False)


if __name__ == '__main__':
    main()
