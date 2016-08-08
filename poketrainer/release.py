import logging

from .release_methods.base import ReleaseMethodFactory


class Release:
    def __init__(self, parent):
        self.parent = parent
        self.log = logging.getLogger(__name__)

        self.releaseMethodFactory = ReleaseMethodFactory(self.parent.config.config_data)

    def do_release_pokemon_by_id(self, p_id):
        release_res = self.parent.api.release_pokemon(pokemon_id=int(p_id)).get('responses', {}).get('RELEASE_POKEMON', {})
        status = release_res.get('result', -1)
        return status

    def do_release_pokemon(self, pokemon):
        self.log.info("Releasing pokemon: %s", pokemon)
        if self.do_release_pokemon_by_id(pokemon.id):
            self.parent.sleep(1.0)
            self.log.info("Successfully Released Pokemon %s", pokemon)
        else:
            # self.log.debug("Failed to release pokemon %s, %s", pokemon, release_res)  # FIXME release_res is not in scope!
            self.log.info("Failed to release Pokemon %s", pokemon)

    def cleanup_pokemon(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.parent.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.parent.get_caught_pokemons(inventory_items)
        releaseMethod = self.releaseMethodFactory.getReleaseMethod()
        for pokemonId, pokemons in caught_pokemon.iteritems():
            pokemonsToRelease, pokemonsToKeep = releaseMethod.getPokemonToRelease(pokemonId, pokemons)

            if self.parent.config.pokemon_cleanup_testing_mode:
                for pokemon in pokemonsToRelease:
                    self.log.info("(TESTING) Would release pokemon: %s", pokemon)
                for pokemon in pokemonsToKeep:
                    self.log.info("(TESTING) Would keep pokemon: %s", pokemon)
            else:
                for pokemon in pokemonsToRelease:
                    self.do_release_pokemon(pokemon)