from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from pga_shootout.models import EvaluationMode
from pga_shootout.strategy import StrategyRegistry
from pga_shootout.strategy_optimizer import (
    CandidateSpec,
    StrategyOptimizationRequest,
    StrategyOptimizer,
    _RuntimeEvaluator,
    render_strategy_optimization_json,
)
from pga_shootout.strategy_optimizer_gui import StrategyOptimizerPresenter
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


def optimizer(database=DATABASE):
    return StrategyOptimizer(
        user_data_path=database,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    )


@pytest.fixture(scope="module")
def results():
    service = optimizer()
    return {
        strategy_id: service.optimize(StrategyOptimizationRequest(
            strategy_id, limit=3, max_evaluations=600,
        ))
        for strategy_id in ("par3", "par4_short", "par4_long", "par5")
    }


def test_all_four_strategies_produce_functional_results_and_distinct_active_clubs(results):
    expected_steps = {"par3": 2, "par4_short": 2, "par4_long": 3, "par5": 3}
    for strategy_id, result in results.items():
        assert result.retained_results
        assert result.result_families
        for candidate in result.retained_results:
            assert len(candidate.active_assignments) == expected_steps[strategy_id]
            assert len(set(candidate.active_assignments.values())) == expected_steps[strategy_id]


def test_par3_reference_values_do_not_regress(results):
    result = results["par3"]
    divebomb = next(
        item for item in result.retained_results
        if item.active_assignments.get("attack") == "divebomb"
        and item.composition == ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm")
    )
    club = next(item for item in divebomb.clubs if item.club_id == "divebomb")
    attack = next(item for item in club.steps if item.step_id == "attack")
    assert attack.final_stats == {"power": 16.0, "control": 9.0, "spin": 9.0}


def test_derived_families_come_from_shot_functions_not_strategy_identifier(results):
    short_ids = {item.identifier for item in results["par4_short"].result_families}
    assert {"attack_max_power", "attack_power_control", "attack_landing_control", "putt_power_control"} <= short_ids
    for strategy_id in ("par4_long", "par5"):
        identifiers = {item.identifier for item in results[strategy_id].result_families}
        assert {
            "drive_max_power", "drive_power_control", "approach_max_power",
            "approach_power_control", "approach_iron", "approach_all_types",
            "putt_power_control", "whole_sequence",
        } <= identifiers


def test_metric_relevance_changes_by_shot_function_and_putt_stays_power_control_only():
    registry = StrategyRegistry.load(REGISTRY)
    strategy = registry.resolve("par4_long").definition
    drive, approach, putt = strategy.sequence
    assert drive.function.identifier == "advance_toward_target"
    assert approach.function.identifier == "reach_target_zone"
    assert putt.function.identifier == "finish"
    assert {item.metric for item in putt.metric_uses if item.usage == "objective"} == {"power", "control"}
    assert next(item for item in putt.metric_uses if item.metric == "spin").usage == "descriptive"
    assert next(item for item in approach.metric_uses if item.metric == "spin").usage == "objective"
    assert next(item for item in approach.metric_uses if item.metric == "loft_angle_degrees").usage == "descriptive"


def test_three_step_chain_survives_intermediate_shot_and_is_consumed_by_putt():
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par4_long")
    service = optimizer()
    spec = CandidateSpec(
        "three-step-chain",
        ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"),
        {"drive": "divebomb", "approach": "jumpstart", "putt": "ember"},
        "test",
    )
    quick = service._evaluate_quick(spec, strategy, runtime, EvaluationMode.PARTIAL)
    assert quick.steps[0].summary.evaluation.result.scheduled_effects
    assert quick.steps[1].summary.evaluation.result.pending_effects
    assert quick.steps[2].summary.evaluation.result.consumed_effect_ids


def test_supports_are_attributed_per_step_and_active_clubs_can_be_hybrid():
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par4_long")
    service = optimizer()
    spec = CandidateSpec(
        "multi-support",
        ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"),
        {"drive": "divebomb", "approach": "jumpstart", "putt": "ember"},
        "test",
    )
    detail = service._detail(
        service._evaluate_quick(spec, strategy, runtime, EvaluationMode.PARTIAL),
        strategy, runtime, EvaluationMode.PARTIAL,
    )
    roles = {item.club_id: item for item in detail.clubs}
    assert roles["divebomb"].role == "hybrid"
    assert roles["jumpstart"].role == "hybrid"
    assert set(roles["steadfast"].support_steps) == {"drive", "approach", "putt"}
    assert roles["sunstorm"].support_steps != roles["steadfast"].support_steps


def test_multi_step_order_changes_several_active_results_without_first_step_shortcut():
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par4_long")
    service = optimizer()
    assignments = {"drive": "divebomb", "approach": "jumpstart", "putt": "ember"}
    left = service._evaluate_quick(CandidateSpec(
        "left", ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"), assignments, "test",
    ), strategy, runtime, EvaluationMode.PARTIAL)
    right = service._evaluate_quick(CandidateSpec(
        "right", ("steadfast", "sunstorm", "ember", "divebomb", "jumpstart"), assignments, "test",
    ), strategy, runtime, EvaluationMode.PARTIAL)
    changed_steps = {
        step_id for step_id in assignments
        if any(
            left.objective_metrics.get(f"{step_id}:{metric}") != right.objective_metrics.get(f"{step_id}:{metric}")
            for metric in ("power", "control", "spin")
        )
    }
    assert len(changed_steps) >= 2


