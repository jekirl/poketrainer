<?php

namespace Poketrainer\model;

use Poketrainer\exceptions\ConfigNotFoundException;
use Poketrainer\helper\Lng;
use Poketrainer\model\CandyCountEnumModel as CandyCount;

class SettingsModel extends Model {
  public $accountId = 0;
  private $namedConfig = [
    "auth_service" => "Account type",
    "username" => "Username",
    "password" => "Password",
    "location" => "Location of the bot",
    "USE_GOOGLE" => "Use Google for directions",
    "GMAPS_API_KEY" => "Google Maps API key (only needed if using Google for directions)",
    "KEEP_CP_OVER" => "Keep Pokémon with CP higher than this value",
    "KEEP_IV_OVER" => "Keep Pokémon with IV higher than this value",
    "STEP_SIZE" => "How many meters per second should the bot walk?",
    "EXPERIMENTAL" => "Allow experimental features?",
    "SKIP_VISITED_FORT_DURATION" => "Avoid a PokéStop for a given number of seconds. This allows bot to explore bigger area.",
    "SPIN_ALL_FORTS" => "Bot will try to route using Google Maps to all visible PokéStops",
    "STAY_WITHIN_PROXIMITY" => "The bot will not travel further than the meters you specify",
    "AUTO_USE_LUCKY_EGG" => "Can the bot use Lucky Eggs?",
    "CAPTURE.MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY" => "After this count of failed captures the bot will use Razz Berry (default 1)",
    "EGG_INCUBATION.ENABLE" => "Can the bot hatch eggs?",
    "EGG_INCUBATION.USE_DISPOSABLE_INCUBATORS" => "Can the bot use incubators with limited use?",
    "EGG_INCUBATION.BIG_EGGS_FIRST" => "Should the bot first hatch eggs with higher km range?",
    "MIN_ITEMS.ITEM_POTION" => "How many potions should the bot keep?",
    "MIN_ITEMS.ITEM_SUPER_POTION" => "How many super potions should the bot keep?",
    "MIN_ITEMS.ITEM_HYPER_POTION" => "How many hyper potions should the bot keep?",
    "MIN_ITEMS.ITEM_MAX_POTION" => "How many max potions should the bot keep?",
    "MIN_ITEMS.ITEM_BLUK_BERRY" => "How many bluk berries should the bot keep?",
    "MIN_ITEMS.ITEM_NANAB_BERRY" => "How many nanab berries should the bot keep?",
    "MIN_ITEMS.ITEM_REVIVE" => "How many revives should the bot keep?",
    "MIN_ITEMS.ITEM_MAX_REVIVE" => "How many max revives should the bot keep?",
    "MIN_ITEMS.ITEM_RAZZ_BERRY" => "How many razz berries should the bot keep?",
    "POKEMON_EVOLUTION" => "Which Pokémon should the bot evolve?",
    "MIN_SIMILAR_POKEMON" => "How many Pokémon of the same type should the bot keep? Other settings can alter the behavior of this",
    "KEEP_POKEMON_NAMES" => "Which Pokémon should the bot keep always?",
    "THROW_POKEMON_NAMES" => "Which Pokémon should the bot always transfer?",
    "MAX_CATCH_ATTEMPTS" => "How many attepts to catch Pokémon before leaving him alone?",
    "RELEASE_DUPLICATES" => "Release duplicate Pokémon? These settings override the CP and IV settings",
    "RELEASE_DUPLICATES_MAX_LV" => "Pokémon with level higher than this value will not be transfered",
    "RELEASE_DUPLICATES_SCALER" => "This value is multiplied by the highest level Pokémon of a type and only those Pokémon that are less than the scaled level are transfered",
    "DEFINE_POKEMON_LV" => "Defines what metrics to use for releasing Pokémon",
    "NEEDY_ITEM_FARMING.ENABLE" => "When enabled, bot will not try to catch Pokémons but will travel from PokéStop to PokéStop and collect PokéBalls",
    "NEEDY_ITEM_FARMING.POKEBALL_FARM_THRESHOLD" => "When the count of PokéBalls drops below this number, the bot will not catch and only collect PokéBalls",
    "NEEDY_ITEM_FARMING.POKEBALL_CONTINUE_THRESHOLD" => "When the count of PokéBalls reaches this amount, the bot will stop farming and will return to catching Pokémon",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_POKEBALL_COUNT" => "Ignore standard PokéBalls?",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_GREATBALL_COUNT" => "Ignore Great Balls?",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_ULTRABALL_COUNT" => "Ignore Ultra Balls?",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_MASTERBALL_COUNT" => "Ignore Master Balls?",
    "NEEDY_ITEM_FARMING.FARM_OVERRIDE_STEP_SIZE" => "When the bot goes farming it will use this value instead of standard step size, set to -1 to disable",
  ];

