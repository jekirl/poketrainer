# Please do not sell the bot, or use it to sell accounts/power leveling or what have you. If you really can't help yourself from trying to make money on it, please donate a portion of your profits to [Kiva](https://www.kiva.org/).
## To the people that have done so already (heard from quite a few already), thank you for making the world a better place.

----

# DISCLAIMER: <del>this is super sketch and just a proof of concept</del> It's not that bad any more, but still, use at your own risk and I claim no credit or responsibility or what have you for parts of it.

## For Contributions: Please open pull request to develop branch not *master* Thank you!

# Don't be a dumbass too, Let's not ruin a good thing...

----

[![Build Status](https://travis-ci.org/j-e-k/poketrainer.svg?branch=master)](https://travis-ci.org/infinitewarp/poketrainer)


 #### Rename `config.json.example` to `config.json`
```
usage: python pokecli.py [-h] [-i CONFIG_INDEX] [-l LOCATION] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -i CONFIG_INDEX, --config_index CONFIG_INDEX
                        Index of account in config.json
  -l LOCATION, --location LOCATION
                        Location
  -d, --debug           Debug Mode
```

### Web UI
 * Run python web.py to get a webservice to show you player information, this can be seen at:
  * http://127.0.0.1:5000/YOUR_USERNAME_HERE
  * Only 1 needs to run regardless of how many bots you are running

----

## Configuration

Copy config.json.example to config.json and change your account information.
Below the accounts you can change options in the `default` section. If you need to change some options for an individual account, you can copy them to the account section and modify as needed.

#### Configuration options (non-exhaustive)

* `BEHAVIOR` section
   * `USE_GOOGLE` will enable google walking directions for navigation
     * You will probably need to provide an api key in `GMAPS_API_KEY` to avoid rate limits
   * `STEP_SIZE` corresponds to how many meters you want to move at most between server calls, set this around 4-6 for walking or 100-200 for really, really fast driving
   * `WANDER_STEPS` will set the distance a pokestop can be away before and still allow us to wander off the walk path. This allows you to get pokestops that aren't close to the sidewalk/road. If you don't set it we won't wander off the path.
   * `EXPERIMENTAL` will set the flag to use exeperimental features
   * `SKIP_VISITED_FORT_DURATION` [Experimental] Avoid a fort for a given number of seconds
     * Setting this to 500 means avoid a fort for 500 seconds before returning, (Should be higher than 300 to have any effect). This will let the bot explore a bigger area.
   * `SPIN_ALL_FORTS` [Experimental] will try to route using google maps(must have key) to all visible forts, if `SKIP_VISITED_FORT_DURATION` is set high enough, you may roam around forever.
* `CAPTURE`
   * `CATCH_POKEMON` Allows you to disabling catching pokemon if you just want to mine for the forts for pokeballs
   * `MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY` minimum number of failed capture attempts before trying to use a Razz Berry (default: 3)
* `EGG_INCUBATION`
   * `ENABLE` enables automatic use of incubators (default: true)
   * `USE_DISPOSABLE_INCUBATORS` enables use of disposable (3-times use) incubators (default: false)
   * `BIG_EGGS_FIRST` incubate big eggs (most km) first (default: true)
* `POKEMON_CLEANUP`
   * `KEEP_POKEMON_NAMES` Names of pokemon you want the bot to hold regardless of IV/CP
   * `THROW_POKEMON_NAMES` Names of pokemon you want the bot to throw away regardless of IV/CP
     * Note: `MIN_SIMILAR_POKEMON` will still be kept for all pokemon types
   * `KEEP_POKEMON_MAX_COUNT` default 9999. If you want to keep a certain type of pokemon but you accidently run into a nest? Don't worry this will make sure you only keep X amount of pokemon specified in `KEEP_POKEMON__NAMES`
   * `RELEASE_METHOD` = "CLASSIC", if you are unsure about the other methods you should stick to this one!
     * `KEEP_CP_OVER` Never transfer any pokemon above this CP, Setting this to 0 will never transfer anything
     * `KEEP_IV_OVER` Never transfer any pokemon above this C IV, Setting this to 0 will never transfer anything
   * `RELEASE_METHOD` = "DUPLICATES"
     * The bot will collect all pokemon it encounters , thus collecting a ton of bad ones and filling up space. Enabling this feature (disabled by default) will have the bot automatically transfer pokemon that are duplicates. To determine which pokemon to transfer when duplicates exist, the pokemons are compared according to the `SCORE_METHOD` setting.  The bot will transfer the lowest scoring pokemon, maintaining `MIN_SIMILAR_POKEMON` of each type. To be completely confident that the bot will not transfer your high lvl pokemon, when this feature is enabled only pokemon with a score below `RELEASE_DUPLICATES_MAX_SCORE` are released. If you have multiple pokemon that are close to the same lvl the bot can be configured to not transfer them by using `RELEASE_DUPLICATES_SCALAR`. The value of this config is multiplied by the highest scoring pokemon of a type and only those pokemon that are less than the scaled score are transfered.
     * EXAMPlES: If you set `SCORE_METHOD` to "IV" while having two Snorlaxs, one with stats CP:14 IV:95 and the other with CP:1800 IV:30 the bot will transfer the Snorlax with CP of 1800 and keep the CP 14 Snorlax because you have indicated you only care about a pokemon's IV. It must be fully understood why this happens to avoid unwanted transfer of pokemon. If not used correctly this feature can very easily transfer a large ammount of your pokemon so please make sure you fully understand it's mechanics before attempting use!
   * `RELEASE_METHOD` = "ADVANCED", this method allows you to keep a minimum amount of pokemon basen on their CP *or* IV
     * `ALWAYS_RELEASE_BELOW_LEVEL` This will release all pokemon below a specified level, ignoring all below options. A pokemon level can range from 1-40 for all pokemon types. For reference you can check [this table](https://docs.google.com/spreadsheets/d/19iql4aABmZ5oZ6YDE3LmZ8qcth3UoH52954WhjuiJow/edit#gid=1488557536) to see how much CP each pokemon will have on different levels. Using Level provides an easy way to filter bad pokemons across all pokemon types.
     * `KEEP_CP_OVER` Don't transfer any pokemon above this CP (this will apply no matter what you set in `BEST_CP`)
     * `KEEP_IV_OVER` Don't transfer any pokemon above this IV (this will apply no matter what you set in `BEST_IV`)
     * `BEST_CP` Additional options for keeping pokemon based on their CP
        * `MIN_AMOUNT` Minimum amount of pokemon to keep by CP
        * `KEEP_ADDITIONAL_SCALAR` The value of this config is multiplied by the highest CP pokemon of a type and only those pokemon that are less than the scaled score are transfered.
        * `MAX_AMOUNT` Maximum amount of pokemon to keep by CP
     * `BEST_IV` Additional options for keeping pokemon based on their IV
        * `MIN_AMOUNT` Minimum amount of pokemon to keep by IV
        * `KEEP_ADDITIONAL_SCALAR` The value of this config is multiplied by the highest IV pokemon of a type and only those pokemon that are less than the scaled score are transfered.
        * `MAX_AMOUNT` Maximum amount of pokemon to keep by IV
        * `IGNORE_BELOW` Pokemon with lover IV than this will be ignored by `MIN_AMOUNT` and `KEEP_ADDITIONAL_SCALAR`
   * `SCORE_METHOD`
     * A pokemon's score is an arbitrary and configurable parameter defines how to sort pokemon by best > worst to decide which one to keep first. Possible values are "CP", "IV", "CPxIV", or "CP+IV" or the special "FANCY" method.
     * The "FANCY" method uses the options a `WEIGHT_IV` and `WEIGHT_LVL` which give the ability to specifically set more weight on Lvl or IV. The formula is as follows: `(iv / 100.0 * SCORE_WEIGHT_IV) + level / (player_level+1.5) * SCORE_WEIGHT_LVL` where player_level+1.5 is the max level that pokemon can reach when fully powered up.
* `NEEDY_ITEM_FARMING` [Experimental] will cease trying to catch pokemon and roam around to collect more pokeballs when inventory is low
   * `ENABLE` : `Boolean`, whether or not this feature is enabled
   * `POKEBALL_FARM_THRESHOLD` : `Integer`, when the observed pokeball count drops on or below this number, skip catching pokemon and begin collecting.
   * `POKEBALL_CONTINUE_THRESHOLD`: `Integer`, when the observed pokeball count reaches this amount, stop farming and go back to catching pokemon.
   * `FARM_IGNORE_POKEBALL_COUNT`: `Boolean`, Whether to include this ball in counting. Same goes for `GREATBALL`, `ULTRABALL`, and `MASTERBALL`. Masterball is ignored by default.
   * `FARM_OVERRIDE_STEP_SIZE`: `Integer`, When it goes into farming mode, the bot assumes this step size to potentially speed up resource gathering. _This might lead to softbans._ Setting to `-1` disables this feature. Disabled by default for safety.
   * If `EXPERIMENTAL` OR `CATCH_POKEMON` are false, this configuration will disable itself.

There are more options, check the current config.json.example, many are self-explanatory.


## Requirements
 * Run `pip install -r requirements.txt`
 * Python 2.7 or 3.5
 * requests
 * protobuf
 * gpsoauth
 * geopy (only for pokecli demo)
 * s2sphere (only for pokecli demo)

### Python 2 vs 3

Although this project was originally built for Python 2.7, we have recently added support for Python 3.5. However, our tools that allow `web.py` to talk with `pokecli.py` currently require them to run on the *same version* of Python. So, if you choose to use Python 3 for one of them, you must use it for both of them (and vice versa for Python 2).


### keeping the code clean
If you make changes to the Python code, please use [tox](https://tox.readthedocs.io/)
to run [flake8](http://flake8.pycqa.org/) and [isort](https://github.com/timothycrosley/isort)
checks against the code. If you see any errors, please fix them before opening a
pull request.

To run tox, just install the package and run the `tox` command from the root
directory of the project. tox will automatically install `flake8` and `isort`
packages into a virtual environment as needed when it runs.
```
pip install tox
tox
```

If you are not updating the Python code, you do not need to install or use tox.


### pokecli with Docker (optional)
Build and run container:

    docker build -t pokecli .
    docker run pokecli

Optionally create an alias:

    alias pokecli='docker run pokecli'

For Chosing what Items to keep, get the names here, [AeonLucidProtos_ItemID](https://github.com/AeonLucid/POGOProtos/blob/master/src/POGOProtos/Inventory/Item/ItemId.proto)
For Choosing what pokemon to keep get the names here,[AeonLucidProtos_Pokemon](https://github.com/AeonLucid/POGOProtos/blob/master/src/POGOProtos/Enums/PokemonId.proto)

Put them in config. Type exactly as the name appears

### What's working:
What's working:
 * A lot of things. Check out the example config to see some of the features. Catching Lured pokemon, sniping, regular pokemon, multiple kinds of navigation (google maps, walking, driving, customized speed), a web ui, auto transfers, auto evolves, auto power ups, auto egg incubation, inventory managament, multiple account botting. And much more, README to be updated soon.

----


### Join slack channel:
  To ask question  related  to api and general help, join Pokemon Go Reverse Engineering Slack team.
 * To join, get a invite from [here](https://shielded-earth-81203.herokuapp.com/) , join team via the email you recieve and then signin [here](https://pkre.slack.com).



## Credits
* [tejado](https://github.com/tejado) for the base of this
* [elliottcarlson](https://github.com/elliottcarlson) for the Google Auth PR
* [AeonLucid](https://github.com/AeonLucid/POGOProtos) for improved protos
* [AHAAAAAAA](https://github.com/AHAAAAAAA/PokemonGo-Map) for parts of the s2sphere stuff
* [beeedy](https://github.com/beeedy) for ability to transfer duplicate pokemon
* [infinitewarp](https://github.com/infinitewarp) for introducing tox and cleaning up the code
* And to anyone on the pokemongodev slack channel <3

>>>>>>> super sketch but yolo
