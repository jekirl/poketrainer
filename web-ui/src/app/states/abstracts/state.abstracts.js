angular.module('Poketrainer.State.Abstracts', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider
            .state('public', {
                abstract: true,
                views: {
                    "header": {
                        templateUrl: 'states/abstracts/header.tpl.html',
                        controller: 'HeaderController'
                    },
                    "content": {
                        template: '<ui-view/>'
                    }
                }
            })
        ;
    })

    .controller('HeaderController', function HeaderController($rootScope, $scope, $state, $stateParams, SocketEvent, PokeSocket, Navigation, UserList){
        $scope.navigation = Navigation.primary.get();
        $scope.state = $state.current.name;
        $scope.user = UserList.getCurrent();

        $scope.reload_api = function() {
            PokeSocket.emit(SocketEvent.ReloadAPI, {username: $scope.user.username});
        };

        $scope.reset_stats = function() {
            PokeSocket.emit(SocketEvent.ResetStats, {username: $scope.user.username});
        };

        $scope.stop_bot = function() {
            PokeSocket.emit(SocketEvent.Stop, {username: $scope.user.username});
        };

        $scope.start_bot = function() {
            PokeSocket.emit(SocketEvent.Start, {username: $scope.user.username});
        };

        // Make sure to listen for new events
        $scope.$on(SocketEvent._prefix + SocketEvent.UserStatus, function(event, user) {
            UserList.update(user);
            $scope.user = UserList.getCurrent();
        });

        $rootScope.$on('currentUser_:changed', function () {
            $scope.user = UserList.getCurrent();
        });

        $rootScope.$on('$stateChangeSuccess', function (event, toState, toParams, fromState, fromParams) {
            $scope.state = toState.name;
        });

        var userEventCb = function userEventCb(message) {
            if(angular.isUndefined(message) || !message.success || !angular.isArray(message.users)){
                return;
            }
            PokeSocket.removeListener(SocketEvent.UserList, userEventCb);
            UserList.set(message.users);
            $scope.user = UserList.getCurrent();
        };

        if ($scope.state !== 'public.users') {
            PokeSocket.on(SocketEvent.UserList, userEventCb);

            PokeSocket.emit(SocketEvent.UserList);
        }
    })

;