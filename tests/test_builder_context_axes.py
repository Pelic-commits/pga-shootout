"""Synthetic DSL fixtures: selection policy changes, never game calculations."""

from dataclasses import replace
from pathlib import Path

import pytest

from pga_shootout.models import Ability, Club, Effect, EvaluationMode, Stats
from pga_shootout.optimizer_cards import club_projection, metric_changes, secondary_summary
from pga_shootout.strategy_optimizer import (
    CandidateSpec, StrategyOptimizer, StrategyOptimizationRequest, BuildFromScratchRequest,
    _RuntimeEvaluator, _attach_power_tier_deltas, _metric_qualifies_support,
)
from pga_shootout.user_data import load_user_data
from pga_shootout.strategy import StrategyRegistry


CATALOG = Path("data/normalized/clubs_official.json")


def synthetic_club(identifier, club_type="iron", **bonuses):
    abilities = []
    for metric, amount in bonuses.items():
        stat = metric in {"power", "control", "spin"}
        program = {"version": "1.0", "nodes": [
            {"id": "targets", "operation": "SELECT_ALL", "inputs": {}},
            {"id": "each", "operation": "FOR_EACH", "inputs": {"items": {"from": "targets.clubs"}},
             "parameters": {"binding": "target", "program": {"nodes": [
                 {"id": "apply", "operation": "ADD_STAT" if stat else "ADD_MODIFIER",
                  "inputs": {"target": {"from": "iteration.target"}, "delta": amount},
                  "parameters": {"stat" if stat else "modifier": metric}},
             ]}}},
        ]}
        ability_id = f"{identifier}__{metric}"
        abilities.append(Ability(ability_id, metric, (Effect("dsl_pipeline", {
            "source_club_id": identifier, "program": program,
        }, source=f"{identifier} / {ability_id}"),)))
    return Club(identifier, identifier, "fixture", club_type, {1: Stats(10, 5, 3)}, tuple(abilities))


def fixture(*, club_type="driver", context=None, bonuses=None):
    optimizer = StrategyOptimizer()
    strategy = StrategyRegistry.load(optimizer.registry_path).resolve("par3")
    attack, putt = strategy.definition.sequence
    attack = replace(attack, context=replace(attack.context, values={**attack.context.values, **(context or {})}))
    strategy = replace(strategy, definition=replace(strategy.definition, sequence=(attack, putt)))
    runtime = _RuntimeEvaluator(CATALOG, (), None)
    runtime.clubs = {club.identifier: club for club in (
        synthetic_club("active", club_type), synthetic_club("putter", "putter"),
        synthetic_club("filler_a"), synthetic_club("filler_b"),
        synthetic_club("power_support", power=2),
        synthetic_club("axis_support", **(bonuses or {"bounce_reduction_percent": 30})),
    )}
    runtime.levels = dict.fromkeys(runtime.clubs, 1)
    quick = tuple(optimizer._evaluate_quick(CandidateSpec(
        support, ("active", "putter", "filler_a", "filler_b", support),
        {"attack": "active", "putt": "putter"}, "build_from_scratch",
    ), strategy, runtime, EvaluationMode.PARTIAL) for support in ("power_support", "axis_support"))
    return optimizer, strategy, runtime, quick


def project(optimizer, strategy, runtime, quick, limit=5):
    families, retained, membership = optimizer._project_builder_families(
        quick, strategy, runtime, StrategyOptimizationRequest("par3", primary_step_id="attack"), limit,
    )
    detail = tuple(optimizer._detail(item, strategy, runtime, EvaluationMode.PARTIAL,
                                    membership[item.spec.identifier]) for item in retained)
    return families, _attach_power_tier_deltas(detail, strategy, "attack")


def test_driver_power_vs_landing_uses_actual_dsl_and_exposes_tradeoff():
    optimizer, strategy, runtime, quick = fixture()
    families, candidates = project(optimizer, strategy, runtime, quick, limit=2)
    assert [item.identifier for item in families] == ["power_max", "landing_profile"]
    assert len(candidates) == 2
    landing = candidates[1]
    assert landing.metric_deltas_from_power_max["attack.power"] == -2
    assert landing.metric_deltas_from_power_max["attack.bounce_reduction_percent"] == 30
    assert not hasattr(landing, "score")
    support = next(item for item in landing.clubs if item.club_id == "axis_support")
    assert support.role == "support"
    assert any("+30 % Bounce Reduction → active" in text for text in club_projection(support, landing, {})["reasons"])
    leaves = quick[1].steps[0].summary.evaluation.result.explain
    assert any(entry.mechanism == "ADD_MODIFIER" and entry.applied for entry in leaves)
    assert runtime.clubs["active"].stats_at(1).power == 10


@pytest.mark.parametrize("club_type", ["iron", "wedge"])
def test_secondary_landing_not_blindly_promoted(club_type):
    optimizer, strategy, runtime, quick = fixture(club_type=club_type)
    families, candidates = project(optimizer, strategy, runtime, quick)
    assert [item.identifier for item in families] == ["power_max"]
    assert candidates[0].candidate_id == "power_support"
    assert not _metric_qualifies_support(quick[1].steps[0].step, "bounce_reduction_percent", optimizer.metric_semantics)


