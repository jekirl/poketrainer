var gulp = require('gulp');
var config = require('../config.js');
var es = require('event-stream');
var util = require('util');
var path = require('path');
var mergeStream = require('merge-stream');
var plugins = require('gulp-load-plugins')();

function compileIndex() {
	var distPath = config.distPath;
	var cssPath = config.stylesDist;
	var jsPath = config.scriptsDist;
	var indexPath = config.index.src;

	var cssStream = gulp.src([path.join(cssPath, "/*.css"), '!' + cssPath + '/epay*.css'], { read: false });
	var jsStream = null;

	if (config.environment.debug) {
		var jsFiles = [];

		config.bundles.filter(function (b) {
			return b.scripts != null;
		}).map(function (b) {
			return b.scripts.map(function (filePath) {
				return jsFiles.push(path.join(jsPath, path.basename(filePath)));
			});
		});

		jsFiles.push(path.join(config.scriptsDist, '*-tpl.js'));
		jsFiles.push(path.join(config.scriptsDist, '**/*.js'));
		jsFiles.push("!" + path.join(config.scriptsDist, '**/*.min.js'));

		jsStream = gulp.src(jsFiles, { read: false, base: distPath });
	} else {
		var streams = config.bundles.map(function (b) {
			var paths = [
				path.join(config.scriptsDist, b.name + '.min.js'),
				path.join(config.scriptsDist, b.name + '-tpl.min.js')
			];

			return gulp.src(paths, { read: false });
		});

		jsStream = mergeStream(streams);
	}

	return gulp.src(indexPath)
		.pipe(plugins.inject(
			es.merge(
				jsStream,
				cssStream
			),
			{
				ignorePath: [
					distPath,
					'src'
				]
			}
		))
        .pipe(plugins.injectString.after('</title>', '\n\t<base href="' + config.index.baseUrl + '"/>'))
		.pipe(plugins.if(!config.environment.debug, plugins.minifyHtml({
            conditionals: true,
			empty: true,
			spare: true,
			quotes: true
		})))
		.pipe(gulp.dest(config.index.dist));
}

var requiredTasks = config.buildTasks.slice();
var index = requiredTasks.indexOf('index-rebuild');
if (index > -1) {
	requiredTasks.splice(index, 1);
}

gulp.task('index-rebuild', requiredTasks, function () {
	return gulp.start('index');
});

gulp.task('index', function () {
	return compileIndex();
});