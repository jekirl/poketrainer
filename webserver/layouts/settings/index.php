<?php
/** @var SettingsController $this */
use Poketrainer\controller\SettingsController;
use Poketrainer\exceptions\TypeNotFoundException;
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
        <form method="post" role="form">
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
                <td class="col-lg-7"><label for="setting-<?=$i?>"><?= $description ?></label></td>
                <td>
                  <div class="form-group">
                  <?php
                  switch ($type) {
                    case "text":
                      ?>
                      <input id="setting-<?=$i?>" class="form-control" type="text" name="<?=$config?>" value="<?=$value?>" />
                      <?php
                      break;
                    case "password":
                      ?>
                      <input id="setting-<?=$i?>" class="form-control" type="password" name="<?=$config?>" value="<?=$value?>" />
                      <?php
                      break;
                    case "select":
                      ?>
                      <select id="setting-<?=$i?>" class="form-control" name="<?=$config?>">
                        <option value="">---</option>
                        <?php
                        foreach ($typeInfo["options"] as $optValue => $displayValue) {
                          $selected = $optValue == $value?"selected":"";
                          $disabled = $optValue == "null"?"disabled":"";
                          ?>
                          <option <?=$selected?> <?=$disabled?> value="<?=$optValue?>"><?=$displayValue?></option>
                          <?php
                        }
                        ?>
                      </select>
                      <?php
                      break;
                    case "bool":
                      $checked = $value?"checked":"";
                      ?>
                      <input type="hidden" name="<?=$config?>" value="false" />
                      <input <?=$checked?> id="setting-<?=$i?>" type="checkbox" name="<?=$config?>" value="true" />
                      <?php
                      break;
                    case "int":
                      ?>
                      <input id="setting-<?=$i?>" type="number" step="1" name="<?=$config?>" value="<?=$value?>" />
                      <?php
                      break;
                    case "float":
                      ?>
                      <input id="setting-<?=$i?>" type="number" step="0.1" name="<?=$config?>" value="<?=$value?>" />
                      <?php
                      break;
                    default:
                      throw new TypeNotFoundException("The type $type is not allowed as a field type");
                  }
                  ?>
                  </div>
                </td>
              </tr>
              <?php
              $i++;
            }
            ?>
            <tr>
              <td colspan="2">
                <input type="submit" class="btn btn-default" value="<?=Lng::translate("Save settings")?>" name="settings-update" />
              </td>
            </tr>
            </tbody>
          </table>
        </form>
      </div>
    </div>
  </div>


<?php
Tpl::end();
