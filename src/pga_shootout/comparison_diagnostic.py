"""Objective completeness facts for bag comparisons; no score or weighting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .reference_gap_report import analyze_reference_gaps


@dataclass(frozen=True)
class BagDiagnostic:
    bag_id: str
    ability_occurrences: int
    simulated_abilities: int
    non_simulated_abilities: int
    ambiguous_abilities: int
    scenario_required_abilities: int
    unsupported_abilities: int
    partial_abilities: int
    resolved_contributions: int
    effective_contributions: int
    ignored_contributions: int
    unresolved_contributions: int
    unknown_user_level_club_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonDiagnostic:
    metrics_compared: tuple[str, ...]
    left: BagDiagnostic
    right: BagDiagnostic


def _bag_diagnostic(side: Any, status_by_ability: dict[str, str], unknown_level_ids: set[str]) -> BagDiagnostic:
    contributions = side.ability_contributions
    resolved = tuple(item for item in contributions if item.evaluated and not item.unresolved)
    effective = tuple(item for item in resolved if any(value != 0 for value in item.modification.values()))
    unresolved = tuple(item for item in contributions if item.unresolved)
    statuses = tuple(status_by_ability.get(item.ability_id, "unsupported") for item in contributions)
    return BagDiagnostic(
        bag_id=side.evaluation.bag.identifier,
        ability_occurrences=len(contributions),
        simulated_abilities=len(resolved),
        non_simulated_abilities=len(unresolved),
        ambiguous_abilities=statuses.count("ambiguous"),
        scenario_required_abilities=statuses.count("scenario_required"),
        unsupported_abilities=statuses.count("unsupported"),
        partial_abilities=statuses.count("partial"),
        resolved_contributions=len(resolved),
        effective_contributions=len(effective),
        ignored_contributions=len(resolved) - len(effective),
        unresolved_contributions=len(unresolved),
        unknown_user_level_club_ids=tuple(
            club_id for club_id in side.evaluation.bag.club_ids if club_id in unknown_level_ids
        ),
    )


def build_comparison_diagnostic(
    left: Any,
    right: Any,
    metrics: Iterable[Any],
    *,
    user_dir: str | Path,
    catalog_path: str | Path,
) -> ComparisonDiagnostic:
    normalized_dir = Path(catalog_path).parent
    raw_path = normalized_dir.parent / "raw" / "pga_club_stats_extract_v2_2026-07-21.json"
    reference = analyze_reference_gaps(
        user_dir=user_dir,
        normalized_dir=normalized_dir,
        raw_catalog_path=raw_path,
    )
    status_by_ability = {item.occurrence_id: item.status for item in reference.abilities}
    unknown_levels = {item.club_id for item in reference.abilities if item.user_level is None}
    return ComparisonDiagnostic(
        metrics_compared=tuple(metric.definition.identifier for metric in metrics),
        left=_bag_diagnostic(left, status_by_ability, unknown_levels),
        right=_bag_diagnostic(right, status_by_ability, unknown_levels),
    )


def render_comparison_diagnostic(diagnostic: ComparisonDiagnostic) -> list[str]:
    lines = [
        "Confidence diagnostic (objective facts; no score)",
        "Metrics compared: " + ", ".join(diagnostic.metrics_compared),
    ]
    for label, bag in (("Left", diagnostic.left), ("Right", diagnostic.right)):
        unknown = ", ".join(bag.unknown_user_level_club_ids) or "none"
        lines.extend(
            [
                f"{label} bag ({bag.bag_id}):",
                f"  Simulated abilities: {bag.simulated_abilities}/{bag.ability_occurrences}",
                f"  Non-simulated abilities: {bag.non_simulated_abilities}",
                f"  Classified gaps: ambiguous={bag.ambiguous_abilities}, scenario_required={bag.scenario_required_abilities}, unsupported={bag.unsupported_abilities}, partial={bag.partial_abilities}",
                f"  Contributions: resolved={bag.resolved_contributions}, effective={bag.effective_contributions}, ignored={bag.ignored_contributions}, unresolved={bag.unresolved_contributions}",
                f"  Unknown user levels: {unknown}",
            ]
        )
    return lines
