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

    .controller('InventoryController', function StatusController($scope, $stateParams, Inventory) {
        $scope.inventory = Inventory.get({ username: $stateParams.username });
    })
;
