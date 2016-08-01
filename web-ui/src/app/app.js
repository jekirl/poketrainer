angular.module('poketrainer', [
	'poketrainer.Module.Templates',

	/** Internal Modules **/

	/** Internal Services **/
	'Poketrainer.Service.Config',
	'Poketrainer.Service.Navigation',
	'Poketrainer.Service.User',

	/** States/Routes **/
	'Poketrainer.State.Abstracts',
	'Poketrainer.State.Users',
    

	/** External Libs **/
	'ui.router',
    'ngMaterial',
    'ngMessages',
    'ngMdIcons'

	/** Internal Directives **/
	
])

	.config(function pokeTrainerConfig($urlRouterProvider, $locationProvider, $urlMatcherFactoryProvider, $mdThemingProvider) {
		$locationProvider
			.hashPrefix('!')
			.html5Mode(true);

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

	.run(function pokeTrainerRun ($state) {

	})

;