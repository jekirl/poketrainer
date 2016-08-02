angular.module('Poketrainer.State.Status', [
    'ui.router',
    'uiGmapgoogle-maps',
    'chart.js',
    'easypiechart'
])

    .config(function config($stateProvider, uiGmapGoogleMapApiProvider) {

        uiGmapGoogleMapApiProvider.configure({
            //key: '<MAPS API KEY>',
            v: '3.24',
            libraries: 'weather,geometry,visualization'
        });

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
        $scope.user.xpPercent = Math.floor(($scope.user.experience-$scope.user.prev_level_xp)/($scope.user.next_level_xp-$scope.user.prev_level_xp)*100);
        $scope.user.uniquePokedexPercent = Math.floor($scope.user.unique_pokedex_entries / 151 * 100);
        $scope.user.pokemonInvPercent = Math.floor($scope.user.pokemon.length / $scope.user.pokemon_capacity  * 100);

        $scope.map = { center: { latitude: userData.latitude, longitude: userData.longitude }, zoom: 14 };
        $scope.marker = {
            id: 0,
            coords: {
                latitude: $scope.user.latitude,
                longitude: $scope.user.longitude
            },
            options: {
                label: $scope.user.username
            }
        };

        $scope.expLvlOptions = {
            animate:{
                duration:1000,
                enabled:true
            },
            barColor:'#03A9F4',
            scaleColor:false,
            lineWidth:10,
            lineCap:'circle'
        };

        $scope.uniquePokedexOptions = {
            animate:{
                duration:1000,
                enabled:true
            },
            barColor:'#FFC107',
            scaleColor:false,
            lineWidth:10,
            lineCap:'circle'
        };

        $scope.pokemonInvOptions = {
            animate:{
                duration:1000,
                enabled:true
            },
            barColor:'#009688',
            scaleColor:false,
            lineWidth:10,
            lineCap:'circle'
        };

        $scope.itemsInvOptions = {
            animate:{
                duration:1000,
                enabled:true
            },
            barColor:'#F44336',
            scaleColor:false,
            lineWidth:10,
            lineCap:'circle'
        };

    })
;
