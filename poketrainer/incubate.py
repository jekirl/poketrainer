from __future__ import absolute_import

from helper.colorlogger import create_logger
from library.api.pgoapi.protos.POGOProtos.Inventory import \
    Item_pb2 as Item_Enums

from .poke_utils import get_pokemon_by_long_id


class Incubate(object):
    def __init__(self, parent):
        self.parent = parent
        self.log = create_logger(__name__)

    def incubate_eggs(self):
        if not self.parent.config.egg_incubation_enabled:
            return
        if self.parent.player_stats.km_walked > 0:
            for incubator in self.parent.inventory.incubators_busy:
                incubator_start_km_walked = incubator.get('start_km_walked', self.parent.player_stats.km_walked)

                incubator_egg_distance = incubator['target_km_walked'] - incubator_start_km_walked
                incubator_distance_done = self.parent.player_stats.km_walked - incubator_start_km_walked
                if incubator_distance_done > incubator_egg_distance:
                    self.attempt_finish_incubation()
                    break
            for incubator in self.parent.inventory.incubators_busy:
                incubator_start_km_walked = incubator.get('start_km_walked', self.parent.player_stats.km_walked)

                incubator_egg_distance = incubator['target_km_walked'] - incubator_start_km_walked
                incubator_distance_done = self.parent.player_stats.km_walked - incubator_start_km_walked
                self.log.info('Incubating %skm egg, %skm done', incubator_egg_distance,
                              round(incubator_distance_done, 2))
        for incubator in self.parent.inventory.incubators_available:
            if incubator['item_id'] == Item_Enums.ITEM_INCUBATOR_BASIC_UNLIMITED:
                pass
            elif (self.parent.config.use_disposable_incubators
                  and incubator['item_id'] == Item_Enums.ITEM_INCUBATOR_BASIC):
                pass
            else:
                continue
            eggs_available = self.parent.inventory.eggs_available
            eggs_available = sorted(eggs_available, key=lambda egg: egg['creation_time_ms'],
                                    reverse=False)  # oldest first
            eggs_available = sorted(eggs_available, key=lambda egg: egg['egg_km_walked_target'],
                                    reverse=self.parent.config.incubate_big_eggs_first)  # now sort as defined
            if not len(eggs_available) > 0 or not self.attempt_start_incubation(eggs_available[0], incubator):
                break

    def attempt_start_incubation(self, egg, incubator):
        self.log.info("Start incubating %skm egg", egg['egg_km_walked_target'])
        self.parent.sleep(0.2 + self.parent.config.extra_wait)
        incubate_res = self.parent.api.use_item_egg_incubator(item_id=incubator['id'], pokemon_id=egg['id']) \
            .get('responses', {}).get('USE_ITEM_EGG_INCUBATOR', {})
        status = incubate_res.get('result', -1)
        if status == 1:
            self.log.info("Incubation started with %skm egg !", egg['egg_km_walked_target'])
            self.parent.inventory.update_player_inventory()
            return True
        else:
            self.log.debug("Could not start incubating %s", incubate_res)
            self.log.info("Could not start incubating %s egg | Status %s", egg['egg_km_walked_target'], status)
            self.parent.inventory.update_player_inventory()
            return False

    def attempt_finish_incubation(self):
        self.log.info("Checking for hatched eggs")
        self.parent.sleep(0.2 + self.parent.config.extra_wait)
        hatch_res = self.parent.api.get_hatched_eggs().get('responses', {}).get('GET_HATCHED_EGGS', {})
        status = hatch_res.get('success', -1)
        # self.sleep(3)
        if status == 1:
            self.parent.inventory.update_player_inventory()
            for i, pokemon_id in enumerate(hatch_res['pokemon_id']):
                pokemon = get_pokemon_by_long_id(pokemon_id, self.parent.inventory.get_raw_inventory_items())
                self.log.info("Egg Hatched! XP +%s, Candy +%s, Stardust +%s, %s",
                              hatch_res['experience_awarded'][i],
                              hatch_res['candy_awarded'][i],
                              hatch_res['stardust_awarded'][i],
                              pokemon)
            return True
        else:
            self.log.debug("Could not get hatched eggs %s", hatch_res)
            self.log.info("Could not get hatched eggs Status %s", status)
            self.parent.inventory.update_player_inventory()
            return False
