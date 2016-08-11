import copy
import logging

from six import iteritems

import base
from POGOProtos import Enums_pb2

logger = logging.getLogger(__name__)


class ReleaseMethod(base.ReleaseMethod):

    def process_config(self, config):
        self.config = config
        self.release_method_factory = base.ReleaseMethodFactory({})
        self.base_config = copy.deepcopy(config)
        if 'RELEASE_METHOD_MULTI' in self.base_config:
            del self.base_config['RELEASE_METHOD_MULTI']

        self.handlers = {}
        self.multi_config = config.get('RELEASE_METHOD_MULTI', {})
        self.default_release_method = self.multi_config.get('MULTI_DEFAULT_RELEASE_METHOD', "CLASSIC")

        # build default config and override with the config values in its section in base config then override with
        # config values in its section in the multi config
        self.default_config = copy.deepcopy(self.base_config)
        self.default_config = base.filtered_dict_merge(self.default_config, self.multi_config, "POKEMON_CONFIGS")
        self.default_config['RELEASE_METHOD'] = self.default_release_method
        self.default_handler = self.release_method_factory.load_release_method(self.default_release_method, self.default_config)

        for pokemon_name, pokemon_config in iteritems(self.multi_config.get('POKEMON_CONFIGS', {})):
            poke_id = getattr(Enums_pb2, pokemon_name)
            release_method = pokemon_config.get('RELEASE_METHOD', self.default_release_method)
            # initialize the config with the default config
            cfg = copy.deepcopy(self.default_config)
            # apply pokemon specific overrides
            cfg = base.filtered_dict_merge(cfg, pokemon_config)
            self.handlers[poke_id] = self.release_method_factory.load_release_method(release_method, cfg)

    def get_pokemon_to_release(self, pokemon_id, pokemons):
        if pokemon_id in self.handlers:
            return self.handlers[pokemon_id].get_pokemon_to_release(pokemon_id, pokemons)
        else:
            return self.default_handler.get_pokemon_to_release(pokemon_id, pokemons)
