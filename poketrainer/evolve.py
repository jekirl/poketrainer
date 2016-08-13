from __future__ import absolute_import

from helper.colorlogger import create_logger

from .pokemon import Pokemon


class Evolve(object):
    def __init__(self, parent):
        self.parent = parent

        self.log = create_logger(__name__, self.parent.config.log_colors["evolve".upper()])

    def attempt_evolve(self):
        caught_pokemon = self.parent.inventory.get_caught_pokemon_by_family()
        for pokemons in caught_pokemon.values():
            if len(pokemons) > self.parent.config.min_similar_pokemon:
                pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)
                for pokemon in pokemons[self.parent.config.min_similar_pokemon:]:
                    # If we can't evolve this type of pokemon anymore, don't check others.
                    if not self.attempt_evolve_pokemon(pokemon):
                        break
            elif self.parent.config.explain_evolution_before_cleanup:
                self.log.info(
                    'Not evolving %s because you have %s but need more than %s.',
                    pokemons[0].pokemon_type, len(pokemons), self.parent.config.min_similar_pokemon
                )

    def attempt_evolve_pokemon(self, pokemon):
        if self.is_pokemon_eligible_for_evolution(pokemon=pokemon):
            return self.do_evolve_pokemon(pokemon)
        else:
            return False

    def do_evolve_pokemon(self, pokemon):
        self.log.info("Evolving pokemon: %s", pokemon)
        self.parent.sleep(0.2 + self.parent.config.extra_wait)
        evo_res = self.parent.api.evolve_pokemon(pokemon_id=int(pokemon.id)).get('responses', {}).get('EVOLVE_POKEMON', {})
        status = evo_res.get('result', -1)
        # self.sleep(3)
        if status == 1:
            evolved_pokemon = Pokemon(evo_res.get('evolved_pokemon_data', {}),
                                      self.parent.player_stats.level, self.parent.config.score_method,
                                      self.parent.config.score_settings)
            self.log.info("Evolved to %s", evolved_pokemon)
            self.parent.push_to_web('pokemon', 'evolved',
                                    {'old': pokemon.__dict__, 'new': evolved_pokemon.__dict__})
            self.parent.inventory.update_player_inventory()
            return True
        else:
            self.log.debug("Could not evolve Pokemon %s", evo_res)
            self.log.info("Could not evolve pokemon %s | Status %s", pokemon, status)
            self.parent.inventory.update_player_inventory()
            return False

    def is_pokemon_eligible_for_evolution(self, pokemon):
        candy_have = self.parent.inventory.pokemon_candy.get(int(pokemon.family_id), -1)
        candy_needed = self.parent.config.pokemon_evolution.get(pokemon.pokemon_id, None)
        in_keep_list = pokemon.pokemon_id in self.parent.config.keep_pokemon_ids
        is_favorite = pokemon.is_favorite
        in_evolution_list = pokemon.pokemon_id in self.parent.config.pokemon_evolution

        eligible_to_evolve = bool(
            candy_needed and
            candy_have > candy_needed and
            not in_keep_list and
            not is_favorite and
            in_evolution_list
        )

        if self.parent.config.explain_evolution_before_cleanup:
            self.log.info(
                "%s can evolve? %s! Need candy: %s. Have candy: %s. Favorite? %s. In keep list? %s. In evolution list? %s.",
                pokemon.pokemon_type, eligible_to_evolve, candy_needed, candy_have, in_keep_list, is_favorite, in_evolution_list
            )
        return eligible_to_evolve
