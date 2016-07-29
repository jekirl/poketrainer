<?php
use Poketrainer\base\App;

if(file_exists("vendor/autoload.php")) {
  require_once "vendor/autoload.php";
}

require_once "base/App.php";

App::start();