import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import build_game_state
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"


class BrandWidePowerTests(unittest.TestCase):
    CASES = (
        ("ranger", "forester_power", "edgewalker", "steadfast", 10, 3),
        ("rising_flame", "phoenix_power", "flamethrower", "steadfast", 10, 3),
        ("saber", "stanchion_power", "rampart", "steadfast", "Elite", 3),
    )

    def state(self, club_ids, level, current_club_id):
        bag = SavedBag("brand_power", "Brand Power", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state, source_id, label_id):
        source = state.bag.get(source_id)
        return next(ability.effects[0] for ability in source.club.abilities if ability.text == label_id)

    def test_three_families_share_exact_pipeline(self):
        entries = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))["entries"]
        programs = [entries[f"label:{label}"]["program"] for _, label, *_ in self.CASES]
        expected = ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_ALL", "MATCH_BRAND", "FOR_EACH")

        for program in programs:
            self.assertEqual(tuple(node["operation"] for node in program["nodes"]), expected)
            self.assertEqual(program["nodes"][-1]["parameters"]["program"]["nodes"][0]["operation"], "ADD_STAT")
        self.assertTrue({*expected, "ADD_STAT"}.issubset(default_dsl_registry().names))

    def test_matching_brand_club_receives_official_bonus(self):
        for source, label, matching, other, level, expected in self.CASES:
            with self.subTest(label=label):
                state = self.state((matching, source, other), level, matching)
                effect = self.effect(state, source, label)
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.parameters["level_value"], expected)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected)

    def test_non_matching_brand_is_unchanged(self):
        for source, label, matching, other, level, _ in self.CASES:
            with self.subTest(label=label):
                state = self.state((matching, source, other), level, other)
                result = RuleEngine().evaluate(state, (self.effect(state, source, label),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats, result.base_stats)

    def test_source_is_included_among_matching_brand_targets(self):
        for source, label, matching, _, level, _ in self.CASES:
            with self.subTest(label=label):
                state = self.state((matching, source), level, matching)
                result = RuleEngine().evaluate(state, (self.effect(state, source, label),), mode=EvaluationMode.STRICT)
                iteration = next(entry for entry in result.explain if entry.mechanism == "FOR_EACH")
                self.assertIn(state.bag.get(source).club.name, iteration.inputs["items"])

    def test_filter_and_iteration_preserve_bag_order(self):
        state = self.state(("edgewalker", "steadfast", "ranger", "outset"), 10, "edgewalker")
        result = RuleEngine().evaluate(state, (self.effect(state, "ranger", "forester_power"),), mode=EvaluationMode.STRICT)
        matching = next(entry for entry in result.explain if entry.mechanism == "MATCH_BRAND")
        iteration = next(entry for entry in result.explain if entry.mechanism == "FOR_EACH")

        self.assertEqual(iteration.inputs["items"], ["Edgewalker", "Ranger", "Outset"])
        self.assertEqual(iteration.outputs["iterations"], 3)
        self.assertEqual(matching.outputs, {"left": None, "right": None})

    def test_absent_level_values_do_not_create_effects(self):
        state = self.state(("rampart", "ranger", "rising_flame", "saber"), 1, "rampart")
        for source, label in (("ranger", "forester_power"), ("rising_flame", "phoenix_power"), ("saber", "stanchion_power")):
            self.assertNotIn(label, {ability.text for ability in state.bag.get(source).club.abilities})

    def test_strict_and_partial_modes_complete(self):
        for source, label, matching, _, level, _ in self.CASES:
            for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
                with self.subTest(label=label, mode=mode):
                    state = self.state((matching, source), level, matching)
                    result = RuleEngine().evaluate(state, (self.effect(state, source, label),), mode=mode)
                    self.assertTrue(result.complete)
                    self.assertEqual(result.unresolved, ())

    def test_explain_contains_selection_filter_iteration_and_effect(self):
        state = self.state(("edgewalker", "steadfast", "ranger"), 10, "edgewalker")
        result = RuleEngine().evaluate(state, (self.effect(state, "ranger", "forester_power"),), mode=EvaluationMode.STRICT)
        rendered = render_explain_entries(result.explain)

        self.assertIn('Outputs: {"clubs": ["Edgewalker", "Steadfast", "Ranger"]}', rendered)
        self.assertIn('Inputs: {"brand": "forester"', rendered)
        self.assertIn('Inputs: {"binding": "target", "items": ["Edgewalker", "Ranger"]}', rendered)
        self.assertIn("Detail: POWER += 3", rendered)


if __name__ == "__main__":
    unittest.main()
