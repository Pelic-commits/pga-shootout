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


class WindResistanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads(
            (ROOT / "data" / "normalized" / "semantic_map.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def bag(*club_ids):
        return SavedBag("wind", "Wind", "fixture", tuple(club_ids), ())

    @staticmethod
    def effect(state, source_id, label):
        return next(
            ability.effects[0]
            for ability in state.bag.get(source_id).club.abilities
            if ability.text == label
        )

    def test_both_scopes_reuse_the_existing_static_modifier_pattern(self):
        entries = self.semantic["entries"]
        self.assertEqual(entries["label:wind_resist_75"]["pattern_id"], "static_modifier_targets")
        self.assertEqual(entries["label:bag_wind_resist"]["pattern_id"], "static_modifier_targets")
        self.assertEqual(
            entries["label:wind_resist_75"]["pattern_parameters"]["selection_operation"],
            "SELECT_SELF",
        )
        self.assertEqual(
            entries["label:bag_wind_resist"]["pattern_parameters"]["selection_operation"],
            "SELECT_ALL",
        )
        self.assertIn("ADD_MODIFIER", default_dsl_registry().names)

    def test_high_flight_resistance_applies_only_to_high_flight(self):
        bag = self.bag("high_flight", "cyclotron")
        for current, expected in (("high_flight", 75), ("cyclotron", 0)):
            with self.subTest(current=current):
                state = build_game_state(bag, CATALOG, 12, current)
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "high_flight", "wind_resist_75"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers.get("wind_resistance_percent", 0), expected)

    def test_high_flight_unlock_level_is_respected(self):
        for level, active in ((4, False), (5, True), (12, True)):
            state = build_game_state(self.bag("high_flight", "cyclotron"), CATALOG, level, "high_flight")
            abilities = {ability.text for ability in state.bag.get("high_flight").club.abilities}
            self.assertEqual("wind_resist_75" in abilities, active)

    def test_rook_bag_resistance_targets_every_position(self):
        bag = self.bag("divebomb", "rook", "jumpstart")
        for current in ("divebomb", "jumpstart"):
            with self.subTest(current=current):
                state = build_game_state(bag, CATALOG, 12, current)
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "rook", "bag_wind_resist"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers, {"wind_resistance_percent": 20.0})

    def test_rook_official_values_are_read_by_level(self):
        for level, expected in ((1, 9), (5, 13), (12, 20), ("Elite", 30)):
            with self.subTest(level=level):
                levels = {"rook": level, "divebomb": 12}
                state = build_game_state(self.bag("rook", "divebomb"), CATALOG, levels, "divebomb")
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "rook", "bag_wind_resist"),),
                    mode=EvaluationMode.STRICT,
                )
                self.assertEqual(result.modifiers["wind_resistance_percent"], expected)

    def test_same_bag_scope_configuration_covers_other_official_occurrence(self):
        levels = {"conspiracy": 12, "divebomb": 12}
        state = build_game_state(self.bag("conspiracy", "divebomb"), CATALOG, levels, "divebomb")
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "conspiracy", "bag_wind_resist"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(result.modifiers, {"wind_resistance_percent": 40.0})

    def test_strict_partial_and_attributed_contribution_are_complete(self):
        bag = self.bag("rook", "divebomb")
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = build_game_state(bag, CATALOG, 12, "divebomb")
                result = RuleEngine().evaluate(
                    state,
                    (self.effect(state, "rook", "bag_wind_resist"),),
                    mode=mode,
                )
                self.assertTrue(result.complete)
                self.assertEqual(result.modifiers["wind_resistance_percent"], 20)

        evaluation = evaluate_bag(
            bag,
            level=12,
            mode=EvaluationMode.PARTIAL,
            catalog_path=CATALOG,
            current_club_id="divebomb",
        )
        contribution = next(
            item
            for item in summarize_bag_evaluation(evaluation, 2).ability_contributions
            if item.ability_id == "rook__bag_wind_resist"
        )
        self.assertEqual(contribution.modification["wind_resistance_percent"], 20)
        self.assertTrue(contribution.applied)
        self.assertEqual(contribution.unresolved, ())

    def test_compare_bags_exposes_wind_resistance_as_a_percent_metric(self):
        comparison = compare_saved_bags(
            "par3_divebomb",
            "par3_high_flight",
            level=12,
            current_position=1,
            mode=EvaluationMode.PARTIAL,
            user_dir=USER_DIR,
            catalog_path=CATALOG,
        )
        metric = next(
            item for item in comparison.metrics
            if item.definition.identifier == "wind_resistance_percent"
        )
        self.assertEqual(metric.definition.unit, "percent")
        self.assertEqual((metric.left_final, metric.right_final, metric.difference_right_minus_left), (0, 75, 75))
        contribution = next(
            item for item in comparison.right.ability_contributions
            if item.ability_id == "high_flight__wind_resist_75"
        )
        self.assertEqual(contribution.modification["wind_resistance_percent"], 75)

        rook = evaluate_bag(
            self.bag("rook", "divebomb"),
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
            item.definition.identifier: item
            for item in _comparable_metrics(
                summarize_bag_evaluation(plain, 1), summarize_bag_evaluation(rook, 2)
            )
        }
        self.assertEqual(metrics["wind_resistance_percent"].right_final, 20)

    def test_high_flight_explain_matches_golden(self):
        state = build_game_state(self.bag("high_flight", "cyclotron"), CATALOG, 12, "high_flight")
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "high_flight", "wind_resist_75"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(
            render_explain_entries(result.explain) + "\n",
            (GOLDEN / "high_flight_wind_resistance_explain.txt").read_text(encoding="utf-8"),
        )

    def test_rook_explain_matches_golden(self):
        state = build_game_state(
            self.bag("divebomb", "rook", "jumpstart"), CATALOG, 12, "divebomb"
        )
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "rook", "bag_wind_resist"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(
            render_explain_entries(result.explain) + "\n",
            (GOLDEN / "rook_bag_wind_resistance_explain.txt").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
