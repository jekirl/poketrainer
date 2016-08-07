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

import thread
import eventlet
from eventlet import wsgi, tpool
import gevent
import zerorpc
from six import PY2, iteritems

from poketrainer.api_wrapper import ApiWrapper
from listener import Listener

import webserver

logger = logging.getLogger(__name__)

poketrainers = []
pool = eventlet.GreenPool()


def init_arguments():
    parser = argparse.ArgumentParser()
    # Read passed in Arguments
    parser.add_argument("-i", "--config_index", help="Index of account to start in config.json", type=int)
    parser.add_argument("-l", "--location",
                        help="Location. Only applies if an account was selected through config_index parameter")
    parser.add_argument("-e", "--encrypt_lib", help="encrypt lib, libencrypt.so/encrypt.dll", default="libencrypt.so")
    parser.add_argument("-w", "--start_webserver",
                        help="Start Webserver. Does not apply if an account was selected through config_index parameter",
                        action='store_true', default=False)
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=False)
    arguments = parser.parse_args()
    return arguments.__dict__, arguments.__dict__['config_index'], arguments.__dict__['start_webserver'], arguments.__dict__['debug']


def main(prev_location=None):
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

    config, config_index, start_webserver, debug = init_config()
    if not config:
        return

    if debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("poketrainer").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)


    #desc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".listeners")
    #sock_port = 0
    #s = socket.socket()
    #s.bind(("", 0))  # let the kernel find a free port
    #sock_port = s.getsockname()[1]
    #s.close()
    #data = {}

    #if os.path.isfile(desc_file):
    #    with open(desc_file, 'r+') as f:
    #        data = f.read()
    #        if PY2:
    #            data = json.loads(data.encode() if len(data) > 0 else '{}')
    #        else:
    #            data = json.loads(data if len(data) > 0 else '{}')
    #data[config["username"]] = sock_port
    #with open(desc_file, "w+") as f:
    #    f.write(json.dumps(data, indent=2))

    # instantiate api wrapper
    #api_wrapper = ApiWrapper(config, prev_location)

    #s = zerorpc.Server(Listener(api_wrapper))
    #s.bind("tcp://127.0.0.1:%i" % sock_port)  # the free port should still be the same
    #gevent.spawn(s.run)

    #poketrainer = Poketrainer(api_wrapper)

    #gevent.spawn(api_wrapper.main_loop)
    #gevent.spawn(poketrainer.main_loop)

    # if config_index is set, start the according thread
    if config_index is not None:
        poketrainer = ApiWrapper(config_index, pool, prev_location)
        poketrainer.open_socket()
        poketrainer.start()
        try:
            poketrainer.thread.wait()
        except KeyboardInterrupt:
            logger.info('Exiting...')
            exit(0)
    # not config_index set, load all accounts
    else:
        # create a class for each account configured
        for config_index, account_config in enumerate(config):
            poketrainers.append(ApiWrapper(config_index, pool, prev_location))

        # start all threads that are configured to auto-start
        for i, account_config in enumerate(config):
            if account_config.get('autostart', False):
                poketrainers[0].start()
                poketrainers.append(ApiWrapper(account_config, pool, prev_location))

        try:
            web_thread = pool.spawn(webserver.main, poketrainers)
            web_thread.wait()
        except KeyboardInterrupt:
            logger.info('Exiting...')


if __name__ == '__main__':
    main()
