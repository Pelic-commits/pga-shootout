import json
import unittest
from pathlib import Path

from pga_shootout.bag_comparison import _comparable_metrics, compare_saved_bags, summarize_bag_evaluation
from pga_shootout.bag_evaluation import build_game_state, evaluate_bag
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
USER_DIR = ROOT / "data" / "user"
GOLDEN = ROOT / "tests" / "golden"


class OwnedStaticModifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads(
            (ROOT / "data" / "normalized" / "semantic_map.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def bag(*club_ids):
        return SavedBag("static", "Static", "fixture", tuple(club_ids), ())

    @staticmethod
    def effect(state, source_id, label):
        return next(
            ability.effects[0]
            for ability in state.bag.get(source_id).club.abilities
            if ability.text == label
        )

    def test_both_abilities_reuse_the_existing_static_modifier_pattern(self):
        entries = self.semantic["entries"]
        for label in ("bounce_reduction_boost", "fade_draw_x2"):
            self.assertEqual(entries[f"label:{label}"]["pattern_id"], "static_modifier_targets")
        self.assertIn("ADD_MODIFIER", default_dsl_registry().names)

    def test_bounce_reduction_targets_only_the_immediate_left_club(self):
        bag = self.bag("divebomb", "cyclotron", "jumpstart")
        for current, expected in (("divebomb", 20), ("cyclotron", 0), ("jumpstart", 0)):
            with self.subTest(current=current):
                state = build_game_state(bag, CATALOG, 12, current)
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "cyclotron", "bounce_reduction_boost"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers.get("bounce_reduction_percent", 0), expected)

    def test_bounce_reduction_handles_first_and_last_source_positions(self):
        first = build_game_state(self.bag("cyclotron", "divebomb"), CATALOG, 12, "cyclotron")
        first_result = RuleEngine().evaluate(
            first,
            (self.effect(first, "cyclotron", "bounce_reduction_boost"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(first_result.modifiers, {})

        last = build_game_state(self.bag("divebomb", "cyclotron"), CATALOG, 12, "divebomb")
        last_result = RuleEngine().evaluate(
            last,
            (self.effect(last, "cyclotron", "bounce_reduction_boost"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(last_result.modifiers, {"bounce_reduction_percent": 20.0})

    def test_official_bounce_values_and_inactive_level(self):
        for level, expected in ((5, 10), (8, 14), (12, 20), ("Elite", 22)):
            with self.subTest(level=level):
                levels = {"divebomb": 12, "cyclotron": level}
                state = build_game_state(self.bag("divebomb", "cyclotron"), CATALOG, levels, "divebomb")
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "cyclotron", "bounce_reduction_boost"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers["bounce_reduction_percent"], expected)
        inactive = build_game_state(self.bag("divebomb", "cyclotron"), CATALOG, 4, "divebomb")
        self.assertNotIn(
            "bounce_reduction_boost",
            {ability.text for ability in inactive.bag.get("cyclotron").club.abilities},
        )

    def test_fade_draw_targets_every_club_at_every_active_level(self):
        bag = self.bag("lodestar", "divebomb", "jumpstart")
        for level in (5, 12, "Elite"):
            for current in bag.club_ids:
                with self.subTest(level=level, current=current):
                    levels = {"lodestar": level, "divebomb": 12, "jumpstart": 12}
                    state = build_game_state(bag, CATALOG, levels, current)
                    result = RuleEngine().evaluate(
                        state,
                        (self.effect(state, "lodestar", "fade_draw_x2"),),
                        mode=EvaluationMode.STRICT,
                    )
                    self.assertEqual(result.modifiers, {"fade_draw_multiplier": 2.0})

    def test_fade_draw_is_absent_before_activation(self):
        state = build_game_state(self.bag("lodestar", "divebomb"), CATALOG, 4, "divebomb")
        self.assertNotIn("fade_draw_x2", {ability.text for ability in state.bag.get("lodestar").club.abilities})

    def test_strict_partial_and_contributions_are_complete(self):
        bag = self.bag("lodestar", "divebomb", "cyclotron")
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = build_game_state(bag, CATALOG, 12, "divebomb")
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "lodestar", "fade_draw_x2"),),
                    mode=mode,
                )
                self.assertTrue(result.complete)
                self.assertEqual(result.modifiers["fade_draw_multiplier"], 2)

        evaluation = evaluate_bag(
            bag,
            level=12,
            mode=EvaluationMode.PARTIAL,
            catalog_path=CATALOG,
            current_club_id="divebomb",
        )
        fade = next(
            item
            for item in summarize_bag_evaluation(evaluation, 2).ability_contributions
            if item.ability_id == "lodestar__fade_draw_x2"
        )
        self.assertEqual(fade.modification["fade_draw_multiplier"], 2)
        self.assertTrue(fade.applied)
        self.assertEqual(fade.unresolved, ())

    def test_compare_bags_exposes_both_objective_metrics(self):
        comparison = compare_saved_bags(
            "par3_divebomb",
            "par3_high_flight",
            level=12,
            current_position=1,
            mode=EvaluationMode.PARTIAL,
            user_dir=USER_DIR,
            catalog_path=CATALOG,
        )
        reduction = next(
            metric for metric in comparison.metrics
            if metric.definition.identifier == "bounce_reduction_percent"
        )
        self.assertEqual((reduction.left_final, reduction.right_final), (0, 40))
        cyclotron = next(
            item for item in comparison.right.ability_contributions
            if item.ability_id == "cyclotron__bounce_reduction_boost"
        )
        self.assertEqual(cyclotron.modification["bounce_reduction_percent"], 20)

        fade = evaluate_bag(
            self.bag("lodestar", "divebomb"),
            level=12,
            mode=EvaluationMode.PARTIAL,
            catalog_path=CATALOG,
            current_club_id="divebomb",
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
            for metric in _comparable_metrics(
                summarize_bag_evaluation(plain, 1), summarize_bag_evaluation(fade, 2)
            )
        }
        self.assertEqual(metrics["fade_draw_multiplier"].definition.unit, "multiplier")
        self.assertEqual(metrics["fade_draw_multiplier"].right_final, 2)

    def test_bounce_explain_matches_golden(self):
        state = build_game_state(
            self.bag("high_flight", "cyclotron", "ember"), CATALOG, 12, "high_flight"
        )
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "cyclotron", "bounce_reduction_boost"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(
            render_explain_entries(result.explain) + "\n",
            (GOLDEN / "cyclotron_bounce_reduction_explain.txt").read_text(encoding="utf-8"),
        )

    def test_fade_draw_explain_matches_golden(self):
        state = build_game_state(
            self.bag("lodestar", "divebomb", "jumpstart"), CATALOG, 12, "divebomb"
        )
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "lodestar", "fade_draw_x2"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(
            render_explain_entries(result.explain) + "\n",
            (GOLDEN / "lodestar_fade_draw_explain.txt").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
