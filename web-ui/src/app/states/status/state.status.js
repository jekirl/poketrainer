angular.module('Poketrainer.State.Status', [
    'ui.router',
    'uiGmapgoogle-maps',
    'chart.js',
    'easypiechart',
    'datatables',
    'ui-leaflet',
    'nemLogging'
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
                locationData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveLocationData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var locationDataCb = function locationDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'location'){
                            return;
                        }
                        console.log('received: ', message.type, ': ', message.data);
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, locationDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['location']
                    });

                    return d.promise;
                }],
                inventoryData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveInventoryData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var inventoryDataCb = function inventoryDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'inventory'){
                            return;
                        }
                        console.log('received: ', message.type, ': ', message.data);
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, inventoryDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['inventory']
                    });

                    return d.promise;
                }],
                playerData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolvePlayerData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var playerDataCb = function playerDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'player'){
                            return;
                        }
                        console.log('received: ', message.type, ': ', message.data);
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, playerDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['player']
                    });

                    return d.promise;
                }],
                playerStatsData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolvePlayerStatsData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var playerStatsDataCb = function playerStatsDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'player_stats'){
                            return;
                        }
                        console.log('received: ', message.type, ': ', message.data);
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, playerStatsDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['player_stats']
                    });

                    return d.promise;
                }],
                pokemonData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolvePokemonData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var pokemonDataCb = function pokemonDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'pokemon'){
                            return;
                        }
                        console.log('received: ', message.type, ': ', message.data);
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, pokemonDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['pokemon']
                    });

                    return d.promise;
                }],
                attacksData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveAttacksData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var attacksDataCb = function attacksDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'attacks'){
                            return;
                        }
                        console.log('received: ', message.type, ': ', message.data);
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, attacksDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['attacks']
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

    .controller('StatusController', function StatusController($scope, $stateParams, PokeSocket,
                                                              locationData, inventoryData, playerData, playerStatsData,
                                                              pokemonData, attacksData, SocketEvent) {
        // Debug only! Remove this after everything works
        PokeSocket.on(SocketEvent.Join, function (data){
            console.log("Join response: ", data);
        });

        // Join specific user room
        PokeSocket.emit(SocketEvent.Join, {room: $stateParams.username});
        console.log("Joined! ", SocketEvent.Join, $stateParams.username);

        //PokeSocket.on('status', function (data) {
        //    console.log(data);
        //});
        
        $scope.$on('inventory:updated', function(event, data) { 
            $scope.inventory = data;
        });
 
        var positionUpdates = 0;
        $scope.$on('position:update', function(event, data) {
            positionUpdates++;
            if (positionUpdates % 5 == 0) {
                $scope.markers.bot.lat = data[0];
                $scope.markers.bot.lng = data[1];
                var newLocation = {lat: data[0], lng: data[1]};
                $scope.paths.main.latlngs.push(newLocation);
            }
        });

        $scope.player = playerData;
        $scope.playerStats = playerStatsData;
        $scope.inventory = inventoryData;
        $scope.pokemon = pokemonData;
        $scope.attacks = attacksData;


        $scope.user = {};

        $scope.playerStats.xpPercent = Math.floor(
            ($scope.playerStats.experience - $scope.playerStats.prev_level_xp)
            /($scope.playerStats.next_level_xp - $scope.playerStats.prev_level_xp)
            *100
        );
        $scope.playerStats.uniquePokedexPercent = Math.floor($scope.playerStats.unique_pokedex_entries / 151 * 100);
        $scope.playerStats.pokemonInvPercent = Math.floor($scope.pokemon.length / $scope.player.max_pokemon_storage  * 100);
        $scope.playerStats.itemsInvPercent = Math.floor($scope.inventory.item_count / $scope.player.max_item_storage  * 100);


        /*$scope.user.xpPercent = Math.floor($scope.user.level_xp/$scope.user.goal_xp*100);
        $scope.user.uniquePokedexPercent = Math.floor($scope.user.unique_pokedex_entries / 151 * 100);
        $scope.user.pokemonInvPercent = Math.floor($scope.user.pokemon.length / $scope.user.pokemon_capacity  * 100);*/

        $scope.map = { center: {
                            lat: locationData[0],
                            lng: locationData[1],
                            zoom: 15
                        }
                     };
        
        $scope.markers = {
            bot: {
                lat: locationData[0],
                lng: locationData[1],
                message: $scope.player.username,
                focus: true,
                draggable: false
            }
        }
        
        $scope.paths = {
            main: {
                color: '#F44336',
                weight: 4,
                latlngs: [
                    { lat: locationData[0], lng: locationData[1] }
                ],
            }
        }
        
        

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
