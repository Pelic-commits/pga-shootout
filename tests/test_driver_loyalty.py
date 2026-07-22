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


class DriverLoyaltyTests(unittest.TestCase):
    SOURCE = "people_s_champion"

    def state(self, club_ids, level):
        bag = SavedBag("driver_loyalty", "Driver Loyalty", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, self.SOURCE)

    @staticmethod
    def effect(state):
        return next(ability.effects[0] for ability in state.current_entry.club.abilities if ability.text == "driver_loyalty")

    def test_configuration_reuses_the_reference_pipeline_shape(self):
        entries = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]
        program = entries["label:driver_loyalty"]["program"]
        operations = tuple(node["operation"] for node in program["nodes"])

        self.assertEqual(
            operations,
            ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "MATCH_TYPE", "COUNT", "SCALE", "ADD_STAT"),
        )
        self.assertTrue(set(operations).issubset(default_dsl_registry().names))
        self.assertEqual(program["nodes"][3]["parameters"]["expected"], "driver")

    def test_no_matching_driver_adds_nothing(self):
        state = self.state(("jumpstart", self.SOURCE, "steadfast"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)

        self.assertEqual(result.final_stats.power, result.base_stats.power)
        self.assertEqual(result.explain[4].outputs["count"], 0)

    def test_one_matching_driver_uses_official_level_value(self):
        state = self.state(("rampart", self.SOURCE, "jumpstart"), 10)
        effect = self.effect(state)
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

        self.assertEqual(effect.parameters["level_value"], 4)
        self.assertEqual(result.explain[4].outputs["count"], 1)
        self.assertEqual(result.final_stats.power, result.base_stats.power + 4)

    def test_two_matching_drivers_are_counted(self):
        state = self.state(("rampart", self.SOURCE, "cyclotron"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)

        self.assertEqual(result.explain[3].outputs["left"]["matches"], True)
        self.assertEqual(result.explain[3].outputs["right"]["matches"], True)
        self.assertEqual(result.explain[4].outputs["count"], 2)
        self.assertEqual(result.final_stats.power, result.base_stats.power + 8)

    def test_edge_position_counts_only_existing_neighbor(self):
        state = self.state((self.SOURCE, "rampart"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)

        self.assertEqual(result.explain[2].outputs, {"left": None, "right": "Rampart"})
        self.assertEqual(result.explain[4].outputs["count"], 1)

    def test_official_values_at_different_levels(self):
        for level, expected in ((5, 3), (9, 4), (12, 5)):
            with self.subTest(level=level):
                state = self.state(("rampart", self.SOURCE), level)
                effect = self.effect(state)
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.parameters["level_value"], expected)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected)

    def test_strict_and_partial_modes_both_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(("rampart", self.SOURCE), 10)
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.unresolved, ())

    def test_explain_contains_inputs_and_outputs_for_every_primitive(self):
        state = self.state(("rampart", self.SOURCE, "jumpstart"), 10)
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        entries = result.explain[:7]
        rendered = render_explain_entries(entries)

        self.assertTrue(all(entry.inputs and entry.outputs for entry in entries))
        self.assertIn('Inputs: {"candidates": ["Rampart", "Jumpstart"], "type": "driver"}', rendered)
        self.assertIn('Outputs: {"left": {"club": "Rampart", "matches": true}', rendered)
        self.assertIn("Detail: POWER += 4", rendered)


if __name__ == "__main__":
    unittest.main()
