"""Five-placement recommendation flow composed from the single-replacement slice."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any

from .models import EvaluationMode
from .optimizer_api import BagEvaluator, RuleEngineBagEvaluator
from .recommendation import (
    AbilitySummary,
    CandidateComparator,
    CandidateEvaluator,
    CandidateValidator,
    CandidateComparison,
    MetricDelta,
    RecommendationRequest,
    RecommendationStatus,
    Replacement,
    ValidationResult,
)
from .user_data import load_user_data


@dataclass(frozen=True)
class PlacementRecommendationRequest:
    bag_id: str
    incoming_club_id: str
    level: int | str | None = None
    mode: EvaluationMode = EvaluationMode.PARTIAL

    @property
    def level_mode(self) -> str:
        return "scenario" if self.level is not None else "actual"


class PlacementCandidateGenerator:
    """Generate only the five same-position replacements for one explicit club."""

    def __init__(self, *, user_dir: str | Path = "data/user") -> None:
        self.user_dir = Path(user_dir)

    def generate(self, request: PlacementRecommendationRequest) -> tuple[RecommendationRequest, ...]:
        bundle = load_user_data(self.user_dir)
        bag = next((item for item in bundle.bags if item.identifier == request.bag_id), None)
        if bag is None:
            raise ValueError(f"Unknown saved bag: {request.bag_id}")
        return tuple(
            RecommendationRequest(
                bag_id=request.bag_id,
                outgoing_club_id=outgoing_club_id,
                incoming_club_id=request.incoming_club_id,
                level=request.level,
                mode=request.mode,
                current_position=position,
            )
            for position, outgoing_club_id in enumerate(bag.club_ids, start=1)
        )


@dataclass(frozen=True)
class PositionEvaluation:
    position: int
    baseline_club_id: str
    baseline_club_name: str
    candidate_club_id: str
    candidate_club_name: str
    metrics: tuple[MetricDelta, ...]
    baseline_complete: bool
    candidate_complete: bool
    baseline_strict_failed: bool
    candidate_strict_failed: bool
    baseline_scheduled_effect_ids: tuple[str, ...]
    candidate_scheduled_effect_ids: tuple[str, ...]

    @property
    def gains(self) -> tuple[MetricDelta, ...]:
        return tuple(item for item in self.metrics if item.delta > 0)

    @property
    def losses(self) -> tuple[MetricDelta, ...]:
        return tuple(item for item in self.metrics if item.delta < 0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "baseline_club_id": self.baseline_club_id,
            "baseline_club_name": self.baseline_club_name,
            "candidate_club_id": self.candidate_club_id,
            "candidate_club_name": self.candidate_club_name,
            "metrics": [item.as_dict() for item in self.metrics],
            "gains": [item.as_dict() for item in self.gains],
            "losses": [item.as_dict() for item in self.losses],
            "baseline_complete": self.baseline_complete,
            "candidate_complete": self.candidate_complete,
            "baseline_strict_failed": self.baseline_strict_failed,
            "candidate_strict_failed": self.candidate_strict_failed,
            "baseline_scheduled_effect_ids": list(self.baseline_scheduled_effect_ids),
            "candidate_scheduled_effect_ids": list(self.candidate_scheduled_effect_ids),
        }


@dataclass(frozen=True)
class PlacementCandidateComparison:
    validation: ValidationResult
    positions: tuple[PositionEvaluation, ...]
    position_comparisons: tuple[CandidateComparison, ...]


@dataclass(frozen=True)
class PlacementCandidateResult:
    replacement: Replacement | None
    status: RecommendationStatus
    positions: tuple[PositionEvaluation, ...]
    gained_abilities: tuple[AbilitySummary, ...]
    lost_abilities: tuple[AbilitySummary, ...]
    new_unresolved_ability_ids: tuple[str, ...]
    new_unresolved_messages: tuple[str, ...]
    warnings: tuple[str, ...]
    exclusion_reasons: tuple[str, ...]
    explanation: str

    @property
    def gains(self) -> tuple[tuple[int, str, MetricDelta], ...]:
        return tuple(
            (position.position, position.candidate_club_name, metric)
            for position in self.positions
            for metric in position.gains
        )

    @property
    def losses(self) -> tuple[tuple[int, str, MetricDelta], ...]:
        return tuple(
            (position.position, position.candidate_club_name, metric)
            for position in self.positions
            for metric in position.losses
        )

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
            "replacement": replacement,
            "status": self.status.value,
            "position_evaluations": [item.as_dict() for item in self.positions],
            "gains": [
                {"position": position, "current_club": club, **metric.as_dict()}
                for position, club, metric in self.gains
            ],
            "losses": [
                {"position": position, "current_club": club, **metric.as_dict()}
                for position, club, metric in self.losses
            ],
            "gained_abilities": [item.as_dict() for item in self.gained_abilities],
            "lost_abilities": [item.as_dict() for item in self.lost_abilities],
            "new_unresolved_ability_ids": list(self.new_unresolved_ability_ids),
            "new_unresolved_messages": list(self.new_unresolved_messages),
            "warnings": list(self.warnings),
            "exclusion_reasons": list(self.exclusion_reasons),
            "explanation": self.explanation,
            "aggregate_score": None,
        }


@dataclass(frozen=True)
class PlacementRecommendationResult:
    request: PlacementRecommendationRequest
    incoming_club_name: str
    candidates: tuple[PlacementCandidateResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "baseline_bag_id": self.request.bag_id,
            "incoming_club_id": self.request.incoming_club_id,
            "incoming_club_name": self.incoming_club_name,
            "level_mode": self.request.level_mode,
            "scenario_level": self.request.level,
            "mode": self.request.mode.value,
            "candidate_count": len(self.candidates),
            "candidates": [item.as_dict() for item in self.candidates],
            "aggregate_score": None,
        }


class PlacementCandidateEvaluator:
    """Evaluate five current positions while caching the baseline by position."""

    def __init__(self, evaluator: CandidateEvaluator, comparator: CandidateComparator) -> None:
        self.evaluator = evaluator
        self.comparator = comparator
        self._baseline_cache: dict[tuple[Any, ...], Any] = {}

    @property
    def cached_baseline_evaluations(self) -> int:
        return len(self._baseline_cache)

    def evaluate(self, validation: ValidationResult) -> PlacementCandidateComparison:
        if not validation.valid:
            raise ValueError("Candidate validation must succeed before matrix evaluation")
        positions: list[PositionEvaluation] = []
        comparisons: list[CandidateComparison] = []
        for position in range(1, 6):
            positioned = replace(validation, evaluated_position=position)
            cache_key = (
                validation.baseline.club_ids,
                tuple(sorted(validation.baseline.levels.items())),
                validation.request.mode.value,
                position,
            )
            baseline = self._baseline_cache.get(cache_key)
            if baseline is None:
                baseline = self.evaluator.evaluate_baseline(positioned, position)
                self._baseline_cache[cache_key] = baseline
            evaluated = self.evaluator.evaluate(positioned, baseline=baseline)
            comparison = self.comparator.compare(evaluated)
            comparisons.append(comparison)
            baseline_entry = evaluated.baseline.evaluation.state.current_entry.club
            candidate_entry = evaluated.candidate.evaluation.state.current_entry.club
            positions.append(
                PositionEvaluation(
                    position=position,
                    baseline_club_id=baseline_entry.identifier,
                    baseline_club_name=baseline_entry.name,
                    candidate_club_id=candidate_entry.identifier,
                    candidate_club_name=candidate_entry.name,
                    metrics=comparison.metrics,
                    baseline_complete=evaluated.baseline.evaluation.result.complete,
                    candidate_complete=evaluated.candidate.evaluation.result.complete,
                    baseline_strict_failed=evaluated.baseline.evaluation.strict_failed,
                    candidate_strict_failed=evaluated.candidate.evaluation.strict_failed,
                    baseline_scheduled_effect_ids=tuple(
                        item.identifier for item in evaluated.baseline.scheduled_effects
                    ),
                    candidate_scheduled_effect_ids=tuple(
                        item.identifier for item in evaluated.candidate.scheduled_effects
                    ),
                )
            )
        return PlacementCandidateComparison(validation, tuple(positions), tuple(comparisons))


def _unique_abilities(items: list[AbilitySummary]) -> tuple[AbilitySummary, ...]:
    return tuple({item.ability_id: item for item in items}[key] for key in sorted({item.ability_id for item in items}))


class PlacementQualificationFilter:
    def __init__(self, *, indispensable_ability_ids: frozenset[str] = frozenset()) -> None:
        self.indispensable_ability_ids = indispensable_ability_ids

    def from_validation(self, validation: ValidationResult) -> PlacementCandidateResult:
        warnings = tuple(
            item
            for item in validation.warnings
            if not item.startswith("Only one current position is evaluated")
        )
        return PlacementCandidateResult(
            replacement=validation.replacement,
            status=RecommendationStatus.EXCLUDED,
            positions=(),
            gained_abilities=(),
            lost_abilities=(),
            new_unresolved_ability_ids=(),
            new_unresolved_messages=(),
            warnings=warnings,
            exclusion_reasons=validation.errors,
            explanation="The placement cannot be evaluated because validation failed.",
        )

    def qualify(self, comparison: PlacementCandidateComparison) -> PlacementCandidateResult:
        gains = [metric for position in comparison.positions for metric in position.gains]
        losses = [metric for position in comparison.positions for metric in position.losses]
        gained = _unique_abilities(
            [item for value in comparison.position_comparisons for item in value.gained_abilities]
        )
        lost = _unique_abilities(
            [item for value in comparison.position_comparisons for item in value.lost_abilities]
        )
        new_unresolved = tuple(
            sorted(
                {
                    item
                    for value in comparison.position_comparisons
                    for item in value.new_unresolved_ability_ids
                }
            )
        )
        unresolved_messages = tuple(
            dict.fromkeys(
                item
                for value in comparison.position_comparisons
                for item in value.unresolved_messages
            )
        )
        warning_items = [
            item
            for value in comparison.position_comparisons
            for item in value.warnings
            if not item.startswith("Only one current position is evaluated")
            and not item.startswith("Delayed effects are reported")
        ]
        if any(
            item.baseline_scheduled_effect_ids or item.candidate_scheduled_effect_ids
            for item in comparison.positions
        ):
            warning_items.append(
                "Delayed effects are reported per position but are not resolved as a multi-shot sequence."
            )
        warnings = tuple(dict.fromkeys(warning_items))
        strict_failed = any(
            item.baseline_strict_failed or item.candidate_strict_failed for item in comparison.positions
        )
        lost_indispensable = tuple(
            sorted(self.indispensable_ability_ids & {item.ability_id for item in lost})
        )
        exclusions: list[str] = []
        if strict_failed:
            exclusions.append("At least one matrix evaluation failed in strict mode.")
        if new_unresolved:
            exclusions.append("The placement introduces unresolved abilities: " + ", ".join(new_unresolved))
        if lost_indispensable:
            exclusions.append("The placement removes indispensable abilities: " + ", ".join(lost_indispensable))

        if exclusions:
            status = RecommendationStatus.EXCLUDED
            explanation = "The placement is excluded because the multi-position result is not sufficiently qualified."
        elif gains and not losses:
            status = RecommendationStatus.PARETO
            explanation = "At least one qualified matrix cell improves and no qualified cell degrades."
        elif not gains and not losses:
            status = RecommendationStatus.NEUTRAL
            explanation = "No qualified matrix cell changes across the five evaluated positions."
        else:
            status = RecommendationStatus.TRADEOFF
            explanation = "The placement contains gains and losses across the multi-position matrix."
        return PlacementCandidateResult(
            replacement=comparison.validation.replacement,
            status=status,
            positions=comparison.positions,
            gained_abilities=gained,
            lost_abilities=lost,
            new_unresolved_ability_ids=new_unresolved,
            new_unresolved_messages=unresolved_messages,
            warnings=warnings,
            exclusion_reasons=tuple(exclusions),
            explanation=explanation,
        )


class PlacementRecommendationFormatter:
    _ORDER = (
        RecommendationStatus.PARETO,
        RecommendationStatus.TRADEOFF,
        RecommendationStatus.NEUTRAL,
        RecommendationStatus.EXCLUDED,
    )
    _HEADINGS = {
        RecommendationStatus.PARETO: "Pareto improvements",
        RecommendationStatus.TRADEOFF: "Tradeoffs to examine",
        RecommendationStatus.NEUTRAL: "Neutral placements",
        RecommendationStatus.EXCLUDED: "Excluded placements",
    }

    @classmethod
    def render_text(cls, result: PlacementRecommendationResult) -> str:
        lines = [
            "=" * 80,
            "Placement recommendation",
            f"Baseline bag: {result.request.bag_id}",
            f"Incoming club: {result.incoming_club_name}",
            f"Level mode: {result.request.level_mode}",
        ]
        if result.request.level is not None:
            lines.append(f"Scenario level: {result.request.level}")
        lines.extend(
            [
                f"Generated placements: {len(result.candidates)}",
                "No aggregate score is computed; every candidate is evaluated on all five current positions.",
            ]
        )
        for status in cls._ORDER:
            candidates = [item for item in result.candidates if item.status is status]
            lines.extend(["", cls._HEADINGS[status] + f" ({len(candidates)})"])
            if not candidates:
                lines.append("  none")
                continue
            for candidate in candidates:
                replacement = candidate.replacement
                if replacement is None:
                    title = "Unknown replacement"
                else:
                    title = (
                        f"Position {replacement.position} — {replacement.outgoing_club_name} "
                        f"-> {replacement.incoming_club_name}"
                    )
                lines.extend(["-" * 80, title, f"Status: {candidate.status.value.upper()}", "Gains:"])
                lines.extend(cls._matrix_lines(candidate.gains))
                lines.append("Losses:")
                lines.extend(cls._matrix_lines(candidate.losses))
                lines.append("Gained abilities:")
                lines.extend(cls._ability_lines(candidate.gained_abilities))
                lines.append("Lost abilities:")
                lines.extend(cls._ability_lines(candidate.lost_abilities))
                lines.append("New unresolved abilities:")
                lines.extend([f"  {item}" for item in candidate.new_unresolved_ability_ids] or ["  none"])
                lines.extend([f"    Reason: {item}" for item in candidate.new_unresolved_messages])
                if candidate.exclusion_reasons:
                    lines.append("Exclusion reasons:")
                    lines.extend(f"  {item}" for item in candidate.exclusion_reasons)
                qualification = (
                    "excluded"
                    if candidate.status is RecommendationStatus.EXCLUDED
                    else "relative to baseline gaps" if any("retains unresolved" in item for item in candidate.warnings)
                    else "complete"
                )
                lines.append(f"Qualification: {qualification}")
                lines.append("Warnings:")
                lines.extend([f"  {item}" for item in candidate.warnings] or ["  none"])
                lines.extend(["Summary:", f"  {candidate.explanation}"])
        lines.extend(["", "=" * 80])
        return "\n".join(lines)

    @staticmethod
    def _matrix_lines(items: tuple[tuple[int, str, MetricDelta], ...]) -> list[str]:
        if not items:
            return ["  none"]
        return [
            f"  Position {position} ({club}): {metric.label} {metric.delta:+g} {metric.unit} "
            f"({metric.baseline:g} -> {metric.candidate:g})"
            for position, club, metric in items
        ]

    @staticmethod
    def _ability_lines(items: tuple[AbilitySummary, ...]) -> list[str]:
        return [f"  {item.source} [{item.ability_id}]" for item in items] or ["  none"]

    @staticmethod
    def render_json(result: PlacementRecommendationResult) -> str:
        return json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)


class PlacementRecommendationService:
    def __init__(
        self,
        *,
        user_dir: str | Path = "data/user",
        catalog_path: str | Path = "data/normalized/clubs_official.json",
        evaluator: BagEvaluator | None = None,
        indispensable_ability_ids: frozenset[str] = frozenset(),
    ) -> None:
        self.generator = PlacementCandidateGenerator(user_dir=user_dir)
        self.validator = CandidateValidator(user_dir=user_dir, catalog_path=catalog_path)
        candidate_evaluator = CandidateEvaluator(evaluator or RuleEngineBagEvaluator(catalog_path))
        comparator = CandidateComparator()
        self.matrix_evaluator = PlacementCandidateEvaluator(candidate_evaluator, comparator)
        self.qualification = PlacementQualificationFilter(
            indispensable_ability_ids=indispensable_ability_ids
        )

    def analyze(self, request: PlacementRecommendationRequest) -> PlacementRecommendationResult:
        generated = self.generator.generate(request)
        candidates: list[PlacementCandidateResult] = []
        incoming_name = request.incoming_club_id
        for candidate_request in generated:
            validation = self.validator.validate(candidate_request)
            if validation.replacement is not None:
                incoming_name = validation.replacement.incoming_club_name
            if not validation.valid:
                candidates.append(self.qualification.from_validation(validation))
                continue
            comparison = self.matrix_evaluator.evaluate(validation)
            candidates.append(self.qualification.qualify(comparison))
        return PlacementRecommendationResult(request, incoming_name, tuple(candidates))
