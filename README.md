# Please do not sell the bot, or use it to sell accounts/power leveling or what have you. If you really can't help yourself from trying to make money on it, please donate a portion of your profits to [Kiva](https://www.kiva.org/).
## To the people that have done so already (heard from quite a few already), thank you for making the world a better place.

----

# DISCLAIMER: <del>this is super sketch and just a proof of concept</del> It's not that bad any more, but still, use at your own risk and I claim no credit or responsibility or what have you for parts of it.

## For Contributions: Please open pull request to develop branch not *master* Thank you!

# Don't be a dumbass too, Let's not ruin a good thing...

----

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
  * http://127.0.0.1:5000/YOUR_USERNAME_HERE/pokemon
  * Only 1 needs to run regardless of how many bots you are running

----


* Configuration (non-exhaustive)
    * USE_GOOGLE will enable google walking directions for navigation
     * You will probably need to provide an api key in `GMAPS_API_KEY` to avoid rate limits
    * `STEP_SIZE` corresponds to how many meters you want to move at most between server calls, set this around 4-6 for walking or 100-200 for really, really fast driving
    * `WANDER_STEPS` will set the distance a pokestop can be away before and still allow us to wander off the walk path. This allows you to get pokestops that aren't close to the sidewalk/road. If you don't set it we won't wander off the path.
    * `MIN_KEEP_IV` is the minimum pokemon IV that you want to keep, note that the highest CP pokemon you have will always be kept regardless of its IV
     * Setting this to 0 will never transfer anything
    * `KEEP_CP_OVER` Never transfer any pokemon above this CP
     * Setting this to 0 will never transfer anything
    * `EXPERIMENTAL` will set the flag to use exeperimental features
    * `SKIP_VISITED_FORT_DURATION` [Experimental] Avoid a fort for a given number of seconds
     * Setting this to 500 means avoid a fort for 500 seconds before returning, (Should be higher than 300 to have any effect). This will let the bot explore a bigger area.
    * `SPIN_ALL_FORTS` [Experimental] will try to route using google maps(must have key) to all visible forts, if `SKIP_VISITED_FORT_DURATION` is set high enough, you may roam around forever.
    * `KEEP_POKEMON_IDS` IDs of pokemon you want the bot to hold regardless of IV/CP
    * `CATCH_POKEMON` Allows you to disabling catching pokemon if you just want to mine for the forts for pokeballs
    * `EGG_INCUBATION`
     * `ENABLE` enables automatic use of incubators (default: true)
     * `USE_DISPOSABLE_INCUBATORS` enables use of disposable (3-times use) incubators (default: false)
     * `BIG_EGGS_FIRST` incubate big eggs (most km) first (default: true)
    * `RELEASE_DUPLICATES` The bot seems to have a bad habit of hoarding pokemon. Enabling this feature (disabled by default) will have the bot automatically transfer pokemon that are duplicates. To determine which pokemon to transfer when duplicates exist, the lvl's of the pokemon are compared. A pokemon's lvl is an arbitrary and configurable parameter that can either be representative of a pokemon's CP, IV, CPxIV, or CP+IV. The bot will transfer the lowest lvl pokemon, maintaining` MIN_SIMILAR_POKEMON` of each type. To be completely confident that the bot will not transfer your high lvl pokemon, when this feature is enabled only pokemon with a lvl below `RELEASE_DUPLICATES_MAX_LVL`. If you have multiple pokemon that are close to the same lvl the bot can be configured to not transfer them by using `RELEASE_DUPLICATES_SCALER`. The value of this config is multiplied by the highest lvl pokemon of a type and only those pokemon that are less than the scaled lvl are transfered.
     * EXAMPlES: If you set lvl to "IV" while having two Snorlaxs, one with stats CP:14 IV:95 and the other with CP:1800 IV:30 the bot will transfer the Snorlax with CP of 1800 and keep the CP 14 Snorlax because you have indicated you only care about a pokemon's IV. It must be fully understood why this happens to avoid unwanted transfer of pokemon. If not used correctly this feature can very easily transfer a large ammount of your pokemon so please make sure you fully understand it's mechanics before attempting use!
    * `NEEDY_ITEM_FARMING` [Experimental] will cease trying to catch pokemon and roam around to collect more pokeballs when inventory is low
     * `ENABLE` : `Boolean`, whether or not this feature is enabled
     * `POKEBALL_FARM_THRESHOLD` : `Integer`, when the observed pokeball count drops on or below this number, skip catching pokemon and begin collecting.
     * `POKEBALL_CONTINUE_THRESHOLD`: `Integer`, when the observed pokeball count reaches this amount, stop farming and go back to catching pokemon.
     * `FARM_IGNORE_POKEBALL_COUNT`: `Boolean`, Whether to include this ball in counting. Same goes for `GREATBALL`, `ULTRABALL`, and `MASTERBALL`. Masterball is ignored by default.
     * `FARM_OVERRIDE_STEP_SIZE`: `Integer`, When it goes into farming mode, the bot assumes this step size to potentially speed up resource gathering. _This might lead to softbans._ Setting to `-1` disables this feature. Disabled by default for safety.
     * If `EXPERIMENTAL` OR `CATCH_POKEMON` are false, this configuration will disable itself.

## Requirements
 * Run `pip install -r requirements.txt`
 * Python 2
 * requests
 * protobuf
 * gpsoauth
 * geopy (only for pokecli demo)
 * s2sphere (only for pokecli demo)

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
 * A lot of things. Check out the example config to see some of the features. Catching Lured pokemon, regular pokemon, multiple kinds of navigation (google maps, walking, driving, customized speed), a web ui, auto transfers, auto evolves, auto power ups, auto egg incubation, inventory managament, multiple account botting. And much more, README to be updated soon

## Chatting with us:
We're hanging out at the [Pokemon GO Reverse Engineering team on Slack](https://pkre.slack.com). [Need an invite?](https://shielded-earth-81203.herokuapp.com/)

## Credits
* [tejado](https://github.com/tejado) for the base of this
* [elliottcarlson](https://github.com/elliottcarlson) for the Google Auth PR  
* [AeonLucid](https://github.com/AeonLucid/POGOProtos) for improved protos  
* [AHAAAAAAA](https://github.com/AHAAAAAAA/PokemonGo-Map) for parts of the s2sphere stuff
* [beeedy](https://github.com/beeedy) for ability to transfer duplicate pokemon
* And to anyone on the pokemongodev slack channel <3

>>>>>>> super sketch but yolo
