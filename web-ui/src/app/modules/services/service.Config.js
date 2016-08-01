angular.module('Poketrainer.Service.Config', [])
    .factory('Config', function () {
        return {
            Api: window.location.protocol + "//192.168.1.12:5000/api/"
        };
    });