import unittest
from pathlib import Path

from pga_shootout.bag_comparison import compare_saved_bags, render_bag_comparison
from pga_shootout.models import EvaluationMode


ROOT = Path(__file__).resolve().parents[1]


class ComparisonDiagnosticTests(unittest.TestCase):
    def comparison(self):
        return compare_saved_bags(
            "par3_divebomb",
            "par3_high_flight",
            level=12,
            current_position=1,
            mode=EvaluationMode.PARTIAL,
            user_dir=ROOT / "data" / "user",
            catalog_path=ROOT / "data" / "normalized" / "clubs_official.json",
        )

    def test_diagnostic_reports_only_countable_facts(self):
        diagnostic = self.comparison().diagnostic
        self.assertEqual(
            diagnostic.metrics_compared,
            ("power", "control", "spin", "bounce_reduction_percent", "loft_angle_degrees"),
        )
        self.assertEqual(
            (
                diagnostic.left.simulated_abilities,
                diagnostic.left.non_simulated_abilities,
                diagnostic.right.simulated_abilities,
                diagnostic.right.non_simulated_abilities,
            ),
            (5, 3, 7, 2),
        )
        self.assertEqual(diagnostic.left.unknown_user_level_club_ids, ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"))
        self.assertEqual(diagnostic.right.ambiguous_abilities, 0)
        self.assertEqual(diagnostic.right.scenario_required_abilities, 1)
        self.assertEqual(diagnostic.right.unsupported_abilities, 1)

    def test_rendered_diagnostic_has_no_score_or_weight(self):
        rendered = render_bag_comparison(self.comparison())
        self.assertIn("Confidence diagnostic (objective facts; no score)", rendered)
        self.assertIn("Simulated abilities: 5/8", rendered)
        self.assertIn("Simulated abilities: 7/9", rendered)
        self.assertNotIn("Confidence score", rendered)
        self.assertNotIn("confidence weight", rendered.casefold())


if __name__ == "__main__":
    unittest.main()
