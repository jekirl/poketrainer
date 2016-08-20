var config = require('./config.js');

config.loadTasks.forEach(function (x) { 
    require('./tasks/' + x);
});