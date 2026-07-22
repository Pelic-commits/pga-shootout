import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import build_game_state, load_saved_bag
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import EvaluationError, RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode, Stats
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "sunstorm_plasma_arc_explain.txt"


class PlasmaArcTests(unittest.TestCase):
    @staticmethod
    def effect(state):
        return next(
            ability.effects[0]
            for ability in state.bag.get("sunstorm").club.abilities
            if ability.text == "plasma_arc_x"
        )

    def test_reference_bags_apply_level_value_to_unique_farthest_club(self):
        for bag_id, base in (
            ("par3_divebomb", Stats(12, 6, 6)),
            ("par3_high_flight", Stats(14, 10, 8)),
        ):
            with self.subTest(bag_id=bag_id):
                bag = load_saved_bag(USER_DIR, bag_id)
                state = build_game_state(bag, CATALOG, 12, bag.club_ids[0])
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.base_stats, base)
                self.assertEqual(
                    result.final_stats,
                    Stats(base.power + 4, base.control + 4, base.spin + 4),
                )

    def test_official_values_at_multiple_levels(self):
        bag = load_saved_bag(USER_DIR, "par3_divebomb")
        for level, amount in ((5, 2), (8, 3), (12, 4)):
            with self.subTest(level=level):
                state = build_game_state(bag, CATALOG, level, "divebomb")
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
                base = result.base_stats
                self.assertEqual(result.final_stats, Stats(base.power + amount, base.control + amount, base.spin + amount))

    def test_farthest_selection_is_direction_independent(self):
        bag = SavedBag(
            "reverse",
            "Reverse",
            "fixture",
            ("sunstorm", "steadfast", "jumpstart", "divebomb", "high_flight"),
            (),
        )
        state = build_game_state(bag, CATALOG, 12, "high_flight")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        self.assertEqual(result.final_stats, Stats(18, 14, 12))

    def test_tied_farthest_target_is_never_guessed(self):
        bag = SavedBag(
            "tie",
            "Tie",
            "fixture",
            ("divebomb", "jumpstart", "sunstorm", "steadfast", "high_flight"),
            (),
        )
        state = build_game_state(bag, CATALOG, 12, "divebomb")
        effect = self.effect(state)
        partial = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.PARTIAL)
        self.assertEqual(partial.final_stats, partial.base_stats)
        self.assertFalse(partial.complete)
        self.assertIn("Farthest club is tied", partial.unresolved[0])
        with self.assertRaisesRegex(EvaluationError, "Farthest club is tied"):
            RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)

    def test_explain_matches_golden_file(self):
        bag = load_saved_bag(USER_DIR, "par3_divebomb")
        state = build_game_state(bag, CATALOG, 12, "divebomb")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        self.assertIn("SELECT_FARTHEST", default_dsl_registry().names)
        self.assertEqual(render_explain_entries(result.explain) + "\n", GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
