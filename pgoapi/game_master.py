import csv
import re
from os import path

from six import iteritems


class PokemonData(object):
    def __init__(self):
        self.PkMn = 0
        self.BaseStamina = 0
        self.BaseAttack = 0
        self.BaseDefense = 0
        self.Type1 = ''
        self.Type2 = ''
        self.BaseCaptureRate = 0.0
        self.BaseFleeRate = 0.0
        self.CollisionRadiusM = 0.0
        self.CollisionHeightM = 0.0
        self.CollisionHeadRadiusM = 0.0
        self.MovementType = 0.0
        self.MovementTimerS = 0.0
        self.JumpTimeS = 0.0
        self.AttackTimerS = 0.0
        self.QuickMoves = ''
        self.CinematicMoves = ''
        self.AnimTime = 0.0
        self.Evolution = 0.0
        self.EvolutionPips = None
        self.PokemonClass = ''
        self.PokedexHeightM = 0.0
        self.PokedexWeightKg = 0.0
        self.HeightStdDev = 0.0
        self.WeightStdDev = 0.0
        self.FamilyId = 0.0
        self.CandyToEvolve = 0.0


GAME_MASTER = {}

_game_master_file_path = path.join(path.dirname(path.dirname(__file__)), "GAME_MASTER_POKEMON_v0_2.tsv")
with open(_game_master_file_path) as tsvfile:
    tsvreader = csv.DictReader(tsvfile, delimiter='\t')
    attributes = []
    for row in tsvreader:
        row["FamilyId"] = re.match("HoloPokemonFamilyId.V([0-9]*).*", row["FamilyId"]).group(1)
        pokemon_data = PokemonData()
        for (k, v) in iteritems(row):
            setattr(pokemon_data, k, v)
        GAME_MASTER[int(row["PkMn"])] = pokemon_data
