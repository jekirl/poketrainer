angular.module('Poketrainer.Service.Config', [])
    .factory('Config', function () {
        return {
            Api: window.location.protocol + "//" + window.location.host + ":5000/api/"
        };
    });