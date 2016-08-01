angular.module('Poketrainer.Service.Inventory', ['ngResource', 'Poketrainer.Service.Config'])
    .factory('Inventory', ['$resource', 'Config', function ($resource, Config) {
        return $resource(Config.Api + 'player/:username/inventory');
    }]);