from __future__ import absolute_import

import json
import logging
import os
import os.path
import socket
from collections import defaultdict
from time import time

import colorlog
import gevent
from gevent.coros import BoundedSemaphore
import six
from six import PY2

import zerorpc
from helper.colorlogger import create_logger
from helper.utilities import dict_merge
from library import api
from pgoapi.exceptions import AuthException

from .config import Config
from .evolve import Evolve
from .fort_walker import FortWalker
from .incubate import Incubate
from .inventory import Inventory
from .location import get_location
from .map_objects import MapObjects
from .player import Player
from .player_stats import PlayerStats
from .poke_catcher import PokeCatcher
from .poke_utils import get_item_name
from .release import Release
from .sniper import Sniper


class Poketrainer(object):
    """ Public functions (without _**) are callable by the webservice! """

    def __init__(self, args):

        self.thread = None
        self.socket = None
        self.cli_args = args
        self.force_debug = args['debug']
        self._req_proxy = None

        # timers, counters and triggers
        self.pokemon_caught = 0
        self._error_counter = 0
        self._error_threshold = 10
        self.start_time = time()
        self.exp_start = None
        self._heartbeat_number = 1  # setting this back to one because we make parse a full heartbeat during login!
        self._heartbeat_frequency = 3  # 1 = always
        self._full_heartbeat_frequency = 15  # 10 = as before (every 10th heartbeat)
        self._farm_mode_triggered = False

        # objects, order is important!
        self.config = None
        self._load_config()

        self.log = create_logger(__name__, self.config.log_colors["poketrainer".upper()])

        self._open_socket()

        # config values that might be changed during runtime
        self.step_size = self.config.step_size
        self.should_catch_pokemon = self.config.should_catch_pokemon
        self.can_push_to_web = False
        self.web_rpc = None

        # other objects
        self.player = Player({})
        self.player_stats = PlayerStats({})
        self.inventory = Inventory(self, [])
        self.fort_walker = FortWalker(self)
        self.map_objects = MapObjects(self)
        self.poke_catcher = PokeCatcher(self)
        self.incubate = Incubate(self)
        self.evolve = Evolve(self)
        self.release = Release(self)
        self.sniper = Sniper(self)

        self._origPosF = (0, 0, 0)
        self.api = None
        self._load_api()

        # threading / locking
        self.sem = BoundedSemaphore(1)  # gevent
        self.persist_lock = False
        self.locker = None

    def sleep(self, t):
        # eventlet.sleep(t * self.config.sleep_mult)
        gevent.sleep(t * self.config.sleep_mult)

    def _open_socket(self):
        desc_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), ".listeners")
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
        data[self.config.username] = sock_port
        with open(desc_file, "w+") as f:
            f.write(json.dumps(data, indent=2))
            f.close()

        s = zerorpc.Server(self)
        s.bind("tcp://127.0.0.1:%i" % sock_port)  # the free port should still be the same
        self.socket = gevent.spawn(s.run)

        # zerorpc requires gevent, thus we would need a solution for eventlets
        # self.socket = self.thread_pool.spawn(wsgi.server, eventlet.listen(('127.0.0.1', sock_port)), self)
        # self.socket = self.thread_pool.spawn(eventlet.serve, eventlet.listen(('127.0.0.1', sock_port)), self)
        # alternative: GreenRPCService

    def _load_config(self):
        if self.config is None:
            config_file = "config.json"

            # If config file exists, load variables from json
            load = {}
            if os.path.isfile(config_file):
                with open(config_file) as data:
                    load.update(json.load(data))

            defaults = load.get('defaults', {})
            config = load.get('accounts', [])[self.cli_args['config_index']]

            if self.cli_args['debug'] or config.get('debug', False):
                colorlog.getLogger("requests").setLevel(logging.DEBUG)
                colorlog.getLogger("pgoapi").setLevel(logging.DEBUG)
                colorlog.getLogger("poketrainer").setLevel(logging.DEBUG)
                colorlog.getLogger("rpc_api").setLevel(logging.DEBUG)

            if config.get('auth_service', '') not in ['ptc', 'google']:
                self.log.error("Invalid Auth service specified for account %s! ('ptc' or 'google')", config.get('username', 'NA'))
                return False

                # merge account section with defaults
            self.config = Config(dict_merge(defaults, config), self.cli_args)
        return True

    def reload_config(self):
        self.config = None
        return self._load_config()

    def _load_api(self, prev_location=None):
        if self.api is None:
            self.api = api.pgoapi.PGoApi()
            # set signature!
            self.api.activate_signature(
                os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), self.cli_args['encrypt_lib'])
            )

            # get position and set it in the API
            if self.cli_args['location']:
                position = get_location(self.cli_args['location'])
            else:
                position = get_location(self.config.location)
            self._origPosF = position
            if prev_location:
                position = prev_location
            self.api.set_position(*position)

            # set proxy if one was provided
            if self.cli_args['proxy']:
                self.api.set_proxy(self.cli_args['proxy'])
                self.log.info('Using proxy: %s', self.cli_args['proxy'])

            # proxies only work with ptc accounts at the moment!
            if self.cli_args['proxy'] and self.config.auth_service != 'ptc':
                self.log.error("Currently proxy only works with ptc accounts.")
                quit()

            # retry login every 30 seconds if any errors
            self.log.info('Starting Login process...')
            login = False
            while not login:
                if self.cli_args['proxy']:
                    login = self.api.login(self.config.auth_service, self.config.username, self.config.get_password(), proxy=self.cli_args['proxy'])
                else:
                    # preserve compatibility with system pgoapi
                    login = self.api.login(self.config.auth_service, self.config.username, self.config.get_password())
                if not login:
                    self.log.error('Login error, retrying Login in 30 seconds')
                    self.sleep(30)
            self.log.info('Login successful')
            self._heartbeat(login, True)
        return True

    def reload_api(self, prev_location=None):
        self.api = None
        return self._load_api(prev_location)

    '''
    Blocking lock
        - only locks if current thread (greenlet) doesn't own the lock
        - persist=True will ensure the lock will not be released until the user
          explicitly sets self.persist_lock=False.
    '''
    def thread_lock(self, persist=False):
        if self.sem.locked():
            if self.locker == id(gevent.getcurrent()):
                self.log.debug("Locker is -- %s. No need to re-lock", id(gevent.getcurrent()))
                return False
            else:
                self.log.debug("Already locked by %s. Greenlet %s will wait...", self.locker, id(gevent.getcurrent()))
        self.sem.acquire()
        self.persist_lock = persist
        self.locker = id(gevent.getcurrent())
        self.log.debug("%s acquired lock (persist=%s)!", self.locker, persist)
        return True

    '''
    Releases the lock if needed and the user didn't persist it
    '''
    def thread_release(self):
        if self.sem.locked() and self.locker == id(gevent.getcurrent()) and not self.persist_lock:
            self.log.debug("%s is now releasing lock", id(gevent.getcurrent()))
            self.sem.release()

    def push_to_web(self, event, action, data):
        gevent.spawn(self._do_push_to_web, event, action, data)

    def _do_push_to_web(self, event, action, data):
        if not self.can_push_to_web:
            self.log.debug('Web pushing is disabled')
            return
        if not self.web_rpc:
            desc_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), ".listeners")
            with open(desc_file) as f:
                sockets = f.read()
                sockets = json.loads(sockets if len(sockets) > 0 else '{}')
                if 'web' not in sockets:
                    self.log.debug('Web RPC socket not found for pushing')
                    self.can_push_to_web = False
                    return
                sock_port = int(sockets['web'])
                f.close()
            self.web_rpc = zerorpc.Client()
            self.web_rpc.connect("tcp://127.0.0.1:%i" % sock_port)
        try:
            self.web_rpc.push(self.config.username, event, action, data)
            self.log.debug('Pushed data to web, event: %s, action: %s', event, action)
        except Exception as e:
            self.log.error('Error trying to push to web, will now stop pushing')
            self.can_push_to_web = False
            self.web_rpc.close()
            self.web_rpc = None
            raise Exception(e)

    def _callback(self, gt):
        try:
            if not gt.exception:
                result = gt.value
                self.log.info('Thread finished with result: %s', result)
        except KeyboardInterrupt:
            return

        self.log.exception('Error in main loop %s, restarting at location: %s',
                           gt.exception, self.get_position())
        # restart after sleep
        self.sleep(30)
        self.reload_config()
        self.reload_api(self.get_position())
        self.start()

    def start(self):
        self.thread = gevent.spawn(self._main_loop)

        self.thread.link(self._callback)

    def stop(self):
        if self.thread:
            self.thread.kill()

    def _main_loop(self):
        if self.config.enable_caching and self.config.experimental:
            if not self.config.use_cache:
                self.log.info('==== CACHING MODE: CACHE FORTS ====')
            else:
                self.log.info('==== CACHING MODE: ROUTE+SPIN CACHED FORTS ====')
            self.fort_walker.setup_cache()
        while True:
            # acquire lock for this thread
            if self.thread_lock(persist=True):
                try:
                    self._heartbeat()
                    self.fort_walker.loop()
                    self.fort_walker.spin_nearest_fort()
                    self.poke_catcher.catch_all()

                finally:
                    # after we're done, release lock
                    self.persist_lock = False
                    self.thread_release()
            # self.log.info("COMPLETED A _main_loop")
            self.sleep(1.0)

    def _heartbeat(self, res=False, login_response=False):
        if not isinstance(res, dict):
            # limit the amount of heartbeats, every second is just too much in my opinion!
            if (not self._heartbeat_number % self._heartbeat_frequency == 0 and
                    not self._heartbeat_number % self._full_heartbeat_frequency == 0):
                self._heartbeat_number += 1
                return

            # making a standard call to update position, etc
            req = self.api.create_request()
            req.get_player()
            if self._heartbeat_number % 10 == 0:
                req.check_awarded_badges()
                req.get_inventory()
            res = req.call()
            if not res or res.get("direction", -1) == 102:
                self.log.error("There were a problem responses for api call: %s. Restarting!!!", res)
                self.api.force_refresh_access_token()
                raise AuthException("Token probably expired?")

        self.log.debug(
            'Response dictionary: \n\r{}'.format(json.dumps(res, indent=2, default=lambda obj: obj.decode('utf8'))))

        status_code = res.get('status_code', -1)
        if status_code == 3:
            self.log.warn('Your account may be banned')
            # exit(0)

        responses = res.get('responses', {})
        if 'GET_PLAYER' in responses:
            self.player = Player(responses.get('GET_PLAYER', {}).get('player_data', {}))
            self.push_to_web('player', 'updated', self.player.__dict__)
            self.log.info("Player Info: {0}, Pokemon Caught in this run: {1}".format(self.player, self.pokemon_caught))

        if 'GET_INVENTORY' in responses:

            # update objects
            self.inventory.update_player_inventory(res=res)
            for inventory_item in self.inventory.get_raw_inventory_items():
                if "player_stats" in inventory_item['inventory_item_data']:
                    old_level = self.player_stats.level
                    self.player_stats = PlayerStats(
                        inventory_item['inventory_item_data']['player_stats'],
                        self.pokemon_caught, self.start_time, self.exp_start
                    )
                    if self.exp_start is None:
                        self.exp_start = self.player_stats.run_exp_start
                    self.push_to_web('player_stats', 'updated', self.player_stats.__dict__)
                    self.log.info("Player Stats: {}".format(self.player_stats))
                    if self.player_stats.level > old_level > 0:
                        self.log.info('Collecting level up rewards for level %s', self.player_stats.level)
                        self.sleep(2.0)
                        resp = self.api.level_up_rewards(level=self.player_stats.level)\
                            .get('responses', {}).get('LEVEL_UP_REWARDS', {})
                        result = resp.get('result', -1)
                        if result == 1:
                            items_awarded = resp.get('items_awarded', [])
                            items = defaultdict(int)
                            for item in items_awarded:
                                items[item['item_id']] += item['item_count']
                            reward = ''
                            for item_id, amount in six.iteritems(items):
                                if reward != '':
                                    reward += ', '
                                reward += str(amount) + 'x ' + get_item_name(item_id)
                            self.log.info('Collected level up rewards: %s', reward)
            if self.config.list_inventory_before_cleanup:
                self.log.info("Player Inventory: %s", self.inventory)
            if not login_response:
                # self.log.debug(self.inventory.cleanup_inventory())
                self.inventory.cleanup_inventory()
                self.log.info("Player Inventory after cleanup: %s", self.inventory)
            if self.config.list_pokemon_before_cleanup:
                self.log.info(os.linesep.join(map(str, self.inventory.get_caught_pokemon())))

            if not login_response:
                # maintenance
                self.incubate.incubate_eggs()
                self.inventory.use_lucky_egg()
                self.evolve.attempt_evolve()
                self.release.cleanup_pokemon()

            # save data dump
            with open("data_dumps/%s.json" % self.config.username, "w") as f:
                posf = self.get_position()
                responses['lat'] = posf[0]
                responses['lng'] = posf[1]
                responses['GET_PLAYER']['player_data']['hourly_exp'] = self.player_stats.run_hourly_exp
                f.write(json.dumps(responses, indent=2, default=lambda obj: obj.decode('utf8')))

            # Farm precon
            if self.config.farm_items_enabled:
                pokeball_count = 0
                if not self.config.farm_ignore_pokeball_count:
                    pokeball_count += self.inventory.poke_balls
                if not self.config.farm_ignore_greatball_count:
                    pokeball_count += self.inventory.great_balls
                if not self.config.farm_ignore_ultraball_count:
                    pokeball_count += self.inventory.ultra_balls
                if not self.config.farm_ignore_masterball_count:
                    pokeball_count += self.inventory.master_balls
                if self.config.pokeball_farm_threshold > pokeball_count and not self._farm_mode_triggered:
                    self.should_catch_pokemon = False
                    self._farm_mode_triggered = True
                    self.log.info("Player only has %s Pokeballs, farming for more...", pokeball_count)
                    if self.config.farm_override_step_size != -1:
                        self.step_size = self.config.farm_override_step_size
                        self.log.info("Player has changed speed to %s", self.step_size)
                elif self.config.pokeball_continue_threshold <= pokeball_count and self._farm_mode_triggered:
                    self.should_catch_pokemon = self.config.should_catch_pokemon  # Restore catch pokemon setting from config file
                    self._farm_mode_triggered = False
                    self.log.info("Player has %s Pokeballs, continuing to catch more!", pokeball_count)
                    if self.config.farm_override_step_size != -1:
                        self.step_size = self.config.step_size
                        self.log.info("Player has returned to normal speed of %s", self.step_size)

        if 'DOWNLOAD_SETTINGS' in responses:
            settings = responses.get('DOWNLOAD_SETTINGS', {}).get('settings', {})
            if settings.get('minimum_client_version', '0.0.0') > '0.33.0':
                self.log.error("Minimum client version has changed... the bot needs to be updated! Will now stop!")
                exit(0)
            map_settings = settings.get('map_settings', {})

            get_map_objects_min_refresh_seconds = map_settings.get('get_map_objects_min_refresh_seconds', 0.0)  # std. 5.0
            if get_map_objects_min_refresh_seconds != self.map_objects.get_api_rate_limit():
                self.map_objects.update_rate_limit(get_map_objects_min_refresh_seconds)

            """
            fort_settings = settings.get('fort_settings', {})
            inventory_settings = settings.get('inventory_settings', {})

            get_map_objects_max_refresh_seconds = map_settings.get('get_map_objects_max_refresh_seconds', 30.0)
            get_map_objects_min_distance_meters = map_settings.get('get_map_objects_min_distance_meters', 10.0)
            encounter_range_meters = map_settings.get('encounter_range_meters', 50.0)
            poke_nav_range_meters = map_settings.get('poke_nav_range_meters', 201.0)
            pokemon_visible_range = map_settings.get('pokemon_visible_range', 70.0)
            get_map_objects_min_refresh_seconds = map_settings.get('get_map_objects_min_refresh_seconds', 5.0)
            google_maps_api_key = map_settings.get('google_maps_api_key', '')

            self.log.info('complete settings: %s', responses.get('DOWNLOAD_SETTINGS', {}))

            self.log.info('minimum_client_version: %s', str(settings.get('minimum_client_version', '0.0.0')))

            self.log.info('poke_nav_range_meters: %s', str(poke_nav_range_meters))
            self.log.info('pokemon_visible_range: %s', str(pokemon_visible_range))

            self.log.info('get_map_objects_min_refresh_seconds: %s', str(get_map_objects_min_refresh_seconds))
            self.log.info('get_map_objects_max_refresh_seconds: %s', str(get_map_objects_max_refresh_seconds))
            self.log.info('get_map_objects_min_distance_meters: %s', str(get_map_objects_min_distance_meters))
            self.log.info('encounter_range_meters: %s', str(encounter_range_meters))
            exit(0)
            """

        self._heartbeat_number += 1
        return res

    def set_position(self, *pos):
        return self.api.set_position(*pos)

    def get_position(self):
        return self.api.get_position()

    def get_orig_position(self):
        return self._origPosF

    """ FOLLOWING ARE FUNCTIONS FOR THE WEB LISTENER """

    def enable_web_pushing(self):
        self.log.info('Enabled pushing to web, caus web told us to!')
        self.can_push_to_web = True
        return self.can_push_to_web

    def current_location(self):
        self.log.info("Web got position: %s", self.get_position())
        return self.get_position()

    def get_player(self):
        return self.player.__dict__

    def get_player_stats(self):
        return self.player_stats.__dict__

    def get_inventory(self):
        return self.inventory.to_dict()

    def get_caught_pokemons(self):
        return self.inventory.get_caught_pokemon(as_dict=True)

    def release_pokemon_by_id(self, p_id):
        # acquire lock for this thread
        if self.thread_lock(persist=True):
            try:
                return self.release.do_release_pokemon_by_id(p_id)
            finally:
                # after we're done, release lock
                self.persist_lock = False
                self.thread_release()
        else:
            return 'Only one Simultaneous request allowed'

    def snipe_pokemon(self, lat, lng):
        # acquire lock for this thread
        if self.thread_lock(persist=True):
            try:
                return self.sniper.snipe_pokemon(float(lat), float(lng))
            finally:
                # after we're done, release lock
                self.map_objects.wait_for_api_timer()
                self.persist_lock = False
                self.thread_release()
        else:
            return 'Only one Simultaneous request allowed'

    """ OLD WEB FUNCTIONS """

    def get_player_info(self):
        return self.player.to_json()

    def get_raw_inventory(self):
        return json.dumps(self.inventory.get_raw_inventory_items())

    def get_caught_pokemons_json(self):
        return self.inventory.get_caught_pokemon_by_family(as_json=True)

    def ping(self):
        self.log.info("Responding to ping")
        return "pong"
