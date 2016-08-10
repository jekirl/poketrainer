angular.module('Poketrainer.State.Users', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider.state('public.users', {
            url: '/',
            resolve: {
                Users: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveUsers($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    PokeSocket.once(SocketEvent.UserList, function userEventCb(message) {
                        if(angular.isUndefined(message) || !message.success || !angular.isArray(message.users)){
                            return;
                        }
                        d.resolve(message.users);
                    });

                    // Emit the event to our socket
                    // after listening for it.
                    PokeSocket.emit(SocketEvent.UserList);

                    return d.promise;
                }]
            },
            controller: 'UsersController',
            templateUrl: 'states/users/users.tpl.html'
        })
        ;
    })

    .run(function (Navigation) {
        Navigation.primary.register("Users", "public.users", 30, 'md md-event-available', 'public.users');
    })

    .controller('UsersController', function UsersController($scope, Users, PokeSocket, SocketEvent) {
        PokeSocket.emit(SocketEvent.Join, {room: 'global'});
        $scope.users = Users;

        var userEventCb = function userEventCb(message) {
            if(angular.isUndefined(message) || !message.success || !angular.isArray(message.users)){
                return;
            }

            $scope.users = message.users;
        };

        // Make sure to listen for new events
        $scope.$on(SocketEvent._prefix + SocketEvent.UserList, userEventCb);
    })
;
