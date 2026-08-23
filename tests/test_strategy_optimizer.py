import json
from dataclasses import replace
from pathlib import Path
import shutil
import sqlite3

import pytest

from pga_shootout.models import EvaluationMode
from pga_shootout.cli import build_parser, main
from pga_shootout.strategy import ClubConstraint, ResolvedStrategy, StrategyRegistry
from pga_shootout.strategy_optimizer import (
    CandidateSpec,
    StrategyOptimizationRequest,
    StrategyOptimizer,
    _RuntimeEvaluator,
    _candidate_lines,
    render_strategy_optimization,
    render_strategy_optimization_json,
)
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pga_shootout.sqlite"
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"
REGISTRY = ROOT / "data" / "strategies" / "strategies.json"


@pytest.fixture(scope="module")
def components():
    bundle = load_user_data(DATABASE)
    runtime = _RuntimeEvaluator(CATALOG, bundle.inventory.entries, None)
    strategy = StrategyRegistry.load(REGISTRY).resolve("par3")
    optimizer = StrategyOptimizer(user_data_path=DATABASE, catalog_path=CATALOG, strategy_registry_path=REGISTRY)
    return bundle, runtime, strategy, optimizer


def spec(identifier, clubs, attack, putt):
    return CandidateSpec(identifier, tuple(clubs), {"attack": attack, "putt": putt}, "test")


def test_real_inventory_and_levels_are_used_without_implicit_common_level(components):
    bundle, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=10))
    unlocked = {item.club_id: item.current_level for item in bundle.inventory.entries if item.unlocked}

    assert result.level_mode == "actual"
    assert result.scenario_level is None
    assert result.search.origin_counts["reference_bag"] == 138
    assert result.search.origin_counts["global_search"] == 10
    assert result.search.candidates_evaluated == 148
    for club in result.retained_results[0].clubs:
        assert club.club_id in unlocked
        assert club.level == unlocked[club.club_id]


def test_unknown_owned_level_is_explicitly_excluded(tmp_path):
    database = tmp_path / "user.sqlite"
    shutil.copyfile(DATABASE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE user_clubs SET current_level = NULL WHERE club_id = 'homestead'")
    result = StrategyOptimizer(
        user_data_path=database,
        catalog_path=CATALOG,
        strategy_registry_path=REGISTRY,
    ).optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=5))
    exclusion = next(item for item in result.excluded_clubs if item.club_id == "homestead")
    assert exclusion.reason == "niveau utilisateur inconnu"
    assert all("homestead" not in item.composition for item in result.retained_results)


def test_active_assignments_are_distinct_and_come_from_strategy_steps(components):
    _, _, strategy, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=3, max_evaluations=20))
    expected_steps = tuple(step.identifier for step in strategy.definition.sequence)
    for candidate in result.retained_results:
        assert tuple(candidate.active_assignments) == expected_steps
        assert len(set(candidate.active_assignments.values())) == 2
        assert len(candidate.composition) == len(set(candidate.composition)) == 5


def test_active_club_constraints_are_only_applied_when_declared(components):
    bundle, runtime, strategy, optimizer = components
    putt_step = strategy.definition.sequence[1]
    assert putt_step.club_constraints == (ClubConstraint("type", "equals", "putter"),)

    unconstrained_step = replace(putt_step, club_constraints=())
    unconstrained_strategy = ResolvedStrategy(
        replace(strategy.definition, sequence=(strategy.definition.sequence[0], unconstrained_step)),
        strategy.applied_variant_ids,
    )
    unconstrained, _, _ = optimizer.generator.generate(unconstrained_strategy, runtime, bundle.bags, max_generated=240)
    assert any(runtime.clubs[item.active_assignments[putt_step.identifier]].club_type != "putter" for item in unconstrained)

    generated, _, _ = optimizer.generator.generate(strategy, runtime, bundle.bags, max_generated=240)
    assert generated
    assert all(runtime.clubs[item.active_assignments[putt_step.identifier]].club_type == "putter" for item in generated)


