class Listener(object):
  def __init__(self,api):
    self.api = api
  def releasePokemonById(self, p_id):
    return self.api.do_release_pokemon_by_id(p_id)
#  def getCaughtPokemons(self):
#    return self.api.get_caught_pokemons()
  def ping(self):
    return "pong"