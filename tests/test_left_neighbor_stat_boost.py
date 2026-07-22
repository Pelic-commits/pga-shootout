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


class LeftNeighborStatBoostTests(unittest.TestCase):
    CASES = (
        ("jumpstart", "power_boost", "power", 10, 3),
        ("galvanizer", "control_boost", "control", 10, 3),
        ("cyclotron", "spin_boost", "spin", 10, 5),
    )

    def state(self, club_ids, level, current_club_id):
        bag = SavedBag("left_boost", "Left Boost", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state, source_id, label_id):
        source = state.bag.get(source_id)
        return next(ability.effects[0] for ability in source.club.abilities if ability.text == label_id)

    def test_three_stats_share_one_generic_program_shape(self):
        entries = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]
        programs = [entries[f"label:{label}"]["program"] for _, label, _, _, _ in self.CASES]
        operations = tuple(node["operation"] for node in programs[0]["nodes"])

        self.assertEqual(operations, ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "ADD_STAT"))
        self.assertTrue(set(operations).issubset(default_dsl_registry().names))
        for program in programs[1:]:
            self.assertEqual(
                [{key: value for key, value in node.items() if key != "parameters"} for node in program["nodes"]],
                [{key: value for key, value in node.items() if key != "parameters"} for node in programs[0]["nodes"]],
            )

    def test_official_level_values_apply_to_each_stat(self):
        for source_id, label_id, stat, level, expected_delta in self.CASES:
            with self.subTest(label=label_id):
                state = self.state(("steadfast", source_id), level, "steadfast")
                effect = self.effect(state, source_id, label_id)
                before = getattr(state.current_entry.club.stats_at(level), stat)
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

                self.assertEqual(effect.parameters["level_value"], expected_delta)
                self.assertEqual(getattr(result.final_stats, stat), before + expected_delta)

    def test_only_the_left_neighbor_receives_the_bonus(self):
        state = self.state(("steadfast", "jumpstart", "divebomb"), 10, "divebomb")
        effect = self.effect(state, "jumpstart", "power_boost")
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

        self.assertEqual(result.final_stats, result.base_stats)
        self.assertFalse(result.explain[-2].applied)
        self.assertIn("not the current club", result.explain[-2].message)

    def test_source_at_left_edge_has_no_target(self):
        state = self.state(("jumpstart", "steadfast"), 10, "jumpstart")
        effect = self.effect(state, "jumpstart", "power_boost")
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

        self.assertEqual(result.final_stats, result.base_stats)
        self.assertFalse(result.explain[-2].applied)
        self.assertEqual(result.explain[-2].inputs["target"], None)
        self.assertIn("no target selected", result.explain[-2].message)

    def test_missing_level_value_does_not_create_an_effect(self):
        state = self.state(("rampart", "jumpstart"), 2, "rampart")
        self.assertNotIn("power_boost", {ability.text for ability in state.bag.get("jumpstart").club.abilities})

    def test_explain_contains_every_reused_primitive(self):
        state = self.state(("steadfast", "jumpstart"), 10, "steadfast")
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "jumpstart", "power_boost"),),
            mode=EvaluationMode.STRICT,
        )
        rendered = render_explain_entries(result.explain)

        self.assertEqual(
            [entry.mechanism for entry in result.explain[:4]],
            ["SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "ADD_STAT"],
        )
        self.assertTrue(all(entry.inputs and entry.outputs for entry in result.explain[:4]))
        self.assertIn('Outputs: {"left": "Steadfast"}', rendered)
        self.assertIn("Detail: POWER += 3", rendered)


if __name__ == "__main__":
    unittest.main()
