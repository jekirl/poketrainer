from __future__ import print_function


class Listener(object):
    def __init__(self, api):
        self.api = api

    def release_pokemon_by_id(self, p_id):
        return self.api.do_release_pokemon_by_id(p_id)

    def current_location(self):
        # FIXME use logger instead of print statements!
        print(self.api._posf)
        return self.api._posf

    def get_caught_pokemons(self):
        return self.api.get_caught_pokemons(as_json=True)

    def get_inventory(self):
        return self.api.get_player_inventory(as_json=True)

    def get_player_info(self):
        return self.api.get_player_info()

    def snipe_pokemon(self, lat, lng):
        return self.api.snipe_pokemon(float(lat), float(lng))

    def ping(self):
        return "pong"
