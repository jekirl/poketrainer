angular.module('Poketrainer.Service.SocketEvent', [])
    .factory('SocketEvent', function () {
        return {
            _prefix: "socket:",
            UserList: 'connect',
            UserStatus: 'user_status',
            Request: 'pull',
            Data: 'push',
            Join: 'join'
        }
    });