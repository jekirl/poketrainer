angular.module('Poketrainer.Service.Socket', ['btford.socket-io'])
    .factory('PokeSocket', function (socketFactory, $location) {
        var path = $location.url().replace(/\/+$/g, '') + '/socket.io';

        return socketFactory({
            ioSocket: io.connect(
                window.location.protocol + '//' + window.location.host + '/poketrainer',
                {
                    path: path
                }
            )
        });
    });