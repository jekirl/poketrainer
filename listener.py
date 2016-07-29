class Listener(object):
  def __init__(self,api):
    self.api = api
  def releasePokemonById(self, p_id):
    return self.api.do_release_pokemon_by_id(p_id)

  def current_location(self):
    print self.api._posf
    return self.api._posf

  def snipePokemon(self, lat, lng):
    return self.api.snipe_pokemon(float(lat), float(lng))
    
#  def getCaughtPokemons(self):
#    return self.api.get_caught_pokemons()
  def ping(self):
    return "pong"
