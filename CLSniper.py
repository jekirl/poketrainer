# You must have both pokecli.py and web.py running for this to work.
# original by @sontek
# modified by @stolencatkarma

import time
from datetime import datetime
from multiprocessing import Process

import pylru
import requests
from dateutil import parser

# EDIT ONLY THESE TWO THINGS
users = [
    'webpyusername1',
    'webpyusername2',
    'webpyusername3'
]
blacklist = ['rattata', 'pidgey']
# -------------------------
base_url = 'http://localhost:5000/%(user)s/snipe/%(coords)s'
rare_url = 'http://www.pokesnipers.com/api/v1/pokemon.json'
cache = pylru.lrucache(15)


def snipe(pokemon, user, coords):
    print('Requesting %s for %s' % (pokemon, user))
    try:
        new_url = base_url % dict(user=user, coords=coords)
        requests.get(new_url)
    except Exception as e:
        print("Couldn't do it... :( %s", e)


def get_latest_rares():
    global blacklist
    response = None
    try:
        response = requests.get(rare_url)
        data = response.json()
    except Exception as e:
        if response:
            error = response.text
        else:
            error = e
        print("Couldn't decode the data", error)
        return
    rares = data['results']
    for pokemon in rares:
        until = parser.parse(pokemon['until']).replace(tzinfo=None)
        coords = pokemon['coords']
        name = pokemon['name']
        # don't attempt ones that we've already sniped
        if coords in cache:
            print("We've already attempted %s, skipping..." % coords)
            continue
        # don't attempt ones that are already gone
        if until > datetime.utcnow():
            if name.lower() in blacklist:
                continue
            print('Found a pokemon we want!, %s at %s' % (name, coords))
            cache[coords] = name
            time.sleep(10)
            processes = []
            for user in users:
                p = Process(target=snipe, args=(name, user, coords))
                processes.append(p)
                p.start()
            for process in processes:
                process.join()


while True:
    print('Checking for new pokemon')
    get_latest_rares()
    time.sleep(30)
