from __future__ import absolute_import

import importlib


class WalkerFactory(object):

    def __init__(self):
        self._walker = None

    def get_walker(self, config, parent):
        """
            instantiates a properly configured ReleaseMethod implementation
            Returns:
                ReleaseMethod
        """
        if not self._walker:
            walker_name = 'default'
            if config.experimental and config.spin_all_forts:
                walker_name = 'spin_all_forts'
            parent.log.info('choosing walker: %s', walker_name)
            klass = getattr(importlib.import_module("poketrainer.walker." + walker_name.lower()), 'Walker')
            self._walker = klass(config, parent)
        return self._walker


class Walker(object):
    """"ReleaseHelper are intended to identify pokemon that should be transferred"""

    def __init__(self, config, parent):
        raise NotImplemented("__init__() must be implemented in all walkers")

    def next_step(self):
        """Should always return one step, not exceeding the step_size limit

            Returns:
                step      :array|dict: {'lat': latitude, 'long': longitude}

        """
        raise NotImplemented("next_step() must be implemented in all walkers")

    def walk_back_to_origin(self, origin):
        """should create a new path back to the origin position

            Args:
                origin    :array: (latitude, longitude)

        """
        raise NotImplemented("walk_back_to_origin() must be implemented in all walkers")
