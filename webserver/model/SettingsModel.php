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

    "GMAPS_API_KEY" => "Google Maps API key (only needed if using Google for directions)",

    "BEHAVIOR.USE_GOOGLE" => "Use Google for directions?",
    "BEHAVIOR.STEP_SIZE" => "How many meters per second should the bot walk?",
    "BEHAVIOR.EXPERIMENTAL" => "Allow experimental features?",
    "BEHAVIOR.SKIP_VISITED_FORT_DURATION" => "Avoid a PokéStop for a given number of seconds. This allows bot to explore bigger area.",
    "BEHAVIOR.SPIN_ALL_FORTS" => "Bot will try to route using Google Maps to all visible PokéStops",
    "BEHAVIOR.STAY_WITHIN_PROXIMITY" => "The bot will not travel further than the meters you specify",
    "BEHAVIOR.AUTO_USE_LUCKY_EGG" => "Can the bot use Lucky Eggs?",

    "CAPTURE.CATCH_POKEMON" => "Should the bot catch Pokémon?",
    "CAPTURE.MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY" => "After this count of failed captures the bot will use Razz Berry (default 3)",
    "CAPTURE.MAX_CATCH_ATTEMPTS" => "How many attepts to catch Pokémon before leaving him alone?",

    "EGG_INCUBATION.ENABLE" => "Can the bot hatch eggs?",
    "EGG_INCUBATION.USE_DISPOSABLE_INCUBATORS" => "Can the bot use incubators with limited use?",
    "EGG_INCUBATION.BIG_EGGS_FIRST" => "Should the bot first hatch eggs with higher km range?",

    "POKEMON_EVOLUTION" => "Which Pokémon should the bot evolve?",

    "POKEMON_CLEANUP.MIN_SIMILAR_POKEMON" => "How many Pokémon of the same type should the bot keep? Other settings can alter the behavior of this",
    "POKEMON_CLEANUP.KEEP_POKEMON_NAMES" => "Which Pokémon should the bot keep always?",
    "POKEMON_CLEANUP.THROW_POKEMON_NAMES" => "Which Pokémon should the bot always transfer?",
    "POKEMON_CLEANUP.RELEASE_METHOD" => "What method to use for releasing? Classic means via CP and IV, duplicates means via level and scaler",

    "POKEMON_CLEANUP.RELEASE_METHOD_CLASSIC.KEEP_CP_OVER" => "Keep Pokémon with CP higher than this value",
    "POKEMON_CLEANUP.RELEASE_METHOD_CLASSIC.KEEP_IV_OVER" => "Keep Pokémon with IV higher than this value",

    "POKEMON_CLEANUP.RELEASE_METHOD_DUPLICATES.RELEASE_DUPLICATES_MAX_SCORE" => "Pokémon with level higher than this value will not be transfered",
    "POKEMON_CLEANUP.RELEASE_METHOD_DUPLICATES.RELEASE_DUPLICATES_SCALAR" => "This value is multiplied by the highest level Pokémon of a type and only those Pokémon that are less than the scaled level are transfered",
    "POKEMON_CLEANUP.SCORE_METHOD" => "Defines what metrics to use for releasing Pokémon",

    "MIN_ITEMS.ITEM_POTION" => "How many potions should the bot keep?",
    "MIN_ITEMS.ITEM_SUPER_POTION" => "How many super potions should the bot keep?",
    "MIN_ITEMS.ITEM_HYPER_POTION" => "How many hyper potions should the bot keep?",
    "MIN_ITEMS.ITEM_MAX_POTION" => "How many max potions should the bot keep?",
    "MIN_ITEMS.ITEM_BLUK_BERRY" => "How many bluk berries should the bot keep?",
    "MIN_ITEMS.ITEM_NANAB_BERRY" => "How many nanab berries should the bot keep?",
    "MIN_ITEMS.ITEM_REVIVE" => "How many revives should the bot keep?",
    "MIN_ITEMS.ITEM_MAX_REVIVE" => "How many max revives should the bot keep?",
    "MIN_ITEMS.ITEM_RAZZ_BERRY" => "How many razz berries should the bot keep?",

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
        "google" => "Google",
      ],
    ],
    "username" => "text",
    "password" => "password",
    "location" => "text",

    "GMAPS_API_KEY" => "text",

    "BEHAVIOR.USE_GOOGLE" => "bool",
    "BEHAVIOR.STEP_SIZE" => "int",
    "BEHAVIOR.EXPERIMENTAL" => "bool",
    "BEHAVIOR.SKIP_VISITED_FORT_DURATION" => "int",
    "BEHAVIOR.SPIN_ALL_FORTS" => "bool",
    "BEHAVIOR.STAY_WITHIN_PROXIMITY" => "int",
    "BEHAVIOR.AUTO_USE_LUCKY_EGG" => "bool",

    "CAPTURE.CATCH_POKEMON" => "bool",
    "CAPTURE.MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY" => "int",
    "CAPTURE.MAX_CATCH_ATTEMPTS" => "int",

    "EGG_INCUBATION.ENABLE" => "bool",
    "EGG_INCUBATION.USE_DISPOSABLE_INCUBATORS" => "bool",
    "EGG_INCUBATION.BIG_EGGS_FIRST" => "bool",

    "POKEMON_EVOLUTION" => [
      "type" => "select",
      "options" => [
        "null" => "Not yet implemented",
      ],
    ],

    "POKEMON_CLEANUP.MIN_SIMILAR_POKEMON" => "int",
    "POKEMON_CLEANUP.KEEP_POKEMON_NAMES" => [
      "type" => "select",
      "options" => [
        "null" => "Not implemented yet",
      ],
    ],
    "POKEMON_CLEANUP.THROW_POKEMON_NAMES" => [
      "type" => "select",
      "options" => [
        "null" => "Not implemented yet",
      ],
    ],
    "POKEMON_CLEANUP.RELEASE_METHOD" => [
      "type" => "select",
      "options" => [
        "CLASSIC" => "Classic",
        "DUPLICATES" => "Duplicates",
      ],
    ],

    "POKEMON_CLEANUP.RELEASE_METHOD_CLASSIC.KEEP_CP_OVER" => "int",
    "POKEMON_CLEANUP.RELEASE_METHOD_CLASSIC.KEEP_IV_OVER" => "int",

    "POKEMON_CLEANUP.RELEASE_METHOD_DUPLICATES.RELEASE_DUPLICATES_MAX_SCORE" => "int",
    "POKEMON_CLEANUP.RELEASE_METHOD_DUPLICATES.RELEASE_DUPLICATES_SCALAR" => "float",
    "POKEMON_CLEANUP.SCORE_METHOD" => [
      "type" => "select",
      "options" => [
        "CP" => "CP",
        "IV" => "IV",
        "CPxIV" => "CP * IV",
        "CP+IV" => "CP + IV",
      ],
    ],

    "MIN_ITEMS.ITEM_POTION" => "int",
    "MIN_ITEMS.ITEM_SUPER_POTION" => "int",
    "MIN_ITEMS.ITEM_HYPER_POTION" => "int",
    "MIN_ITEMS.ITEM_MAX_POTION" => "int",
    "MIN_ITEMS.ITEM_BLUK_BERRY" => "int",
    "MIN_ITEMS.ITEM_NANAB_BERRY" => "int",
    "MIN_ITEMS.ITEM_REVIVE" => "int",
    "MIN_ITEMS.ITEM_MAX_REVIVE" => "int",
    "MIN_ITEMS.ITEM_RAZZ_BERRY" => "int",

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
    "BEHAVIOR.SKIP_VISITED_FORT_DURATION",
    "BEHAVIOR.SPIN_ALL_FORTS",
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
          "username" => "",
          "password" => "",
          "location" => "",
          "GMAPS_API_KEY" => "",
          "BEHAVIOR" => [
            "USE_GOOGLE" => TRUE,
            "STEP_SIZE" => 5,
            "WANDER_STEPS" => 0,
            "EXPERIMENTAL" => TRUE,
            "SKIP_VISITED_FORT_DURATION" => 600,
            "SPIN_ALL_FORTS" => TRUE,
            "STAY_WITHIN_PROXIMITY" => 9999,
            "AUTO_USE_LUCKY_EGG" => FALSE,
          ],
          "CAPTURE" => [
            "CATCH_POKEMON" => TRUE,
            "MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY" => 3,
            "MAX_CATCH_ATTEMPTS" => 10,
          ],
          "EGG_INCUBATION" => [
            "ENABLE" => TRUE,
            "USE_DISPOSABLE_INCUBATORS" => FALSE,
            "BIG_EGGS_FIRST" => TRUE,
          ],
          "POKEMON_EVOLUTION" => [
            "PIDGEY" => CandyCount::PIDGEY,
            "WEEDLE" => CandyCount::WEEDLE,
          ],
          "POKEMON_CLEANUP" => [
            "MIN_SIMILAR_POKEMON" => 1,
            "MAX_SIMILAR_POKEMON" => 999,
            "KEEP_POKEMON_NAMES" => ["MEWTWO"],
            "THROW_POKEMON_NAMES" => [],
            "RELEASE_METHOD" => "CLASSIC",
            "RELEASE_METHOD_CLASSIC" => [
              "KEEP_CP_OVER" => 500,
              "KEEP_IV_OVER" => 50,
              "KEEP_IV_ONLY_WITH_PERCENT_CP" => 20,
              "MAX_POKEMON_HIGH_IV" => 999,
            ],
            "RELEASE_METHOD_DUPLICATES" => [
              "RELEASE_DUPLICATES_MAX_SCORE" => 1000,
              "RELEASE_DUPLICATES_SCALAR" => 0.9,
            ],
            "SCORE_METHOD" => "CP",
            "SCORE_METHOD_FANCY" => [
              "WEIGHT_IV" => 0.5,
              "HEIGHT_IV" => 0.5,
            ],
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
          "CONSOLE_OUTPUT" => [
            "LIST_POKEMON_BEFORE_CLEANUP" => FALSE,
            "LIST_INVENTORY_BEFORE_CLEANUP" => FALSE,
          ],
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
    }
    else {
      if (strpos($key, ".") !== FALSE) {
        $newkey = explode(".", $key);
        $count = count($newkey);
        if($count == 2) {
          if (isset($this->fileOpts["accounts"][$this->accountId][$newkey[0]][$newkey[1]])) {
            return $this->fileOpts["accounts"][$this->accountId][$newkey[0]][$newkey[1]];
          }
        } else if($count == 3) {
          if (isset($this->fileOpts["accounts"][$this->accountId][$newkey[0]][$newkey[1]][$newkey[2]])) {
            return $this->fileOpts["accounts"][$this->accountId][$newkey[0]][$newkey[1]][$newkey[2]];
          }
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