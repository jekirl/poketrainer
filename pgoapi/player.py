
class Player:
    CP_Multipliers = [
        0.094     ,  0.16639787,  0.21573247,  0.25572005,  0.29024988,
        0.3210876 ,  0.34921268,  0.37523559,  0.39956728,  0.42250001,
        0.44310755,  0.46279839,  0.48168495,  0.49985844,  0.51739395,
        0.53435433,  0.55079269,  0.56675452,  0.58227891,  0.59740001,
        0.61215729,  0.62656713,  0.64065295,  0.65443563,  0.667934  ,
        0.68116492,  0.69414365,  0.70688421,  0.71939909,  0.7317    ,
        0.73776948,  0.74378943,  0.74976104,  0.75568551,  0.76156384,
        0.76739717,  0.7731865 ,  0.77893275,  0.78463697,  0.79030001
    ]

    def __init__(self, player_data):
        self.player_data = player_data
        self.username = 0
        self.team = 0
        self.max_pokemon_storage = 0
        self.creation_timestamp_ms = 0
        self.max_item_storage = 0
        self.currencies = []
        self.parse_values()

    def parse_values(self):
        self.username = self.player_data.get('username', 'NA')
        self.team = self.player_data.get('team', 0)
        self.max_pokemon_storage = self.player_data.get('max_pokemon_storage', 0)
        self.creation_timestamp_ms = self.player_data.get('creation_timestamp_ms', 0)
        self.max_item_storage = self.player_data.get('max_item_storage', 0)
        self.currencies = self.player_data.get('currencies', [])

    def __str__(self):
        currency_data = ",".join(
            map(lambda x: "{0}: {1}".format(x.get('name', 'NA'), x.get('amount', 'NA')), self.currencies))
        return "{0}, Currencies: {1}".format(self.username, currency_data).encode('utf-8', 'ignore')

    def __repr__(self):
        return self.__str__()
