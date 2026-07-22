"""Explainable comparison of two saved bags without invented scoring weights."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .bag_evaluation import BagEvaluation, evaluate_saved_bag, load_saved_bag
from .models import EvaluationMode


class BagComparisonError(ValueError):
    pass


@dataclass(frozen=True)
class AppliedChange:
    source: str
    mechanism: str
    modification: Mapping[str, float]


@dataclass(frozen=True)
class AbilityContribution:
    source_club_id: str
    ability_id: str
    source: str
    mechanism: str
    modification: Mapping[str, float]
    evaluated: bool
    applied: bool
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ComparedBag:
    evaluation: BagEvaluation
    current_position: int
    applied_changes: tuple[AppliedChange, ...]
    ability_impact: Mapping[str, float]
    modifier_impact: Mapping[str, float]
    ability_contributions: tuple[AbilityContribution, ...]


@dataclass(frozen=True)
class BagComparison:
    left: ComparedBag
    right: ComparedBag
    level: int | str
    mode: EvaluationMode
    final_difference_right_minus_left: Mapping[str, float]
    ability_impact_difference_right_minus_left: Mapping[str, float]
    modifier_difference_right_minus_left: Mapping[str, float]

    @property
    def strict_failed(self) -> bool:
        return self.left.evaluation.strict_failed or self.right.evaluation.strict_failed

    @property
    def gained_ability_impact(self) -> Mapping[str, float]:
        return {stat: value for stat, value in self.ability_impact_difference_right_minus_left.items() if value > 0}

    @property
    def lost_ability_impact(self) -> Mapping[str, float]:
        return {stat: value for stat, value in self.ability_impact_difference_right_minus_left.items() if value < 0}

    @property
    def gained_modifier_impact(self) -> Mapping[str, float]:
        return {name: value for name, value in self.modifier_difference_right_minus_left.items() if value > 0}

    @property
    def lost_modifier_impact(self) -> Mapping[str, float]:
        return {name: value for name, value in self.modifier_difference_right_minus_left.items() if value < 0}


def _applied_changes(evaluation: BagEvaluation) -> tuple[AppliedChange, ...]:
    return tuple(
        AppliedChange(entry.source, entry.mechanism, dict(entry.modification))
        for entry in evaluation.result.explain
        if entry.mechanism != "dsl_pipeline"
        and entry.applied
        and any(value != 0 for value in entry.modification.values())
    )


def _ability_impact(evaluation: BagEvaluation) -> dict[str, float]:
    base = evaluation.result.base_stats.as_dict()
    final = evaluation.result.final_stats.as_dict()
    return {stat: final[stat] - base[stat] for stat in ("power", "control", "spin")}


def ability_contributions(evaluation: BagEvaluation) -> tuple[AbilityContribution, ...]:
    """Return stable, machine-readable totals for every ability in bag order."""
    contributions = []
    for bag_entry in evaluation.state.bag.entries:
        for ability in bag_entry.club.abilities:
            for effect in ability.effects:
                journal = tuple(entry for entry in evaluation.result.explain if entry.source == effect.source)
                leaves = tuple(entry for entry in journal if entry.mechanism != "dsl_pipeline")
                modification = {
                    stat: sum(entry.modification.get(stat, 0.0) for entry in leaves if entry.applied)
                    for stat in ("power", "control", "spin")
                }
                modifier_names = {
                    name
                    for entry in leaves
                    for name in entry.modification
                    if name not in modification
                }
                modification.update(
                    {
                        name: sum(entry.modification.get(name, 0.0) for entry in leaves if entry.applied)
                        for name in sorted(modifier_names)
                    }
                )
                unresolved = tuple(entry.message for entry in journal if entry.message.startswith("Unresolved"))
                contributions.append(
                    AbilityContribution(
                        source_club_id=bag_entry.club.identifier,
                        ability_id=ability.identifier,
                        source=effect.source,
                        mechanism=effect.mechanism,
                        modification=modification,
                        evaluated=bool(journal),
                        applied=any(entry.applied for entry in leaves),
                        unresolved=unresolved,
                    )
                )
    return tuple(contributions)


def summarize_bag_evaluation(evaluation: BagEvaluation, current_position: int) -> ComparedBag:
    return ComparedBag(
        evaluation,
        current_position,
        _applied_changes(evaluation),
        _ability_impact(evaluation),
        dict(evaluation.result.modifiers),
        ability_contributions(evaluation),
    )


def compare_saved_bags(
    left_bag_id: str,
    right_bag_id: str,
    *,
    level: int | str,
    current_position: int = 1,
    mode: EvaluationMode,
    user_dir: str | Path = "data/user",
    catalog_path: str | Path = "data/normalized/clubs_official.json",
) -> BagComparison:
    if current_position < 1:
        raise BagComparisonError("Current position must be at least 1")
    left_saved = load_saved_bag(user_dir, left_bag_id)
    right_saved = load_saved_bag(user_dir, right_bag_id)
    if current_position > len(left_saved.club_ids) or current_position > len(right_saved.club_ids):
        raise BagComparisonError(f"Current position {current_position} is not present in both bags")

    left = evaluate_saved_bag(
        left_bag_id,
        level=level,
        mode=mode,
        user_dir=user_dir,
        catalog_path=catalog_path,
        current_club_id=left_saved.club_ids[current_position - 1],
    )
    right = evaluate_saved_bag(
        right_bag_id,
        level=level,
        mode=mode,
        user_dir=user_dir,
        catalog_path=catalog_path,
        current_club_id=right_saved.club_ids[current_position - 1],
    )
    left_stats = left.result.final_stats.as_dict()
    right_stats = right.result.final_stats.as_dict()
    left_impact = _ability_impact(left)
    right_impact = _ability_impact(right)
    left_summary = summarize_bag_evaluation(left, current_position)
    right_summary = summarize_bag_evaluation(right, current_position)
    modifier_names = left_summary.modifier_impact.keys() | right_summary.modifier_impact.keys()
    return BagComparison(
        left=left_summary,
        right=right_summary,
        level=level,
        mode=mode,
        final_difference_right_minus_left={
            stat: right_stats[stat] - left_stats[stat]
            for stat in ("power", "control", "spin")
        },
        ability_impact_difference_right_minus_left={
            stat: right_impact[stat] - left_impact[stat]
            for stat in ("power", "control", "spin")
        },
        modifier_difference_right_minus_left={
            name: right_summary.modifier_impact.get(name, 0.0) - left_summary.modifier_impact.get(name, 0.0)
            for name in sorted(modifier_names)
        },
    )


def _change_lines(side: ComparedBag) -> list[str]:
    if not side.applied_changes:
        return ["  none"]
    lines = []
    for change in side.applied_changes:
        deltas = ", ".join(
            f"{stat} {value:+g}" for stat, value in change.modification.items() if value != 0
        )
        lines.append(f"  {change.source} / {change.mechanism}: {deltas}")
    return lines


def _unresolved_lines(evaluation: BagEvaluation) -> list[str]:
    if not evaluation.result.unresolved:
        return ["  none"]
    return [f"  {item}" for item in evaluation.result.unresolved]


def render_bag_comparison(comparison: BagComparison) -> str:
    left = comparison.left.evaluation
    right = comparison.right.evaluation
    lines = [
        "=" * 72,
        "Bag comparison",
        f"Level scenario: {comparison.level}",
        f"Evaluation mode: {comparison.mode.value}",
        f"Selected position: {comparison.left.current_position}",
        "",
        "Composition",
    ]
    for index, (left_id, right_id) in enumerate(zip(left.bag.club_ids, right.bag.club_ids), start=1):
        marker = "==" if left_id == right_id else "!="
        left_name = left.state.bag.get(left_id).club.name
        right_name = right.state.bag.get(right_id).club.name
        lines.append(f"{index}. {left_name} {marker} {right_name}")

    left_current = left.state.current_entry.club.name
    right_current = right.state.current_entry.club.name
    lines.extend(
        [
            "",
            f"Left:  {left.bag.name} - {left_current}",
            f"Right: {right.bag.name} - {right_current}",
            "",
            "Stats (difference = right - left)",
            "Stat       Left base  Left abilities  Left final  Right base  Right abilities  Right final  Final diff",
        ]
    )
    left_base = left.result.base_stats.as_dict()
    left_final = left.result.final_stats.as_dict()
    right_base = right.result.base_stats.as_dict()
    right_final = right.result.final_stats.as_dict()
    for stat in ("power", "control", "spin"):
        lines.append(
            f"{stat.capitalize():<10} {left_base[stat]:>9g}  {comparison.left.ability_impact[stat]:>+14g}"
            f"  {left_final[stat]:>10g}  {right_base[stat]:>10g}"
            f"  {comparison.right.ability_impact[stat]:>+15g}  {right_final[stat]:>11g}"
            f"  {comparison.final_difference_right_minus_left[stat]:>+10g}"
        )

    if comparison.modifier_difference_right_minus_left:
        lines.extend(["", "Static modifiers (difference = right - left)", "Modifier                 Left  Right  Diff"])
        for name, difference in comparison.modifier_difference_right_minus_left.items():
            lines.append(
                f"{name:<24} {comparison.left.modifier_impact.get(name, 0.0):>5g}"
                f"  {comparison.right.modifier_impact.get(name, 0.0):>5g}  {difference:>+5g}"
            )

    lines.extend(["", "Applied ability changes - left"])
    lines.extend(_change_lines(comparison.left))
    lines.append("Applied ability changes - right")
    lines.extend(_change_lines(comparison.right))
    gained = [
        f"{stat} +{value:g}"
        for stat, value in comparison.gained_ability_impact.items()
    ]
    lost = [
        f"{stat} {value:g}"
        for stat, value in comparison.lost_ability_impact.items()
    ]
    lines.extend(
        [
            "",
            "Bonuses gained by right vs left: " + (", ".join(gained) if gained else "none"),
            "Bonuses lost by right vs left: " + (", ".join(lost) if lost else "none"),
            "",
            f"Unresolved bonuses - left ({len(left.result.unresolved)}):",
            *_unresolved_lines(left),
            f"Unresolved bonuses - right ({len(right.result.unresolved)}):",
            *_unresolved_lines(right),
            f"Strict status: {'FAILED' if comparison.strict_failed else 'SUCCESS' if comparison.mode is EvaluationMode.STRICT else 'NOT REQUESTED'}",
            "No aggregate score: user preference weights and real club levels are not yet validated.",
            "=" * 72,
        ]
    )
    return "\n".join(lines)
