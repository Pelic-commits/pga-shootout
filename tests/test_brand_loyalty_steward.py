import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import build_game_state
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"


class StewardBrandLoyaltyTests(unittest.TestCase):
    def state(self, club_ids, level):
        bag = SavedBag("steward_test", "Steward Test", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, "steward")

    def effect(self, state):
        return next(
            ability.effects[0]
            for ability in state.current_entry.club.abilities
            if ability.text == "brand_loyalty"
        )

    def test_configuration_reuses_the_reference_program_and_primitives(self):
        semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]
        configured = semantic["label:brand_loyalty"]
        reference = semantic["label:brand_loyalty_x"]
        operations = tuple(node["operation"] for node in configured["program"]["nodes"])

        self.assertEqual(configured["mechanic_id"], "dsl_pipeline")
        self.assertEqual(configured["program"], reference["program"])
        self.assertTrue(set(operations).issubset(default_dsl_registry().names))

    def test_official_level_values_with_one_matching_neighbor(self):
        expected = {8: (1, 12), 10: (2, 14), 12: (2, 15)}
        for level, (level_value, final_power) in expected.items():
            with self.subTest(level=level):
                state = self.state(("steward", "homestead"), level)
                effect = self.effect(state)
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

                self.assertEqual(effect.parameters["level_value"], level_value)
                self.assertEqual(result.final_stats.power, final_power)

    def test_two_distinct_willoughsby_neighbors_are_counted(self):
        state = self.state(("homestead", "steward", "steadfast"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)

        self.assertEqual(result.explain[4].outputs["count"], 2)
        self.assertEqual(result.final_stats.power, 16)

    def test_incompatible_neighbor_does_not_add_power(self):
        state = self.state(("steward", "divebomb"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)

        self.assertEqual(result.explain[4].outputs["count"], 0)
        self.assertEqual(result.final_stats.power, 12)

    def test_absent_level_value_does_not_create_the_ability(self):
        state = self.state(("steward", "homestead"), 7)
        self.assertNotIn("brand_loyalty", {ability.text for ability in state.current_entry.club.abilities})

    def test_explain_is_complete_for_every_reused_step(self):
        state = self.state(("homestead", "steward", "steadfast"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        entries = result.explain[:7]
        rendered = render_explain_entries(entries)

        self.assertEqual(
            [entry.mechanism for entry in entries],
            ["SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "MATCH_BRAND", "COUNT", "SCALE", "ADD_STAT"],
        )
        self.assertTrue(all(entry.inputs and entry.outputs for entry in entries))
        self.assertIn('Outputs: {"club": "Steward"}', rendered)
        self.assertIn('Outputs: {"left": "Homestead", "right": "Steadfast"}', rendered)
        self.assertIn("Detail: POWER += 4", rendered)


if __name__ == "__main__":
    unittest.main()
