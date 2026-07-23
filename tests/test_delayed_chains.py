import json
import unittest
from pathlib import Path

from pga_shootout.bag_comparison import compare_saved_bags, render_bag_comparison
from pga_shootout.bag_evaluation import build_game_state
from pga_shootout.dsl import default_dsl_registry
from pga_shootout.engine import RuleEngine
from pga_shootout.explain import render_explain_entries
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
USER_DIR = ROOT / "data" / "user"
GOLDEN = ROOT / "tests" / "golden" / "chains_into_putters_resolution_explain.txt"


class DelayedChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.semantic = json.loads(
            (ROOT / "data" / "normalized" / "semantic_map.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def bag(*club_ids):
        return SavedBag("chains", "Chains", "fixture", tuple(club_ids), ())

    @staticmethod
    def effect(state, source_id, label):
        return next(
            ability.effects[0]
            for ability in state.bag.get(source_id).club.abilities
            if ability.text == label
        )

    def schedule(self, bag, source_id, label, level=12, mode=EvaluationMode.STRICT):
        state = build_game_state(bag, CATALOG, level, source_id)
        return RuleEngine().evaluate(
            state,
            (self.effect(state, source_id, label),),
            mode=mode,
        )

    def test_three_groups_share_one_delayed_pattern_and_primitive(self):
        entries = self.semantic["entries"]
        for label in ("chains_into_willoughsby", "chains_into_wedges", "chains_into_putters"):
            self.assertEqual(
                entries[f"label:{label}"]["pattern_id"],
                "delayed_all_stats_by_club_attribute",
            )
        self.assertIn("SCHEDULE_EFFECT", default_dsl_registry().names)

    def test_source_shot_creates_one_delayed_effect_without_changing_current_stats(self):
        result = self.schedule(
            self.bag("divebomb", "jumpstart", "ember"),
            "divebomb",
            "chains_into_putters",
        )
        self.assertEqual(result.final_stats, result.base_stats)
        self.assertEqual(len(result.scheduled_effects), 1)
        delayed = result.scheduled_effects[0]
        self.assertEqual(delayed.trigger.parameters, {"field": "club_type", "value": "putter"})
        self.assertEqual(delayed.effect.parameters, {"amount": 6.0})
        self.assertEqual(result.pending_effects, result.scheduled_effects)

    def test_ability_does_not_schedule_when_its_source_is_not_current(self):
        bag = self.bag("divebomb", "jumpstart", "ember")
        state = build_game_state(bag, CATALOG, 12, "jumpstart")
        result = RuleEngine().evaluate(
            state,
            (self.effect(state, "divebomb", "chains_into_putters"),),
            mode=EvaluationMode.STRICT,
        )
        self.assertEqual(result.scheduled_effects, ())
        rendered = render_explain_entries(result.explain)
        self.assertIn("source Divebomb is not the current club; no delayed effect scheduled", rendered)

    def test_incompatible_club_does_not_trigger_and_effect_remains_pending(self):
        bag = self.bag("divebomb", "jumpstart", "ember")
        first = self.schedule(bag, "divebomb", "chains_into_putters")
        state = build_game_state(bag, CATALOG, 12, "jumpstart", first.pending_effects)
        result = RuleEngine().evaluate(state, (), mode=EvaluationMode.STRICT)
        self.assertEqual(result.final_stats, result.base_stats)
        self.assertEqual(result.pending_effects, first.pending_effects)
        self.assertEqual(result.consumed_effect_ids, ())
        self.assertIn("effect remains pending", render_explain_entries(result.explain))

    def test_brand_type_and_putter_filters_trigger_the_same_generic_effect(self):
        cases = (
            (self.bag("kinship", "steadfast"), "kinship", "chains_into_willoughsby", "steadfast"),
            (self.bag("outset", "steadfast"), "outset", "chains_into_wedges", "steadfast"),
            (self.bag("conqueror", "ember"), "conqueror", "chains_into_putters", "ember"),
        )
        for bag, source, label, target in cases:
            with self.subTest(label=label):
                first = self.schedule(bag, source, label)
                state = build_game_state(bag, CATALOG, 12, target, first.pending_effects)
                result = RuleEngine().evaluate(state, (), mode=EvaluationMode.STRICT)
                available = state.current_entry.club.available_stats_at(state.current_entry.level)
                for stat, base_value in result.base_stats.as_dict().items():
                    expected = base_value + 6 if stat in available else base_value
                    self.assertEqual(result.final_stats.as_dict()[stat], expected)
                self.assertEqual(result.pending_effects, ())
                self.assertEqual(result.consumed_effect_ids, (first.pending_effects[0].identifier,))

    def test_consumed_effect_cannot_apply_twice(self):
        bag = self.bag("divebomb", "ember")
        first = self.schedule(bag, "divebomb", "chains_into_putters")
        target = build_game_state(bag, CATALOG, 12, "ember", first.pending_effects)
        resolved = RuleEngine().evaluate(target, (), mode=EvaluationMode.STRICT)
        replay = build_game_state(bag, CATALOG, 12, "ember", resolved.pending_effects)
        replayed = RuleEngine().evaluate(replay, (), mode=EvaluationMode.STRICT)
        self.assertEqual(replayed.final_stats, replayed.base_stats)
        self.assertEqual(replayed.consumed_effect_ids, ())

    def test_putter_bonus_changes_only_stats_defined_by_official_catalog(self):
        bag = self.bag("divebomb", "ember")
        first = self.schedule(bag, "divebomb", "chains_into_putters")
        target = build_game_state(bag, CATALOG, 12, "ember", first.pending_effects)
        result = RuleEngine().evaluate(target, (), mode=EvaluationMode.STRICT)
        self.assertEqual(result.base_stats.as_dict(), {"power": 5.0, "control": 13.0, "spin": 0.0})
        self.assertEqual(result.final_stats.as_dict(), {"power": 11.0, "control": 19.0, "spin": 0.0})

    def test_strict_and_partial_modes_schedule_the_same_effect(self):
        bag = self.bag("kinship", "steadfast")
        for mode in (EvaluationMode.STRICT, EvaluationMode.PARTIAL):
            with self.subTest(mode=mode):
                result = self.schedule(bag, "kinship", "chains_into_willoughsby", mode=mode)
                self.assertTrue(result.complete)
                self.assertEqual(len(result.scheduled_effects), 1)
                self.assertEqual(result.unresolved, ())

    def test_compare_bags_exposes_scheduled_chain_and_attributed_contribution(self):
        comparison = compare_saved_bags(
            "par3_divebomb",
            "par3_high_flight",
            level=12,
            current_position=1,
            mode=EvaluationMode.PARTIAL,
            user_dir=USER_DIR,
            catalog_path=CATALOG,
        )
        self.assertEqual(len(comparison.left.scheduled_effects), 1)
        self.assertEqual(comparison.right.scheduled_effects, ())
        contribution = next(
            item for item in comparison.left.ability_contributions
            if item.ability_id == "divebomb__chains_into_putters"
        )
        self.assertTrue(contribution.applied)
        self.assertEqual(
            contribution.scheduled_effect_ids,
            ("divebomb__chains_into_putters:next-compatible-shot",),
        )
        self.assertEqual(contribution.unresolved, ())
        rendered = render_bag_comparison(comparison)
        self.assertIn("Scheduled effects - left (1)", rendered)
        self.assertIn("club_type=putter", rendered)

    def test_resolution_explain_matches_golden(self):
        bag = self.bag("divebomb", "ember")
        first = self.schedule(bag, "divebomb", "chains_into_putters")
        target = build_game_state(bag, CATALOG, 12, "ember", first.pending_effects)
        result = RuleEngine().evaluate(target, (), mode=EvaluationMode.STRICT)
        self.assertEqual(
            render_explain_entries(result.explain) + "\n",
            GOLDEN.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
