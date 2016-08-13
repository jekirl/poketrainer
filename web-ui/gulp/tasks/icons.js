var gulp = require('gulp');
var config = require('../config.js');
var plugins = require('gulp-load-plugins')();
var mergeStream = require('merge-stream');

gulp.task('icons', function (cb) {
    var streams = config.bundles.filter(function (b) {
        return b.icons != null;
    }).map(function (b) {
        var ignores = b.ignorePlugins != null ? b.ignorePlugins : [];

        var useNewer = ignores.indexOf("newer") == -1;
        var useImagemin = ignores.indexOf("imagemin") == -1;

        return gulp.src(b.icons)
            //.pipe(plugins.plumber(config.errorHandler("icons")))
            .pipe(plugins.if(useNewer, plugins.newer(config.iconsDist)))
            .pipe(plugins.if(useImagemin, plugins.imagemin()))
            .pipe(gulp.dest(config.iconsDist));
    });
    return mergeStream(streams);
});