import json


class Player:
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
        return "{0}, Currencies: {1}".format(self.username, currency_data)

    def __repr__(self):
        return self.__str__()

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
