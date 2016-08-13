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

        $stateProvider.state('public.dashboard', {
            url: '/dashboard/:username',
            resolve: {
                locationData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveLocationData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var locationDataCb = function locationDataCb(message) {
                        if(angular.isUndefined(message) || !message.success || message.type != 'location'){
                            return;
                        }
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
            controller: 'DashboardController',
            templateUrl: 'states/dashboard/dashboard.tpl.html'
        })
        ;
    })

    .run(function (Navigation) {
        Navigation.primary.register("Users", "public.users", 30, 'md md-event-available', 'public.users');
    })

    .controller('DashboardController', function DashboardController($scope, $stateParams, $mdToast, PokeSocket, leafletData,
                                                                    locationData, inventoryData, playerData, playerStatsData,
                                                                    pokemonData, attacksData, SocketEvent, DTOptionsBuilder) {

        // Join specific user room
        // TODO: we should leave the room when we change the page
        PokeSocket.emit(SocketEvent.Join, {room: $stateParams.username});
        //console.log("Joined! ", SocketEvent.Join, $stateParams.username);

        var transfer_p_id;
        var transferCb = function transferCb(message) {
            //message.success;
            $scope.transfer_disabled = false;
            if (message.success) {
                for(var i=$scope.pokemon.length-1; i>=0; i--) {
                    if ($scope.pokemon[i].id == transfer_p_id) {
                        $scope.pokemon.splice(i,1);
                    }
                }
            }
            transfer_p_id = 0;
            PokeSocket.removeListener(SocketEvent.Transfer, transferCb);
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(1000)
            );
        };
        $scope.transfer_disabled = false;
        $scope.transfer = function(p_id) {
            transfer_p_id = p_id;
            $scope.transfer_disabled = true;
            PokeSocket.on(SocketEvent.Transfer, transferCb);
            PokeSocket.emit(SocketEvent.Transfer, {username: $stateParams.username, p_id: p_id});
        };

        var snipedCb = function snipedCb(message) {
            //message.success;
            $scope.snipe_disabled = false;
            PokeSocket.removeListener(SocketEvent.Snipe, snipedCb);
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(1000)
            );
        };
        $scope.snipe_coords = '';
        $scope.snipe_disabled = false;
        $scope.snipe_auto = false; // not implemented
        $scope.snipe = function(snipe_coords) {
            $scope.snipe_disabled = true;
            PokeSocket.on(SocketEvent.Snipe, snipedCb);
            PokeSocket.emit(SocketEvent.Snipe, {username: $stateParams.username, latlng: snipe_coords});
        };
        
        $scope.$on('inventory:updated', function(event, data) { 
            $scope.inventory = data;
            updatePercentages();
        });

        $scope.$on('player_stats:updated', function(event, data) {
            $scope.playerStats = data;
            updatePercentages();
        });

        $scope.$on('player:updated', function(event, data) {
            $scope.player = data;
            updatePercentages();
        });

        // this makes the pokemon table go crazy for a bit
        // we insert / delete based on other evens, so it _should_ be accurate anyway
        /*$scope.$on('caught_pokemon:updated', function(event, data) {
            $scope.pokemon = data;
        });*/
 
        $scope.$on('pokemon:caught', function(event, data) {
            var pokemon = data;
            //pokemon.creation_time_ms = new Date().getTime();
            $scope.pokemon.push(pokemon);
            updatePercentages();
            $mdToast.show(
                $mdToast.simple()
                    .textContent('Caught: ' + pokemon.name + ' (IV: ' + Math.floor(pokemon.iv) + ' | CP: ' + pokemon.cp + ')')
                    .position('top center')
                    .hideDelay(3000)
            );
        });

        $scope.$on('pokemon:released', function(event, data) {
            var pokemon = data;
            for(var i=$scope.pokemon.length-1; i>=0; i--) {
                if ($scope.pokemon[i].id == pokemon.id) {
                    $scope.pokemon.splice(i,1);
                }
            }
            updatePercentages();
            $mdToast.show(
                $mdToast.simple()
                    .textContent('Released: ' + pokemon.name + ' (IV: ' + Math.floor(pokemon.iv) + ' | CP: ' + pokemon.cp + ')')
                    .position('top center')
                    .hideDelay(3000)
            );
        });

        $scope.$on('fort:spun', function(event, data) {
            $mdToast.show(
                $mdToast.simple()
                    .textContent('Fort spun, reward: ' + data.reward)
                    .position('top center')
                    .hideDelay(3000)
            );
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

        var updatePercentages = function updatePercentages() {
            $scope.playerStats.xpPercent = Math.floor(
                ($scope.playerStats.experience - $scope.playerStats.prev_level_xp)
                /($scope.playerStats.next_level_xp - $scope.playerStats.prev_level_xp)
                *100
            );
            $scope.playerStats.uniquePokedexPercent = Math.floor($scope.playerStats.unique_pokedex_entries / 151 * 100);
            $scope.playerStats.pokemonInvPercent = Math.floor($scope.pokemon.length / $scope.player.max_pokemon_storage  * 100);
            $scope.playerStats.itemsInvPercent = Math.floor($scope.inventory.item_count / $scope.player.max_item_storage  * 100);
        };
        updatePercentages();

        // very dirty fix to make the leaflet map load fullscreen
        $scope.$on('$viewContentLoaded', function() {
            leafletData.getMap().then(function(map) {
                setTimeout(function(){ map.invalidateSize(); }, 3000);
            });
        });
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
        };
        
        $scope.paths = {
            main: {
                color: '#F44336',
                weight: 4,
                latlngs: [
                    { lat: locationData[0], lng: locationData[1] }
                ]
            }
        };
        
        $scope.pokemonDataTableOptions = DTOptionsBuilder.newOptions()
            .withOption('order', [[ 0, "desc" ]]);
            /*.withOption('paging', true)
            .withOption('scrollY', '75vh')
            .withOption('scrollX', true);*/

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
