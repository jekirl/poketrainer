<?php

namespace Poketrainer\controller;

class IndexController extends Controller {

  public function __construct($controller, $action) {
    parent::__construct($controller, $action);
    if(!$this->settingsModel->configFileExists()) {
      Redirect("/settings");
    }
  }

  public function indexAction() {
    $this->render = "index/index";
    $this->render();
  }

}