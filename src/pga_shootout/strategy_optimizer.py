"""Generic, bounded strategy search built above the existing Rule Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from itertools import permutations, product
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
from .strategy import OutcomeRequirement, ResolvedStrategy, ShotStep, StrategyRegistry
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

    @property
    def level_mode(self) -> str:
        return "scenario" if self.scenario_level is not None else "actual"


@dataclass(frozen=True)
class ClubExclusion:
    club_id: str
    club_name: str
    reason: str


@dataclass(frozen=True)
class CandidateSpec:
    identifier: str
    club_ids: tuple[str, ...]
    active_assignments: Mapping[str, str]
    provenance: str


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


@dataclass(frozen=True)
class ClubStepResult:
    step_id: str
    context: Mapping[str, Any]
    base_stats: Mapping[str, float | None]
    final_stats: Mapping[str, float | None]
    deltas: Mapping[str, float | None]
    additional_metrics: Mapping[str, float]
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
        source = document.get("source", {})
        self.catalog_version = str(source.get("source_sha256") or source.get("captured_at") or document["schema_version"])
        self.engine = RuleEngine()

    def _can_affect_other_clubs(self, data: Mapping[str, Any], level: int | str) -> bool:
        outward = ("SELECT_ALL", "SELECT_ADJACENT", "FOR_EACH", "SCHEDULE_EFFECT", "MATCH_BRAND", "MATCH_TYPE", "MATCH_RARITY")
        for ability in data.get("abilities", ()):
            if str(level) not in ability.get("values_by_level", {}):
                continue
            semantic = self.semantic_entries.get(f"label:{ability.get('label_id')}", {})
            for spec in _semantic_effect_specs(semantic):
                program = _semantic_program(spec, self.semantic_patterns)
                serialized = json.dumps(program, sort_keys=True) if program else ""
                if any(operation in serialized for operation in outward):
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
        return summarize_bag_evaluation(evaluation, spec.club_ids.index(current_club_id) + 1)


class StrategyCandidateGenerator:
    """Deterministic reduction; it never claims to enumerate the full universe."""

    ACTIVE_POOL_SIZE = 8
    SUPPORT_SETS_PER_ASSIGNMENT = 4
    ORDERS_PER_COMPOSITION = 8

    def generate(
        self,
        strategy: ResolvedStrategy,
        runtime: _RuntimeEvaluator,
        saved_bags: tuple[SavedBag, ...],
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
        for bag in saved_bags:
            if len(bag.club_ids) != definition.bag_size or any(club_id not in runtime.clubs for club_id in bag.club_ids):
                continue
            saved_role_pools = tuple(
                tuple(club_id for club_id in bag.club_ids if _matches_step(runtime.clubs[club_id], step))
                for step in definition.sequence
            )
            assignments = product(*saved_role_pools)
            for assigned in assignments:
                if not definition.allow_active_club_reuse and len(set(assigned)) != len(assigned):
                    continue
                self._add(generated, bag.club_ids, definition, assigned, f"saved_bag:{bag.identifier}")

        active_pools = tuple(self._pareto_active_pool(runtime, pool) for pool in full_role_pools)
        active_pool_union = tuple(dict.fromkeys(item for pool in active_pools for item in pool))
        assignments = product(*active_pools)
        for assigned in assignments:
            if not definition.allow_active_club_reuse and len(set(assigned)) != len(assigned):
                continue
            for support_set in self._support_sets(runtime, eligible_ids, assigned, definition.available_support_clubs, active_pool_union):
                physical = tuple(dict.fromkeys((*assigned, *support_set)))
                if len(physical) != definition.bag_size:
                    continue
                order_space = (tuple(sorted(physical)), assigned)
                if order_space in searched_order_spaces:
                    continue
                searched_order_spaces.add(order_space)
                representative_orders = self._representative_orders(physical)
                permutations_eliminated += math.factorial(definition.bag_size) - len(representative_orders)
                for order in representative_orders:
                    self._add(generated, order, definition, assigned, "reduced_generic_search")
        return tuple(generated.values()), theoretical, permutations_eliminated

    def _pareto_active_pool(self, runtime: _RuntimeEvaluator, eligible_ids: tuple[str, ...]) -> tuple[str, ...]:
        remaining = list(eligible_ids)
        ordered: list[str] = []
        while remaining and len(ordered) < self.ACTIVE_POOL_SIZE:
            frontier = []
            for club_id in remaining:
                stats = runtime.clubs[club_id].stats_at(runtime.levels[club_id]).as_dict()
                if not any(
                    _dominates_values(
                        runtime.clubs[other].stats_at(runtime.levels[other]).as_dict(),
                        stats,
                    )
                    for other in remaining
                    if other != club_id
                ):
                    frontier.append(club_id)
            ordered.extend(frontier)
            remaining = [item for item in remaining if item not in frontier]
        return tuple(ordered[: self.ACTIVE_POOL_SIZE])

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
        outward = [item for item in eligible_ids if item not in assigned_set and item in runtime.support_capable_ids]
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

    def _representative_orders(self, club_ids: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
        values = tuple(permutations(club_ids))
        if len(values) <= self.ORDERS_PER_COMPOSITION:
            return values
        indices = tuple(
            round(index * (len(values) - 1) / (self.ORDERS_PER_COMPOSITION - 1))
            for index in range(self.ORDERS_PER_COMPOSITION)
        )
        return tuple(values[index] for index in dict.fromkeys(indices))

    @staticmethod
    def _add(
        target: dict[tuple[Any, ...], CandidateSpec],
        order: tuple[str, ...],
        definition: Any,
        assigned: tuple[str, ...],
        provenance: str,
    ) -> None:
        assignments = dict(zip((step.identifier for step in definition.sequence), assigned, strict=True))
        key = (order, tuple(assignments.items()))
        if key in target:
            return
        digest = sha256(repr(key).encode("utf-8")).hexdigest()[:12]
        target[key] = CandidateSpec(f"strategy-{digest}", order, assignments, provenance)


class StrategyOptimizer:
    def __init__(
        self,
        *,
        user_data_path: str | Path = "data/pga_shootout.sqlite",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        strategy_registry_path: str | Path = "data/strategies/strategies.json",
    ) -> None:
        self.user_data_path = Path(user_data_path)
        self.catalog_path = Path(catalog_path)
        self.registry_path = Path(strategy_registry_path)
        self.generator = StrategyCandidateGenerator()

    def optimize(self, request: StrategyOptimizationRequest) -> StrategyOptimizationResult:
        if request.limit < 1:
            raise StrategyOptimizationError("Display limit must be at least 1")
        if request.max_evaluations < 1:
            raise StrategyOptimizationError("Evaluation safety limit must be at least 1")
        registry = StrategyRegistry.load(self.registry_path)
        strategy = registry.resolve(request.strategy_id, request.variant_ids)
        bundle = load_user_data(self.user_data_path)
        runtime = _RuntimeEvaluator(self.catalog_path, bundle.inventory.entries, request.scenario_level)

        generation_started = perf_counter()
        generated, theoretical, eliminated = self.generator.generate(strategy, runtime, bundle.bags)
        generation_seconds = perf_counter() - generation_started

        evaluation_started = perf_counter()
        evaluated: list[_QuickCandidate] = []
        excluded_candidates = 0
        for spec in generated[: request.max_evaluations]:
            quick = self._evaluate_quick(spec, strategy, runtime, request.mode)
            if quick.strict_failed:
                excluded_candidates += 1
            else:
                evaluated.append(quick)
        evaluation_seconds = perf_counter() - evaluation_started
        unique = self._deduplicate(evaluated)
        layered = self._assign_layers(unique)
        selected_quick = layered[: request.limit]
        detailed = tuple(self._detail(item, strategy, runtime, request.mode) for item in selected_quick)
        safety_reached = len(generated) > request.max_evaluations
        warnings = [
            "La portée réelle n'est pas modélisée ; atteindre le green reste indéterminable.",
            "La réussite du putt n'est pas modélisée.",
            "Les candidats sont comparés uniquement sur les métriques calculables du moteur.",
            "La recherche applique une réduction déterministe et n'est pas exhaustive sur tout l'inventaire.",
        ]
        if request.scenario_level is not None:
            warnings.append(f"Analyse hypothétique : niveau de scénario {request.scenario_level} appliqué explicitement.")
        if safety_reached:
            warnings.append(
                f"Limite de sécurité atteinte : {request.max_evaluations} candidats évalués sur {len(generated)} générés."
            )
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
                candidates_evaluated=len(evaluated) + excluded_candidates,
                candidate_result_duplicates_removed=len(evaluated) - len(unique),
                permutations_eliminated_before_evaluation=eliminated,
                safety_limit=request.max_evaluations,
                safety_limit_reached=safety_reached,
                search_method="deterministic_pareto_pool_support_windows_representative_orders",
                completeness="partial_reduced_search",
                generation_seconds=round(generation_seconds, 6),
                evaluation_seconds=round(evaluation_seconds, 6),
            ),
            retained_results=detailed,
            excluded_candidate_count=excluded_candidates,
            warnings=tuple(warnings),
        )

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
        objective_metrics = _objective_metrics(tuple(steps))
        return _QuickCandidate(
            spec,
            tuple(steps),
            requirements,
            objective_metrics,
            tuple(dict.fromkeys(unresolved)),
            strict_failed,
        )

    def _deduplicate(self, values: list[_QuickCandidate]) -> tuple[_QuickCandidate, ...]:
        unique: dict[tuple[Any, ...], _QuickCandidate] = {}
        for value in values:
            signature = (
                tuple(value.spec.active_assignments.items()),
                tuple(sorted((key, round(metric, 9)) for key, metric in value.objective_metrics.items())),
                value.unresolved,
                tuple((item.requirement_id, item.status, item.missing_data) for item in value.requirements),
            )
            previous = unique.get(signature)
            if previous is None:
                unique[signature] = value
            else:
                unique[signature] = replace(previous, equivalent_candidates=previous.equivalent_candidates + 1)
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
            rows, emitted = _build_step_rows(step, quick_step.active_club_id, summaries, runtime)
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
            keys = with_values.keys() | without_values.keys()
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


def _objective_metrics(steps: tuple[_QuickStep, ...]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in steps:
        available = _summary_metrics(item.summary)
        for objective in item.step.local_objectives:
            if objective.metric == "all_comparable_metrics":
                for metric, value in available.items():
                    values[f"{item.step.identifier}:{metric}"] = value
            elif objective.metric in available:
                values[f"{item.step.identifier}:{objective.metric}"] = available[objective.metric]
    return values


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
        f"Durée évaluation : {result.search.evaluation_seconds:.3f} s",
        "Aucun score global n'a été calculé.",
    ]
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
        "Composition : " + " | ".join(
            f"{club.position}. {club.club_name}" for club in candidate.clubs
        ),
        "Clubs actifs : " + ", ".join(
            f"{step}={next(club.club_name for club in candidate.clubs if club.club_id == club_id)}"
            for step, club_id in candidate.active_assignments.items()
        ),
        f"Raison : {candidate.retained_reason}",
        "Exigences :",
    ]
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
                lines.append("      Métriques additionnelles : " + ", ".join(
                    f"{key}={value:g}" for key, value in sorted(step.additional_metrics.items())
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
