import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pga_shootout.cli import main
from pga_shootout.models import EvaluationMode
from pga_shootout.optimizer_api import BagEvaluator, RuleEngineBagEvaluator
from pga_shootout.placement_recommendation import (
    PlacementCandidateGenerator,
    PlacementRecommendationRequest,
    PlacementRecommendationService,
)
from pga_shootout.recommendation import RecommendationStatus


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "recommend_placement_cyclotron.txt"


class CountingEvaluator:
    def __init__(self, delegate: BagEvaluator):
        self.delegate = delegate
        self.calls = []

    def evaluate(self, request):
        self.calls.append((request.candidate.identifier, request.current_position))
        return self.delegate.evaluate(request)


class PlacementRecommendationTests(unittest.TestCase):
    @staticmethod
    def request(incoming="cyclotron", level=12):
        return PlacementRecommendationRequest(
            "par3_divebomb",
            incoming,
            level,
            EvaluationMode.PARTIAL,
        )

    def analyze(self, incoming="cyclotron"):
        return PlacementRecommendationService(user_dir=USER_DIR, catalog_path=CATALOG).analyze(
            self.request(incoming)
        )

    def test_generator_creates_exactly_the_five_same_position_replacements(self):
        generated = PlacementCandidateGenerator(user_dir=USER_DIR).generate(self.request())

        self.assertEqual(len(generated), 5)
        self.assertEqual([item.current_position for item in generated], [1, 2, 3, 4, 5])
        self.assertEqual(
            [item.outgoing_club_id for item in generated],
            ["divebomb", "jumpstart", "steadfast", "ember", "sunstorm"],
        )
        self.assertEqual({item.incoming_club_id for item in generated}, {"cyclotron"})

    def test_placement_creating_a_duplicate_is_preserved_as_excluded(self):
        request = PlacementRecommendationRequest(
            "par3_high_flight",
            "cyclotron",
            12,
            EvaluationMode.PARTIAL,
        )
        result = PlacementRecommendationService(user_dir=USER_DIR, catalog_path=CATALOG).analyze(request)

        self.assertEqual(len(result.candidates), 5)
        self.assertTrue(all(item.status is RecommendationStatus.EXCLUDED for item in result.candidates))
        self.assertTrue(
            all(item.exclusion_reasons for item in result.candidates)
        )

    def test_every_candidate_evaluates_five_positions_and_baseline_is_cached(self):
        evaluator = CountingEvaluator(RuleEngineBagEvaluator(CATALOG))
        service = PlacementRecommendationService(
            user_dir=USER_DIR,
            catalog_path=CATALOG,
            evaluator=evaluator,
        )
        result = service.analyze(self.request())

        self.assertEqual([len(item.positions) for item in result.candidates], [5, 5, 5, 5, 5])
        baseline_calls = [item for item in evaluator.calls if item[0].endswith(":baseline")]
        candidate_calls = [item for item in evaluator.calls if not item[0].endswith(":baseline")]
        self.assertEqual(baseline_calls, [("par3_divebomb:baseline", position) for position in range(1, 6)])
        self.assertEqual(len(candidate_calls), 25)
        self.assertEqual(service.matrix_evaluator.cached_baseline_evaluations, 5)

    def test_replacing_jumpstart_changes_divebomb_on_another_position(self):
        result = self.analyze()
        placement = next(item for item in result.candidates if item.replacement.position == 2)
        divebomb = next(item for item in placement.positions if item.position == 1)
        deltas = {item.identifier: item.delta for item in divebomb.metrics if item.delta}

        self.assertEqual(
            deltas,
            {"power": -4.0, "spin": 6.0, "bounce_reduction_percent": 20.0},
        )

    def test_adjacency_change_is_visible_on_an_unchanged_club(self):
        with tempfile.TemporaryDirectory() as directory:
            user_dir = Path(directory) / "user"
            shutil.copytree(USER_DIR, user_dir)
            bags_path = user_dir / "bags.json"
            data = json.loads(bags_path.read_text(encoding="utf-8"))
            data["bags"].append(
                {
                    "id": "willoughsby_fixture",
                    "name": "Willoughsby fixture",
                    "status": "user_observed",
                    "club_ids": ["homestead", "commonlaw", "high_flight", "sandsend", "steadfast"],
                    "notes": [],
                }
            )
            bags_path.write_text(json.dumps(data), encoding="utf-8")
            result = PlacementRecommendationService(user_dir=user_dir, catalog_path=CATALOG).analyze(
                PlacementRecommendationRequest(
                    "willoughsby_fixture",
                    "kinship",
                    12,
                    EvaluationMode.PARTIAL,
                )
            )

        placement = next(item for item in result.candidates if item.replacement.position == 3)
        commonlaw = next(item for item in placement.positions if item.position == 2)
        power = next(item for item in commonlaw.metrics if item.identifier == "power")
        self.assertGreater(power.delta, 0)
        self.assertEqual(commonlaw.candidate_club_id, "commonlaw")

    def test_bag_wide_bonus_changes_other_positions(self):
        result = self.analyze("rook")
        placement = next(item for item in result.candidates if item.replacement.position == 2)
        steadfast = next(item for item in placement.positions if item.position == 3)
        wind = next(item for item in steadfast.metrics if item.identifier == "wind_resistance_percent")

        self.assertEqual(wind.delta, 20.0)
        self.assertEqual(steadfast.candidate_club_id, "steadfast")

    def test_matrix_classifies_pareto_and_tradeoff_placements(self):
        result = self.analyze()
        statuses = {item.replacement.position: item.status for item in result.candidates}

        self.assertEqual(statuses[1], RecommendationStatus.PARETO)
        self.assertEqual(statuses[2], RecommendationStatus.TRADEOFF)
        self.assertIn(RecommendationStatus.TRADEOFF, statuses.values())

    def test_declared_indispensable_ability_prevents_pareto_qualification(self):
        result = PlacementRecommendationService(
            user_dir=USER_DIR,
            catalog_path=CATALOG,
            indispensable_ability_ids=frozenset({"divebomb__chains_into_putters"}),
        ).analyze(self.request())
        first = next(item for item in result.candidates if item.replacement.position == 1)

        self.assertEqual(first.status, RecommendationStatus.EXCLUDED)
        self.assertTrue(any("removes indispensable" in item for item in first.exclusion_reasons))

    def test_new_unresolved_ability_excludes_and_is_propagated(self):
        result = self.analyze("neon_impulse")

        self.assertTrue(all(item.status is RecommendationStatus.EXCLUDED for item in result.candidates))
        self.assertTrue(
            all("neon_impulse__power_shot" in item.new_unresolved_ability_ids for item in result.candidates)
        )
        self.assertTrue(
            all(any("unsupported:power_shot" in reason for reason in item.new_unresolved_messages) for item in result.candidates)
        )

    def test_scenario_and_actual_level_modes_are_explicit(self):
        scenario = self.analyze()
        actual = PlacementRecommendationService(user_dir=USER_DIR, catalog_path=CATALOG).analyze(
            self.request(level=None)
        )

        self.assertEqual(scenario.request.level_mode, "scenario")
        self.assertTrue(any("Explicit level scenario 12" in warning for warning in scenario.candidates[0].warnings))
        self.assertEqual(actual.request.level_mode, "actual")
        self.assertTrue(all(item.status is RecommendationStatus.EXCLUDED for item in actual.candidates))
        self.assertTrue(
            all(any("No recorded user level" in reason for reason in item.exclusion_reasons) for item in actual.candidates)
        )

    def test_cli_text_and_json_come_from_the_same_five_candidate_result(self):
        common = [
            "recommend-placement",
            "par3_divebomb",
            "cyclotron",
            "--scenario-level",
            "12",
            "--partial",
            "--user-dir",
            str(USER_DIR),
            "--catalog",
            str(CATALOG),
        ]
        text_output = io.StringIO()
        with contextlib.redirect_stdout(text_output):
            text_exit = main(common)
        json_output = io.StringIO()
        with contextlib.redirect_stdout(json_output):
            json_exit = main([*common, "--json"])
        payload = json.loads(json_output.getvalue())

        self.assertEqual((text_exit, json_exit), (0, 0))
        self.assertIn("Generated placements: 5", text_output.getvalue())
        self.assertIn("Position 2 — Jumpstart -> Cyclotron", text_output.getvalue())
        self.assertEqual(payload["candidate_count"], 5)
        self.assertEqual(len(payload["candidates"]), 5)
        self.assertTrue(all(len(item["position_evaluations"]) == 5 for item in payload["candidates"]))
        self.assertIsNone(payload["aggregate_score"])
        self.assertTrue(all(item["aggregate_score"] is None for item in payload["candidates"]))

    def test_legacy_level_alias_remains_a_scenario_level(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "recommend-placement",
                    "par3_divebomb",
                    "cyclotron",
                    "--level",
                    "12",
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
        self.assertEqual(payload["level_mode"], "scenario")
        self.assertEqual(payload["scenario_level"], 12)

    def test_cyclotron_placement_output_matches_golden(self):
        result = self.analyze()
        lines = []
        for candidate in result.candidates:
            replacement = candidate.replacement
            lines.append(
                f"placement {replacement.position} {replacement.outgoing_club_id}->{replacement.incoming_club_id} "
                f"{candidate.status.value}"
            )
            for position in candidate.positions:
                deltas = [
                    f"{metric.identifier}={metric.delta:+g}"
                    for metric in position.metrics
                    if metric.delta
                ]
                if deltas:
                    lines.append(
                        f"  evaluated {position.position} {position.candidate_club_id}: " + ", ".join(deltas)
                    )
        self.assertEqual(
            "\n".join(lines) + "\n",
            GOLDEN.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
