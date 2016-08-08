from __future__ import absolute_import

import logging

from six import iteritems
from .release_methods.base import ReleaseMethodFactory


class Release:
    def __init__(self, parent):
        self.parent = parent
        self.log = logging.getLogger(__name__)

        self.release_method_factory = ReleaseMethodFactory(self.parent.config.config_data)

    def do_release_pokemon_by_id(self, p_id):
        release_res = self.parent.api.release_pokemon(pokemon_id=int(p_id)).get('responses', {}).get('RELEASE_POKEMON', {})
        status = release_res.get('result', -1)
        if not status:
            self.log.debug("Failed to release pokemon id %s, %s", p_id, release_res)
        return status

    def do_release_pokemon(self, pokemon):
        self.log.info("Releasing pokemon: %s", pokemon)
        if self.do_release_pokemon_by_id(pokemon.id):
            self.parent.sleep(1.0)
            self.log.info("Successfully Released Pokemon %s", pokemon)
        else:
            self.log.info("Failed to release Pokemon %s", pokemon)

    def cleanup_pokemon(self):
        caught_pokemon = self.parent.inventory.get_caught_pokemon_by_family()
        release_method = self.release_method_factory.getReleaseMethod()
        for pokemon_family_id, pokemon_list in iteritems(caught_pokemon):
            pokemon_to_release, pokemon_to_keep = release_method.getPokemonToRelease(pokemon_family_id, pokemon_list)

            if self.parent.config.pokemon_cleanup_testing_mode:
                for pokemon in pokemon_to_release:
                    self.log.info("(TESTING) Would release pokemon: %s", pokemon)
                for pokemon in pokemon_to_keep:
                    self.log.info("(TESTING) Would keep pokemon: %s", pokemon)
            else:
                for pokemon in pokemon_to_release:
                    self.do_release_pokemon(pokemon)
