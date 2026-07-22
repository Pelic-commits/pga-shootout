import json
import unittest
from pathlib import Path

from pga_shootout.bag_evaluation import _semantic_program, build_game_state
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
CATALOG = NORMALIZED / "clubs_official.json"
GOLDEN = ROOT / "tests" / "golden" / "mirage_bounces_explain.txt"


class MirageBounceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

    def state(self, level, current_club_id="mirage"):
        return build_game_state(
            SavedBag("mirage", "Mirage", "active", ("mirage", "high_flight"), ()),
            CATALOG,
            level,
            current_club_id,
        )

    @staticmethod
    def effects(state):
        return tuple(ability.effects[0] for ability in state.bag.get("mirage").club.abilities)

    def test_both_abilities_reuse_the_static_modifier_pattern(self):
        for label, modifier in (("sand_bounce", "sand_bounce_count"), ("water_bounce", "water_bounce_count")):
            with self.subTest(label=label):
                entry = self.semantic["entries"][f"label:{label}"]
                self.assertEqual(entry["pattern_id"], "static_modifier_targets")
                self.assertEqual(entry["pattern_parameters"]["modifier"], modifier)
                self.assertEqual(
                    tuple(node["operation"] for node in _semantic_program(entry, self.semantic["patterns"])["nodes"]),
                    ("SELECT_SELF", "READ_LEVEL_VALUE", "SELECT_SELF", "FOR_EACH"),
                )

    def test_level_twelve_exposes_each_bounce_metric_separately(self):
        state = self.state(12)
        result = RuleEngine().evaluate(state, self.effects(state), mode=EvaluationMode.STRICT)
        self.assertEqual(result.modifiers, {"sand_bounce_count": 2.0, "water_bounce_count": 2.0})
        self.assertEqual(result.final_stats, result.base_stats)

    def test_modifiers_apply_only_when_mirage_is_the_current_club(self):
        state = self.state(12, "high_flight")
        result = RuleEngine().evaluate(state, self.effects(state), mode=EvaluationMode.STRICT)
        self.assertEqual(result.modifiers, {})

    def test_official_unlock_levels_are_respected(self):
        state = self.state(1)
        self.assertEqual({ability.text for ability in state.bag.get("mirage").club.abilities}, {"sand_bounce"})
        result = RuleEngine().evaluate(state, self.effects(state), mode=EvaluationMode.STRICT)
        self.assertEqual(result.modifiers, {"sand_bounce_count": 1.0})

    def test_strict_partial_and_explain_are_complete(self):
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                state = self.state(12)
                result = RuleEngine().evaluate(state, self.effects(state), mode=mode)
                self.assertTrue(result.complete)
                rendered = render_explain_entries(result.explain)
                self.assertIn("Detail: SAND_BOUNCE_COUNT += 2", rendered)
                self.assertIn("Detail: WATER_BOUNCE_COUNT += 2", rendered)

    def test_complete_explain_matches_the_golden_file(self):
        state = self.state(12)
        result = RuleEngine().evaluate(state, self.effects(state), mode=EvaluationMode.STRICT)
        self.assertEqual(render_explain_entries(result.explain) + "\n", GOLDEN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
