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
from helper.utilities import flat_map

from .location import distance_in_meters, filtered_forts, get_route
from .poke_utils import get_item_name

if six.PY3:
    from past.builtins import map


class FortWalker(object):
    def __init__(self, parent):
        self.parent = parent
        self.visited_forts = TTLCache(maxsize=120, ttl=self.parent.config.skip_visited_fort_duration)
        self.route = {'steps': [], 'total_distance': 0}  # route should contain the complete path we're planning to go
        self.route_only_forts = False
        self.steps = []  # steps contain all steps to the next route target
        self.next_step = None
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

    """ will always only walk 1 step (i.e. waypoint), so we can accurately control the speed (via step_size) """

    def loop(self):
        if self._error_counter >= self._error_threshold:
            self._error_counter = 0
            raise TooManyEmptyResponses('Too many errors in this run!!!')
        if not self.next_step:
            # if wander_step was set, we will create a route to this point ignoring google
            if self.wander_steps:
                self.next_step = self.wander_steps.pop(0)
                self.wander_steps = []
            else:
                # if we don't have a waypoint atm, calculate new waypoints until location
                if not self.steps:
                    if self.parent.config.show_distance_traveled and self.total_distance_traveled > 0 and self.route_only_forts:
                        self.log.info('Traveled %.2f meters of %.2f of the trip', self.total_distance_traveled, self.total_trip_distance)

                    # create general route first
                    if not self.route['steps']:
                        # we have completed a previously set route
                        if not self.route_only_forts and self.total_distance_traveled > 0:
                            self.log.info('===============================================')
                        # get new route
                        if not self._get_route(self.parent.config.experimental, self.parent.config.spin_all_forts,
                                               self.parent.config.use_google, self.parent.config.enable_caching):
                            return
                        # if the route is not only forts, it contains a lot of points
                        # thus we show the total trip size here (after route is calculated) and not for every route-point
                        if not self.route_only_forts:
                            posf = self.parent.get_position()
                            self.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
                            self.total_distance_traveled = 0
                            self.total_trip_distance = self.route['total_distance']
                            self.log.info('===============================================')
                            self.log.info("Total trip distance will be: {0:.2f} meters".
                                          format(self.total_trip_distance))

                    next_loc = self.route['steps'].pop(0)
                    # if the route is not only forts, we can just set one step at a time
                    if not self.route_only_forts:
                        self.steps = [next_loc]
                    else:
                        # we have completed a previously set route
                        if self.total_distance_traveled > 0:
                            self.log.info('===============================================')
                        # route contains only forts, so we actually get a sub-route here with individual steps
                        route_data = get_route(
                            self.parent.get_position(), (next_loc['lat'], next_loc['long']),
                            self.parent.config.use_google, self.parent.config.gmaps_api_key,
                            self.parent.config.experimental and self.parent.config.spin_all_forts,
                            step_size=self.parent.step_size
                        )
                        posf = self.parent.get_position()
                        self.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
                        self.total_distance_traveled = 0
                        self.total_trip_distance = route_data['total_distance']
                        self.log.info('===============================================')
                        self.log.info("Total trip distance will be: {0:.2f} meters"
                                      .format(self.total_trip_distance))
                        self.steps = route_data['steps']

                if self.parent.config.show_distance_traveled and self.total_distance_traveled > 0:
                    self.log.info('Traveled %.2f meters of %.2f of the trip',
                                  self.total_distance_traveled, self.total_trip_distance)
                self.next_step = self.steps.pop(0)
        self._walk(self.next_step)
        self.next_step = None

    """ replaces old spin_all_forts_visible, spin_near_fort and spin_all_cached_forts
        but returns only the forts to spin """

    def _get_route(self, experimental, spin_all_forts, use_google, enable_caching):
        destinations = []
        if self.use_cache and experimental and enable_caching:
            destinations = self._sort_cached_forts()

            if not destinations:
                self.log.info('Turning on caching mode')
                self._walk_back_to_origin()
                self.use_cache = False
                self.cache_is_sorted = False

        if not destinations:
            res = self.parent.map_objects.nearby_map_objects()
            self.log.debug("nearby_map_objects: %s", res)
            map_cells = res.get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
            forts = flat_map(lambda c: c.get('forts', []), map_cells)
            # filter forts and sort by distance
            destinations = filtered_forts(self.parent.get_orig_position(), self.parent.get_position(), forts,
                                          self.parent.config.stay_within_proximity,
                                          self.visited_forts)
            if not destinations:
                self.log.debug("No fort to walk to! %s", res)
                self.log.info('No more spinnable forts within proximity. Or server error')
                self._error_counter += 1
                self._walk_back_to_origin()
                return False
            self._error_counter = 0

            if enable_caching and experimental and not self.use_cache:
                self._cache_forts(forts=destinations)

        posf = self.parent.get_position()
        self.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
        self.total_distance_traveled = 0

        # honestly it makes no sense to use spin_all_forts without google, but i'm leaving it that way
        # wander_steps should only be used if we're not using google i guess
        if experimental and spin_all_forts:
            if len(destinations) >= 20:
                destinations = destinations[:20]
            furthest_fort = destinations[0][0]
            # this will essentially sort the forts in the most efficient way (using google)
            route_data = get_route(
                self.parent.get_position(), (furthest_fort['latitude'], furthest_fort['longitude']),
                use_google, self.parent.config.gmaps_api_key,
                experimental and spin_all_forts,
                map(lambda x: "via:%f,%f" % (x[0]['latitude'], x[0]['longitude']), destinations[1:]),
                step_size=self.parent.step_size
            )
            self.route = route_data
            self.route_only_forts = False
        else:
            self.route = {'steps': [
                {
                    'lat': float(fort_data[0]['latitude']),
                    'long': float(fort_data[0]['longitude'])
                } for fort_data in destinations
            ], 'total_distance': 0}
            self.route_only_forts = True
        return True

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
        orig_posf = self.parent.get_orig_position()
        self.route = {'steps': [
            {
                'lat': orig_posf[0],
                'long': orig_posf[1]
            }
        ], 'total_distance': 0}
        self.steps = []
        # though this is wrong, it ensures we're calculating a new path no matter the settings
        self.route_only_forts = True

    def spin_nearest_fort(self):
        map_cells = self.parent.map_objects.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {})\
            .get('map_cells', [])
        forts = flat_map(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self.parent.get_orig_position(), self.parent.get_position(), forts,
                                      self.parent.config.stay_within_proximity,
                                      self.visited_forts)
        if destinations:
            nearest_fort = destinations[0][0]
            nearest_fort_dis = destinations[0][1]
            if self.parent.config.show_nearest_fort_distance:
                self.log.info("Nearest fort distance is {0:.2f} meters".format(nearest_fort_dis))

            # Fort is close enough to change our route and walk to
            if not self.wander_steps and nearest_fort_dis < self.parent.config.wander_steps and nearest_fort_dis > 40:
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

                while (len(temp_sorted) < len(self.all_cached_forts)):  # sort all elements
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
