angular.module('Poketrainer.State.Inventory', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider.state('public.inventory', {
            url: '/inventory/:username',
            controller: 'InventoryController',
            templateUrl: 'states/inventory/inventory.tpl.html'
        })
        ;
    })

    .controller('InventoryController', function StatusController($scope, $stateParams, Inventory, $mdToast) {
        $scope.isLoading = true;
        $scope.inventory = Inventory.get({ username: $stateParams.username }, function getSuccess(){
            $scope.isLoading = false;
        }, function getError(){
            $mdToast.showSimple('Awww, we failed to load your inventory :-( Check that web.py is still running, pleeeeease!');
        });
    })
;
