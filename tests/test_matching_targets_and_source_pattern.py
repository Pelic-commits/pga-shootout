import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import BagEvaluationError, _semantic_program, build_game_state
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"


class MatchingTargetsAndSourcePatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    @staticmethod
    def state(club_ids, level, current_club_id):
        bag = SavedBag("pattern", "Pattern", "active", tuple(club_ids), ())
        return build_game_state(bag, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state, source_id, label_id):
        return next(
            ability.effects[0]
            for ability in state.bag.get(source_id).club.abilities
            if ability.text == label_id
        )

    def test_two_families_reference_one_declarative_pattern(self):
        entries = self.semantic["entries"]
        alloy = entries["label:alloy"]
        nautilus = entries["label:nautilus_boost"]
        self.assertEqual(alloy["pattern_id"], "matching_targets_and_source_per_match")
        self.assertEqual(nautilus["pattern_id"], alloy["pattern_id"])
        self.assertNotIn("program", alloy)
        self.assertNotIn("program", nautilus)

    def test_pattern_parameters_change_only_selection_and_filtering(self):
        pattern = self.semantic["patterns"]
        entries = self.semantic["entries"]
        alloy = _semantic_program(entries["label:alloy"], pattern)
        nautilus = _semantic_program(entries["label:nautilus_boost"], pattern)
        self.assertEqual(alloy["nodes"][2]["operation"], "SELECT_ALL")
        self.assertEqual(alloy["nodes"][3]["operation"], "MATCH_TYPE")
        self.assertEqual(nautilus["nodes"][2]["operation"], "SELECT_ADJACENT")
        self.assertEqual(nautilus["nodes"][3]["operation"], "MATCH_BRAND")
        for program in (alloy, nautilus):
            nested = program["nodes"][-1]["parameters"]["program"]["nodes"]
            self.assertEqual([node["operation"] for node in nested], ["ADD_STAT", "ADD_STAT"])
            self.assertTrue(all(node["parameters"]["stat"] == "power" for node in nested))

    def test_missing_pattern_parameter_fails_before_evaluation(self):
        entry = {"pattern_id": "matching_targets_and_source_per_match", "pattern_parameters": {}}
        with self.assertRaisesRegex(BagEvaluationError, "Missing semantic pattern parameter"):
            _semantic_program(entry, self.semantic["patterns"])

    def test_alloy_applies_once_to_each_hybrid_target(self):
        for current, expected_delta in (("high_flight", 6), ("ironbark", 6), ("steadfast", 0)):
            with self.subTest(current=current):
                state = self.state(("high_flight", "ember", "ironbark", "steadfast"), 8, current)
                effect = self.effect(state, "ember", "alloy")
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.parameters["level_value"], 6)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected_delta)

    def test_nautilus_boost_scales_source_by_matching_neighbors(self):
        state = self.state(("dunecrawler", "wave", "maelstrom"), 9, "wave")
        effect = self.effect(state, "wave", "nautilus_boost")
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
        self.assertEqual(effect.parameters["level_value"], 3)
        self.assertEqual(result.final_stats.power, result.base_stats.power + 6)

    def test_nautilus_target_gets_one_bonus_and_incompatible_neighbor_gets_none(self):
        bag = ("dunecrawler", "wave", "steadfast")
        for current, expected_delta in (("dunecrawler", 3), ("steadfast", 0)):
            with self.subTest(current=current):
                state = self.state(bag, 9, current)
                result = RuleEngine().evaluate(
                    state, (self.effect(state, "wave", "nautilus_boost"),), mode=EvaluationMode.STRICT
                )
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected_delta)

    def test_strict_and_partial_modes_complete(self):
        for source, label, clubs, level, current in (
            ("ember", "alloy", ("high_flight", "ember"), 8, "high_flight"),
            ("wave", "nautilus_boost", ("dunecrawler", "wave"), 9, "wave"),
        ):
            for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
                with self.subTest(label=label, mode=mode):
                    state = self.state(clubs, level, current)
                    result = RuleEngine().evaluate(state, (self.effect(state, source, label),), mode=mode)
                    self.assertTrue(result.complete)
                    self.assertEqual(result.unresolved, ())

    def test_explain_shows_selection_filter_and_both_per_match_effects(self):
        state = self.state(("dunecrawler", "wave", "maelstrom"), 9, "wave")
        result = RuleEngine().evaluate(
            state, (self.effect(state, "wave", "nautilus_boost"),), mode=EvaluationMode.STRICT
        )
        rendered = render_explain_entries(result.explain)
        self.assertIn('Outputs: {"left": "Dunecrawler", "right": "Maelstrom"}', rendered)
        self.assertIn('Inputs: {"binding": "target", "items": ["Dunecrawler", "Maelstrom"]}', rendered)
        self.assertEqual(sum(entry.mechanism == "ADD_STAT" for entry in result.explain), 4)
        self.assertEqual(rendered.count("Detail: POWER += 3"), 2)


if __name__ == "__main__":
    unittest.main()
