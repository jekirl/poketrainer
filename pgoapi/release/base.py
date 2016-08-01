import importlib

class ReleaseMethodFactory(object):

    def __init__(self, config):
        """
            Args:
                config  (dict): takes the full apllication config and uses that to setup config for the ReleaseHelpers

        """
        self.config = config
        self._releaseHelper = None

    def getReleaseMethod(self):
        """
            instantiates a properly configured ReleaseMethod implementation
            Returns:
                ReleaseMethod
        """
        if not self._releaseHelper:
            releaseHelperName = self.config.get('POKEMON_CLEANUP', {}).get('RELEASE_METHOD', 'CLASSIC').lower()
            klass = getattr(importlib.import_module("pgoapi.release." + releaseHelperName), 'ReleaseMethod')
            sections = klass.getConfigSections()
            config = self.config.get('POKEMON_CLEANUP', {}).copy()

            for section in sections:
                config.update(self.config.get('POKEMON_CLEANUP', {}).get(section, {}))
            self._releaseHelper = klass(config)
        return self._releaseHelper


class ReleaseMethod(object):
    """"ReleaseHelper are intended to identify pokemon that should be transferred"""

    def __init__(self, config):
        self.processConfig(config)

    def processConfig(self, config):
        """this can be overridden in subclasses if there is any post processing that is needed

            Args:
                config      :config object, at a minimum this should be a dict

        """
        self.config = config

    @staticmethod
    def getConfigSections():
        """this should return either a string for a subsection name in "POKEMON_CLEANUP" section of config or an array/tuple
            of subsection names to apply in order to the base configs in POKEMON_CLEANUP this should effectively be a constant
            for the module

            Returns:
                list|tuple:
        """

        raise NotImplemented("get configSections must be implemented")

    def getPokemonToRelease(self, pokemonId, pokemons):
        """Goes through the list of all pokemon of a given pokemonId and returns a list of pokemon to transfer

            Args:
                pokemonId   (int): integer pokemon id
                pokemons    (list): list of all the caught pokemon of given pokemon id

            Returns:
                (list, list): first list is pokemon that are slated for transfer, second list is pokemon that are not to keep
        """
        raise NotImplemented("getPokemonToRelease() must be implemented in all transfer helpers")


