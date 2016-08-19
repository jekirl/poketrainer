from __future__ import absolute_import

from poketrainer.location import get_route

from . import base


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
            if self.config.show_distance_traveled and self.parent.total_distance_traveled > 0:
                self.log.info('Traveled %.2f meters of %.2f of the trip', self.parent.total_distance_traveled,
                              self.parent.total_trip_distance)

            # create general route first
            if not self.route['steps']:
                # get new route
                if not self._get_route():
                    return False

            next_loc = self.route['steps'].pop(0)

            # we have completed a previously set route
            if self.parent.total_distance_traveled > 0:
                self.log.info('===============================================')
            # route contains only forts, so we actually get a sub-route here with individual steps
            route_data = get_route(
                self.parent.get_position(), (next_loc['lat'], next_loc['long']),
                self.config.use_google, self.config.gmaps_api_key,
                self.config.experimental and self.config.spin_all_forts,
                step_size=self.parent.get_step_size()
            )
            posf = self.parent.get_position()
            self.parent.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
            self.parent.total_distance_traveled = 0
            self.parent.total_trip_distance = route_data['total_distance']
            self.log.info('===============================================')
            self.log.info("Total trip distance will be: {0:.2f} meters"
                          .format(self.parent.total_trip_distance))
            self.steps = route_data['steps']

        if self.config.show_distance_traveled and self.parent.total_distance_traveled > 0:
            self.log.info('Traveled %.2f meters of %.2f of the trip',
                          self.parent.total_distance_traveled, self.parent.total_trip_distance)

        return self.steps.pop(0)

    def walk_back_to_origin(self, origin):
        self.route = {'steps': [
            {
                'lat': origin[0],
                'long': origin[1]
            }
        ], 'total_distance': 0}
        self.steps = []

    """ replaces old spin_near_fort but returns only the forts to spin """

    def _get_route(self):

        forts = self.parent.get_forts()

        if not forts:
            return False

        posf = self.parent.get_position()
        self.parent.base_travel_link = "https://www.google.com/maps/dir/%s,%s/" % (posf[0], posf[1])
        self.parent.total_distance_traveled = 0

        self.route = {'steps': [
            {
                'lat': float(fort_data[0]['latitude']),
                'long': float(fort_data[0]['longitude'])
            } for fort_data in forts
            ], 'total_distance': 0}

        return True