  private $configTypes = [
    "auth_service" => [
      "type" => "select",
      "options" => [
        "ptc" => "Pokémon Trainer Club",
        "google" => "Google account",
      ],
    ],
    "username" => "text",
    "password" => "text",
    "location" => "text",
    "USE_GOOGLE" => "bool",
    "GMAPS_API_KEY" => "text",
    "KEEP_CP_OVER" => "int",
    "KEEP_IV_OVER" => "int",
    "STEP_SIZE" => "int",
    "EXPERIMENTAL" => "bool",
    "SKIP_VISITED_FORT_DURATION" => "int",
    "SPIN_ALL_FORTS" => "bool",
    "STAY_WITHIN_PROXIMITY" => "int",
    "AUTO_USE_LUCKY_EGG" => "bool",
    "CAPTURE.MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY" => "int",
    "EGG_INCUBATION.ENABLE" => "bool",
    "EGG_INCUBATION.USE_DISPOSABLE_INCUBATORS" => "bool",
    "EGG_INCUBATION.BIG_EGGS_FIRST" => "bool",
    "MIN_ITEMS.ITEM_POTION" => "int",
    "MIN_ITEMS.ITEM_SUPER_POTION" => "int",
    "MIN_ITEMS.ITEM_HYPER_POTION" => "int",
    "MIN_ITEMS.ITEM_MAX_POTION" => "int",
    "MIN_ITEMS.ITEM_BLUK_BERRY" => "int",
    "MIN_ITEMS.ITEM_NANAB_BERRY" => "int",
    "MIN_ITEMS.ITEM_REVIVE" => "int",
    "MIN_ITEMS.ITEM_MAX_REVIVE" => "int",
    "MIN_ITEMS.ITEM_RAZZ_BERRY" => "int",
    "POKEMON_EVOLUTION" => [
      "type" => "select",
      "options" => [
        "null" => "Not working yet",
      ],
    ],
    "MIN_SIMILAR_POKEMON" => "int",
    "KEEP_POKEMON_NAMES" => [
      "type" => "select",
      "options" => [
        "null" => "Not working yet",
      ],
    ],
    "THROW_POKEMON_NAMES" => [
      "type" => "select",
      "options" => [
        "null" => "Not working yet",
      ],
    ],
    "MAX_CATCH_ATTEMPTS" => "int",
    "RELEASE_DUPLICATES" => "bool",
    "RELEASE_DUPLICATES_MAX_LV" => "int",
    "RELEASE_DUPLICATES_SCALER" => "float",
    "DEFINE_POKEMON_LV" => [
      "type" => "select",
      "options" => [
        "CP" => "CP",
        "IV" => "IV",
        "CP*IV" => "CP * IV",
        "CP+IV" => "CP + IV",
      ],
    ],
    "NEEDY_ITEM_FARMING.ENABLE" => "bool",
    "NEEDY_ITEM_FARMING.POKEBALL_FARM_THRESHOLD" => "int",
    "NEEDY_ITEM_FARMING.POKEBALL_CONTINUE_THRESHOLD" => "int",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_POKEBALL_COUNT" => "bool",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_GREATBALL_COUNT" => "bool",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_ULTRABALL_COUNT" => "bool",
    "NEEDY_ITEM_FARMING.FARM_IGNORE_MASTERBALL_COUNT" => "bool",
    "NEEDY_ITEM_FARMING.FARM_OVERRIDE_STEP_SIZE" => "int",
  ];

  private $experimental = [
    "SKIP_VISITED_FORT_DURATION",
    "SPIN_ALL_FORTS",
    "NEEDY_ITEM_FARMING",
  ];
  /** @var string $file */
  private $file;
  private $fileOpts;

