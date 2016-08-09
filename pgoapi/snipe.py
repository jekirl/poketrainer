import requests
from time import time
import json
class AutoSniper(object):
    """docstring for AutoSniper"""
    def __init__(self, fetch_server):
        super(AutoSniper, self).__init__()
        self.fetch_url = fetch_server
        self.last_fetch = 0
        self.fetch_cache = []
        self.seen = set()
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
            yield {"encounter_id": r['Id'], "spawn_point_id" : str(r["Spawn_point_id"]), "loc": loc}
    def post_encounter(self,**payload):
        print(json.dumps(payload))
        try:
            r = requests.post(self.fetch_url, json=payload)
        except Exception as e:
            print("Failed to post encounter: %s with error %s" % (payload,e))
DEFAULT_SNIPER = AutoSniper("http://autosnipe1.ngrok.io/pokemon") # CHECK SLACK FOR LATEST AUTO SNIPER DEV WORK, SUPER ALPHA ATM
