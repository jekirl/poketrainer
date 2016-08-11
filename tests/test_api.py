import unittest

from pgoapi.pokemon import Pokemon


mock_caught_eevee = {
    'move_1': 221,
    'move_2': 26,
    'captured_cell_id': 9970561120513919632,
    'pokeball': 1,
    'pokemon_id': 133,
    'creation_time_ms': 1469596340021,
    'height_m': 0.2028486435644989,
    'stamina_max': 69,
    'weight_kg': 1.812894354329834,
    'individual_defense': 3,
    'cp_multiplier': 0.5822789072940417,
    'stamina': 69,
    'individual_stamina': 9,
    'individual_attack': 15,
    'cp': 546,
    'id': 10537581451037376812
}

mock_wild_spearow = {
    'move_1': 211,
    'move_2': 45,
    'pokemon_id': 21,
    'height_m': 0.2692510320415297,
    'stamina_max': 27,
    'weight_kg': 1.8720885511213213,
    'individual_defense': 5,
    'cp_multiplier': 0.3210875988206512,
    'stamina': 27,
    'individual_stamina': 7,
    'individual_attack': 9,
    'cp': 97
}


class TestPokemon(unittest.TestCase):

    def test_wild_spearow_data(self):
        # Type: Spearow CP: 97, IV: 46.67, Lvl: 6.0, LvlWild: 6.0, MaxCP: 17, Score: 97, IV-Norm.: 47
        p = Pokemon(mock_wild_spearow, 0, 'CP', {})
        self.assertEqual(p.pokemon_type.decode('utf-8'), 'Spearow')
        self.assertEqual(p.cp, 97)
        self.assertEqual(round(p.iv, 2), 46.67)
        self.assertEqual(p.level, 6.0)
        self.assertEqual(p.level_wild, 6.0)
        self.assertEqual(round(p.max_cp), 17)
        self.assertEqual(p.score, 97)
        self.assertEqual(round(p.iv_normalized), 47)

    def test_caught_eevee_data(self):
        # Type: Eevee CP: 546, IV: 60.00, Lvl: 19.0, LvlWild: 19.0, MaxCP: 675, Score: 546, IV-Norm.: 69
        p = Pokemon(mock_caught_eevee, 22, 'CP', {})
        self.assertEqual(p.pokemon_type.decode('utf-8'), 'Eevee')
        self.assertEqual(p.cp, 546)
        self.assertEqual(round(p.iv, 2), 60.00)
        self.assertEqual(p.level, 19.0)
        self.assertEqual(p.level_wild, 19.0)
        self.assertEqual(round(p.max_cp), 675)
        self.assertEqual(p.score, 546)
        self.assertEqual(round(p.iv_normalized), 69)
