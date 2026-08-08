from __future__ import annotations

from dataclasses import replace
from itertools import permutations
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
    _QuickCandidate,
    _RuntimeEvaluator,
    _dominates_candidate,
)
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


@pytest.fixture()
def local_database(tmp_path):
    destination = tmp_path / "local.sqlite"
    shutil.copyfile(DATABASE, destination)
    allowed = ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm", "gearshift")
    placeholders = ",".join("?" for _ in allowed)
    with sqlite3.connect(destination) as connection:
        connection.execute(f"UPDATE user_clubs SET unlocked = club_id IN ({placeholders})", allowed)
    return destination


def optimizer(database=DATABASE):
    return StrategyOptimizer(
        user_data_path=database,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    )


def test_every_compatible_saved_bag_bypasses_global_preselection_and_gets_120_orders():
    service = optimizer()
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    references = service.generator.reference_candidates(strategy, runtime, bundle.bags)
    by_composition = {}
    for item in references:
        by_composition.setdefault(frozenset(item.club_ids), []).append(item)
    assert len(by_composition) == len(bundle.bags) == 2
    assert all(len(values) == 120 for values in by_composition.values())
    assert {item.provenance for item in references} == {"reference_bag"}


def test_real_high_flight_reference_is_evaluated_but_current_validated_data_produces_13_spin():
    result = optimizer().optimize(StrategyOptimizationRequest("par3", limit=20, max_evaluations=2000))
    reference = next(
        item for item in result.retained_results
        if item.origin == "reference_bag" and item.active_assignments["attack"] == "high_flight"
    )
    high_flight = next(item for item in reference.clubs if item.club_id == "high_flight")
    attack = next(item for item in high_flight.steps if item.step_id == "attack")
    assert attack.base_stats == {"power": 12.0, "control": 8.0, "spin": 5.0}
    assert attack.final_stats == {"power": 19.0, "control": 10.0, "spin": 13.0}
    spin = {
        item.ability_id: item.modification["spin"]
        for item in attack.contributions_received if "spin" in item.modification
    }
    assert spin == {
        "cyclotron__spin_boost": 4.0,
        "maelstrom__bag_spin_bonus": 2.0,
        "sunstorm__plasma_arc_x": 2.0,
    }


def test_reference_dominance_rejects_19_10_13_but_keeps_a_real_putter_tradeoff():
    base = _QuickCandidate(
        CandidateSpec("candidate", ("a", "b", "c", "d", "e"), {}, "global_search"),
        (), (), {}, (), False,
    )
    weaker = replace(base, objective_metrics={"attack.power": 19, "attack.control": 10, "attack.spin": 13, "putt.control": 10})
    reference = replace(
        base,
        spec=replace(base.spec, identifier="reference", provenance="reference_bag"),
        objective_metrics={"attack.power": 19, "attack.control": 10, "attack.spin": 14, "putt.control": 10},
    )
    compromise = replace(
        base,
        spec=replace(base.spec, identifier="tradeoff"),
        objective_metrics={"attack.power": 19, "attack.control": 10, "attack.spin": 13, "putt.control": 17},
    )
    assert _dominates_candidate(reference, weaker)
    assert not _dominates_candidate(reference, compromise)


def test_one_replacement_compositions_are_exhaustive_and_every_order_is_reoptimized(local_database):
    service = optimizer(local_database)
    bundle = load_user_data(local_database)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    bag = next(item for item in bundle.bags if item.identifier == "par3_high_flight")
    generated = service.generator.generate_local(strategy, runtime, bag, replacement_depth=1)
    spaces = {}
    for item in generated:
        spaces.setdefault(item.order_space_id, []).append(item)
    # Original plus Gearshift replacing each of the five positions.
    assert len(spaces) == 6
    assert all(len(items) == 120 for items in spaces.values())
    compositions = {frozenset(item.club_ids) for item in generated}
    assert frozenset(bag.club_ids) in compositions
    assert all(any("gearshift" in item.club_ids for item in items) for key, items in spaces.items() if frozenset(items[0].club_ids) != frozenset(bag.club_ids))


