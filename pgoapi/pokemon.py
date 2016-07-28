from __future__ import absolute_import

from math import sqrt
from pgoapi.player import Player as Player

class Pokemon:
    def __init__(self, pokemon_data=dict(), pokemon_names=dict(), additional_data=None, score_expression=None, player_level=1):
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

        self.max_cp = -1.0
        self.score = -1.0

        if additional_data is not None:
            # Thanks to http://pokemongo.gamepress.gg/pokemon-stats-advanced for the magical formulas
            cp_multiplier = Player.CP_Multipliers[player_level-1]
            attack = float(additional_data.BaseAttack) + 15
            defense = float(additional_data.BaseDefense) + 15
            stamina = float(additional_data.BaseStamina) + 15

            self.max_cp = (attack * sqrt(defense) * sqrt(stamina) * cp_multiplier * cp_multiplier) / 10

        if score_expression is not None:
            CP = self.cp
            MAX_CP = self.max_cp
            IV = self.iv

            try:
                self.score = eval(score_expression)
            except Exception as e:
                pass

    def __str__(self):
        nickname = ""

        if len(self.nickname) > 0:
            nickname = "Nickname: " + self.nickname + ", "

        if self.max_cp > 0:
            return "{0}Type: {1}, CP: {2}, IV: {3:.2f}, Max CP: {4:.0f}, Score: {5:.2f}".format(nickname, self.pokemon_type, self.cp, self.iv, self.max_cp, self.score)
        else:
            return "{0}Type: {1}, CP: {2}, IV: {3:.2f}".format(nickname, self.pokemon_type, self.cp, self.iv)

    def __repr__(self):
        return self.__str__()

    def get_iv_percentage(self):
        return ((self.individual_attack + self.individual_stamina + self.individual_defense + 0.0) / 45.0) * 100.0

    def is_valid_pokemon(self):
        return self.pokemon_id > 0
