var gulp = require('gulp');
var config = require('../config.js');
var gulpif = require('gulp-if');
var rename = require("gulp-rename");
var change = require('gulp-change');
var fs = require('fs');

gulp.task('envcontext', function () {

    var path = "./src/app/modules/";
    var source = "./src/app/modules/dgda.module.Mockups.js";

    function addMockups(content) {
        return content.replace(/\[\]/g, fs.readFileSync('./src/app/modules/_dgda.modules.mockups.data.json', 'utf8'));
    }
    
    return gulp.src(source)
        .pipe(gulpif(config.environment.mock, change(addMockups)))
        .pipe(rename('_dgda.module.Mockups.js'))
        .pipe(gulp.dest(path));
});