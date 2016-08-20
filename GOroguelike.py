#!/usr/bin/env python
# Created from pokecli.py by @stolencatkarma

import json
import logging

import gevent

from helper.colorlogger import create_logger
from poketrainer.poketrainer import Poketrainer

poketrainer = {}
logger = create_logger(__name__, color='white')


def init_poketrainer():
    global poketrainer
    logger.info('Parsing config.json')
    try:
        with open('config.json') as data_file:
            data = json.load(data_file)
        # print(data)
    except Exception:
        logger.error("Could not parse config.json - please make sure it's setup correctly.")
        raise

    for account in data['accounts']:
        logger.info('Found login info for ' + str(account['username']))
        arguments = {}
        # Read passed in Arguments
        arguments['config_index'] = 0
        arguments['encrypt_lib'] = 'libencrypt.so'
        arguments['auth_service'] = account['auth_service']
        arguments['location'] = account['location']
        arguments['debug'] = False
        poketrainer = Poketrainer(arguments)
        # auto-start bot
        # poketrainer.start()
        continue


def main():
    # log settings
    # log format
    logging.basicConfig(level=logging.INFO, format='[%(module)10s] [%(levelname)5s] s%(message)s')
    # log level for http request class
    create_logger("requests", log_level=logging.WARNING)
    # log level for pgoapi class
    create_logger("pgoapi", log_level=logging.WARNING)
    # log level for internal pgoapi class
    create_logger("rpc_api", log_level=logging.INFO)

    init_poketrainer()
    # because the bot spawns 'threads' so it can start / stop we're making an infinite loop here
    while True:
        try:
            poketrainer._heartbeat()
            user_input = raw_input("\nWhat would you like to do next? (look, walk, run, catch, spin): ")  # or `input("Some...` in python 3
            if(user_input == 'look'):
                lookaround()
            elif(user_input == 'catch'):
                catchpoke()
            elif(user_input == 'walk'):
                walk()
            elif(user_input == 'run'):
                run()
            gevent.sleep(1.0)
        except KeyboardInterrupt:
            logger.info('Exiting...')
            exit(0)


def walk():
    logger.info('You walk along the path towards your next goal.')
    poketrainer.fort_walker.loop()


def run():
    poketrainer.fort_walker.loop()
    poketrainer.fort_walker.loop()
    poketrainer.fort_walker.loop()


def lookaround():
    global poketrainer
    logger.info('You scan the horizon all around you.')
    res = poketrainer.map_objects.nearby_map_objects()['responses']['GET_MAP_OBJECTS']['map_cells'][0]
    forts = res['forts']
    spawn_points = res['spawn_points']
    # logger.info("forts: %s", forts)
    if(forts is not None):
        for fort in forts:
            if('type' in fort):
                logger.info('You see a Pokestop.')
            else:
                logger.info('You see a Gym.')
    # logger.info("catchable_pokemons: %s", catchable_pokemons)
    if(spawn_points is not None):
        for spawn_point in spawn_points:
            logger.debug('You see a spawn_points.')


def catchpoke():
    global poketrainer
    poketrainer.poke_catcher.catch_all()

if __name__ == '__main__':
    main()
