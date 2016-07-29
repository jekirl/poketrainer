<?php

namespace Poketrainer\controller;

use Poketrainer\base\App;
use Poketrainer\helper\Lng;
use Poketrainer\model\SettingsModel;

abstract class Controller {

  public $layout = "layout";
  public $layout_dir = "/layouts";
  public $render = "site";
  public $data = [];
  public $controller;
  public $action;

  public $settingsModel;

  abstract public function indexAction();

  public function __construct($controller, $action) {
    $this->settingsModel = new SettingsModel();
    $this->data["title"] = Lng::translate(App::APP_TITLE);
    $this->controller = $controller;
    $this->action = $action;
  }

  public function render() {
    ob_start();
    foreach ($this->data as $key => $value) {
      $$key = $value;
    }
    require_once $this->getRenderFile();
    require_once $this->getLayoutFile();
    echo ob_get_clean();
  }

  protected function getLayoutFile() {
    return ROOT."$this->layout_dir/$this->layout.php";
  }

  protected function getRenderFile() {
    return ROOT."$this->layout_dir/$this->render.php";
  }

}