import requests
from time import time
import json
import urllib2
class AutoSniper(object):
    """docstring for AutoSniper"""
    def __init__(self, fetch_server):
        super(AutoSniper, self).__init__()
        self.fetch_url = fetch_server
        self.last_fetch = 0
        self.fetch_cache = []
        self.seen = set()

        self.fetch_cache_2 = []
    def poll_since(self):
        payload = {"since" : self.last_fetch}
        self.last_fetch = int(time())
        r = requests.get(self.fetch_url, params=payload)
        self.fetch_cache = r.json()
        for r in self.fetch_cache:
            lat = r['Point']['Lat']
            lon = r['Point']['Lon']
            loc = (lat,lon)
            if loc in self.seen:
                continue
            self.seen.add(loc)
            yield {"encounter_id": r['Id'], "iv": r['Iv'], "cp": r['Cp'], "pokemon_id": r['Pokemon_ID'], "spawn_point_id" : str(r["Spawn_point_id"]), "loc": loc}
    def poll_since_2(self):
        site= "http://pokesnipers.com/api/v1/pokemon.json"
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
               'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
               'Accept-Encoding': 'none',
               'Accept-Language': 'en-US,en;q=0.8',
               'Connection': 'keep-alive'}
        req = urllib2.Request(site, headers=hdr)

        try:
            page = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            print e.fp.read()

        content = json.loads(page.read())
        #data = simplejson.load(content)
        #print content[0]
        for pokemon in content['results']:
            if not any(pokemon['id'] == x['id'] for x in self.fetch_cache_2):
                loc = pokemon['coords'].split(',')
                lat = float(loc[0])
                lon = float(loc[1])
                loc = (lat,lon)
                self.fetch_cache_2.append(pokemon)
                yield {"loc": loc}

    def post_encounter(self,**payload):
        print(json.dumps(payload))
        try:
            r = requests.post(self.fetch_url, json=payload)
        except Exception as e:
            print("Failed to post encounter: %s with error %s" % (payload,e))
DEFAULT_SNIPER = AutoSniper("http://autosnipe1.ngrok.io/pokemon") # CHECK SLACK FOR LATEST AUTO SNIPER DEV WORK, SUPER ALPHA ATM
