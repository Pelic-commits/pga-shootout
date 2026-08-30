"""Generic transformation contract: synthetic owners, effects and positions only."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from pga_shootout.bag_evaluation import _semantic_program
from pga_shootout.engine import RuleEngine, EvaluationError
from pga_shootout.models import Ability, Bag, BagEntry, Club, Effect, GameState, Stats, EvaluationMode, Condition


def club(identifier, abilities=(), kind="iron"):
    return Club(identifier, identifier, "test", kind, {1: Stats(10, 5, 3)}, tuple(abilities))


def amplifier(identifier="c", direction="left", wrap=False):
    patterns = json.loads(Path("data/normalized/semantic_map.json").read_text(encoding="utf-8"))["patterns"]
    program = _semantic_program({"pattern_id": "adjacent_ability_amplifier",
                                 "pattern_parameters": {"directions": [direction], "wrap": wrap}}, patterns)
    source = f"{identifier} / {identifier}__amplify"
    effect = Effect("dsl_pipeline", {"phase": "ability_transform", "program": program,
        "source_club_id": identifier, "ability_source": source, "ability_level": 1, "level_value": 2}, source=source)
    return club(identifier, (Ability(identifier + "__amplify", "Amplify", (effect,)),))


def bonus(identifier="b", metric="power", amount=3, selection="SELECT_ADJACENT", *, condition=None):
    source = f"{identifier} / {identifier}__{metric}"
    program = {"version": "1.0", "nodes": [
        {"id": "self", "operation": "SELECT_SELF", "inputs": {"source_club_id": {"from": "effect.source_club_id"}}},
        {"id": "targets", "operation": selection, "inputs": {"origin": {"from": "self.club"}, "source_club_id": {"from": "self.club"}}, "parameters": {"directions": ["left"]}},
        {"id": "each", "operation": "FOR_EACH", "inputs": {"items": {"from": "targets.clubs"}}, "parameters": {
            "binding": "target", "program": {"nodes": [
                {"id": "effect", "operation": "ADD_STAT" if metric in {"power", "control", "spin"} else "ADD_MODIFIER",
                 "parameters": {"stat" if metric in {"power", "control", "spin"} else "modifier": metric},
                 "inputs": {"target": {"from": "iteration.target"}, "delta": amount}},
            ]}}},
    ]}
    effect = Effect("dsl_pipeline", {"program": program, "source_club_id": identifier}, condition or Condition("always"), source)
    return Ability(identifier + "__" + metric, metric, (effect,))


def evaluate(clubs, current="a", mode=EvaluationMode.PARTIAL, reverse=False, pending=()):
    state = GameState(Bag(tuple(BagEntry(item, 1) for item in clubs)), current, pending_effects=list(pending))
    effects = tuple(effect for item in clubs for ability in item.abilities for effect in ability.effects)
    result = RuleEngine().evaluate(state, tuple(reversed(effects)) if reverse else effects, mode=mode)
    return state, result


def facts(result):
    return [entry.outputs for entry in result.explain if entry.mechanism == "ABILITY_AMPLIFICATION"]


@pytest.mark.parametrize("metric,amount,expected", [("power", 3, 16), ("control", 2, 9), ("spin", 2, 7)])
@pytest.mark.parametrize("mode", [EvaluationMode.STRICT, EvaluationMode.PARTIAL])
def test_additive_magnitude_not_final_stats(metric, amount, expected, mode):
    owner = club("b", (bonus(metric=metric, amount=amount),))
    _, result = evaluate((club("a"), owner, amplifier()), mode=mode)
    assert result.complete and getattr(result.final_stats, metric) == expected
    resolved = next(item for item in facts(result) if item["status"] == "resolved")
    assert resolved["original"] == amount and resolved["amplified"] == amount * 2
    assert resolved["target_club_id"] == "b" and resolved["final_target"] == "a"
    assert sum(entry.modification.get(metric, 0) for entry in result.explain if entry.applied and entry.mechanism != "dsl_pipeline") == amount * 2


def test_transform_precedes_resolution_regardless_of_effect_list_order():
    clubs = (club("a"), club("b", (bonus(),)), amplifier())
    assert evaluate(clubs)[1].final_stats == evaluate(clubs, reverse=True)[1].final_stats
    # Inputs are immutable; a second evaluation cannot amplify the first one's result.
    assert evaluate(clubs)[1].final_stats.power == 16


def test_multiple_active_abilities_all_receive_one_transformation():
    _, result = evaluate((club("a"), club("b", (bonus(), bonus(metric="control", amount=2))), amplifier()))
    assert result.final_stats == Stats(16, 9, 3)
    assert len([item for item in facts(result) if item["status"] == "resolved"]) == 2


def test_right_direction_and_wrong_position():
    owner = club("b", (bonus(selection="SELECT_ALL"),))
    assert evaluate((club("a"), amplifier(direction="right"), owner))[1].final_stats.power == 16
    assert evaluate((club("a"), amplifier(), owner))[1].final_stats.power == 13


def test_boundary_wrap_is_explicit_and_never_self_selects_singleton():
    owner = club("b", (bonus(selection="SELECT_ALL"),))
    assert evaluate((amplifier(), club("a"), owner))[1].final_stats.power == 13
    assert evaluate((amplifier(wrap=True), club("a"), owner))[1].final_stats.power == 16
    _, singleton = evaluate((amplifier(wrap=True),), current="c")
    assert singleton.complete and not facts(singleton)


def test_original_condition_and_transform_condition_are_preserved():
    disabled = Condition("current_club_attribute_equals", {"field": "club_type", "value": "putter"})
    owner = club("b", (bonus(condition=disabled),))
    assert evaluate((club("a"), owner, amplifier()))[1].final_stats.power == 10
    amp = amplifier()
    ability = amp.abilities[0]
    amp = replace(amp, abilities=(replace(ability, effects=(replace(ability.effects[0], condition=disabled),)),))
    assert evaluate((club("a"), club("b", (bonus(),)), amp))[1].final_stats.power == 13


def test_unimplemented_ability_stays_unknown_but_identifies_amplification():
    owner = club("b", (Ability("b__unknown", "unknown", (Effect("unsupported:unknown", source="b / b__unknown"),)), bonus()))
    _, result = evaluate((club("a"), owner, amplifier()))
    assert not result.complete and result.final_stats.power == 16
    assert any(item["status"] == "unresolved" and item["multiplier"] == 2 for item in facts(result))
    with pytest.raises(EvaluationError):
        evaluate((club("a"), owner, amplifier()), mode=EvaluationMode.STRICT)


@pytest.mark.parametrize("metric", ["bounce_reduction_percent", "wind_resistance_percent", "loft_angle_degrees", "fade_draw_multiplier"])
def test_numeric_modifier_is_not_assumed_additive_under_extra_instance(metric):
    _, result = evaluate((club("a"), club("b", (bonus(metric=metric, amount=20),)), amplifier()))
    assert result.modifiers[metric] == 20
    assert not result.complete
    assert any(item["status"] == "unresolved" for item in facts(result))


def test_overlapping_amplifiers_do_not_guess_x3_or_x4():
    _, result = evaluate((club("a"), amplifier("left", "right"), club("b", (bonus(selection="SELECT_ALL"),)), amplifier("right")))
    assert result.final_stats.power == 13
    assert any("stacking" in message for message in result.unresolved)


def test_recursive_transformations_terminate_and_remain_unresolved():
    _, result = evaluate((club("a"), amplifier("left", "right"), amplifier("right")))
    assert not result.complete and result.final_stats.power == 10
    assert any("recursion" in message for message in result.unresolved)
    assert len(result.explain) < 30


def test_renaming_all_clubs_does_not_change_calculation():
    def run(a, b, c):
        return evaluate((club(a), club(b, (bonus(identifier=b),)), amplifier(c)), current=a)[1].final_stats
    assert run("a", "b", "c") == run("new_active", "new_owner", "new_amplifier")


def test_chain_payload_is_amplified_once_and_provenance_survives_consumption():
    source = "b / b__chain"
    program = {"nodes": [{"id": "schedule", "operation": "SCHEDULE_EFFECT",
        "inputs": {"source": "b", "amount": 2, "ability_id": "b__chain", "ability_source": source},
        "parameters": {"filter_field": "club_type", "filter_value": "putter"}}]}
    owner = club("b", (Ability("b__chain", "chain", (Effect("dsl_pipeline", {"program": program}, source=source),)),))
    clubs = (club("a", kind="putter"), owner, amplifier())
    _, shot = evaluate(clubs, current="b")
    assert shot.scheduled_effects[0].effect.parameters["amount"] == 4
    _, next_shot = evaluate(clubs, pending=shot.pending_effects)
    assert next_shot.final_stats == Stats(14, 9, 7)
    assert next_shot.consumed_effect_ids and not next_shot.pending_effects
    assert any(item["status"] == "resolved" and item["original"] == 2 and item["amplified"] == 4 for item in facts(next_shot))
    assert evaluate(clubs, pending=next_shot.pending_effects)[1].final_stats == Stats(10, 5, 3)


def test_comparison_contributions_preserve_provenance_without_double_counting():
    from pga_shootout.bag_comparison import summarize_bag_evaluation
    from pga_shootout.bag_evaluation import BagEvaluation
    from pga_shootout.user_data import SavedBag
    clubs = (club("a"), club("b", (bonus(),)), amplifier())
    state, result = evaluate(clubs)
    evaluation = BagEvaluation(SavedBag("test", "test", "test", ("a", "b", "c"), ()), state, result,
                               EvaluationMode.PARTIAL, False, RuleEngine().mechanisms.names)
    summary = summarize_bag_evaluation(evaluation, 1)
    assert summary.ability_impact["power"] == 6
    assert sum(item.modification["power"] for item in summary.ability_contributions) == 6
    owner, amp = summary.ability_contributions
    assert owner.modification["power"] == 6 and amp.modification["power"] == 0
    assert amp.applied and amp.amplifications
    assert amp.amplifications[-1] == {
        "source_club_id": "c", "target_club_id": "b", "multiplier": 2.0, "source": "c / c__amplify",
        "target_ability_id": "b__power", "target_ability_source": "b / b__power", "status": "resolved",
        "original": 3, "amplified": 6.0, "metric": "power", "final_target": "a", "operation": "ADD_STAT",
    }


def test_temporary_effect_is_not_mistaken_for_a_native_ability():
    clubs = (club("a"), club("b", (bonus(),)), amplifier())
    state = GameState(Bag(tuple(BagEntry(item, 1) for item in clubs)), "a")
    effects = tuple(effect for item in clubs for ability in item.abilities for effect in ability.effects)
    state.active_bonuses.append(Effect("add_stat", {"stat": "control", "amount": 1}, source="b / b__power"))
    result = RuleEngine().evaluate(state, effects, mode=EvaluationMode.PARTIAL)
    assert result.final_stats == Stats(16, 6, 3)
    assert any("temporary or non-native" in value for value in result.unresolved)
