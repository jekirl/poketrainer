var gulp = require('gulp');
var config = require('../config.js');
var plugins = require('gulp-load-plugins')();
var mergeStream = require('merge-stream');

gulp.task('fonts', function (cb) {
    var streams = config.bundles.filter(function (b) {
        return b.fonts != null;
    }).map(function (b) {
        var ignores = b.ignorePlugins != null ? b.ignorePlugins : [];

        var useNewer = ignores.indexOf("newer") == -1;
        var useImagemin = ignores.indexOf("imagemin") == -1;

        return gulp.src(b.fonts)
            //.pipe(plugins.plumber(config.errorHandler("fonts")))
            .pipe(plugins.if(useNewer, plugins.newer(config.fontsDist)))
            .pipe(plugins.if(useImagemin, plugins.imagemin()))
            .pipe(gulp.dest(config.fontsDist));
    });
    return mergeStream(streams);
});