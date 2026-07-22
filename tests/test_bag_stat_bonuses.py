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


class BagStatBonusTests(unittest.TestCase):
    CASES = (
        ("commonlaw", "bag_control", "control", False),
        ("maelstrom", "bag_spin_bonus", "spin", True),
    )

    def state(self, club_ids, level, current_club_id):
        bag = SavedBag("bag_stats", "Bag Stats", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state, source_id, label_id):
        source = state.bag.get(source_id)
        return next(ability.effects[0] for ability in source.club.abilities if ability.text == label_id)

    def test_families_share_the_same_pipeline_shape(self):
        entries = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]
        programs = [entries[f"label:{label}"]["program"] for _, label, _, _ in self.CASES]

        for program in programs:
            self.assertEqual(
                tuple(node["operation"] for node in program["nodes"]),
                ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ALL", "FOR_EACH"),
            )
            self.assertEqual(program["nodes"][-1]["parameters"]["program"]["nodes"][0]["operation"], "ADD_STAT")
        self.assertTrue({"SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ALL", "FOR_EACH", "ADD_STAT"}.issubset(default_dsl_registry().names))

    def test_bag_control_applies_to_other_clubs_only(self):
        for current, expected_delta in (("commonlaw", 0), ("steadfast", 1), ("jumpstart", 1)):
            with self.subTest(current=current):
                state = self.state(("steadfast", "commonlaw", "jumpstart"), 5, current)
                effect = self.effect(state, "commonlaw", "bag_control")
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats.control, result.base_stats.control + expected_delta)

    def test_bag_spin_bonus_includes_every_club_and_source(self):
        for current in ("maelstrom", "steadfast", "jumpstart"):
            with self.subTest(current=current):
                state = self.state(("steadfast", "maelstrom", "jumpstart"), 5, current)
                effect = self.effect(state, "maelstrom", "bag_spin_bonus")
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats.spin, result.base_stats.spin + 2)

    def test_select_all_preserves_order_and_source_policy(self):
        for source_id, label_id, _, include_source in self.CASES:
            with self.subTest(label=label_id):
                others = ("steadfast", "jumpstart")
                club_ids = (others[0], source_id, others[1])
                state = self.state(club_ids, 5, others[0])
                result = RuleEngine().evaluate(state, (self.effect(state, source_id, label_id),), mode=EvaluationMode.STRICT)
                selection = next(entry for entry in result.explain if entry.mechanism == "SELECT_ALL")
                expected = [state.bag.get(club_id).club.name for club_id in club_ids if include_source or club_id != source_id]

                self.assertEqual(selection.outputs["clubs"], expected)
                self.assertEqual(selection.inputs["include_source"], include_source)

    def test_official_values_at_different_levels(self):
        cases = (
            ("commonlaw", "bag_control", "control", ((5, 1), (7, 2), (12, 3))),
            ("maelstrom", "bag_spin_bonus", "spin", ((5, 2), (7, 3), (10, 4))),
        )
        for source_id, label_id, stat, levels in cases:
            for level, expected in levels:
                with self.subTest(label=label_id, level=level):
                    state = self.state(("steadfast", source_id), level, "steadfast")
                    effect = self.effect(state, source_id, label_id)
                    result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                    self.assertEqual(effect.parameters["level_value"], expected)
                    self.assertEqual(getattr(result.final_stats, stat), getattr(result.base_stats, stat) + expected)

    def test_absent_level_values_do_not_create_effects(self):
        state = self.state(("rampart", "commonlaw", "maelstrom"), 1, "rampart")
        self.assertNotIn("bag_control", {ability.text for ability in state.bag.get("commonlaw").club.abilities})
        self.assertNotIn("bag_spin_bonus", {ability.text for ability in state.bag.get("maelstrom").club.abilities})

    def test_strict_and_partial_modes_complete(self):
        for source_id, label_id, _, _ in self.CASES:
            for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
                with self.subTest(label=label_id, mode=mode):
                    state = self.state(("steadfast", source_id), 5, "steadfast")
                    result = RuleEngine().evaluate(state, (self.effect(state, source_id, label_id),), mode=mode)
                    self.assertTrue(result.complete)
                    self.assertEqual(result.unresolved, ())

    def test_explain_contains_selection_iteration_and_effect(self):
        state = self.state(("steadfast", "commonlaw", "jumpstart"), 5, "steadfast")
        result = RuleEngine().evaluate(state, (self.effect(state, "commonlaw", "bag_control"),), mode=EvaluationMode.STRICT)
        rendered = render_explain_entries(result.explain)

        self.assertIn('Outputs: {"clubs": ["Steadfast", "Jumpstart"]}', rendered)
        self.assertIn('Outputs: {"iterations": 2}', rendered)
        self.assertIn("Detail: CONTROL += 1", rendered)


if __name__ == "__main__":
    unittest.main()
