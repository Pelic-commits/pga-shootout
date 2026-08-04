"""Serializable, generic contract for future bag optimization requests.

This module defines requests only.  It deliberately contains no candidate
search, scoring, natural-language interpretation, or rule-engine behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RequestProvenance:
    channel: str
    reference: str
    catalog_version: str


@dataclass(frozen=True)
class SearchScope:
    inventory_selector: Mapping[str, Any]
    bag_size: int = 5
    ordered: bool = True
    scenarios: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class Constraint:
    identifier: str
    subject: Mapping[str, Any]
    operator: str
    expected: Any
    provenance: str
    required_data: tuple[str, ...] = ()


@dataclass(frozen=True)
class Objective:
    priority: int
    operation: str
    metric: str
    scenario_selector: Mapping[str, Any] | None = None
    tie_behavior: str = "continue"


@dataclass(frozen=True)
class OptimizationRequest:
    schema_version: str
    request_id: str
    provenance: RequestProvenance
    scope: SearchScope
    constraints: tuple[Constraint, ...]
    objectives: tuple[Objective, ...]
    comparison_policy: str = "lexicographic_then_pareto"
    uncertainty_policy: str = "report_and_exclude_if_required"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationRequest":
        return cls(
            schema_version=str(value["schema_version"]), request_id=str(value["request_id"]),
            provenance=RequestProvenance(**value["provenance"]),
            scope=SearchScope(
                inventory_selector=dict(value["scope"]["inventory_selector"]),
                bag_size=int(value["scope"].get("bag_size", 5)), ordered=bool(value["scope"].get("ordered", True)),
                scenarios=tuple(value["scope"].get("scenarios", ())),
            ),
            constraints=tuple(
                Constraint(
                    identifier=item["identifier"], subject=dict(item["subject"]), operator=item["operator"],
                    expected=item.get("expected"), provenance=item["provenance"],
                    required_data=tuple(item.get("required_data", ())),
                )
                for item in value.get("constraints", ())
            ),
            objectives=tuple(Objective(**item) for item in value.get("objectives", ())),
            comparison_policy=str(value.get("comparison_policy", "lexicographic_then_pareto")),
            uncertainty_policy=str(value.get("uncertainty_policy", "report_and_exclude_if_required")),
        )


def optimization_examples(catalog_version: str) -> tuple[OptimizationRequest, ...]:
    """Eight fixtures proving that one contract supports unlike questions."""
    base = RequestProvenance("documentation_example", "generic-contract-fixtures", catalog_version)
    owned = {"kind": "owned_clubs", "unlocked": True}

    def request(identifier: str, objectives: tuple[Objective, ...], constraints: tuple[Constraint, ...] = (), scenarios: tuple[Mapping[str, Any], ...] = (), policy: str = "lexicographic_then_pareto") -> OptimizationRequest:
        return OptimizationRequest("1.0.0", identifier, base, SearchScope(owned, scenarios=scenarios), constraints, objectives, policy)

    return (
        request("example-01", (Objective(1, "maximize", "power"),)),
        request("example-02", (Objective(1, "maximize", "control"),)),
        request("example-03", (Objective(1, "maximize", "control"),), (
            Constraint("required-reach", {"metric": "real_carry"}, "gte", {"source": "selected_context"}, "context", ("validated_carry_model",)),
        )),
        request("example-04", (Objective(1, "maximize_minimum", "control", {"kind": "all"}),), scenarios=({"terrain": "fairway"}, {"terrain": "rough"})),
        request("example-05", (Objective(1, "pareto", "power"), Objective(1, "pareto", "control")), policy="pareto_retain_all"),
        request("example-06", (Objective(1, "maximize", "spin"),), (
            Constraint("keep-selected-club", {"collection": "bag", "attribute": "club_id"}, "contains", {"source": "user_selection"}, "user"),
            Constraint("resolved-only", {"metric": "unresolved_abilities"}, "eq", 0, "user"),
        )),
        request("example-07", (Objective(1, "minimize", "bounce"), Objective(2, "maximize", "spin")), scenarios=({"hole_type": "par3"},)),
        request("example-08", (Objective(1, "minimize_variance", "real_carry", {"kind": "all"}),), scenarios=({"wind_speed": 0}, {"wind_speed": 10}, {"wind_speed": 20})),
    )
