import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import _abilities_at_level, build_game_state
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import EvaluationError, RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import Bag, BagEntry, Club, Condition, Effect, EvaluationMode, GameState, Stats
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
GOLDEN = ROOT / "tests" / "golden" / "brand_loyalty_explain.txt"


class BrandLoyaltyPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))
        cls.program = semantic["entries"]["label:brand_loyalty_x"]["program"]

    def club(self, identifier: str, brand: str, name: str | None = None) -> Club:
        return Club(identifier, name or identifier.title(), brand, "test", {1: Stats(10, 5, 3), 2: Stats(10, 5, 3)})

    def evaluate(self, brands: tuple[str, ...], source_index: int, amount: float, mode=EvaluationMode.STRICT, level=1):
        clubs = tuple(self.club(f"club_{index}", brand) for index, brand in enumerate(brands))
        return self.evaluate_clubs(clubs, source_index, amount, mode, level)

    def evaluate_clubs(self, clubs, source_index: int, amount: float, mode=EvaluationMode.STRICT, level=1):
        state = GameState(
            Bag(tuple(BagEntry(club, 1) for club in clubs)),
            current_club_id=clubs[source_index].identifier,
        )
        effect = Effect(
            "dsl_pipeline",
            {
                "program": self.program,
                "source_club_id": clubs[source_index].identifier,
                "ability_level": level,
                "level_value": amount,
            },
            Condition("always"),
            "declarative ability",
        )
        return RuleEngine().evaluate(state, (effect,), mode=mode)

    def test_registry_contains_the_reference_and_reusable_type_filter_primitives(self):
        self.assertEqual(
            default_dsl_registry().names,
            (
                "SELECT_SELF",
                "READ_LEVEL_VALUE",
                "SELECT_ALL",
                "SELECT_ADJACENT",
                "MATCH_BRAND",
                "MATCH_TYPE",
                "MATCH_RARITY",
                "COUNT",
                "EXISTS",
                "SCALE",
                "FOR_EACH",
                "UNLESS",
                "ADD_STAT",
                "ADD_MODIFIER",
            ),
        )

    def test_no_matching_neighbor_adds_nothing(self):
        result = self.evaluate(("red", "blue", "green"), 1, 3)
        self.assertEqual(result.final_stats.power, 10)
        self.assertIn("counted 0 item(s)", result.explain[4].message)

    def test_one_matching_neighbor(self):
        result = self.evaluate(("blue", "blue", "green"), 1, 3)
        self.assertEqual(result.final_stats.power, 13)

    def test_left_matching_neighbor_only(self):
        result = self.evaluate(("blue", "blue", "green"), 1, 3)
        self.assertEqual(result.final_stats.power, 13)
        self.assertEqual(result.explain[3].outputs["left"]["matches"], True)
        self.assertEqual(result.explain[3].outputs["right"]["matches"], False)

    def test_right_matching_neighbor_only(self):
        result = self.evaluate(("green", "blue", "blue"), 1, 3)
        self.assertEqual(result.final_stats.power, 13)
        self.assertEqual(result.explain[3].outputs["left"]["matches"], False)
        self.assertEqual(result.explain[3].outputs["right"]["matches"], True)

    def test_two_matching_neighbors(self):
        result = self.evaluate(("blue", "blue", "blue"), 1, 3)
        self.assertEqual(result.final_stats.power, 16)
        self.assertIn("counted 2 item(s)", result.explain[4].message)

    def test_first_position_has_only_right_neighbor(self):
        result = self.evaluate(("blue", "blue", "blue"), 0, 2)
        self.assertEqual(result.final_stats.power, 12)
        self.assertEqual(result.explain[2].outputs, {"left": None, "right": "Club_1"})

    def test_last_position_has_only_left_neighbor(self):
        result = self.evaluate(("blue", "blue", "blue"), 2, 2)
        self.assertEqual(result.final_stats.power, 12)
        self.assertEqual(result.explain[2].outputs, {"left": "Club_1", "right": None})

    def test_middle_position_has_two_neighbors(self):
        result = self.evaluate(("blue", "blue", "blue"), 1, 2)
        self.assertEqual(result.final_stats.power, 14)
        self.assertEqual(result.explain[2].outputs, {"left": "Club_0", "right": "Club_2"})

    def test_two_identical_neighbor_clubs_are_counted_as_two_instances(self):
        duplicate = self.club("duplicate", "blue", "Duplicate")
        source = self.club("source", "blue", "Source")
        result = self.evaluate_clubs((duplicate, source, duplicate), 1, 2)
        self.assertEqual(result.explain[4].outputs["count"], 2)
        self.assertEqual(result.final_stats.power, 14)

    def test_different_clubs_of_the_same_brand_are_both_counted(self):
        clubs = (
            self.club("left", "blue", "Left Model"),
            self.club("source", "blue", "Source Model"),
            self.club("right", "blue", "Right Model"),
        )
        result = self.evaluate_clubs(clubs, 1, 2)
        self.assertEqual(result.explain[4].outputs["count"], 2)
        self.assertEqual(result.final_stats.power, 14)

    def test_wrong_brand_is_filtered_out(self):
        result = self.evaluate(("red", "blue", "red"), 1, 4)
        self.assertEqual(result.final_stats.power, 10)
        self.assertIn("matched 0 club(s)", result.explain[3].message)

    def test_zero_level_bonus_is_a_valid_applied_effect(self):
        result = self.evaluate(("blue", "blue"), 0, 0)
        self.assertTrue(result.complete)
        self.assertEqual(result.final_stats.power, 10)
        self.assertTrue(result.explain[6].applied)
        self.assertEqual(result.explain[6].message, "POWER += 0")

    def test_official_level_values_are_read_from_data(self):
        bag = SavedBag("test", "Test", "active", ("cloudcatcher", "rook"), ())
        expected = {7: (1, 8), 11: (2, 11), 12: (2, 12), "Elite": (3, 16)}
        for level, (expected_value, expected_power) in expected.items():
            with self.subTest(level=level):
                state = build_game_state(bag, NORMALIZED / "clubs_official.json", level, "cloudcatcher")
                effect = state.current_entry.club.abilities[-1].effects[0]
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.mechanism, "dsl_pipeline")
                self.assertEqual(effect.parameters["level_value"], expected_value)
                self.assertEqual(result.explain[1].inputs["level"], level)
                self.assertEqual(result.final_stats.power, expected_power)

    def test_absent_official_value_does_not_create_an_effect(self):
        catalog = json.loads((NORMALIZED / "clubs_official.json").read_text(encoding="utf-8"))
        semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]
        abilities = _abilities_at_level(catalog["clubs"]["cloudcatcher"], 1, semantic)
        self.assertNotIn("brand_loyalty_x", {ability.text for ability in abilities})

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
        self.assertTrue(all(entry.inputs for entry in result.explain[:7]))
        self.assertTrue(all(entry.outputs for entry in result.explain[:7]))

    def test_explain_matches_the_reference_golden_file(self):
        clubs = (
            self.club("groundskeep", "willoughsby", "Groundskeep"),
            self.club("steadfast", "willoughsby", "Steadfast"),
            self.club("homestead", "willoughsby", "Homestead"),
        )
        result = self.evaluate_clubs(clubs, 1, 2, level=11)
        rendered = render_explain_entries(result.explain[:7]) + "\n"
        self.assertEqual(rendered, GOLDEN.read_text(encoding="utf-8"))

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
