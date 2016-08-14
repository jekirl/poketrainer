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

			return path + '/';
		})
		.otherwise('/');

		$urlMatcherFactoryProvider.strictMode(false);

        $mdThemingProvider.theme('default')
            .primaryPalette('blue')
            .accentPalette('red');

	})

	.run(function pokeTrainerRun ($state, $rootScope, $document) {
		$rootScope.$on('inventory:updated', function(event, data){
			//console.log("Inventory!! :D ")
		});
		$rootScope.$on('$stateChangeStart', function(){
			$document.find('.screen-loading-overlay').removeClass('hidden');
		});
		$rootScope.$on('$stateChangeSuccess', function(){
			$document.find('.screen-loading-overlay').addClass('hidden');
		});
		$rootScope.$on('$stateChangeError', function (event, toState, toParams, fromState, fromParams, error) {
			if (error === "offline") {
				$state.go("public.users");
				$document.find('.screen-loading-overlay').removeClass('hidden');
			}
		});
	})

;