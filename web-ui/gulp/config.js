var notifier = require('node-notifier');
var argv = require('yargs').argv;

module.exports = (function () {
    var projectName = "poketrainer";

    var projectPath = "./src";
    var vendorPath = "./vendor";
    var bowerPath = vendorPath + "/bower";
    var distPath = "./dist";
    var assetsPath = projectPath + "/assets";
    var assetsDistPath = distPath + "/assets";

    var cleanPaths = [
		distPath + "/index.html",
		distPath + "/app",
		distPath + "/assets"
    ];


    var debug = true;
    var live = false;
    if( typeof(argv.profile) !== "undefined"){
        live = (argv.profile.toLowerCase() === "live" || argv.profile.toLowerCase() === "production");
        debug = (argv.profile.toLowerCase() === "debug") || mockups;
    }
    
    var baseUrl = '/';

    // If we're not running the mockup version,
    // do not include the JS files.
    var angularScripts = [
        projectPath + "/app/**/*.js",
        "!" + projectPath + "/app/**/_*.js" // Exclude all files starting with an underscore
    ];

	return {
		projectName: projectName,

        environment: {
            debug: debug,
            live: live
        },

        errorHandler: function(taskName) 
        {
            return function (e) {
                notifier.notify({
                    "title": taskName,
                    "message": "An error occured in the " + e.plugin + " plugin."
                });
                console.log(e.message);
                this.emit("end");
            };
        },

        bowerPath: bowerPath,
		distPath: distPath,
        cleanPaths: cleanPaths,

        loadTasks: [
            "bower", "envcontext", "styles",
            "scripts", "images", "icons", 
            "copy", "watch", "build", 
            "html2js", "index"
        ],
        buildTasks: [
            "envcontext", "styles", "scripts",
            "images", "icons", "copy",
            "html2js", "index-rebuild"
        ],

    	// ------------- Scripts -------------
        index: {
        	src: projectPath + "/index.html",
			dist: distPath,
            baseUrl: baseUrl
        },

        // ------------- Scripts -------------
        scriptsDist: assetsDistPath + "/js",

        // ------------- Icons -------------
        iconsDist: assetsDistPath + "/images/icons",

        // ------------- Fonts -------------
        fontsDist: assetsDistPath + "/fonts",

        // ------------- Styles -------------
        stylesDist: assetsDistPath + "/css",
        stylesVendorPrefixes: [
            "last 2 version",
            "safari 5",
            "ie 8",
            "ie 9",
            "opera 12.1",
            "ios 6",
            "android 4"
        ],

        // ------------- Images -------------
        imagesDist: assetsDistPath + "/images",
        imagesOptimizationLevel: 5,
        imagesProgressive: true,
        imagesInterlaced: true,

        // ------------- Livereload -------------
        livereloadPort: 1337,
        livereloadPaths: [
			assetsDistPath + "/js/*.js",
			assetsDistPath + "/css/*.css",
			distPath + "/**/*.html"
        ],

        // ------------- Watch -------------
        watchImages: [ assetsPath + "/images/*"],
        watchIcons: [ assetsPath + "/images/icons/*"],
        watchFonts: [ assetsPath + "/fonts/*"],
        watchScripts: [
            projectPath + "/**/*.js",
            vendorPath + "/**/*.js"
        ],
        watchStyles: [
            projectPath + "/**/*.less",
            vendorPath + "/**/*.less"
        ],
        watchTpls: [
			projectPath + "/**/*.tpl.html"
        ],

        // ------------- Copy on build -------------
        buildCopy: [{
            from: assetsPath + "/fonts/**/*",
            to: assetsDistPath  + "/fonts"
        },
        {
        	from: assetsPath + "/js/vendor/**/*",
        	to: assetsDistPath + "/js/vendor"
        }],

        // ------------- Bundles -------------
        bundles: [{
            name: "vendor",
            ignorePlugins: ["jscs", "jshint", "sourcemaps"],
            scripts: [
                bowerPath + '/jquery/dist/jquery.js',

                /** Bootstrap **/

                /** Angular Stuff **/
                bowerPath + '/angular/angular.js',
                bowerPath + '/angular-resource/angular-resource.js',
                bowerPath + '/angular-ui-router/release/angular-ui-router.js',
                bowerPath + '/angular-google-maps/dist/angular-google-maps.js',

                assetsPath + "/js/plugins/*.js"
            ]
        },
        {
        	name: "master",
        	ignorePlugins: ['autoprefixer', 'imagemin', "sourcemaps"],
            scripts: [ assetsPath + "/js/*.js", '!' + assetsPath + "/js/-*.js" ],
            styles: [ assetsPath + "/less/main.less" ],
            images: [ assetsPath + "/images/**/*.{jpg,png,gif,svg}" ],
            icons: [assetsPath + "/images/icons/*.svg" ]
        },
        {
        	name: "angular",

            ignorePlugins: ['autoprefixer', 'imagemin'],
        	scripts: angularScripts,
        	tpl: [projectPath + "/**/*.tpl.html"]
        }]
    }
})();