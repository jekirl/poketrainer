var Config = {
	/** COMMON **/
	Api: window.location.protocol + "//api." + window.location.host + "/v1/",
	BrainTreePublicKey: "MIIBCgKCAQEAvUbqiTd5rvMR6PQPCsV6J/1Z5mnPJ3srxwcUnTqpyybm/8reJPF3+qYTwjglwMEsfW+zMRC5GxkIoauqwvoZqmQRhn6BqcnU6RTqLg6A56/ewI4E8aG/ceSus9kW2xoK5QBb40/S6fox+ySocqGcRU8O6FV5iXE7JDY1hKHQzosqNCuypi4df+TfFouQfuHwjHgaV9HhdJ7Vr1hd79SsZ8RvVXC2+sydua1NZCpwqA4GPmRl5VFKh1xYIoFnwjAimc4IcKyKIX8DZSHDDx7zVtsquVkiq81O4kvusGnRsy+rPCA8jhaNRSPZmSARTQ+y5N9Wmznkr6LhaBrv1tFYtQIDAQAB",
	EnableBooking: true,
    MockupPath: '/assets/js/mockups/'
};

/** DGDA ANGULAR **/
angular.module('dgda', [
	'dgda.Module.Templates',

	/** Internal Modules **/
	'dgda.analytics',
	'dgda.meta',
	'dgda.module.UiUtils',
	'dgda.filter.toTrustedHtml',
	'dgda.filter.formatCurrency',
	'dgda.filter.personalMessageLength',
	'dgda.filter.variantPriceGroup',

	/** States/Routes **/
    'dgda.state.Abstracts',
    'dgda.state.Products',
	'dgda.state.Product',
	'dgda.state.Checkout.v3',
	'dgda.state.CustomerService',
	'dgda.state.Booking',
	'dgda.state.EaseBooking',
	'dgda.state.Error.404',
	'dgda.state.Review',
    'dgda.state.Affiliate',
    'dgda.state.AboutUs',
    'dgda.state.Supplier',
    'dgda.state.GiftExchange',
	'dgda.state.Refund',
	'dgda.state.Content',

	/** External Libs **/
	'ui.router',
	'infinite-scroll',
	'truncate',
	'ivpusic.cookie',
	'cgBusy',
    'LocalStorageModule',
    'angular.filter',
    'dcbImgFallback',
    'angular-packery',

    /** Internal Services **/
	'dgda.service.Product',
	'dgda.service.Category',
	'dgda.service.Review',
	'dgda.service.Basket',
	'dgda.service.OrderLine',
	'dgda.service.ShippingMethod',
	'dgda.service.Voucher',
	'dgda.service.Order',
	'dgda.service.Payment',
	'dgda.service.Filter',
	'dgda.service.Support',
	'dgda.service.Content',
	'dgda.service.Booking',
	'dgda.service.UserTracking',
	'dgda.service.Marketing',
	'dgda.service.FilterHelpers',
	'dgda.service.Zipcode',
	'dgda.service.PagedProducts',
	'dgda.service.Employee',
	'dgda.service.SocialProof',
    'dgda.service.GiftExchange',
	'dgda.service.Refund',
	'dgda.service.SupplierCode',
	'dgda.service.Customer',

/** Internal Directives **/
	'dgda.directive.ProductListItem',
	'dgda.directive.AnchorNgClick',
	'dgda.directive.RatingStars',
	'dgda.directive.CheckoutSteps',
	'dgda.directive.InputValidation',
	'dgda.directive.FeaturedVideo',
	'dgda.directive.PersonalMessage',
	'dgda.directive.WistiaTracker',
	'dgda.directive.WistiaVideo',
	'dgda.directive.LoaderButton',
	'dgda.directive.AddToBasket',
	'dgda.directive.CustomerInfo',
	'dgda.directive.EaseBooking.Events',
    'dgda.directive.AnchorLinkScroll',
    'dgda.directive.DgdaLogo',
    'dgda.directive.SocialProofWidget',

	'dgda.directive.Alert',
	'dgda.directive.NewsletterPopup',
    'Dgda.Directive.NgRepeatAfter',

    //'dgda.module.SplittestVariantLoader',
	'dgda.service.ViaBillTestModule.Control', // Load the 'control' of ViaBill test => Do not show ViaBill
	'dgda.directive.Viabill',
	'dgda.module.ViabillTemplate',
	'dgda.service.ProductPriceTestModule.Control',
	'dgda.service.ProductSortTestModule.Variant',

    "dgda.module.Mockups"
])
.config(function ($urlRouterProvider, $locationProvider, localStorageServiceProvider, $uiViewScrollProvider) {
	$locationProvider
	.hashPrefix('!')
	.html5Mode(true);

	/**
	 * Normalize URLs and add a trailing slash, if it's missing
	 */
	$urlRouterProvider.rule(function ($injector, $location) {
		var path = $location.path(),
			normalized = path.toLowerCase();

		if (path != normalized) {
			path = normalized;
		}

		if (path[path.length - 1] !== '/') {
			path = path + "/";
		}

		return path;
	});

	/**
	 * If no other routes match, simply redirect to the front page
	 * (or change this to any other page, like a 404).
	 */
	$urlRouterProvider.otherwise('/');
    localStorageServiceProvider.setPrefix('dgda');
    $uiViewScrollProvider.useAnchorScroll();
})

