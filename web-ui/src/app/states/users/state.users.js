angular.module('Poketrainer.State.Users', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider.state('public.users', {
            url: '/',
            resolve: {
                Users: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', 'UserList', function resolveUsers($q, $stateParams, PokeSocket, SocketEvent, UserList){
                    var d = $q.defer();

                    var userEventCb = function userEventCb(message) {
                        if(angular.isUndefined(message) || !message.success || !angular.isArray(message.users)){
                            return;
                        }
                        PokeSocket.removeListener(SocketEvent.UserList, userEventCb);
                        UserList.set(message.users);
                        d.resolve();
                    };

                    PokeSocket.on(SocketEvent.UserList, userEventCb);

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

    .controller('UsersController', function UsersController($scope, UserList, PokeSocket, SocketEvent) {
        // we don't need any data from the global scope here... yet?
        //PokeSocket.emit(SocketEvent.Join, {room: 'global'});
        $scope.users = UserList.get();
        UserList.setCurrent('');

        var userEventUpdate = function userEventUpdate(event, user) {
            $scope.users = UserList.update(user);
        };

        // Make sure to listen for new events
        $scope.$on(SocketEvent._prefix + SocketEvent.UserStatus, userEventUpdate);
    })
;
