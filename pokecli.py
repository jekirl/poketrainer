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
import logging

import gevent

from helper.colorlogger import create_logger
from poketrainer.poketrainer import Poketrainer

logger = create_logger(__name__, color='red')


def init_arguments():
    parser = argparse.ArgumentParser()
    # Read passed in Arguments
    parser.add_argument("-i", "--config_index", help="Index of account to start in config.json", default=0, type=int)
    parser.add_argument("-l", "--location",
                        help="Location. Only applies if an account was selected through config_index parameter")
    parser.add_argument("-e", "--encrypt_lib", help="encrypt lib, libencrypt.so/encrypt.dll", default="libencrypt.so")
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=False)
<<<<<<< HEAD
    parser.add_argument("-p", "--proxy", help="Use Proxy, proxy_ip:port", default=None)
    config = parser.parse_args()
    defaults = load.get('defaults', {})
    account = load['accounts'][config.__dict__['config_index']]
    load = dict_merge(defaults, account)
    # Passed in arguments shoud trump
    for key, value in iteritems(load):
        if key not in config.__dict__ or not config.__dict__[key]:
            config.__dict__[key] = value
    if config.auth_service not in ['ptc', 'google']:
        logger.error("Invalid Auth service specified! ('ptc' or 'google')")
        return None

    return config.__dict__


def main(position=None):
=======
    arguments = parser.parse_args()
    return arguments.__dict__


def main():
>>>>>>> j-e-k/develop
    # log settings
    # log format

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)10s] [%(levelname)5s] s%(message)s')
    # log level for http request class
    create_logger("requests", log_level=logging.WARNING)
    # log level for pgoapi class
    create_logger("pgoapi", log_level=logging.WARNING)
    # log level for internal pgoapi class
    create_logger("rpc_api", log_level=logging.INFO)

    args = init_arguments()
    if not args:
        return

<<<<<<< HEAD
    if config["debug"]:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)

    if not position:
        position = get_pos_by_name(config["location"])

    # instantiate pgoapi
    api = PGoApi(config)

    # set signature!
    api.activate_signature(config['encrypt_lib'])

    # provide player position on the earth
    api.set_position(*position)

    # set proxy
    if config["proxy"]:
        api.set_proxy(config["proxy"])

    desc_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".listeners")
    sock_port = 0
    s = socket.socket()
    s.bind(("", 0))  # let the kernel find a free port
    sock_port = s.getsockname()[1]
    s.close()
    data = {}

    if os.path.isfile(desc_file):
        with open(desc_file, 'r+') as f:
            data = f.read()
            if PY2:
                data = json.loads(data.encode() if len(data) > 0 else '{}')
            else:
                data = json.loads(data if len(data) > 0 else '{}')
    data[config["username"]] = sock_port
    with open(desc_file, "w+") as f:
        f.write(json.dumps(data, indent=2))

    s = zerorpc.Server(Listener(api))
    s.bind("tcp://127.0.0.1:%i" % sock_port) # the free port should still be the same
    gevent.spawn(s.run)

    # retry login every 30 seconds if any errors
    while not api.login(config["auth_service"], config["username"], config["password"], config["proxy"]):
        logger.error('Retrying Login in 30 seconds')
        sleep(30)

    # main loop
=======
    poketrainer = Poketrainer(args)
    # auto-start bot
    poketrainer.start()
    # because the bot spawns 'threads' so it can start / stop we're making an infinite lop here
>>>>>>> j-e-k/develop
    while True:
        try:
            gevent.sleep(1.0)
        except KeyboardInterrupt:
            logger.info('Exiting...')
            exit(0)


if __name__ == '__main__':
    main()
