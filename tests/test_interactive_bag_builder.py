from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from pga_shootout.strategy_optimizer import (
    StrategyOptimizationError,
    StrategyOptimizationRequest,
    StrategyOptimizer,
)


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def _run(
    strategy_id: str = "par3",
    roles: tuple[tuple[str, str], ...] = (("high_flight", "attack"),),
    minimums: tuple[tuple[str, str, float], ...] = (),
    locks: tuple[tuple[int, str], ...] = (),
):
    optimizer = StrategyOptimizer(
        user_data_path=ROOT / "data" / "pga_shootout.sqlite",
        catalog_path=ROOT / "data" / "normalized" / "clubs_official.json",
        strategy_registry_path=ROOT / "data" / "strategies" / "strategies.json",
    )
    grouped: dict[str, dict[str, float]] = {}
    for step, metric, value in minimums:
        grouped.setdefault(step, {})[metric] = value
    return optimizer.optimize(StrategyOptimizationRequest(
        strategy_id,
        search_mode="interactive_builder",
        club_roles=dict(roles),
        metric_minimums=grouped,
        locked_positions=dict(locks),
        primary_step_id="drive" if strategy_id in {"par4_long", "par5"} else "attack",
        limit=10,
        max_evaluations=1000,
    ))


def _active_step(candidate, step_id):
    club_id = candidate.active_assignments[step_id]
    club = next(item for item in candidate.clubs if item.club_id == club_id)
    return next(item for item in club.steps if item.step_id == step_id)


def _best_metric(result, step_id, metric):
    return max(_active_step(item, step_id).final_stats[metric] for item in result.retained_results)


def test_one_required_active_club_and_power_tier_feedback():
    result = _run()
    assert all("high_flight" in item.composition for item in result.retained_results)
    assert all(item.active_assignments["attack"] == "high_flight" for item in result.retained_results)
    assert result.retained_results[0].optimization_badges == ("MEILLEURE PUISSANCE TROUVÉE",)
    assert any("POUR -" in badge for item in result.retained_results for badge in item.optimization_badges)
    assert all(item.metric_deltas_from_power_max is not None for item in result.retained_results)


def test_two_required_clubs_can_have_distinct_active_roles():
    result = _run(roles=(("high_flight", "attack"), ("ember", "putt")))
    assert all({"high_flight", "ember"}.issubset(item.composition) for item in result.retained_results)
    assert all(item.active_assignments == {"attack": "high_flight", "putt": "ember"} for item in result.retained_results)


def test_three_required_clubs_optimize_only_remaining_places():
    result = _run(roles=(("high_flight", "attack"), ("ember", "putt"), ("maelstrom", "support")))
    assert all({"high_flight", "ember", "maelstrom"}.issubset(item.composition) for item in result.retained_results)
    assert all(item.active_assignments["putt"] == "ember" for item in result.retained_results)
    assert all("maelstrom" not in item.active_assignments.values() for item in result.retained_results)


def test_automatic_role_and_two_putters_are_allowed():
    result = _run(roles=(("high_flight", "attack"), ("ember", "support"), ("homestead", "putt")))
    assert result.retained_results
    assert all(item.active_assignments["putt"] == "homestead" for item in result.retained_results)
    assert all({"ember", "homestead"}.issubset(item.composition) for item in result.retained_results)


def test_automatic_role_can_choose_active_or_support_without_club_specific_code():
    result = _run(roles=(("wave", "auto"),))
    assert result.retained_results
    assert all("wave" in item.composition for item in result.retained_results)
    assert any(item.unresolved_abilities for item in result.retained_results)


def test_position_lock_is_respected_and_free_position_is_reoptimized():
    locked = _run(roles=(("high_flight", "attack"), ("ember", "putt")), locks=((4, "ember"),))
    assert locked.retained_results
    assert all(item.composition[3] == "ember" for item in locked.retained_results)
    free = _run(roles=(("high_flight", "attack"), ("ember", "putt")))
    assert any(item.composition.index("ember") != 3 for item in free.retained_results)


def test_control_and_spin_minimums_filter_final_values_together():
    result = _run(
        roles=(("high_flight", "attack"), ("ember", "putt")),
        minimums=(("attack", "control", 12.0), ("attack", "spin", 7.0)),
    )
    assert result.criteria_satisfied
    assert all(_active_step(item, "attack").final_stats["control"] >= 12 for item in result.retained_results)
    assert all(_active_step(item, "attack").final_stats["spin"] >= 7 for item in result.retained_results)


