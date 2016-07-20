import logging
from geopy.geocoders import GoogleV3
from gmaps.directions import *
import s2sphere
from geopy.distance import VincentyDistance, vincenty
from protos.RpcEnum_pb2 import *
import pyproj
from time import time
g = pyproj.Geod(ellps='WGS84')
geolocator = GoogleV3()
directions_service = Directions()
def getLocation(search):
    loc = geolocator.geocode(search)
    return (loc.latitude, loc.longitude, loc.altitude)


#http://python-gmaps.readthedocs.io/en/latest/gmaps.html#module-gmaps.directions
def get_route(start,end, use_google = False):
    origin = (start[0], start[1])
    destination = (end[0], end[1])
    if use_google:
        d = directions_service.directions(origin, destination, mode="walking",units="metric")
        steps = d[0]['legs'][0]['steps']
        return [(step['end_location']["lat"],step['end_location']["lng"]) for step in steps]
    else:
        return [destination]


# step_size corresponds to how many meters between each step we want
def get_increments(start,end,step_size=200):
# def get_increments(start,end,step_size=3):
    g = pyproj.Geod(ellps='WGS84')
    (startlat, startlong, _) = start
    (endlat, endlong) = end
    (az12, az21, dist) = g.inv(startlong, startlat, endlong, endlat)
    # calculate line string along path with segments <= 1 km
    lonlats = g.npts(startlong, startlat, endlong, endlat,
                     1 + int(dist / step_size))
    # npts doesn't include start/end points, so append
    lonlats.append((endlong, endlat))
    return [(l[1],l[0],0) for l in lonlats] # reorder to be lat,long instead of long,lat




def distance_in_meters(p1,p2):
    return vincenty(p1,p2).meters

def filtered_forts(origin, forts):
    forts = [(fort, distance_in_meters(origin,(fort['latitude'], fort['longitude']))) for fort in forts if fort.get('type',None) == CHECKPOINT and fort.get('enabled',None) and fort.get('cooldown_complete_timestamp_ms',-1) < time()*1000]
    sorted_forts = sorted(forts, lambda x,y : cmp(x[1],y[1]))
    return [x[0] for x in sorted_forts]

#from pokemongodev slack @erhan
def getNeighbors(loc, level=15, spread=700):
    distance = VincentyDistance(meters=spread)
    center = (loc[0], loc[1], 0)
    p1 = distance.destination(point=center, bearing=45)
    p2 = distance.destination(point=center, bearing=225)
    p1 = s2sphere.LatLng.from_degrees(p1[0], p1[1])
    p2 = s2sphere.LatLng.from_degrees(p2[0], p2[1])
    rect = s2sphere.LatLngRect.from_point_pair(p1, p2)
    region = s2sphere.RegionCoverer()
    region.min_level = level
    region.max_level = level
    cells = region.get_covering(rect)
    return sorted([c.id() for c in cells])
