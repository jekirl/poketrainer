from __future__ import absolute_import

import logging
from time import time

from .location import get_neighbors


class MapObjects:
    def __init__(self, parent):
        self.parent = parent
        self.log = logging.getLogger(__name__)

        self._map_objects_rate_limit = 5.0
        self._last_got_map_objects = 0

        # cache
        self._objects = {}

    def get_api_rate_limit(self):
        return self._map_objects_rate_limit

    def update_rate_limit(self, new_rate_limit):
        self._map_objects_rate_limit = new_rate_limit

    def wait_for_api_timer(self):
        self.log.info("Waiting for API limit timer ...")
        while time() - self._last_got_map_objects < self._map_objects_rate_limit:
            self.parent.sleep(0.1)

    def nearby_map_objects(self):
        if time() - self._last_got_map_objects > self._map_objects_rate_limit:
            position = self.parent.api.get_position()
            neighbors = get_neighbors(self.parent.get_position())
            self.parent.sleep(1.0 + self.parent.config.extra_wait)
            self._objects = self.parent.api.get_map_objects(
                latitude=position[0], longitude=position[1],
                since_timestamp_ms=[0, ] * len(neighbors),
                cell_id=neighbors)
            self._last_got_map_objects = time()
        return self._objects
