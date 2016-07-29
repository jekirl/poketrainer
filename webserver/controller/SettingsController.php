<?php

namespace Poketrainer\controller;

use Poketrainer\helper\Lng;

class SettingsController extends Controller {

  public function __construct($controller, $action) {
    parent::__construct($controller, $action);
    if(isset($_POST['settings-update'])) {
      $this->settingsModel->saveSettings();
    }
  }

  public function indexAction() {
    $this->render = "settings/index";
    $this->data["title"] = Lng::translate("Settings");
    $this->render();
  }

}