def test_order_changes_an_adjacency_ability_without_strategy_specific_logic(components):
    _, runtime, strategy, optimizer = components
    near = spec(
        "near", ("homestead", "commonlaw", "high_flight", "lowball", "ember"),
        "homestead", "lowball",
    )
    far = spec(
        "far", ("homestead", "high_flight", "ember", "lowball", "commonlaw"),
        "homestead", "lowball",
    )
    near_result = optimizer._evaluate_quick(near, strategy, runtime, EvaluationMode.PARTIAL)
    far_result = optimizer._evaluate_quick(far, strategy, runtime, EvaluationMode.PARTIAL)
    assert near_result.steps[0].summary.evaluation.result.final_stats.power > far_result.steps[0].summary.evaluation.result.final_stats.power


def test_type_and_bag_contributions_are_attributed_to_sources(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "typed", ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm"),
        "high_flight", "cyclotron",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    detailed = optimizer._detail(quick, strategy, runtime, EvaluationMode.PARTIAL)
    high_flight = next(item for item in detailed.clubs if item.club_id == "high_flight")
    received = high_flight.steps[0].contributions_received
    assert any(item.ability_id == "ember__alloy" and item.modification["power"] > 0 for item in received)
    assert any(item.ability_id == "maelstrom__bag_spin_bonus" for item in received)


def test_chain_is_transmitted_and_consumed_on_the_compatible_next_step(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "chain", ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"),
        "divebomb", "ember",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    first = quick.steps[0].summary.evaluation.result
    second = quick.steps[1].summary.evaluation.result
    assert any(item.source_club_id == "divebomb" for item in first.scheduled_effects)
    assert second.consumed_effect_ids
    assert second.final_stats.power > second.base_stats.power


def test_five_clubs_have_a_club_by_step_metric_matrix_and_missing_stat(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "matrix", ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm"),
        "high_flight", "cyclotron",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    detailed = optimizer._detail(quick, strategy, runtime, EvaluationMode.PARTIAL)
    assert len(detailed.clubs) == 5
    assert all(len(item.steps) == 2 for item in detailed.clubs)
    ember = next(item for item in detailed.clubs if item.club_id == "ember")
    assert ember.steps[0].base_stats["spin"] is None
    assert any("Spin   : —" in line for line in _candidate_lines(detailed))


def test_context_can_produce_different_final_values_between_steps(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "context", ("sidewinder", "lowball", "commonlaw", "steadfast", "sunstorm"),
        "sidewinder", "lowball",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    detailed = optimizer._detail(quick, strategy, runtime, EvaluationMode.PARTIAL)
    sidewinder = next(item for item in detailed.clubs if item.club_id == "sidewinder")
    attack, putt = sidewinder.steps
    assert attack.context["terrain"] == "tee"
    assert putt.context["terrain"] == "green"
    assert attack.final_stats["power"] > putt.final_stats["power"]


def test_support_and_hybrid_roles_require_observed_contribution(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "roles", ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm"),
        "ember", "high_flight",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    detailed = optimizer._detail(quick, strategy, runtime, EvaluationMode.PARTIAL)
    roles = {item.club_id: item.role for item in detailed.clubs}
    assert roles["ember"] == "hybrid"
    # Maelstrom's only observed benefit here is not relevant to either active
    # step, so the technical contribution remains visible without qualifying it.
    assert roles["maelstrom"] == "neutral"
    assert all(item.role != "support" or item.support_steps for item in detailed.clubs)


def test_support_counterfactual_reports_metrics_lost_on_removal(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "counterfactual", ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm"),
        "high_flight", "cyclotron",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    detailed = optimizer._detail(quick, strategy, runtime, EvaluationMode.PARTIAL)
    maelstrom = next(item for item in detailed.support_counterfactuals if item.club_id == "maelstrom")
    assert maelstrom.conclusion == "support utile"
    assert any(
        "spin" in change.lost_metrics_if_removed
        for change in maelstrom.changes
    )


def test_putt_loft_and_bounce_remain_calculated_but_never_qualify_support(components):
    _, runtime, strategy, optimizer = components
    candidate = spec(
        "descriptive", ("high_flight", "lowball", "cloudcatcher", "cyclotron", "maelstrom"),
        "high_flight", "lowball",
    )
    quick = optimizer._evaluate_quick(candidate, strategy, runtime, EvaluationMode.PARTIAL)
    detailed = optimizer._detail(quick, strategy, runtime, EvaluationMode.PARTIAL)
    for club_id in ("cloudcatcher", "cyclotron"):
        support = next(item for item in detailed.clubs if item.club_id == club_id)
        assert "putt" not in support.support_steps
    putt = next(item for item in detailed.clubs if item.club_id == "lowball").steps[1]
    assert putt.metric_relevance.get("loft_angle_degrees") == "descriptive"
    bounce_records = [
        item for item in putt.contributions_received
        if "bounce_reduction_percent" in item.modification
    ]
    assert all(item.metric_relevance["bounce_reduction_percent"] == "descriptive" for item in bounce_records)


def test_result_families_and_landing_profile_are_score_free(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=3, max_evaluations=600))
    assert {item.identifier for item in result.result_families} == {
        "iron_max_power", "iron_power_control", "iron_stability", "all_types_competitor",
    }
    assert any(item.candidate_ids for item in result.result_families if item.identifier.startswith("iron"))
    assert result.retained_results
    assert all(profile.aggregate_score is None for item in result.retained_results for profile in item.landing_profiles)
    assert all(
        metric.status == "descriptive"
        for item in result.retained_results for profile in item.landing_profiles
        for metric in profile.metrics if metric.metric == "loft_angle_degrees"
    )


def test_base_dominated_iron_is_not_preselected_away_before_bag_synergy(components):
    bundle, runtime, strategy, optimizer = components
    divebomb = runtime.clubs["divebomb"].stats_at(runtime.levels["divebomb"]).as_dict()
    ironbark = runtime.clubs["ironbark"].stats_at(runtime.levels["ironbark"]).as_dict()
    assert all(ironbark[key] > divebomb[key] for key in ("power", "control", "spin"))
    attack_pool = tuple(runtime.clubs)
    selected = optimizer.generator._pareto_active_pool(
        runtime, attack_pool, strategy.definition.sequence[0],
        tuple(club_id for bag in bundle.bags for club_id in bag.club_ids),
    )
    assert "divebomb" in selected
    assert set(selected) == set(attack_pool)
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=2, max_evaluations=600))
    family = next(item for item in result.result_families if item.identifier == "iron_max_power")
    winner = next(item for item in result.retained_results if item.candidate_id in family.candidate_ids)
    assert winner.active_assignments["attack"] == "divebomb"
    club = next(item for item in winner.clubs if item.club_id == "divebomb")
    attack = next(item for item in club.steps if item.step_id == "attack")
    assert attack.final_stats["power"] > divebomb["power"]


def test_empirical_reference_uses_saved_bag_final_power_without_distance_claim(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest(
        "par3", limit=2, max_evaluations=360, reference_bag_id="par3_divebomb"
    ))
    reference = result.empirical_reference
    assert reference is not None
    assert reference.club_id == "divebomb"
    assert "distance garantie" in reference.statement
    for candidate in result.retained_results:
        active = next(club for club in candidate.clubs if "attack" in club.active_steps)
        step = next(item for item in active.steps if item.step_id == "attack")
        assert step.final_stats["power"] >= reference.final_power


def test_exact_order_audit_is_exposed_on_every_retained_candidate(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=240))
    audit = result.retained_results[0].order_audit
    assert audit["theoretical_permutations"] == 120
    assert audit["evaluated_permutations"] <= audit["structurally_distinct_permutations"]
    assert audit["equivalence_reason"] != "legacy_representative_sample"


def test_result_deduplication_has_no_score_and_keeps_multiple_compromises(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=5, max_evaluations=100))
    assert result.aggregate_score is None
    assert result.search.candidate_result_duplicates_removed > 0
    assert len(result.retained_results) > 1
    assert all(item.aggregate_score is None for item in result.retained_results)
    assert len({item.candidate_id for item in result.retained_results}) == len(result.retained_results)


def test_requirements_remain_indeterminate_without_carry_and_putt_models(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=5))
    requirements = result.retained_results[0].requirements
    assert {item.status for item in requirements} == {"indeterminate"}
    assert any("validated_carry_model" in item.missing_data for item in requirements)
    assert any("validated_putt_model" in item.missing_data for item in requirements)


