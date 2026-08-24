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


@pytest.fixture()
def historical_reference_database(tmp_path):
    destination = tmp_path / "historical.sqlite"
    shutil.copyfile(DATABASE, destination)
    levels = {
        "high_flight": 8, "cyclotron": 8, "ember": 7, "maelstrom": 6, "sunstorm": 6,
        "divebomb": 8, "jumpstart": 8, "steadfast": 7,
    }
    with sqlite3.connect(destination) as connection:
        for club_id, level in levels.items():
            connection.execute(
                "UPDATE user_clubs SET unlocked = 1, current_level = ? WHERE club_id = ?",
                (level, club_id),
            )
    return destination


def optimizer(database=DATABASE):
    return StrategyOptimizer(
        user_data_path=database,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    )


def test_every_compatible_saved_bag_bypasses_global_preselection_and_gets_all_structural_orders():
    service = optimizer()
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    references = service.generator.reference_candidates(strategy, runtime, bundle.bags)
    by_composition = {}
    for item in references:
        by_composition.setdefault(frozenset(item.club_ids), []).append(item)
    assert len(by_composition) == len(bundle.bags) == 2
    assert all(values for values in by_composition.values())
    assert all(len(values) <= 120 for values in by_composition.values())
    assert {item.provenance for item in references} == {"reference_bag"}


def test_historical_high_flight_reference_keeps_the_validated_19_10_13_scenario(historical_reference_database):
    result = optimizer(historical_reference_database).optimize(
        StrategyOptimizationRequest("par3", limit=20, max_evaluations=2000)
    )
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


def test_historical_divebomb_reference_keeps_the_validated_16_9_9_scenario(historical_reference_database):
    result = optimizer(historical_reference_database).optimize(
        StrategyOptimizationRequest("par3", limit=20, max_evaluations=2000)
    )
    reference = next(
        item for item in result.retained_results
        if item.origin == "reference_bag" and item.active_assignments["attack"] == "divebomb"
    )
    divebomb = next(item for item in reference.clubs if item.club_id == "divebomb")
    attack = next(item for item in divebomb.steps if item.step_id == "attack")
    assert attack.final_stats == {"power": 16.0, "control": 9.0, "spin": 9.0}


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


def test_one_replacement_compositions_are_exhaustive_and_every_structural_order_is_reoptimized(local_database):
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
    assert all(1 <= len(items) <= 120 for items in spaces.values())
    assert all(items[0].structurally_distinct_permutations == len(items) for items in spaces.values())
    compositions = {frozenset(item.club_ids) for item in generated}
    assert frozenset(bag.club_ids) in compositions
    assert all(any("gearshift" in item.club_ids for item in items) for key, items in spaces.items() if frozenset(items[0].club_ids) != frozenset(bag.club_ids))


def test_structural_order_reduction_is_exact_against_full_120(local_database):
    service = optimizer(local_database)
    bundle = load_user_data(local_database)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    club_ids = next(item for item in bundle.bags if item.identifier == "par3_high_flight").club_ids
    assignment = service.generator._preferred_assignment(strategy.definition, runtime, club_ids)

    def outcomes(mode):
        result = set()
        orders = service.generator._orders_for(club_ids, runtime, mode)
        for index, (order, reason) in enumerate(orders):
            spec = CandidateSpec(str(index), order, dict(zip((s.identifier for s in strategy.definition.sequence), assignment)), "test")
            quick = service._evaluate_quick(spec, strategy, runtime, EvaluationMode.PARTIAL)
            result.add((tuple(sorted(quick.objective_metrics.items())), quick.unresolved))
        return result, len(orders)

    reduced, reduced_count = outcomes("structural_exact")
    complete, complete_count = outcomes("full_120")
    assert reduced == complete
    assert reduced_count < complete_count == 120


