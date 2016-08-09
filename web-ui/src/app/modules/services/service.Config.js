angular.module('Poketrainer.Service.Config', [])
    .factory('Config', function () {
        return {
            Api: window.location.protocol + "//" + window.location.hostname + ":5000/api/"
        };
    });