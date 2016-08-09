angular.module('Poketrainer.Service.Config', [])
    .factory('Config', function () {
        return {
            Api: window.location.protocol + "//" + window.location.host + window.location.pathname.replace(/\/+$/g, '') + "/api/"
        };
    });