def test_text_and_json_share_the_same_result_objects(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=1, max_evaluations=5))
    text = render_strategy_optimization(result)
    payload = json.loads(render_strategy_optimization_json(result))
    assert "AVERTISSEMENTS" in text
    assert "Power  :" in text
    assert "rôle actif" in text or "rôle support" in text
    assert "Aucun score global" in text
    assert payload["aggregate_score"] is None
    assert payload["retained_results"][0]["clubs"]
    assert payload["retained_results"][0]["support_counterfactuals"]


def test_scenario_mode_is_explicitly_hypothetical(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(
        StrategyOptimizationRequest("par3", limit=1, max_evaluations=5, scenario_level=12)
    )
    assert result.level_mode == "scenario"
    assert result.scenario_level == 12
    assert any("hypothétique" in item for item in result.warnings)
    assert all(club.level == 12 for club in result.retained_results[0].clubs)


def test_structurally_exact_inventory_search_is_instrumented_and_bounded(components):
    _, _, _, optimizer = components
    result = optimizer.optimize(StrategyOptimizationRequest("par3", limit=2, max_evaluations=200))
    assert result.search.theoretical_candidates > 1_000_000
    assert result.search.reduced_candidates_generated < result.search.theoretical_candidates
    assert result.search.origin_counts["reference_bag"] == 138
    assert 0 < result.search.origin_counts["global_search"] <= 200
    assert result.search.candidates_evaluated <= 338
    assert result.search.safety_limit_reached
    assert result.search.completeness == "partial_bounded_search_with_exact_retained_order_spaces"
    assert result.search.permutations_structurally_distinct >= result.search.candidates_evaluated
    assert result.search.evaluation_seconds < 10


def test_optimizer_source_has_no_strategy_identifier_branch():
    source = (ROOT / "src" / "pga_shootout" / "strategy_optimizer.py").read_text(encoding="utf-8")
    for token in ("if strategy ==", "if strategy_id ==", "if par3", "if par4", "if par5"):
        assert token not in source.lower()
    for token in ("if result_family ==", "if family.identifier ==", "if iron_max_power"):
        assert token not in source.lower()


def test_cli_rejects_conflicting_evaluation_modes():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["optimize-strategy", "par3", "--partial", "--strict"])


def test_cli_json_exposes_the_same_stable_contract(capsys):
    assert main([
        "optimize-strategy", "par3", "--partial", "--limit", "1", "--max-evaluations", "5",
        "--user-dir", str(DATABASE), "--catalog", str(CATALOG), "--registry", str(REGISTRY), "--json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["aggregate_score"] is None
    assert payload["search"]["origin_counts"] == {
        "global_search": 5,
        "reference_bag": 138,
        "reference_neighborhood": 0,
    }
    assert payload["search"]["candidates_evaluated"] == 143
    # The display limit applies per result family; both saved reference bags
    # remain visible as independent control candidates.
    assert len(payload["retained_results"]) == 2
    assert {item["origin"] for item in payload["retained_results"]} == {"reference_bag"}
