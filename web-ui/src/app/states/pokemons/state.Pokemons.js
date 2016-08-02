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

    .run(function (Navigation) {
        Navigation.primary.register("Pokemons", "public.pokemons", 30, 'md md-event-available', 'public.pokemons');
    })

    .controller('PokemonsController', function PokemonsController($scope, $stateParams, Pokemon) {
        $scope.isLoading = true;
        $scope.pokemons = Pokemon.get({ username: $stateParams.username }, function getSuccess(){
            $scope.isLoading = false;
        }, function getError(){
            $mdToast.showSimple('Awww, we failed to load your pokémons :-( Check that web.py is still running, pleeeeease!');
        });
    })
;
