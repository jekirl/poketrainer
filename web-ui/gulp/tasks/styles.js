var gulp = require('gulp');
var config = require('../config.js');
var mergeStream = require('merge-stream');
var plugins = require('gulp-load-plugins')();

gulp.task('styles', function () {
	var streams = config.bundles.filter(function (b) {
		return b.styles != null;
	}).map(function (b) {
		var ignores = b.ignorePlugins != null ? b.ignorePlugins : [];

		var useSourcemaps = ignores.indexOf("sourcemaps") == -1;
		var useAutoprefixer = ignores.indexOf("autoprefixer") == -1;

		return gulp.src(b.styles)
            .pipe(plugins.plumber(config.errorHandler("styles")))
            //.pipe(plugins.if(!config.debug && useSourcemaps, plugins.sourcemaps.init({ loadMaps: true })))
            .pipe(plugins.less())
            .pipe(plugins.if(!config.environment.debug && useAutoprefixer, plugins.autoprefixer(config.stylesVendorPrefixes)))
            //.pipe(plugins.if(!config.debug && useSourcemaps, plugins.sourcemaps.write()))
            .pipe(plugins.base64({
                extensions: ['svg']
            }))
            .pipe(plugins.if(!config.environment.debug, plugins.minifyCss({compatibility: 'ie8'})))
            .pipe(gulp.dest(config.stylesDist));
	});

	return mergeStream(streams);
});