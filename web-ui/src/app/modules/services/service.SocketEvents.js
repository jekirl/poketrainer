angular.module('Poketrainer.Service.SocketEvent', [])
    .factory('SocketEvent', function () {
        return {
            _prefix: "socket:",
            UserList: 'connect',
            UserStatus: 'status',
            Data: 'push',
            Join: 'join'
        }
    });