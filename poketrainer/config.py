from __future__ import absolute_import

import hashlib

from helper.colorlogger import create_logger
from library.api.pgoapi.protos.POGOProtos import Enums_pb2 as Enums
from library.api.pgoapi.protos.POGOProtos.Inventory import \
    Item_pb2 as Item_Enums


class Config:

    def __init__(self, config, cli_args):
        self.log = create_logger(__name__)

        self.__config_data = config
        self.config_data = config
        self.__password = self.config_data.pop("password", 'NA')

        self.location = config["location"]
        self.auth_service = config["auth_service"]
        self.username = config["username"]
        self.gmaps_api_key = config.get("GMAPS_API_KEY", "")

        self.step_size = config.get("BEHAVIOR", {}).get("STEP_SIZE", 200)
        self.wander_steps = config.get("BEHAVIOR", {}).get("WANDER_STEPS", 0)
        self.extra_wait = config.get("BEHAVIOR", {}).get("EXTRA_WAIT", 0.3)
        self.sleep_mult = config.get("BEHAVIOR", {}).get("SLEEP_MULT", 1.5)
        self.use_lucky_egg = config.get("BEHAVIOR", {}).get("AUTO_USE_LUCKY_EGG", False)
        self.use_google = config.get("BEHAVIOR", {}).get("USE_GOOGLE", False)
        self.skip_visited_fort_duration = config.get("BEHAVIOR", {}).get("SKIP_VISITED_FORT_DURATION", 600)
        self.spin_all_forts = config.get("BEHAVIOR", {}).get("SPIN_ALL_FORTS", False)
        self.stay_within_proximity = config.get("BEHAVIOR", {}).get("STAY_WITHIN_PROXIMITY",
                                                                    9999999)  # Stay within proximity
        self.should_catch_pokemon = config.get("CAPTURE", {}).get("CATCH_POKEMON", True)
        self.max_catch_attempts = config.get("CAPTURE", {}).get("MAX_CATCH_ATTEMPTS", 10)
        self.min_failed_attempts_before_using_berry = config.get("CAPTURE", {}).get("MIN_FAILED_ATTEMPTS_BEFORE_USING_BERRY", 3)
        pokeball_percent = config.get("CAPTURE", {}).get("USE_POKEBALL_IF_PERCENT", 50)
        greatball_percent = config.get("CAPTURE", {}).get("USE_GREATBALL_IF_PERCENT", 50)
        ultraball_percent = config.get("CAPTURE", {}).get("USE_ULTRABALL_IF_PERCENT", 50)
        use_masterball = config.get("CAPTURE", {}).get("USE_MASTERBALL", False)
        self.ball_priorities = [pokeball_percent, greatball_percent, ultraball_percent, use_masterball]

        self.min_items = {}
        for k, v in config.get("MIN_ITEMS", {}).items():
            self.min_items[getattr(Item_Enums, k)] = v

        self.pokemon_evolution = {}
        self.pokemon_evolution_family = {}
        for k, v in config.get("POKEMON_EVOLUTION", {}).items():
            self.pokemon_evolution[getattr(Enums, k)] = v
            self.pokemon_evolution_family[getattr(Enums, k)] = getattr(Enums, "FAMILY_" + k)

        self.experimental = config.get("BEHAVIOR", {}).get("EXPERIMENTAL", False)

        self.pokemon_cleanup_testing_mode = config.get('POKEMON_CLEANUP', {}).get('TESTING_MODE', False)
        self.min_similar_pokemon = config.get("POKEMON_CLEANUP", {}).get("MIN_SIMILAR_POKEMON",
                                                                         1)  # Keep atleast one of everything.
        self.keep_pokemon_ids = map(lambda x: getattr(Enums, x),
                                    config.get("POKEMON_CLEANUP", {}).get("KEEP_POKEMON_NAMES", []))

        self.release_method = config.get("POKEMON_CLEANUP", {}).get("RELEASE_METHOD", "CLASSIC")
        self.release_method_conf = config.get("POKEMON_CLEANUP", {}).get("RELEASE_METHOD_" + self.release_method, {})

        self.score_method = config.get("POKEMON_CLEANUP", {}).get("SCORE_METHOD", "CP")
        self.score_settings = config.get("POKEMON_CLEANUP", {}).get("SCORE_METHOD_" + self.score_method, {})

        self.egg_incubation_enabled = config.get("EGG_INCUBATION", {}).get("ENABLE", True)
        self.use_disposable_incubators = config.get("EGG_INCUBATION", {}).get("USE_DISPOSABLE_INCUBATORS", False)
        self.incubate_big_eggs_first = config.get("EGG_INCUBATION", {}).get("BIG_EGGS_FIRST", True)

        self.farm_items_enabled = config.get("NEEDY_ITEM_FARMING", {}).get("ENABLE",
                                                                           True and self.experimental)  # be concious of pokeball/item limits
        self.pokeball_continue_threshold = config.get("NEEDY_ITEM_FARMING", {}).get("POKEBALL_CONTINUE_THRESHOLD",
                                                                                    50)  # keep at least 10 pokeballs of any assortment, otherwise go farming
        self.pokeball_farm_threshold = config.get("NEEDY_ITEM_FARMING", {}).get("POKEBALL_FARM_THRESHOLD",
                                                                                10)  # at this point, go collect pokeballs
        self.farm_ignore_pokeball_count = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_POKEBALL_COUNT",
                                                                                   False)  # ignore pokeballs in the continue tally
        self.farm_ignore_greatball_count = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_GREATBALL_COUNT",
                                                                                    False)  # ignore greatballs in the continue tally
        self.farm_ignore_ultraball_count = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_ULTRABALL_COUNT",
                                                                                    False)  # ignore ultraballs in the continue tally
        self.farm_ignore_masterball_count = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_IGNORE_MASTERBALL_COUNT",
                                                                                     True)  # ignore masterballs in the continue tally
        self.farm_override_step_size = config.get("NEEDY_ITEM_FARMING", {}).get("FARM_OVERRIDE_STEP_SIZE",
                                                                                -1)  # should the step size be overriden when looking for more inventory, -1 to disable
        self._sanity_check_needy_item_farming()

        self.explain_evolution_before_cleanup = config.get("CONSOLE_OUTPUT", {}).get("EXPLAIN_EVOLUTION_BEFORE_CLEANUP",
                                                                                     False)  # explain individual evolution criteria in console
        self.list_pokemon_before_cleanup = config.get("CONSOLE_OUTPUT", {}).get("LIST_POKEMON_BEFORE_CLEANUP",
                                                                                False)  # list pokemon in console
        self.list_inventory_before_cleanup = config.get("CONSOLE_OUTPUT", {}).get("LIST_INVENTORY_BEFORE_CLEANUP",
                                                                                  True)  # list inventory in console
        self.show_steps = config.get("CONSOLE_OUTPUT", {}).get("SHOW_STEPS", True)  # show steps walked in console
        self.show_travel_link_with_steps = config.get("CONSOLE_OUTPUT", {}).get("SHOW_TRAVEL_LINK_WITH_STEPS", True)
        self.show_distance_traveled = config.get("CONSOLE_OUTPUT", {}).get("SHOW_DISTANCE_TRAVELED", True)
        self.show_nearest_fort_distance = config.get("CONSOLE_OUTPUT", {}).get("SHOW_NEAREST_FORT_DISTANCE", True)
        self.notify_no_nearby_pokemon = config.get("CONSOLE_OUTPUT", {}).get("NOTIFY_NO_NEARBY_POKEMON", False)

        self.log_colors = config.get("CONSOLE_OUTPUT", {}).get("COLORLOG",
                                                               {"FORT_WALKER": "blue",
                                                                "POKE_CATCHER": "green",
                                                                "RELEASE": "cyan",
                                                                "EVOLVE": "cyan",
                                                                "POKETRAINER": "yellow",
                                                                "INVENTORY": "purple"})

        if cli_args['location']:
            start_location = cli_args['location']
        else:
            start_location = self.location
            self.cache_filename = './cache/cache ' + (hashlib.md5(start_location.encode())).hexdigest() + str(self.stay_within_proximity)
            self.use_cache = config.get("BEHAVIOR", {}).get("USE_CACHED_FORTS", False)
            self.cache_is_sorted = config.get("BEHAVIOR", {}).get("CACHED_FORTS_SORTED", False)
            self.enable_caching = config.get("BEHAVIOR", {}).get("ENABLE_CACHING", False)

    def _sanity_check_needy_item_farming(self):
        # Sanity checking, farm_items is Experimental, and we needn't do this if we're farming anyway
        self.farm_items_enabled = (self.farm_items_enabled and
                                   self.experimental and
                                   self.should_catch_pokemon)
        if (self.farm_items_enabled and self.farm_ignore_pokeball_count and self.farm_ignore_greatball_count and self.farm_ignore_ultraball_count and self.farm_ignore_masterball_count):
            self.farm_items_enabled = False
            self.log.warn("FARM_ITEMS has been disabled due to all Pokeball counts being ignored.")
        elif self.farm_items_enabled and not self.pokeball_farm_threshold < self.pokeball_continue_threshold:
            self.farm_items_enabled = False
            self.log.warn("FARM_ITEMS has been disabled due to farming threshold being below the continue. " +
                          "Set 'CATCH_POKEMON' to 'false' to enable captureless traveling.")

    def get_password(self):
        return self.__password
