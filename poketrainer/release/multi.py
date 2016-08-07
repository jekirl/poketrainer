import copy
import logging


from six import iteritems

from pgoapi.protos.POGOProtos import Enums_pb2

import base

logger = logging.getLogger(__name__)


class ReleaseMethod(base.ReleaseMethod):

    def processConfig(self, config):
        self.config = config
        self.releaseMethodFactory = base.ReleaseMethodFactory({})
        self.baseConfig = copy.deepcopy(config)
        if 'RELEASE_METHOD_MULTI' in self.baseConfig:
            del self.baseConfig['RELEASE_METHOD_MULTI']

        self.handlers = {}
        self.multiConfig = config.get('RELEASE_METHOD_MULTI', {})
        self.DEFAULT_RELEASE_METHOD = self.multiConfig.get('MULTI_DEFAULT_RELEASE_METHOD', "CLASSIC")

        # build default config and override with the config values in its section in base config then override with
        # config values in its section in the multi config
        self.defaultConfig = copy.deepcopy(self.baseConfig)
        self.defaultConfig = base.filtered_dict_merge(self.defaultConfig, self.multiConfig, "POKEMON_CONFIGS")
        self.defaultConfig['RELEASE_METHOD'] = self.DEFAULT_RELEASE_METHOD
        self.defaultHandler = self.releaseMethodFactory.loadReleaseMethod(self.DEFAULT_RELEASE_METHOD, self.defaultConfig)

        for pokemonName, pokemonConfig in iteritems(self.multiConfig.get('POKEMON_CONFIGS', {})):
            pokeId = getattr(Enums_pb2, pokemonName)
            releaseMethod = pokemonConfig.get('RELEASE_METHOD', self.DEFAULT_RELEASE_METHOD)
            # initialize the config with the default config
            cfg = copy.deepcopy(self.defaultConfig)
            # apply pokemon specific overrides
            cfg = base.filtered_dict_merge(cfg, pokemonConfig)
            self.handlers[pokeId] = self.releaseMethodFactory.loadReleaseMethod(releaseMethod, cfg)

    def getPokemonToRelease(self, pokemonId, pokemons):
        if pokemonId in self.handlers:
            return self.handlers[pokemonId].getPokemonToRelease(pokemonId, pokemons)
        else:
            return self.defaultHandler.getPokemonToRelease(pokemonId, pokemons)
