# DISCLAIMER, this is super sketch and just a proof of concept. Use at your own risk and I claim no credit or responsibility or what have you for parts of it.

# Don't be a dumbass too, Let's not ruin a good thing...

Usage:

 * Rename `config.json.example` to `config.json`
 * Run the client with `python pokecli.py -i ACCOUNT_INDEX --[cached]`
    * Use `--cached` after you have already logged in once, doing so will cache your login and prevent soft bans
    * The `ACCOUNT_INDEX` is the index of the account you want to use from `config.json` indexing from 0
 * You probably also need an API key for the directions service in `location.py`, check that out

What's working:
 * Walking to pokestops and spinning them
 * Capturing any pokemon it sees on the way
 * Releasing pokemon that you have duplicates of if under CP_CUTOFF (FIXME this is not the best idea....)
  * Change CP_CUTOFF in `pgoapi.py` to configure this, by default it is 9999 (to never release)


## Requirements
 * Run `pip install -r requirements.txt`
 * Python 2
 * requests
 * protobuf
 * gpsoauth
 * geopy (only for pokecli demo)
 * s2sphere (only for pokecli demo)


## Credits
* [tejado](https://github.com/tejado) for the base of this and everything else really
* [Mila432](https://github.com/Mila432/Pokemon_Go_API) for the login secrets  
* [elliottcarlson](https://github.com/elliottcarlson) for the Google Auth PR  
* [AeonLucid](https://github.com/AeonLucid/POGOProtos) for improved protos  
* [AHAAAAAAA](https://github.com/AHAAAAAAA/PokemonGo-Map) for parts of the s2sphere stuff
* And to anyone on the pokemongodev slack channel <3
