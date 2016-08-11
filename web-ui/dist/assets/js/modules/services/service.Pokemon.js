angular.module('Poketrainer.Service.Pokemon', ['ngResource', 'Poketrainer.Service.Config'])
    .factory('Pokemon', ['$resource', 'Config', function ($resource, Config) {
        return $resource(Config.Api + 'player/:username/pokemon');
    }]);