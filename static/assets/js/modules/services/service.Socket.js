angular.module('Poketrainer.Service.Socket', ['btford.socket-io'])
    .factory('PokeSocket', ['socketFactory', function (socketFactory) {
        return socketFactory({
            ioSocket: io.connect(window.location.protocol + "//" + window.location.host + window.location.pathname + "/api")
        });
    }]);