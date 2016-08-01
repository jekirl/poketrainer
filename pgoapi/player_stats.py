class PlayerStats:
    def __init__(self, player_stats):
        self.player_stats = player_stats
        self.experience = 0
        self.next_level_xp = 0
        self.prev_level_xp = 0
        self.unique_pokedex_entries = 0
        self.km_walked = 0
        self.level = 0
        self.parse_values()

    def parse_values(self):
        self.experience = self.player_stats.get('experience', 0)
        self.next_level_xp = self.player_stats.get('next_level_xp', 0)
        self.prev_level_xp = self.player_stats.get('prev_level_xp', 0)
        self.unique_pokedex_entries = self.player_stats.get('unique_pokedex_entries', 0)
        self.km_walked = self.player_stats.get('km_walked', 0)
        self.level = self.player_stats.get('level', 0)

    def __str__(self):
        str_ = "Level: {0}, XP: {1}/{2}, Pokedex: {3}, km walked: {4:.2f}"
        return str_.format(self.level,
                           self.experience,
                           self.next_level_xp,
                           self.unique_pokedex_entries,
                           self.km_walked)

    def __repr__(self):
        return self.__str__()
