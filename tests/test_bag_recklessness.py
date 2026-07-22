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


class BagRecklessnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    @staticmethod
    def state(club_ids, level, current_club_id):
        saved = SavedBag("recklessness", "Recklessness", "active", tuple(club_ids), ())
        return build_game_state(saved, CATALOG, level, current_club_id)

    @staticmethod
    def effect(state):
        return next(
            ability.effects[0]
            for ability in state.bag.get("into_the_breach").club.abilities
            if ability.text == "bag_recklessness"
        )

    def test_configuration_uses_one_declarative_multi_stat_pattern(self):
        entry = self.semantic["entries"]["label:bag_recklessness"]
        self.assertEqual(entry["pattern_id"], "bag_multi_stat_tradeoff")
        self.assertNotIn("program", entry)
        program = _semantic_program(entry, self.semantic["patterns"])
        self.assertEqual(
            [node["operation"] for node in program["nodes"]],
            ["SELECT_SELF", "READ_LEVEL_VALUE", "READ_LEVEL_VALUE", "SELECT_ALL", "FOR_EACH"],
        )

    def test_other_club_gains_power_and_spin_but_loses_control(self):
        state = self.state(("jumpstart", "into_the_breach", "high_flight"), 12, "jumpstart")
        effect = self.effect(state)
        result = RuleEngine().evaluate(state, (effect,), mode=EvaluationMode.STRICT)
        self.assertEqual(
            effect.parameters["level_components"],
            {"power_spin_bonus": 4.0, "control_delta": -4.0},
        )
        self.assertEqual(result.final_stats.power, result.base_stats.power + 4)
        self.assertEqual(result.final_stats.spin, result.base_stats.spin + 4)
        self.assertEqual(result.final_stats.control, result.base_stats.control - 4)

    def test_every_non_source_target_receives_the_same_tradeoff(self):
        for current in ("jumpstart", "high_flight"):
            with self.subTest(current=current):
                state = self.state(("jumpstart", "into_the_breach", "high_flight"), 12, current)
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
                self.assertEqual(result.final_stats.power - result.base_stats.power, 4)
                self.assertEqual(result.final_stats.control - result.base_stats.control, -4)
                self.assertEqual(result.final_stats.spin - result.base_stats.spin, 4)

    def test_source_is_explicitly_excluded(self):
        state = self.state(("jumpstart", "into_the_breach", "high_flight"), 12, "into_the_breach")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        self.assertEqual(result.final_stats, result.base_stats)

    def test_official_components_are_read_independently_at_elite(self):
        state = self.state(("into_the_breach", "high_flight"), "Elite", "into_the_breach")
        effect = self.effect(state)
        self.assertEqual(
            effect.parameters["level_components"],
            {"power_spin_bonus": 4.0, "control_delta": -3.0},
        )
        entries = []
        for entry in state.bag.entries:
            if entry.club.identifier == "high_flight":
                stats = dict(entry.club.stats_by_level)
                stats["Elite"] = Stats(power=10, control=10, spin=10)
                entry = BagEntry(replace(entry.club, stats_by_level=stats), entry.level)
            entries.append(entry)
        target_state = GameState(Bag(tuple(entries)), current_club_id="high_flight")
        result = RuleEngine().evaluate(target_state, (effect,), mode=EvaluationMode.STRICT)
        self.assertEqual(result.final_stats, Stats(power=14, control=7, spin=14))

    def test_missing_level_value_creates_no_effect(self):
        state = self.state(("rampart", "into_the_breach"), 1, "rampart")
        labels = {ability.text for ability in state.bag.get("into_the_breach").club.abilities}
        self.assertNotIn("bag_recklessness", labels)

    def test_strict_and_partial_modes_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(("jumpstart", "into_the_breach"), 12, "jumpstart")
                result = RuleEngine().evaluate(state, (self.effect(state),), mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(result.unresolved, ())

    def test_explain_reports_each_signed_stat_impact(self):
        state = self.state(("jumpstart", "into_the_breach"), 12, "jumpstart")
        result = RuleEngine().evaluate(state, (self.effect(state),), mode=EvaluationMode.STRICT)
        rendered = render_explain_entries(result.explain)
        self.assertIn("Detail: POWER += 4", rendered)
        self.assertIn("Detail: SPIN += 4", rendered)
        self.assertIn("Detail: CONTROL += -4", rendered)
        applied_stats = [
            entry.inputs["stat"]
            for entry in result.explain
            if entry.mechanism == "ADD_STAT" and entry.applied
        ]
        self.assertEqual(applied_stats, ["power", "spin", "control"])


if __name__ == "__main__":
    unittest.main()
