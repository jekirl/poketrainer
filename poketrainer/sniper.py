from __future__ import absolute_import

from helper.colorlogger import create_logger
from helper.utilities import flat_map

from .location import distance_in_meters
from .pokedex import pokedex
from .pokemon import POKEMON_NAMES


class Sniper(object):
    def __init__(self, parent):
        self.parent = parent
        self.log = create_logger(__name__)

    # instead of a full heartbeat, just update position.
    # useful for sniping for example
    def send_update_pos(self):
        res = self.parent.api.get_player()
        if not res or res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Can't snipe!", res)
            return False
        return True

    def snipe_pokemon(self, lat, lng):
        posf = self.parent.get_position()
        curr_lat = posf[0]
        curr_lng = posf[1]

        try:
            self.log.info("Sniping pokemon at %f, %f", lat, lng)
            self.parent.map_objects.wait_for_api_timer()

            # move to snipe location
            self.parent.api.set_position(lat, lng, 0.0)
            if not self.send_update_pos():
                return False

            self.log.debug("Teleported to sniping location %f, %f", lat, lng)

            # find pokemons in dest
            map_cells = self.parent.map_objects.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {})\
                .get('map_cells', [])
            pokemons = flat_map(lambda c: c.get('catchable_pokemons', []), map_cells)

            # catch first pokemon:
            pokemon_rarity_and_dist = [
                (
                    pokemon, pokedex.get_rarity_by_id(pokemon['pokemon_id']),
                    distance_in_meters(self.parent.get_position(), (pokemon['latitude'], pokemon['longitude']))
                )
                for pokemon in pokemons]
            pokemon_rarity_and_dist.sort(key=lambda x: x[1], reverse=True)

            if pokemon_rarity_and_dist:
                self.log.info("Rarest pokemon: : %s", POKEMON_NAMES[str(pokemon_rarity_and_dist[0][0]['pokemon_id'])])
                return self.parent.poke_catcher.encounter_pokemon(pokemon_rarity_and_dist[0][0], new_loc=(curr_lat, curr_lng))
            else:
                self.log.info("No nearby pokemon. Can't snipe!")
                return False

        finally:
            self.parent.api.set_position(curr_lat, curr_lng, 0.0)
            self.send_update_pos()
            posf = self.parent.get_position()
            self.log.info("Teleported back to origin at %f, %f", posf[0], posf[1])
