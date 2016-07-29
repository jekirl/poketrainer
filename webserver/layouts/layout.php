<?php
/** @var string $title */
use Poketrainer\base\App;
use Poketrainer\controller\IndexController;
use Poketrainer\controller\SettingsController;
use Poketrainer\helper\A;
use Poketrainer\helper\Lng;
use Poketrainer\helper\Msg;
use Poketrainer\helper\Tpl;

?>
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title><?=$title?></title>
  <script src="/static/js/jquery.js"></script>
  <script src="/static/js/script.js"></script>
  <link rel="stylesheet" href="/static/css/style.css" />
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<div id="wrapper">
  <nav class="navbar navbar-default navbar-static-top" role="navigation" id="top-navigation">
    <div class="navbar-header">
      <?=A::href(IndexController::class,"index",Lng::translate(App::APP_TITLE),[
        "class" => "navbar-brand"
      ])?>
    </div>
    <div class="navbar-default sidebar" role="navigation">
      <div class="sidebar-nav">
        <ul id="side-menu" class="nav in">
          <li><?=A::href(IndexController::class, "index", Lng::translate("Home"))?></li>
          <li><?=A::href(SettingsController::class,"index",Lng::translate("Settings"))?></li>
        </ul>
      </div>
    </div>
  </nav>
  <div id="page-wrapper">
    <div class="row">
      <div class="col-lg-12">
        <h1 class="page-header"><?=$title?></h1>
      </div>
    </div>
    <?=Msg::get()?>
    <?=Tpl::get("main")?>
  </div>
</div>
</body>
</html>