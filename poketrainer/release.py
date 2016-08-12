from __future__ import absolute_import

from six import iteritems

from helper.colorlogger import create_logger

from .release_methods.base import ReleaseMethodFactory


class Release(object):
    def __init__(self, parent):
        self.parent = parent

        self.log = create_logger(__name__, self.parent.config.log_colors["release".upper()])

        self.release_method_factory = ReleaseMethodFactory(self.parent.config.config_data)

    def do_release_pokemon_by_id(self, p_id):
        release_res = self.parent.api.release_pokemon(pokemon_id=int(p_id)).get('responses', {}).get('RELEASE_POKEMON', {})
        status = release_res.get('result', -1)
        if not status:
            self.log.debug("Failed to release pokemon id %s, %s", p_id, release_res)
        return status

    def do_release_pokemon(self, pokemon):
        self.log.debug("Releasing pokemon: %s", pokemon)
        self.parent.sleep(1.0 + self.parent.config.extra_wait)
        if self.do_release_pokemon_by_id(pokemon.id):
            self.log.info("Successfully Released Pokemon %s", pokemon)
        else:
            self.log.info("Failed to release Pokemon %s", pokemon)

    def cleanup_pokemon(self):
        caught_pokemon = self.parent.inventory.get_caught_pokemon_by_family()
        release_method = self.release_method_factory.get_release_method()
        for pokemon_family_id, pokemon_list in iteritems(caught_pokemon):
            pokemon_to_release, pokemon_to_keep = release_method.get_pokemon_to_release(pokemon_family_id, pokemon_list)

            if self.parent.config.pokemon_cleanup_testing_mode:
                for pokemon in pokemon_to_release:
                    self.log.info("(TESTING) Would release pokemon: %s", pokemon)
                for pokemon in pokemon_to_keep:
                    self.log.info("(TESTING) Would keep pokemon: %s", pokemon)
            else:
                for pokemon in pokemon_to_release:
                    self.do_release_pokemon(pokemon)
