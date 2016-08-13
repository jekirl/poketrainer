angular.module('Poketrainer.State.Users', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider.state('public.users', {
            url: '/',
            resolve: {
                Users: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveUsers($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var userEventCb = function userEventCb(message) {
                        if(angular.isUndefined(message) || !message.success || !angular.isArray(message.users)){
                            return;
                        }
                        PokeSocket.removeListener(SocketEvent.UserList, userEventCb);
                        d.resolve(message.users);
                    };

                    PokeSocket.on(SocketEvent.UserList, userEventCb);

                    // Emit the event to our socket
                    // after listening for it.
                    // we don't need to since we connect anyway, any issues?
                    // we ened it to get back to the bots-overview?
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
        // we don't need any data from the global scope here... yet?
        //PokeSocket.emit(SocketEvent.Join, {room: 'global'});
        $scope.users = Users;

        var userEventUpdate = function userEventUpdate(event, message) {
            for (var i = 0; i < $scope.users.length; i++) {
                if ($scope.users[i].username == message.username) {
                    $scope.users[i].status = message.status;
                }
            }
        };

        // Make sure to listen for new events
        $scope.$on(SocketEvent._prefix + SocketEvent.UserStatus, userEventUpdate);
    })
;
