import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import build_game_state
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import EvaluationError, RuleEngine
from pga_shootout.models import Bag, BagEntry, Club, Condition, Effect, EvaluationMode, GameState, Stats
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"


class BrandLoyaltyPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))
        cls.program = semantic["entries"]["label:brand_loyalty_x"]["program"]

    def club(self, identifier: str, brand: str) -> Club:
        return Club(identifier, identifier.title(), brand, "test", {1: Stats(10, 5, 3), 2: Stats(10, 5, 3)})

    def evaluate(self, brands: tuple[str, ...], source_index: int, amount: float, mode=EvaluationMode.STRICT):
        clubs = tuple(self.club(f"club_{index}", brand) for index, brand in enumerate(brands))
        state = GameState(
            Bag(tuple(BagEntry(club, 1) for club in clubs)),
            current_club_id=clubs[source_index].identifier,
        )
        effect = Effect(
            "dsl_pipeline",
            {
                "program": self.program,
                "source_club_id": clubs[source_index].identifier,
                "level_value": amount,
            },
            Condition("always"),
            "declarative ability",
        )
        return RuleEngine().evaluate(state, (effect,), mode=mode)

    def test_registers_exactly_the_seven_required_primitives(self):
        self.assertEqual(
            default_dsl_registry().names,
            ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ADJACENT", "MATCH_BRAND", "COUNT", "SCALE", "ADD_STAT"),
        )

    def test_no_matching_neighbor_adds_nothing(self):
        result = self.evaluate(("red", "blue", "green"), 1, 3)
        self.assertEqual(result.final_stats.power, 10)
        self.assertIn("counted 0 item(s)", result.explain[4].message)

    def test_one_matching_neighbor(self):
        result = self.evaluate(("blue", "blue", "green"), 1, 3)
        self.assertEqual(result.final_stats.power, 13)

    def test_two_matching_neighbors(self):
        result = self.evaluate(("blue", "blue", "blue"), 1, 3)
        self.assertEqual(result.final_stats.power, 16)
        self.assertIn("counted 2 item(s)", result.explain[4].message)

    def test_first_position_has_only_right_neighbor(self):
        result = self.evaluate(("blue", "blue", "blue"), 0, 2)
        self.assertEqual(result.final_stats.power, 12)
        self.assertIn("['club_1']", result.explain[2].message)

    def test_last_position_has_only_left_neighbor(self):
        result = self.evaluate(("blue", "blue", "blue"), 2, 2)
        self.assertEqual(result.final_stats.power, 12)
        self.assertIn("['club_1']", result.explain[2].message)

    def test_middle_position_has_two_neighbors(self):
        result = self.evaluate(("blue", "blue", "blue"), 1, 2)
        self.assertEqual(result.final_stats.power, 14)
        self.assertIn("['club_0', 'club_2']", result.explain[2].message)

    def test_wrong_brand_is_filtered_out(self):
        result = self.evaluate(("red", "blue", "red"), 1, 4)
        self.assertEqual(result.final_stats.power, 10)
        self.assertIn("matched brand blue: []", result.explain[3].message)

    def test_zero_level_bonus_is_a_valid_applied_effect(self):
        result = self.evaluate(("blue", "blue"), 0, 0)
        self.assertTrue(result.complete)
        self.assertEqual(result.final_stats.power, 10)
        self.assertTrue(result.explain[6].applied)
        self.assertIn("added 0 to power", result.explain[6].message)

    def test_official_level_values_are_read_from_data(self):
        bag = SavedBag("test", "Test", "active", ("cloudcatcher", "rook"), ())
        expected = {7: 8, 12: 12}
        for level, expected_power in expected.items():
            with self.subTest(level=level):
                state = build_game_state(bag, NORMALIZED / "clubs_official.json", level, "cloudcatcher")
                effect = state.current_entry.club.abilities[-1].effects[0]
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.mechanism, "dsl_pipeline")
                self.assertEqual(result.final_stats.power, expected_power)

    def test_explain_contains_every_pipeline_step_in_order(self):
        result = self.evaluate(("blue", "blue", "blue"), 1, 2)
        self.assertEqual(
            [entry.mechanism for entry in result.explain],
            [
                "SELECT_SELF",
                "READ_LEVEL_VALUE",
                "SELECT_ADJACENT",
                "MATCH_BRAND",
                "COUNT",
                "SCALE",
                "ADD_STAT",
                "dsl_pipeline",
            ],
        )
        self.assertEqual(result.explain[6].before["power"], 10)
        self.assertEqual(result.explain[6].modification["power"], 4)
        self.assertEqual(result.explain[6].after["power"], 14)

    def test_complete_pipeline_succeeds_in_strict_and_partial_modes(self):
        strict = self.evaluate(("blue", "blue"), 0, 2, EvaluationMode.STRICT)
        partial = self.evaluate(("blue", "blue"), 0, 2, EvaluationMode.PARTIAL)
        self.assertTrue(strict.complete)
        self.assertTrue(partial.complete)
        self.assertEqual(strict.final_stats, partial.final_stats)

    def test_unknown_primitive_obeys_strict_and_partial_modes(self):
        broken_program = {"nodes": [{"id": "missing", "operation": "NOT_IMPLEMENTED"}]}
        club = self.club("source", "blue")
        state = GameState(Bag((BagEntry(club, 1),)), "source")
        effect = Effect("dsl_pipeline", {"program": broken_program}, source="broken declaration")

        with self.assertRaises(EvaluationError):
            RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
        partial = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.PARTIAL)
        self.assertFalse(partial.complete)
        self.assertIn("Unknown DSL primitive", partial.unresolved[0])


if __name__ == "__main__":
    unittest.main()
