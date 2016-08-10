angular.module('Poketrainer.Service.Socket', ['btford.socket-io'])
    .factory('PokeSocket', function (socketFactory, $location) {
        console.log("Returning a socket!");

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