.run(function ($http, $rootScope, $state, $window, $location, Analytics) {
	// Enable credientials (ie. cookies etc.) through the $http Angular Service
	$http.defaults.withCredentials = true;

	$rootScope.prerender = {
		StatusCode: 200,
		Header: ""
	};

    $rootScope.$on('$locationChangeStart', function watchLocationChange(event, newUrl){
        var index = newUrl.indexOf('/magasin/');
        if(index > 0){
            window.location.href = newUrl;
            return;
        }else if(index == 0){
            window.location.href = 'https://duglemmerdetaldrig.dk' + newUrl;
        }
    });

	// Reset the status code to 200 on state changes.
	// This allows individual states to override the
	// statuscode on a "navigation state basis", and
	// always default back to state 200 on state change.
	$rootScope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
		$rootScope.prerender = {
			StatusCode: ($rootScope.isRedirect ? 301 : 200),
			Header: ($rootScope.isRedirect ? $rootScope.prerender.Header : "")
		};

		$rootScope.isRedirect = false;
	});

	$rootScope.$on('$stateNotFound', function (event, unfoundState, fromState, fromParams) {
		Analytics.trackEvent('page-error', '404', $location.url());
		$state.go('public.404');
	});

	$rootScope.$on('$stateChangeSuccess', function (event, toState, toParams, fromState, fromParams) {
		// Set (or reset) "body class" upon finished navigation
		if (angular.isDefined(toState.data) && angular.isDefined(toState.data.bodyClass)) {
			$rootScope.bodyClass = toState.data.bodyClass;
		} else {
			$rootScope.bodyClass = '';
		}

		// Scroll to top upon navigation
		$window.scrollTo(0, 0);
	});
})

.controller('dgdaCtrl', function dgdaCtrl($scope) {
	/* cache dom references */
	var $body = $('body');
	var isMobile = /Android/i.test(navigator.userAgent) || /iP(hone|ad)/i.test(navigator.userAgent);

	if (isMobile) {
		/* bind events */
		document.addEventListener("focusin", function (e) {
			if (!$(e.target).is('input,textarea,select')) {
				return;
			}
			return $body.addClass('input-focus');
		});
		document.addEventListener("focusout", function (e) {
			if (!$(e.target).is('input,textarea,select')) {
				return;
			}
			$body.removeClass('input-focus');
		});
	}
})

.controller('NavigationCtrl', function NavigationCtrl($scope, $rootScope, Content, $window, $timeout, Analytics, $location) {
	$scope.quicklinks = Content.quicklinks();
	$scope.shippingMessage = Content.shipping();

	$rootScope.showInspiration = false;
	$rootScope.doToggleInspirationWidget = function doToggleInspirationWidget() {
		$rootScope.showInspiration = !$rootScope.showInspiration;
		$('.landing-widget').slideToggle();
	};

	/*
	$rootScope.showXmasUPS = false;
	$rootScope.doToggleshowXmasUPS = function doToggleshowXmasUPS() {
		$rootScope.showXmasUPS = !$rootScope.showXmasUPS;
		$('.header-top-inner.christmas-usp').slideToggle();
		$('.christmas-toggle').slideToggle();
	};

	var eventTimeout = null;
	var url = $location.url();
	$scope.startSnow = function startSnow(){
		$window.snowStorm.toggleSnow();

		// Start event tracking timer!
		eventTimeout = $timeout(function(){
			Analytics.trackEvent('fun-factory', 'let-it-snow', url);
		}, 1000);
	};

	$scope.stopSnow = function stopSnow(){
		$window.snowStorm.toggleSnow();
		if(eventTimeout !== null){
			$timeout.cancel(eventTimeout);
		}
	};*/

})

.controller('LandingPageWidgetCtrl', function LandingPageWidgetCtrl($scope, Content, $state) {
	$scope.landingpages = Content.landingpages();

	$scope.doNavigate = function doNavigate(slug) {
		$scope.doToggleInspirationWidget();
		$state.go('public.content', {
			url: slug
		});
	};
})

.controller('MainNavigationCtrl', function MainNavigationCtrl($rootScope, $scope, Content, $state) {
	    $scope.navigation = Content.navigation();

        $rootScope.showSearchField = false;
        $rootScope.doToggleSearchField = function doToggleSearchField(){
            $rootScope.showSearchField = !$rootScope.showSearchField;
        };

        $scope.searchQuery = "";
        $scope.search = function () {
            if ($scope.searchQuery === "") {
                return;
            }
            $scope.doToggleSearchField();
            $state.go("public.search", { query: $scope.searchQuery.toLowerCase() });
            $scope.searchQuery = '';
        };
})

;