def test_explicit_landing_context_can_qualify_an_iron():
    families, candidates = project(*fixture(club_type="iron", context={"landing_goal": "reduce_roll"}))
    assert "landing_profile" in {item.identifier for item in families}


@pytest.mark.parametrize("wind,expected", [(False, False), (True, True)])
def test_wind_needs_explicit_context(wind, expected):
    optimizer, strategy, runtime, quick = fixture(
        club_type="iron", context={"wind_relation": "head_or_crosswind"} if wind else {},
        bonuses={"wind_resistance_percent": 30},
    )
    families, candidates = project(optimizer, strategy, runtime, quick)
    assert ("wind_profile" in {item.identifier for item in families}) is expected
    assert _metric_qualifies_support(quick[1].steps[0].step, "wind_resistance_percent", optimizer.metric_semantics) is expected
    if wind:
        assert candidates[1].metric_deltas_from_power_max["attack.wind_resistance_percent"] == 30
        assert candidates[1].metric_deltas_from_power_max["attack.power"] == -2
    else:
        assert all(item.candidate_id != "axis_support" for item in candidates)


def test_identical_winners_share_one_card_and_mixed_support_keeps_both_contributions():
    families, candidates = project(*fixture(context={"wind_relation": "head_or_crosswind"},
                                            bonuses={"bounce_reduction_percent": 30, "wind_resistance_percent": 25, "control": 1}))
    assert len(candidates) == 2
    mixed = candidates[1]
    assert {"landing_profile", "wind_profile"} <= set(mixed.result_family_ids)
    support = next(club for club in mixed.clubs if club.club_id == "axis_support")
    reasons = club_projection(support, mixed, {})["reasons"]
    assert "Bounce Reduction" in reasons[0] and "Wind Resistance" in reasons[1]
    assert any("+1 Control" in reason for reason in reasons)
    step = next(club for club in mixed.clubs if club.club_id == "active").steps[0]
    assert secondary_summary(step, complete=True) == ("Bounce Reduction 30 %", "Wind Resistance 25 %")


def test_unknown_never_becomes_zero_or_an_invented_delta():
    optimizer, strategy, runtime, quick = fixture()
    _, complete = project(optimizer, strategy, runtime, quick)
    partial = replace(complete[0], unresolved_abilities=("unqualified-copy",))
    candidates = _attach_power_tier_deltas((partial, complete[1]), strategy, "attack")
    assert candidates[1].metric_deltas_from_power_max["attack.bounce_reduction_percent"] is None
    assert any("écart indéterminé" in text for text in metric_changes(candidates[1], {}))
    step = partial.clubs[0].steps[0]
    assert secondary_summary(step, complete=False) == ("Bounce Reduction — %",)
    assert secondary_summary(step, complete=True) == ("Bounce Reduction 0 %",)
    assert not any("Wind Resistance" in text or "Putt" in text for text in metric_changes(candidates[1], {"putt": "Putt"})
                   if "indéterminé" in text)


def test_axes_are_reserved_before_filling_secondary_power_tiers():
    optimizer, strategy, runtime, quick = fixture()
    families, candidates = project(optimizer, strategy, runtime, quick, limit=1)
    assert len(candidates) == 1
    assert [item.identifier for item in families] == ["power_max"]


@pytest.mark.parametrize("identifier", ["meteor", "flashpoint"])
def test_real_owned_club_is_candidate_with_known_level_and_explicit_unknowns(identifier):
    inventory = load_user_data("data/pga_shootout.sqlite").inventory
    entry = next(item for item in inventory.entries if item.club_id == identifier)
    assert entry.unlocked and entry.current_level is not None
    runtime = _RuntimeEvaluator(CATALOG, inventory.entries, None)
    assert identifier in runtime.clubs and identifier in runtime.support_capable_ids
    result = StrategyOptimizer().build_from_scratch(BuildFromScratchRequest(
        "par3", identifier, club_roles={identifier: "attack"}, max_evaluations=30, limit=2,
    ))
    assert result.retained_results
    for candidate in result.retained_results:
        assert identifier in candidate.composition
        club = next(item for item in candidate.clubs if item.club_id == identifier)
        assert club.level == entry.current_level
        if identifier == "flashpoint":
            assert any(item.startswith(identifier + "__") for step in club.steps for item in step.unresolved_abilities)
            assert candidate.unresolved_abilities
        else:
            # A qualified amplifier with no left neighbor is now complete, not
            # permanently unknown merely because of the owning club identity.
            assert all("alien_world" not in item and "alien_relic_right" not in item
                       for step in club.steps for item in step.unresolved_abilities)


def test_no_real_club_name_added_to_generic_code():
    for path in (Path("src/pga_shootout/strategy_optimizer.py"), Path("src/pga_shootout/optimizer_cards.py")):
        text = path.read_text(encoding="utf-8").casefold()
        assert "flashpoint" not in text and "meteor" not in text
