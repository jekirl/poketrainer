angular.module('Poketrainer.Service.Socket', ['btford.socket-io'])
    .factory('PokeSocket', ['socketFactory', function (socketFactory) {
        return socketFactory({
            ioSocket: io.connect(window.location.protocol + "//" + window.location.hostname + ":5000/api")
        });
    }]);