def test_putt_minimums_use_final_chain_aware_evaluation_values():
    result = _run(
        roles=(("high_flight", "attack"), ("ember", "putt")),
        minimums=(("putt", "power", 10.0), ("putt", "control", 12.0)),
    )
    assert result.criteria_satisfied
    assert all(_active_step(item, "putt").final_stats["power"] >= 10 for item in result.retained_results)
    assert all(_active_step(item, "putt").final_stats["control"] >= 12 for item in result.retained_results)


def test_builder_can_keep_current_putter_while_reoptimizing_its_position():
    result = StrategyOptimizer(
        user_data_path=ROOT / "data" / "pga_shootout.sqlite",
        catalog_path=ROOT / "data" / "normalized" / "clubs_official.json",
        strategy_registry_path=ROOT / "data" / "strategies" / "strategies.json",
    ).optimize(StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder", target_bag_id="par3_high_flight",
        club_roles={"high_flight": "attack"}, keep_current_putter=True,
        primary_step_id="attack", limit=5, max_evaluations=300,
    ))
    assert result.retained_results
    assert all(item.active_assignments["putt"] == "ember" for item in result.retained_results)


def test_impossible_minimums_are_not_silently_relaxed():
    result = _run(minimums=(("attack", "control", 99.0), ("putt", "power", 99.0)))
    assert not result.criteria_satisfied
    assert result.requested_minimums == {"attack": {"control": 99.0}, "putt": {"power": 99.0}}
    assert result.closest_candidate_ids
    assert any("Aucun sac ne satisfait" in warning for warning in result.warnings)


def test_three_step_strategy_accepts_three_explicit_active_clubs():
    result = _run(
        "par5",
        (("high_flight", "drive"), ("divebomb", "approach"), ("ember", "putt")),
    )
    assert result.retained_results
    assert all(item.active_assignments == {
        "drive": "high_flight", "approach": "divebomb", "putt": "ember",
    } for item in result.retained_results)
    assert result.search.total_seconds < 15


def test_incompatible_role_is_rejected_factually():
    with pytest.raises(StrategyOptimizationError, match="compatible"):
        _run(roles=(("high_flight", "putt"),))


def test_attainable_ranges_only_contain_observed_candidate_values():
    result = _run()
    assert result.attainable_ranges["attack"]["control"]
    assert result.attainable_ranges["putt"]["power"]
    assert tuple(result.attainable_ranges["attack"]["control"]) == tuple(sorted(result.attainable_ranges["attack"]["control"]))


def test_bounce_reduction_preference_is_data_driven_by_function_and_club_type():
    policy = json.loads((ROOT / "data" / "strategies" / "optimization_policies.json").read_text(encoding="utf-8"))
    progression = policy["shot_functions"]["advance_toward_target"]
    attack = policy["shot_functions"]["reach_target_zone"]
    assert progression["user_function"] == "progression"
    assert progression["important_landing_metrics_by_club_type"] == {}
    for club_type in ("driver", "wood", "hybrid"):
        assert attack["important_landing_metrics_by_club_type"][club_type] == ["bounce_reduction_percent"]
    assert "iron" not in attack["important_landing_metrics_by_club_type"]


def test_hybrid_green_attack_can_retain_a_distinct_landing_variant_but_progression_does_not():
    attack = _run(roles=(("high_flight", "attack"), ("maelstrom", "support")))
    assert any(item.identifier == "landing_profile" for item in attack.result_families)
    progression = _run(
        "par5",
        (("high_flight", "drive"), ("maelstrom", "support"), ("ember", "putt")),
    )
    assert all(item.identifier != "landing_profile" for item in progression.result_families)


def test_more_imposed_roles_reduce_the_active_assignment_search_space():
    one = _run()
    two = _run(roles=(("high_flight", "attack"), ("ember", "putt")))
    three = _run(roles=(("high_flight", "attack"), ("ember", "putt"), ("maelstrom", "support")))
    assert two.search.active_assignments_theoretical < one.search.active_assignments_theoretical
    assert three.search.active_assignments_theoretical == two.search.active_assignments_theoretical


