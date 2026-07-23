import copy
import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import build_game_state, evaluate_saved_bag, load_saved_bag, render_bag_evaluation
from pga_shootout.models import EvaluationMode, Stats


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG_PATH = ROOT / "data" / "normalized" / "clubs_official.json"


class BagEvaluationEndToEndTests(unittest.TestCase):
    def test_loads_saved_bag_and_builds_game_state_from_official_stats(self):
        bag = load_saved_bag(USER_DIR, "par3_divebomb")
        state = build_game_state(bag, CATALOG_PATH, 12)

        self.assertEqual(bag.club_ids, ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"))
        self.assertEqual(state.current_club_id, "divebomb")
        self.assertEqual(tuple(entry.club.identifier for entry in state.bag.entries), bag.club_ids)
        self.assertEqual(state.current_entry.club.stats_at(12), Stats(12, 6, 6))

    def test_partial_mode_returns_result_and_explain_for_unsupported_abilities(self):
        evaluation = evaluate_saved_bag(
            "par3_divebomb", level=12, mode=EvaluationMode.PARTIAL, user_dir=USER_DIR, catalog_path=CATALOG_PATH
        )

        self.assertFalse(evaluation.strict_failed)
        self.assertFalse(evaluation.result.complete)
        self.assertGreater(len(evaluation.result.explain), 0)
        self.assertGreater(len(evaluation.result.unresolved), 0)
        rendered = render_bag_evaluation(evaluation)
        self.assertIn("Base stats", rendered)
        self.assertIn("Status: UNSUPPORTED", rendered)
        self.assertIn("Partial mode: SUCCESS", rendered)

    def test_strict_mode_stops_at_first_missing_mechanic_with_explain(self):
        evaluation = evaluate_saved_bag(
            "par3_divebomb", level=12, mode=EvaluationMode.STRICT, user_dir=USER_DIR, catalog_path=CATALOG_PATH
        )

        self.assertTrue(evaluation.strict_failed)
        self.assertFalse(evaluation.result.complete)
        self.assertEqual(len(evaluation.result.unresolved), 1)
        self.assertEqual(len(evaluation.result.explain), 5)
        self.assertEqual(len(evaluation.result.scheduled_effects), 1)
        self.assertEqual(evaluation.result.explain[2].mechanism, "SCHEDULE_EFFECT")
        self.assertIn("Strict mode: FAILED", render_bag_evaluation(evaluation))

    def test_existing_two_mechanics_flow_through_registry_without_club_logic(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        configured = copy.deepcopy(catalog)
        divebomb = configured["clubs"]["divebomb"]
        jumpstart = configured["clubs"]["jumpstart"]
        divebomb["abilities"][0]["mechanism"] = "add_all_stats"
        divebomb["abilities"][0]["effect_parameters"] = {"amount": 2}
        jumpstart["abilities"][0]["mechanism"] = "add_stat"
        jumpstart["abilities"][0]["effect_parameters"] = {"stat": "power", "amount": 3}
        # Keep only these two declarative effects so the complete result is deterministic.
        for club_id in ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"):
            configured["clubs"][club_id]["abilities"] = [
                ability for ability in configured["clubs"][club_id]["abilities"] if ability.get("mechanism")
            ]

        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.json"
            catalog_path.write_text(json.dumps(configured), encoding="utf-8")
            evaluation = evaluate_saved_bag(
                "par3_divebomb",
                level=12,
                mode=EvaluationMode.STRICT,
                user_dir=USER_DIR,
                catalog_path=catalog_path,
            )

        self.assertFalse(evaluation.strict_failed)
        self.assertTrue(evaluation.result.complete)
        self.assertEqual(evaluation.result.final_stats, Stats(17, 8, 8))
        self.assertEqual([entry.mechanism for entry in evaluation.result.explain], ["add_all_stats", "add_stat"])
        self.assertTrue(all(entry.applied for entry in evaluation.result.explain))


if __name__ == "__main__":
    unittest.main()
