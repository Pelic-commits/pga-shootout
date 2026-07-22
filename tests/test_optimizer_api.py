import unittest
from pathlib import Path

from pga_shootout.models import EvaluationMode
from pga_shootout.optimizer_api import BagCandidate, BagEvaluationRequest, BagEvaluator, RuleEngineBagEvaluator


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
        self.assertEqual(result.evaluation.result.final_stats.as_dict(), {"power": 20.0, "control": 10.0, "spin": 10.0})
        self.assertEqual(result.ability_impact, {"power": 8.0, "control": 4.0, "spin": 4.0})
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

        self.assertEqual(result.modifier_impact, {"loft_angle_degrees": 5.0})
        contribution = next(item for item in result.ability_contributions if item.ability_id == "high_flight__loft_angle_5")
        self.assertEqual(contribution.modification["loft_angle_degrees"], 5.0)


if __name__ == "__main__":
    unittest.main()
