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
GOLDEN = ROOT / "tests" / "golden" / "high_flight_loft_explain.txt"


class StaticLoftModifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    def state(self, club_ids, level, current_club_id):
        return build_game_state(
            SavedBag("loft", "Loft", "active", tuple(club_ids), ()),
            CATALOG,
            level,
            current_club_id,
        )

    @staticmethod
    def effect(state, source_id, label):
        return next(ability.effects[0] for ability in state.bag.get(source_id).club.abilities if ability.text == label)

    def test_both_families_share_the_same_generic_pattern(self):
        entries = self.semantic["entries"]
        patterns = self.semantic["patterns"]
        for label in ("bag_loft_angle_10", "loft_angle_5"):
            entry = entries[f"label:{label}"]
            self.assertEqual(entry["pattern_id"], "static_modifier_targets")
            program = _semantic_program(entry, patterns)
            self.assertEqual(
                tuple(node["operation"] for node in program["nodes"]),
                ("SELECT_SELF", "READ_LEVEL_VALUE", entry["pattern_parameters"]["selection_operation"], "FOR_EACH"),
            )
        self.assertIn("ADD_MODIFIER", default_dsl_registry().names)

    def test_high_flight_adds_five_degrees_only_to_itself(self):
        for current_id, expected in (("high_flight", 5), ("divebomb", 0)):
            with self.subTest(current=current_id):
                state = self.state(("high_flight", "divebomb"), 12, current_id)
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "high_flight", "loft_angle_5"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers.get("loft_angle_degrees", 0), expected)

    def test_cloudcatcher_adds_ten_degrees_to_every_club(self):
        for current_id in ("cloudcatcher", "high_flight", "divebomb"):
            with self.subTest(current=current_id):
                state = self.state(("cloudcatcher", "high_flight", "divebomb"), 12, current_id)
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "cloudcatcher", "bag_loft_angle_10"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers, {"loft_angle_degrees": 10.0})

    def test_modifiers_stack_additively_without_changing_official_stats(self):
        state = self.state(("cloudcatcher", "high_flight", "divebomb"), 12, "high_flight")
        result = RuleEngine().evaluate(
            state,
            (
                self.effect(state, "cloudcatcher", "bag_loft_angle_10"),
                self.effect(state, "high_flight", "loft_angle_5"),
            ),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(result.modifiers, {"loft_angle_degrees": 15.0})
        self.assertEqual(result.final_stats, result.base_stats)

    def test_absent_level_value_creates_no_effect(self):
        state = self.state(("divebomb", "cloudcatcher"), 1, "divebomb")
        self.assertNotIn("bag_loft_angle_10", {ability.text for ability in state.bag.get("cloudcatcher").club.abilities})

    def test_strict_partial_and_explain_are_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(("high_flight", "divebomb"), 12, "high_flight")
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "high_flight", "loft_angle_5"),),
                    mode=mode,
                )
                self.assertTrue(result.complete)
                rendered = render_explain_entries(result.explain)
                self.assertIn('Inputs: {"delta": 5.0, "modifier": "loft_angle_degrees", "target": "High Flight"}', rendered)
                self.assertIn("Detail: LOFT_ANGLE_DEGREES += 5", rendered)

    def test_high_flight_explain_matches_the_golden_file(self):
        state = self.state(("high_flight", "cyclotron"), 12, "high_flight")
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "high_flight", "loft_angle_5"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(render_explain_entries(result.explain) + "\n", GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