def test_real_saved_bags_are_injected_and_remain_visible_as_regression_controls():
    high_flight = _run()
    reference = next(
        item for item in high_flight.retained_results
        if item.composition == ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm")
    )
    assert _active_step(reference, "attack").final_stats["power"] > 0
    assert reference.origin == "reference_bag"
    assert high_flight.search.saved_bag_candidates_injected > 0

    divebomb = _run(roles=(("divebomb", "attack"),))
    reference = next(
        item for item in divebomb.retained_results
        if item.composition == ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm")
    )
    assert _active_step(reference, "attack").final_stats["power"] > 0


def test_required_club_monotonicity_for_real_bags_and_identical_objectives():
    high_flight = _run()
    high_flight_ember = _run(roles=(("high_flight", "attack"), ("ember", "putt")))
    high_flight_ember_maelstrom = _run(roles=(
        ("high_flight", "attack"), ("ember", "putt"), ("maelstrom", "support"),
    ))
    assert _best_metric(high_flight, "attack", "power") >= _best_metric(high_flight_ember, "attack", "power")
    assert _best_metric(high_flight_ember, "attack", "power") >= _best_metric(
        high_flight_ember_maelstrom, "attack", "power",
    )

    divebomb = _run(roles=(("divebomb", "attack"),))
    divebomb_ember = _run(roles=(("divebomb", "attack"), ("ember", "putt")))
    assert _best_metric(divebomb, "attack", "power") >= _best_metric(divebomb_ember, "attack", "power")


@pytest.mark.parametrize("minimums", (
    (("attack", "control", 10.0),),
    (("attack", "spin", 10.0),),
    (("attack", "control", 10.0), ("attack", "spin", 10.0)),
    (("putt", "power", 10.0), ("putt", "control", 12.0)),
))
def test_required_club_monotonicity_with_identical_metric_minimums(minimums):
    broad = _run(minimums=minimums)
    constrained = _run(
        roles=(("high_flight", "attack"), ("ember", "putt")),
        minimums=minimums,
    )
    assert broad.criteria_satisfied == constrained.criteria_satisfied
    assert _best_metric(broad, "attack", "power") >= _best_metric(constrained, "attack", "power")


def test_more_constrained_discovery_is_reused_by_a_broader_query_for_three_steps():
    service = StrategyOptimizer(
        user_data_path=ROOT / "data" / "pga_shootout.sqlite",
        catalog_path=ROOT / "data" / "normalized" / "clubs_official.json",
        strategy_registry_path=ROOT / "data" / "strategies" / "strategies.json",
    )

    def run(roles):
        return service.optimize(StrategyOptimizationRequest(
            "par5", search_mode="interactive_builder", club_roles=roles,
            primary_step_id="drive", limit=5, max_evaluations=50,
        ))

    constrained = run({"high_flight": "drive", "divebomb": "approach", "ember": "putt"})
    broader = run({"high_flight": "drive", "divebomb": "approach"})
    assert broader.search.known_candidates_injected > 0
    assert _best_metric(broader, "drive", "power") >= _best_metric(constrained, "drive", "power")


def test_bounded_search_diagnostic_separates_safe_heuristic_and_budget_reductions():
    result = _run()
    assert result.search.optimality_status == "best_found"
    assert result.search.safety_limit_reached
    assert result.search.removal_reasons is not None
    assert set(result.search.removal_reasons) == {
        "safe_order_equivalence", "position_constraint",
        "heuristic_support_pool_cap", "budget_limit",
    }


def test_session_candidates_are_not_reused_after_inventory_level_changes(tmp_path):
    database = tmp_path / "inventory.sqlite"
    shutil.copy2(ROOT / "data" / "pga_shootout.sqlite", database)
    service = StrategyOptimizer(
        user_data_path=database,
        catalog_path=ROOT / "data" / "normalized" / "clubs_official.json",
        strategy_registry_path=ROOT / "data" / "strategies" / "strategies.json",
    )
    request = StrategyOptimizationRequest(
        "par3", search_mode="interactive_builder",
        club_roles={"high_flight": "attack", "ember": "putt"},
        primary_step_id="attack", limit=5, max_evaluations=50,
    )
    service.optimize(request)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE user_clubs SET current_level = 7 WHERE club_id = 'high_flight'")
    refreshed = service.optimize(replace(request, club_roles={"high_flight": "attack"}))
    assert refreshed.search.known_candidates_injected == 0
