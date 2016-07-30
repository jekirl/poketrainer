var gulp = require('gulp');
var config = require('../config.js');
var plugins = require('gulp-load-plugins')();
var mergeStream = require('merge-stream');

gulp.task('images', function (cb) {
    var streams = config.bundles.filter(function (b) {
        return b.images != null;
    }).map(function (b) {
        var ignores = b.ignorePlugins != null ? b.ignorePlugins : [];

        var useNewer = ignores.indexOf("newer") == -1;
        var useImagemin = ignores.indexOf("imagemin") == -1;

        return gulp.src(b.images)
            //.pipe(plugins.plumber(config.errorHandler("images")))
            .pipe(plugins.if(useNewer, plugins.newer(config.imagesDist)))
            .pipe(plugins.if(useImagemin, plugins.imagemin({
                optimizationLevel: config.imagesOptimizationLevel,
                progressive: config.imagesProgressive,
                interlaced: config.imagesInterlaced
            })))
            .pipe(gulp.dest(config.imagesDist));
    });
    return mergeStream(streams);
});