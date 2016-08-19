from __future__ import absolute_import

import logging

from poketrainer.location import get_location, get_route

from . import base


class Walker(base.Walker):
    def __init__(self, config, parent):
        self.config = config
        self.parent = parent

        self.route = []  # route should contain the complete path we're planning to go
        self.steps = []  # steps contain all steps to the next route target

    """ will always only walk 1 step (i.e. waypoint), so we can accurately control the speed (via step_size) """

    def next_step(self):
        # if we don't have a waypoint atm, calculate new waypoints to location
        if not self.steps:
            if self.config.show_distance_traveled and self.parent.total_distance_traveled > 0:
                self.parent.module_log(logging.INFO, 'Traveled %.2f meters of %.2f of the trip',
                                       self.parent.total_distance_traveled, self.parent.total_trip_distance)

            # create general route first
            if not self.route:
                self._get_route()

            next_loc = self.route.pop(0)

            # we have completed a previously set route
            if self.parent.total_distance_traveled > 0:
                self.parent.module_log(logging.INFO, '===============================================')

            # create a sub-route with individual steps to next location
            route_data = get_route(
                self.parent.get_position(), next_loc,
                self.config.use_google, self.config.gmaps_api_key,
                step_size=self.parent.get_step_size()
            )
            posf = self.parent.get_position()
            self.parent.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
            self.parent.total_distance_traveled = 0
            self.parent.total_trip_distance = route_data['total_distance']
            self.parent.module_log(logging.INFO, '===============================================')
            self.parent.module_log(logging.INFO, "Total trip distance will be: {0:.2f} meters"
                                   .format(self.parent.total_trip_distance))
            self.steps = route_data['steps']

        if self.config.show_distance_traveled and self.parent.total_distance_traveled > 0:
            self.parent.module_log(logging.INFO, 'Traveled %.2f meters of %.2f of the trip',
                                   self.parent.total_distance_traveled, self.parent.total_trip_distance)

        return self.steps.pop(0)

    def walk_back_to_origin(self, origin):
        self._get_route()
        self.steps = []

    def _get_route(self):
        self.route = []
        for waypoint in self.config.predefined_path:
            self.route.append(get_location(waypoint))
        return True
