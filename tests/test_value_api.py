import unittest
from pathlib import Path

from pga_shootout.bag_comparison import compare_saved_bags, render_bag_comparison
from pga_shootout.models import EvaluationMode
from pga_shootout.value_api import MetricKind, MetricWeightProvider, MetricWeightingRequest, WeightingContext


ROOT = Path(__file__).resolve().parents[1]


class FixtureWeightProvider:
    def weights_for(self, request: MetricWeightingRequest):
        return {metric.definition.identifier: 1.0 for metric in request.metrics}


class ValueApiTests(unittest.TestCase):
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

    def test_compare_bags_exposes_every_metric_independently(self):
        metrics = {metric.definition.identifier: metric for metric in self.comparison().metrics}
        self.assertEqual(
            set(metrics),
            {"power", "control", "spin", "loft_angle_degrees", "bounce_reduction_percent"},
        )
        self.assertEqual(metrics["power"].definition.kind, MetricKind.STAT)
        self.assertEqual(metrics["loft_angle_degrees"].definition.unit, "degrees")
        self.assertEqual(metrics["loft_angle_degrees"].right_final, 5.0)
        self.assertEqual(metrics["loft_angle_degrees"].difference_right_minus_left, 5.0)
        self.assertEqual(metrics["bounce_reduction_percent"].definition.unit, "percent")
        self.assertEqual(metrics["bounce_reduction_percent"].right_final, 20.0)
        self.assertIn("Launch angle adjustment (degrees)", render_bag_comparison(self.comparison()))

    def test_every_loaded_ability_has_a_stable_contribution_identity(self):
        comparison = self.comparison()
        for side in (comparison.left, comparison.right):
            self.assertTrue(side.ability_contributions)
            self.assertTrue(all(item.source_club_id and item.ability_id and item.source for item in side.ability_contributions))

    def test_weighting_contract_accepts_context_without_computing_a_score(self):
        comparison = self.comparison()
        request = MetricWeightingRequest(
            WeightingContext(
                user_profile={"profile_id": "pierre"},
                course_type="par3",
                objective="precision",
            ),
            comparison.metrics,
        )
        provider: MetricWeightProvider = FixtureWeightProvider()
        weights = provider.weights_for(request)

        self.assertEqual(set(weights), {metric.definition.identifier for metric in comparison.metrics})
        self.assertFalse(hasattr(request, "score"))
        self.assertFalse(hasattr(comparison, "score"))


if __name__ == "__main__":
    unittest.main()
