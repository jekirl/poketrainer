import logging
from collections import defaultdict
from cachetools import TTLCache

import six

from helper.exceptions import TooManyEmptyResponses
from helper.utilities import flatmap
from .location import (distance_in_meters, filtered_forts,
                       get_increments, get_route)
from .poke_utils import get_item_name


class FortWalker:
    def __init__(self, parent):
        self.parent = parent
        self.visited_forts = TTLCache(maxsize=120, ttl=self.parent.config.skip_visited_fort_duration)
        self.route = []
        self.sub_route = []
        self.waypoints = []
        self.next_waypoint = None
        self.total_distance_traveled = 0
        self.base_travel_link = ''
        self._error_counter = 0
        self._error_threshold = 10
        self.log = logging.getLogger(__name__)

    """ will always only walk 1 step (i.e. waypoint), so we can accurately control the speed (via step_size) """

    def loop(self):
        if self._error_counter >= self._error_threshold:
            raise TooManyEmptyResponses('Too many errors in this run!!!')
        if not self.next_waypoint:
            # if we don't have a waypoint atm, calculate new waypoints until location
            if not self.waypoints:
                # create general route first
                if not self.route:
                    if not self._get_route(self.parent.config.experimental, self.parent.config.spin_all_forts,
                                           self.parent.config.use_google):
                        return
                # if we don't 'spin all forts', we create a sub_route here because we don't have one already
                if not (self.parent.config.experimental and self.parent.config.spin_all_forts and self.parent.config.use_google):
                    if not self.sub_route:
                        next_sub_loc = self.route.pop(0)
                        posf = self.parent.get_position()
                        self.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
                        route_data = get_route(
                            self.parent.get_position(), (next_sub_loc['lat'], next_sub_loc['long']),
                            self.parent.config.use_google, self.parent.config.gmaps_api_key,
                            self.parent.config.experimental and self.parent.config.spin_all_forts
                        )
                        self.log.info('===============================================')
                        self.log.info(
                            "Total trip distance will be: {0:.2f} meters".format(route_data['total_distance']))
                        self.sub_route = route_data['steps']
                    next_loc = self.sub_route.pop(0)
                else:
                    next_loc = self.route.pop(0)
                    self.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % self.parent.get_position()
                self.waypoints = get_increments(self.parent.get_position(), (next_loc['lat'], next_loc['long']),
                                                self.parent.step_size)
            self.next_waypoint = self.waypoints.pop(0)
        self._walk(self.next_waypoint)
        self.next_waypoint = None

    """ replaces old spin_all_forts_visible and spin_near_fort, but returns only the forts to spin """

    def _get_route(self, experimental, spin_all_forts, use_google):
        res = self.parent.nearby_map_objects()
        self.log.debug("nearby_map_objects: %s", res)
        map_cells = res.get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', [])
        forts = flatmap(lambda c: c.get('forts', []), map_cells)
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
                map(lambda x: "via:%f,%f" % (x[0]['latitude'], x[0]['longitude']), destinations[1:])
            )
            self.log.info('===============================================')
            self.log.info("Total trip distance will be: {0:.2f} meters".format(route_data['total_distance']))
            self.route = route_data['steps']
        else:
            # convert the forts array to the same format as with google steps
            self.route = [
                {
                    'lat': fort_data[0]['latitude'],
                    'long': fort_data[0]['longitude']
                } for fort_data in destinations
                ]
        return True

    """ replaces the old walking method inside of walk_to"""

    def _walk(self, next_point):
        distance_to_point = distance_in_meters(self.parent.get_position(), next_point)
        self.total_distance_traveled += distance_to_point
        travel_link = '%s%s,%s' % (self.base_travel_link, next_point[0], next_point[1])
        self.log.info("Travel Link: %s", travel_link)
        print(next_point)
        self.parent.api.set_position(*next_point)

    def _walk_back_to_origin(self):
        orig_posf = self.parent.get_orig_position()
        self.route = [{
            'lat': orig_posf[0],
            'long': orig_posf[1]
        }]

    def spin_nearest_fort(self):
        map_cells = self.parent.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells',
                                                                                                         [])
        forts = flatmap(lambda c: c.get('forts', []), map_cells)
        destinations = filtered_forts(self.parent.get_orig_position(), self.parent.get_position(), forts,
                                      self.parent.config.stay_within_proximity,
                                      self.visited_forts)
        if destinations:
            nearest_fort = destinations[0][0]
            nearest_fort_dis = destinations[0][1]
            self.log.info("Nearest fort distance is {0:.2f} meters".format(nearest_fort_dis))

            # Fort is close enough to change our route and walk to
            if nearest_fort_dis > 40.00 <= self.parent.config.wander_steps > 0:
                self.next_waypoint = (destinations[0][0]['latitude'], destinations[0][0]['longitude'], 0)
            elif nearest_fort_dis <= 40.00:
                self.do_fort_spin(nearest_fort, player_postion=self.parent.api.get_position(),
                                  fort_distance=nearest_fort_dis)
                if 'lure_info' in nearest_fort and self.parent.should_catch_pokemon:
                    self.parent.catcher.disk_encounter_pokemon(nearest_fort['lure_info'])

        else:
            self.log.info('No spinnable forts within proximity. Or server returned no map objects.')
            self._error_counter += 1
            self._walk_back_to_origin()

    def do_fort_spin(self, fort, player_postion, fort_distance):
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
            self.parent.sleep(1.0)
            if "items_awarded" in res:
                items = defaultdict(int)
                for item in res['items_awarded']:
                    items[item['item_id']] += item['item_count']
                reward = 'XP +' + str(res['experience_awarded'])
                for item_id, amount in six.iteritems(items):
                    reward += ', ' + str(amount) + 'x ' + get_item_name(item_id)
                self.log.info("Fort spun, yielding: %s",
                              reward)
            else:
                self.log.info("Fort spun, but did not yield any rewards. Possible soft ban?")
            self.visited_forts[fort['id']] = fort
        elif result == 4:
            self.log.debug("Fort spun but Your inventory is full : %s", res)
            self.log.info("Fort spun but Your inventory is full.")
            self.visited_forts[fort['id']] = fort
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
