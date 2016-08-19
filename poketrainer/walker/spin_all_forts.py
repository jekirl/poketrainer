from __future__ import absolute_import

import six

from poketrainer.location import get_route

from . import base

if six.PY3:
    from past.builtins import map


class Walker(base.Walker):
    def __init__(self, config, parent):
        self.config = config
        self.parent = parent
        self.log = parent.log

        self.route = {'steps': [], 'total_distance': 0}  # route should contain the complete path we're planning to go
        self.steps = []  # steps contain all steps to the next route target

    """ will always only walk 1 step (i.e. waypoint), so we can accurately control the speed (via step_size) """

    def next_step(self):
        # if we don't have a waypoint atm, calculate new waypoints to location
        if not self.steps:
            # create general route first
            if not self.route['steps']:
                # we have completed a previously set route
                if self.parent.total_distance_traveled > 0:
                    self.log.info('===============================================')
                # get new route
                if not self._get_route():
                    return False
                # if the route is not only forts, it contains a lot of points
                # thus we show the total trip size here (after route is calculated) and not for every route-point
                posf = self.parent.get_position()
                self.parent.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
                self.parent.total_distance_traveled = 0
                self.parent.total_trip_distance = self.route['total_distance']
                self.log.info('===============================================')
                self.log.info("Total trip distance will be: {0:.2f} meters".
                              format(self.parent.total_trip_distance))

            next_loc = self.route['steps'].pop(0)
            # if the route is not only forts, we can just set one step at a time
            self.steps = [next_loc]

        if self.config.show_distance_traveled and self.parent.total_distance_traveled > 0:
            self.log.info('Traveled %.2f meters of %.2f of the trip',
                          self.parent.total_distance_traveled, self.parent.total_trip_distance)
        return self.steps.pop(0)

    def walk_back_to_origin(self, origin):
        self.route = get_route(
            self.parent.get_position(), (origin[0], origin[1]),
            self.config.use_google, self.config.gmaps_api_key, True,
            step_size=self.parent.get_step_size()
        )
        self.steps = []

    """ replaces old spin_all_forts_visible """

    def _get_route(self):

        forts = self.parent.get_forts()

        if not forts:
            return False

        posf = self.parent.get_position()
        self.parent.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
        self.parent.total_distance_traveled = 0

        # honestly it makes no sense to use spin_all_forts without google, but i'm leaving it that way
        # wander_steps should only be used if we're not using google i guess
        if len(forts) >= 20:
            forts = forts[:20]
        furthest_fort = forts[0][0]
        # this will essentially sort the forts in the most efficient way (using google)
        route_data = get_route(
            self.parent.get_position(), (furthest_fort['latitude'], furthest_fort['longitude']),
            self.config.use_google, self.config.gmaps_api_key, True,
            map(lambda x: "via:%f,%f" % (x[0]['latitude'], x[0]['longitude']), forts[1:]),
            step_size=self.parent.get_step_size()
        )
        self.route = route_data

        return True
