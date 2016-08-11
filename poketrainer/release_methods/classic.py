import logging

import base
from library.api.pgoapi.protos.POGOProtos import Enums_pb2

logger = logging.getLogger(__name__)


class ReleaseMethod(base.ReleaseMethod):

    def process_config(self, config):
        self.config = config
        self.keep_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("KEEP_POKEMON_NAMES", []))
        self.throw_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("THROW_POKEMON_NAMES", []))
        self.keep_cp_over = self.config.get('RELEASE_METHOD_CLASSIC', {}).get('KEEP_CP_OVER', 0)
        self.keep_iv_over = self.config.get('RELEASE_METHOD_CLASSIC', {}).get('KEEP_IV_OVER', 0)
        self.max_similar_pokemon = self.config.get('MAX_SIMILAR_POKEMON', 999)
        self.min_similar_pokemon = self.config.get('MIN_SIMILAR_POKEMON', 1)

    def get_pokemon_to_release(self, pokemon_id, pokemons):
        pokemon_to_release = []
        pokemon_to_keep = []

        if len(pokemons) > self.min_similar_pokemon:
            # sorting for CLASSIC method as default
            sorted_pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)

            kept_pokemon_of_type = self.min_similar_pokemon
            pokemon_to_keep = sorted_pokemons[0:self.min_similar_pokemon]
            for pokemon in sorted_pokemons[self.min_similar_pokemon:]:
                if self.is_pokemon_eligible_for_transfer(pokemon, sorted_pokemons[0], kept_pokemon_of_type):
                    pokemon_to_release.append(pokemon)
                else:
                    pokemon_to_keep.append(pokemon)
                    kept_pokemon_of_type += 1
        else:
            pokemon_to_keep = pokemons
        return pokemon_to_release, pokemon_to_keep

    def is_pokemon_eligible_for_transfer(self, pokemon, best_pokemon=None, kept_pokemon_of_type=0, kept_pokemon_of_type_high_iv=0):
        # never release favorites
        if pokemon.is_favorite:
            return False
        # keep defined pokemon unless we are above MAX_SIMILAR_POKEMON
        if pokemon.pokemon_id in self.keep_pokemon_ids and kept_pokemon_of_type <= self.max_similar_pokemon:
            return False
        # release defined throwaway pokemons
        if pokemon.pokemon_id in self.throw_pokemon_ids:
            return True
        # CLASSIC fallback method
        if pokemon.cp > self.keep_cp_over or pokemon.iv > self.keep_iv_over:
            return False
        return True