  public function __construct() {
    $file = ROOT . "/../config.json";
    $this->file = $file;
    foreach ($this->namedConfig as $config => $description) {
      $this->namedConfig[$config] = Lng::translate($description);
    }
  }

  public function configFileExists() {
    return file_exists($this->file);
  }

  public function createConfigFile() {
    $data = [
      "accounts" => [
        [
          "auth_service" => "google",
          "username" => "test@gmail.com",
          "password" => "password",
          "location" => "",
          "USE_GOOGLE" => TRUE,
          "GMAPS_API_KEY" => "",
          "KEEP_CP_OVER" => 500,
          "KEEP_IV_OVER" => 50,
          "STEP_SIZE" => 5,
          "EXPERIMENTAL" => TRUE,
          "SKIP_VISITED_FORT_DURATION" => 600,
          "SPIN_ALL_FORTS" => TRUE,
          "STAY_WITHIN_PROXIMITY" => 9999,
          "AUTO_USE_LUCKY_EGG" => FALSE,
          "CAPTURE" => [
            "MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY" => 3,
          ],
          "EGG_INCUBATION" => [
            "ENABLE" => TRUE,
            "USE_DISPOSABLE_INCUBATORS" => FALSE,
            "BIG_EGGS_FIRST" => TRUE,
          ],
          "MIN_ITEMS" => [
            "ITEM_POTION" => 10,
            "ITEM_SUPER_POTION" => 10,
            "ITEM_HYPER_POTION" => 10,
            "ITEM_MAX_POTION" => 20,
            "ITEM_BLUK_BERRY" => 10,
            "ITEM_NANAB_BERRY" => 10,
            "ITEM_REVIVE" => 10,
            "ITEM_MAX_REVIVE" => 10,
            "ITEM_RAZZ_BERRY" => 10,
          ],
          "NEEDY_ITEM_FARMING" => [
            "ENABLE" => FALSE,
            "POKEBALL_CONTINUE_THRESHOLD" => 50,
            "POKEBALL_FARM_THRESHOLD" => 10,
            "FARM_IGNORE_POKEBALL_COUNT" => FALSE,
            "FARM_IGNORE_GREATBALL_COUNT" => FALSE,
            "FARM_IGNORE_ULTRABALL_COUNT" => FALSE,
            "FARM_IGNORE_MASTERBALL_COUNT" => TRUE,
            "FARM_OVERRIDE_STEP_SIZE" => -1,
          ],
          "POKEMON_EVOLUTION" => [
            "PIDGEY" => CandyCount::PIDGEY,
            "WEEDLE" => CandyCount::WEEDLE,
          ],
          "MIN_SIMILAR_POKEMON" => 1,
          "KEEP_POKEMON_NAMES" => [
            "MEWTWO",
          ],
          "THROW_POKEMON_NAMES" => [],
          "LIST_POKEMON_BEFORE_CLEANUP" => FALSE,
          "LIST_INVENTORY_BEFORE_CLEANUP" => FALSE,
          "MAX_CATCH_ATTEMPTS" => 10,
          "RELEASE_DUPLICATES" => FALSE,
          "RELEASE_DUPLICATES_MAX_LV" => 1000,
          "RELEASE_DUPLICATES_SCALER" => 0.9,
          "DEFINE_POKEMON_LV" => "CP",
        ],
      ],
    ];
    file_put_contents($this->file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
  }

  public function getConfig() {
    return $this->namedConfig;
  }

  public function getConfigValue($key) {
    if (!is_array($this->fileOpts)) {
      $data = file_get_contents($this->file);
      $this->fileOpts = json_decode($data, TRUE);
    }
    if (isset($this->fileOpts["accounts"][$this->accountId][$key])) {
      return $this->fileOpts["accounts"][$this->accountId][$key];
    } else {
      if(strpos($key,".") !== false) {
        $newkey = explode(".",$key);
        if(isset($this->fileOpts["accounts"][$this->accountId][$newkey[0]][$newkey[1]])) {
          return $this->fileOpts["accounts"][$this->accountId][$newkey[0]][$newkey[1]];
        }
      }
    }
    throw new ConfigNotFoundException("The specified config ($key) not found in config file.");
  }

  public function getConfigType($config) {
    if (isset($this->configTypes[$config])) {
      return $this->configTypes[$config];
    }
    throw new ConfigNotFoundException("The specified config ($config) not found in config types.");
  }

}