import unittest
from pathlib import Path

from pga_shootout.bag_comparison import compare_saved_bags
from pga_shootout.bag_evaluation import build_game_state, evaluate_saved_bag, load_saved_bag
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "maelstrom_bag_bounce_reduction_explain.txt"


class BagBounceReductionTests(unittest.TestCase):
    @staticmethod
    def effect(state):
        return next(
            ability.effects[0]
            for ability in state.bag.get("maelstrom").club.abilities
            if ability.text == "bag_bounce_reduction"
        )

    def test_official_level_values_apply_to_matching_types(self):
        bag = load_saved_bag(USER_DIR, "par3_high_flight")
        for level, expected in ((5, 10), (8, 14), (12, 20), ("Elite", 22)):
            with self.subTest(level=level):
                current = "cyclotron" if level == "Elite" else "high_flight"
                levels = {
                    "high_flight": 12,
                    "cyclotron": level,
                    "ember": 10,
                    "maelstrom": level,
                    "sunstorm": 10,
                }
                state = build_game_state(bag, CATALOG, levels, current)
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.modifiers, {"bounce_reduction_percent": float(expected)})
                self.assertEqual(result.final_stats, result.base_stats)

    def test_driver_wood_and_hybrid_match_while_putter_and_wedge_do_not(self):
        bag = load_saved_bag(USER_DIR, "par3_high_flight")
        expected_by_club = {
            "high_flight": 20,
            "cyclotron": 20,
            "maelstrom": 0,
            "sunstorm": 20,
        }
        levels = {"high_flight": 12, "cyclotron": 12, "ember": 10, "maelstrom": 12, "sunstorm": 10}
        for club_id, expected in expected_by_club.items():
            with self.subTest(club_id=club_id):
                state = build_game_state(bag, CATALOG, levels, club_id)
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.modifiers.get("bounce_reduction_percent", 0), expected)

        source_state = build_game_state(bag, CATALOG, levels, "high_flight")
        rendered = render_explain_entries(
            RuleEngine().evaluate(source_state, (self.effect(source_state),), mode=EvaluationMode.STRICT).explain
        )
        self.assertIn('Inputs: {"binding": "target", "items": ["High Flight", "Cyclotron", "Sunstorm"]}', rendered)

    def test_strict_partial_and_full_bag_contribution(self):
        bag = load_saved_bag(USER_DIR, "par3_high_flight")
        state = build_game_state(bag, CATALOG, 12, "high_flight")
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.modifiers["bounce_reduction_percent"], 20)

        evaluation = evaluate_saved_bag(
            "par3_high_flight",
            level=12,
            mode=EvaluationMode.PARTIAL,
            user_dir=USER_DIR,
            catalog_path=CATALOG,
            current_club_id="high_flight",
        )
        self.assertEqual(evaluation.result.modifiers["bounce_reduction_percent"], 20)
        self.assertEqual(len(evaluation.result.unresolved), 4)

    def test_compare_bags_exposes_the_new_metric(self):
        comparison = compare_saved_bags(
            "par3_divebomb",
            "par3_high_flight",
            level=12,
            current_position=1,
            mode=EvaluationMode.PARTIAL,
            user_dir=USER_DIR,
            catalog_path=CATALOG,
        )
        metric = next(item for item in comparison.metrics if item.definition.identifier == "bounce_reduction_percent")
        self.assertEqual((metric.left_final, metric.right_final, metric.difference_right_minus_left), (0, 20, 20))
        contribution = next(
            item for item in comparison.right.ability_contributions
            if item.ability_id == "maelstrom__bag_bounce_reduction"
        )
        self.assertEqual(contribution.modification["bounce_reduction_percent"], 20)

    def test_explain_matches_golden_file(self):
        bag = load_saved_bag(USER_DIR, "par3_high_flight")
        state = build_game_state(bag, CATALOG, 12, "high_flight")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        self.assertEqual(render_explain_entries(result.explain) + "\n", GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
