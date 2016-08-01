import base
import logging
import copy
from pgoapi.protos.POGOProtos import Enums_pb2
logger = logging.getLogger(__name__)

class ReleaseMethod(base.ReleaseMethod):

    @staticmethod
    def getConfigSections():
        return []

    def processConfig(self, config):
        self.config                 = config
        self.releaseMethodFactory   = base.ReleaseMethodFactory({})
        self.baseConfig             = copy.deepcopy(config)
        self.handlers               = {}
        self.multiConfig            = config.get('RELEASE_METHOD_MULTI', {})
        self.DEFAULT_RELEASE_METHOD = self.multiConfig.get('MULTI_DEFAULT_RELEASE_METHOD', "CLASSIC")

        if 'RELEASE_METHOD_MULTI' in self.baseConfig:
            del self.baseConfig['RELEASE_METHOD_MULTI']

        # build default config and override with the config values in its section in base config then override with
        # config values in its section in the multi config
        self.defaultConfig = copy.deepcopy(self.baseConfig)
        klass = self.releaseMethodFactory.getKlass(self.DEFAULT_RELEASE_METHOD)
        sections = klass.getConfigSections()
        for section in sections:
            self.defaultConfig.update(self.baseConfig.get(section, {}))
            self.defaultConfig.update(self.multiConfig.get(section, {}))
        self.defaultHandler = self.releaseMethodFactory.loadReleaseMethod(self.DEFAULT_RELEASE_METHOD, self.defaultConfig)

        for pokemonName, pokemonConfig in self.multiConfig.get('POKEMON_CONFIGS', {}).iteritems():
            pokeId = getattr(Enums_pb2, pokemonName)
            releaseMethod = pokemonConfig.get('RELEASE_METHOD', self.DEFAULT_RELEASE_METHOD)
            klass = self.releaseMethodFactory.getKlass(releaseMethod)
            sections = klass.getConfigSections()
            cfg = copy.deepcopy(self.baseConfig)
            for section in sections:
                cfg.update(self.baseConfig.get(section, {}))
                cfg.update(self.multiConfig.get(section, {}))
            cfg.update(pokemonConfig)
            self.handlers[pokeId] = self.releaseMethodFactory.loadReleaseMethod(releaseMethod, cfg)


    def getPokemonToRelease(self, pokemonId, pokemons):
        if pokemonId in self.handlers:
            return self.handlers[pokemonId].getPokemonToRelease(pokemonId, pokemons)
        else:
            return self.defaultHandler.getPokemonToRelease(pokemonId, pokemons)



