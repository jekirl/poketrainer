import collections
import importlib

from six import iteritems


def filtered_dict_merge(dct, merge_dct, filtered_key=None):
    for k, v in iteritems(merge_dct):
        if filtered_key and k == filtered_key:
            continue
        if (
            k in dct and isinstance(dct[k], dict) and
            isinstance(merge_dct[k], collections.Mapping)
        ):
            filtered_dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]
    return dct


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
            self._releaseHelper = self.loadReleaseMethod(releaseHelperName, self.config.get('POKEMON_CLEANUP', {}))
        return self._releaseHelper

    def getKlass(self, modulename):
        return getattr(importlib.import_module("poketrainer.release_methods." + modulename.lower()), 'ReleaseMethod')

    def loadReleaseMethod(self, modulename, config):
        klass = self.getKlass(modulename)
        return klass(config)


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

    def getPokemonToRelease(self, pokemonId, pokemons):
        """Goes through the list of all pokemon of a given pokemonId and returns a list of pokemon to transfer

            Args:
                pokemonId   (int): integer pokemon id
                pokemons    (list): list of all the caught pokemon of given pokemon id

            Returns:
                (list, list): first list is pokemon that are slated for transfer, second list is pokemon that are not to keep
        """
        raise NotImplemented("getPokemonToRelease() must be implemented in all transfer helpers")
