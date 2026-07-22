import json
import unittest
from dataclasses import replace
from pathlib import Path

from pga_shootout.bag_evaluation import _semantic_program, build_game_state
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import Bag, BagEntry, EvaluationMode, GameState, Stats
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"


class AbsentTypesStatBonusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    @staticmethod
    def state(club_ids, level, current_club_id):
        saved = SavedBag("exclusion", "Exclusion", "active", tuple(club_ids), ())
        return build_game_state(saved, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state, label_id):
        return next(
            ability.effects[0]
            for ability in state.bag.get("earthquake").club.abilities
            if ability.text == label_id
        )

    @staticmethod
    def with_synthetic_source_stats(state, level):
        entries = []
        for entry in state.bag.entries:
            if entry.club.identifier == "earthquake":
                stats = dict(entry.club.stats_by_level)
                stats[level] = Stats(power=3, control=7, spin=99)
                entry = BagEntry(replace(entry.club, stats_by_level=stats), entry.level)
            entries.append(entry)
        return GameState(bag=Bag(tuple(entries)), current_club_id="earthquake")

    def test_two_families_reference_one_pattern_without_inline_programs(self):
        entries = self.semantic["entries"]
        self_bonus = entries["label:iron_wedge_exclusion"]
        bag_bonus = entries["label:exclusion_zone"]
        self.assertEqual(self_bonus["pattern_id"], "absent_types_stat_bonus")
        self.assertEqual(bag_bonus["pattern_id"], self_bonus["pattern_id"])
        self.assertNotIn("program", self_bonus)
        self.assertNotIn("program", bag_bonus)

    def test_pattern_changes_only_target_selection(self):
        entries = self.semantic["entries"]
        patterns = self.semantic["patterns"]
        self_program = _semantic_program(entries["label:iron_wedge_exclusion"], patterns)
        bag_program = _semantic_program(entries["label:exclusion_zone"], patterns)
        self.assertEqual(self_program["nodes"][-1]["operation"], "UNLESS")
        self.assertEqual(bag_program["nodes"][-1]["operation"], "UNLESS")
        self_targets = next(node for node in self_program["nodes"] if node["id"] == "targets")
        bag_targets = next(node for node in bag_program["nodes"] if node["id"] == "targets")
        self.assertEqual(self_targets["operation"], "SELECT_SELF")
        self.assertEqual(bag_targets["operation"], "SELECT_ALL")

    def test_exclusion_zone_applies_to_every_other_club_when_types_are_absent(self):
        for current in ("jumpstart", "high_flight"):
            with self.subTest(current=current):
                state = self.state(("earthquake", "jumpstart", "high_flight"), 3, current)
                effect = self.effect(state, "exclusion_zone")
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.parameters["level_value"], 3)
                self.assertEqual(result.final_stats.power, result.base_stats.power + 3)

    def test_exclusion_zone_is_blocked_by_either_iron_or_wedge(self):
        for excluded_club in ("wave", "into_the_blue"):
            with self.subTest(excluded_club=excluded_club):
                state = self.state(("earthquake", "jumpstart", excluded_club), 3, "jumpstart")
                result = RuleEngine().evaluate(
                    state, (self.effect(state, "exclusion_zone"),), mode=EvaluationMode.STRICT
                )
                self.assertEqual(result.final_stats, result.base_stats)
                branch = next(entry for entry in result.explain if entry.mechanism == "UNLESS")
                self.assertFalse(branch.applied)
                self.assertEqual(branch.outputs, {"executed": False})

    def test_iron_wedge_exclusion_targets_only_the_source(self):
        state = self.state(("earthquake", "jumpstart", "high_flight"), 3, "jumpstart")
        state = self.with_synthetic_source_stats(state, 3)
        result = RuleEngine().evaluate(
            state, (self.effect(state, "iron_wedge_exclusion"),), mode=EvaluationMode.STRICT
        )
        self.assertEqual(result.final_stats.power, result.base_stats.power + 8)

    def test_official_values_vary_by_level(self):
        for level, expected in ((3, 3), (10, 4)):
            with self.subTest(level=level):
                state = self.state(("earthquake", "jumpstart"), level, "jumpstart")
                effect = self.effect(state, "exclusion_zone")
                result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
                self.assertEqual(effect.parameters["level_value"], expected)
                self.assertEqual(result.final_stats.power, result.base_stats.power + expected)

    def test_absent_level_values_create_no_effects(self):
        state = self.state(("earthquake", "rampart"), 1, "rampart")
        labels = {ability.text for ability in state.bag.get("earthquake").club.abilities}
        self.assertNotIn("iron_wedge_exclusion", labels)
        self.assertNotIn("exclusion_zone", labels)

    def test_strict_and_partial_modes_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(("earthquake", "jumpstart"), 3, "jumpstart")
                result = RuleEngine().evaluate(state, (self.effect(state, "exclusion_zone"),), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.unresolved, ())

    def test_explain_reports_absence_condition_branch_and_target_effect(self):
        state = self.state(("earthquake", "jumpstart", "high_flight"), 3, "jumpstart")
        result = RuleEngine().evaluate(
            state, (self.effect(state, "exclusion_zone"),), mode=EvaluationMode.STRICT
        )
        rendered = render_explain_entries(result.explain)
        self.assertIn('"type": ["iron", "wedge"]', rendered)
        self.assertIn('Outputs: {"exists": false}', rendered)
        self.assertIn('Outputs: {"executed": true}', rendered)
        self.assertIn('Inputs: {"binding": "target", "items": ["Jumpstart", "High Flight"]}', rendered)
        self.assertIn("Detail: POWER += 3", rendered)


if __name__ == "__main__":
    unittest.main()
