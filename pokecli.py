#!/usr/bin/env python
"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>
Modifications Copyright (c) 2016 j-e-k <https://github.com/j-e-k>

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
"""

import os
import re
import json
import collections
import struct
import logging
import requests
import argparse
import tempfile
import zerorpc
import os
import gevent
import socket
from listener import Listener
from time import sleep
from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f
from pgoapi.location import getNeighbors

from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import CellId, LatLng

log = logging.getLogger(__name__)
from threading import Thread
from Queue import Queue


def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    loc = geolocator.geocode(location_name)

    log.info('Your given location: %s', loc.address.encode('utf-8'))
    log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)

    return (loc.latitude, loc.longitude, loc.altitude)


def dict_merge(dct, merge_dct):
    for k, v in merge_dct.iteritems():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]
    return dct


def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load['accounts'][0].keys()
    parser.add_argument("-i", "--config_index", help="Index of account in config.json", default=0, type=int)
    parser.add_argument("-l", "--location", help="Location", required=required("location"))
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true', default=False)
    config = parser.parse_args()
    defaults = load.get('defaults', {})
    account = load['accounts'][config.__dict__['config_index']]
    load = dict_merge(defaults, account)
    # Passed in arguments shoud trump
    for key,value in load.iteritems():
        if key not in config.__dict__ or not config.__dict__[key]:
            config.__dict__[key] = value
    if config.auth_service not in ['ptc', 'google']:
      log.error("Invalid Auth service specified! ('ptc' or 'google')")
      return None

    return config.__dict__


def main(position=None):
    # log settings
    # log format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    config = init_config()
    if not config:
        return

    if config["debug"]:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)


    if not position:
        position = get_pos_by_name(config["location"])


    # instantiate pgoapi
    api = PGoApi(config)

    # provide player position on the earth
    api.set_position(*position)

    desc_file = os.path.dirname(os.path.realpath(__file__))+os.sep+".listeners"
    sock_port = 0
    s=socket.socket()
    s.bind(("", 0)) #let the kernel find a free port
    sock_port = s.getsockname()[1]
    s.close()
    with open(desc_file,'w+') as f:
        data = f.read()
        data = json.loads(data.encode() if len(data) > 0 else '{}')
        data[config["username"]] = sock_port
        f.write(json.dumps(data,indent=2))

    s = zerorpc.Server(Listener(api))
    s.bind("tcp://127.0.0.1:%i"%sock_port) # the free port should still be the same
    gevent.spawn(s.run)

    # retry login every 30 seconds if any errors
    while not api.login(config["auth_service"], config["username"], config["password"]):
        log.error('Retrying Login in 30 seconds')
        sleep(30)

    # main loop
    while True:
        try:
            api.main_loop()
        except Exception as e:
            log.exception('Error in main loop %s, restarting at location: %s', e, api._posf)
            # restart after sleep
            sleep(30)
            try:
                main(api._posf)
            except:
                pass

if __name__ == '__main__':
    main()
