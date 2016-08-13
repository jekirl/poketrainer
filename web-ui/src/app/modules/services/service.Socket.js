angular.module('Poketrainer.Service.Socket', ['btford.socket-io'])
    .factory('PokeSocket', function (socketFactory, $location) {
        var path = window.location.pathname.replace(/\/+$/g, '') + '/socket.io';
        //var path = '/socket.io';

        return socketFactory({
            ioSocket: io.connect(
                window.location.protocol + '//' + window.location.host + '/poketrainer',
                {
                    path: path
                }
            )
        });
    });