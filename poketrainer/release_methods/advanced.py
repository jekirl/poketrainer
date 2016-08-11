import base
from POGOProtos import Enums_pb2


class ReleaseMethod(base.ReleaseMethod):

    def process_config(self, config):
        self.config = config
        self.keep_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("KEEP_POKEMON_NAMES", []))
        self.throw_pokemon_ids = map(lambda x: getattr(Enums_pb2, x), config.get("THROW_POKEMON_NAMES", []))
        self.max_similar_pokemon = self.config.get('MAX_SIMILAR_POKEMON', 999)
        self.min_similar_pokemon = self.config.get('MIN_SIMILAR_POKEMON', 1)

    def get_pokemon_to_release(self, pokemon_id, pokemons):
        pokemon_to_release = []
        pokemon_to_keep = []

        if len(pokemons) > self.min_similar_pokemon:
            # sorting for CLASSIC method as default
            sorted_pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)

            # Release method ADVANCED will set try_keep for each pokemon that qualifies
            sorted_pokemons = sorted(sorted_pokemons, key=lambda x: (x.iv, x.cp), reverse=True)
            iv_options = self.config.get('RELEASE_METHOD_ADVANCED', {}).get("BEST_IV", {})
            keep = 0
            for i, pokemon in enumerate(sorted_pokemons):
                if keep >= iv_options.get("MAX_AMOUNT", 999) or pokemon.iv < (
                        iv_options.get("IGNORE_BELOW", 0)):
                    break
                if keep < iv_options.get("MIN_AMOUNT", 1) or pokemon.iv > (sorted_pokemons[0].iv * iv_options.get("KEEP_ADDITIONAL_SCALAR", 1.0)):
                    sorted_pokemons[i].try_keep = True
                    keep += 1
            sorted_pokemons = sorted(sorted_pokemons, key=lambda x: (x.cp, x.iv), reverse=True)
            cp_options = self.config.get('RELEASE_METHOD_ADVANCED', {}).get("BEST_CP", {})
            keep = 0
            for i, pokemon in enumerate(sorted_pokemons):
                if keep >= cp_options.get("MAX_AMOUNT", 999):
                    break
                if keep < cp_options.get("MIN_AMOUNT", 1) or pokemon.cp > (sorted_pokemons[0].cp * cp_options.get("KEEP_ADDITIONAL_SCALAR", 1.0)):
                    sorted_pokemons[i].try_keep = True
                    keep += 1

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
        if pokemon.level < self.config.get('RELEASE_METHOD_ADVANCED', {}).get("ALWAYS_RELEASE_BELOW_LEVEL", 0):
            return True
        elif pokemon.try_keep:
            return False
        elif pokemon.cp > self.config.get('RELEASE_METHOD_ADVANCED', {}).get("KEEP_CP_OVER", 500) \
                or pokemon.iv > self.config.get('RELEASE_METHOD_ADVANCED', {}).get("KEEP_IV_OVER", 50):
            return False
        return True
