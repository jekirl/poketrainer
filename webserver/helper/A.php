<?php

namespace Poketrainer\helper;

class A {

  const TYPE_CONTROLLER = 1;
  const TYPE_ACTION = 2;

  public static function href($controllerUrl, $actionTitle, $titleParams = "", $params = []) {

    $isHttp = false;

    $httpMatch = [
      "/",
      "http:",
      "https:",
      "ftp:",
      "mailto:",
      "tel:"
    ];

    foreach ($httpMatch as $item) {
      if(strpos($controllerUrl, $item) !== false) {
        $isHttp = true;
      }
    }

    if($isHttp) {
      $params = "";
      if(is_array($titleParams)) {
        foreach ($titleParams as $param => $value) {
          $params .= "$param='$value' ";
        }
      }
      return "<a $params href='$controllerUrl'>$actionTitle</a>";
    }

    $controller = self::transformNames($controllerUrl, self::TYPE_CONTROLLER);
    $action = self::transformNames($actionTitle, self::TYPE_ACTION);
    if($action == "index") {
      $action = "";
    }
    if($controller == "index" && !$action) {
      $controller = "";
    }

    $url = [$controller, $action];
    $url = array_filter($url);
    $url = implode("/",$url);
    $parameters = "";
    if($params) {
      foreach ($params as $param => $value) {
        $parameters .= "$param='$value'";
      }
    }
    return "<a $parameters href='/$url'>$titleParams</a>";
  }

  private static function transformNames($name, $type) {
    if ($type == self::TYPE_CONTROLLER) {
      $name = end(explode("\\",$name));
      $name = str_replace("Controller", "", $name);
    } else if($type == self::TYPE_ACTION) {
      $name = str_replace("Action","",$name);
    }
    $preg1 = "@([A-Z])@"; // transform big letters
    $name = preg_replace_callback($preg1, function ($m) {
      $m[1] = strtolower($m[1]);
      return "-" . $m[1];
    }, $name);
    $name = trim($name,"-");
    return $name;
  }

}