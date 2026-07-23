import json
import shutil
import tempfile
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
            {"power": 1.0, "control": 0.0, "spin": 8.0},
        )
        rendered = render_bag_comparison(comparison)
        self.assertIn("Stats (difference = right - left)", rendered)
        self.assertIn("No aggregate score", rendered)
        self.assertNotIn("winner", rendered.casefold())

    def test_applied_changes_keep_only_leaf_effects(self):
        comparison = self.compare()
        self.assertEqual(
            [(change.source, change.mechanism) for change in comparison.left.applied_changes],
            [
                ("Jumpstart / jumpstart__power_boost", "ADD_STAT"),
                ("Steadfast / steadfast__bag_rarity_boost", "ADD_STAT"),
                ("Steadfast / steadfast__bag_rarity_boost", "ADD_STAT"),
                ("Steadfast / steadfast__bag_rarity_boost", "ADD_STAT"),
                ("Sunstorm / sunstorm__plasma_arc_x", "ADD_STAT"),
                ("Sunstorm / sunstorm__plasma_arc_x", "ADD_STAT"),
                ("Sunstorm / sunstorm__plasma_arc_x", "ADD_STAT"),
            ],
        )
        self.assertTrue(comparison.right.applied_changes)
        self.assertNotIn("dsl_pipeline", {change.mechanism for change in comparison.right.applied_changes})

    def test_exposes_machine_readable_contributions_for_every_ability(self):
        comparison = self.compare()
        contribution = next(
            item
            for item in comparison.left.ability_contributions
            if item.ability_id == "steadfast__bag_rarity_boost"
        )
        self.assertEqual(contribution.source_club_id, "steadfast")
        self.assertEqual(contribution.modification, {"power": 4.0, "control": 4.0, "spin": 4.0})
        self.assertTrue(contribution.evaluated)
        self.assertTrue(contribution.applied)
        unresolved = next(
            item for item in comparison.left.ability_contributions if item.ability_id == "divebomb__chains_into_putters"
        )
        self.assertTrue(unresolved.evaluated)
        self.assertFalse(unresolved.applied)
        self.assertTrue(unresolved.unresolved)

    def test_exposes_structured_gained_and_lost_bonus_totals(self):
        comparison = self.compare()
        self.assertEqual(comparison.gained_ability_impact, {"spin": 6.0})
        self.assertEqual(comparison.lost_ability_impact, {"power": -1.0, "control": -4.0})
        self.assertEqual(
            comparison.gained_modifier_impact,
            {
                "bounce_reduction_percent": 40.0,
                "loft_angle_degrees": 5.0,
                "wind_resistance_percent": 75.0,
            },
        )
        self.assertEqual(comparison.lost_modifier_impact, {})

    def test_new_tradeoff_is_reported_as_gained_and_lost_bonuses(self):
        with tempfile.TemporaryDirectory() as directory:
            user_dir = Path(directory) / "user"
            shutil.copytree(USER_DIR, user_dir)
            bags_path = user_dir / "bags.json"
            data = json.loads(bags_path.read_text(encoding="utf-8"))
            data["bags"].extend(
                [
                    {
                        "id": "baseline",
                        "name": "Baseline",
                        "status": "user_observed",
                        "club_ids": ["jumpstart", "outset", "high_flight", "rampart", "sunstorm"],
                    },
                    {
                        "id": "reckless",
                        "name": "Reckless",
                        "status": "user_observed",
                        "club_ids": ["jumpstart", "into_the_breach", "high_flight", "rampart", "sunstorm"],
                    },
                ]
            )
            bags_path.write_text(json.dumps(data), encoding="utf-8")
            comparison = compare_saved_bags(
                "baseline",
                "reckless",
                level=12,
                current_position=1,
                mode=EvaluationMode.PARTIAL,
                user_dir=user_dir,
                catalog_path=CATALOG,
            )

        self.assertEqual(
            comparison.ability_impact_difference_right_minus_left,
            {"power": 4.0, "control": -4.0, "spin": 4.0},
        )
        rendered = render_bag_comparison(comparison)
        self.assertIn("Bonuses gained by right vs left: power +4, spin +4", rendered)
        self.assertIn("Bonuses lost by right vs left: control -4", rendered)
        self.assertIn("Into the Breach / into_the_breach__bag_recklessness", rendered)

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
