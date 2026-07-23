"""Single-replacement recommendation vertical slice built above the Rule Engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Mapping

from .bag_comparison import AbilityContribution, ComparedBag
from .loader import load_raw_json
from .models import EvaluationMode
from .optimizer_api import BagCandidate, BagEvaluationRequest, BagEvaluator, RuleEngineBagEvaluator
from .user_data import load_user_data
from .value_api import MetricKind, metric_definition


class RecommendationStatus(StrEnum):
    PARETO = "pareto"
    TRADEOFF = "tradeoff"
    NEUTRAL = "neutral"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class RecommendationRequest:
    bag_id: str
    outgoing_club_id: str
    incoming_club_id: str
    level: int | str
    mode: EvaluationMode = EvaluationMode.PARTIAL
    current_position: int | None = None


@dataclass(frozen=True)
class Replacement:
    position: int
    outgoing_club_id: str
    outgoing_club_name: str
    incoming_club_id: str
    incoming_club_name: str


@dataclass(frozen=True)
class ValidationResult:
    request: RecommendationRequest
    replacement: Replacement | None
    baseline: BagCandidate | None
    candidate: BagCandidate | None
    evaluated_position: int | None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors and self.baseline is not None and self.candidate is not None


@dataclass(frozen=True)
class CandidateEvaluation:
    validation: ValidationResult
    baseline: ComparedBag
    candidate: ComparedBag


@dataclass(frozen=True)
class MetricDelta:
    identifier: str
    label: str
    unit: str
    baseline: float
    candidate: float
    delta: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "label": self.label,
            "unit": self.unit,
            "baseline": self.baseline,
            "candidate": self.candidate,
            "delta": self.delta,
        }


@dataclass(frozen=True)
class AbilitySummary:
    ability_id: str
    source_club_id: str
    source: str

    def as_dict(self) -> dict[str, str]:
        return {
            "ability_id": self.ability_id,
            "source_club_id": self.source_club_id,
            "source": self.source,
        }


@dataclass(frozen=True)
class CandidateComparison:
    evaluation: CandidateEvaluation
    metrics: tuple[MetricDelta, ...]
    gained_abilities: tuple[AbilitySummary, ...]
    lost_abilities: tuple[AbilitySummary, ...]
    new_unresolved_ability_ids: tuple[str, ...]
    inherited_unresolved_ability_ids: tuple[str, ...]
    unresolved_messages: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationResult:
    request: RecommendationRequest
    status: RecommendationStatus
    replacement: Replacement | None
    evaluated_position: int | None
    metrics: tuple[MetricDelta, ...]
    gained_abilities: tuple[AbilitySummary, ...]
    lost_abilities: tuple[AbilitySummary, ...]
    new_unresolved_ability_ids: tuple[str, ...]
    new_unresolved_messages: tuple[str, ...]
    warnings: tuple[str, ...]
    exclusion_reasons: tuple[str, ...]
    explanation: str

    @property
    def gains(self) -> tuple[MetricDelta, ...]:
        return tuple(item for item in self.metrics if item.delta > 0)

    @property
    def losses(self) -> tuple[MetricDelta, ...]:
        return tuple(item for item in self.metrics if item.delta < 0)

    def as_dict(self) -> dict[str, Any]:
        replacement = None
        if self.replacement is not None:
            replacement = {
                "position": self.replacement.position,
                "outgoing_club_id": self.replacement.outgoing_club_id,
                "outgoing_club_name": self.replacement.outgoing_club_name,
                "incoming_club_id": self.replacement.incoming_club_id,
                "incoming_club_name": self.replacement.incoming_club_name,
            }
        return {
            "schema_version": "1.0.0",
            "bag_id": self.request.bag_id,
            "replacement": replacement,
            "evaluated_position": self.evaluated_position,
            "level_scenario": self.request.level,
            "mode": self.request.mode.value,
            "status": self.status.value,
            "metrics": [item.as_dict() for item in self.metrics],
            "gains": [item.as_dict() for item in self.gains],
            "losses": [item.as_dict() for item in self.losses],
            "gained_abilities": [item.as_dict() for item in self.gained_abilities],
            "lost_abilities": [item.as_dict() for item in self.lost_abilities],
            "new_unresolved_ability_ids": list(self.new_unresolved_ability_ids),
            "new_unresolved_messages": list(self.new_unresolved_messages),
            "warnings": list(self.warnings),
            "exclusion_reasons": list(self.exclusion_reasons),
            "explanation": self.explanation,
            "aggregate_score": None,
        }


class CandidateValidator:
    def __init__(
        self,
        *,
        user_dir: str | Path = "data/user",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
    ) -> None:
        self.user_dir = Path(user_dir)
        self.catalog_path = Path(catalog_path)

    def validate(self, request: RecommendationRequest) -> ValidationResult:
        bundle = load_user_data(self.user_dir)
        catalog = load_raw_json(self.catalog_path)
        clubs = catalog.get("clubs", {}) if isinstance(catalog, Mapping) else {}
        errors: list[str] = []
        warnings = [
            f"Explicit level scenario {request.level!s} is used for every club; it is not a recorded user level.",
            "Only one current position is evaluated; effects on the other four positions are not included.",
        ]
        if not bundle.inventory.inventory_complete:
            warnings.append("The user inventory is incomplete; this result is not an exhaustive recommendation.")

        saved_bag = next((item for item in bundle.bags if item.identifier == request.bag_id), None)
        if saved_bag is None:
            errors.append(f"Unknown saved bag: {request.bag_id}")
            return ValidationResult(request, None, None, None, None, tuple(errors), tuple(warnings))

        occurrences = [index for index, club_id in enumerate(saved_bag.club_ids) if club_id == request.outgoing_club_id]
        if len(occurrences) != 1:
            errors.append(
                f"Outgoing club {request.outgoing_club_id!r} must appear exactly once in bag {request.bag_id!r}."
            )
        outgoing_index = occurrences[0] if len(occurrences) == 1 else None

        incoming_data = clubs.get(request.incoming_club_id) if isinstance(clubs, Mapping) else None
        outgoing_data = clubs.get(request.outgoing_club_id) if isinstance(clubs, Mapping) else None
        if not isinstance(incoming_data, Mapping):
            errors.append(f"Unknown official incoming club: {request.incoming_club_id}")
        inventory_entry = bundle.inventory.get(request.incoming_club_id)
        if inventory_entry is None:
            errors.append(f"Incoming club {request.incoming_club_id!r} is not confirmed in the user inventory.")
        elif not inventory_entry.unlocked:
            errors.append(f"Incoming club {request.incoming_club_id!r} is not unlocked.")
        if request.incoming_club_id in saved_bag.club_ids and request.incoming_club_id != request.outgoing_club_id:
            errors.append(f"Incoming club {request.incoming_club_id!r} is already present in the bag.")
        if request.incoming_club_id == request.outgoing_club_id:
            errors.append("Outgoing and incoming clubs must be different.")

        evaluated_position = request.current_position
        if evaluated_position is None and outgoing_index is not None:
            evaluated_position = outgoing_index + 1
        if evaluated_position is None or not 1 <= evaluated_position <= len(saved_bag.club_ids):
            errors.append("Evaluated position must exist in the five-club bag.")

        candidate_ids = list(saved_bag.club_ids)
        if outgoing_index is not None:
            candidate_ids[outgoing_index] = request.incoming_club_id
        if len(set(candidate_ids)) != len(candidate_ids):
            errors.append("Candidate bag contains duplicate clubs.")

        for club_id in set((*saved_bag.club_ids, *candidate_ids)):
            club_data = clubs.get(club_id) if isinstance(clubs, Mapping) else None
            if not isinstance(club_data, Mapping):
                errors.append(f"Unknown official club in candidate evaluation: {club_id}")
                continue
            levels = club_data.get("levels", {})
            level_data = levels.get(str(request.level)) if isinstance(levels, Mapping) else None
            if not isinstance(level_data, Mapping) or not level_data.get("available"):
                errors.append(f"Level {request.level!s} is unavailable for club {club_id!r}.")

        replacement = None
        if outgoing_index is not None and isinstance(incoming_data, Mapping) and isinstance(outgoing_data, Mapping):
            replacement = Replacement(
                outgoing_index + 1,
                request.outgoing_club_id,
                str(outgoing_data.get("name", request.outgoing_club_id)),
                request.incoming_club_id,
                str(incoming_data.get("name", request.incoming_club_id)),
            )

        if errors:
            return ValidationResult(
                request,
                replacement,
                None,
                None,
                evaluated_position,
                tuple(dict.fromkeys(errors)),
                tuple(warnings),
            )

        levels = {club_id: request.level for club_id in set((*saved_bag.club_ids, *candidate_ids))}
        baseline = BagCandidate(f"{request.bag_id}:baseline", saved_bag.club_ids, levels)
        candidate = BagCandidate(
            f"{request.bag_id}:p{outgoing_index + 1}:{request.outgoing_club_id}-to-{request.incoming_club_id}",
            tuple(candidate_ids),
            levels,
        )
        return ValidationResult(
            request,
            replacement,
            baseline,
            candidate,
            evaluated_position,
            (),
            tuple(warnings),
        )


class CandidateEvaluator:
    def __init__(self, evaluator: BagEvaluator) -> None:
        self.evaluator = evaluator

    def evaluate(self, validation: ValidationResult) -> CandidateEvaluation:
        if not validation.valid or validation.evaluated_position is None:
            raise ValueError("Candidate validation must succeed before evaluation")
        baseline = self.evaluator.evaluate(
            BagEvaluationRequest(validation.baseline, validation.evaluated_position, validation.request.mode)
        )
        candidate = self.evaluator.evaluate(
            BagEvaluationRequest(validation.candidate, validation.evaluated_position, validation.request.mode)
        )
        return CandidateEvaluation(validation, baseline, candidate)


def _ability_summary(item: AbilityContribution) -> AbilitySummary:
    return AbilitySummary(item.ability_id, item.source_club_id, item.source)


def _unresolved_ids(side: ComparedBag) -> set[str]:
    return {item.ability_id for item in side.ability_contributions if item.unresolved}


class CandidateComparator:
    def compare(self, evaluation: CandidateEvaluation) -> CandidateComparison:
        baseline = evaluation.baseline
        candidate = evaluation.candidate
        baseline_final = baseline.evaluation.result.final_stats.as_dict()
        candidate_final = candidate.evaluation.result.final_stats.as_dict()
        metrics: list[MetricDelta] = []
        for identifier in ("power", "control", "spin"):
            definition = metric_definition(identifier, MetricKind.STAT)
            metrics.append(
                MetricDelta(
                    identifier,
                    definition.label,
                    definition.unit,
                    baseline_final[identifier],
                    candidate_final[identifier],
                    candidate_final[identifier] - baseline_final[identifier],
                )
            )
        modifier_ids = sorted(baseline.modifier_impact.keys() | candidate.modifier_impact.keys())
        for identifier in modifier_ids:
            definition = metric_definition(identifier, MetricKind.STATIC_MODIFIER)
            before = float(baseline.modifier_impact.get(identifier, 0.0))
            after = float(candidate.modifier_impact.get(identifier, 0.0))
            metrics.append(MetricDelta(identifier, definition.label, definition.unit, before, after, after - before))

        baseline_abilities = {item.ability_id: item for item in baseline.ability_contributions}
        candidate_abilities = {item.ability_id: item for item in candidate.ability_contributions}
        gained_ids = candidate_abilities.keys() - baseline_abilities.keys()
        lost_ids = baseline_abilities.keys() - candidate_abilities.keys()
        baseline_unresolved = _unresolved_ids(baseline)
        candidate_unresolved = _unresolved_ids(candidate)
        new_unresolved = tuple(sorted(candidate_unresolved - baseline_unresolved))
        inherited = tuple(sorted(candidate_unresolved & baseline_unresolved))
        messages = tuple(
            message
            for item in candidate.ability_contributions
            if item.ability_id in new_unresolved
            for message in item.unresolved
        )
        warnings = list(evaluation.validation.warnings)
        if inherited:
            warnings.append("The candidate retains unresolved abilities already present in the baseline: " + ", ".join(inherited))
        if baseline.scheduled_effects or candidate.scheduled_effects:
            warnings.append("Delayed effects are reported but not resolved across other positions in this single-position slice.")
        return CandidateComparison(
            evaluation,
            tuple(metrics),
            tuple(_ability_summary(candidate_abilities[item]) for item in sorted(gained_ids)),
            tuple(_ability_summary(baseline_abilities[item]) for item in sorted(lost_ids)),
            new_unresolved,
            inherited,
            messages,
            tuple(warnings),
        )


class QualificationFilter:
    def from_validation(self, validation: ValidationResult) -> RecommendationResult:
        reason = "The proposed replacement cannot be evaluated: " + " ".join(validation.errors)
        return RecommendationResult(
            request=validation.request,
            status=RecommendationStatus.EXCLUDED,
            replacement=validation.replacement,
            evaluated_position=validation.evaluated_position,
            metrics=(),
            gained_abilities=(),
            lost_abilities=(),
            new_unresolved_ability_ids=(),
            new_unresolved_messages=(),
            warnings=validation.warnings,
            exclusion_reasons=validation.errors,
            explanation=reason,
        )

    def qualify(self, comparison: CandidateComparison) -> RecommendationResult:
        evaluation = comparison.evaluation
        exclusion_reasons: list[str] = []
        if evaluation.baseline.evaluation.strict_failed or evaluation.candidate.evaluation.strict_failed:
            exclusion_reasons.append("Baseline or candidate evaluation failed in strict mode.")
        if comparison.new_unresolved_ability_ids:
            exclusion_reasons.append(
                "The replacement introduces unresolved abilities: "
                + ", ".join(comparison.new_unresolved_ability_ids)
            )
        gains = tuple(item for item in comparison.metrics if item.delta > 0)
        losses = tuple(item for item in comparison.metrics if item.delta < 0)
        if exclusion_reasons:
            status = RecommendationStatus.EXCLUDED
            explanation = "The candidate is excluded because its result is not sufficiently qualified."
        elif gains and not losses:
            status = RecommendationStatus.PARETO
            explanation = (
                "The replacement improves at least one observed metric and loses none at the evaluated position."
            )
        elif not gains and not losses:
            status = RecommendationStatus.NEUTRAL
            explanation = "No objective metric changes at the evaluated position."
        else:
            status = RecommendationStatus.TRADEOFF
            if gains:
                explanation = "The replacement creates both objective gains and losses at the evaluated position."
            else:
                explanation = "The replacement produces objective losses and no observed gain at the evaluated position."
        return RecommendationResult(
            request=evaluation.validation.request,
            status=status,
            replacement=evaluation.validation.replacement,
            evaluated_position=evaluation.validation.evaluated_position,
            metrics=comparison.metrics,
            gained_abilities=comparison.gained_abilities,
            lost_abilities=comparison.lost_abilities,
            new_unresolved_ability_ids=comparison.new_unresolved_ability_ids,
            new_unresolved_messages=comparison.unresolved_messages,
            warnings=comparison.warnings,
            exclusion_reasons=tuple(exclusion_reasons),
            explanation=explanation,
        )


class RecommendationFormatter:
    @staticmethod
    def render_text(result: RecommendationResult) -> str:
        replacement = result.replacement
        if replacement is None:
            proposal = f"{result.request.outgoing_club_id} -> {result.request.incoming_club_id}"
        else:
            proposal = (
                f"{replacement.outgoing_club_name} -> {replacement.incoming_club_name} "
                f"(bag position {replacement.position})"
            )
        lines = [
            "=" * 72,
            "Single replacement recommendation",
            f"Bag: {result.request.bag_id}",
            f"Proposed replacement: {proposal}",
            f"Evaluated current position: {result.evaluated_position if result.evaluated_position is not None else 'unavailable'}",
            f"Level scenario: {result.request.level}",
            f"Status: {result.status.value.upper()}",
            "",
            "Gains by metric",
        ]
        lines.extend(RecommendationFormatter._metric_lines(result.gains))
        lines.extend(["", "Losses by metric"])
        lines.extend(RecommendationFormatter._metric_lines(result.losses))
        lines.extend(["", "Gained abilities"])
        lines.extend(RecommendationFormatter._ability_lines(result.gained_abilities))
        lines.extend(["", "Lost abilities"])
        lines.extend(RecommendationFormatter._ability_lines(result.lost_abilities))
        lines.extend(["", "New unresolved abilities"])
        lines.extend([f"  {item}" for item in result.new_unresolved_ability_ids] or ["  none"])
        lines.extend([f"    Reason: {item}" for item in result.new_unresolved_messages])
        if result.exclusion_reasons:
            lines.extend(["", "Exclusion reasons"])
            lines.extend(f"  {item}" for item in result.exclusion_reasons)
        lines.extend(["", "Warnings"])
        lines.extend([f"  {item}" for item in result.warnings] or ["  none"])
        lines.extend(
            [
                "",
                "Summary",
                f"  {result.explanation}",
                "  No aggregate score was computed.",
                "=" * 72,
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _metric_lines(metrics: tuple[MetricDelta, ...]) -> list[str]:
        if not metrics:
            return ["  none"]
        return [
            f"  {item.label}: {item.delta:+g} {item.unit} ({item.baseline:g} -> {item.candidate:g})"
            for item in metrics
        ]

    @staticmethod
    def _ability_lines(abilities: tuple[AbilitySummary, ...]) -> list[str]:
        if not abilities:
            return ["  none"]
        return [f"  {item.source} [{item.ability_id}]" for item in abilities]

    @staticmethod
    def render_json(result: RecommendationResult) -> str:
        return json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)


class RecommendationService:
    """Orchestrate the permanent vertical-slice components without touching rules."""

    def __init__(
        self,
        *,
        user_dir: str | Path = "data/user",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        evaluator: BagEvaluator | None = None,
    ) -> None:
        self.validator = CandidateValidator(user_dir=user_dir, catalog_path=catalog_path)
        self.evaluator = CandidateEvaluator(evaluator or RuleEngineBagEvaluator(catalog_path))
        self.comparator = CandidateComparator()
        self.qualification = QualificationFilter()

    def analyze(self, request: RecommendationRequest) -> RecommendationResult:
        validation = self.validator.validate(request)
        if not validation.valid:
            return self.qualification.from_validation(validation)
        evaluation = self.evaluator.evaluate(validation)
        comparison = self.comparator.compare(evaluation)
        return self.qualification.qualify(comparison)
