<?php
/** @var SettingsController $this */
use Poketrainer\controller\SettingsController;
use Poketrainer\helper\Lng;
use Poketrainer\helper\Tpl;

Tpl::start("main");
?>
<?php
if (!$this->settingsModel->configFileExists()) {
  $this->settingsModel->createConfigFile();
  ?>
  <div class="row">
    <div class="col-lg-4">
      <div class="panel panel-info">
        <div class="panel-heading">
          <?= Lng::translate("Info") ?>
        </div>
        <div class="panel-body">
          <?= Lng::translate("This is the first time you are using this bot, it is a good idea to set it up first.") ?>
        </div>
      </div>
    </div>
  </div>
  <?php
}
?>
  <div class="row">
    <div class="col-lg-12">
      <?= Lng::translate("Here you can set various settings of Pokémon GO Bot") ?><br><br>
    </div>
  </div>
  <div class="row">
    <div class="col-lg-12">
      <div class="table-responsive">
        <table class="table table-striped table-bordered">
          <thead>
          <tr>
            <th><?= Lng::translate("Setting") ?></th>
            <th><?= Lng::translate("Value") ?></th>
          </tr>
          </thead>
          <tbody>
          <?php
          $i = 0;
          foreach ($this->settingsModel->getConfig() as $config => $description) {
            $typeInfo = $this->settingsModel->getConfigType($config);
            if(is_string($typeInfo)) {
              $type = $typeInfo;
            } else if(is_array($typeInfo) && isset($typeInfo["type"])) {
              $type = $typeInfo["type"];
            } else {
              throw new Exception("Type of $config not found");
            }
            $value = $this->settingsModel->getConfigValue($config);
            ?>
            <tr>
              <td><label for="setting-<?=$i?>"><?= $description ?></label></td>
              <td></td>
            </tr>
            <?php
            $i++;
          }
          ?>
          </tbody>
        </table>
      </div>
    </div>
  </div>


<?php
Tpl::end();
