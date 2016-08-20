var gulp = require('gulp');
var config = require('../config.js');
var plugins = require('gulp-load-plugins')();
var mergeStream = require('merge-stream');

gulp.task("copy", function () {
    var streams = config.buildCopy.map(function (x) {
        return gulp.src(x.from)
            .pipe(plugins.newer(x.to))
            .pipe(gulp.dest(x.to));
    });
    return mergeStream(streams);
});