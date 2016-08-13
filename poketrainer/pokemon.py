from __future__ import absolute_import

import json
from math import floor, sqrt
from os import sep as os_sep
from os import path

from helper.utilities import all_in
from poketrainer.game_master import GAME_MASTER, PokemonData
from poketrainer.poke_lvl_data import POKEMON_LVL_DATA, TCPM_VALS, get_tcpm

POKEMON_NAMES = {}

_names_file_path = path.join(path.dirname(path.dirname(__file__)), "resources" + os_sep + "pokemon.en.json")
with open(_names_file_path) as jsonfile:
    POKEMON_NAMES.update(json.load(jsonfile))


class Pokemon(object):
    # Used for calculating the pokemon level
    # source http://pokemongo.gamepress.gg/cp-multiplier
    cpm_calculation_increments = [
        {
            'max_level': 1,
            'cpm_sqrt_increase_per_level': 0.008836,
            'max_level_cpm': 0.094  # we can't calculate this value, thus we set it here
        },
        {
            'max_level': 10,
            'cpm_sqrt_increase_per_level': 0.009426125 * 2,
        },
        {
            'max_level': 20,
            'cpm_sqrt_increase_per_level': 0.008919026 * 2,
        },
        {
            'max_level': 30,
            'cpm_sqrt_increase_per_level': 0.008924906 * 2,
        },
        {
            'max_level': 40,
            'cpm_sqrt_increase_per_level': 0.004459461 * 2,
        }
    ]

    def __init__(self, pokemon_data, player_level=0,
                 score_method="CP", score_settings=None):
        if not score_settings:
            score_settings = dict()
        self.pokemon_data = pokemon_data
        self.creation_time_ms = pokemon_data.get('creation_time_ms', 0)
        self.stamina = pokemon_data.get('stamina', 0)
        self.favorite = pokemon_data.get('favorite', -1)
        self.is_favorite = self.favorite != -1
        self.pokemon_id = pokemon_data.get('pokemon_id', 0)
        self.id = str(pokemon_data.get('id', 'NA'))
        self.cp = pokemon_data.get('cp', 0)
        self.stamina_max = pokemon_data.get('stamina_max', 0)
        self.is_egg = pokemon_data.get('is_egg', False)
        self.origin = pokemon_data.get('origin', 0)
        self.height_m = pokemon_data.get('height', 0.0)
        self.weight_kg = pokemon_data.get('weight_kg', 0.0)
        self.individual_attack = pokemon_data.get('individual_attack', 0)
        self.individual_defense = pokemon_data.get('individual_defense', 0)
        self.individual_stamina = pokemon_data.get('individual_stamina', 0)
        self.cp_multiplier = pokemon_data.get('cp_multiplier', 0.0)
        self.additional_cp_multiplier = pokemon_data.get('additional_cp_multiplier', 0.0)
        self.nickname = pokemon_data.get('nickname', "").encode('utf8')
        self.iv = self.get_iv_percentage()
        self.pokemon_type = POKEMON_NAMES.get(str(self.pokemon_id), "NA").encode('utf-8', 'ignore')

        # Used in Web.py
        if self.nickname is not "":
            self.name = self.nickname.decode('utf-8')
        else:
            self.name = self.pokemon_type
        self.move_1 = pokemon_data.get('move_1', 0)
        self.move_2 = pokemon_data.get('move_2', 0)

        self.iv_normalized = -1.0
        self.max_cp = -1.0
        self.max_cp_absolute = -1.0

        additional_data = GAME_MASTER.get(self.pokemon_id)
        self.family_id = int(additional_data.FamilyId) if additional_data else -1

        # helps with rounding errors
        self.cpm_total = get_tcpm(self.cp_multiplier + self.additional_cp_multiplier)
        self.level_wild = self.get_level_by_cpm(self.cp_multiplier)
        self.level = self.get_level_by_cpm(self.cpm_total)

        # Max Evolve based on ur lvl vals and Power Up
        self.candy_needed_to_evolve = 0
        self.candy_needed_to_max_evolve = 0
        self.dust_needed_to_max_evolve = 0
        self.max_evolve_cp = 0
        self.power_up_result = 0
        self.set_max_cp(self.get_cpm_by_level(player_level + 1.5))

        # Thanks to http://pokemongo.gamepress.gg/pokemon-stats-advanced for the magical formulas
        attack = float(additional_data.BaseAttack) if additional_data else 0.0
        defense = float(additional_data.BaseDefense) if additional_data else 0.0
        stamina = float(additional_data.BaseStamina) if additional_data else 0.0

        self.max_cp = self.calc_cp(self.get_cpm_by_level(player_level + 1.5), additional_data)
        self.max_cp_absolute = self.calc_cp(self.get_cpm_by_level(40), additional_data)

        # calculating these for level 40 to get more accurate values
        worst_iv_cp = (attack * sqrt(defense) * sqrt(stamina) * pow(self.get_cpm_by_level(40), 2)) / 10
        perfect_iv_cp = ((attack + 15) * sqrt(defense + 15) * sqrt(stamina + 15) * pow(self.get_cpm_by_level(40), 2)) / 10
        if perfect_iv_cp - worst_iv_cp > 0:
                self.iv_normalized = 100 * (self.max_cp_absolute - worst_iv_cp) / (perfect_iv_cp - worst_iv_cp)
        self.score = 0.0
        if score_method == "CP":
            self.score = self.cp
        elif score_method == "IV":
            self.score = self.iv_normalized
        elif score_method == "CP*IV":
            self.score = self.cp * self.iv_normalized
        elif score_method == "CP+IV":
            self.score = self.cp + self.iv_normalized
        elif score_method == "FANCY":
            self.score = (self.iv_normalized / 100.0 * score_settings.get("WEIGHT_IV", 0.5)) + \
                         (self.level / (player_level + 1.5) * score_settings.get("WEIGHT_LVL", 0.5))

        self.try_keep = False

    def __str__(self):
        nickname = ""

        if len(self.nickname) > 0:
            nickname = "Nickname: " + self.nickname + ", "

        if self.max_cp > 0:
            str_ = "{0}Type: {1}, CP: {2}, IV: {3:.2f}, Lvl: {4:.1f}, " \
                   "LvlWild: {5:.1f}, MaxCP: {6:.0f}, Score: {7}, IV-Norm.: {8:.0f}"
            return str_.format(nickname,
                               self.pokemon_type.decode('utf8'),
                               self.cp, self.iv,
                               self.level,
                               self.level_wild,
                               self.max_cp,
                               self.score,
                               self.iv_normalized)
        else:
            str_ = "{0}Type: {1}, CP: {2}, IV: {3:.2f}, Lvl: {4:.1f}, LvlWild: {5:.1f}"
            return str_.format(nickname,
                               self.pokemon_type.decode('utf8'),
                               self.cp, self.iv,
                               self.level,
                               self.level_wild)

    def __repr__(self):
        return self.__str__()

    def calc_cp(self, tcpm, pokemon_details):
        if not isinstance(pokemon_details, PokemonData) or not isinstance(tcpm, float):
            return 0

        base_attk = int(pokemon_details.BaseAttack)
        base_def = int(pokemon_details.BaseDefense)
        base_stamina = int(pokemon_details.BaseStamina)

        attk = (base_attk + self.individual_attack) * tcpm
        defense = (base_def + self.individual_defense) * tcpm
        stamina = (base_stamina + self.individual_stamina) * tcpm

        return int(max(10, floor(sqrt(stamina) * attk * sqrt(defense) / 10)))

    def set_max_cp(self, max_tcpm):
        max_tcpm = round(max_tcpm, 7)
        poke_game_data = GAME_MASTER.get(self.pokemon_id, PokemonData())
        if int(poke_game_data.PkMn) == 0 or max_tcpm not in TCPM_VALS or not all_in(['cp', 'cp_multiplier'], self.pokemon_data):
            return

        candy_to_evolve = int(poke_game_data.CandyToEvolve)

        self.candy_needed_to_evolve = candy_to_evolve
        self.candy_needed_to_max_evolve = POKEMON_LVL_DATA[max_tcpm].candy_to_this_lvl - POKEMON_LVL_DATA[self.cpm_total].candy_to_this_lvl + candy_to_evolve
        self.dust_needed_to_max_evolve = POKEMON_LVL_DATA[max_tcpm].stardust_to_this_lvl - POKEMON_LVL_DATA[self.cpm_total].stardust_to_this_lvl

        i = 0
        if self.pokemon_id == 133:  # is an Eevee
            if self.nickname is 'Sparky':
                i = 2
            elif self.nickname is 'Pyro':
                i = 3
            else:  # Rainer or Vaporean is the default
                i = 1
        else:
            while GAME_MASTER.get(self.pokemon_id + i + 1, PokemonData()).FamilyId == poke_game_data.FamilyId and candy_to_evolve > 0:
                candy_to_evolve = int(GAME_MASTER.get(self.pokemon_id + i + 1, PokemonData()).CandyToEvolve)
                self.candy_needed_to_max_evolve += candy_to_evolve
                i += 1

        if(i == 0):
            self.max_evolve_cp = self.calc_cp(max_tcpm, poke_game_data)
        else:
            evolved_poke_data = GAME_MASTER.get(self.pokemon_id + i, PokemonData())
            self.max_evolve_cp = self.calc_cp(max_tcpm, evolved_poke_data)

        poke_lvl = POKEMON_LVL_DATA[self.cpm_total].pokemon_lvl
        self.power_up_result = self.calc_cp(TCPM_VALS[poke_lvl], poke_game_data) - self.cp

    def get_level_by_cpm(self, cpm_total):
        prev_max_level = 0
        prev_max_level_cpm = 0
        for cpm_increment in self.cpm_calculation_increments:
            max_level = cpm_increment['max_level']
            cpm_sqrt_increase_per_level = cpm_increment['cpm_sqrt_increase_per_level']
            if "max_level_cpm" in cpm_increment:
                max_level_cpm = cpm_increment['max_level_cpm']
            else:
                # this calculates the CPM for a pokemon with max_level of the current iteration
                max_level_cpm = self.get_cpm_by_level(max_level)
            if cpm_total <= max_level_cpm:
                # cpm_sqrt_increase_per_level is only valid for CPM increase since prev_max_level
                level_diff_prev_max_level = (pow(cpm_total, 2) - pow(prev_max_level_cpm, 2)) / cpm_sqrt_increase_per_level
                return round(prev_max_level + level_diff_prev_max_level, 1)
            else:
                prev_max_level = max_level
                prev_max_level_cpm = max_level_cpm
        return 0.0

    def get_cpm_by_level(self, level):
        prev_max_level = 0
        prev_max_level_cpm = 0
        for cpm_increment in self.cpm_calculation_increments:
            max_level = cpm_increment['max_level']
            cpm_sqrt_increase_per_level = cpm_increment['cpm_sqrt_increase_per_level']
            if level <= max_level:  # we are below the max level of current cpm iteration
                # this calculates the CPM for a pokemon with given level
                return sqrt(
                    pow(prev_max_level_cpm, 2) +
                    cpm_sqrt_increase_per_level * (level - prev_max_level)
                )
            else:
                # this calculates the CPM for a pokemon with max_level, used in next iteration
                prev_max_level_cpm = sqrt(
                    pow(prev_max_level_cpm, 2) +
                    cpm_sqrt_increase_per_level * (max_level - prev_max_level)
                )
                prev_max_level = max_level
        return 0.0

    def get_iv_percentage(self):
        return ((self.individual_attack + self.individual_stamina + self.individual_defense + 0.0) / 45.0) * 100.0

    def is_valid_pokemon(self):
        return self.pokemon_id > 0

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
