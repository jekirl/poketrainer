import base
from pgoapi.protos.POGOProtos import Enums_pb2


class ReleaseMethod(base.ReleaseMethod):

    @staticmethod
    def getConfigSections():
        return ("RELEASE_METHOD_CLASSIC", "RELEASE_METHOD_DUPLICATES")

    def processConfig(self, config):
        self.config = config
        self.keep_pokemon_ids               = map(lambda x: getattr(Enums_pb2, x), config.get("KEEP_POKEMON_NAMES", []))
        self.throw_pokemon_ids              = map(lambda x: getattr(Enums_pb2, x), config.get("THROW_POKEMON_NAMES", []))
        self.MAX_SIMILAR_POKEMON            = self.config.get('MAX_SIMILAR_POKEMON', 999)
        self.MIN_SIMILAR_POKEMON            = self.config.get('MIN_SIMILAR_POKEMON', 1)

    def getPokemonToRelease(self, pokemonId, pokemons):
        pokemonToRelease = []
        pokemonToKeep = []

        if len(pokemons) > self.MIN_SIMILAR_POKEMON:
            # sorting for CLASSIC method as default
            sorted_pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)

            sorted_pokemons = sorted(sorted_pokemons, key=lambda x: (x.score, x.cp, x.iv), reverse=True)

            kept_pokemon_of_type = self.MIN_SIMILAR_POKEMON
            pokemonToKeep = sorted_pokemons[0:self.MIN_SIMILAR_POKEMON]
            for pokemon in sorted_pokemons[self.MIN_SIMILAR_POKEMON:]:
                if self.is_pokemon_eligible_for_transfer(pokemon, sorted_pokemons[0], kept_pokemon_of_type):
                    pokemonToRelease.append(pokemon)
                else:
                    pokemonToKeep.append(pokemon)
                    kept_pokemon_of_type += 1
        else:
            pokemonToKeep = pokemons

        return pokemonToRelease, pokemonToKeep


    def is_pokemon_eligible_for_transfer(self, pokemon, best_pokemon=None, kept_pokemon_of_type=0, kept_pokemon_of_type_high_iv=0):
        # never release favorites
        if pokemon.is_favorite:
            return False
        # keep defined pokemon unless we are above MAX_SIMILAR_POKEMON
        if pokemon.pokemon_id in self.keep_pokemon_ids and kept_pokemon_of_type <= self.MAX_SIMILAR_POKEMON:
            return False
        # release defined throwaway pokemons
        if pokemon.pokemon_id in self.throw_pokemon_ids:
            return True
        if best_pokemon.score * self.config.get("RELEASE_DUPLICATES_SCALAR", 1.0) > pokemon.score \
                and pokemon.score < self.config.get("RELEASE_DUPLICATES_MAX_SCORE", 0):
            return True
        else:
            return False
