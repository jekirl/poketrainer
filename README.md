# Please do not sell the bot, or use it to sell accounts/power leveling or what have you. If you really can't help yourself from trying to make money on it, please donate a portion of your profits to [Kiva](https://www.kiva.org/).
## To the people that have done so already (heard from quite a few already), thank you for making the world a better place.

----

# DISCLAIMER, this is super sketch and just a proof of concept. Use at your own risk and I claim no credit or responsibility or what have you for parts of it.

## For Contributions: Please open pull request to develop branch not *master* Thank you!

# Don't be a dumbass too, Let's not ruin a good thing...

Usage:

 * Rename `config.json.example` to `config.json`
 * Run the client with `python pokecli.py -i ACCOUNT_INDEX --[cached]`
    * Use `--cached` after you have already logged in once, doing so will cache your login and prevent soft bans
    * The `ACCOUNT_INDEX` is the index of the account you want to use from `config.json` indexing from 0
    * USE_GOOGLE will enable google walking directions for navigation
     * You will probably need to provide an api key in `GMAPS_API_KEY` to avoid rate limits
    * `STEP_SIZE` corresponds to how many meters you want to move at most between server calls, set this around 4-6 for walking or 100-200 for really, really fast driving
    * `MIN_KEEP_IV` is the minimum pokemon IV that you want to keep, note that the highest CP pokemon you have will always be kept regardless of its IV
     * Setting this to 0 will never transfer anything
    * `KEEP_CP_OVER` Never transfer any pokemon above this CP
     * Setting this to 0 will never transfer anything
    * `EXERIMENTAL` will set the flag to use exeperimental features
    * `SKIP_VISITED_FORT_DURATION` [Experimental] Avoid a fort for a given number of seconds
     * Setting this to 500 means avoid a fort for 500 seconds before returning, (Should be higher than 300 to have any effect). This will let the bot explore a bigger area.
    * `SPIN_ALL_FORTS` [Experimental] will try to route using google maps(must have key) to all visible forts, if `SKIP_VISITED_FORT_DURATION` is set high enough, you may roam around forever.
    * `KEEP_POKEMON_IDS` IDs of pokemon you want the bot to hold regardless of IV/CP

 * Run python web.py to get a webservice to show you player information, this can be seen at:
  * http://127.0.0.1:5000/YOUR_USERNAME_HERE/pokemon
  * Only 1 needs to run regardless of how many bots you are running


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
 * Walking to pokestops and spinning them
 * Capturing any pokemon it sees on the way
 * Releasing pokemon that you have duplicates of if under CP_CUTOFF (FIXME this is not the best idea....)
  * Change CP_CUTOFF in `pgoapi.py` to configure this, by default it is 0 (to never release)
 * And other stufff, readme needs to be updated...

## Credits
* [tejado](https://github.com/tejado) for the base of this and everything else really
* [Mila432](https://github.com/Mila432/Pokemon_Go_API) for the login secrets  
* [elliottcarlson](https://github.com/elliottcarlson) for the Google Auth PR  
* [AeonLucid](https://github.com/AeonLucid/POGOProtos) for improved protos  
* [AHAAAAAAA](https://github.com/AHAAAAAAA/PokemonGo-Map) for parts of the s2sphere stuff
* And to anyone on the pokemongodev slack channel <3

>>>>>>> super sketch but yolo
