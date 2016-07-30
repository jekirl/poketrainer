var gulp = require('gulp');
var config = require('../config.js');
var del = require('del');
var plugins = require('gulp-load-plugins')();

gulp.task('clean', function (cb) {
	return del(config.cleanPaths, {
		force: true
	}, cb);
});

gulp.task('rebuild', ['clean'], function () {
    return gulp.start('default');
});

gulp.task('default', config.buildTasks);