angular.module('Poketrainer.State.Pokemons', [
    'ui.router'
])

    .config(function config($stateProvider) {
        $stateProvider.state('public.pokemons', {
            url: '/pokemons/:username',
            controller: 'PokemonsController',
            templateUrl: 'states/pokemons/pokemons.tpl.html'
        })
        ;
    })

    .controller('PokemonsController', function PokemonsController($scope, $stateParams, Pokemon) {
        $scope.pokemons = Pokemon.get({ username: $stateParams.username });
    })
;
