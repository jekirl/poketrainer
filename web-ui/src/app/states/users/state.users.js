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

                    var userEventUpdate = function userEventUpdate(message) {
                        console.log('got: ', message);
                    };


                    PokeSocket.on(SocketEvent.UserList, userEventCb);
                    PokeSocket.on(SocketEvent.UserStatus, userEventUpdate);

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

        var userEventUpdate = function userEventUpdate(message) {
            // for some reason this event will not contain the actual emitted data?
            console.log(message);
        };

        // Make sure to listen for new events
        $scope.$on(SocketEvent._prefix + SocketEvent.UserList, userEventCb);
        $scope.$on(SocketEvent._prefix + SocketEvent.UserStatus, userEventUpdate);
    })
;