def test_approach_families_include_iron_and_non_iron_competitors(results):
    result = results["par5"]
    by_id = {item.candidate_id: item for item in result.retained_results}
    iron_family = next(item for item in result.result_families if item.identifier == "approach_iron")
    all_types = next(item for item in result.result_families if item.identifier == "approach_all_types")
    assert iron_family.candidate_ids
    assert all(
        next(club for club in by_id[candidate_id].clubs if club.club_id == by_id[candidate_id].active_assignments["approach"]).club_type == "iron"
        for candidate_id in iron_family.candidate_ids
    )
    assert any(
        next(club for club in by_id[candidate_id].clubs if club.club_id == by_id[candidate_id].active_assignments["approach"]).club_type != "iron"
        for candidate_id in all_types.candidate_ids
    )


def test_gearshift_can_be_putter_hybrid_or_directional_support_on_three_steps():
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par5")
    service = optimizer()
    active = CandidateSpec(
        "gear-active", ("gearshift", "high_flight", "cyclotron", "commonlaw", "homestead"),
        {"drive": "high_flight", "approach": "cyclotron", "putt": "gearshift"}, "test",
    )
    active_detail = service._detail(
        service._evaluate_quick(active, strategy, runtime, EvaluationMode.PARTIAL),
        strategy, runtime, EvaluationMode.PARTIAL,
    )
    gearshift = next(item for item in active_detail.clubs if item.club_id == "gearshift")
    assert gearshift.role == "hybrid"
    assert gearshift.active_steps == ("putt",)
    assert {"drive", "approach"} <= set(gearshift.support_steps)

    support = CandidateSpec(
        "gear-support", ("gearshift", "high_flight", "cyclotron", "commonlaw", "homestead"),
        {"drive": "high_flight", "approach": "cyclotron", "putt": "homestead"}, "test",
    )
    support_detail = service._detail(
        service._evaluate_quick(support, strategy, runtime, EvaluationMode.PARTIAL),
        strategy, runtime, EvaluationMode.PARTIAL,
    )
    gearshift = next(item for item in support_detail.clubs if item.club_id == "gearshift")
    assert gearshift.role == "support"
    assert {"drive", "approach", "putt"} <= set(gearshift.support_steps)


def test_three_step_local_improvement_exports_deltas_for_every_active_step(tmp_path):
    database = tmp_path / "local.sqlite"
    shutil.copyfile(DATABASE, database)
    allowed = ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm", "gearshift")
    placeholders = ",".join("?" for _ in allowed)
    with sqlite3.connect(database) as connection:
        connection.execute(f"UPDATE user_clubs SET unlocked = club_id IN ({placeholders})", allowed)
    result = optimizer(database).optimize(StrategyOptimizationRequest(
        "par4_long", limit=2, search_mode="improve_bag", target_bag_id="par3_high_flight",
        replacement_depth=1, max_evaluations=10,
    ))
    assert result.search.local_search_completeness == "exhaustive_one_replacement"
    assert result.retained_results[0].result_family_ids == ("current_bag",)
    keys = set(result.retained_results[0].metric_deltas_from_reference or {})
    assert any(item.startswith("drive.") for item in keys)
    assert any(item.startswith("approach.") for item in keys)
    assert any(item.startswith("putt.") for item in keys)


def test_exports_and_performance_instrumentation_cover_multi_step_search(results):
    result = results["par4_long"]
    payload = json.loads(render_strategy_optimization_json(result))
    search = payload["search"]
    assert search["theoretical_compositions"] > search["compositions_generated"]
    assert search["compositions_evaluated"] > 0
    assert search["active_assignments_theoretical"] > search["active_assignments_considered"]
    assert search["comparison_seconds"] >= 0
    assert search["total_seconds"] >= search["generation_seconds"] + search["evaluation_seconds"]
    assert search["evaluation_cache_hits"] >= 0
    assert payload["retained_results"][0]["active_assignments"].keys() == {"drive", "approach", "putt"}


def test_gui_overview_adapts_to_two_and_three_steps(results):
    presenter = StrategyOptimizerPresenter.load(REGISTRY)
    short = presenter.present(results["par4_short"]).details[0].overview
    long = presenter.present(results["par4_long"]).details[0].overview
    assert "ATTAQUE DIRECTE DU GREEN" in short and "TERMINER DEPUIS LE GREEN" in short
    assert "DÉPART" in long and "APPROCHE VERS LE GREEN" in long and "TERMINER DEPUIS LE GREEN" in long
    assert "Club :" in long and "SUPPORTS" in long and "ORDRE" in long


def test_empirical_reference_works_without_explicit_reference_step_id():
    result = optimizer().optimize(StrategyOptimizationRequest(
        "par4_long", limit=1, max_evaluations=5, reference_bag_id="par3_divebomb",
    ))
    assert result.empirical_reference is not None
    assert result.retained_results

