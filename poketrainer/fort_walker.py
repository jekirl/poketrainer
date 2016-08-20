from __future__ import absolute_import

import copy
import os
import pickle
import sys
from collections import defaultdict

import six
from cachetools import TTLCache

from helper.colorlogger import create_logger
from helper.exceptions import TooManyEmptyResponses

from .location import distance_in_meters, filtered_forts, get_route
from .poke_utils import get_item_name
from .walker.base import WalkerFactory


class FortWalker(object):
    def __init__(self, parent):
        self.parent = parent
        self.visited_forts = TTLCache(maxsize=120, ttl=self.parent.config.skip_visited_fort_duration)

        self.wander_steps = []  # only set when we want to wander
        self.total_distance_traveled = 0
        self.total_trip_distance = 0
        self.base_travel_link = ''

        self._error_counter = 0
        self._error_threshold = 10

        self.all_cached_forts = []
        self.spinnable_cached_forts = []
        self.cache_is_sorted = self.parent.config.cache_is_sorted
        self.use_cache = self.parent.config.use_cache

        self.log = create_logger(__name__, self.parent.config.log_colors["fort_walker".upper()])

        self.walker_factory = WalkerFactory()
        self.walker = None

    """ provide log function for children, so all logs are sent from this module """

    def module_log(self, lvl, msg, *args, **kwargs):
        self.log.log(lvl, msg, *args, **kwargs)

    """ will always only walk 1 step (i.e. waypoint), so we can accurately control the speed (via step_size) """

    def loop(self):
        if self._error_counter >= self._error_threshold:
            self._error_counter = 0
            raise TooManyEmptyResponses('Too many errors in this run!!!')

        # if wander_step was set, we will create a route to this point ignoring google and our walker
        if self.wander_steps:
            next_step = self.wander_steps.pop(0)
            # self.wander_steps = []  # bug?
        else:
            next_step = self.get_walker().next_step()
            if not next_step:
                return False
        self._walk(next_step)

    def get_position(self):
        return self.parent.get_position()

    def get_step_size(self):
        return self.parent.step_size

    def get_walker(self):
        if not self.walker:
            self.walker = self.walker_factory.get_walker(self.parent.config, self)
        return self.walker

    def get_forts(self):
        forts = []
        if self.use_cache and self.parent.config.experimental and self.parent.config.enable_caching:
            forts = self._sort_cached_forts()

            if not forts:
                self.log.info('Turning on caching mode')
                self._walk_back_to_origin()
                self.use_cache = False
                self.cache_is_sorted = False

        if not forts:
            forts = self.parent.map_objects.get_forts()
            if not forts:
                self.log.debug("No fort to walk to! %s", forts)
                self.log.info('No more forts within proximity. Or server error')
                self._error_counter += 1
            else:
                self._error_counter = 0
            # filter forts and sort by distance
            forts = filtered_forts(self.parent.get_orig_position(), self.parent.get_position(), forts,
                                   self.parent.config.stay_within_proximity, self.visited_forts)
            if not forts:
                self.log.info('No more spinnable forts within proximity. Walking back to origin')
                self._walk_back_to_origin()
                return False

            if forts and self.parent.config.experimental and self.parent.config.enable_caching and not self.use_cache:
                self._cache_forts(forts=forts)

        return forts

    """ replaces the old walking method inside of walk_to"""

    def _walk(self, next_point):
        next_point = (next_point['lat'], next_point['long'], 0)
        distance_to_point = distance_in_meters(self.parent.get_position(), next_point)
        self.total_distance_traveled += distance_to_point
        if self.parent.config.show_steps:
            travel_link = ''
            if self.parent.config.show_travel_link_with_steps:
                travel_link = ': %s%s,%s' % (self.base_travel_link, next_point[0], next_point[1])
            self.log.info("Walking %.1fm%s", distance_to_point, travel_link)
        self.parent.api.set_position(*next_point)
        self.parent.push_to_web('position', 'update', next_point)

    def _walk_back_to_origin(self):
        self.get_walker().walk_back_to_origin(self.parent.get_orig_position())

    def spin_nearest_fort(self):
        # we cannot use the cached forts here, because of lures
        forts = self.parent.map_objects.get_forts()
        destinations = filtered_forts(self.parent.get_orig_position(), self.parent.get_position(), forts,
                                      self.parent.config.stay_within_proximity, self.visited_forts)
        if destinations:
            nearest_fort = destinations[0][0]
            nearest_fort_dis = destinations[0][1]
            if self.parent.config.show_nearest_fort_distance:
                self.log.info("Nearest fort distance is {0:.2f} meters".format(nearest_fort_dis))

            # Fort is close enough to change our route and walk to
            if not self.wander_steps and 40 < nearest_fort_dis < self.parent.config.wander_steps:
                # create route directly to fort, disabling google
                route_data = get_route(
                    self.parent.get_position(), (destinations[0][0]['latitude'], destinations[0][0]['longitude']),
                    use_google=False, gmaps_api_key='', walk_to_all_forts=False, waypoints=None,
                    step_size=self.parent.step_size
                )
                self.wander_steps = route_data['steps']
            elif nearest_fort_dis <= 40.00:
                self.do_fort_spin(nearest_fort, player_postion=self.parent.api.get_position(),
                                  fort_distance=nearest_fort_dis)
                if 'lure_info' in nearest_fort and self.parent.should_catch_pokemon:
                    self.parent.poke_catcher.disk_encounter_pokemon(nearest_fort['lure_info'])

            self._error_counter = 0

        else:
            self.log.info('No spinnable forts within proximity. Or server returned no map objects.')
            self._error_counter += 1
            self._walk_back_to_origin()

    def do_fort_spin(self, fort, player_postion, fort_distance):
        self.parent.sleep(0.2 + self.parent.config.extra_wait)
        res = self.parent.api.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'],
                                          fort_longitude=fort['longitude'],
                                          player_latitude=player_postion[0],
                                          player_longitude=player_postion[1])
        result = -1
        if res:
            res = res.get('responses', {}).get('FORT_SEARCH', {})
            result = res.pop('result', -1)
        if result == 1:
            self.log.info("Visiting fort... (http://maps.google.com/maps?q=%s,%s)", fort['latitude'], fort['longitude'])
            if "items_awarded" in res:
                items = defaultdict(int)
                for item in res['items_awarded']:
                    items[item['item_id']] += item['item_count']
                reward = 'XP +' + str(res['experience_awarded'])
                for item_id, amount in six.iteritems(items):
                    reward += ', ' + str(amount) + 'x ' + get_item_name(item_id)
                self.log.info("Fort spun, yielding: %s",
                              reward)
                self.parent.push_to_web('fort', 'spun', {
                    'reward': reward, 'location': {'lat': fort['latitude'], 'long': fort['longitude']}
                })
            else:
                self.log.warning("Fort spun, but did not yield any rewards. Possible soft ban?")
            self.visited_forts[fort['id']] = fort
            self.parent.forts_spun += 1
        elif result == 4:
            self.log.debug("Fort spun but Your inventory is full : %s", res)
            self.log.info("Fort spun but Your inventory is full.")
            self.visited_forts[fort['id']] = fort
            self.parent.forts_spun += 1
        elif result == 2:
            self.log.debug("Could not spin fort -  fort not in range %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Not in Range %s", fort['latitude'],
                          fort['longitude'], fort_distance)
        elif result == 3:
            self.log.debug("Could not spin fort -  still on cooldown %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Still on cooldown",
                          fort['latitude'],
                          fort['longitude'])
        else:
            self.log.debug("Could not spin fort %s", res)
            self.log.info("Could not spin fort http://maps.google.com/maps?q=%s,%s, Error id: %s", fort['latitude'],
                          fort['longitude'], result)
            return False
        return True

    def setup_cache(self):
        try:
            self.log.debug("Opening cache file...")
            with open(self.parent.config.cache_filename, 'rb') as handle:
                self.all_cached_forts = pickle.load(handle)

        except Exception as e:
            self.log.debug("Could not find or open cache, making new cache... %s", e)
            if not os.path.exists('./cache'):
                os.makedirs('./cache')
            try:
                os.remove(self.parent.config.cache_filename)
            except OSError:
                pass
            with open(self.parent.config.cache_filename, 'wb') as handle:
                pickle.dump(self.all_cached_forts, handle)

    def _cache_forts(self, forts):
        if not self.all_cached_forts:
            with open(self.parent.config.cache_filename, 'wb') as handle:
                pickle.dump(forts, handle)

            with open(self.parent.config.cache_filename, 'rb') as handle:
                self.all_cached_forts = pickle.load(handle)

            self.log.info("Cache was empty... Dumping in new forts and initializing all_cached_forts")

        else:
            for fort in forts:
                if not any(fort[0]['id'] == x[0]['id'] for x in self.all_cached_forts):
                    self.all_cached_forts.insert(0, fort)
                    self.log.info("Added new fort to cache")

            with open(self.parent.config.cache_filename, 'wb') as handle:
                pickle.dump(self.all_cached_forts, handle)

        self.log.info("Cached forts %s: ", len(self.all_cached_forts))

    def _sort_cached_forts(self):
        if len(self.all_cached_forts) > 0:
            if not self.cache_is_sorted:
                self.log.info("Cache is unsorted, sorting now...")
                temp_all_cached = copy.deepcopy(self.all_cached_forts)  # copy over original
                temp_sorted = [copy.deepcopy(temp_all_cached[0])]  # the final list to copy to cache
                temp_element = copy.deepcopy(temp_all_cached[0])  # cur element
                temp_bool = True

                while len(temp_sorted) < len(self.all_cached_forts):  # sort all elements
                    temp_last_element = copy.deepcopy(temp_sorted[-1])
                    temp_element = copy.deepcopy(temp_sorted[0])
                    temp_max_float = sys.float_info.max  # start with max float to find min distance

                    if (temp_bool):
                        for fort in temp_all_cached:
                            orig_posf = self.parent.get_orig_position()
                            if distance_in_meters((orig_posf[0], orig_posf[1]),
                                                  (fort[0]['latitude'], fort[0]['longitude'])) <= temp_max_float:
                                temp_element = copy.deepcopy(fort)
                                temp_max_float = distance_in_meters((orig_posf[0], orig_posf[1]),
                                                                    (fort[0]['latitude'], fort[0]['longitude']))

                        temp_sorted.pop(0)
                        temp_sorted.append(temp_element)
                        temp_all_cached.remove(temp_element)
                        temp_bool = False
                    else:
                        for fort in temp_all_cached:
                            if ((distance_in_meters((temp_last_element[0]['latitude'], temp_last_element[0]['longitude']),
                                                    (fort[0]['latitude'], fort[0]['longitude'])) <= temp_max_float) and
                                    (not any(fort[0]['id'] == x[0]['id'] for x in temp_sorted))):
                                temp_element = copy.deepcopy(fort)
                                temp_max_float = distance_in_meters(
                                    (temp_last_element[0]['latitude'], temp_last_element[0]['longitude']),
                                    (fort[0]['latitude'], fort[0]['longitude']))
                        temp_all_cached.remove(temp_element)
                        temp_sorted.append(temp_element)

                self.spinnable_cached_forts = copy.deepcopy(temp_sorted)
                self.cache_is_sorted = True

                with open(self.parent.config.cache_filename, 'wb') as handle:
                    pickle.dump(self.spinnable_cached_forts, handle)

            if not self.spinnable_cached_forts:
                self.spinnable_cached_forts = copy.deepcopy(self.all_cached_forts)
            return self.spinnable_cached_forts
        else:
            self.log.info("Cache is empty! Switching mode to cache forts")
            return False