def test_optimized_one_replacement_neighborhood_matches_legacy_full_results(local_database):
    service = optimizer(local_database)
    bundle = load_user_data(local_database)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    bag = next(item for item in bundle.bags if item.identifier == "par3_high_flight")

    def outcomes(order_mode):
        specs = service.generator.generate_local(
            strategy, runtime, bag, replacement_depth=1, order_mode=order_mode,
        )
        values = set()
        for spec in specs:
            quick = service._evaluate_quick(spec, strategy, runtime, EvaluationMode.PARTIAL)
            values.add((
                tuple(sorted(spec.club_ids)),
                tuple(sorted(quick.objective_metrics.items())),
                quick.unresolved,
            ))
        return values, len(specs)

    optimized, optimized_count = outcomes("structural_exact")
    legacy, legacy_count = outcomes("full_120")
    assert optimized == legacy
    assert optimized_count < legacy_count


def test_local_constraints_lock_keep_exclude_and_allow_two_putters(local_database):
    service = optimizer(local_database)
    bundle = load_user_data(local_database)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    bag = next(item for item in bundle.bags if item.identifier == "par3_high_flight")
    generated = service.generator.generate_local(
        strategy, runtime, bag,
        required_club_ids=("cyclotron", "gearshift"),
        excluded_club_ids=("maelstrom",),
        locked_positions={2: "cyclotron"},
        keep_current_putter=True,
    )
    assert generated
    assert all({"cyclotron", "gearshift", "ember"}.issubset(item.club_ids) for item in generated)
    assert all("maelstrom" not in item.club_ids and item.club_ids[1] == "cyclotron" for item in generated)
    assert all(sum(runtime.clubs[item].club_type == "putter" for item in spec.club_ids) == 2 for spec in generated)


def test_optimizer_detects_inventory_and_level_changes_without_restart(local_database):
    service = optimizer(local_database)
    first = service.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=1))
    assert not first.inventory_changes.added_club_ids
    with sqlite3.connect(local_database) as connection:
        connection.execute("UPDATE user_clubs SET unlocked = 1, current_level = 7, cards_owned = 2 WHERE club_id = 'wave'")
        connection.execute("UPDATE user_clubs SET current_level = 9, cards_owned = 3 WHERE club_id = 'gearshift'")
    second = service.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=1))
    assert second.inventory_changes.added_club_ids == ("wave",)
    assert second.inventory_changes.level_changes["gearshift"] == (8, 9)
    assert second.inventory_changes.cards_changes["gearshift"] == (0, 3)
    wave = second.new_club_diagnostics[0]
    assert (wave.club_id, wave.level, wave.brand, wave.club_type, wave.rarity) == (
        "wave", 7, "nautilus", "iron", "epic",
    )
    assert {item.status for item in wave.abilities} == {"resolved", "physics_required"}


def test_new_club_mode_tests_wave_as_active_or_support_without_name_specific_logic(local_database):
    with sqlite3.connect(local_database) as connection:
        connection.execute("UPDATE user_clubs SET unlocked = 1, current_level = 7 WHERE club_id = 'wave'")
    service = optimizer(local_database)
    bundle = load_user_data(local_database)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    bag = next(item for item in bundle.bags if item.identifier == "par3_high_flight")
    generated = service.generator.generate_local(
        strategy, runtime, bag, required_club_ids=("wave",), replacement_depth=1,
    )
    assert generated and all("wave" in item.club_ids for item in generated)
    assert any("wave" in item.active_assignments.values() for item in generated)
    assert any("wave" not in item.active_assignments.values() for item in generated)
    production = (ROOT / "src" / "pga_shootout" / "strategy_optimizer.py").read_text(encoding="utf-8").casefold()
    assert 'club_id == "wave"' not in production and 'club_id == "gearshift"' not in production


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


def test_around_club_search_is_global_and_keeps_requested_role():
    result = optimizer().optimize(StrategyOptimizationRequest(
        "par4_long", limit=3, max_evaluations=80,
        search_mode="around_club", target_bag_id="par3_high_flight",
        fixed_club_id="wave", fixed_step_id="approach",
    ))
    candidates = tuple(item for item in result.retained_results if item.origin == "around_club")
    assert candidates
    assert all(item.active_assignments["approach"] == "wave" for item in candidates)
    assert result.search.local_search_completeness == "bounded_around_fixed_club"
    assert result.search.origin_counts["around_club"] > 0


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
    assert 0 < len(selected) <= 240
    depths = {len(set(item.club_ids) - set(bag.club_ids)) for item in selected}
    assert {0, 2}.issubset(depths) and depths.issubset({0, 1, 2})


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
