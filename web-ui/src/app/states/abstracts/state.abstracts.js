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

    .controller('HeaderController', function HeaderController($rootScope, $scope, $state, Navigation){
        $scope.navigation = Navigation.primary.get();
        $scope.state = $state.current.name;

        $rootScope.$on('$stateChangeSuccess', function (event, toState, toParams, fromState, fromParams) {
            $scope.state = toState.name;
        });
    })

;