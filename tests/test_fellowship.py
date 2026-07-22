import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import _semantic_program, build_game_state
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "fellowship_explain.txt"


class FellowshipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    def state(self, club_ids, level, current_club_id):
        bag = SavedBag("fellowship", "Fellowship", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state):
        return next(ability.effects[0] for ability in state.bag.get("steward").club.abilities if ability.text == "fellowship")

    def evaluate(self, club_ids, level, current_club_id):
        state = self.state(club_ids, level, current_club_id)
        return RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)

    def test_configuration_uses_only_existing_primitives(self):
        entry = self.semantic["entries"]["label:fellowship"]
        program = _semantic_program(entry, self.semantic["patterns"])
        self.assertEqual(
            tuple(node["operation"] for node in program["nodes"]),
            ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "FOR_EACH", "MATCH_BRAND", "FOR_EACH"),
        )

    def test_non_matching_adjacent_club_receives_base_bonus_once(self):
        result = self.evaluate(("divebomb", "steward", "sunstorm"), 5, "divebomb")
        self.assertEqual(result.final_stats.power, result.base_stats.power + 1)

    def test_willoughsby_adjacent_club_receives_double_bonus(self):
        result = self.evaluate(("steadfast", "steward", "divebomb"), 5, "steadfast")
        self.assertEqual(result.final_stats.power, result.base_stats.power + 2)

    def test_only_immediate_neighbors_receive_the_bonus(self):
        clubs = ("steadfast", "divebomb", "steward", "sunstorm", "groundskeep")
        for current_id, expected in (("steadfast", 0), ("divebomb", 1), ("steward", 0), ("sunstorm", 1), ("groundskeep", 0)):
            with self.subTest(current=current_id):
                result = self.evaluate(clubs, 5, current_id)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected)

    def test_edge_source_has_only_one_target(self):
        result = self.evaluate(("steward", "steadfast", "divebomb"), 5, "steadfast")
        self.assertEqual(result.final_stats.power, result.base_stats.power + 2)
        selection = next(entry for entry in result.explain if entry.mechanism == "SELECT_ADJACENT")
        self.assertIsNone(selection.outputs["left"])
        self.assertEqual(selection.outputs["right"], "Steadfast")

    def test_official_values_vary_by_level(self):
        for level, value in ((5, 1), (7, 2), (11, 3), (12, 3)):
            with self.subTest(level=level):
                result = self.evaluate(("steadfast", "steward"), level, "steadfast")
                self.assertEqual(result.final_stats.power, result.base_stats.power + 2 * value)

    def test_absent_level_value_creates_no_effect(self):
        state = self.state(("divebomb", "steward"), 1, "divebomb")
        self.assertNotIn("fellowship", {ability.text for ability in state.bag.get("steward").club.abilities})

    def test_strict_partial_and_explain_are_complete(self):
        state = self.state(("steadfast", "steward", "divebomb"), 12, "steadfast")
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=mode)
                self.assertTrue(result.complete)
                rendered = render_explain_entries(result.explain)
                self.assertIn("Detail: POWER += 3", rendered)
                self.assertEqual(rendered.count("Detail: POWER += 3"), 2)
                self.assertIn('Inputs: {"brand": "willoughsby", "candidates": ["Steadfast", "Divebomb"], "source": "Steward"}', rendered)
                self.assertIn("Detail: matched 1 club(s) against brand willoughsby", rendered)

    def test_full_explain_matches_the_golden_file(self):
        state = self.state(("steadfast", "steward", "divebomb"), 12, "steadfast")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        self.assertEqual(render_explain_entries(result.explain) + "\n", GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
