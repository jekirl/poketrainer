<?php

namespace Poketrainer\controller;

use Poketrainer\helper\Lng;

class SettingsController extends Controller {

  public function indexAction() {
    $this->render = "settings/index";
    $this->data["title"] = Lng::translate("Settings");
    $this->render();
  }

}