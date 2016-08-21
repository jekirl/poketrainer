angular.module('Poketrainer.Service.SocketEvent', [])
    .factory('SocketEvent', function () {
        return {
            _prefix: "socket:",
            UserList: 'users',
            UserStatus: 'user_status',
            Request: 'pull',
            Data: 'push',
            Join: 'join',
            Leave: 'leave',
            Action: 'action'
        }
    });