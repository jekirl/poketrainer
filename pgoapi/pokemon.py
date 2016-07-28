from math import sqrt


class Pokemon:
    # Used for calculating the pokemon level
    # source http://pokemongo.gamepress.gg/cp-multiplier
    CPM_calculation_increments = [
        {
            'max_level': 1,
            'cpm_sqrt_increase_per_level': 0.008836,
            'max_level_cpm': 0.094  # we can't calculate this value, thus we set it here
        },
        {
            'max_level': 10,
            'cpm_sqrt_increase_per_level': 0.009426125*2
        },
        {
            'max_level': 20,
            'cpm_sqrt_increase_per_level': 0.008919026*2
        },
        {
            'max_level': 30,
            'cpm_sqrt_increase_per_level': 0.008924906*2
        },
        {
            'max_level': 40,
            'cpm_sqrt_increase_per_level': 0.004459461*2
        }
    ]

    def __init__(self, pokemon_data=dict(), pokemon_names=dict(), additional_data=None, player_level=0):
        self.pokemon_data = pokemon_data
        self.stamina = pokemon_data.get('stamina', 0)
        self.favorite = pokemon_data.get('favorite', -1)
        self.is_favorite = self.favorite != -1
        self.pokemon_id = pokemon_data.get('pokemon_id', 0)
        self.id = pokemon_data.get('id', 0)
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
        self.pokemon_type = pokemon_names.get(str(self.pokemon_id), "NA").encode('utf-8', 'ignore')
        self.pokemon_additional_data = additional_data
        self.iv_normalized = -1.0
        self.max_cp = -1.0
        self.max_cp_absolute = -1.0
        self.cpm_total = self.cp_multiplier + self.additional_cp_multiplier
        self.level_wild = self.get_level_by_cpm(self.cp_multiplier)
        self.level = self.get_level_by_cpm(self.cpm_total)
        if additional_data is not None:
            # Thanks to http://pokemongo.gamepress.gg/pokemon-stats-advanced for the magical formulas
            attack = float(additional_data.BaseAttack)
            defense = float(additional_data.BaseDefense)
            stamina = float(additional_data.BaseStamina)
            worst_iv_cp = (attack * sqrt(defense) * sqrt(stamina) * pow(self.cpm_total, 2)) / 10
            perfect_iv_cp = ((attack + 15) * sqrt(defense + 15) * sqrt(stamina + 15) * pow(self.cpm_total, 2)) / 10
            if perfect_iv_cp - worst_iv_cp > 0:
                self.iv_normalized = 100 * (self.cp - worst_iv_cp) / (perfect_iv_cp - worst_iv_cp)
            self.max_cp = ((attack + self.individual_attack) *
                           sqrt(defense + self.individual_defense) *
                           sqrt(stamina + self.individual_stamina) *
                           pow(self.get_cpm_by_level(player_level+1.5), 2)) / 10
            self.max_cp_absolute = ((attack + self.individual_attack) *
                           sqrt(defense + self.individual_defense) *
                           sqrt(stamina + self.individual_stamina) *
                           pow(self.get_cpm_by_level(40), 2)) / 10

    def __str__(self):
        nickname = ""

        if len(self.nickname) > 0:
            nickname = "Nickname: " + self.nickname + ", "

        if self.max_cp > 0:
            return "{0}Type: {1} CP: {2}, IV: {3:.2f}, Lvl: {4:.1f}, " \
                   "LvlWild: {5:.1f}, MaxCP: {6:.0f}, MaxCPAbs: {7:.0f}, IV-Norm.: {8:.0f}".format(nickname,
                                                                                                   self.pokemon_type,
                                                                                                   self.cp, self.iv,
                                                                                                   self.level,
                                                                                                   self.level_wild,
                                                                                                   self.max_cp,
                                                                                                   self.max_cp_absolute,
                                                                                                   self.iv_normalized)
        else:
            return "{0}Type: {1}, CP: {2}, IV: {3:.2f}, Lvl: {4:.1f}, LvlWild: {5:.1f}".format(nickname,
                                                                                                self.pokemon_type,
                                                                                                self.cp, self.iv,
                                                                                                self.level,
                                                                                                self.level_wild)

    def __repr__(self):
        return self.__str__()

    def get_level_by_cpm(self, cpm_total):
        prev_max_level = 0
        prev_max_level_cpm = 0
        for cpm_increment in self.CPM_calculation_increments:
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
        for cpm_increment in self.CPM_calculation_increments:
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
