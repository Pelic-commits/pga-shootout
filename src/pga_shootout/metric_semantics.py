"""Data-driven meaning and safe usage rules for objective metrics."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


VALID_DIRECTIONS = {"maximize", "minimize", "target", "descriptive", "context_dependent"}


class MetricSemanticsError(ValueError):
    pass


@dataclass(frozen=True)
class MetricSemantic:
    identifier: str
    label: str
    unit: str | None
    direction: str
    relevant_functions: tuple[str, ...]
    relevant_contexts: Mapping[str, tuple[Any, ...]]
    constraint_allowed: bool
    objective_allowed: bool
    support_qualifying_allowed: bool
    confidence: str
    provenance: str

    def context_matches(self, function_id: str, context: Mapping[str, Any]) -> bool:
        if self.relevant_functions and function_id not in self.relevant_functions:
            return False
        return all(context.get(key) in accepted for key, accepted in self.relevant_contexts.items())


class MetricSemanticsRegistry:
    def __init__(self, metrics: tuple[MetricSemantic, ...], default: MetricSemantic) -> None:
        self._metrics = {item.identifier: item for item in metrics}
        self.default = default

    @classmethod
    def load(cls, path: str | Path = "data/strategies/metric_semantics.json") -> "MetricSemanticsRegistry":
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if document.get("schema_version") != "1.0.0":
            raise MetricSemanticsError("Unsupported metric-semantics schema")
        default = _semantic("__default__", document["default"])
        metrics = tuple(_semantic(str(item["identifier"]), item) for item in document.get("metrics", ()))
        if len({item.identifier for item in metrics}) != len(metrics):
            raise MetricSemanticsError("Metric identifiers must be unique")
        return cls(metrics, default)

    def get(self, identifier: str) -> MetricSemantic:
        return self._metrics.get(identifier, MetricSemantic(
            identifier=identifier,
            label=identifier.replace("_", " ").title(),
            unit=self.default.unit,
            direction=self.default.direction,
            relevant_functions=self.default.relevant_functions,
            relevant_contexts=self.default.relevant_contexts,
            constraint_allowed=self.default.constraint_allowed,
            objective_allowed=self.default.objective_allowed,
            support_qualifying_allowed=self.default.support_qualifying_allowed,
            confidence=self.default.confidence,
            provenance=self.default.provenance,
        ))

    @property
    def metrics(self) -> tuple[MetricSemantic, ...]:
        return tuple(self._metrics.values())


def _semantic(identifier: str, value: Mapping[str, Any]) -> MetricSemantic:
    direction = str(value["direction"])
    if direction not in VALID_DIRECTIONS:
        raise MetricSemanticsError(f"Invalid direction for {identifier}: {direction}")
    return MetricSemantic(
        identifier=identifier,
        label=str(value["label"]),
        unit=str(value["unit"]) if value.get("unit") is not None else None,
        direction=direction,
        relevant_functions=tuple(str(item) for item in value.get("relevant_functions", ())),
        relevant_contexts={str(key): tuple(items) for key, items in value.get("relevant_contexts", {}).items()},
        constraint_allowed=bool(value.get("constraint_allowed", False)),
        objective_allowed=bool(value.get("objective_allowed", False)),
        support_qualifying_allowed=bool(value.get("support_qualifying_allowed", False)),
        confidence=str(value.get("confidence", "unknown")),
        provenance=str(value.get("provenance", "")),
    )
