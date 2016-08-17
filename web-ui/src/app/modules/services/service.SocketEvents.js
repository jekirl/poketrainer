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
            Transfer: 'transfer',
            Evolve: 'evolve',
            Snipe: 'snipe',
            Start: 'start',
            Stop: 'stop',
            ResetStats: 'reset_stats',
            ReloadAPI: 'reload_api'
        }
    });