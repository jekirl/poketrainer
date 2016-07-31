import csv
from utilities import take_closest


class PokemonLvlData:
    def __init__(self):
        self.total_cp_multiplier = 0.0
        self.stardust_to_this_lvl = 0
        self.candy_to_this_lvl = 0
        self.power_up_result = 0.0
        self.stardust_to_power_up = 0
        self.candy_to_power_up = 0
        self.pokemon_lvl = 0
        self.tcpm_difference = 0.0


POKEMON_LVL_DATA = {}
TCPM_VALS = []
with open ("PoGoPokeLvl.tsv") as tsv: #data gathered from here: https://www.reddit.com/r/TheSilphRoad/comments/4sa4p5/stardust_costs_increase_every_4_power_ups/
    reader = csv.DictReader(tsv, delimiter='\t')
    for row in reader:
        pokemon_lvl_data = PokemonLvlData()

        pokemon_lvl_data.total_cp_multiplier = float(row["TotalCpMultiplier"])
        pokemon_lvl_data.stardust_to_this_lvl = int(row["Stardust to this level"])
        pokemon_lvl_data.candy_to_this_lvl = int(row["Candies to this level"])
        pokemon_lvl_data.pokemon_lvl = int(row["Pokemon level"])
        pokemon_lvl_data.power_up_result = float(row["Delta(TCpM^2)"])
        pokemon_lvl_data.tcpm_difference = float(row["TCPM Difference"])
        pokemon_lvl_data.stardust_to_power_up = int(row["Stardust"])
        pokemon_lvl_data.candy_to_power_up = int(row["Candies"])

        POKEMON_LVL_DATA[pokemon_lvl_data.total_cp_multiplier] = pokemon_lvl_data
        TCPM_VALS.append(pokemon_lvl_data.total_cp_multiplier)

def get_tcpm(tcpm):
    return take_closest(tcpm, TCPM_VALS)