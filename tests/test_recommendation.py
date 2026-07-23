import contextlib
import io
import json
import unittest
from pathlib import Path

from pga_shootout.cli import main
from pga_shootout.models import EvaluationMode
from pga_shootout.optimizer_api import RuleEngineBagEvaluator
from pga_shootout.recommendation import (
    CandidateComparator,
    CandidateEvaluator,
    CandidateValidator,
    QualificationFilter,
    RecommendationRequest,
    RecommendationService,
    RecommendationStatus,
)


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"


class RecommendationVerticalSliceTests(unittest.TestCase):
    @staticmethod
    def request(*, incoming="cyclotron", position=None):
        return RecommendationRequest(
            bag_id="par3_divebomb",
            outgoing_club_id="jumpstart",
            incoming_club_id=incoming,
            level=12,
            mode=EvaluationMode.PARTIAL,
            current_position=position,
        )

    def test_explicit_replacement_flows_through_all_components_as_pareto_improvement(self):
        request = self.request()
        validation = CandidateValidator(user_dir=USER_DIR, catalog_path=CATALOG).validate(request)
        self.assertTrue(validation.valid)
        self.assertEqual(validation.replacement.position, 2)

        evaluation = CandidateEvaluator(RuleEngineBagEvaluator(CATALOG)).evaluate(validation)
        comparison = CandidateComparator().compare(evaluation)
        result = QualificationFilter().qualify(comparison)

        self.assertEqual(result.status, RecommendationStatus.PARETO)
        self.assertEqual(
            {item.identifier: item.delta for item in result.gains},
            {"power": 3.0, "control": 2.0, "spin": 8.0},
        )
        self.assertEqual(result.losses, ())
        self.assertEqual(
            {item.ability_id for item in result.gained_abilities},
            {"cyclotron__spin_boost", "cyclotron__bounce_reduction_boost"},
        )
        self.assertEqual(
            {item.ability_id for item in result.lost_abilities},
            {"jumpstart__power_boost"},
        )
        self.assertEqual(result.new_unresolved_ability_ids, ())

    def test_explicit_position_exposes_a_tradeoff(self):
        result = RecommendationService(user_dir=USER_DIR, catalog_path=CATALOG).analyze(
            self.request(position=1)
        )

        self.assertEqual(result.status, RecommendationStatus.TRADEOFF)
        self.assertEqual(
            {item.identifier: item.delta for item in result.gains},
            {"spin": 6.0, "bounce_reduction_percent": 20.0},
        )
        self.assertEqual(
            {item.identifier: item.delta for item in result.losses},
            {"power": -4.0},
        )

    def test_candidate_with_new_unresolved_ability_is_excluded(self):
        result = RecommendationService(user_dir=USER_DIR, catalog_path=CATALOG).analyze(
            self.request(incoming="neon_impulse")
        )

        self.assertEqual(result.status, RecommendationStatus.EXCLUDED)
        self.assertEqual(result.new_unresolved_ability_ids, ("neon_impulse__power_shot",))
        self.assertTrue(any("unsupported:power_shot" in item for item in result.new_unresolved_messages))
        self.assertTrue(any("introduces unresolved" in item for item in result.exclusion_reasons))

    def test_invalid_unowned_candidate_is_returned_as_an_excluded_result(self):
        result = RecommendationService(user_dir=USER_DIR, catalog_path=CATALOG).analyze(
            self.request(incoming="meteor")
        )

        self.assertEqual(result.status, RecommendationStatus.EXCLUDED)
        self.assertTrue(any("not confirmed" in item for item in result.exclusion_reasons))
        self.assertEqual(result.metrics, ())

    def test_cli_text_output_is_readable_without_full_explain(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "recommend-replacement",
                    "par3_divebomb",
                    "jumpstart",
                    "cyclotron",
                    "--level",
                    "12",
                    "--partial",
                    "--user-dir",
                    str(USER_DIR),
                    "--catalog",
                    str(CATALOG),
                ]
            )

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Proposed replacement: Jumpstart -> Cyclotron", rendered)
        self.assertIn("Status: PARETO", rendered)
        self.assertIn("Power: +3 points", rendered)
        self.assertIn("Gained abilities", rendered)
        self.assertIn("Lost abilities", rendered)
        self.assertIn("New unresolved abilities", rendered)
        self.assertIn("No aggregate score was computed", rendered)

    def test_cli_json_output_uses_the_same_structured_result(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "recommend-replacement",
                    "par3_divebomb",
                    "jumpstart",
                    "cyclotron",
                    "--level",
                    "12",
                    "--position",
                    "1",
                    "--partial",
                    "--json",
                    "--user-dir",
                    str(USER_DIR),
                    "--catalog",
                    str(CATALOG),
                ]
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["status"], "tradeoff")
        self.assertEqual(payload["replacement"]["incoming_club_id"], "cyclotron")
        self.assertEqual(payload["aggregate_score"], None)
        self.assertEqual(
            {item["identifier"]: item["delta"] for item in payload["losses"]},
            {"power": -4.0},
        )


if __name__ == "__main__":
    unittest.main()
