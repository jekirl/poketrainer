import logging

from .pokemon import Pokemon


class Evolve:
    def __init__(self, parent):
        self.parent = parent
        self.log = logging.getLogger(__name__)

    def attempt_evolve(self, inventory_items=None):
        if not inventory_items:
            self.parent.sleep(0.2)
            inventory_items = self.parent.api.get_inventory() \
                .get('responses', {}).get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
        caught_pokemon = self.parent.get_caught_pokemons(inventory_items)
        self.inventory = Player_Inventory(self.parent.config.ball_priorities, inventory_items)
        for pokemons in caught_pokemon.values():
            if len(pokemons) > self.parent.config.min_similar_pokemon:
                pokemons = sorted(pokemons, key=lambda x: (x.cp, x.iv), reverse=True)
                for pokemon in pokemons[self.parent.config.min_similar_pokemon:]:
                    # If we can't evolve this type of pokemon anymore, don't check others.
                    if not self.attempt_evolve_pokemon(pokemon):
                        break

    def attempt_evolve_pokemon(self, pokemon):
        if self.is_pokemon_eligible_for_evolution(pokemon=pokemon):
            self.log.info("Evolving pokemon: %s", pokemon)
            self.parent.sleep(0.2)
            evo_res = self.parent.api.evolve_pokemon(pokemon_id=pokemon.id).get('responses', {}).get('EVOLVE_POKEMON', {})
            status = evo_res.get('result', -1)
            # self.sleep(3)
            if status == 1:
                evolved_pokemon = Pokemon(evo_res.get('evolved_pokemon_data', {}),
                                          self.parent.player_stats.level, self.parent.config.score_method,
                                          self.parent.config.score_settings)
                # I don' think we need additional stats for evolved pokemon. Since we do not do anything with it.
                # evolved_pokemon.pokemon_additional_data = self.game_master.get(pokemon.pokemon_id, PokemonData())
                self.log.info("Evolved to %s", evolved_pokemon)
                self.parent.update_player_inventory()
                return True
            else:
                self.log.debug("Could not evolve Pokemon %s", evo_res)
                self.log.info("Could not evolve pokemon %s | Status %s", pokemon, status)
                self.parent.update_player_inventory()
                return False
        else:
            return False

    def is_pokemon_eligible_for_evolution(self, pokemon):
        candy_have = self.inventory.pokemon_candy.get(
            self.parent.config.pokemon_evolution_family.get(pokemon.pokemon_id, None), -1)
        candy_needed = self.parent.config.pokemon_evolution.get(pokemon.pokemon_id, None)
        return candy_have > candy_needed and \
               pokemon.pokemon_id not in self.parent.config.keep_pokemon_ids \
               and not pokemon.is_favorite \
               and pokemon.pokemon_id in self.parent.config.pokemon_evolution
