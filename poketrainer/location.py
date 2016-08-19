from __future__ import absolute_import

from time import time

import pyproj
import s2sphere
import six
from geopy.distance import VincentyDistance, vincenty
from geopy.geocoders import GoogleV3
from gmaps.directions import Directions
import math
from random import random

if six.PY3:
    from past.builtins import map

g = pyproj.Geod(ellps='WGS84')
geolocator = GoogleV3()


def get_location(search):
    # skip geocode if possible (search = coordinates)
    coordinates = search.split(',')
    if len(coordinates) == 2:
        try:
            lon = float(coordinates[0].strip(' '))
            lat = float(coordinates[1].strip(' '))
            return (lon, lat, 0)
        except Exception:
            pass
    loc = geolocator.geocode(search)
    return (loc.latitude, loc.longitude, loc.altitude)


# http://gis.stackexchange.com/questions/25877/how-to-generate-random-locations-nearby-my-location
def randomize_coordinates(lat, lon, alt, distance=20):
    """
        randomize the coordinate
    """
    x0 = lon
    y0 = lat
    r = distance / 111300.0  # convert meters to degrees (at equator)
    u = random()
    v = random()
    w = r * math.sqrt(u)
    t = 2 * math.pi * v
    x = w * math.cos(t)
    y = w * math.sin(t)
    # adjust for shrinking in east-west distances
    x1 = x / math.cos(y0 * math.pi / 180)
    return (y0 + y, x0 + x1, alt)


# http://python-gmaps.readthedocs.io/en/latest/gmaps.html#module-gmaps.directions
def get_route(start, end, use_google=False, gmaps_api_key="", walk_to_all_forts=False, waypoints=None, step_size=200):
    origin = (start[0], start[1])
    destination = (end[0], end[1])
    if use_google:
        directions_service = Directions(api_key=gmaps_api_key)
        if walk_to_all_forts and waypoints is not None:
            d = directions_service.directions(origin, destination, mode="walking", units="metric",
                                              optimize_waypoints=True, waypoints=waypoints)
        else:
            d = directions_service.directions(origin, destination, mode="walking", units="metric")
        steps = d[0]['legs'][0]['steps']
        final_steps_google = [
            {
                'lat': step['end_location']['lat'],
                'long': step['end_location']['lng'],
                'distance': step['distance']['value'],
            } for step in steps
        ]
        final_steps = []
        for step_google in final_steps_google:
            # make sure our steps are not bigger than step_size
            if step_google['distance'] <= step_size:
                final_steps.append(step_google)
            else:
                if len(final_steps) < 1:
                    prev_final_step = start
                else:
                    prev_final_step = final_steps[len(final_steps) - 1]
                    prev_final_step = (prev_final_step['lat'], prev_final_step['long'], 0)
                step_increments = get_increments(
                    prev_final_step,
                    (step_google['lat'], step_google['long']),
                    step_size
                )
                previous_step = step_increments[0]
                for step in step_increments[1:]:
                    final_steps.append({
                        'lat': step[0],
                        'long': step[1],
                        'distance': distance_in_meters(previous_step, step)
                    })
                    previous_step = step
        return {
            'total_distance': d[0]['legs'][0]['distance']['value'],
            'steps': final_steps
        }
    else:
        total_distance = distance_in_meters(start, destination)
        step_increments = get_increments(start, destination, step_size)
        final_steps = []
        previous_step = step_increments[0]
        for step in step_increments[1:]:
            final_steps.append({
                'lat': step[0],
                'long': step[1],
                'distance': distance_in_meters(previous_step, step)
            })
            previous_step = step

        return {
            'total_distance': total_distance,
            'steps': final_steps
        }


# step_size corresponds to how many meters between each step we want
def get_increments(start, end, step_size=200):
    # def get_increments(start,end,step_size=3):
    g = pyproj.Geod(ellps='WGS84')
    (startlat, startlong, _) = start
    (endlat, endlong) = end
    (az12, az21, dist) = g.inv(startlong, startlat, endlong, endlat)
    # calculate line string along path with segments <= 1 km
    lonlats = g.npts(startlong, startlat, endlong, endlat,
                     1 + int(dist / step_size))
    # npts doesn't include start/end points, so append
    lonlats.insert(0, (startlong, startlat))
    lonlats.append((endlong, endlat))
    return [(l[1], l[0], 0) for l in lonlats]  # reorder to be lat,long instead of long,lat


def distance_in_meters(p1, p2):
    return vincenty(p1, p2).meters


def filtered_forts(starting_location, origin, forts, proximity, visited_forts=None, reverse=False):
    if visited_forts is None:
        visited_forts = {}
    forts = filter(lambda f: is_active_pokestop(f[0], visited_forts=visited_forts, starting_location=starting_location,
                                                proximity=proximity),
                   map(lambda x: (x, distance_in_meters(origin, (x['latitude'], x['longitude']))), forts))

    sorted_forts = sorted(forts, key=lambda x: x[1], reverse=reverse)
    return sorted_forts


def is_active_pokestop(fort, visited_forts, starting_location, proximity):
    is_active_fort = fort.get('type') == 1 and ("enabled" in fort or 'lure_info' in fort) and fort.get(
        'cooldown_complete_timestamp_ms', -1) < time() * 1000
    if proximity and proximity > 0:
        return is_active_fort and fort['id'] not in visited_forts and distance_in_meters(starting_location, (
            fort['latitude'], fort['longitude'])) < proximity
    else:
        return is_active_fort and fort['id'] not in visited_forts


# from pokemongodev slack @erhan
def get_neighbors(loc, level=15, spread=700):
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
