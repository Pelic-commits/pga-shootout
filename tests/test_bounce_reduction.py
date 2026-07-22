import unittest
from pathlib import Path

from pga_shootout.bag_comparison import _comparable_metrics, summarize_bag_evaluation
from pga_shootout.bag_evaluation import build_game_state, evaluate_bag
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "cloudcatcher_bounce_reduction_explain.txt"


class BounceReductionTests(unittest.TestCase):
    @staticmethod
    def bag(*club_ids):
        return SavedBag("bounce", "Bounce", "fixture", tuple(club_ids), ())

    def test_level_values_are_applied_to_cloudcatcher_only(self):
        for level, expected in ((6, 10), (10, 23), (12, 30), ("Elite", 35)):
            with self.subTest(level=level):
                state = build_game_state(self.bag("cloudcatcher", "divebomb"), CATALOG, level, "cloudcatcher")
                effect = next(
                    ability.effects[0]
                    for ability in state.current_entry.club.abilities
                    if ability.text == "bounce_reduction"
                )
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(result.modifiers["bounce_reduction_percent"], expected)
                self.assertEqual(result.final_stats, result.base_stats)

                other_levels = {"cloudcatcher": level, "divebomb": 12}
                other_state = build_game_state(
                    self.bag("cloudcatcher", "divebomb"), CATALOG, other_levels, "divebomb"
                )
                other_effect = next(
                    ability.effects[0]
                    for ability in other_state.bag.get("cloudcatcher").club.abilities
                    if ability.text == "bounce_reduction"
                )
                other = RuleEngine().evaluate(other_state, (other_effect,), mode=EvaluationMode.STRICT)
                self.assertNotIn("bounce_reduction_percent", other.modifiers)

    def test_absent_level_value_does_not_materialize_the_ability(self):
        state = build_game_state(self.bag("cloudcatcher", "divebomb"), CATALOG, 5, "cloudcatcher")
        self.assertNotIn("bounce_reduction", {ability.text for ability in state.current_entry.club.abilities})

    def test_strict_partial_and_attributed_contribution(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = build_game_state(self.bag("cloudcatcher", "divebomb"), CATALOG, 12, "cloudcatcher")
                effect = next(
                    ability.effects[0]
                    for ability in state.current_entry.club.abilities
                    if ability.text == "bounce_reduction"
                )
                result = RuleEngine().evaluate(state, (effect,), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.modifiers["bounce_reduction_percent"], 30)

        evaluation = evaluate_bag(
            self.bag("cloudcatcher", "divebomb"),
            level=12,
            mode=EvaluationMode.PARTIAL,
            catalog_path=CATALOG,
            current_club_id="cloudcatcher",
        )
        contribution = next(
            item
            for item in summarize_bag_evaluation(evaluation, 1).ability_contributions
            if item.ability_id == "cloudcatcher__bounce_reduction"
        )
        self.assertEqual(contribution.modification["bounce_reduction_percent"], 30)
        self.assertTrue(contribution.applied)
        self.assertEqual(contribution.unresolved, ())

    def test_explain_matches_golden_file(self):
        state = build_game_state(self.bag("cloudcatcher", "divebomb"), CATALOG, 12, "cloudcatcher")
        effect = next(
            ability.effects[0]
            for ability in state.current_entry.club.abilities
            if ability.text == "bounce_reduction"
        )
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
        self.assertEqual(render_explain_entries(result.explain) + "\n", GOLDEN.read_text(encoding="utf-8"))

    def test_comparator_exposes_reduction_as_a_separate_percent_metric(self):
        cloud = evaluate_bag(
            self.bag("cloudcatcher", "divebomb"),
            level=12,
            mode=EvaluationMode.PARTIAL,
            catalog_path=CATALOG,
            current_club_id="cloudcatcher",
        )
        plain = evaluate_bag(
            self.bag("divebomb", "jumpstart"),
            level=12,
            mode=EvaluationMode.PARTIAL,
            catalog_path=CATALOG,
            current_club_id="divebomb",
        )
        metrics = {
            metric.definition.identifier: metric
            for metric in _comparable_metrics(summarize_bag_evaluation(plain, 1), summarize_bag_evaluation(cloud, 1))
        }
        reduction = metrics["bounce_reduction_percent"]
        self.assertEqual(reduction.definition.unit, "percent")
        self.assertEqual(reduction.left_final, 0)
        self.assertEqual(reduction.right_final, 30)
        self.assertEqual(reduction.difference_right_minus_left, 30)


if __name__ == "__main__":
    unittest.main()