def test_local_mode_shows_current_bag_first_and_exports_reference_deltas(local_database):
    result = optimizer(local_database).optimize(StrategyOptimizationRequest(
        "par3", limit=5, search_mode="improve_bag", target_bag_id="par3_high_flight",
        replacement_depth=1, max_evaluations=100,
    ))
    assert result.retained_results[0].origin == "reference_bag"
    assert result.retained_results[0].composition == (
        "high_flight", "cyclotron", "ember", "maelstrom", "sunstorm",
    )
    assert result.retained_results[0].result_family_ids == ("current_bag",)
    assert result.search.local_search_completeness == "exhaustive_one_replacement"
    assert result.search.origin_counts["reference_neighborhood"] > 0
    assert all(item.metric_deltas_from_reference is not None for item in result.retained_results)
    assert any(item.added_club_ids == ("gearshift",) for item in result.retained_results[1:]) or result.search.origin_counts["reference_neighborhood"] > 0


@pytest.mark.parametrize("club_id", ("high_flight", "divebomb", "gearshift"))
def test_around_club_generation_keeps_the_requested_active_club(club_id):
    service = optimizer()
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    bag = next((item for item in bundle.bags if club_id in item.club_ids), bundle.bags[0])
    generated = service.generator.generate_local(
        strategy, runtime, bag, replacement_depth=1, fixed_club_id=club_id,
    )
    assert generated
    assert all(item.active_assignments["attack"] == club_id for item in generated)
    assert all(club_id in item.club_ids for item in generated)


def test_trace_composition_reports_generation_or_exact_reduction_stage():
    result = optimizer().trace_composition(
        "par3", ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm")
    )
    assert result["status"] == "generated"
    assert "reference_bag" in result["origins"]
    invalid = optimizer().trace_composition("par3", ("high_flight",) * 5)
    assert invalid["stage"] == "composition_validation"


def test_support_potential_is_structural_and_has_no_synthetic_score():
    service = optimizer()
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    potential = service.generator.support_potential(runtime, ("high_flight",))
    assert "gearshift" in potential
    assert "whole_bag" in potential["gearshift"]
    assert all(isinstance(categories, tuple) for categories in potential.values())
    assert "score" not in repr(potential).casefold()


def test_two_replacement_search_is_explicitly_structurally_reduced(local_database):
    with sqlite3.connect(local_database) as connection:
        connection.execute("UPDATE user_clubs SET unlocked = 1 WHERE club_id IN ('steadfast', 'outlaw')")
    service = optimizer(local_database)
    bundle = load_user_data(local_database)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    bag = next(item for item in bundle.bags if item.identifier == "par3_high_flight")
    generated = service.generator.generate_local(strategy, runtime, bag, replacement_depth=2)
    assert generated
    assert service.generator.last_generation_stats["replacement_depth"] == 2
    assert any(len(set(item.club_ids) - set(bag.club_ids)) == 2 for item in generated)
    selected = service._bounded_local_order_spaces(generated, bag, 240)
    assert len(selected) == 240
    assert {len(set(item.club_ids) - set(bag.club_ids)) for item in selected} == {0, 2}


def test_real_gearshift_is_fully_resolved_as_left_or_right_support():
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)

    def contribution(order, ability_id):
        summary = runtime.evaluate(
            CandidateSpec("gear", order, {"attack": "high_flight"}, "test"),
            "high_flight", mode=EvaluationMode.PARTIAL, terrain="tee",
        )
        return next(item for item in summary.ability_contributions if item.ability_id == ability_id)

    left = contribution(
        ("gearshift", "high_flight", "ember", "sunstorm", "maelstrom"),
        "gearshift__first_gear",
    )
    assert left.modification == {
        "power": 0.0, "control": 1.0, "spin": 0.0, "bounce_reduction_percent": 11.0,
    }
    assert left.unresolved == ()
    right = contribution(
        ("high_flight", "ember", "sunstorm", "maelstrom", "gearshift"),
        "gearshift__top_gear",
    )
    assert right.modification == {
        "power": 1.0, "control": 0.0, "spin": 0.0, "groundspin_increase_percent": 60.0,
    }
    assert right.unresolved == ()


def test_each_optimization_reloads_inventory_without_gui_restart(local_database):
    service = optimizer(local_database)
    with sqlite3.connect(local_database) as connection:
        connection.execute("UPDATE user_clubs SET unlocked = 0 WHERE club_id = 'gearshift'")
        connection.execute("UPDATE inventory_state SET observed_at = 'before' WHERE profile_id = 1")
    before = service.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=1))
    with sqlite3.connect(local_database) as connection:
        connection.execute("UPDATE user_clubs SET unlocked = 1 WHERE club_id = 'gearshift'")
        connection.execute("UPDATE inventory_state SET observed_at = 'after' WHERE profile_id = 1")
    after = service.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=1))
    assert (before.inventory_owned_count, before.inventory_observed_at) == (5, "before")
    assert (after.inventory_owned_count, after.inventory_observed_at) == (6, "after")
