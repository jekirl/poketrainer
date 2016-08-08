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

    .controller('NavigationController', function NavigationController($rootScope, $scope, $state, $stateParams, $mdSidenav, Navigation, PokeSocket){
        $scope.navigation = Navigation.primary.get();

        
        PokeSocket.on('connection_status', function (data) {
            console.log(data);
        });
        
        PokeSocket.on('connect', function () {
            console.log("connected");
        });

        $scope.params = $state.params;
        $scope.state = $state.current.name;

        $scope.isActiveState = function isActiveState(stateName) {
            var currentStateName = $state.current.name;
            return (currentStateName.indexOf(stateName) >= 0);
        };

        $scope.getUrl = function primaryNavGetUrl(state) {
            return $state.href(state);
        };

        $rootScope.$on('$stateChangeSuccess', function (event, toState, toParams, fromState, fromParams) {
            $scope.navigation = Navigation.sidebar.get(toState.name);
            $scope.state = toState.name;
            $scope.params = toParams;
        });

    })

    .controller('HeaderController', function HeaderController($rootScope, $scope, $state, $mdSidenav, Navigation){
        $scope.navigation = Navigation.primary.get();
        $scope.state = $state.current.name;

        $rootScope.$on('$stateChangeSuccess', function (event, toState, toParams, fromState, fromParams) {
            $scope.navigation = Navigation.sidebar.get(toState.name);
            $scope.state = toState.name;
        });

        $scope.toggleSidebar = function () {
            $mdSidenav('left').toggle();
        }
    })

;