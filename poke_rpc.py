import os
import re
import json
import struct
import logging
import requests
import argparse
from time import sleep
from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f
from pgoapi.location import getNeighbors

from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import CellId, LatLng

from threading import Thread
from Queue import Queue

class PokeRPC(object):
    def __init__(self, q):
        super(PokeRPC, self).__init__()
        self.q = q
