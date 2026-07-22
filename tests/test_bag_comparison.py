import unittest
from pathlib import Path

from pga_shootout.bag_comparison import BagComparisonError, compare_saved_bags, render_bag_comparison
from pga_shootout.models import EvaluationMode


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"


class BagComparisonTests(unittest.TestCase):
    def compare(self, left="par3_divebomb", right="par3_high_flight", **overrides):
        parameters = {
            "level": 12,
            "current_position": 1,
            "mode": EvaluationMode.PARTIAL,
            "user_dir": USER_DIR,
            "catalog_path": CATALOG,
        }
        parameters.update(overrides)
        return compare_saved_bags(left, right, **parameters)

    def test_compares_the_clubs_at_the_same_selected_position(self):
        comparison = self.compare()
        self.assertEqual(comparison.left.evaluation.state.current_club_id, "divebomb")
        self.assertEqual(comparison.right.evaluation.state.current_club_id, "high_flight")
        self.assertEqual(comparison.left.current_position, 1)
        self.assertEqual(comparison.right.current_position, 1)

    def test_reports_reproducible_per_stat_differences_without_scoring(self):
        comparison = self.compare()
        self.assertEqual(
            comparison.final_difference_right_minus_left,
            {"power": 5.0, "control": 4.0, "spin": 12.0},
        )
        rendered = render_bag_comparison(comparison)
        self.assertIn("Stats (difference = right - left)", rendered)
        self.assertIn("No aggregate score", rendered)
        self.assertNotIn("winner", rendered.casefold())

    def test_applied_changes_keep_only_leaf_effects(self):
        comparison = self.compare()
        self.assertEqual(
            [(change.source, change.mechanism) for change in comparison.left.applied_changes],
            [("Jumpstart / jumpstart__power_boost", "ADD_STAT")],
        )
        self.assertTrue(comparison.right.applied_changes)
        self.assertNotIn("dsl_pipeline", {change.mechanism for change in comparison.right.applied_changes})

    def test_composition_is_rendered_position_by_position(self):
        rendered = render_bag_comparison(self.compare())
        self.assertIn("1. Divebomb != High Flight", rendered)
        self.assertIn("5. Sunstorm == Sunstorm", rendered)

    def test_comparing_a_bag_with_itself_produces_zero_differences(self):
        comparison = self.compare("par3_divebomb", "par3_divebomb")
        self.assertEqual(
            comparison.final_difference_right_minus_left,
            {"power": 0.0, "control": 0.0, "spin": 0.0},
        )

    def test_strict_failure_is_preserved_for_the_cli_exit_status(self):
        comparison = self.compare(mode=EvaluationMode.STRICT)
        self.assertTrue(comparison.strict_failed)
        self.assertIn("Strict status: FAILED", render_bag_comparison(comparison))

    def test_position_must_exist_in_both_bags(self):
        for position in (0, 6):
            with self.subTest(position=position):
                with self.assertRaises(BagComparisonError):
                    self.compare(current_position=position)


if __name__ == "__main__":
    unittest.main()
