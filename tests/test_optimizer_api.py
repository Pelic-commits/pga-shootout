import unittest
from pathlib import Path

from pga_shootout.models import EvaluationMode
from pga_shootout.optimizer_api import (
    BagCandidate,
    BagEvaluationRequest,
    BagEvaluator,
    ReadinessStatus,
    RuleEngineBagEvaluator,
    optimizer_readiness_checklist,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"


class OptimizerApiTests(unittest.TestCase):
    def candidate(self):
        club_ids = ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm")
        return BagCandidate("candidate", club_ids, {club_id: 12 for club_id in club_ids})

    def test_rule_engine_adapter_implements_the_optimizer_protocol(self):
        evaluator: BagEvaluator = RuleEngineBagEvaluator(CATALOG)
        result = evaluator.evaluate(BagEvaluationRequest(self.candidate(), 1, EvaluationMode.PARTIAL))

        self.assertEqual(result.evaluation.state.current_club_id, "divebomb")
        self.assertEqual(result.evaluation.result.final_stats.as_dict(), {"power": 24.0, "control": 14.0, "spin": 14.0})
        self.assertEqual(result.ability_impact, {"power": 12.0, "control": 8.0, "spin": 8.0})
        self.assertTrue(result.ability_contributions)
        self.assertTrue(result.evaluation.result.explain)
        self.assertTrue(result.evaluation.result.unresolved)
        contribution_total = {
            stat: sum(item.modification[stat] for item in result.ability_contributions)
            for stat in ("power", "control", "spin")
        }
        self.assertEqual(contribution_total, result.ability_impact)

    def test_candidate_accepts_real_per_club_levels(self):
        candidate = self.candidate()
        levels = dict(candidate.levels)
        levels["steadfast"] = 5
        result = RuleEngineBagEvaluator(CATALOG).evaluate(
            BagEvaluationRequest(BagCandidate(candidate.identifier, candidate.club_ids, levels), 1)
        )

        rarity = next(item for item in result.ability_contributions if item.ability_id == "steadfast__bag_rarity_boost")
        self.assertEqual(rarity.modification, {"power": 2.0, "control": 2.0, "spin": 2.0})

    def test_missing_level_and_position_are_rejected_before_evaluation(self):
        candidate = self.candidate()
        for request in (
            BagEvaluationRequest(BagCandidate("missing", candidate.club_ids, {}), 1),
            BagEvaluationRequest(candidate, 6),
        ):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    RuleEngineBagEvaluator(CATALOG).evaluate(request)

    def test_optimizer_result_exposes_static_modifiers_and_their_source(self):
        club_ids = ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm")
        candidate = BagCandidate("high-flight", club_ids, {club_id: 12 for club_id in club_ids})
        result = RuleEngineBagEvaluator(CATALOG).evaluate(BagEvaluationRequest(candidate, 1))

        self.assertEqual(
            result.modifier_impact,
            {
                "loft_angle_degrees": 5.0,
                "wind_resistance_percent": 75.0,
                "bounce_reduction_percent": 40.0,
            },
        )
        contribution = next(item for item in result.ability_contributions if item.ability_id == "high_flight__loft_angle_5")
        self.assertEqual(contribution.modification["loft_angle_degrees"], 5.0)
        bounce = next(
            item for item in result.ability_contributions
            if item.ability_id == "maelstrom__bag_bounce_reduction"
        )
        self.assertEqual(bounce.modification["bounce_reduction_percent"], 20.0)
        wind = next(
            item for item in result.ability_contributions
            if item.ability_id == "high_flight__wind_resist_75"
        )
        self.assertEqual(wind.modification["wind_resistance_percent"], 75.0)

    def test_readiness_is_an_objective_eight_item_checklist(self):
        checklist = {item.identifier: item.status for item in optimizer_readiness_checklist()}
        self.assertEqual(
            checklist,
            {
                "separate_metrics": ReadinessStatus.READY,
                "ability_contributions": ReadinessStatus.READY,
                "normalization": ReadinessStatus.MISSING,
                "configurable_weights": ReadinessStatus.PARTIAL,
                "objective_profiles": ReadinessStatus.PARTIAL,
                "multi_club_aggregation": ReadinessStatus.PARTIAL,
                "ranking": ReadinessStatus.MISSING,
                "inventory_constraints": ReadinessStatus.PARTIAL,
            },
        )


if __name__ == "__main__":
    unittest.main()
