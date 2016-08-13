from __future__ import absolute_import

import json
from time import time

from cachetools import TTLCache

from helper.colorlogger import create_logger
from helper.utilities import flat_map

from .location import distance_in_meters
from .poke_utils import create_capture_probability, get_item_name
from .pokemon import POKEMON_NAMES, Pokemon


class PokeCatcher(object):
    def __init__(self, parent):
        self.parent = parent
        self.encountered_pokemons = TTLCache(maxsize=120, ttl=self.parent.map_objects.get_api_rate_limit() * 2)

        self.log = create_logger(__name__, self.parent.config.log_colors["poke_catcher".upper()])

    def catch_all(self):
        catch_attempt = 0
        # if catching fails 10 times, maybe you are sofbanned.
        # We can't actually use this as a basis for being softbanned. Pokemon Flee if you are softbanned (~stolencatkarma)
        while self.catch_near_pokemon() and catch_attempt <= self.parent.config.max_catch_attempts:
            # self.sleep(1)
            catch_attempt += 1
        if catch_attempt > self.parent.config.max_catch_attempts:
            self.log.warn("You have reached the maximum amount of catch attempts. Gave up after %s times",
                          catch_attempt)

    def catch_near_pokemon(self):
        if self.parent.should_catch_pokemon is False:
            return False

        map_cells = self.parent.map_objects.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {})\
            .get('map_cells', [])
        pokemons = flat_map(lambda c: c.get('catchable_pokemons', []), map_cells)
        pokemons = filter(lambda p: (p['encounter_id'] not in self.encountered_pokemons), pokemons)

        # catch first pokemon:
        origin = self.parent.get_position()
        pokemon_distances = [(pokemon, distance_in_meters(origin, (pokemon['latitude'], pokemon['longitude']))) for
                             pokemon
                             in pokemons]
        if pokemons:
            self.log.debug("Nearby pokemon: : %s", pokemon_distances)
            self.log.info("Nearby Pokemon: %s",
                          ", ".join(map(lambda x: POKEMON_NAMES[str(x['pokemon_id'])], pokemons)))
        elif self.parent.config.notify_no_nearby_pokemon:
            self.log.info("No nearby pokemon")
        catches_successful = False
        for pokemon_distance in pokemon_distances:
            target = pokemon_distance
            self.log.debug("Catching pokemon: : %s, distance: %f meters", target[0], target[1])
            catches_successful &= self.encounter_pokemon(target[0])
            # self.sleep(random.randrange(4, 8))
        return catches_successful

    def attempt_catch(self, encounter_id, spawn_point_id, capture_probability=None):
        catch_status = -1
        catch_attempts = 1
        ret = {}
        if not capture_probability:
            capture_probability = {}
        # Max 4 attempts to catch pokemon
        while catch_status != 1 and self.parent.inventory.can_attempt_catch() and catch_attempts <= self.parent.config.max_catch_attempts:
            item_capture_mult = 1.0

            # Try to use a berry to increase the chance of catching the pokemon when we have failed enough attempts
            if catch_attempts > self.parent.config.min_failed_attempts_before_using_berry \
                    and self.parent.inventory.has_berry():
                self.log.info("Feeding da razz berry!")
                self.parent.sleep(0.2 + self.parent.config.extra_wait)
                r = self.parent.api.use_item_capture(item_id=self.parent.inventory.take_berry(),
                                                     encounter_id=encounter_id,
                                                     spawn_point_id=spawn_point_id) \
                    .get('responses', {}).get('USE_ITEM_CAPTURE', {})
                if r.get("success", False):
                    item_capture_mult = r.get("item_capture_mult", 1.0)
                else:
                    self.log.info("Could not feed the Pokemon. (%s)", r)

            pokeball = self.parent.inventory.take_next_ball(capture_probability)
            self.log.info("Attempting catch with {0} at {1:.2f}% chance. Try Number: {2}".format(get_item_name(
                pokeball), item_capture_mult * capture_probability.get(pokeball, 0.0) * 100, catch_attempts))
            self.parent.sleep(0.5 + self.parent.config.extra_wait)
            r = self.parent.api.catch_pokemon(
                normalized_reticle_size=1.950,
                pokeball=pokeball,
                spin_modifier=0.850,
                hit_pokemon=True,
                normalized_hit_position=1,
                encounter_id=encounter_id,
                spawn_point_id=spawn_point_id,
            ).get('responses', {}).get('CATCH_POKEMON', {})
            catch_attempts += 1
            if "status" in r:
                catch_status = r['status']
                # fleed or error
                if catch_status == 3 or catch_status == 0:
                    break
            ret = r
            # Sleep between catch attempts
            # self.sleep(3)
        # Sleep after the catch (the pokemon animation time)
        # self.sleep(4)
        return ret

    def do_catch_pokemon(self, encounter_id, spawn_point_id, capture_probability, pokemon):
        self.log.info("Catching Pokemon: %s", pokemon)
        catch_attempt = self.attempt_catch(encounter_id, spawn_point_id, capture_probability)
        capture_status = catch_attempt.get('status', -1)
        if capture_status == 1:
            pokemon.id = str(catch_attempt.get('captured_pokemon_id', 'NA'))
            pokemon.creation_time_ms = time() * 1000
            self.log.debug("Caught Pokemon: : %s", catch_attempt)
            self.log.info("Caught Pokemon:  %s", pokemon)
            self.parent.push_to_web('pokemon', 'caught', pokemon.__dict__)
            self.parent.pokemon_caught += 1
            return True
        elif capture_status == 3:
            self.log.debug("Pokemon fleed : %s", catch_attempt)
            self.log.info("Pokemon fleed:  %s", pokemon)
            return False
        elif capture_status == 2:
            self.log.debug("Pokemon escaped: : %s", catch_attempt)
            self.log.info("Pokemon escaped:  %s", pokemon)
            return False
        elif capture_status == 4:
            self.log.debug("Catch Missed: : %s", catch_attempt)
            self.log.info("Catch Missed:  %s", pokemon)
            return False
        else:
            self.log.debug("Could not catch pokemon: %s", catch_attempt)
            self.log.info("Could not catch pokemon:  %s, status: %s", pokemon, capture_status)
            return False

    def encounter_pokemon(self, pokemon_data, retry=False,
                          new_loc=None):  # take in a MapPokemon from MapCell.catchable_pokemons
        # Update Inventory to make sure we can catch this mon
        try:
            self.parent.inventory.update_player_inventory()
            if not self.parent.inventory.can_attempt_catch():
                self.log.info("No balls to catch %s, exiting encounter", self.parent.inventory)
                return False
            encounter_id = pokemon_data['encounter_id']
            spawn_point_id = pokemon_data['spawn_point_id']
            # begin encounter_id
            position = self.parent.api.get_position()
            pokemon = Pokemon(pokemon_data)
            self.log.info("Trying initiate catching Pokemon: %s", pokemon.pokemon_type)
            self.parent.sleep(0.2 + self.parent.config.extra_wait)
            encounter = self.parent.api.encounter(encounter_id=encounter_id,
                                                  spawn_point_id=spawn_point_id,
                                                  player_latitude=position[0],
                                                  player_longitude=position[1]) \
                .get('responses', {}).get('ENCOUNTER', {})
            self.log.debug("Attempting to Start Encounter: %s", encounter)
            result = encounter.get('status', -1)
            if result == 1 and 'wild_pokemon' in encounter and 'capture_probability' in encounter:
                pokemon = Pokemon(encounter.get('wild_pokemon', {}).get('pokemon_data', {}),
                                  self.parent.player_stats.level,
                                  self.parent.config.score_method, self.parent.config.score_settings)
                capture_probability = create_capture_probability(encounter.get('capture_probability', {}))
                self.log.debug("Attempt Encounter Capture Probability: %s",
                               json.dumps(encounter, indent=4, sort_keys=True))

                if new_loc:
                    # change loc for sniping
                    self.log.info("Teleporting to %f, %f before catching", new_loc[0], new_loc[1])
                    self.parent.api.set_position(new_loc[0], new_loc[1], 0.0)
                    self.parent.sniper.send_update_pos()
                    # self.sleep(2)

                self.encountered_pokemons[encounter_id] = pokemon_data
                return self.do_catch_pokemon(encounter_id, spawn_point_id, capture_probability, pokemon)
            elif result == 7:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try",
                              pokemon.pokemon_type)
                self.parent.release.cleanup_pokemon()
                if not retry:
                    return self.encounter_pokemon(pokemon_data, retry=True, new_loc=new_loc)
            else:
                self.log.info("Could not start encounter for pokemon: %s, status %s", pokemon.pokemon_type, result)
            return False
        except Exception as e:
            self.log.error("Error in pokemon encounter %s", e)
            return False

    def disk_encounter_pokemon(self, lureinfo, retry=False):
        try:
            self.parent.inventory.update_player_inventory()
            if not self.parent.inventory.can_attempt_catch():
                self.log.info("No balls to catch %s, exiting disk encounter", self.parent.inventory)
                return False
            encounter_id = lureinfo['encounter_id']
            fort_id = lureinfo['fort_id']
            position = self.parent.get_position()
            self.log.debug("At Fort with lure %s".encode('utf-8', 'ignore'), lureinfo)
            self.log.info("At Fort with Lure AND Active Pokemon %s",
                          POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            resp = self.parent.api.disk_encounter(encounter_id=encounter_id, fort_id=fort_id,
                                                  player_latitude=position[0],
                                                  player_longitude=position[1]) \
                .get('responses', {}).get('DISK_ENCOUNTER', {})
            result = resp.get('result', -1)
            if result == 1 and 'pokemon_data' in resp and 'capture_probability' in resp:
                pokemon = Pokemon(resp.get('pokemon_data', {}),
                                  self.parent.player_stats.level,
                                  self.parent.config.score_method, self.parent.config.score_settings)
                capture_probability = create_capture_probability(resp.get('capture_probability', {}))
                self.log.debug("Attempt Encounter: %s", json.dumps(resp, indent=4, sort_keys=True))
                return self.do_catch_pokemon(encounter_id, fort_id, capture_probability, pokemon)
            elif result == 5:
                self.log.info("Couldn't catch %s Your pokemon bag was full, attempting to clear and re-try",
                              POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
                self.parent.release.cleanup_pokemon()
                if not retry:
                    return self.disk_encounter_pokemon(lureinfo, retry=True)
            elif result == 2:
                self.log.info("Could not start Disk (lure) encounter for pokemon: %s, not available",
                              POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"))
            else:
                self.log.info("Could not start Disk (lure) encounter for pokemon: %s, Result: %s",
                              POKEMON_NAMES.get(str(lureinfo.get('active_pokemon_id', 0)), "NA"),
                              result)
        except Exception as e:
            self.log.error("Error in disk encounter %s", e)
            return False
