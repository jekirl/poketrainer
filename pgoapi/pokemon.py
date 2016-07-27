
class Pokemon:
    def __init__(self, pokemon_data=dict(), pokemon_names=dict(), additional_data=None):
        self.pokemon_data = pokemon_data
        self.stamina = 0
        self.pokemon_id = 0
        self.cp = 0
        self.stamina_max = 0
        self.is_egg = False
        self.origin = -1
        self.height_m = 0.0
        self.weight_kg = 0.0
        self.individual_attack = 0
        self.individual_defense = 0
        self.individual_stamina = 0
        self.cp_multiplier = 0.0
        self.nickname = ""
        self.additional_cp_multiplier = 0.0
        self.id = 0
        self.pokemon_id = 0
        self.favorite = -1
        self.is_favorite = False
        self.iv = 0.0
        self.parse_values()
        self.pokemon_type = pokemon_names.get(str(self.pokemon_id), "NA").encode('utf-8', 'ignore')
        self.pokemon_additional_data = additional_data

    def parse_values(self):
        self.stamina = self.pokemon_data.get('stamina', 0)
        self.favorite = self.pokemon_data.get('favorite', -1)
        self.is_favorite = self.favorite != -1
        self.pokemon_id = self.pokemon_data.get('pokemon_id', 0)
        self.id = self.pokemon_data.get('id', 0)
        self.cp = self.pokemon_data.get('cp', 0)
        self.stamina_max = self.pokemon_data.get('stamina_max', 0)
        self.is_egg = self.pokemon_data.get('is_egg', False)
        self.origin = self.pokemon_data.get('origin', 0)
        self.height_m = self.pokemon_data.get('height', 0.0)
        self.weight_kg = self.pokemon_data.get('weight_kg', 0.0)
        self.individual_attack = self.pokemon_data.get('individual_attack', 0)
        self.individual_defense = self.pokemon_data.get('individual_defense', 0)
        self.individual_stamina = self.pokemon_data.get('individual_stamina', 0)
        self.cp_multiplier = self.pokemon_data.get('cp_multiplier', 0.0)
        self.additional_cp_multiplier = self.pokemon_data.get('additional_cp_multiplier', 0.0)
        self.nickname = self.pokemon_data.get('nickname', "").encode('utf8')
        self.iv = self.get_iv_percentage()

    def __str__(self):
        return "Nickname: {0}, Type: {1}, CP: {2}, IV: {3}".format(self.nickname, self.pokemon_type, self.cp, self.iv)

    def __repr__(self):
        return self.__str__()

    def get_iv_percentage(self):
        return ((self.individual_attack + self.individual_stamina + self.individual_defense + 0.0) / 45.0) * 100.0

    def is_valid_pokemon(self):
        return self.pokemon_id > 0
