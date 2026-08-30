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
