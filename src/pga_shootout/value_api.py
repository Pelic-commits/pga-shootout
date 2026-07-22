"""Neutral metric and weighting contracts; this module never computes a score."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Protocol


class MetricKind(StrEnum):
    STAT = "stat"
    STATIC_MODIFIER = "static_modifier"


@dataclass(frozen=True)
class MetricDefinition:
    identifier: str
    label: str
    kind: MetricKind
    unit: str


@dataclass(frozen=True)
class ComparableMetric:
    definition: MetricDefinition
    left_base: float
    left_contribution: float
    left_final: float
    right_base: float
    right_contribution: float
    right_final: float
    difference_right_minus_left: float


@dataclass(frozen=True)
class WeightingContext:
    user_profile: Mapping[str, Any]
    course_type: str | None = None
    objective: str | None = None


@dataclass(frozen=True)
class MetricWeightingRequest:
    context: WeightingContext
    metrics: tuple[ComparableMetric, ...]


class MetricWeightProvider(Protocol):
    def weights_for(self, request: MetricWeightingRequest) -> Mapping[str, float]: ...


METRIC_DEFINITIONS: Mapping[str, MetricDefinition] = {
    "power": MetricDefinition("power", "Power", MetricKind.STAT, "points"),
    "control": MetricDefinition("control", "Control", MetricKind.STAT, "points"),
    "spin": MetricDefinition("spin", "Spin", MetricKind.STAT, "points"),
    "loft_angle_degrees": MetricDefinition(
        "loft_angle_degrees", "Launch angle adjustment", MetricKind.STATIC_MODIFIER, "degrees"
    ),
    "sand_bounce_count": MetricDefinition(
        "sand_bounce_count", "Maximum sand bounces", MetricKind.STATIC_MODIFIER, "bounces"
    ),
    "water_bounce_count": MetricDefinition(
        "water_bounce_count", "Maximum water bounces", MetricKind.STATIC_MODIFIER, "bounces"
    ),
    "bounce_reduction_percent": MetricDefinition(
        "bounce_reduction_percent", "Bounce reduction", MetricKind.STATIC_MODIFIER, "percent"
    ),
}


def metric_definition(identifier: str, kind: MetricKind) -> MetricDefinition:
    return METRIC_DEFINITIONS.get(
        identifier,
        MetricDefinition(identifier, identifier.replace("_", " ").title(), kind, "value"),
    )
