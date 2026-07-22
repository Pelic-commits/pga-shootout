import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import _semantic_program, build_game_state
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"


class BagRarityBoostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    def state(self, club_ids, level, current_club_id):
        bag = SavedBag("rarity", "Rarity", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state):
        return next(
            ability.effects[0]
            for ability in state.bag.get("steadfast").club.abilities
            if ability.text == "bag_rarity_boost"
        )

    def test_program_uses_only_generic_dsl_primitives(self):
        entry = self.semantic["entries"]["label:bag_rarity_boost"]
        program = _semantic_program(entry, self.semantic["patterns"])
        self.assertEqual(
            tuple(node["operation"] for node in program["nodes"]),
            ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ALL", "MATCH_RARITY", "FOR_EACH"),
        )
        self.assertTrue(
            {"SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ALL", "MATCH_RARITY", "FOR_EACH", "ADD_STAT"}.issubset(
                default_dsl_registry().names
            )
        )

    def test_catalog_rarity_is_loaded_into_game_state(self):
        state = self.state(("divebomb", "jumpstart", "steadfast", "sunstorm"), 12, "divebomb")
        self.assertEqual(
            [entry.club.rarity for entry in state.bag.entries],
            ["common", "rare", "epic", "epic"],
        )

    def test_common_and_rare_targets_gain_all_stats(self):
        state = self.state(("divebomb", "jumpstart", "steadfast", "sunstorm"), 12, "divebomb")
        effect = self.effect(state)
        for current_id, expected_delta in (("divebomb", 4), ("jumpstart", 4), ("steadfast", 0), ("sunstorm", 0)):
            with self.subTest(current=current_id):
                current_state = self.state(tuple(entry.club.identifier for entry in state.bag.entries), 12, current_id)
                result = RuleEngine().evaluate(current_state, (self.effect(current_state),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected_delta)
                self.assertEqual(result.final_stats.control, result.base_stats.control + expected_delta)
                self.assertEqual(result.final_stats.spin, result.base_stats.spin + expected_delta)

    def test_official_level_values_are_respected(self):
        for level, expected in ((5, 2), (10, 3), (11, 4), (12, 4)):
            with self.subTest(level=level):
                state = self.state(("divebomb", "steadfast"), level, "divebomb")
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected)
        elite_state = self.state(("divebomb", "steadfast"), "Elite", "steadfast")
        self.assertEqual(self.effect(elite_state).parameters["level_value"], 4)

    def test_absent_level_value_does_not_create_the_effect(self):
        state = self.state(("divebomb", "steadfast"), 1, "divebomb")
        self.assertNotIn("bag_rarity_boost", {ability.text for ability in state.bag.get("steadfast").club.abilities})

    def test_strict_and_partial_modes_both_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(("divebomb", "steadfast"), 12, "divebomb")
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.unresolved, ())

    def test_explain_lists_filter_inputs_and_each_stat_effect(self):
        state = self.state(("divebomb", "jumpstart", "steadfast", "sunstorm"), 12, "divebomb")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        rendered = render_explain_entries(result.explain)

        self.assertIn('Inputs: {"candidates": ["Divebomb", "Jumpstart", "Steadfast", "Sunstorm"], "operator": "in", "rarity": ["common", "rare"]}', rendered)
        self.assertIn("Detail: POWER += 4", rendered)
        self.assertIn("Detail: CONTROL += 4", rendered)
        self.assertIn("Detail: SPIN += 4", rendered)


if __name__ == "__main__":
    unittest.main()
