<?php

namespace Poketrainer\helper;

use Poketrainer\base\App;

class Lng extends Helper {

  private static $dictionary;
  public static $called;

  public static function translate($key) {
    if(!is_array(self::$dictionary)) {
      if(file_exists(ROOT."/languages/".App::$lng.".json")) {
        $data = file_get_contents(ROOT."/languages/".App::$lng.".json");
        $data = json_decode($data,true);
        if($data) {
          self::$dictionary = $data;
        }
      } else {
        self::$dictionary = [];
      }
    }

    self::$called[] = $key;
    if(isset(self::$dictionary[$key]) && self::$dictionary[$key]) {
      return self::$dictionary[$key];
    }

    return $key;

  }

}