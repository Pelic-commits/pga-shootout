"""Public engine boundary for a future bag optimizer; no search algorithm lives here."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Protocol

from .bag_comparison import ComparedBag, summarize_bag_evaluation
from .bag_evaluation import evaluate_bag
from .models import EvaluationMode
from .user_data import SavedBag


ClubLevel = int | str


class ReadinessStatus(StrEnum):
    READY = "ready"
    PARTIAL = "partial"
    MISSING = "missing"


@dataclass(frozen=True)
class OptimizerReadinessItem:
    identifier: str
    status: ReadinessStatus
    evidence: str


def optimizer_readiness_checklist() -> tuple[OptimizerReadinessItem, ...]:
    """Return factual capabilities; no percentage or subjective score."""
    return (
        OptimizerReadinessItem("separate_metrics", ReadinessStatus.READY, "ComparableMetric exposes each metric separately."),
        OptimizerReadinessItem("ability_contributions", ReadinessStatus.READY, "AbilityContribution identifies every source ability."),
        OptimizerReadinessItem("normalization", ReadinessStatus.MISSING, "No cross-unit metric normalization policy exists."),
        OptimizerReadinessItem("configurable_weights", ReadinessStatus.PARTIAL, "MetricWeightProvider is a protocol without a validated provider."),
        OptimizerReadinessItem("objective_profiles", ReadinessStatus.PARTIAL, "WeightingContext accepts an objective but no validated profiles exist."),
        OptimizerReadinessItem("multi_club_aggregation", ReadinessStatus.PARTIAL, "Candidates are evaluable by position; bag-wide aggregation is undefined."),
        OptimizerReadinessItem("ranking", ReadinessStatus.MISSING, "No aggregate score or ranking algorithm exists."),
        OptimizerReadinessItem("inventory_constraints", ReadinessStatus.PARTIAL, "Inventory data exists but candidate generation does not enforce it."),
    )


@dataclass(frozen=True)
class BagCandidate:
    identifier: str
    club_ids: tuple[str, ...]
    levels: Mapping[str, ClubLevel]


@dataclass(frozen=True)
class BagEvaluationRequest:
    candidate: BagCandidate
    current_position: int
    mode: EvaluationMode = EvaluationMode.PARTIAL


class BagEvaluator(Protocol):
    def evaluate(self, request: BagEvaluationRequest) -> ComparedBag: ...


@dataclass(frozen=True)
class RuleEngineBagEvaluator:
    catalog_path: str | Path = "data/normalized/clubs_official.json"

    def evaluate(self, request: BagEvaluationRequest) -> ComparedBag:
        candidate = request.candidate
        if not 1 <= request.current_position <= len(candidate.club_ids):
            raise ValueError("Current position must exist in the candidate bag")
        missing_levels = tuple(club_id for club_id in candidate.club_ids if club_id not in candidate.levels)
        if missing_levels:
            raise ValueError(f"Missing candidate club levels: {', '.join(missing_levels)}")
        saved_bag = SavedBag(candidate.identifier, candidate.identifier, "candidate", candidate.club_ids, ())
        evaluation = evaluate_bag(
            saved_bag,
            level=candidate.levels,
            mode=request.mode,
            catalog_path=self.catalog_path,
            current_club_id=candidate.club_ids[request.current_position - 1],
        )
        return summarize_bag_evaluation(evaluation, request.current_position)
