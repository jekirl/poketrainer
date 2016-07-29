<?php

namespace Poketrainer\base;

use Poketrainer\exceptions\ClassNotFoundException;
use Poketrainer\helper\Lng;

class App {

  const APP_TITLE = "Pokémon GO Bot";

  /** @var \SQLite3 $db */
  public static $db;
  public static $routing;
  public static $lng = "en";

  public static function start() {
    set_time_limit(0);
    session_start();
    header("Content-type: text/html; charset=utf-8");
    self::constants();
    self::assignLng();
    self::autoload();
    self::assignDb();
    self::generateLngFilesOnShutdown();
    self::$routing = new Routing();
  }

  private static function constants() {
    define('ROOT', $_SERVER["DOCUMENT_ROOT"]);
    define('ENDL', PHP_EOL);
  }

  private static function autoload() {
    require_once ROOT."/exceptions/ClassNotFoundException.php";
    spl_autoload_register(function ($class) {
      $path = ROOT . str_replace(["\\","Poketrainer"], ["/",""], $class).".php";
      if(file_exists($path)) {
        require_once $path;
        return true;
      }
      throw new ClassNotFoundException("Class $class not found");
    });
  }

  private static function assignLng() {
    if(file_exists(ROOT."/lng.json")) {
      $data = file_get_contents(ROOT."/lng.json");
      $data = json_decode($data, true);
      if(isset($data["lng"])) {
        self::$lng = $data["lng"];
      }
    } else {
      $lng = [
        "lng" => self::$lng
      ];
      $data = json_encode($lng,JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
      file_put_contents("lng.json",$data);
    }
  }

  private static function assignDb() {
    // To be done later
    return false;
    self::$db = new \SQLite3("../db.sqlite");
  }

  private static function generateLngFilesOnShutdown() {
    register_shutdown_function(function() {
      $data = [];
      $file = ROOT."/languages/default.json";
      if(file_exists($file)) {
        $data = file_get_contents($file);
        $data = json_decode($data, true);
      }
      foreach (Lng::$called as $value) {
        $data[$value] = "";
      }
      $data = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
      file_put_contents($file, $data);
    });
  }

}