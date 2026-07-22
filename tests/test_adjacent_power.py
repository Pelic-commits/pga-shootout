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


class AdjacentPowerTests(unittest.TestCase):
    def state(self, club_ids, level, current_club_id):
        bag = SavedBag("adjacent_power", "Adjacent Power", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state, source_id):
        source = state.bag.get(source_id)
        return next(ability.effects[0] for ability in source.club.abilities if ability.text == "adjacent_power")

    def test_configuration_uses_generic_iteration(self):
        entry = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]["label:adjacent_power"]
        operations = tuple(node["operation"] for node in entry["program"]["nodes"])
        nested = entry["program"]["nodes"][-1]["parameters"]["program"]["nodes"]

        self.assertEqual(operations, ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "FOR_EACH"))
        self.assertEqual(tuple(node["operation"] for node in nested), ("ADD_STAT",))
        self.assertTrue({*operations, "ADD_STAT"}.issubset(default_dsl_registry().names))

    def test_left_neighbor_receives_official_rampart_bonus(self):
        state = self.state(("steadfast", "rampart", "jumpstart"), 10, "steadfast")
        effect = self.effect(state, "rampart")
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

        self.assertEqual(effect.parameters["level_value"], 1)
        self.assertEqual(result.final_stats.power, result.base_stats.power + 1)

    def test_right_neighbor_receives_official_outlaw_bonus(self):
        state = self.state(("outlaw", "steadfast"), 10, "steadfast")
        effect = self.effect(state, "outlaw")
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

        self.assertEqual(effect.parameters["level_value"], 5)
        self.assertEqual(result.final_stats.power, result.base_stats.power + 5)

    def test_non_neighbor_and_source_are_unchanged(self):
        for current in ("outlaw", "jumpstart"):
            with self.subTest(current=current):
                state = self.state(("outlaw", "steadfast", "jumpstart"), 10, current)
                result = RuleEngine().evaluate(state, (self.effect(state, "outlaw"),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats, result.base_stats)

    def test_two_neighbors_create_two_ordered_iterations(self):
        state = self.state(("steadfast", "rampart", "jumpstart"), 10, "steadfast")
        result = RuleEngine().evaluate(state, (self.effect(state, "rampart"),), mode=EvaluationMode.STRICT)
        iteration = next(entry for entry in result.explain if entry.mechanism == "FOR_EACH")
        nested = [entry for entry in result.explain if entry.condition.startswith("DSL node each_neighbor[")]

        self.assertEqual(iteration.inputs["items"], ["Steadfast", "Jumpstart"])
        self.assertEqual(iteration.outputs["iterations"], 2)
        self.assertEqual([entry.condition for entry in nested], [
            "DSL node each_neighbor[0].apply_power",
            "DSL node each_neighbor[1].apply_power",
        ])

    def test_edge_position_iterates_only_existing_neighbor(self):
        state = self.state(("rampart", "steadfast"), 10, "steadfast")
        result = RuleEngine().evaluate(state, (self.effect(state, "rampart"),), mode=EvaluationMode.STRICT)
        iteration = next(entry for entry in result.explain if entry.mechanism == "FOR_EACH")

        self.assertEqual(iteration.outputs["iterations"], 1)

    def test_no_neighbor_produces_an_empty_iteration(self):
        state = self.state(("rampart",), 10, "rampart")
        result = RuleEngine().evaluate(state, (self.effect(state, "rampart"),), mode=EvaluationMode.STRICT)
        iteration = next(entry for entry in result.explain if entry.mechanism == "FOR_EACH")

        self.assertEqual(iteration.inputs["items"], [])
        self.assertEqual(iteration.outputs["iterations"], 0)
        self.assertEqual(result.final_stats, result.base_stats)

    def test_absent_level_value_does_not_create_effect(self):
        state = self.state(("rampart", "outlaw"), 1, "rampart")
        self.assertNotIn("adjacent_power", {ability.text for ability in state.bag.get("outlaw").club.abilities})

    def test_strict_and_partial_modes_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(("rampart", "steadfast"), 10, "steadfast")
                result = RuleEngine().evaluate(state, (self.effect(state, "rampart"),), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.unresolved, ())

    def test_explain_reports_iteration_inputs_and_effect_outputs(self):
        state = self.state(("steadfast", "rampart", "jumpstart"), 10, "steadfast")
        result = RuleEngine().evaluate(state, (self.effect(state, "rampart"),), mode=EvaluationMode.STRICT)
        rendered = render_explain_entries(result.explain)

        self.assertIn('Inputs: {"binding": "target", "items": ["Steadfast", "Jumpstart"]}', rendered)
        self.assertIn('Outputs: {"iterations": 2}', rendered)
        self.assertIn("Detail: POWER += 1", rendered)


if __name__ == "__main__":
    unittest.main()
