angular.module('Poketrainer.State.Status', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider.state('public.status', {
            url: '/status/:username',
            resolve: {
                userData: ['$q', '$stateParams', 'User', function resolveUserData($q, $stateParams, User){
                    var d = $q.defer();

                    User.get({
                        username: $stateParams.username
                    }, function resolveSuccess(userData){
                        d.resolve(userData);
                    }, function resolveError(error){
                        d.reject(error);
                    });

                    return d.promise;
                }]
            },
            controller: 'StatusController',
            templateUrl: 'states/status/status.tpl.html'
        })
        ;
    })

    .run(function (Navigation) {
        Navigation.primary.register("Users", "public.users", 30, 'md md-event-available', 'public.users');
    })

    .controller('StatusController', function StatusController($scope, User, userData) {
        $scope.user = userData;
    })
;
