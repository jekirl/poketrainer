angular.module('poketrainer', [
	'poketrainer.Module.Templates',

	/** Internal Modules **/
	'Poketrainer.Module.SocketEventEmitter',

	/** Internal Services **/
	'Poketrainer.Service.Navigation',
	'Poketrainer.Service.SocketEvent',
	'Poketrainer.Service.Socket',

	/** States/Routes **/
	'Poketrainer.State.Abstracts',
	'Poketrainer.State.Status',
	'Poketrainer.State.Users',


	/** External Libs **/
	'ui.router',
    'ngMaterial',
    'ngMessages'

	/** Internal Directives **/
	
])

	.config(function pokeTrainerConfig($urlRouterProvider, $locationProvider, $urlMatcherFactoryProvider, $mdThemingProvider) {
		//$locationProvider
		//	.hashPrefix('!')
		//	.html5Mode(false);

		$urlRouterProvider.rule(function ($injector, $location) {
			var path = $location.url().toLowerCase();

			// check to see if the path already has a slash where it should be
			if (path[path.length - 1] === '/' || path.indexOf('/?') > -1) {
				return;
			}

			if (path.indexOf('?') > -1) {
				return path.replace('?', '/?');
			}

			console.log(path);
			return path + '/';
		})
		.otherwise('/');

		$urlMatcherFactoryProvider.strictMode(false);

        $mdThemingProvider.theme('default')
            .primaryPalette('blue')
            .accentPalette('red');

	})

	.run(function pokeTrainerRun ($state, $rootScope) {
		$rootScope.$on('inventory:updated', function(data){
			//console.log("Inventory!! :D ")
		})
	})

;