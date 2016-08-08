import logging


class MapObjects:
    def __init__(self, parent):
        self.parent = parent
        self.log = logging.getLogger(__name__)

    def nearby_map_objects(self):
        if time() - self._last_got_map_objects > self._map_objects_rate_limit:
            position = self.api.get_position()
            neighbors = get_neighbors(self.get_position())
            gevent.sleep(1.0)
            self.map_objects = self.api.get_map_objects(
                latitude=position[0], longitude=position[1],
                since_timestamp_ms=[0, ] * len(neighbors),
                cell_id=neighbors)
            self._last_got_map_objects = time()
        return self.map_objects