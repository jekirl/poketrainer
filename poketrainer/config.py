from __future__ import absolute_import

from cachetools import TTLCache

from library.api.pgoapi.protos.POGOProtos.Inventory import Item_pb2 as Item_Enums
from library.api.pgoapi.protos.POGOProtos import Enums_pb2 as Enums


class Config:

    def __init__(self, config):
        self.__config_data = config
        self.config_data = config
        self.__password = self.config_data.pop("password", 'NA')
        self.__password_used = False

        self.location = config["location"]
        self.auth_service = config["auth_service"]
        self.username = config["username"]
        self.gmaps_api_key = config.get("GMAPS_API_KEY", "")

        self.step_size = config.get("BEHAVIOR", {}).get("STEP_SIZE", 200)
        self.wander_steps = config.get("BEHAVIOR", {}).get("WANDER_STEPS", 0)
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
        self.list_pokemon_before_cleanup = config.get("CONSOLE_OUTPUT", {}).get("LIST_POKEMON_BEFORE_CLEANUP",
                                                                                True)  # list pokemon in console
        self.list_inventory_before_cleanup = config.get("CONSOLE_OUTPUT", {}).get("LIST_INVENTORY_BEFORE_CLEANUP",
                                                                                  True)  # list inventory in console

    def get_password(self):
        # for security reasons, we only make the password available once
        if not self.__password_used:
            self.__password_used = True
            return self.__password
        return ''
