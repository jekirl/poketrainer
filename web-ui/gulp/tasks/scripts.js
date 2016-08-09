var gulp = require('gulp');
var config = require('../config.js');
var mergeStream = require('merge-stream');
var plugins = require('gulp-load-plugins')();
var change = require('gulp-change');

gulp.task('scripts', function () {
    var streams = config.bundles.filter(function (b) {
        return b.scripts != null;
    }).map(function (b) {
        var ignores = b.ignorePlugins != null ? b.ignorePlugins : [];

        var useJshint = ignores.indexOf("jshint") == -1;
        var useJscs = ignores.indexOf("jscs") == -1;
        var useSourcemaps = ignores.indexOf("sourcemaps") == -1;
        var useUglify = ignores.indexOf("uglify") == -1;

        function removeMocksModule(content) {
            return content.replace(',"dgda.module.Mockups"', "");
        }

        return gulp.src(b.scripts)
            //.pipe(plugins.plumber(config.errorHandler("scripts")))
            .pipe(plugins.resolveDependencies({ pattern: /\* @require [\s-]*(.*?\.js)/g }))
			.pipe(plugins.if(useJshint, plugins.jshint()))
            .pipe(plugins.if(useJscs, plugins.jscs()))
            .pipe(plugins.if(!config.environment.debug && useSourcemaps, plugins.sourcemaps.init({ loadMaps: true })))
            .pipe(plugins.if(!config.environment.debug, plugins.concat(b.name + ".min.js")))
			.pipe(plugins.if(!config.environment.debug, plugins.ngmin()))
            .pipe(plugins.if(!config.environment.debug && useUglify, plugins.uglify()))
            .pipe(plugins.if(!config.environment.debug && useSourcemaps, plugins.sourcemaps.write()))
            .pipe(plugins.if(config.environment.live, change(removeMocksModule)))
            .pipe(gulp.dest(config.scriptsDist));
    });

    return mergeStream(streams);
});