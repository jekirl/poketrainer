<?php

namespace Poketrainer\base;

use Poketrainer\exceptions\ActionNotFoundException;
use Poketrainer\exceptions\ControllerNotFoundException;

class Routing {

  public $controller = "index";
  public $action = "index";
  public $args = [];

  public function __construct() {
    if (getp(1)) {
      $this->controller = getp(1);
    }
    if (getp(2)) {
      $this->action = getp(2);
    }
    for ($i = 3; $i <= getpCount(); $i++) {
      $this->args[] = getp($i);
    }

    $controller = "Poketrainer\\controller\\".$this->getController();
    $action = $this->getAction();
    if(!class_exists($controller)) {
      throw new ControllerNotFoundException("Specified controller ($controller) does not exist");
    }
    $runtime = new $controller($this->controller, $this->action);
    if (method_exists($runtime, "exceptionHandler")) {
      set_exception_handler([$runtime, "exceptionHandler"]);
    }
    if (!method_exists($runtime, $action)) {
      throw new ActionNotFoundException("Specified action ($action) not found");
    }
    call_user_func_array([$runtime, $action], $this->args);
  }

  private function getController() {
    $tmp = strtolower($this->controller);
    $tmp = explode("-", $tmp);
    $controller = "";
    foreach ($tmp as $item) {
      $item = ucfirst($item);
      $controller .= $item;
    }
    $controller .= "Controller";
    return $controller;
  }

  private function getAction() {
    $tmp = strtolower($this->action);
    $tmp = explode("-", $tmp);
    $action = "";
    $i = 0;
    foreach ($tmp as $item) {
      if ($i > 0) {
        $item = ucfirst($item);
      }
      $action .= $item;
      $i++;
    }
    $action .= "Action";
    return $action;
  }

}