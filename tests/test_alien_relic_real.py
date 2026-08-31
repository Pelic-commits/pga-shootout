"""Official-data smoke tests; all amplification rules live in generic tests."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from pga_shootout.bag_comparison import ability_contributions
from pga_shootout.bag_evaluation import build_game_state, BagEvaluation
from pga_shootout.engine import RuleEngine
from pga_shootout.models import EvaluationMode
from pga_shootout.user_data import SavedBag, load_user_data


CATALOG = Path("data/normalized/clubs_official.json")


def levels():
    return {item.club_id: item.current_level for item in load_user_data("data/pga_shootout.sqlite").inventory.entries}


@pytest.mark.parametrize("neighbor,label,metric", [
    ("jumpstart", "power_boost", "power"), ("galvanizer", "control_boost", "control"),
    ("commonlaw", "bag_control", "control"),
])
def test_real_levels_amplify_known_directional_and_bag_bonuses(neighbor, label, metric):
    bag = SavedBag("smoke", "smoke", "test", ("blacksmith", neighbor, "meteor"), ())
    state = build_game_state(bag, CATALOG, levels(), "blacksmith", terrain="tee")
    effects = tuple(effect for entry in state.bag.entries for ability in entry.club.abilities for effect in ability.effects)
    engine = RuleEngine()
    before = engine.evaluate(state, tuple(effect for effect in effects if effect.parameters.get("phase") != "ability_transform"), mode=EvaluationMode.PARTIAL)
    after = engine.evaluate(state, effects, mode=EvaluationMode.PARTIAL)
    def contribution(result):
        evaluation = BagEvaluation(bag, state, result, EvaluationMode.PARTIAL, False, engine.mechanisms.names)
        return next(item for item in ability_contributions(evaluation) if item.ability_id == neighbor + "__" + label)
    assert contribution(after).modification[metric] == contribution(before).modification[metric] * 2
    assert contribution(before).modification[metric] > 0
    provenance = [entry.outputs for entry in after.explain if entry.mechanism == "ABILITY_AMPLIFICATION" and entry.outputs.get("status") == "resolved"]
    assert any(item["target_club_id"] == neighbor and item["final_target"] == "blacksmith" for item in provenance)


def test_current_level_activation_and_future_right_wrap_are_only_data():
    bag = SavedBag("levels", "levels", "test", ("meteor", "blacksmith", "jumpstart"), ())
    current = levels()
    assert current["meteor"] == 9
    for level, expected in [(9, {"alien_relic_left"}), (10, {"alien_relic_left", "alien_relic_right"}),
                            ("Elite", {"alien_relic_left", "alien_relic_right", "alien_world"})]:
        state = build_game_state(bag, CATALOG, {**current, "meteor": level}, "blacksmith", terrain="tee")
        abilities = state.bag.get("meteor").club.abilities
        assert {ability.text for ability in abilities} == expected
        left = next(ability.effects[0] for ability in abilities if ability.text == "alien_relic_left")
        node = next(node for node in left.parameters["program"]["nodes"] if node["operation"] == "SELECT_ADJACENT")
        assert node["parameters"]["wrap"] is (level == "Elite")
        boost = next(ability.effects[0] for ability in state.bag.get("jumpstart").club.abilities if ability.text == "power_boost")
        result = RuleEngine().evaluate(state, (left, boost), mode=EvaluationMode.STRICT)
        delta = result.final_stats.power - result.base_stats.power
        assert delta == boost.parameters["level_value"] * (2 if level == "Elite" else 1)


def test_catalogue_coverage_is_partial_not_unconditionally_complete():
    from pga_shootout.bag_evaluation import semantic_support
    from pga_shootout.registry import default_mechanism_registry
    semantic = json.loads(CATALOG.with_name("semantic_map.json").read_text(encoding="utf-8"))
    for label in ("alien_relic_left", "alien_relic_right"):
        full, partial, _ = semantic_support(semantic["entries"]["label:" + label], semantic["patterns"], default_mechanism_registry().names)
        assert not full and partial


def test_rule_and_dsl_code_has_no_special_case_real_club_names():
    for name in ("engine.py", "dsl.py", "ability_amplification.py", "strategy_optimizer.py"):
        text = Path("src/pga_shootout", name).read_text(encoding="utf-8").casefold()
        assert "meteor" not in text and "jumpstart" not in text and "alien_relic" not in text


@pytest.mark.parametrize("composition,current,owner,label,metric,normal", [
    (("high_flight", "maelstrom", "meteor"), "high_flight", "maelstrom", "bag_bounce_reduction", "bounce_reduction_percent", 12),
    (("high_flight", "cyclotron", "meteor"), "high_flight", "cyclotron", "bounce_reduction_boost", "bounce_reduction_percent", 16),
    (("high_flight", "rook", "meteor"), "high_flight", "rook", "bag_wind_resist", "wind_resistance_percent", 17),
    (("high_flight", "meteor", "blacksmith"), "high_flight", "high_flight", "wind_resist_75", "wind_resistance_percent", 75),
    (("sidewinder", "meteor", "blacksmith"), "sidewinder", "sidewinder", "groundspin_x3", "groundspin_multiplier", 3),
    (("meanderer", "meteor", "blacksmith"), "meanderer", "meanderer", "groundspin_x4", "groundspin_multiplier", 4),
])
def test_real_modifier_payloads_keep_their_own_level_and_target(composition, current, owner, label, metric, normal):
    inventory = load_user_data("data/pga_shootout.sqlite").inventory.entries
    assert all(next(item for item in inventory if item.club_id == club_id).unlocked for club_id in composition)
    state = build_game_state(SavedBag("modifiers", "modifiers", "test", composition, ()), CATALOG, levels(), current, terrain="tee")
    effects = tuple(effect for entry in state.bag.entries for ability in entry.club.abilities for effect in ability.effects)
    before = RuleEngine().evaluate(state, tuple(effect for effect in effects if effect.parameters.get("phase") != "ability_transform"), mode=EvaluationMode.PARTIAL)
    after = RuleEngine().evaluate(state, effects, mode=EvaluationMode.PARTIAL)
    records = [entry.outputs for entry in after.explain if entry.mechanism == "ABILITY_AMPLIFICATION"
               and entry.outputs.get("target_ability_id") == owner + "__" + label and entry.outputs.get("status") == "resolved"]
    assert len(records) == 1
    assert records[0]["original"] == normal and records[0]["amplified"] == normal * 2
    assert records[0]["metric"] == metric and records[0]["final_target"] == current
    assert records[0]["physical_interpretation"] == "not_modeled"
    assert after.modifiers[metric] - before.modifiers[metric] == normal


def test_current_left_amplifier_cannot_enable_rightmost_groundspin_condition():
    bag = SavedBag("position", "position", "test", ("high_flight", "gearshift", "meteor"), ())
    state = build_game_state(bag, CATALOG, levels(), "high_flight")
    effects = tuple(effect for entry in state.bag.entries for ability in entry.club.abilities for effect in ability.effects)
    result = RuleEngine().evaluate(state, effects, mode=EvaluationMode.PARTIAL)
    assert "groundspin_increase_percent" not in result.modifiers
    assert not any(entry.outputs.get("metric") == "groundspin_increase_percent" and entry.outputs.get("status") == "resolved" for entry in result.explain)
