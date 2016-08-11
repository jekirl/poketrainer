angular.module('Poketrainer.Service.SocketEvent', [])
    .factory('SocketEvent', function () {
        return {
            _prefix: "socket:",
            UserList: 'connect',
            UserStatus: 'user_status',
            UserData: 'user_data',
            Data: 'push',
            Request: 'pull',
            Join: 'join'
        }
    });