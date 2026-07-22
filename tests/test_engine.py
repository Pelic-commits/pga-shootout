import unittest

from pga_shootout.engine import EvaluationError, RuleEngine
from pga_shootout.models import Condition, Effect, EvaluationMode, Stats
from tests.helpers import make_game_state


class RuleEngineTests(unittest.TestCase):
    def setUp(self):
        self.game_state = make_game_state()

    def test_stat_and_all_stat_modifications_are_numeric(self):
        effects = [
            Effect("add_stat", {"stat": "power", "amount": 5}, source="test power"),
            Effect("add_all_stats", {"amount": 2}, source="test all"),
        ]
        result = RuleEngine().evaluate(self.game_state, effects)
        self.assertEqual(result.base_stats, Stats(10, 20, 30))
        self.assertEqual(result.final_stats, Stats(17, 22, 32))
        self.assertTrue(result.complete)

    def test_explain_records_before_delta_after_and_source(self):
        effect = Effect("add_stat", {"stat": "control", "amount": 3}, source="fixture ability")
        entry = RuleEngine().evaluate(self.game_state, [effect]).explain[0]
        self.assertEqual(entry.source, "fixture ability")
        self.assertTrue(entry.applied)
        self.assertEqual(entry.before, {"power": 10, "control": 20, "spin": 30})
        self.assertEqual(entry.modification, {"power": 0, "control": 3, "spin": 0})
        self.assertEqual(entry.after, {"power": 10, "control": 23, "spin": 30})

    def test_effect_is_ignored_when_condition_is_not_satisfied(self):
        effect = Effect(
            "add_stat",
            {"stat": "spin", "amount": 99},
            condition=Condition("state_equals", {"field": "terrain", "value": "rough"}),
            source="conditional fixture",
        )
        result = RuleEngine().evaluate(self.game_state, [effect])
        self.assertEqual(result.final_stats, result.base_stats)
        self.assertFalse(result.explain[0].applied)
        self.assertEqual(result.explain[0].message, "condition not satisfied")
        self.assertEqual(result.explain[0].modification, {"power": 0, "control": 0, "spin": 0})

    def test_strict_mode_fails_on_unknown_mechanism(self):
        with self.assertRaisesRegex(EvaluationError, "UnknownMechanismError"):
            RuleEngine().evaluate(self.game_state, [Effect("not_registered", source="fixture")])

    def test_partial_mode_reports_unknown_mechanism(self):
        result = RuleEngine().evaluate(
            self.game_state,
            [Effect("not_registered", source="fixture")],
            mode=EvaluationMode.PARTIAL,
        )
        self.assertEqual(result.final_stats, result.base_stats)
        self.assertFalse(result.complete)
        self.assertIn("UnknownMechanismError", result.unresolved[0])
        self.assertFalse(result.explain[0].applied)


if __name__ == "__main__":
    unittest.main()
