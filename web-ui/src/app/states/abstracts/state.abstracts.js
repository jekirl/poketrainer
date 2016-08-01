angular.module('Poketrainer.State.Abstracts', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider
            .state('public', {
                abstract: true,
                views: {
                    "navigation": {
                        templateUrl: 'states/abstracts/navigation.tpl.html',
                        controller: 'NavigationController'
                    },
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

    .controller('NavigationController', function NavigationController($scope, $state, Navigation){

        $scope.navigation = Navigation.primary.get();

        $scope.isActiveState = function isActiveState(stateName) {
            var currentStateName = $state.current.name;
            return (currentStateName.indexOf(stateName) >= 0);
        };

        $scope.getUrl = function primaryNavGetUrl(state) {
            return $state.href(state);
        };
    })

    .controller('HeaderController', function HeaderController($scope){

    })

;