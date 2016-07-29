<?php

namespace Poketrainer\helper;

class Tpl extends Helper {
  private static $blocks = [];
  private static $last_block;

  public static function start($block) {
    self::$blocks[$block] = "";
    self::$last_block = $block;
    ob_start();
  }

  public static function end($block = false) {
    if ($block === false) {
      $block = self::$last_block;
    }
    $content = ob_get_contents();
    ob_end_clean();
    self::$blocks[$block] = $content;
  }

  public static function get($block, $echo = false) {
    $ret = isset(self::$blocks[$block]) ? self::$blocks[$block] : "";
    if ($echo) {
      echo $ret;
    }
    else {
      return $ret;
    }
    return true;
  }
}