angular.module('Poketrainer.State.Status', [
    'ui.router',
    'uiGmapgoogle-maps',
    'chart.js',
    'easypiechart',
    'datatables',
    'ui-leaflet',
    'nemLogging',
	'xeditable'
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
                        if(angular.isUndefined(message) || message.type != 'location') {
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
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
                        if(angular.isUndefined(message) || message.type != 'inventory'){
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
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
                        if(angular.isUndefined(message) || message.type != 'player'){
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
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
                        if(angular.isUndefined(message) || message.type != 'player_stats'){
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
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
                        if(angular.isUndefined(message) || message.type != 'pokemon'){
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
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
                fortsData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveFortsData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var fortsDataCb = function fortsDataCb(message) {
                        if(angular.isUndefined(message) || message.type != 'forts'){
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
                            return;
                        }
                        d.resolve(angular.fromJson(message.data));
                    };

                    PokeSocket.on(SocketEvent.Request, fortsDataCb);
                    PokeSocket.emit(SocketEvent.Request, {
                        username: $stateParams.username,
                        types: ['forts']
                    });

                    return d.promise;
                }],
                attacksData: ['$q', '$stateParams', 'PokeSocket', 'SocketEvent', function resolveAttacksData($q, $stateParams, PokeSocket, SocketEvent){
                    var d = $q.defer();

                    var attacksDataCb = function attacksDataCb(message) {
                        if(angular.isUndefined(message) || message.type != 'attacks'){
                            return;
                        }
                        if (!message.success) {
                            d.reject('offline');
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

    .controller('DashboardController', function DashboardController($rootScope, $scope, $stateParams, $mdToast, $q, PokeSocket, leafletData,
                                                                    UserList, locationData, inventoryData, playerData, playerStatsData,
                                                                    pokemonData, fortsData, attacksData, SocketEvent, DTOptionsBuilder,
                                                                    editableOptions, editableThemes) {
        UserList.setCurrent($stateParams.username);
        $rootScope.$broadcast("currentUser_:changed");

        editableThemes.bs3.inputClass = 'input-sm';
        editableThemes.bs3.buttonsClass = 'btn-sm';
        editableOptions.theme = 'bs3';

        var userEventUpdate = function userEventUpdate(event, message) {
            if ($stateParams.username == message.username) {
                if (message.status == 'offline') {
                    $state.go('public.users');
                }
            }
        };
        $scope.$on(SocketEvent._prefix + SocketEvent.UserStatus, userEventUpdate);

        $scope.$on("$destroy", function(){
            PokeSocket.emit(SocketEvent.Leave, {room: $stateParams.username});
        });
        // Join specific user room
        PokeSocket.emit(SocketEvent.Join, {room: $stateParams.username});

        /** TRANSFER **/
        var transfer_p_id;
        var transferCb = function transferCb(message) {
            $scope.evolve_disabled = false;
            $scope.transfer_disabled = false;
            if (message.success) {
                for(var i=$scope.pokemon.length-1; i>=0; i--) {
                    if ($scope.pokemon[i].id == transfer_p_id) {
                        $scope.pokemon.splice(i,1);
                        break;
                    }
                }
            }
            transfer_p_id = 0;
            PokeSocket.removeListener('release_pokemon_by_id', transferCb);
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(3000)
            );
        };
        $scope.transfer_disabled = false;
        $scope.transfer = function(p_id) {
            transfer_p_id = p_id;
            $scope.evolve_disabled = true;
            $scope.transfer_disabled = true;
            PokeSocket.on('release_pokemon_by_id', transferCb);
            PokeSocket.emit(SocketEvent.Action, {username: $stateParams.username, action: 'release_pokemon_by_id', params: [p_id]});
        };

        /** EVOLVE **/
        var evolveCb = function evolveCb(message) {
            $scope.evolve_disabled = false;
            $scope.transfer_disabled = false;
            PokeSocket.removeListener('evolve_pokemon_by_id', evolveCb);
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(3000)
            );
        };
        $scope.evolve_disabled = false;
        $scope.evolve = function(p_id) {
            $scope.evolve_disabled = true;
            $scope.transfer_disabled = true;
            PokeSocket.on('evolve_pokemon_by_id', evolveCb);
            PokeSocket.emit(SocketEvent.Action, {username: $stateParams.username, action: 'evolve_pokemon_by_id', params: [p_id]});
        };

        /** SNIPE **/
        var snipedCb = function snipedCb(message) {
            //message.success;
            $scope.snipe_disabled = false;
            PokeSocket.removeListener('snipe_pokemon', snipedCb);
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(3000)
            );
        };
        $scope.snipe_coords = '';
        $scope.snipe_disabled = false;
        $scope.snipe_auto = false; // not implemented
        $scope.snipe = function(snipe_coords) {
            $scope.snipe_disabled = true;
            PokeSocket.on('snipe_pokemon', snipedCb);
            PokeSocket.emit(SocketEvent.Action, {username: $stateParams.username, action: 'snipe_pokemon', latlng: snipe_coords});
        };

        /** Upgrade pokemon **/
        var upgrade_pkm;
        var upgradeCb = function upgradeCb(message) {
            $scope.upgrade_disabled = false;
            PokeSocket.removeListener('upgrade_pokemon_by_id', upgradeCb);
            if (message.success) {
                $scope.inventory.pokemon_candy[upgrade_pkm.family_id] -= upgrade_pkm.candy_needed_to_upgrade;
                $scope.player.currencies[1].amount -= upgrade_pkm.dust_needed_to_upgrade;
                for(var i=$scope.pokemon.length-1; i>=0; i--) {
                    if ($scope.pokemon[i].id == message.upgraded_pokemon.id) {
                        $scope.pokemon[i] = message.upgraded_pokemon;
                        break;
                    }
                }
            }
            upgrade_pkm = {};
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(3000)
            );
        };
        $scope.upgrade_disabled = false;
        $scope.upgrade = function(pkm) {
            upgrade_pkm = pkm;
            $scope.upgrade_disabled = true;
            PokeSocket.on('upgrade_pokemon_by_id', upgradeCb);
            PokeSocket.emit(SocketEvent.Action, {username: $stateParams.username, action: 'upgrade_pokemon_by_id', params: [pkm.id]});
        };

        /** Nickname **/
        $scope.nick_change_disabled = false;
        $scope.nick_change = function(p_id, nickname) {
            var d = $q.defer();

            var nick_changeCb = function nick_changeCb(message) {
                $scope.nick_change_disabled = false;
                PokeSocket.removeListener('nickname_pokemon_by_id', nick_changeCb);
                if (message.success) {
                    d.resolve(true);
                    // this is usually not needed, but in case the pokemon list is messed we do it anyway to be sure
                    for(var i=$scope.pokemon.length-1; i>=0; i--) {
                        if ($scope.pokemon[i].id == p_id) {
                            $scope.pokemon[i].name = nickname;
                            break;
                        }
                    }
                } else {
                    d.reject(false);
                }
                $mdToast.show(
                    $mdToast.simple()
                        .textContent(message.message)
                        .position('top center')
                        .hideDelay(3000)
                );
            };

            $scope.nick_change_disabled = true;
            PokeSocket.on('nickname_pokemon_by_id', nick_changeCb);
            PokeSocket.emit(SocketEvent.Action, {username: $stateParams.username, action: 'nickname_pokemon_by_id', params: [p_id, nickname]});

            return d.promise;
        };


        /** Favorite **/
        var set_favorite_p_id;
        var set_favorite_favorite;
        var set_favoriteCb = function set_favoriteCb(message) {
            $scope.set_favorite_disabled = false;
            PokeSocket.removeListener('set_favorite_pokemon_by_id', set_favoriteCb);
            if (message.success) {
                for(var i=$scope.pokemon.length-1; i>=0; i--) {
                    if ($scope.pokemon[i].id == set_favorite_p_id) {
                        $scope.pokemon[i].is_favorite = set_favorite_favorite;
                        break;
                    }
                }
            }
            set_favorite_p_id = 0;
            set_favorite_favorite = false;
            $mdToast.show(
                $mdToast.simple()
                    .textContent(message.message)
                    .position('top center')
                    .hideDelay(3000)
            );
        };
        $scope.set_favorite_disabled = false;
        $scope.set_favorite = function(p_id, favorite) {
            set_favorite_p_id = p_id;
            set_favorite_favorite = favorite;
            $scope.set_favorite_disabled = true;
            PokeSocket.on('set_favorite_pokemon_by_id', set_favoriteCb);
            PokeSocket.emit(SocketEvent.Action, {username: $stateParams.username, action: 'set_favorite_pokemon_by_id', params: [p_id, favorite]});
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

        $scope.$on('pokemon:evolved', function(event, data) {
            var pokemon_old = data.old;
            var pokemon_new = data.new;
            for(var i=$scope.pokemon.length-1; i>=0; i--) {
                if ($scope.pokemon[i].id == pokemon_old.id) {
                    $scope.pokemon.splice(i,1);
                }
            }
            $scope.pokemon.push(pokemon_new);
            $mdToast.show(
                $mdToast.simple()
                    .textContent('Evolved: ' + pokemon_old.name + ' to ' + pokemon_new.name +
                        ' (IV: ' + Math.floor(pokemon_new.iv) + ' | CP: ' + pokemon_new.cp + ')')
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
            if (positionUpdates % 1 == 0) {
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

        var markers = {};
        for (var i = 0; i < fortsData.length; i++) {
            var fort = fortsData[i];
            if (fort.type == 1 && (fort.enabled || fort.lure_info)) {
                markers['fort_' + i] = {
                    lat: fort.latitude,
                    lng: fort.longitude,
                    message: fort.latitude + ', ' + fort.longitude,
                    icon: {
                        iconUrl: 'assets/images/fort.png',
                        iconSize: [30, 32],
                        iconAnchor: [16, 31]
                    }
                }
            } else {
                // GYM, we could display them aswell
            }
        }
        markers['bot'] = {
            lat: locationData[0],
            lng: locationData[1],
            message: $scope.player.username,
            focus: true,
            draggable: false
        };
        $scope.markers = markers;
        
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
            .withOption('order', [[ 0, "desc" ]])
            .withOption('stateSave', true);
            /*.withOption('scrollY', '75vh')
            .withOption('scrollX', true);
            .withOption('paging', true)*/

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
