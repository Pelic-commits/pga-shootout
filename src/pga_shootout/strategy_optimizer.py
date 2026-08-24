"""Generic, bounded strategy search built above the existing Rule Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from itertools import combinations, permutations, product
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

from .bag_comparison import AbilityContribution, ComparedBag, summarize_bag_evaluation
from .bag_evaluation import (
    BagEvaluation,
    _abilities_at_level,
    _available_stats_by_level,
    _semantic_effect_specs,
    _semantic_program,
    _stats_by_level,
)
from .engine import EvaluationError, RuleEngine
from .models import Bag, BagEntry, Club, DelayedEffect, EvaluationMode, GameState
from .metric_semantics import MetricSemantic, MetricSemanticsRegistry
from .strategy import (
    OutcomeRequirement, ResolvedStrategy, ResultFamilyConstraint, ResultFamilyDefinition,
    ResultFamilyObjective, ShotStep, StrategyRegistry,
)
from .user_data import InventoryEntry, SavedBag, load_user_data


class StrategyOptimizationError(ValueError):
    pass


@dataclass(frozen=True)
class StrategyOptimizationRequest:
    strategy_id: str
    variant_ids: tuple[str, ...] = ()
    limit: int = 20
    mode: EvaluationMode = EvaluationMode.PARTIAL
    scenario_level: int | str | None = None
    max_evaluations: int = 2000
    order_mode: str = "structural_exact"
    reference_bag_id: str | None = None
    search_mode: str = "global"
    target_bag_id: str | None = None
    fixed_club_id: str | None = None
    replacement_depth: int = 1
    required_club_ids: tuple[str, ...] = ()
    excluded_club_ids: tuple[str, ...] = ()
    locked_positions: Mapping[int, str] | None = None
    keep_current_putter: bool = False
    fixed_step_id: str | None = None
    club_roles: Mapping[str, str] | None = None
    metric_minimums: Mapping[str, Mapping[str, float]] | None = None
    primary_step_id: str | None = None

    @property
    def level_mode(self) -> str:
        return "scenario" if self.scenario_level is not None else "actual"


@dataclass(frozen=True)
class ClubExclusion:
    club_id: str
    club_name: str
    reason: str


@dataclass(frozen=True)
class InventoryAbilityDiagnostic:
    ability_id: str
    label: str
    official_value: str | None
    status: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class InventoryClubDiagnostic:
    club_id: str
    club_name: str
    level: int | str
    brand: str
    club_type: str
    rarity: str
    base_stats: Mapping[str, float | None]
    abilities: tuple[InventoryAbilityDiagnostic, ...]
    active_step_ids: tuple[str, ...]
    support_categories: tuple[str, ...]


@dataclass(frozen=True)
class InventoryChangeSet:
    added_club_ids: tuple[str, ...] = ()
    removed_club_ids: tuple[str, ...] = ()
    level_changes: Mapping[str, tuple[int | None, int | None]] | None = None
    cards_changes: Mapping[str, tuple[int | None, int | None]] | None = None


@dataclass(frozen=True)
class CandidateSpec:
    identifier: str
    club_ids: tuple[str, ...]
    active_assignments: Mapping[str, str]
    provenance: str
    order_space_id: str = ""
    theoretical_permutations: int = 120
    structurally_distinct_permutations: int = 120
    order_equivalence_reason: str = "none"


@dataclass(frozen=True)
class RequirementResult:
    step_id: str
    requirement_id: str
    description: str
    status: str
    missing_data: tuple[str, ...]


@dataclass(frozen=True)
class ContributionRecord:
    source_club_id: str
    target_club_id: str
    ability_id: str
    mechanism: str
    modification: Mapping[str, float]
    scheduled_effect_ids: tuple[str, ...] = ()
    metric_relevance: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ClubStepResult:
    step_id: str
    context: Mapping[str, Any]
    base_stats: Mapping[str, float | None]
    final_stats: Mapping[str, float | None]
    deltas: Mapping[str, float | None]
    additional_metrics: Mapping[str, float]
    metric_relevance: Mapping[str, str]
    active_abilities: tuple[str, ...]
    abilities_without_effect: tuple[str, ...]
    unresolved_abilities: tuple[str, ...]
    contributions_received: tuple[ContributionRecord, ...]
    contributions_sent: tuple[ContributionRecord, ...]


@dataclass(frozen=True)
class CounterfactualChange:
    step_id: str
    target_club_id: str
    lost_metrics_if_removed: Mapping[str, float]
    gained_metrics_if_removed: Mapping[str, float]


@dataclass(frozen=True)
class SupportCounterfactual:
    club_id: str
    changes: tuple[CounterfactualChange, ...]
    conclusion: str


@dataclass(frozen=True)
class OptimizedClubResult:
    position: int
    club_id: str
    club_name: str
    club_type: str
    level: int | str
    role: str
    active_steps: tuple[str, ...]
    support_steps: tuple[str, ...]
    steps: tuple[ClubStepResult, ...]


@dataclass(frozen=True)
class StrategyCandidateResult:
    candidate_id: str
    composition: tuple[str, ...]
    active_assignments: Mapping[str, str]
    clubs: tuple[OptimizedClubResult, ...]
    requirements: tuple[RequirementResult, ...]
    unresolved_abilities: tuple[str, ...]
    comparison_group: str
    comparison_layer: int
    retained_reason: str
    equivalent_candidates: int
    support_counterfactuals: tuple[SupportCounterfactual, ...]
    order_audit: Mapping[str, Any]
    result_family_ids: tuple[str, ...]
    landing_profiles: tuple["LandingProfile", ...]
    origin: str = "global_search"
    removed_club_ids: tuple[str, ...] = ()
    added_club_ids: tuple[str, ...] = ()
    metric_deltas_from_reference: Mapping[str, float | None] | None = None
    gained_contribution_ids: tuple[str, ...] = ()
    lost_contribution_ids: tuple[str, ...] = ()
    position_changes: Mapping[str, tuple[int | None, int | None]] | None = None
    metric_values_from_reference: Mapping[str, Mapping[str, float | None]] | None = None
    optimization_badges: tuple[str, ...] = ()
    metric_deltas_from_power_max: Mapping[str, float | None] | None = None
    aggregate_score: None = None


@dataclass(frozen=True)
class SearchInstrumentation:
    theoretical_candidates: int
    reduced_candidates_generated: int
    candidates_evaluated: int
    candidate_result_duplicates_removed: int
    permutations_eliminated_before_evaluation: int
    safety_limit: int
    safety_limit_reached: bool
    search_method: str
    completeness: str
    generation_seconds: float
    evaluation_seconds: float
    compositions_generated: int = 0
    permutations_theoretical: int = 0
    permutations_proven_equivalent: int = 0
    permutations_structurally_distinct: int = 0
    average_seconds_per_composition: float = 0.0
    candidates_retained_by_family: Mapping[str, int] | None = None
    stage_counts: Mapping[str, int] | None = None
    origin_counts: Mapping[str, int] | None = None
    replacement_depth: int = 0
    local_search_completeness: str = "not_applicable"
    theoretical_compositions: int = 0
    compositions_evaluated: int = 0
    active_assignments_theoretical: int = 0
    active_assignments_considered: int = 0
    evaluation_cache_hits: int = 0
    evaluation_cache_misses: int = 0
    comparison_seconds: float = 0.0
    total_seconds: float = 0.0
    optimality_status: str = "best_found"
    support_clubs_considered: int = 0
    compositions_removed: int = 0
    removal_reasons: Mapping[str, int] | None = None
    saved_bag_candidates_injected: int = 0
    known_candidates_injected: int = 0


@dataclass(frozen=True)
class LandingMetric:
    metric: str
    value: float | None
    status: str
    confidence: str
    provenance: str
    source_abilities: tuple[str, ...]


@dataclass(frozen=True)
class LandingProfile:
    step_id: str
    club_id: str
    metrics: tuple[LandingMetric, ...]
    aggregate_score: None = None


@dataclass(frozen=True)
class ResultFamilyResult:
    identifier: str
    user_name: str
    description: str
    candidate_ids: tuple[str, ...]
    selection_policy: str


@dataclass(frozen=True)
class EmpiricalReference:
    bag_id: str
    bag_name: str
    step_id: str
    club_id: str
    club_name: str
    final_power: float
    statement: str


@dataclass(frozen=True)
class TypeComparisonRow:
    club_type: str
    owned_clubs: int
    evaluated_clubs: int
    excluded_clubs: int
    excluded_reasons: tuple[str, ...]
    best_final_power: float | None
    best_control_by_power: Mapping[str, float]
    best_final_spin: float | None
    best_activated_wind_resistance: float | None
    best_activated_bounce_reduction: float | None
    groundspin_values: tuple[float, ...]
    loft_range: tuple[float, float] | None
    supports_for_best_power: tuple[str, ...]
    unresolved_abilities: tuple[str, ...]
    best_order: tuple[str, ...]


@dataclass(frozen=True)
class StrategyOptimizationResult:
    schema_version: str
    catalog_version: str
    strategy_id: str
    strategy_version: str
    applied_variant_ids: tuple[str, ...]
    level_mode: str
    scenario_level: int | str | None
    excluded_clubs: tuple[ClubExclusion, ...]
    search: SearchInstrumentation
    retained_results: tuple[StrategyCandidateResult, ...]
    excluded_candidate_count: int
    warnings: tuple[str, ...]
    result_families: tuple[ResultFamilyResult, ...] = ()
    empirical_reference: EmpiricalReference | None = None
    type_comparison: tuple[TypeComparisonRow, ...] = ()
    inventory_owned_count: int = 0
    inventory_observed_at: str | None = None
    inventory_changes: InventoryChangeSet = InventoryChangeSet()
    new_club_diagnostics: tuple[InventoryClubDiagnostic, ...] = ()
    requested_minimums: Mapping[str, Mapping[str, float]] | None = None
    attainable_ranges: Mapping[str, Mapping[str, tuple[float, ...]]] | None = None
    criteria_satisfied: bool = True
    closest_candidate_ids: tuple[str, ...] = ()
    aggregate_score: None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _QuickStep:
    step: ShotStep
    active_club_id: str
    summary: ComparedBag
    incoming_pending: tuple[DelayedEffect, ...]


@dataclass(frozen=True)
class _QuickCandidate:
    spec: CandidateSpec
    steps: tuple[_QuickStep, ...]
    requirements: tuple[RequirementResult, ...]
    objective_metrics: Mapping[str, float]
    unresolved: tuple[str, ...]
    strict_failed: bool
    equivalent_candidates: int = 1
    comparison_layer: int = 0
    orders_evaluated_in_space: int = 1
    best_orders: tuple[tuple[str, ...], ...] = ()


class _RuntimeEvaluator:
    """Cache immutable runtime clubs; every calculation still uses RuleEngine.evaluate."""

    def __init__(
        self,
        catalog_path: str | Path,
        entries: tuple[InventoryEntry, ...],
        scenario_level: int | str | None,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        document = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        self.catalog_document = document
        clubs_data = document["clubs"]
        semantic_path = self.catalog_path.with_name("semantic_map.json")
        semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
        self.semantic_entries = semantic.get("entries", {})
        self.semantic_patterns = semantic.get("patterns", {})
        self.levels: dict[str, int | str] = {}
        self.clubs: dict[str, Club] = {}
        self.exclusions: list[ClubExclusion] = []
        self.support_capable_ids: set[str] = set()
        self.support_categories: dict[str, tuple[str, ...]] = {}
        self.order_sensitive_ids: set[str] = set()
        self.order_sensitivity: dict[str, str] = {}
        self.order_neighbor_directions: dict[str, tuple[str, ...]] = {}
        self.contextual_active_ids: set[str] = set()
        self.evaluation_cache: dict[tuple[Any, ...], ComparedBag] = {}
        self.evaluation_cache_hits = 0
        self.evaluation_cache_misses = 0
        for entry in entries:
            if not entry.unlocked:
                continue
            level = scenario_level if scenario_level is not None else entry.current_level
            if level is None:
                self.exclusions.append(ClubExclusion(entry.club_id, entry.display_name, "niveau utilisateur inconnu"))
                continue
            data = clubs_data.get(entry.club_id)
            if not isinstance(data, Mapping):
                self.exclusions.append(ClubExclusion(entry.club_id, entry.display_name, "club absent du catalogue officiel"))
                continue
            stats = _stats_by_level(data)
            if level not in stats:
                reason = f"niveau {level!r} absent des statistiques officielles"
                self.exclusions.append(ClubExclusion(entry.club_id, entry.display_name, reason))
                continue
            club = Club(
                identifier=entry.club_id,
                name=str(data["name"]),
                brand=str(data["brand"]["id"]),
                club_type=str(data["club_type"]["id"]),
                stats_by_level=stats,
                abilities=_abilities_at_level(data, level, self.semantic_entries, self.semantic_patterns),
                rarity=str(data["rarity"]["id"]),
                available_stats_by_level=_available_stats_by_level(data),
            )
            self.clubs[entry.club_id] = club
            self.levels[entry.club_id] = level
            if self._can_affect_other_clubs(data, level):
                self.support_capable_ids.add(entry.club_id)
                self.support_categories[entry.club_id] = self._support_categories(data, level)
            sensitivity = self._order_sensitivity(data, level)
            if sensitivity != "none":
                self.order_sensitive_ids.add(entry.club_id)
                self.order_sensitivity[entry.club_id] = sensitivity
                if sensitivity == "adjacency":
                    self.order_neighbor_directions[entry.club_id] = self._adjacency_directions(data, level)
            if self._has_contextual_active_ability(data, level):
                self.contextual_active_ids.add(entry.club_id)
        source = document.get("source", {})
        self.catalog_version = str(source.get("source_sha256") or source.get("captured_at") or document["schema_version"])
        self.engine = RuleEngine()

    def _can_affect_other_clubs(self, data: Mapping[str, Any], level: int | str) -> bool:
        outward = ("SELECT_ALL", "SELECT_ADJACENT", "FOR_EACH", "SCHEDULE_EFFECT", "MATCH_BRAND", "MATCH_TYPE", "MATCH_RARITY")
        for ability in data.get("abilities", ()):
            if str(level) not in ability.get("values_by_level", {}):
                continue
            semantic = self.semantic_entries.get(f"label:{ability.get('label_id')}", {})
            if not str(semantic.get("interpretation_status", "")).startswith("implemented"):
                # Keep potentially useful unresolved support abilities in the search.
                return True
            for spec in _semantic_effect_specs(semantic):
                program = _semantic_program(spec, self.semantic_patterns)
                serialized = json.dumps({"program": program, "effect": spec}, sort_keys=True) if program else ""
                if any(operation in serialized for operation in outward):
                    return True
        return False

    def _is_order_sensitive(self, data: Mapping[str, Any], level: int | str) -> bool:
        return self._order_sensitivity(data, level) != "none"

    def _order_sensitivity(self, data: Mapping[str, Any], level: int | str) -> str:
        sensitivity = "none"
        for ability in data.get("abilities", ()):
            if str(level) not in ability.get("values_by_level", {}):
                continue
            semantic = self.semantic_entries.get(f"label:{ability.get('label_id')}", {})
            if not str(semantic.get("interpretation_status", "")).startswith("implemented"):
                # An unresolved ability emits no calculated contribution. Its possible
                # real-game behavior remains warned about, but cannot change this run.
                continue
            for spec in _semantic_effect_specs(semantic):
                program = _semantic_program(spec, self.semantic_patterns)
                serialized = json.dumps({"program": program, "effect": spec}, sort_keys=True) if program else ""
                if any(token in serialized for token in (
                    "SELECT_BY_POSITION", "bag_position_equals",
                    "leftmost", "rightmost",
                )):
                    return "positional"
                if "SELECT_FARTHEST" in serialized:
                    sensitivity = "farthest"
                if "SELECT_ADJACENT" in serialized:
                    sensitivity = "adjacency" if sensitivity == "none" else sensitivity
        return sensitivity

    def _adjacency_directions(self, data: Mapping[str, Any], level: int | str) -> tuple[str, ...]:
        directions: list[str] = []
        for ability in data.get("abilities", ()):
            if str(level) not in ability.get("values_by_level", {}):
                continue
            semantic = self.semantic_entries.get(f"label:{ability.get('label_id')}", {})
            if not str(semantic.get("interpretation_status", "")).startswith("implemented"):
                continue
            for spec in _semantic_effect_specs(semantic):
                program = _semantic_program(spec, self.semantic_patterns) or {}
                for node in program.get("nodes", ()):
                    if node.get("operation") == "SELECT_ADJACENT":
                        directions.extend(str(item) for item in node.get("parameters", {}).get("directions", ()))
        return tuple(dict.fromkeys(directions or ("left", "right")))

    def _support_categories(self, data: Mapping[str, Any], level: int | str) -> tuple[str, ...]:
        """Describe structural support relations without assigning them a score."""
        categories: list[str] = []
        tokens = {
            "SELECT_ADJACENT": "adjacency",
            "MATCH_BRAND": "brand",
            "MATCH_TYPE": "type",
            "MATCH_RARITY": "rarity",
            "SELECT_ALL": "whole_bag",
            "SCHEDULE_EFFECT": "chain",
        }
        for ability in data.get("abilities", ()):
            if str(level) not in ability.get("values_by_level", {}):
                continue
            semantic = self.semantic_entries.get(f"label:{ability.get('label_id')}", {})
            if not str(semantic.get("interpretation_status", "")).startswith("implemented"):
                categories.append("unresolved_structural")
                continue
            for spec in _semantic_effect_specs(semantic):
                program = _semantic_program(spec, self.semantic_patterns)
                serialized = json.dumps(program, sort_keys=True) if program else ""
                categories.extend(category for token, category in tokens.items() if token in serialized)
        return tuple(dict.fromkeys(categories or ("direct",)))

    def _has_contextual_active_ability(self, data: Mapping[str, Any], level: int | str) -> bool:
        for ability in data.get("abilities", ()):
            if str(level) not in ability.get("values_by_level", {}):
                continue
            semantic = self.semantic_entries.get(f"label:{ability.get('label_id')}", {})
            serialized = json.dumps(semantic, sort_keys=True)
            if any(token in serialized for token in ('"terrain"', 'tee', 'fairway', 'rough', 'bunker', 'green')):
                return True
        return False

    def evaluate(
        self,
        spec: CandidateSpec,
        current_club_id: str,
        *,
        mode: EvaluationMode,
        terrain: str | None,
        pending_effects: tuple[DelayedEffect, ...] = (),
        previous_club_id: str | None = None,
    ) -> ComparedBag:
        cache_key = (
            spec.club_ids,
            current_club_id,
            mode.value,
            terrain,
            tuple(repr(item) for item in pending_effects),
            previous_club_id,
        )
        cached = self.evaluation_cache.get(cache_key)
        if cached is not None:
            self.evaluation_cache_hits += 1
            return cached
        self.evaluation_cache_misses += 1
        entries = tuple(BagEntry(self.clubs[club_id], self.levels[club_id]) for club_id in spec.club_ids)
        state = GameState(
            bag=Bag(entries),
            current_club_id=current_club_id,
            previous_club_id=previous_club_id,
            terrain=terrain,
            pending_effects=list(pending_effects),
        )
        effects = [effect for item in entries for ability in item.club.abilities for effect in ability.effects]
        strict_failed = False
        try:
            result = self.engine.evaluate(state, effects, mode=mode)
        except EvaluationError as exc:
            if exc.result is None:
                raise
            result = exc.result
            strict_failed = True
        saved = SavedBag(spec.identifier, spec.identifier, "optimizer_candidate", spec.club_ids, ())
        evaluation = BagEvaluation(saved, state, result, mode, strict_failed, self.engine.mechanisms.names)
        summary = summarize_bag_evaluation(evaluation, spec.club_ids.index(current_club_id) + 1)
        self.evaluation_cache[cache_key] = summary
        return summary


class StrategyCandidateGenerator:
    """Deterministic reduction; it never claims to enumerate the full universe."""

    ACTIVE_POOL_SIZE = 8
    SUPPORT_SETS_PER_ASSIGNMENT = 4
    LEGACY_ORDERS_PER_COMPOSITION = 8
    STRUCTURAL_PAIR_COMPOSITION_LIMIT = 300

    def __init__(self, semantics: MetricSemanticsRegistry | None = None) -> None:
        self.semantics = semantics or MetricSemanticsRegistry.load()
        self.last_generation_stats: dict[str, int] = {}

    def generate(
        self,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        saved_bags: tuple[SavedBag, ...],
        order_mode: str = "structural_exact",
        max_generated: int | None = None,
    ) -> tuple[tuple[CandidateSpec, ...], int, int]:
        definition = strategy.definition
        eligible_ids = tuple(runtime.clubs)
        role_count = len(definition.expected_active_roles)
        if len(eligible_ids) < definition.bag_size:
            raise StrategyOptimizationError("Not enough eligible owned clubs to build a bag")
        full_role_pools = tuple(
            tuple(club_id for club_id in eligible_ids if _matches_step(runtime.clubs[club_id], step))
            for step in definition.sequence
        )
        active_theoretical = sum(
            1
            for assigned in product(*full_role_pools)
            if definition.allow_active_club_reuse or len(set(assigned)) == len(assigned)
        )
        remaining = len(eligible_ids) - (0 if definition.allow_active_club_reuse else role_count)
        support_theoretical = math.comb(remaining, definition.available_support_clubs)
        theoretical = active_theoretical * support_theoretical * math.factorial(definition.bag_size)

        generated: dict[tuple[Any, ...], CandidateSpec] = {}
        searched_order_spaces: set[tuple[Any, ...]] = set()
        permutations_eliminated = 0
        budget_reached = False
        saved_club_ids = tuple(dict.fromkeys(club_id for bag in saved_bags for club_id in bag.club_ids))
        references = self.reference_candidates(strategy, runtime, saved_bags, order_mode)
        for spec in references:
            key = (spec.club_ids, tuple(spec.active_assignments.items()))
            generated[key] = spec

        active_pools = tuple(
            self._pareto_active_pool(runtime, pool, step, saved_club_ids)
            for pool, step in zip(full_role_pools, definition.sequence, strict=True)
        )
        active_pool_union = tuple(dict.fromkeys(item for pool in active_pools for item in pool))
        assignment_limit = min(max_generated or 512, 512)
        assignments = tuple(
            assigned for assigned in self._fair_assignments(active_pools, assignment_limit * 2)
            if definition.allow_active_club_reuse or len(set(assigned)) == len(assigned)
        )[:assignment_limit]
        support_choices = {
            assigned: self._support_sets(
                runtime, eligible_ids, assigned,
                definition.available_support_clubs, active_pool_union,
            )
            for assigned in assignments
        }
        for support_index in range(self.SUPPORT_SETS_PER_ASSIGNMENT):
            if budget_reached:
                break
            for assigned in assignments:
                choices = support_choices[assigned]
                if support_index >= len(choices):
                    continue
                support_set = choices[support_index]
                physical = tuple(dict.fromkeys((*assigned, *support_set)))
                if len(physical) != definition.bag_size:
                    continue
                order_space = (tuple(sorted(physical)), assigned)
                if order_space in searched_order_spaces:
                    continue
                searched_order_spaces.add(order_space)
                selected_orders = self._orders_for(physical, runtime, order_mode)
                global_count = sum(item.provenance == "global_search" for item in generated.values())
                if max_generated is not None and global_count and global_count + len(selected_orders) > max_generated:
                    budget_reached = True
                    break
                permutations_eliminated += math.factorial(definition.bag_size) - len(selected_orders)
                for order, reason in selected_orders:
                    self._add(generated, order, definition, assigned, "global_search", reason, len(selected_orders))
            if budget_reached:
                break
        spaces = {item.order_space_id for item in generated.values()}
        theoretical_orders = len(spaces) * math.factorial(definition.bag_size)
        distinct_orders = len(generated)
        self.last_generation_stats = {
            "compositions": len(spaces),
            "permutations_theoretical": theoretical_orders,
            "permutations_distinct": distinct_orders,
            "permutations_equivalent": theoretical_orders - distinct_orders,
            "budget_reached": int(budget_reached),
            "inventory": len(eligible_ids),
            "active_potential": sum(len(pool) for pool in full_role_pools),
            "active_assignments": len(assignments),
            "active_assignments_theoretical": active_theoretical,
            "theoretical_compositions": active_theoretical * support_theoretical,
            "reference_candidates": len(references),
            "global_candidates": sum(item.provenance == "global_search" for item in generated.values()),
        }
        return tuple(generated.values()), theoretical, permutations_eliminated

    def reference_candidates(
        self,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        saved_bags: tuple[SavedBag, ...],
        order_mode: str = "structural_exact",
    ) -> tuple[CandidateSpec, ...]:
        """Build every compatible saved bag independently from global reduction."""
        target: dict[tuple[Any, ...], CandidateSpec] = {}
        definition = strategy.definition
        for bag in saved_bags:
            if len(bag.club_ids) != definition.bag_size or any(item not in runtime.clubs for item in bag.club_ids):
                continue
            used: set[str] = set()
            assigned: list[str] = []
            for step in definition.sequence:
                club_id = next(
                    (item for item in bag.club_ids if (definition.allow_active_club_reuse or item not in used) and _matches_step(runtime.clubs[item], step)),
                    None,
                )
                if club_id is None:
                    assigned = []
                    break
                assigned.append(club_id)
                used.add(club_id)
            if assigned:
                selected_orders = self._orders_for(bag.club_ids, runtime, order_mode)
                for order, reason in selected_orders:
                    self._add(target, order, definition, tuple(assigned), "reference_bag", reason, len(selected_orders))
        return tuple(target.values())

    def generate_local(
        self,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        bag: SavedBag,
        *,
        replacement_depth: int = 1,
        fixed_club_id: str | None = None,
        order_mode: str = "structural_exact",
        required_club_ids: tuple[str, ...] = (),
        excluded_club_ids: tuple[str, ...] = (),
        locked_positions: Mapping[int, str] | None = None,
        fixed_step_id: str | None = None,
        keep_current_putter: bool = False,
    ) -> tuple[CandidateSpec, ...]:
        """Enumerate one replacement and structurally justified replacement pairs."""
        definition = strategy.definition
        if len(bag.club_ids) != definition.bag_size or any(item not in runtime.clubs for item in bag.club_ids):
            raise StrategyOptimizationError("Le sac sélectionné n'est pas évaluable avec l'inventaire actuel")
        if fixed_club_id is not None and fixed_club_id not in runtime.clubs:
            raise StrategyOptimizationError("Le club fixé n'est pas disponible dans l'inventaire actuel")
        required = set(required_club_ids)
        excluded = set(excluded_club_ids)
        locks = dict(locked_positions or {})
        if any(position < 1 or position > definition.bag_size for position in locks):
            raise StrategyOptimizationError("Une position verrouillée est hors du sac")
        if required & excluded:
            raise StrategyOptimizationError("Un club ne peut pas être à la fois obligatoire et exclu")
        if any(position < 1 or position > definition.bag_size for position in locks):
            raise StrategyOptimizationError("Une position verrouillée est hors du sac")
        if any(club_id not in bag.club_ids for club_id in locks.values()):
            raise StrategyOptimizationError("Une position ne peut verrouiller qu'un club du sac actuel")
        original_assignment = self._preferred_assignment(definition, runtime, bag.club_ids)
        if keep_current_putter:
            finish_index = next(
                (index for index, step in enumerate(definition.sequence) if step.function.identifier == "finish"),
                None,
            )
            if finish_index is not None and original_assignment:
                required.add(original_assignment[finish_index])
        if fixed_club_id is not None:
            required.add(fixed_club_id)

        compositions: dict[tuple[str, ...], tuple[str, tuple[str, ...]]] = {}

        def add_composition(values: tuple[str, ...], origin: str) -> None:
            if len(set(values)) != definition.bag_size:
                return
            if not required.issubset(values) or excluded.intersection(values):
                return
            compositions.setdefault(tuple(sorted(values)), (origin, values))

        seed = bag.club_ids
        if fixed_club_id is not None and fixed_club_id not in seed:
            forced_step = next(
                (step for step in definition.sequence if step.identifier == fixed_step_id),
                definition.sequence[0],
            )
            replace_index = next(
                (index for index, club_id in enumerate(seed) if _matches_step(runtime.clubs[club_id], forced_step)),
                0,
            )
            seed = tuple(fixed_club_id if index == replace_index else club_id for index, club_id in enumerate(seed))
        add_composition(seed, "reference_neighborhood")
        preferred_assignment = self._preferred_assignment(
            definition, runtime, seed, forced_first=fixed_club_id, forced_step_id=fixed_step_id,
        )
        eligible = tuple(item for item in runtime.clubs if item not in excluded)
        for index, outgoing in enumerate(seed):
            if outgoing == fixed_club_id:
                continue
            for incoming in eligible:
                if incoming in seed:
                    continue
                changed = tuple(incoming if position == index else club_id for position, club_id in enumerate(seed))
                add_composition(changed, "reference_neighborhood")

        pair_compositions = 0
        if replacement_depth >= 2:
            outside = tuple(item for item in eligible if item not in seed)
            pair_limit_reached = False
            for removed in combinations(range(definition.bag_size), 2):
                if fixed_club_id is not None and any(seed[index] == fixed_club_id for index in removed):
                    continue
                for incoming in combinations(outside, 2):
                    missing_required = required - set(seed)
                    if not missing_required.issubset(incoming) and not self._pair_has_structural_synergy(runtime, incoming, seed, removed):
                        continue
                    changed = list(seed)
                    for index, club_id in zip(removed, incoming, strict=True):
                        changed[index] = club_id
                    add_composition(tuple(changed), "reference_neighborhood")
                    pair_compositions += 1
                    if pair_compositions >= self.STRUCTURAL_PAIR_COMPOSITION_LIMIT:
                        pair_limit_reached = True
                        break
                if pair_limit_reached:
                    break

        generated: dict[tuple[Any, ...], CandidateSpec] = {}
        for origin, composition in compositions.values():
            assignment = self._preferred_assignment(
                definition,
                runtime,
                composition,
                forced_first=fixed_club_id,
                forced_step_id=fixed_step_id,
                preferred=preferred_assignment,
            )
            if assignment:
                selected_orders = self._orders_for(composition, runtime, order_mode)
                for order, reason in selected_orders:
                    if any(order[position - 1] != club_id for position, club_id in locks.items()):
                        continue
                    matching_orders = sum(
                        not any(item[position - 1] != club_id for position, club_id in locks.items())
                        for item, _ in selected_orders
                    )
                    self._add(generated, order, definition, assignment, origin, reason, matching_orders)
        self.last_generation_stats = {
            "inventory": len(eligible),
            "reference_candidates": 0,
            "global_candidates": 0,
            "local_compositions": len(compositions),
            "local_candidates": len(generated),
            "replacement_depth": replacement_depth,
            "pair_compositions": pair_compositions,
            "pair_composition_limit_reached": int(
                replacement_depth >= 2 and pair_compositions >= self.STRUCTURAL_PAIR_COMPOSITION_LIMIT
            ),
        }
        return tuple(generated.values())

    def generate_around(
        self,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        fixed_club_id: str,
        *,
        fixed_step_id: str | None = None,
        order_mode: str = "structural_exact",
        max_generated: int = 2000,
        required_club_ids: tuple[str, ...] = (),
        excluded_club_ids: tuple[str, ...] = (),
    ) -> tuple[CandidateSpec, ...]:
        """Build a bounded global neighborhood with one club active on a chosen compatible step."""
        definition = strategy.definition
        if fixed_club_id not in runtime.clubs:
            raise StrategyOptimizationError("Le club fixé n'est pas disponible dans l'inventaire actuel")
        eligible = tuple(item for item in runtime.clubs if item not in set(excluded_club_ids))
        step_index = next(
            (
                index for index, step in enumerate(definition.sequence)
                if (fixed_step_id is None or step.identifier == fixed_step_id)
                and _matches_step(runtime.clubs[fixed_club_id], step)
            ),
            None,
        )
        if step_index is None:
            raise StrategyOptimizationError("Le club choisi n'est pas compatible avec le rôle actif demandé")
        pools = tuple(
            (fixed_club_id,) if index == step_index else self._pareto_active_pool(runtime, tuple(
                item for item in eligible if _matches_step(runtime.clubs[item], step)
            ), step)
            for index, step in enumerate(definition.sequence)
        )
        assignments = tuple(
            values for values in self._fair_assignments(pools, 512)
            if definition.allow_active_club_reuse or len(set(values)) == len(values)
        )
        required = set(required_club_ids) | {fixed_club_id}
        generated: dict[tuple[Any, ...], CandidateSpec] = {}
        spaces: set[tuple[str, ...]] = set()
        supports_by_assignment: dict[tuple[str, ...], tuple[tuple[str, ...], ...]] = {}
        for assigned in assignments:
            support_sets = self._support_sets(
                runtime, eligible, assigned, definition.available_support_clubs,
                tuple(dict.fromkeys(item for pool in pools for item in pool)),
            )
            forced_supports = tuple(sorted(item for item in required if item not in assigned))
            if len(forced_supports) <= definition.available_support_clubs:
                fill = tuple(
                    item for item in eligible
                    if item not in assigned and item not in forced_supports
                )[: definition.available_support_clubs - len(forced_supports)]
                if len((*forced_supports, *fill)) == definition.available_support_clubs:
                    support_sets = (tuple((*forced_supports, *fill)), *support_sets)
            supports_by_assignment[assigned] = tuple(dict.fromkeys(support_sets))
        budget_reached = False
        schedule = sorted(
            (
                (assignment_index, support_index)
                for assignment_index, assigned in enumerate(assignments)
                for support_index in range(len(supports_by_assignment[assigned]))
            ),
            key=lambda item: (max(item), sum(item), item),
        )
        for assignment_index, support_index in schedule:
            assigned = assignments[assignment_index]
            supports = supports_by_assignment[assigned][support_index]
            composition = tuple(dict.fromkeys((*assigned, *supports)))
            if len(composition) != definition.bag_size or not required.issubset(composition):
                continue
            selected_orders = self._orders_for(composition, runtime, order_mode)
            if generated and len(generated) + len(selected_orders) > max_generated:
                budget_reached = True
                continue
            spaces.add(tuple(sorted(composition)))
            for order, reason in selected_orders:
                self._add(
                    generated, order, definition, assigned, "around_club",
                    reason, len(selected_orders),
                )
            if len(generated) >= max_generated:
                break
        self.last_generation_stats = {
            "inventory": len(eligible),
            "active_assignments": len(assignments),
            "active_assignments_theoretical": math.prod(len(pool) for pool in pools),
            "compositions": len(spaces),
            "permutations_theoretical": len(spaces) * math.factorial(definition.bag_size),
            "permutations_distinct": len(generated),
            "permutations_equivalent": len(spaces) * math.factorial(definition.bag_size) - len(generated),
            "budget_reached": int(budget_reached or len(generated) >= max_generated),
        }
        return tuple(generated.values())

    def generate_builder(
        self,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        *,
        club_roles: Mapping[str, str],
        excluded_club_ids: tuple[str, ...] = (),
        locked_positions: Mapping[int, str] | None = None,
        order_mode: str = "structural_exact",
        max_generated: int = 4000,
    ) -> tuple[CandidateSpec, ...]:
        """Build bags around any number of required clubs and optional active roles."""
        definition = strategy.definition
        excluded = set(excluded_club_ids)
        roles = dict(club_roles)
        required = set(roles)
        valid_roles = {"auto", "support", *(step.identifier for step in definition.sequence)}
        unknown_roles = sorted(set(roles.values()) - valid_roles)
        if unknown_roles:
            raise StrategyOptimizationError("Rôle de club inconnu : " + ", ".join(unknown_roles))
        if required & excluded:
            raise StrategyOptimizationError("Un club ne peut pas être à la fois utilisé et exclu")
        if len(required) > definition.bag_size:
            raise StrategyOptimizationError("Le nombre de clubs imposés dépasse la taille du sac")
        unavailable = sorted(required - set(runtime.clubs))
        if unavailable:
            raise StrategyOptimizationError("Clubs imposés indisponibles : " + ", ".join(unavailable))
        forced_by_step: dict[str, str] = {}
        for club_id, role in roles.items():
            if role in {"auto", "support"}:
                continue
            if role in forced_by_step:
                raise StrategyOptimizationError(f"Deux clubs ne peuvent pas occuper l'étape {role}")
            step = next(item for item in definition.sequence if item.identifier == role)
            if not _matches_step(runtime.clubs[club_id], step):
                raise StrategyOptimizationError(
                    f"{runtime.clubs[club_id].name} n'est pas compatible avec l'étape {step.name}"
                )
            forced_by_step[role] = club_id
        eligible = tuple(item for item in runtime.clubs if item not in excluded)
        support_only = {club_id for club_id, role in roles.items() if role == "support"}
        auto_required = {club_id for club_id, role in roles.items() if role == "auto"}
        pools: list[tuple[str, ...]] = []
        for step in definition.sequence:
            forced = forced_by_step.get(step.identifier)
            if forced:
                pools.append((forced,))
                continue
            compatible = tuple(
                item for item in eligible
                if item not in support_only and _matches_step(runtime.clubs[item], step)
            )
            preferred_auto = tuple(item for item in auto_required if item in compatible)
            pools.append(tuple(dict.fromkeys((
                *preferred_auto,
                *self._pareto_active_pool(runtime, compatible, step),
            ))))
        assignments = tuple(
            assigned for assigned in self._fair_assignments(tuple(pools), 1024)
            if (definition.allow_active_club_reuse or len(set(assigned)) == len(assigned))
            and all(
                roles.get(club_id) in {None, "auto", step.identifier}
                for step, club_id in zip(definition.sequence, assigned, strict=True)
            )
        )
        generated: dict[tuple[Any, ...], CandidateSpec] = {}
        spaces: set[tuple[str, ...]] = set()
        locks = dict(locked_positions or {})
        if any(position < 1 or position > definition.bag_size for position in locks):
            raise StrategyOptimizationError("Une position verrouillée est hors du sac")
        if any(club_id not in required for club_id in locks.values()):
            raise StrategyOptimizationError("Une position ne peut verrouiller qu'un club imposé")
        if len(set(locks.values())) != len(locks):
            raise StrategyOptimizationError("Un même club ne peut pas être verrouillé à plusieurs positions")
        budget_reached = False
        active_pool = tuple(dict.fromkeys(item for pool in pools for item in pool))
        compositions_by_assignment: dict[tuple[str, ...], tuple[tuple[str, ...], ...]] = {}
        support_pool_truncated_assignments = 0
        for assigned in assignments:
            forced_supports = tuple(sorted(required - set(assigned)))
            support_count = definition.bag_size - len(set(assigned))
            if len(forced_supports) > support_count:
                continue
            fill_count = support_count - len(forced_supports)
            base_sets = self._support_sets(runtime, eligible, assigned, support_count, active_pool)
            structural = tuple(self.support_potential(runtime, assigned))
            support_candidates = tuple(dict.fromkeys(
                item
                for values in base_sets
                for item in values
                if item not in assigned and item not in forced_supports
            ))
            fallback = tuple(
                item for item in eligible
                if item not in assigned and item not in forced_supports
            )
            full_pool = tuple(dict.fromkeys((*support_candidates, *structural, *fallback)))
            if len(full_pool) > 24:
                support_pool_truncated_assignments += 1
            pool = full_pool[:24]
            if fill_count == 0:
                fills = ((),)
            else:
                seeded: list[tuple[str, ...]] = []
                for values in base_sets:
                    fill = tuple(
                        item for item in values
                        if item not in assigned and item not in forced_supports
                    )[:fill_count]
                    if len(fill) == fill_count:
                        seeded.append(fill)
                for anchor in structural:
                    fill = tuple(dict.fromkeys((
                        anchor,
                        *(item for item in pool if item != anchor),
                    )))[:fill_count]
                    if len(fill) == fill_count:
                        seeded.append(fill)
                fills = tuple(dict.fromkeys((*seeded, *combinations(pool, fill_count))))
            compositions = []
            for fill in fills:
                composition = tuple(dict.fromkeys((*assigned, *forced_supports, *fill)))
                if len(composition) != definition.bag_size or not required.issubset(composition):
                    continue
                compositions.append(composition)
            compositions_by_assignment[assigned] = tuple(dict.fromkeys(compositions))
        schedule = sorted(
            (
                (assignment_index, composition_index)
                for assignment_index, assigned in enumerate(assignments)
                for composition_index in range(len(compositions_by_assignment.get(assigned, ())))
            ),
            # Cover every active assignment once before spending the budget on
            # a second support set for any assignment.
            key=lambda item: (item[1], item[0]),
        )
        position_lock_removed = 0
        budget_removed = 0
        for assignment_index, composition_index in schedule:
            assigned = assignments[assignment_index]
            composition = compositions_by_assignment[assigned][composition_index]
            selected_orders = self._orders_for(composition, runtime, order_mode)
            matching = tuple(
                (order, reason) for order, reason in selected_orders
                if not any(order[position - 1] != club_id for position, club_id in locks.items())
            )
            if not matching:
                position_lock_removed += 1
                continue
            if generated and len(generated) + len(matching) > max_generated:
                budget_reached = True
                budget_removed += 1
                continue
            spaces.add(tuple(sorted(composition)))
            for order, reason in matching:
                self._add(generated, order, definition, assigned, "interactive_builder", reason, len(matching))
            if len(generated) >= max_generated:
                break
        self.last_generation_stats = {
            "inventory": len(eligible),
            "active_assignments": len(assignments),
            "active_assignments_theoretical": math.prod(len(pool) for pool in pools),
            "compositions": len(spaces),
            "permutations_theoretical": len(spaces) * math.factorial(definition.bag_size),
            "permutations_distinct": len(generated),
            "permutations_equivalent": len(spaces) * math.factorial(definition.bag_size) - len(generated),
            "budget_reached": int(budget_reached),
            "theoretical_compositions": len(schedule),
            "support_clubs_considered": len(active_pool),
            "position_lock_removed": position_lock_removed,
            "budget_removed": budget_removed,
            "support_pool_truncated_assignments": support_pool_truncated_assignments,
        }
        return tuple(generated.values())

    @staticmethod
    def _preferred_assignment(
        definition: Any,
        runtime: _RuntimeEvaluator,
        club_ids: tuple[str, ...],
        *,
        forced_first: str | None = None,
        forced_step_id: str | None = None,
        preferred: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        used: set[str] = set()
        assigned: list[str] = []
        for index, step in enumerate(definition.sequence):
            forced_index = (
                next((i for i, item in enumerate(definition.sequence) if item.identifier == forced_step_id), 0)
                if forced_first is not None else None
            )
            forced = forced_first if index == forced_index else None
            old = preferred[index] if index < len(preferred) else None
            club_id = next(
                (
                    item for item in (forced, old, *club_ids)
                    if item is not None
                    and item in club_ids
                    and (definition.allow_active_club_reuse or item not in used)
                    and _matches_step(runtime.clubs[item], step)
                ),
                None,
            )
            if club_id is None:
                return ()
            assigned.append(club_id)
            used.add(club_id)
        return tuple(assigned)

    @staticmethod
    def _assignments_for(
        definition: Any,
        runtime: _RuntimeEvaluator,
        club_ids: tuple[str, ...],
        forced_first: str | None = None,
    ) -> tuple[tuple[str, ...], ...]:
        pools = []
        for index, step in enumerate(definition.sequence):
            if index == 0 and forced_first is not None:
                pool = (forced_first,) if forced_first in club_ids and _matches_step(runtime.clubs[forced_first], step) else ()
            else:
                pool = tuple(item for item in club_ids if _matches_step(runtime.clubs[item], step))
            pools.append(pool)
        return tuple(
            assigned for assigned in product(*pools)
            if definition.allow_active_club_reuse or len(set(assigned)) == len(assigned)
        )

    @staticmethod
    def _pair_has_structural_synergy(
        runtime: _RuntimeEvaluator,
        incoming: tuple[str, str],
        seed: tuple[str, ...],
        removed: tuple[int, int],
    ) -> bool:
        left, right = (runtime.clubs[item] for item in incoming)
        remaining = [runtime.clubs[item] for index, item in enumerate(seed) if index not in removed]
        related = (
            left.brand == right.brand
            or left.club_type == right.club_type
            or left.rarity == right.rarity
            or incoming[0] in runtime.support_capable_ids
            or incoming[1] in runtime.support_capable_ids
        )
        helps_remaining = any(
            club.brand in {left.brand, right.brand}
            or club.club_type in {left.club_type, right.club_type}
            or club.rarity in {left.rarity, right.rarity}
            for club in remaining
        )
        return related and helps_remaining

    @staticmethod
    def _fair_assignments(
        pools: tuple[tuple[str, ...], ...],
        limit: int | None = None,
    ) -> tuple[tuple[str, ...], ...]:
        """Return the same fair diagonal prefix without materializing the full product."""
        if not pools or any(not pool for pool in pools):
            return ()
        target = limit if limit is not None else math.prod(len(pool) for pool in pools)
        result: list[tuple[str, ...]] = []
        for maximum_index in range(max(len(pool) for pool in pools)):
            ranges = tuple(range(min(len(pool), maximum_index + 1)) for pool in pools)
            shell = [indices for indices in product(*ranges) if max(indices) == maximum_index]
            shell.sort(key=lambda indices: (sum(indices), indices))
            for indices in shell:
                result.append(tuple(pool[index] for pool, index in zip(pools, indices, strict=True)))
                if len(result) >= target:
                    return tuple(result)
        return tuple(result)

    def _pareto_active_pool(
        self,
        runtime: _RuntimeEvaluator,
        eligible_ids: tuple[str, ...],
        step: ShotStep,
        saved_club_ids: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        metrics = tuple(
            item.metric for item in step.metric_uses
            if _metric_relevance(step, item.metric, self.semantics) == "objective"
            and item.metric in {"power", "control", "spin"}
        ) or ("power", "control")

        def values(club_id: str) -> dict[str, float]:
            raw = runtime.clubs[club_id].stats_at(runtime.levels[club_id]).as_dict()
            return {metric: float(raw[metric]) for metric in metrics if metric in raw}

        frontier = [
            club_id for club_id in eligible_ids
            if not any(
                _dominates_values(values(other), values(club_id))
                for other in eligible_ids if other != club_id
            )
        ]
        best_each = [
            max(eligible_ids, key=lambda club_id: (values(club_id).get(metric, -math.inf), club_id))
            for metric in metrics
        ]
        by_type: list[str] = []
        for club_type in sorted({runtime.clubs[item].club_type for item in eligible_ids}):
            typed = tuple(item for item in eligible_ids if runtime.clubs[item].club_type == club_type)
            for metric in metrics:
                by_type.append(max(typed, key=lambda club_id: (values(club_id).get(metric, -math.inf), club_id)))
        saved = [item for item in saved_club_ids if item in eligible_ids]
        contextual_or_receiving = [
            item for item in eligible_ids
            if item in runtime.contextual_active_ids
            or any(
                runtime.clubs[item].brand == runtime.clubs[support].brand
                or runtime.clubs[item].club_type == runtime.clubs[support].club_type
                or runtime.clubs[item].rarity == runtime.clubs[support].rarity
                for support in runtime.support_capable_ids
            )
        ]
        selected = tuple(dict.fromkeys((*frontier, *best_each, *by_type, *saved, *contextual_or_receiving)))
        grouped = {
            club_type: [item for item in selected if runtime.clubs[item].club_type == club_type]
            for club_type in sorted({runtime.clubs[item].club_type for item in selected})
        }
        interleaved: list[str] = []
        for index in range(max((len(items) for items in grouped.values()), default=0)):
            interleaved.extend(items[index] for items in grouped.values() if index < len(items))
        return tuple(interleaved)

    def _support_sets(
        self,
        runtime: _RuntimeEvaluator,
        eligible_ids: tuple[str, ...],
        assigned: tuple[str, ...],
        count: int,
        active_pool: tuple[str, ...],
    ) -> tuple[tuple[str, ...], ...]:
        if count == 0:
            return ((),)
        assigned_set = set(assigned)
        active_clubs = [runtime.clubs[item] for item in assigned_set]
        potential = self.support_potential(runtime, assigned)
        outward = [item for item in eligible_ids if item not in assigned_set and item in potential]
        matching = [
            item for item in eligible_ids
            if item not in assigned_set
            and any(
                runtime.clubs[item].brand == active.brand
                or runtime.clubs[item].club_type == active.club_type
                or runtime.clubs[item].rarity == active.rarity
                for active in active_clubs
            )
        ]
        pareto = [item for item in active_pool if item not in assigned_set]
        fallback = [item for item in eligible_ids if item not in assigned_set]
        candidates = [outward, outward[count:], matching, pareto, fallback]
        result: list[tuple[str, ...]] = []
        for values in candidates:
            selected = tuple(dict.fromkeys(values))[:count]
            if len(selected) == count and selected not in result:
                result.append(selected)
            if len(result) >= self.SUPPORT_SETS_PER_ASSIGNMENT:
                break
        return tuple(result)

    @staticmethod
    def support_potential(
        runtime: _RuntimeEvaluator,
        active_ids: tuple[str, ...] | set[str],
    ) -> dict[str, tuple[str, ...]]:
        """Return demonstrable support relations for active clubs, never a synthetic score."""
        active_set = set(active_ids)
        active_clubs = tuple(runtime.clubs[item] for item in active_set)
        result: dict[str, tuple[str, ...]] = {}
        for club_id, club in runtime.clubs.items():
            if club_id in active_set:
                continue
            categories = list(runtime.support_categories.get(club_id, ()))
            if any(club.brand == active.brand for active in active_clubs):
                categories.append("brand")
            if any(club.club_type == active.club_type for active in active_clubs):
                categories.append("type")
            if any(club.rarity == active.rarity for active in active_clubs):
                categories.append("rarity")
            if categories:
                result[club_id] = tuple(dict.fromkeys(categories))
        return result

    def _representative_orders(self, club_ids: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
        values = tuple(permutations(club_ids))
        if len(values) <= self.LEGACY_ORDERS_PER_COMPOSITION:
            return values
        indices = tuple(
            round(index * (len(values) - 1) / (self.LEGACY_ORDERS_PER_COMPOSITION - 1))
            for index in range(self.LEGACY_ORDERS_PER_COMPOSITION)
        )
        return tuple(values[index] for index in dict.fromkeys(indices))

    def _orders_for(
        self,
        club_ids: tuple[str, ...],
        runtime: _RuntimeEvaluator,
        mode: str,
    ) -> tuple[tuple[tuple[str, ...], str], ...]:
        if mode == "legacy_reduced":
            return tuple((order, "legacy_representative_sample") for order in self._representative_orders(club_ids))
        if mode == "full_120":
            return tuple((order, "full_permutation_enumeration") for order in permutations(club_ids))
        if mode != "structural_exact":
            raise StrategyOptimizationError(f"Unsupported order mode: {mode}")
        if not any(club_id in runtime.order_sensitive_ids for club_id in club_ids):
            return ((tuple(club_ids), "all_clubs_proven_order_insensitive"),)
        if not hasattr(runtime, "order_sensitivity"):
            return tuple((order, "position_sensitive_semantics_present") for order in permutations(club_ids))
        orders = tuple(permutations(club_ids))
        if any(runtime.order_sensitivity.get(club_id) == "positional" for club_id in club_ids):
            return tuple((order, "position_sensitive_semantics_present") for order in orders)
        representatives: dict[tuple[Any, ...], tuple[str, ...]] = {}
        sensitive = tuple(club_id for club_id in club_ids if runtime.order_sensitivity.get(club_id) == "adjacency")
        farthest = tuple(club_id for club_id in club_ids if runtime.order_sensitivity.get(club_id) == "farthest")
        for order in orders:
            signature = []
            for club_id in sensitive:
                position = order.index(club_id)
                directions = runtime.order_neighbor_directions.get(club_id, ("left", "right"))
                signature.append((club_id, *(
                    order[position - 1] if direction == "left" and position else
                    order[position + 1] if direction == "right" and position + 1 < len(order) else None
                    for direction in directions
                )))
            for club_id in farthest:
                position = order.index(club_id)
                distances = {item: abs(index - position) for index, item in enumerate(order) if item != club_id}
                maximum = max(distances.values())
                signature.append((club_id, "farthest", tuple(
                    item for item, distance in distances.items() if distance == maximum
                )))
            representatives.setdefault(tuple(signature), order)
        return tuple(
            (order, "equivalent_non_adjacent_support_permutations")
            for order in representatives.values()
        )

    def _add(
        self,
        target: dict[tuple[Any, ...], CandidateSpec],
        order: tuple[str, ...],
        definition: Any,
        assigned: tuple[str, ...],
        provenance: str,
        equivalence_reason: str,
        structurally_distinct_permutations: int | None = None,
    ) -> None:
        assignments = dict(zip((step.identifier for step in definition.sequence), assigned, strict=True))
        key = (order, tuple(assignments.items()))
        if key in target:
            return
        digest = sha256(repr(key).encode("utf-8")).hexdigest()[:12]
        sensitive = equivalence_reason in {"position_sensitive_semantics_present", "full_permutation_enumeration"}
        distinct = structurally_distinct_permutations if structurally_distinct_permutations is not None else (
            math.factorial(len(order)) if sensitive
            else len(self._representative_orders(order)) if equivalence_reason == "legacy_representative_sample"
            else 1 if equivalence_reason == "all_clubs_proven_order_insensitive"
            else math.factorial(len(order))
        )
        target[key] = CandidateSpec(
            f"strategy-{digest}", order, assignments, provenance,
            sha256(repr((tuple(sorted(order)), tuple(assignments.items()))).encode("utf-8")).hexdigest()[:12],
            math.factorial(len(order)),
            distinct,
            equivalence_reason,
        )


class StrategyOptimizer:
    def __init__(
        self,
        *,
        user_data_path: str | Path = "data/pga_shootout.sqlite",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        strategy_registry_path: str | Path = "data/strategies/strategies.json",
        metric_semantics_path: str | Path = "data/strategies/metric_semantics.json",
        optimization_policy_path: str | Path = "data/strategies/optimization_policies.json",
    ) -> None:
        self.user_data_path = Path(user_data_path)
        self.catalog_path = Path(catalog_path)
        self.registry_path = Path(strategy_registry_path)
        self.metric_semantics = MetricSemanticsRegistry.load(metric_semantics_path)
        policy_path = Path(optimization_policy_path)
        self.optimization_policy = (
            json.loads(policy_path.read_text(encoding="utf-8")) if policy_path.exists() else {}
        )
        self.generator = StrategyCandidateGenerator(self.metric_semantics)
        initial = load_user_data(self.user_data_path)
        self._inventory_snapshot = self._inventory_signature(initial.inventory.entries)
        # Session-only guardrail. Entries are additionally scoped by the exact
        # inventory, catalog, strategy and evaluation context before reuse.
        self._known_candidates: dict[tuple[Any, ...], dict[tuple[Any, ...], CandidateSpec]] = {}

    @staticmethod
    def _inventory_signature(
        entries: tuple[InventoryEntry, ...],
    ) -> dict[str, tuple[bool, int | None, int | None]]:
        return {
            item.club_id: (item.unlocked, item.current_level, item.cards_owned)
            for item in entries
        }

    def _inventory_changes(self, entries: tuple[InventoryEntry, ...]) -> InventoryChangeSet:
        current = self._inventory_signature(entries)
        previous = self._inventory_snapshot
        all_ids = sorted(set(previous) | set(current))
        changes = InventoryChangeSet(
            added_club_ids=tuple(
                club_id for club_id in all_ids
                if current.get(club_id, (False, None, None))[0]
                and not previous.get(club_id, (False, None, None))[0]
            ),
            removed_club_ids=tuple(
                club_id for club_id in all_ids
                if previous.get(club_id, (False, None, None))[0]
                and not current.get(club_id, (False, None, None))[0]
            ),
            level_changes={
                club_id: (previous[club_id][1], current[club_id][1])
                for club_id in all_ids if club_id in previous and club_id in current
                and previous[club_id][1] != current[club_id][1]
            },
            cards_changes={
                club_id: (previous[club_id][2], current[club_id][2])
                for club_id in all_ids if club_id in previous and club_id in current
                and previous[club_id][2] != current[club_id][2]
            },
        )
        self._inventory_snapshot = current
        return changes

    @staticmethod
    def _candidate_satisfies_builder_constraints(
        spec: CandidateSpec,
        roles: Mapping[str, str],
        excluded_club_ids: tuple[str, ...],
        locked_positions: Mapping[int, str] | None,
    ) -> bool:
        composition = set(spec.club_ids)
        if not set(roles).issubset(composition) or composition.intersection(excluded_club_ids):
            return False
        if any(spec.club_ids[position - 1] != club_id for position, club_id in (locked_positions or {}).items()):
            return False
        active = set(spec.active_assignments.values())
        for club_id, role in roles.items():
            if role == "support" and club_id in active:
                return False
            if role not in {"auto", "support"} and spec.active_assignments.get(role) != club_id:
                return False
        return True

    @staticmethod
    def _merge_candidate_specs(*groups: tuple[CandidateSpec, ...]) -> tuple[CandidateSpec, ...]:
        merged: dict[tuple[Any, ...], CandidateSpec] = {}
        for group in groups:
            for item in group:
                key = (item.club_ids, tuple(item.active_assignments.items()))
                merged.setdefault(key, item)
        return tuple(merged.values())

    def _known_context_key(
        self,
        request: StrategyOptimizationRequest,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        inventory_signature: Mapping[str, tuple[bool, int | None, int | None]],
    ) -> tuple[Any, ...]:
        return (
            tuple(sorted(inventory_signature.items())),
            runtime.catalog_version,
            strategy.definition.identifier,
            strategy.definition.version,
            strategy.applied_variant_ids,
            request.scenario_level,
            request.mode.value,
            request.order_mode,
        )

    def _compatible_known_candidates(
        self,
        context_key: tuple[Any, ...],
        roles: Mapping[str, str],
        request: StrategyOptimizationRequest,
    ) -> tuple[CandidateSpec, ...]:
        compatible = []
        for item in self._known_candidates.get(context_key, {}).values():
            if self._candidate_satisfies_builder_constraints(
                item, roles, request.excluded_club_ids, request.locked_positions,
            ):
                compatible.append(replace(item, provenance="known_candidate"))
        return tuple(compatible)

    def _remember_candidates(
        self,
        context_key: tuple[Any, ...],
        candidates: tuple[_QuickCandidate, ...],
    ) -> None:
        target = self._known_candidates.setdefault(context_key, {})
        for candidate in candidates:
            spec = candidate.spec
            key = (spec.club_ids, tuple(spec.active_assignments.items()))
            target[key] = replace(spec, provenance="known_candidate")
        # The cache is a guardrail, not an unbounded second search index.
        while len(target) > 100:
            target.pop(next(iter(target)))

    @staticmethod
    def _club_diagnostic(
        club_id: str,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
    ) -> InventoryClubDiagnostic:
        club = runtime.clubs[club_id]
        level = runtime.levels[club_id]
        raw = runtime.catalog_document["clubs"][club_id]
        abilities: list[InventoryAbilityDiagnostic] = []
        for ability in raw.get("abilities", ()):
            value = ability.get("values_by_level", {}).get(str(level))
            if value is None:
                continue
            label_id = str(ability.get("label_id"))
            semantic = runtime.semantic_entries.get(f"label:{label_id}", {})
            qualification = semantic.get("qualification", {})
            status = (
                "resolved"
                if str(semantic.get("interpretation_status", "")).startswith("implemented")
                else str(qualification.get("status") or semantic.get("interpretation_status") or "unresolved")
            )
            notation = value.get("official_notation", {}) if isinstance(value, Mapping) else {}
            abilities.append(InventoryAbilityDiagnostic(
                ability_id=str(ability.get("occurrence_id")),
                label=label_id.replace("_", " ").title(),
                official_value=str(notation.get("raw")) if notation.get("raw") is not None else None,
                status=status,
                dependencies=tuple(str(item) for item in semantic.get("dependencies", ())),
            ))
        return InventoryClubDiagnostic(
            club_id=club_id,
            club_name=club.name,
            level=level,
            brand=club.brand,
            club_type=club.club_type,
            rarity=club.rarity,
            base_stats=club.stats_at(level).as_dict(),
            abilities=tuple(abilities),
            active_step_ids=tuple(
                step.identifier for step in strategy.definition.sequence if _matches_step(club, step)
            ),
            support_categories=runtime.support_categories.get(club_id, ()),
        )

    def trace_composition(
        self,
        strategy_id: str,
        club_ids: tuple[str, ...],
        *,
        variant_ids: tuple[str, ...] = (),
        scenario_level: int | str | None = None,
    ) -> dict[str, Any]:
        registry = StrategyRegistry.load(self.registry_path)
        strategy = registry.resolve(strategy_id, variant_ids)
        bundle = load_user_data(self.user_data_path)
        runtime = _RuntimeEvaluator(self.catalog_path, bundle.inventory.entries, scenario_level)
        requested = tuple(club_ids)
        missing = tuple(item for item in requested if item not in runtime.clubs)
        if len(requested) != strategy.definition.bag_size or len(set(requested)) != len(requested):
            return {
                "club_ids": requested,
                "status": "eliminated",
                "stage": "composition_validation",
                "reason": "La composition doit contenir cinq clubs distincts.",
            }
        if missing:
            return {
                "club_ids": requested,
                "status": "eliminated",
                "stage": "inventory",
                "reason": "Clubs absents ou sans niveau évaluable.",
                "missing_club_ids": missing,
            }
        assignments = self.generator._assignments_for(strategy.definition, runtime, requested)
        if not assignments:
            return {
                "club_ids": requested,
                "status": "eliminated",
                "stage": "active_assignments",
                "reason": "Aucune affectation compatible avec les étapes de la stratégie.",
            }
        generated, _, _ = self.generator.generate(strategy, runtime, bundle.bags, "structural_exact", 2000)
        matches = tuple(item for item in generated if set(item.club_ids) == set(requested))
        if matches:
            return {
                "club_ids": requested,
                "status": "generated",
                "stage": "permutations",
                "candidate_count": len(matches),
                "origins": tuple(sorted({item.provenance for item in matches})),
                "stage_counts": dict(self.generator.last_generation_stats),
            }
        active_ids = {item for assignment in assignments for item in assignment}
        structural_support = self.generator.support_potential(runtime, active_ids)
        potential_supports = {
            item: structural_support[item]
            for item in requested
            if item not in active_ids and item in structural_support
        }
        return {
            "club_ids": requested,
            "status": "eliminated",
            "stage": "support_set_reduction",
            "reason": "La composition n'appartient à aucun des ensembles de supports structurels retenus.",
            "valid_assignment_count": len(assignments),
            "support_potential": potential_supports,
            "stage_counts": dict(self.generator.last_generation_stats),
        }

    def optimize(self, request: StrategyOptimizationRequest) -> StrategyOptimizationResult:
        optimization_started = perf_counter()
        if request.limit < 1:
            raise StrategyOptimizationError("Display limit must be at least 1")
        if request.max_evaluations < 1:
            raise StrategyOptimizationError("Evaluation safety limit must be at least 1")
        if request.search_mode not in {"global", "improve_bag", "around_club", "test_new_club", "interactive_builder"}:
            raise StrategyOptimizationError(f"Unsupported search mode: {request.search_mode}")
        if request.replacement_depth not in {1, 2}:
            raise StrategyOptimizationError("Replacement depth must be 1 or 2")
        registry = StrategyRegistry.load(self.registry_path)
        strategy = registry.resolve(request.strategy_id, request.variant_ids)
        if request.metric_minimums:
            step_ids = {step.identifier for step in strategy.definition.sequence}
            unknown_steps = sorted(set(request.metric_minimums) - step_ids)
            if unknown_steps:
                raise StrategyOptimizationError("Étape inconnue dans les minimums : " + ", ".join(unknown_steps))
            unknown_metrics = sorted({
                metric for values in request.metric_minimums.values() for metric in values
                if metric not in {"power", "control", "spin"}
            })
            if unknown_metrics:
                raise StrategyOptimizationError("Métrique minimale inconnue : " + ", ".join(unknown_metrics))
        bundle = load_user_data(self.user_data_path)
        inventory_changes = self._inventory_changes(bundle.inventory.entries)
        runtime = _RuntimeEvaluator(self.catalog_path, bundle.inventory.entries, request.scenario_level)
        inventory_signature = self._inventory_signature(bundle.inventory.entries)
        known_context_key = self._known_context_key(request, strategy, runtime, inventory_signature)
        constrained_ids = set(request.required_club_ids) | set(request.excluded_club_ids) | set(request.club_roles or {})
        if request.fixed_club_id:
            constrained_ids.add(request.fixed_club_id)
        unavailable = tuple(sorted(constrained_ids - set(runtime.clubs)))
        if unavailable:
            raise StrategyOptimizationError(
                "Clubs contraints absents de l'inventaire évaluable : " + ", ".join(unavailable)
            )
        if set(request.required_club_ids) & set(request.excluded_club_ids):
            raise StrategyOptimizationError("Un club ne peut pas être à la fois obligatoire et exclu")
        target_bag: SavedBag | None = None

        generation_started = perf_counter()
        references = self.generator.reference_candidates(strategy, runtime, bundle.bags, request.order_mode)
        injected_saved = 0
        injected_known = 0
        if request.search_mode == "global":
            generated, theoretical, eliminated = self.generator.generate(
                strategy, runtime, bundle.bags, request.order_mode,
                max_generated=max(request.max_evaluations, math.factorial(strategy.definition.bag_size)),
            )
            generation_stats = dict(self.generator.last_generation_stats)
        elif request.search_mode == "interactive_builder":
            builder_roles = dict(request.club_roles or {
                club_id: "auto" for club_id in request.required_club_ids
            })
            if request.keep_current_putter:
                target_bag = next(
                    (item for item in bundle.bags if item.identifier == request.target_bag_id),
                    bundle.bags[0] if bundle.bags else None,
                )
                if target_bag is None:
                    raise StrategyOptimizationError("Aucun sac enregistré ne permet de conserver le putter actuel")
                assignment = self.generator._preferred_assignment(
                    strategy.definition, runtime, target_bag.club_ids,
                )
                finish_index = next(
                    (index for index, step in enumerate(strategy.definition.sequence) if step.function.identifier == "finish"),
                    None,
                )
                if finish_index is not None and assignment:
                    finish_step = strategy.definition.sequence[finish_index]
                    existing = next((club_id for club_id, role in builder_roles.items() if role == finish_step.identifier), None)
                    if existing and existing != assignment[finish_index]:
                        raise StrategyOptimizationError("Le putter imposé diffère du putter actuel à conserver")
                    builder_roles[assignment[finish_index]] = finish_step.identifier
            broad = self.generator.generate_builder(
                strategy,
                runtime,
                club_roles=builder_roles,
                excluded_club_ids=request.excluded_club_ids,
                locked_positions=request.locked_positions,
                order_mode=request.order_mode,
                max_generated=request.max_evaluations,
            )
            broad_stats = dict(self.generator.last_generation_stats)
            compatible_references = tuple(
                item for item in references
                if self._candidate_satisfies_builder_constraints(
                    item, builder_roles, request.excluded_club_ids, request.locked_positions,
                )
            )
            known = self._compatible_known_candidates(known_context_key, builder_roles, request)

            # A saved bag provides a factual active-role seed. Deepening this
            # subspace is generic and prevents a broader query from receiving
            # less attention than the same query with one of those roles added.
            seeded_groups: list[tuple[CandidateSpec, ...]] = []
            seeded_stats: list[Mapping[str, int]] = []
            seeded_role_maps: set[tuple[tuple[str, str], ...]] = set()
            for reference in compatible_references:
                seeded_roles = dict(builder_roles)
                conflict = False
                for step_id, club_id in reference.active_assignments.items():
                    current = seeded_roles.get(club_id)
                    if current == "support":
                        conflict = True
                        break
                    occupied = next(
                        (item for item, role in seeded_roles.items() if role == step_id and item != club_id),
                        None,
                    )
                    if occupied is not None:
                        conflict = True
                        break
                    seeded_roles.setdefault(club_id, step_id)
                signature = tuple(sorted(seeded_roles.items()))
                if conflict or signature == tuple(sorted(builder_roles.items())) or signature in seeded_role_maps:
                    continue
                seeded_role_maps.add(signature)
                seeded_groups.append(self.generator.generate_builder(
                    strategy,
                    runtime,
                    club_roles=seeded_roles,
                    excluded_club_ids=request.excluded_club_ids,
                    locked_positions=request.locked_positions,
                    order_mode=request.order_mode,
                    max_generated=request.max_evaluations,
                ))
                seeded_stats.append(dict(self.generator.last_generation_stats))

            generated = self._merge_candidate_specs(
                compatible_references, known, *seeded_groups, broad,
            )
            injected_saved = len(compatible_references)
            injected_known = len(known)
            all_stats = (broad_stats, *seeded_stats)
            generation_stats = {
                "inventory": broad_stats.get("inventory", len(runtime.clubs)),
                "active_assignments": sum(item.get("active_assignments", 0) for item in all_stats),
                "active_assignments_theoretical": broad_stats.get("active_assignments_theoretical", 0),
                "compositions": len({item.order_space_id for item in generated}),
                "permutations_theoretical": sum(item.get("permutations_theoretical", 0) for item in all_stats),
                "permutations_distinct": len(generated),
                "permutations_equivalent": sum(item.get("permutations_equivalent", 0) for item in all_stats),
                "budget_reached": int(any(item.get("budget_reached", 0) for item in all_stats)),
                "theoretical_compositions": sum(item.get("theoretical_compositions", 0) for item in all_stats),
                "support_clubs_considered": broad_stats.get("support_clubs_considered", 0),
                "position_lock_removed": sum(item.get("position_lock_removed", 0) for item in all_stats),
                "budget_removed": sum(item.get("budget_removed", 0) for item in all_stats),
                "support_pool_truncated_assignments": sum(
                    item.get("support_pool_truncated_assignments", 0) for item in all_stats
                ),
                "seeded_saved_bag_searches": len(seeded_groups),
                "reference_candidates": injected_saved,
                "known_candidates": injected_known,
            }
            self.generator.last_generation_stats = generation_stats
            theoretical = int(broad_stats.get("active_assignments_theoretical", 0))
            eliminated = int(generation_stats.get("permutations_equivalent", 0))
        else:
            if request.target_bag_id:
                target_bag = next((item for item in bundle.bags if item.identifier == request.target_bag_id), None)
            else:
                target_bag = next(
                    (item for item in bundle.bags if request.fixed_club_id in item.club_ids),
                    bundle.bags[0] if bundle.bags else None,
                )
            if target_bag is None:
                raise StrategyOptimizationError("Aucun sac enregistré ne peut servir de point de départ")
            if request.search_mode == "around_club":
                around_required = set(request.required_club_ids)
                if request.keep_current_putter:
                    assignment = self.generator._preferred_assignment(
                        strategy.definition, runtime, target_bag.club_ids,
                    )
                    finish_index = next(
                        (index for index, step in enumerate(strategy.definition.sequence) if step.function.identifier == "finish"),
                        None,
                    )
                    if finish_index is not None and assignment:
                        around_required.add(assignment[finish_index])
                local = self.generator.generate_around(
                    strategy, runtime, request.fixed_club_id or "",
                    fixed_step_id=request.fixed_step_id,
                    order_mode=request.order_mode,
                    max_generated=max(request.max_evaluations, math.factorial(strategy.definition.bag_size)),
                    required_club_ids=tuple(around_required),
                    excluded_club_ids=request.excluded_club_ids,
                )
                if request.locked_positions:
                    local = tuple(
                        item for item in local if all(
                            item.club_ids[position - 1] == club_id
                            for position, club_id in request.locked_positions.items()
                        )
                    )
            else:
                local_required = set(request.required_club_ids)
                if request.search_mode == "test_new_club" and request.fixed_club_id:
                    local_required.add(request.fixed_club_id)
                local = self.generator.generate_local(
                    strategy,
                    runtime,
                    target_bag,
                    replacement_depth=request.replacement_depth,
                    fixed_club_id=None,
                    order_mode=request.order_mode,
                    required_club_ids=tuple(local_required),
                    excluded_club_ids=request.excluded_club_ids,
                    locked_positions=request.locked_positions or {},
                    fixed_step_id=request.fixed_step_id,
                    keep_current_putter=request.keep_current_putter,
                )
            merged: dict[tuple[Any, ...], CandidateSpec] = {
                (item.club_ids, tuple(item.active_assignments.items())): item for item in references
                if set(item.club_ids) == set(target_bag.club_ids)
            }
            for item in local:
                merged.setdefault((item.club_ids, tuple(item.active_assignments.items())), item)
            generated = tuple(merged.values())
            theoretical = len(local)
            eliminated = 0
            generation_stats = dict(self.generator.last_generation_stats)
        generation_seconds = perf_counter() - generation_started

        evaluation_started = perf_counter()
        evaluated: list[_QuickCandidate] = []
        excluded_candidates = 0
        reference_specs = tuple(item for item in generated if item.provenance == "reference_bag")
        search_specs = tuple(item for item in generated if item.provenance != "reference_bag")
        if request.search_mode in {"around_club", "interactive_builder"} or (
            request.search_mode in {"improve_bag", "test_new_club"} and request.replacement_depth == 1
        ):
            # The one-replacement neighborhood is deliberately exhaustive.
            selected_specs = (*reference_specs, *search_specs)
        elif request.search_mode != "global" and target_bag is not None:
            selected_specs = (
                *reference_specs,
                *self._bounded_local_order_spaces(search_specs, target_bag, request.max_evaluations),
            )
        else:
            selected_specs = (*reference_specs, *search_specs[: request.max_evaluations])
        order_counts: dict[str, int] = {}
        for spec in selected_specs:
            order_counts[spec.order_space_id] = order_counts.get(spec.order_space_id, 0) + 1
        for spec in selected_specs:
            quick = self._evaluate_quick(spec, strategy, runtime, request.mode)
            quick = replace(
                quick,
                orders_evaluated_in_space=order_counts[spec.order_space_id],
                best_orders=(spec.club_ids,),
            )
            if quick.strict_failed:
                excluded_candidates += 1
            else:
                evaluated.append(quick)
        evaluation_seconds = perf_counter() - evaluation_started
        comparison_started = perf_counter()
        evaluated_before_minimums = len(evaluated)
        attainable_ranges = _attainable_ranges(tuple(evaluated), strategy)
        criteria_satisfied = True
        closest_candidate_ids: tuple[str, ...] = ()
        if request.search_mode == "interactive_builder" and request.metric_minimums:
            satisfying = tuple(
                item for item in evaluated if _meets_minimums(item, request.metric_minimums)
            )
            if satisfying:
                evaluated = list(satisfying)
            else:
                criteria_satisfied = False
                closest = _closest_to_minimums(tuple(evaluated), request.metric_minimums)
                closest_candidate_ids = tuple(item.spec.identifier for item in closest)
                evaluated = list(closest)
        current_saved_quick = (
            next(
                (
                    item for item in evaluated
                    if target_bag is not None
                    and item.spec.provenance == "reference_bag"
                    and item.spec.club_ids == target_bag.club_ids
                ),
                None,
            )
            if request.search_mode != "global"
            else None
        )
        empirical_reference = None
        if request.reference_bag_id:
            reference_bag = next((item for item in bundle.bags if item.identifier == request.reference_bag_id), None)
            if reference_bag is None:
                raise StrategyOptimizationError(f"Unknown reference bag: {request.reference_bag_id}")
            empirical_reference = self._empirical_reference(reference_bag, strategy, runtime, request.mode)
            reference_step = (
                strategy.definition.reference_step_id
                or next(
                    (step.identifier for step in strategy.definition.sequence if step.function.identifier != "finish"),
                    strategy.definition.sequence[0].identifier,
                )
            )
            evaluated = [
                item for item in evaluated
                if _quick_metric(item, reference_step, "power") >= empirical_reference.final_power
            ]
        unique_before_reference_guard = self._deduplicate(evaluated)
        reference_controls = tuple(
            item for item in unique_before_reference_guard if item.spec.provenance == "reference_bag"
        )
        unique = (
            tuple(
                item for item in unique_before_reference_guard
                if item.spec.provenance == "reference_bag"
                or not any(_dominates_candidate(reference, item) for reference in reference_controls)
            )
            if request.search_mode in {"global", "improve_bag"}
            else unique_before_reference_guard
        )
        reference_dominated_removed = len(unique_before_reference_guard) - len(unique)
        layered = self._assign_layers(unique)
        projection_pool = (
            tuple(item for item in layered if item.spec.provenance != "reference_bag")
            if request.search_mode not in {"global", "interactive_builder"}
            else layered
        )
        if request.search_mode == "interactive_builder":
            family_results, selected_quick, memberships = self._project_builder_families(
                projection_pool, strategy, runtime, request, request.limit,
            )
        else:
            family_results, selected_quick, memberships = self._project_families(
                projection_pool, strategy, runtime, request.limit, empirical_reference is not None,
                force_generic=request.search_mode == "around_club",
            )
        if request.search_mode == "interactive_builder":
            self._remember_candidates(known_context_key, selected_quick)
        if request.search_mode != "global" and target_bag is not None:
            current = current_saved_quick
            if current is not None:
                selected_quick = (current, *(item for item in selected_quick if item.spec.identifier != current.spec.identifier))
                memberships[current.spec.identifier] = ("current_bag",)
                family_results = (
                    ResultFamilyResult(
                        "current_bag", "SAC ACTUEL", "Sac enregistré utilisé comme référence de contrôle.",
                        (current.spec.identifier,), "reference_control",
                    ),
                    *family_results,
                )
        detailed = tuple(
            self._detail(item, strategy, runtime, request.mode, memberships.get(item.spec.identifier, ()))
            for item in selected_quick
        )
        if request.search_mode == "interactive_builder" and detailed:
            detailed = _attach_power_tier_deltas(detailed, strategy, request.primary_step_id)
        if request.search_mode != "global" and target_bag is not None:
            baseline = next(
                (
                    item for item in detailed
                    if item.origin == "reference_bag" and set(item.composition) == set(target_bag.club_ids)
                ),
                None,
            )
            if baseline is not None:
                detailed = tuple(self._with_reference_delta(item, baseline) for item in detailed)
        type_comparison = _build_type_comparison(layered, strategy, runtime, self.metric_semantics)
        comparison_seconds = perf_counter() - comparison_started
        total_seconds = perf_counter() - optimization_started
        safety_reached = (
            len(search_specs) > request.max_evaluations
            and not (request.search_mode != "global" and request.replacement_depth == 1)
            or bool(generation_stats.get("budget_reached"))
        )
        optimality_status = (
            "maximum_proven"
            if request.search_mode in {"improve_bag", "test_new_club"}
            and request.replacement_depth == 1 and not safety_reached
            else "best_found"
        )
        origin_names = (
            "reference_bag", "reference_neighborhood", "global_search",
            *(("around_club",) if request.search_mode == "around_club" else ()),
            *(("interactive_builder",) if request.search_mode == "interactive_builder" else ()),
            *(("known_candidate",) if request.search_mode == "interactive_builder" else ()),
        )
        warnings = [
            "La portée réelle n'est pas modélisée ; atteindre le green reste indéterminable.",
            "La réussite du putt n'est pas modélisée.",
            "Les candidats sont comparés uniquement sur les métriques calculables du moteur.",
            "La recherche applique une réduction déterministe et n'est pas exhaustive sur tout l'inventaire.",
        ]
        if request.search_mode in {"improve_bag", "test_new_club"}:
            warnings.append(
                "Recherche locale : tous les remplacements simples ont été parcourus ; "
                + ("les doubles remplacements sont réduits par relations structurelles." if request.replacement_depth == 2 else "aucun double remplacement demandé.")
            )
        elif request.search_mode in {"around_club", "test_new_club"}:
            warnings.append(f"Recherche centrée sur le club {request.fixed_club_id}.")
        if request.search_mode == "interactive_builder" and not criteria_satisfied:
            warnings.append(
                "Aucun sac ne satisfait actuellement tous les minimums demandés ; "
                "les solutions non dominées les plus proches sont affichées sans modifier les critères."
            )
        if request.strategy_id in {"par4_long", "par5"}:
            warnings.append(
                "Les besoins de distance de Par 4 long et Par 5 ne peuvent pas encore être distingués "
                "avec les données disponibles. Les propositions peuvent donc être identiques."
            )
        if inventory_changes.added_club_ids:
            names = tuple(
                runtime.clubs[item].name for item in inventory_changes.added_club_ids if item in runtime.clubs
            )
            if names:
                warnings.append("Nouveau(x) club(s) détecté(s) : " + ", ".join(names))
        if request.scenario_level is not None:
            warnings.append(f"Analyse hypothétique : niveau de scénario {request.scenario_level} appliqué explicitement.")
        if safety_reached:
            warnings.append(
                f"Limite de sécurité de {request.max_evaluations} évaluations atteinte : "
                f"{len(generated)} candidats générés en conservant des espaces d'ordre complets ; "
                "des compositions supplémentaires n'ont pas été générées."
            )
        if empirical_reference:
            warnings.append(empirical_reference.statement)
        return StrategyOptimizationResult(
            schema_version="1.0.0",
            catalog_version=runtime.catalog_version,
            strategy_id=strategy.definition.identifier,
            strategy_version=strategy.definition.version,
            applied_variant_ids=strategy.applied_variant_ids,
            level_mode=request.level_mode,
            scenario_level=request.scenario_level,
            excluded_clubs=tuple(runtime.exclusions),
            search=SearchInstrumentation(
                theoretical_candidates=theoretical,
                reduced_candidates_generated=len(generated),
                candidates_evaluated=evaluated_before_minimums + excluded_candidates,
                candidate_result_duplicates_removed=len(evaluated) - len(unique_before_reference_guard),
                permutations_eliminated_before_evaluation=eliminated,
                safety_limit=request.max_evaluations,
                safety_limit_reached=safety_reached,
                search_method=(
                    f"synergy_aware_{request.order_mode}_order_search"
                    if request.search_mode == "global"
                    else f"{request.search_mode}_{request.replacement_depth}_replacement_{request.order_mode}_order_search"
                ),
                completeness=(
                    "partial_bounded_search_with_exact_retained_order_spaces"
                    if request.search_mode == "global"
                    else "bounded_composition_search_around_fixed_active_club"
                    if request.search_mode == "around_club"
                    else "bounded_composition_search_around_required_clubs"
                    if request.search_mode == "interactive_builder"
                    else "exhaustive_one_replacement"
                    if request.replacement_depth == 1
                    else "structurally_reduced_two_replacements"
                ),
                generation_seconds=round(generation_seconds, 6),
                evaluation_seconds=round(evaluation_seconds, 6),
                compositions_generated=generation_stats.get(
                    "compositions", generation_stats.get("local_compositions", 0)
                ),
                permutations_theoretical=generation_stats.get(
                    "permutations_theoretical", len(selected_specs)
                ),
                permutations_proven_equivalent=generation_stats.get("permutations_equivalent", 0),
                permutations_structurally_distinct=generation_stats.get(
                    "permutations_distinct", len(selected_specs)
                ),
                average_seconds_per_composition=round(
                    evaluation_seconds / max(1, len({item.order_space_id for item in selected_specs})), 6
                ),
                candidates_retained_by_family={item.identifier: len(item.candidate_ids) for item in family_results},
                stage_counts={
                    "inventory": generation_stats.get("inventory", len(runtime.clubs)),
                    "active_potential": generation_stats.get("active_potential", 0),
                    "active_assignments": generation_stats.get("active_assignments", 0),
                    "compositions_finales": generation_stats.get("compositions", generation_stats.get("local_compositions", 0)),
                    "permutations": len(selected_specs),
                    "resultats_uniques": len(unique),
                    "domines_par_reference": reference_dominated_removed,
                    "paires_generees": generation_stats.get("pair_compositions", 0),
                    "paires_evaluees": len({
                        item.order_space_id for item in selected_specs
                        if target_bag is not None and len(set(item.club_ids) - set(target_bag.club_ids)) == 2
                    }),
                },
                origin_counts={origin: sum(item.provenance == origin for item in selected_specs) for origin in origin_names},
                replacement_depth=request.replacement_depth if request.search_mode in {"improve_bag", "test_new_club"} else 0,
                local_search_completeness=(
                    "bounded_around_fixed_club" if request.search_mode == "around_club"
                    else "exhaustive_one_replacement" if request.search_mode in {"improve_bag", "test_new_club"} and request.replacement_depth == 1
                    else "structurally_reduced_two_replacements" if request.search_mode in {"improve_bag", "test_new_club"}
                    else "not_applicable"
                ),
                theoretical_compositions=generation_stats.get("theoretical_compositions", theoretical),
                compositions_evaluated=len({item.order_space_id for item in selected_specs}),
                active_assignments_theoretical=generation_stats.get("active_assignments_theoretical", 0),
                active_assignments_considered=generation_stats.get("active_assignments", 0),
                evaluation_cache_hits=runtime.evaluation_cache_hits,
                evaluation_cache_misses=runtime.evaluation_cache_misses,
                comparison_seconds=round(comparison_seconds, 6),
                total_seconds=round(total_seconds, 6),
                optimality_status=optimality_status,
                support_clubs_considered=generation_stats.get("support_clubs_considered", 0),
                compositions_removed=sum((
                    generation_stats.get("position_lock_removed", 0),
                    generation_stats.get("budget_removed", 0),
                )),
                removal_reasons={
                    "safe_order_equivalence": generation_stats.get("permutations_equivalent", 0),
                    "position_constraint": generation_stats.get("position_lock_removed", 0),
                    "heuristic_support_pool_cap": generation_stats.get("support_pool_truncated_assignments", 0),
                    "budget_limit": generation_stats.get("budget_removed", 0),
                },
                saved_bag_candidates_injected=injected_saved,
                known_candidates_injected=injected_known,
            ),
            retained_results=detailed,
            excluded_candidate_count=excluded_candidates,
            warnings=tuple(warnings),
            result_families=family_results,
            empirical_reference=empirical_reference,
            type_comparison=type_comparison,
            inventory_owned_count=sum(item.unlocked for item in bundle.inventory.entries),
            inventory_observed_at=bundle.inventory.observed_at,
            inventory_changes=inventory_changes,
            new_club_diagnostics=tuple(
                self._club_diagnostic(item, strategy, runtime)
                for item in inventory_changes.added_club_ids if item in runtime.clubs
            ),
            requested_minimums=request.metric_minimums or {},
            attainable_ranges=attainable_ranges,
            criteria_satisfied=criteria_satisfied,
            closest_candidate_ids=closest_candidate_ids,
        )

    @staticmethod
    def _bounded_local_order_spaces(
        specs: tuple[CandidateSpec, ...],
        target_bag: SavedBag,
        max_evaluations: int,
    ) -> tuple[CandidateSpec, ...]:
        """Share a bounded budget between complete one- and two-change order spaces."""
        grouped: dict[str, list[CandidateSpec]] = {}
        for item in specs:
            grouped.setdefault(item.order_space_id, []).append(item)
        single: list[list[CandidateSpec]] = []
        double: list[list[CandidateSpec]] = []
        baseline = set(target_bag.club_ids)
        for values in grouped.values():
            added = len(set(values[0].club_ids) - baseline)
            (double if added >= 2 else single).append(values)
        chosen: list[CandidateSpec] = []
        for index in range(max(len(single), len(double))):
            for pools in (single, double):
                if index >= len(pools):
                    continue
                values = pools[index]
                if len(chosen) + len(values) > max_evaluations:
                    continue
                chosen.extend(values)
        return tuple(chosen)

    @staticmethod
    def _with_reference_delta(
        candidate: StrategyCandidateResult,
        reference: StrategyCandidateResult,
    ) -> StrategyCandidateResult:
        def active_metrics(value: StrategyCandidateResult) -> tuple[dict[str, float | None], set[str]]:
            metrics: dict[str, float | None] = {}
            relevant: set[str] = set()
            clubs = {item.club_id: item for item in value.clubs}
            for step_id, club_id in value.active_assignments.items():
                step = next(item for item in clubs[club_id].steps if item.step_id == step_id)
                for name, amount in step.final_stats.items():
                    key = f"{step_id}.{name}"
                    metrics[key] = amount
                    if step.metric_relevance.get(name) in {"objective", "constraint"}:
                        relevant.add(key)
                for name, amount in step.additional_metrics.items():
                    key = f"{step_id}.{name}"
                    metrics[key] = amount
                    if step.metric_relevance.get(name) in {"objective", "constraint"}:
                        relevant.add(key)
            return metrics, relevant

        def received_ids(value: StrategyCandidateResult) -> set[str]:
            result: set[str] = set()
            clubs = {item.club_id: item for item in value.clubs}
            for step_id, club_id in value.active_assignments.items():
                step = next(item for item in clubs[club_id].steps if item.step_id == step_id)
                result.update(item.ability_id for item in step.contributions_received)
            return result

        current, current_relevant = active_metrics(candidate)
        before, before_relevant = active_metrics(reference)
        deltas = {
            key: None if current.get(key) is None or before.get(key) is None else current[key] - before[key]
            for key in sorted(set(current) | set(before))
        }
        current_contributions = received_ids(candidate)
        reference_contributions = received_ids(reference)
        positions_before = {club.club_id: club.position for club in reference.clubs}
        positions_after = {club.club_id: club.position for club in candidate.clubs}
        position_changes = {
            club_id: (positions_before.get(club_id), positions_after.get(club_id))
            for club_id in sorted(set(positions_before) | set(positions_after))
            if positions_before.get(club_id) != positions_after.get(club_id)
        }
        values = {
            key: {"before": before.get(key), "after": current.get(key)}
            for key in sorted(set(current) | set(before))
        }
        relevant_keys = current_relevant | before_relevant
        relevant_keys.update(
            key for key in set(current) | set(before)
            if key.endswith(".bounce_reduction_percent")
        )
        numeric = tuple(value for key, value in deltas.items() if key in relevant_keys and value is not None)
        newly_unresolved = set(candidate.unresolved_abilities) - set(reference.unresolved_abilities)
        if newly_unresolved:
            group = "with_warnings"
        elif any(value > 0 for value in numeric) and not any(value < 0 for value in numeric):
            group = "without_observed_loss"
        elif any(value != 0 for value in numeric):
            group = "tradeoff"
        else:
            group = "neutral"
        return replace(
            candidate,
            removed_club_ids=tuple(item for item in reference.composition if item not in candidate.composition),
            added_club_ids=tuple(item for item in candidate.composition if item not in reference.composition),
            metric_deltas_from_reference=deltas,
            gained_contribution_ids=tuple(sorted(current_contributions - reference_contributions)),
            lost_contribution_ids=tuple(sorted(reference_contributions - current_contributions)),
            position_changes=position_changes,
            metric_values_from_reference=values,
            comparison_group=group,
        )

    def _empirical_reference(
        self,
        bag: SavedBag,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        mode: EvaluationMode,
    ) -> EmpiricalReference:
        if len(bag.club_ids) != strategy.definition.bag_size or any(item not in runtime.clubs for item in bag.club_ids):
            raise StrategyOptimizationError("Reference bag cannot be evaluated with the current inventory")
        used: set[str] = set()
        assignments: dict[str, str] = {}
        for step in strategy.definition.sequence:
            club_id = next(
                (item for item in bag.club_ids if item not in used and _matches_step(runtime.clubs[item], step)),
                None,
            )
            if club_id is None:
                raise StrategyOptimizationError(f"Reference bag has no compatible club for step {step.identifier}")
            assignments[step.identifier] = club_id
            used.add(club_id)
        spec = CandidateSpec(
            f"reference-{bag.identifier}", bag.club_ids, assignments, "empirical_reference"
        )
        quick = self._evaluate_quick(spec, strategy, runtime, mode)
        step_id = strategy.definition.reference_step_id or strategy.definition.sequence[0].identifier
        club_id = assignments[step_id]
        power = _quick_metric(quick, step_id, "power")
        club_name = runtime.clubs[club_id].name
        return EmpiricalReference(
            bag.identifier, bag.name, step_id, club_id, club_name, power,
            f"Puissance minimale empirique : {power:g}, issue de {club_name} dans votre sac {bag.name}. "
            "Cette valeur ne correspond pas à une distance garantie.",
        )

    def _project_families(
        self,
        candidates: tuple[_QuickCandidate, ...],
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        limit: int,
        has_reference: bool,
        force_generic: bool = False,
    ) -> tuple[tuple[ResultFamilyResult, ...], tuple[_QuickCandidate, ...], dict[str, tuple[str, ...]]]:
        definitions = (
            self._derived_result_families(strategy)
            if force_generic else strategy.definition.result_families or self._derived_result_families(strategy)
        )
        if not definitions:
            selected = candidates[:limit]
            family = ResultFamilyResult("default", "Propositions retenues", "", tuple(item.spec.identifier for item in selected), "nondominated")
            return (family,), selected, {item.spec.identifier: ("default",) for item in selected}
        family_results: list[ResultFamilyResult] = []
        selected_by_id: dict[str, _QuickCandidate] = {}
        memberships: dict[str, list[str]] = {}
        for definition in definitions:
            eligible = tuple(item for item in candidates if _family_matches(item, definition, runtime))
            objectives = (
                strategy.definition.reference_objectives
                if has_reference and strategy.definition.reference_objectives
                else definition.objectives
            )
            retained = _select_family(eligible, definition.selection_policy, objectives, limit)
            ids = tuple(item.spec.identifier for item in retained)
            family_results.append(ResultFamilyResult(
                definition.identifier, definition.user_name, definition.description, ids, definition.selection_policy
            ))
            for item in retained:
                selected_by_id.setdefault(item.spec.identifier, item)
                memberships.setdefault(item.spec.identifier, []).append(definition.identifier)
        return (
            tuple(family_results), tuple(selected_by_id.values()),
            {key: tuple(value) for key, value in memberships.items()},
        )

    def _project_builder_families(
        self,
        candidates: tuple[_QuickCandidate, ...],
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        request: StrategyOptimizationRequest,
        limit: int,
    ) -> tuple[tuple[ResultFamilyResult, ...], tuple[_QuickCandidate, ...], dict[str, tuple[str, ...]]]:
        """Expose factual Power tiers without combining metrics into a synthetic score."""
        if not candidates:
            return (), (), {}
        step = next(
            (
                item for item in strategy.definition.sequence
                if item.identifier == request.primary_step_id
            ),
            next(
                item for item in strategy.definition.sequence
                if item.function.identifier != "finish"
            ),
        )
        finish = next(
            (item for item in strategy.definition.sequence if item.function.identifier == "finish"),
            None,
        )

        def key(item: _QuickCandidate, secondary: str) -> tuple[float, ...]:
            return (
                _quick_metric(item, step.identifier, "power"),
                _quick_metric(item, step.identifier, secondary),
                _quick_metric(item, step.identifier, "spin" if secondary == "control" else "control"),
                _quick_metric(item, finish.identifier, "power") if finish else -math.inf,
                _quick_metric(item, finish.identifier, "control") if finish else -math.inf,
            )

        maximum = max(candidates, key=lambda item: key(item, "control"))
        maximum_power = _quick_metric(maximum, step.identifier, "power")
        maximum_control = _quick_metric(maximum, step.identifier, "control")
        maximum_spin = _quick_metric(maximum, step.identifier, "spin")
        selected: dict[str, _QuickCandidate] = {maximum.spec.identifier: maximum}
        memberships: dict[str, list[str]] = {maximum.spec.identifier: ["power_max"]}
        families: list[ResultFamilyResult] = [ResultFamilyResult(
            "power_max", "MEILLEURE PUISSANCE TROUVÉE",
            f"Meilleure Power observée dans la recherche bornée pour {step.name}, puis Control, Spin et qualité finale du putt.",
            (maximum.spec.identifier,), "lexicographic_power_first",
        )]
        levels = sorted(
            {_quick_metric(item, step.identifier, "power") for item in candidates if _quick_metric(item, step.identifier, "power") < maximum_power},
            reverse=True,
        )
        for power in levels:
            tier = tuple(item for item in candidates if _quick_metric(item, step.identifier, "power") == power)
            loss = maximum_power - power
            for metric, baseline in (("control", maximum_control), ("spin", maximum_spin)):
                best = max(tier, key=lambda item: key(item, metric))
                gain = _quick_metric(best, step.identifier, metric) - baseline
                if gain <= 0:
                    continue
                identifier = f"{metric}_plus_{gain:g}_for_minus_{loss:g}_power".replace(".", "_")
                label = f"{metric.upper()} +{gain:g} POUR -{loss:g} POWER"
                families.append(ResultFamilyResult(
                    identifier, label,
                    f"Meilleur {metric.title()} observé au palier réel de Power {power:g}.",
                    (best.spec.identifier,), "best_secondary_at_exact_power_tier",
                ))
                selected.setdefault(best.spec.identifier, best)
                memberships.setdefault(best.spec.identifier, []).append(identifier)
            if len(selected) >= limit:
                break

        function_policy = self.optimization_policy.get("shot_functions", {}).get(
            step.function.identifier, {}
        )
        landing_by_type = function_policy.get("important_landing_metrics_by_club_type", {})
        landing_candidates: list[tuple[float, _QuickCandidate, str]] = []
        for item in candidates:
            club_id = item.spec.active_assignments[step.identifier]
            club_type = runtime.clubs[club_id].club_type
            for metric in landing_by_type.get(club_type, ()):
                value = _quick_metric(item, step.identifier, metric)
                if value != -math.inf:
                    landing_candidates.append((value, item, metric))
        if landing_candidates:
            value, landing, metric = max(
                landing_candidates,
                key=lambda entry: (entry[0], _quick_metric(entry[1], step.identifier, "power")),
            )
            families.append(ResultFamilyResult(
                "landing_profile", "MEILLEUR ATTERRISSAGE",
                f"Meilleure valeur calculable de {metric} ({value:g}) selon la politique fonction/type.",
                (landing.spec.identifier,), "best_declared_landing_metric",
            ))
            selected.setdefault(landing.spec.identifier, landing)
            memberships.setdefault(landing.spec.identifier, []).append("landing_profile")
        return (
            tuple(families),
            tuple(selected.values())[:limit],
            {key: tuple(value) for key, value in memberships.items()},
        )

    def _derived_result_families(
        self,
        strategy: ResolvedStrategy,
    ) -> tuple[ResultFamilyDefinition, ...]:
        """Build reusable views from shot functions and declared metric relevance."""
        steps = strategy.definition.sequence

        def objectives(
            step: ShotStep,
            order: tuple[str, ...],
            *,
            first_priority_together: bool = False,
        ) -> tuple[ResultFamilyObjective, ...]:
            available = {
                item.metric for item in step.metric_uses
                if _metric_relevance(step, item.metric, self.metric_semantics) == "objective"
            }
            result = []
            for index, metric in enumerate(order, 1):
                if metric in available:
                    result.append(ResultFamilyObjective(
                        1 if first_priority_together else index,
                        step.identifier,
                        metric,
                        "maximize",
                    ))
            return tuple(result)

        def secondary_objectives(excluded_step_id: str) -> tuple[ResultFamilyObjective, ...]:
            result: list[ResultFamilyObjective] = []
            for step in steps:
                if step.identifier == excluded_step_id:
                    continue
                for objective in objectives(step, ("power", "control", "spin"), first_priority_together=True):
                    result.append(replace(objective, priority=4))
            return tuple(result)

        families: list[ResultFamilyDefinition] = []
        for step in (item for item in steps if item.function.identifier != "finish"):
            power_first = objectives(step, ("power", "control", "spin"))
            if power_first:
                families.extend((
                    ResultFamilyDefinition(
                        f"{step.identifier}_max_power",
                        f"{step.name} — meilleure Power trouvée",
                        "derived_from_shot_function",
                        "lexicographic_best",
                        (),
                        (*power_first, *secondary_objectives(step.identifier)),
                        (),
                        "Meilleure Power calculable trouvée, sans prétendre à une distance réelle ni à un optimum exhaustif.",
                    ),
                    ResultFamilyDefinition(
                        f"{step.identifier}_power_control",
                        f"{step.name} — Power / Control",
                        "derived_from_shot_function",
                        "best_per_primary_value",
                        (),
                        (*power_first, *secondary_objectives(step.identifier)),
                        (),
                        "Meilleur Control observé aux différents paliers réels de Power.",
                    ),
                ))
            if step.function.identifier == "reach_target_zone":
                attack = objectives(step, ("control", "spin", "power"), first_priority_together=True)
                families.extend((
                    ResultFamilyDefinition(
                        f"{step.identifier}_landing_control",
                        f"{step.name} — contrôle de l’attaque",
                        "derived_from_shot_function",
                        "nondominated",
                        (),
                        (*attack, *secondary_objectives(step.identifier)),
                        (),
                        "Compromis calculables de Control, Spin et Power pour l’attaque de la zone cible.",
                    ),
                    ResultFamilyDefinition(
                        f"{step.identifier}_iron",
                        f"{step.name} — approche Iron",
                        "derived_from_shot_function",
                        "nondominated",
                        (ResultFamilyConstraint(step.identifier, "type", "equals", "iron"),),
                        (*attack, *secondary_objectives(step.identifier)),
                        (),
                        "Meilleures approches calculables dont le club actif est un Iron.",
                    ),
                    ResultFamilyDefinition(
                        f"{step.identifier}_all_types",
                        f"{step.name} — meilleur concurrent tous types",
                        "derived_from_shot_function",
                        "nondominated",
                        (),
                        (*attack, *secondary_objectives(step.identifier)),
                        (),
                        "Tous les types restent admissibles et sont comparés sans préférence imposée.",
                    ),
                ))
        finish = next((item for item in steps if item.function.identifier == "finish"), None)
        if finish is not None:
            putt = objectives(finish, ("power", "control"), first_priority_together=True)
            families.append(ResultFamilyDefinition(
                f"{finish.identifier}_power_control",
                f"{finish.name} — Power / Control",
                "derived_from_shot_function",
                "nondominated",
                (),
                putt,
                (),
                "Compromis Power / Control du club de finition, sans utiliser les métriques descriptives.",
            ))
        whole_sequence = tuple(
            objective
            for step in steps
            for objective in objectives(step, ("power", "control", "spin"), first_priority_together=True)
        )
        if whole_sequence:
            families.append(ResultFamilyDefinition(
                "whole_sequence",
                "Meilleurs compromis sur toute la séquence",
                "derived_from_shot_function",
                "nondominated",
                (),
                whole_sequence,
                (),
                "Front non dominé considérant simultanément tous les clubs actifs.",
            ))
        return tuple(families)

    def _evaluate_quick(
        self,
        spec: CandidateSpec,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        mode: EvaluationMode,
    ) -> _QuickCandidate:
        pending: tuple[DelayedEffect, ...] = ()
        previous: str | None = None
        steps: list[_QuickStep] = []
        unresolved: list[str] = []
        strict_failed = False
        for step in strategy.definition.sequence:
            current = spec.active_assignments[step.identifier]
            incoming = pending
            summary = runtime.evaluate(
                spec,
                current,
                mode=mode,
                terrain=_terrain(step),
                pending_effects=incoming,
                previous_club_id=previous,
            )
            steps.append(_QuickStep(step, current, summary, incoming))
            pending = summary.evaluation.result.pending_effects
            previous = current
            unresolved.extend(summary.evaluation.result.unresolved)
            strict_failed = strict_failed or summary.evaluation.strict_failed
        requirements = tuple(
            _requirement_result(step, requirement)
            for step in strategy.definition.sequence
            for requirement in step.requirements
        )
        objective_metrics = _objective_metrics(tuple(steps), self.metric_semantics)
        return _QuickCandidate(
            spec,
            tuple(steps),
            requirements,
            objective_metrics,
            tuple(sorted(set(unresolved))),
            strict_failed,
        )

    def _deduplicate(self, values: list[_QuickCandidate]) -> tuple[_QuickCandidate, ...]:
        unique: dict[tuple[Any, ...], _QuickCandidate] = {}
        for value in values:
            signature = (
                tuple(sorted(value.spec.club_ids)),
                tuple(value.spec.active_assignments.items()),
                tuple(sorted((key, round(metric, 9)) for key, metric in value.objective_metrics.items())),
                value.unresolved,
                tuple((item.requirement_id, item.status, item.missing_data) for item in value.requirements),
            )
            previous = unique.get(signature)
            if previous is None:
                unique[signature] = value
            else:
                unique[signature] = replace(
                    previous,
                    equivalent_candidates=previous.equivalent_candidates + 1,
                    orders_evaluated_in_space=max(
                        previous.orders_evaluated_in_space, value.orders_evaluated_in_space
                    ),
                    best_orders=tuple(dict.fromkeys((*previous.best_orders, *value.best_orders))),
                )
        return tuple(unique.values())

    def _assign_layers(self, values: tuple[_QuickCandidate, ...]) -> tuple[_QuickCandidate, ...]:
        remaining = list(values)
        ordered: list[_QuickCandidate] = []
        layer = 0
        while remaining:
            frontier = [
                candidate for candidate in remaining
                if not any(_dominates_candidate(other, candidate) for other in remaining if other is not candidate)
            ]
            frontier.sort(key=lambda item: item.spec.identifier)
            ordered.extend(replace(item, comparison_layer=layer) for item in frontier)
            remaining = [item for item in remaining if item not in frontier]
            layer += 1
        return tuple(ordered)

    def _detail(
        self,
        quick: _QuickCandidate,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        mode: EvaluationMode,
        result_family_ids: tuple[str, ...] = (),
    ) -> StrategyCandidateResult:
        step_rows: dict[str, dict[str, ClubStepResult]] = {}
        emitted_by_step: dict[str, dict[str, list[ContributionRecord]]] = {}
        active_by_step = {step.step.identifier: step for step in quick.steps}
        previous: str | None = None
        for quick_step in quick.steps:
            step = quick_step.step
            summaries: dict[str, ComparedBag] = {}
            for club_id in quick.spec.club_ids:
                if club_id == quick_step.active_club_id:
                    summary = quick_step.summary
                else:
                    summary = runtime.evaluate(
                        quick.spec,
                        club_id,
                        mode=mode,
                        terrain=_terrain(step),
                        pending_effects=quick_step.incoming_pending,
                        previous_club_id=previous,
                    )
                summaries[club_id] = summary
            rows, emitted = _build_step_rows(
                step, quick_step.active_club_id, summaries, runtime, self.metric_semantics
            )
            step_rows[step.identifier] = rows
            emitted_by_step[step.identifier] = emitted
            previous = quick_step.active_club_id

        active_steps_by_club = {
            club_id: tuple(step_id for step_id, active_id in quick.spec.active_assignments.items() if active_id == club_id)
            for club_id in quick.spec.club_ids
        }
        counterfactuals: list[SupportCounterfactual] = []
        support_steps_by_club: dict[str, tuple[str, ...]] = {club_id: () for club_id in quick.spec.club_ids}
        for club_id in quick.spec.club_ids:
            if active_steps_by_club[club_id]:
                sent_to_active = []
                for step_id, emitted in emitted_by_step.items():
                    active_target = quick.spec.active_assignments[step_id]
                    if any(
                        item.target_club_id == active_target and item.target_club_id != club_id
                        for item in emitted.get(club_id, ())
                    ):
                        sent_to_active.append(step_id)
                support_steps_by_club[club_id] = tuple(sent_to_active)
                continue
            counterfactual = self._counterfactual(club_id, quick, strategy, runtime, mode)
            counterfactuals.append(counterfactual)
            support_steps_by_club[club_id] = tuple(
                item.step_id
                for item in counterfactual.changes
                if item.lost_metrics_if_removed
            )

        clubs: list[OptimizedClubResult] = []
        for position, club_id in enumerate(quick.spec.club_ids, start=1):
            active_steps = active_steps_by_club[club_id]
            support_steps = support_steps_by_club[club_id]
            if active_steps and support_steps:
                role = "hybrid"
            elif active_steps:
                role = "active"
            elif support_steps:
                role = "support"
            else:
                role = "neutral"
            clubs.append(
                OptimizedClubResult(
                    position,
                    club_id,
                    runtime.clubs[club_id].name,
                    runtime.clubs[club_id].club_type,
                    runtime.levels[club_id],
                    role,
                    active_steps,
                    support_steps,
                    tuple(step_rows[step.identifier][club_id] for step in strategy.definition.sequence),
                )
            )
        indeterminate = any(item.status == "indeterminate" for item in quick.requirements)
        group = "with_warnings" if quick.unresolved or indeterminate else (
            "without_observed_loss" if quick.comparison_layer == 0 else "tradeoff"
        )
        reason = (
            f"Conservé dans la couche de comparaison {quick.comparison_layer}; "
            f"{quick.equivalent_candidates} résultat(s) équivalent(s) regroupé(s)."
        )
        landing_profiles = tuple(
            _landing_profile(
                quick_step.step,
                quick_step.active_club_id,
                step_rows[quick_step.step.identifier][quick_step.active_club_id],
                self.metric_semantics,
            )
            for quick_step in quick.steps
            if quick_step.step.function.identifier == "reach_target_zone"
        )
        return StrategyCandidateResult(
            candidate_id=quick.spec.identifier,
            composition=quick.spec.club_ids,
            active_assignments=dict(quick.spec.active_assignments),
            clubs=tuple(clubs),
            requirements=quick.requirements,
            unresolved_abilities=quick.unresolved,
            comparison_group=group,
            comparison_layer=quick.comparison_layer,
            retained_reason=reason,
            equivalent_candidates=quick.equivalent_candidates,
            support_counterfactuals=tuple(counterfactuals),
            order_audit={
                "theoretical_permutations": quick.spec.theoretical_permutations,
                "proven_equivalent_permutations": (
                    quick.spec.theoretical_permutations - quick.spec.structurally_distinct_permutations
                ),
                "structurally_distinct_permutations": quick.spec.structurally_distinct_permutations,
                "evaluated_permutations": quick.orders_evaluated_in_space,
                "best_orders": quick.best_orders,
                "equivalence_reason": quick.spec.order_equivalence_reason,
                "complete": quick.orders_evaluated_in_space >= quick.spec.structurally_distinct_permutations,
            },
            result_family_ids=result_family_ids,
            landing_profiles=landing_profiles,
            origin=quick.spec.provenance,
        )

    def _counterfactual(
        self,
        removed_id: str,
        quick: _QuickCandidate,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        mode: EvaluationMode,
    ) -> SupportCounterfactual:
        order = tuple(item for item in quick.spec.club_ids if item != removed_id)
        spec = CandidateSpec(quick.spec.identifier + f"-without-{removed_id}", order, quick.spec.active_assignments, "counterfactual_removal")
        pending: tuple[DelayedEffect, ...] = ()
        previous: str | None = None
        changes: list[CounterfactualChange] = []
        for original in quick.steps:
            without = runtime.evaluate(
                spec,
                original.active_club_id,
                mode=mode,
                terrain=_terrain(original.step),
                pending_effects=pending,
                previous_club_id=previous,
            )
            pending = without.evaluation.result.pending_effects
            previous = original.active_club_id
            with_values = _summary_metrics(original.summary)
            without_values = _summary_metrics(without)
            keys = {
                key for key in with_values.keys() | without_values.keys()
                if _metric_qualifies_support(original.step, key, self.metric_semantics)
            }
            delta = {key: with_values.get(key, 0.0) - without_values.get(key, 0.0) for key in keys}
            losses = {key: value for key, value in sorted(delta.items()) if value > 0}
            gains = {key: -value for key, value in sorted(delta.items()) if value < 0}
            if losses or gains:
                changes.append(CounterfactualChange(original.step.identifier, original.active_club_id, losses, gains))
        conclusion = "support utile" if any(item.lost_metrics_if_removed for item in changes) else "neutre pour les étapes actives observées"
        return SupportCounterfactual(removed_id, tuple(changes), conclusion)


def _build_step_rows(
    step: ShotStep,
    active_club_id: str,
    summaries: Mapping[str, ComparedBag],
    runtime: _RuntimeEvaluator,
    metric_semantics: MetricSemanticsRegistry,
) -> tuple[dict[str, ClubStepResult], dict[str, list[ContributionRecord]]]:
    emitted: dict[str, list[ContributionRecord]] = {club_id: [] for club_id in summaries}
    received: dict[str, list[ContributionRecord]] = {club_id: [] for club_id in summaries}
    for target_id, summary in summaries.items():
        for contribution in summary.ability_contributions:
            modification = {key: value for key, value in contribution.modification.items() if value != 0}
            if not modification and not contribution.scheduled_effect_ids:
                continue
            if contribution.scheduled_effect_ids and not modification and target_id != active_club_id:
                continue
            record = ContributionRecord(
                contribution.source_club_id,
                target_id,
                contribution.ability_id,
                contribution.mechanism,
                modification,
                contribution.scheduled_effect_ids,
                {metric: _metric_relevance(step, metric, metric_semantics) for metric in modification},
            )
            if record not in emitted.setdefault(contribution.source_club_id, []):
                emitted[contribution.source_club_id].append(record)
            if record not in received[target_id]:
                received[target_id].append(record)
    rows: dict[str, ClubStepResult] = {}
    for club_id, summary in summaries.items():
        result = summary.evaluation.result
        available = summary.evaluation.state.current_entry.club.available_stats_at(runtime.levels[club_id])
        base_raw = result.base_stats.as_dict()
        final_raw = result.final_stats.as_dict()
        base = {name: base_raw[name] if name in available else None for name in ("power", "control", "spin")}
        final = {name: final_raw[name] if name in available else None for name in ("power", "control", "spin")}
        deltas = {
            name: final[name] - base[name] if final[name] is not None and base[name] is not None else None
            for name in ("power", "control", "spin")
        }
        own = tuple(item for item in summary.ability_contributions if item.source_club_id == club_id)
        active = tuple(item.ability_id for item in own if item.applied)
        unresolved = tuple(item.ability_id for item in own if item.unresolved)
        no_effect = tuple(item.ability_id for item in own if not item.applied and not item.unresolved)
        rows[club_id] = ClubStepResult(
            step.identifier,
            dict(step.context.values),
            base,
            final,
            deltas,
            dict(summary.modifier_impact),
            {
                metric: _metric_relevance(step, metric, metric_semantics)
                for metric in {
                    *_summary_metrics(summary),
                    *(item.metric for item in step.metric_uses),
                }
            },
            active,
            no_effect,
            unresolved,
            tuple(received[club_id]),
            tuple(emitted.get(club_id, ())),
        )
    return rows, emitted


def _terrain(step: ShotStep) -> str | None:
    value = step.context.values.get("terrain")
    return str(value) if value is not None else None


def _matches_step(club: Club, step: ShotStep) -> bool:
    attributes = {
        "identity": club.identifier,
        "brand": club.brand,
        "type": club.club_type,
        "rarity": club.rarity,
    }
    for constraint in step.club_constraints:
        if constraint.attribute not in attributes:
            raise StrategyOptimizationError(f"Unsupported club constraint attribute: {constraint.attribute}")
        observed = attributes[constraint.attribute]
        if constraint.operator == "equals":
            matched = observed == constraint.expected
        elif constraint.operator == "not_equals":
            matched = observed != constraint.expected
        elif constraint.operator == "in":
            matched = observed in constraint.expected
        else:
            raise StrategyOptimizationError(f"Unsupported club constraint operator: {constraint.operator}")
        if not matched:
            return False
    return True


def _requirement_result(step: ShotStep, requirement: OutcomeRequirement) -> RequirementResult:
    available = set(step.context.values)
    missing = tuple(item for item in requirement.required_data if item not in available)
    if missing:
        status = "indeterminate"
    else:
        # This layer has no outcome/physics evaluator yet, even when inputs are present.
        status = "indeterminate"
    return RequirementResult(step.identifier, requirement.identifier, requirement.description, status, missing)


def _summary_metrics(summary: ComparedBag) -> dict[str, float]:
    values = dict(summary.evaluation.result.final_stats.as_dict())
    values.update({key: float(value) for key, value in summary.modifier_impact.items()})
    return values


def _objective_metrics(
    steps: tuple[_QuickStep, ...],
    semantics: MetricSemanticsRegistry,
) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in steps:
        available = _summary_metrics(item.summary)
        for objective in item.step.local_objectives:
            if objective.metric == "all_comparable_metrics":
                for metric, value in available.items():
                    if _metric_relevance(item.step, metric, semantics) == "objective":
                        values[f"{item.step.identifier}:{metric}"] = value
            elif objective.metric in available and _metric_relevance(item.step, objective.metric, semantics) == "objective":
                values[f"{item.step.identifier}:{objective.metric}"] = available[objective.metric]
    return values


def _metric_use(step: ShotStep, metric: str):
    return next((item for item in step.metric_uses if item.metric == metric), None)


def _metric_relevance(
    step: ShotStep,
    metric: str,
    semantics: MetricSemanticsRegistry,
) -> str:
    """Return an explicit functional status; unknown metrics are always descriptive."""

    declared = _metric_use(step, metric)
    semantic: MetricSemantic = semantics.get(metric)
    if declared is None or declared.usage == "descriptive":
        return "descriptive"
    if declared.usage == "context_dependent":
        if semantic.direction != "context_dependent":
            return "descriptive"
        return "objective" if semantic.context_matches(step.function.identifier, step.context.values) else "descriptive"
    if declared.usage == "objective" and semantic.objective_allowed:
        return "objective"
    if declared.usage == "constraint" and semantic.constraint_allowed:
        return "constraint"
    return "descriptive"


def _metric_qualifies_support(
    step: ShotStep,
    metric: str,
    semantics: MetricSemanticsRegistry,
) -> bool:
    declared = _metric_use(step, metric)
    semantic = semantics.get(metric)
    return bool(
        declared
        and declared.qualifies_support
        and semantic.support_qualifying_allowed
        and _metric_relevance(step, metric, semantics) in {"objective", "constraint"}
    )


def _quick_metric(candidate: _QuickCandidate, step_id: str, metric: str) -> float:
    step = next((item for item in candidate.steps if item.step.identifier == step_id), None)
    if step is None:
        return -math.inf
    return float(_summary_metrics(step.summary).get(metric, -math.inf))


def _attainable_ranges(
    candidates: tuple[_QuickCandidate, ...],
    strategy: ResolvedStrategy,
) -> dict[str, dict[str, tuple[float, ...]]]:
    return {
        step.identifier: {
            metric: tuple(sorted({
                value for item in candidates
                if (value := _quick_metric(item, step.identifier, metric)) != -math.inf
            }))
            for metric in ("power", "control", "spin")
        }
        for step in strategy.definition.sequence
    }


def _meets_minimums(
    candidate: _QuickCandidate,
    minimums: Mapping[str, Mapping[str, float]],
) -> bool:
    return all(
        _quick_metric(candidate, step_id, metric) >= float(expected)
        for step_id, values in minimums.items()
        for metric, expected in values.items()
    )


def _closest_to_minimums(
    candidates: tuple[_QuickCandidate, ...],
    minimums: Mapping[str, Mapping[str, float]],
) -> tuple[_QuickCandidate, ...]:
    """Return the non-dominated deficit frontier; deficits are never summed."""
    requested = tuple(
        (step_id, metric, float(expected))
        for step_id, values in minimums.items()
        for metric, expected in values.items()
    )

    def deficits(item: _QuickCandidate) -> tuple[float, ...]:
        return tuple(
            max(0.0, expected - _quick_metric(item, step_id, metric))
            for step_id, metric, expected in requested
        )

    result = []
    for item in candidates:
        current = deficits(item)
        if any(
            all(left <= right for left, right in zip(deficits(other), current, strict=True))
            and any(left < right for left, right in zip(deficits(other), current, strict=True))
            for other in candidates if other is not item
        ):
            continue
        result.append(item)
    return tuple(result)


def _candidate_active_metrics(candidate: StrategyCandidateResult) -> dict[str, float | None]:
    clubs = {item.club_id: item for item in candidate.clubs}
    values: dict[str, float | None] = {}
    for step_id, club_id in candidate.active_assignments.items():
        step = next(item for item in clubs[club_id].steps if item.step_id == step_id)
        values.update({f"{step_id}.{metric}": value for metric, value in step.final_stats.items()})
        values.update({f"{step_id}.{metric}": value for metric, value in step.additional_metrics.items()})
    return values


def _builder_badge(family_id: str) -> str:
    if family_id == "power_max":
        return "MEILLEURE PUISSANCE TROUVÉE"
    if family_id == "landing_profile":
        return "MEILLEUR ATTERRISSAGE"
    for metric in ("control", "spin"):
        prefix = f"{metric}_plus_"
        if family_id.startswith(prefix):
            gain, loss = family_id[len(prefix):].split("_for_minus_", 1)
            return f"{metric.upper()} +{gain.replace('_', '.')} POUR -{loss.removesuffix('_power').replace('_', '.')} POWER"
    return family_id.replace("_", " ").upper()


def _attach_power_tier_deltas(
    candidates: tuple[StrategyCandidateResult, ...],
    strategy: ResolvedStrategy,
    primary_step_id: str | None,
) -> tuple[StrategyCandidateResult, ...]:
    baseline = next(
        (item for item in candidates if "power_max" in item.result_family_ids),
        candidates[0],
    )
    before = _candidate_active_metrics(baseline)
    result = []
    for item in candidates:
        after = _candidate_active_metrics(item)
        deltas = {
            key: None if before.get(key) is None or after.get(key) is None
            else float(after[key]) - float(before[key])
            for key in sorted(set(before) | set(after))
        }
        result.append(replace(
            item,
            optimization_badges=tuple(_builder_badge(value) for value in item.result_family_ids),
            metric_deltas_from_power_max=deltas,
        ))
    return tuple(result)


def _family_matches(
    candidate: _QuickCandidate,
    family: ResultFamilyDefinition,
    runtime: _RuntimeEvaluator,
) -> bool:
    for constraint in family.constraints:
        club_id = candidate.spec.active_assignments.get(constraint.step_id)
        if club_id is None:
            return False
        club = runtime.clubs[club_id]
        values = {
            "type": club.club_type, "brand": club.brand,
            "rarity": club.rarity, "identity": club.identifier,
        }
        observed = values.get(constraint.attribute)
        if constraint.operator == "equals":
            matched = observed == constraint.expected
        elif constraint.operator == "not_equals":
            matched = observed != constraint.expected
        elif constraint.operator == "in":
            matched = observed in constraint.expected
        else:
            raise StrategyOptimizationError(
                f"Unsupported result-family constraint operator: {constraint.operator}"
            )
        if not matched:
            return False
    return True


def _objective_value(candidate: _QuickCandidate, objective: ResultFamilyObjective) -> float:
    value = _quick_metric(candidate, objective.step_id, objective.metric)
    if objective.direction == "maximize":
        return value
    if objective.direction == "minimize":
        return -value
    raise StrategyOptimizationError(
        f"Result-family objective direction requires an explicit target contract: {objective.direction}"
    )


def _select_family(
    candidates: tuple[_QuickCandidate, ...],
    policy: str,
    objectives: tuple[ResultFamilyObjective, ...],
    limit: int,
) -> tuple[_QuickCandidate, ...]:
    ordered_objectives = tuple(sorted(objectives, key=lambda item: item.priority))
    if not candidates or not ordered_objectives:
        return ()

    def key(item: _QuickCandidate) -> tuple[float, ...]:
        return tuple(_objective_value(item, objective) for objective in ordered_objectives)

    def pareto(items: list[_QuickCandidate], group: tuple[ResultFamilyObjective, ...]) -> list[_QuickCandidate]:
        vectors = {
            item.spec.identifier: {index: _objective_value(item, objective) for index, objective in enumerate(group)}
            for item in items
        }
        return [
            item for item in items
            if not any(
                _dominates_values(vectors[other.spec.identifier], vectors[item.spec.identifier])
                for other in items if other is not item
            )
        ]

    def ordered_priorities(items: list[_QuickCandidate], objectives_to_apply: tuple[ResultFamilyObjective, ...]) -> list[_QuickCandidate]:
        retained = items
        previous: tuple[ResultFamilyObjective, ...] = ()
        for priority in sorted({item.priority for item in objectives_to_apply}):
            group = tuple(item for item in objectives_to_apply if item.priority == priority)
            partitions: dict[tuple[float, ...], list[_QuickCandidate]] = {}
            for item in retained:
                signature = tuple(_objective_value(item, objective) for objective in previous)
                partitions.setdefault(signature, []).append(item)
            retained = [item for values in partitions.values() for item in pareto(values, group)]
            previous = (*previous, *group)
        return retained

    if policy == "lexicographic_best":
        retained = ordered_priorities(list(candidates), ordered_objectives)
        retained.sort(key=lambda item: (*key(item), item.spec.identifier), reverse=True)
        return tuple(retained[:limit])
    if policy == "best_per_primary_value":
        primary = ordered_objectives[0]
        groups: dict[float, list[_QuickCandidate]] = {}
        for item in candidates:
            groups.setdefault(_objective_value(item, primary), []).append(item)
        remaining_objectives = tuple(item for item in ordered_objectives if item is not primary)
        retained = [
            item
            for _, items in sorted(groups.items(), reverse=True)
            for item in ordered_priorities(items, remaining_objectives)
        ]
        return tuple(retained[:limit])
    if policy == "nondominated":
        first_priority = min(item.priority for item in ordered_objectives)
        first_group = tuple(item for item in ordered_objectives if item.priority == first_priority)
        frontier = pareto(list(candidates), first_group)
        later = tuple(item for item in ordered_objectives if item.priority != first_priority)
        if later:
            partitions: dict[tuple[float, ...], list[_QuickCandidate]] = {}
            for item in frontier:
                signature = tuple(_objective_value(item, objective) for objective in first_group)
                partitions.setdefault(signature, []).append(item)
            frontier = [
                item for values in partitions.values()
                for item in ordered_priorities(values, later)
            ]
        frontier.sort(key=lambda item: (*key(item), item.spec.identifier), reverse=True)
        return tuple(frontier[:limit])
    raise StrategyOptimizationError(f"Unsupported result-family selection policy: {policy}")


def _landing_profile(
    step: ShotStep,
    club_id: str,
    row: ClubStepResult,
    semantics: MetricSemanticsRegistry,
) -> LandingProfile:
    metric_ids = (
        "loft_angle_degrees", "bounce_reduction_percent", "groundspin",
        "spin", "control", "wind_resistance_percent",
    )
    values: dict[str, float | None] = {
        "spin": row.final_stats.get("spin"),
        "control": row.final_stats.get("control"),
        **{key: float(value) for key, value in row.additional_metrics.items()},
    }
    metrics: list[LandingMetric] = []
    for metric in metric_ids:
        semantic = semantics.get(metric)
        sources = tuple(dict.fromkeys(
            item.ability_id for item in row.contributions_received
            if metric in item.modification
        ))
        metrics.append(LandingMetric(
            metric=metric,
            value=values.get(metric),
            status=_metric_relevance(step, metric, semantics),
            confidence=semantic.confidence,
            provenance=semantic.provenance,
            source_abilities=sources,
        ))
    return LandingProfile(step.identifier, club_id, tuple(metrics))


def _build_type_comparison(
    candidates: tuple[_QuickCandidate, ...],
    strategy: ResolvedStrategy,
    runtime: _RuntimeEvaluator,
    semantics: MetricSemanticsRegistry,
) -> tuple[TypeComparisonRow, ...]:
    attack_step = next(
        (item for item in strategy.definition.sequence if item.function.identifier == "reach_target_zone"),
        strategy.definition.sequence[0],
    )
    owned_by_type: dict[str, set[str]] = {}
    for club_id, club in runtime.clubs.items():
        if _matches_step(club, attack_step):
            owned_by_type.setdefault(club.club_type, set()).add(club_id)
    excluded_by_type: dict[str, list[str]] = {}
    catalog_clubs = runtime.catalog_document.get("clubs", {})
    for excluded in runtime.exclusions:
        raw = catalog_clubs.get(excluded.club_id, {})
        club_type = str(raw.get("club_type", {}).get("id", "unknown"))
        excluded_by_type.setdefault(club_type, []).append(excluded.reason)
    grouped: dict[str, list[_QuickCandidate]] = {}
    for candidate in candidates:
        club_id = candidate.spec.active_assignments.get(attack_step.identifier)
        if club_id:
            grouped.setdefault(runtime.clubs[club_id].club_type, []).append(candidate)
    rows: list[TypeComparisonRow] = []
    for club_type in sorted(owned_by_type.keys() | grouped.keys() | excluded_by_type.keys()):
        items = grouped.get(club_type, [])
        active_ids = {item.spec.active_assignments[attack_step.identifier] for item in items}
        power_tiers: dict[str, float] = {}
        loft_values: list[float] = []
        wind_values: list[float] = []
        bounce_values: list[float] = []
        groundspin_values: list[float] = []
        for item in items:
            power = _quick_metric(item, attack_step.identifier, "power")
            control = _quick_metric(item, attack_step.identifier, "control")
            power_tiers[str(power)] = max(power_tiers.get(str(power), -math.inf), control)
            quick_step = next(step for step in item.steps if step.step.identifier == attack_step.identifier)
            metrics = _summary_metrics(quick_step.summary)
            if "loft_angle_degrees" in metrics:
                loft_values.append(metrics["loft_angle_degrees"])
            if _metric_relevance(attack_step, "wind_resistance_percent", semantics) == "objective" and "wind_resistance_percent" in metrics:
                wind_values.append(metrics["wind_resistance_percent"])
            if _metric_relevance(attack_step, "bounce_reduction_percent", semantics) == "objective" and "bounce_reduction_percent" in metrics:
                bounce_values.append(metrics["bounce_reduction_percent"])
            if "groundspin" in metrics:
                groundspin_values.append(metrics["groundspin"])
        best = max(
            items,
            key=lambda item: (
                _quick_metric(item, attack_step.identifier, "power"),
                _quick_metric(item, attack_step.identifier, "control"),
                _quick_metric(item, attack_step.identifier, "spin"),
            ),
            default=None,
        )
        active_id = best.spec.active_assignments[attack_step.identifier] if best else None
        rows.append(TypeComparisonRow(
            club_type=club_type,
            owned_clubs=len(owned_by_type.get(club_type, ())),
            evaluated_clubs=len(active_ids),
            excluded_clubs=len(excluded_by_type.get(club_type, ())),
            excluded_reasons=tuple(sorted(set(excluded_by_type.get(club_type, ())))),
            best_final_power=max((_quick_metric(item, attack_step.identifier, "power") for item in items), default=None),
            best_control_by_power=dict(sorted(power_tiers.items(), key=lambda pair: float(pair[0]), reverse=True)),
            best_final_spin=max((_quick_metric(item, attack_step.identifier, "spin") for item in items), default=None),
            best_activated_wind_resistance=max(wind_values, default=None),
            best_activated_bounce_reduction=max(bounce_values, default=None),
            groundspin_values=tuple(sorted(set(groundspin_values))),
            loft_range=(min(loft_values), max(loft_values)) if loft_values else None,
            supports_for_best_power=tuple(item for item in best.spec.club_ids if item != active_id) if best else (),
            unresolved_abilities=tuple(sorted({value for item in items for value in item.unresolved})),
            best_order=best.spec.club_ids if best else (),
        ))
    return tuple(rows)


def _dominates_values(left: Mapping[str, float], right: Mapping[str, float]) -> bool:
    keys = left.keys() | right.keys()
    return all(left.get(key, 0.0) >= right.get(key, 0.0) for key in keys) and any(
        left.get(key, 0.0) > right.get(key, 0.0) for key in keys
    )


def _dominates_candidate(left: _QuickCandidate, right: _QuickCandidate) -> bool:
    return _dominates_values(left.objective_metrics, right.objective_metrics)


def render_strategy_optimization_json(result: StrategyOptimizationResult) -> str:
    return json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def render_strategy_optimization(result: StrategyOptimizationResult) -> str:
    lines = [
        "=" * 88,
        f"Optimisation de stratégie : {result.strategy_id}",
        "AVERTISSEMENTS",
        *[f"- {item}" for item in result.warnings],
        "",
        f"Mode de niveaux : {result.level_mode}",
        *([f"Niveau hypothétique : {result.scenario_level}"] if result.scenario_level is not None else []),
        f"Méthode : {result.search.search_method}",
        f"Complétude : {result.search.completeness}",
        f"Combinaisons théoriques : {result.search.theoretical_candidates}",
        f"Candidats générés après réduction : {result.search.reduced_candidates_generated}",
        f"Candidats évalués : {result.search.candidates_evaluated}",
        f"Doublons de résultat éliminés : {result.search.candidate_result_duplicates_removed}",
        f"Durée génération : {result.search.generation_seconds:.3f} s",
        f"Durée moteur : {result.search.evaluation_seconds:.3f} s",
        f"Durée comparaison et détails : {result.search.comparison_seconds:.3f} s",
        f"Durée totale : {result.search.total_seconds:.3f} s",
        f"Compositions théoriques : {result.search.theoretical_compositions}",
        f"Compositions générées : {result.search.compositions_generated}",
        f"Compositions évaluées : {result.search.compositions_evaluated}",
        f"Affectations actives considérées : {result.search.active_assignments_considered} / {result.search.active_assignments_theoretical}",
        f"Permutations théoriques : {result.search.permutations_theoretical}",
        f"Permutations prouvées équivalentes : {result.search.permutations_proven_equivalent}",
        f"Permutations structurellement distinctes : {result.search.permutations_structurally_distinct}",
        f"Cache d'évaluation : {result.search.evaluation_cache_hits} hits / {result.search.evaluation_cache_misses} misses",
        f"Origines : {dict(result.search.origin_counts or {})}",
        f"Étapes de réduction : {dict(result.search.stage_counts or {})}",
        f"Complétude locale : {result.search.local_search_completeness}",
        f"Inventaire : {result.inventory_owned_count} clubs possédés — observation {result.inventory_observed_at or 'inconnue'}",
        "Aucun score global n'a été calculé.",
    ]
    if result.inventory_changes.added_club_ids:
        lines.extend((
            "",
            "Nouveaux clubs détectés : " + ", ".join(result.inventory_changes.added_club_ids),
        ))
        for club in result.new_club_diagnostics:
            lines.append(
                f"- {club.club_name} niveau {club.level} — {club.brand}/{club.club_type}/{club.rarity} — "
                + ", ".join(f"{key}={value}" for key, value in club.base_stats.items())
            )
            lines.extend(
                f"  {ability.label} ({ability.official_value or '—'}) : {ability.status}"
                for ability in club.abilities
            )
    if result.empirical_reference:
        lines.extend(["", result.empirical_reference.statement])
    if result.requested_minimums:
        lines.extend((
            "",
            "Minimums demandés : " + ", ".join(
                f"{step}.{metric}>={value:g}"
                for step, metrics in result.requested_minimums.items()
                for metric, value in metrics.items()
            ),
            "Critères satisfaits : " + ("oui" if result.criteria_satisfied else "non"),
        ))
    if result.result_families:
        lines.extend(["", "Familles de résultats"])
        lines.extend(
            f"- {family.user_name}: {len(family.candidate_ids)} proposition(s) — {family.description}"
            for family in result.result_families
        )
    if result.excluded_clubs:
        lines.extend(["", "Clubs exclus avant recherche"])
        lines.extend(f"- {item.club_name} ({item.club_id}) : {item.reason}" for item in result.excluded_clubs)
    headings = (
        ("without_observed_loss", "Améliorations sans contrepartie observée"),
        ("tradeoff", "Meilleurs compromis"),
        ("with_warnings", "Candidats conservés avec avertissements"),
        ("excluded", "Candidats exclus"),
    )
    for group, heading in headings:
        candidates = tuple(item for item in result.retained_results if item.comparison_group == group)
        lines.extend(["", f"{heading} ({len(candidates)})"])
        if not candidates:
            lines.append("- aucun")
            continue
        for candidate in candidates:
            lines.extend(_candidate_lines(candidate))
    lines.extend(["", f"Candidats exclus pendant l'évaluation : {result.excluded_candidate_count}", "=" * 88])
    return "\n".join(lines)


def _candidate_lines(candidate: StrategyCandidateResult) -> list[str]:
    role_labels = {"active": "actif", "support": "support", "hybrid": "hybride", "neutral": "neutre"}
    lines = [
        "-" * 88,
        f"Sac {candidate.candidate_id} — couche {candidate.comparison_layer}",
        f"Origine : {candidate.origin}",
        "Badge : " + (" / ".join(candidate.optimization_badges) or "aucun"),
        "Familles : " + (", ".join(candidate.result_family_ids) or "générique"),
        "Composition : " + " | ".join(
            f"{club.position}. {club.club_name}" for club in candidate.clubs
        ),
        "Clubs actifs : " + ", ".join(
            f"{step}={next(club.club_name for club in candidate.clubs if club.club_id == club_id)}"
            for step, club_id in candidate.active_assignments.items()
        ),
        f"Raison : {candidate.retained_reason}",
        "Ordre : "
        f"{candidate.order_audit['evaluated_permutations']}/{candidate.order_audit['structurally_distinct_permutations']} "
        "permutations structurellement distinctes évaluées",
        "Exigences :",
    ]
    if candidate.metric_deltas_from_reference is not None:
        lines.extend((
            "Clubs retirés : " + (", ".join(candidate.removed_club_ids) or "aucun"),
            "Clubs ajoutés : " + (", ".join(candidate.added_club_ids) or "aucun"),
            "Écarts avec le sac actuel : " + ", ".join(
                f"{key}={'indéterminé' if value is None else f'{value:+g}'}"
                for key, value in candidate.metric_deltas_from_reference.items()
            ),
            "Contributions gagnées : " + (", ".join(candidate.gained_contribution_ids) or "aucune"),
            "Contributions perdues : " + (", ".join(candidate.lost_contribution_ids) or "aucune"),
        ))
    if candidate.metric_deltas_from_power_max is not None:
        lines.append("Écarts avec la meilleure Power trouvée : " + ", ".join(
            f"{key}={'indéterminé' if value is None else '=' if value == 0 else f'{value:+g}'}"
            for key, value in candidate.metric_deltas_from_power_max.items()
        ))
    lines.extend(
        f"  {item.step_id}/{item.requirement_id}: {item.status}"
        + (f" — manque {', '.join(item.missing_data)}" if item.missing_data else "")
        for item in candidate.requirements
    )
    for club in candidate.clubs:
        lines.extend(
            [
                "",
                f"  Position {club.position} — {club.club_name} — niveau {club.level} — rôle {role_labels[club.role]}",
                f"  Étapes actives : {', '.join(club.active_steps) or 'aucune'}",
                f"  Étapes soutenues : {', '.join(club.support_steps) or 'aucune'}",
            ]
        )
        previous_signature = None
        for step in club.steps:
            signature = (tuple(step.base_stats.items()), tuple(step.final_stats.items()), tuple(step.additional_metrics.items()))
            if signature == previous_signature:
                lines.append(f"    {step.step_id}: valeurs identiques à l'étape précédente")
                continue
            previous_signature = signature
            lines.append(f"    {step.step_id}:")
            for stat in ("power", "control", "spin"):
                lines.append(f"      {stat.capitalize():<7}: {_stat_transition(step, stat)}")
            if step.additional_metrics:
                functional = {
                    key: value for key, value in step.additional_metrics.items()
                    if step.metric_relevance.get(key) in {"objective", "constraint"}
                }
                descriptive = {
                    key: value for key, value in step.additional_metrics.items()
                    if step.metric_relevance.get(key) == "descriptive"
                }
                if functional:
                    lines.append("      Métriques pertinentes : " + ", ".join(
                        f"{key}={value:g}" for key, value in sorted(functional.items())
                    ))
                if descriptive:
                    lines.append("      Métriques seulement descriptives : " + ", ".join(
                        f"{key}={value:g}" for key, value in sorted(descriptive.items())
                    ))
            lines.append("      Capacités actives : " + (", ".join(step.active_abilities) or "aucune"))
            lines.append("      Capacités sans effet : " + (", ".join(step.abilities_without_effect) or "aucune"))
            lines.append("      Capacités non résolues : " + (", ".join(step.unresolved_abilities) or "aucune"))
            lines.append("      Contributions reçues : " + _contribution_text(step.contributions_received, received=True))
            lines.append("      Contributions envoyées : " + _contribution_text(step.contributions_sent, received=False))
    lines.append("  Analyse contrefactuelle des clubs non actifs :")
    for item in candidate.support_counterfactuals:
        lines.append(f"    {item.club_id}: {item.conclusion}")
        for change in item.changes:
            if change.lost_metrics_if_removed:
                lines.append(
                    f"      {change.step_id}/{change.target_club_id} perdrait "
                    + ", ".join(f"{key} {value:+g}" for key, value in change.lost_metrics_if_removed.items())
                )
            if change.gained_metrics_if_removed:
                lines.append(
                    f"      {change.step_id}/{change.target_club_id} gagnerait "
                    + ", ".join(f"{key} {value:+g}" for key, value in change.gained_metrics_if_removed.items())
                )
    if candidate.unresolved_abilities:
        lines.append("  Éléments non résolus : " + "; ".join(candidate.unresolved_abilities))
    for profile in candidate.landing_profiles:
        lines.append(f"  Profil d'atterrissage ({profile.step_id}, sans score) :")
        lines.extend(
            f"    {item.metric}: {'—' if item.value is None else f'{item.value:g}'} [{item.status}]"
            for item in profile.metrics
        )
    return lines


def _stat_transition(step: ClubStepResult, stat: str) -> str:
    base = step.base_stats[stat]
    final = step.final_stats[stat]
    delta = step.deltas[stat]
    if base is None or final is None or delta is None:
        return "—"
    return f"{base:g} → {final:g} ({delta:+g})"


def _contribution_text(values: tuple[ContributionRecord, ...], *, received: bool) -> str:
    if not values:
        return "aucune"
    parts = []
    for item in values:
        counterpart = item.source_club_id if received else item.target_club_id
        changes = ", ".join(f"{key} {value:+g}" for key, value in item.modification.items())
        scheduled = f"; effets planifiés {', '.join(item.scheduled_effect_ids)}" if item.scheduled_effect_ids else ""
        parts.append(f"{counterpart}/{item.ability_id}: {changes or 'planification'}{scheduled}")
    return " | ".join(parts)
