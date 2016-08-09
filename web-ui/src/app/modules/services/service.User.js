angular.module('Poketrainer.Service.User', ['ngResource', 'Poketrainer.Service.Config'])
    .factory('User', ['$resource', 'Config', function ($resource, Config) {
        return $resource(Config.Api + 'player/:username', { username: '@username' } );
    }]);