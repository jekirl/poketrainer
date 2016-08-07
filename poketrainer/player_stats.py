from time import time


class PlayerStats:
    def __init__(self, player_stats, pokemon_caught=0, start_time=time(), exp_start=None):
        self.player_stats = player_stats
        self.experience = 0
        self.next_level_xp = 0
        self.prev_level_xp = 0
        self.unique_pokedex_entries = 0
        self.km_walked = 0
        self.level = 0
        self.run_pokemon_caught = pokemon_caught
        self.run_start_time = start_time
        self.run_exp_start = exp_start
        self.run_duration_s = 0
        self.run_exp_earned = 0
        self.run_hourly_exp = 0
        self.parse_values()

    def parse_values(self):
        self.experience = self.player_stats.get('experience', 0)
        self.next_level_xp = self.player_stats.get('next_level_xp', 0)
        self.prev_level_xp = self.player_stats.get('prev_level_xp', 0)
        self.unique_pokedex_entries = self.player_stats.get('unique_pokedex_entries', 0)
        self.km_walked = self.player_stats.get('km_walked', 0)
        self.level = self.player_stats.get('level', 0)
        if not self.experience <= 0:
            if self.run_exp_start is None:
                self.run_exp_start = self.experience
            self.run_exp_earned = float(self.experience - self.run_exp_start)
            self.run_duration_s = float(time() - self.run_start_time)
            self.run_hourly_exp = float(self.run_exp_earned / (self.run_duration_s / 3600.00))

    def __str__(self):
        str_ = "Level: {0}, XP: {1}/{2}, Runtime (h): {3}, XP/h: {4}, Pokedex: {5}, km walked: {6:.2f}"
        return str_.format(self.level,
                           self.experience,
                           self.next_level_xp,
                           round((self.run_duration_s / 3600.00), 2),
                           round(self.run_hourly_exp),
                           self.unique_pokedex_entries,
                           self.km_walked)

    def __repr__(self):
        return self.__str__()
