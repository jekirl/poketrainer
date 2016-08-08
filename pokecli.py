#!/usr/bin/env python
"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>
Modifications Copyright (c) 2016 j-e-k <https://github.com/j-e-k>
Modifications Copyright (c) 2016 Brad Smith <https://github.com/infinitewarp>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
Modifications by: j-e-k <https://github.com/j-e-k>
Modifications by: Brad Smith <https://github.com/infinitewarp>
"""

import argparse
import collections
import json
import logging
import os
import os.path
import socket
from time import sleep

import eventlet
import gevent

from poketrainer.poketrainer import Poketrainer

logger = logging.getLogger(__name__)


def init_arguments():
    parser = argparse.ArgumentParser()
    # Read passed in Arguments
    parser.add_argument("-i", "--config_index", help="Index of account to start in config.json", default=0, type=int)
    parser.add_argument("-l", "--location",
                        help="Location. Only applies if an account was selected through config_index parameter")
    parser.add_argument("-e", "--encrypt_lib", help="encrypt lib, libencrypt.so/encrypt.dll", default="libencrypt.so")
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=False)
    arguments = parser.parse_args()
    return arguments.__dict__


def main():
    # log settings
    # log format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.WARNING)
    # log level for main bot class
    logging.getLogger("poketrainer").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    args = init_arguments()
    if not args:
        return

    poketrainer = Poketrainer(args)
    # auto-start bot
    poketrainer.start()
    # because the bot spawns 'threads' so it can start / stop we're making an infinite lop here
    while True:
        try:
            #eventlet.sleep(1.0)
            gevent.sleep(1.0)
        except KeyboardInterrupt:
            logger.info('Exiting...')
            exit(0)


if __name__ == '__main__':
    main()
