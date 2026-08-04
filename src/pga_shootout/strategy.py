"""Data-driven game-strategy contracts and read-only consultation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Mapping

from .optimization_contract import (
    Constraint,
    Objective,
    OptimizationRequest,
    RequestProvenance,
    SearchScope,
)


class StrategyError(ValueError):
    """Raised when a strategy catalog violates the generic contract."""


@dataclass(frozen=True)
class ShotFunction:
    identifier: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class StepContext:
    values: Mapping[str, Any]
    required_data: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutcomeRequirement:
    identifier: str
    subject: Mapping[str, Any]
    operator: str
    expected: Any
    description: str
    required_data: tuple[str, ...] = ()
    mandatory: bool = True


@dataclass(frozen=True)
class LocalObjective:
    priority: int
    operation: str
    metric: str
    description: str
    required_data: tuple[str, ...] = ()
    tie_behavior: str = "continue"


@dataclass(frozen=True)
class ShotStep:
    identifier: str
    name: str
    active_role: str
    function: ShotFunction
    context: StepContext
    requirements: tuple[OutcomeRequirement, ...]
    local_objectives: tuple[LocalObjective, ...]


@dataclass(frozen=True)
class StrategyDefinition:
    identifier: str
    version: str
    user_name: str
    description: str
    origin: str
    bag_size: int
    sequence: tuple[ShotStep, ...]
    uncertainty_policy: str
    expected_active_roles: tuple[str, ...]
    available_support_clubs: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StrategyDefinition":
        sequence = tuple(_step_from_dict(item) for item in value.get("sequence", ()))
        result = cls(
            identifier=str(value["identifier"]),
            version=str(value["version"]),
            user_name=str(value["user_name"]),
            description=str(value["description"]),
            origin=str(value.get("origin", "bundled")),
            bag_size=int(value.get("bag_size", 5)),
            sequence=sequence,
            uncertainty_policy=str(value.get("uncertainty_policy", "report_indeterminate")),
            expected_active_roles=tuple(str(item) for item in value.get("expected_active_roles", ())),
            available_support_clubs=int(value["available_support_clubs"]),
        )
        _validate_strategy(result)
        return result


@dataclass(frozen=True)
class VariantStepPatch:
    step_id: str
    context_updates: Mapping[str, Any]
    required_context_data: tuple[str, ...]
    add_requirements: tuple[OutcomeRequirement, ...]
    add_local_objectives: tuple[LocalObjective, ...]


@dataclass(frozen=True)
class StrategyVariant:
    identifier: str
    version: str
    user_name: str
    description: str
    compatible_strategy_ids: tuple[str, ...]
    patches: tuple[VariantStepPatch, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StrategyVariant":
        patches = tuple(
            VariantStepPatch(
                step_id=str(item["step_id"]),
                context_updates=dict(item.get("context_updates", {})),
                required_context_data=tuple(str(entry) for entry in item.get("required_context_data", ())),
                add_requirements=tuple(_requirement_from_dict(entry) for entry in item.get("add_requirements", ())),
                add_local_objectives=tuple(_objective_from_dict(entry) for entry in item.get("add_local_objectives", ())),
            )
            for item in value.get("patches", ())
        )
        if not patches:
            raise StrategyError(f"Variant {value.get('identifier')!r} has no patches")
        return cls(
            identifier=str(value["identifier"]),
            version=str(value["version"]),
            user_name=str(value["user_name"]),
            description=str(value["description"]),
            compatible_strategy_ids=tuple(str(item) for item in value.get("compatible_strategy_ids", ())),
            patches=patches,
        )


@dataclass(frozen=True)
class ResolvedStrategy:
    definition: StrategyDefinition
    applied_variant_ids: tuple[str, ...] = ()

    @property
    def missing_evaluation_data(self) -> tuple[str, ...]:
        missing: list[str] = []
        for step in self.definition.sequence:
            sources = [
                step.context.required_data,
                *(requirement.required_data for requirement in step.requirements),
                *(objective.required_data for objective in step.local_objectives),
            ]
            for values in sources:
                for value in values:
                    if value not in missing:
                        missing.append(value)
        return tuple(missing)


class StrategyRegistry:
    """Mergeable registry; strategy semantics come exclusively from catalog data."""

    def __init__(
        self,
        strategies: Mapping[str, StrategyDefinition],
        variants: Mapping[str, StrategyVariant],
    ) -> None:
        self._strategies = dict(strategies)
        self._variants = dict(variants)
        self._validate_references()

    @classmethod
    def load(cls, *paths: str | Path) -> "StrategyRegistry":
        if not paths:
            paths = ("data/strategies/strategies.json",)
        strategies: dict[str, StrategyDefinition] = {}
        variants: dict[str, StrategyVariant] = {}
        for source in paths:
            path = Path(source)
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise StrategyError(f"Cannot load strategy catalog {path}: {exc}") from exc
            if not isinstance(document, Mapping) or document.get("schema_version") != "1.0.0":
                raise StrategyError(f"Unsupported strategy catalog schema in {path}")
            for raw in document.get("strategies", ()):
                strategy = StrategyDefinition.from_dict(raw)
                _insert_unique(strategies, strategy.identifier, strategy, path)
            for raw in document.get("variants", ()):
                variant = StrategyVariant.from_dict(raw)
                _insert_unique(variants, variant.identifier, variant, path)
        return cls(strategies, variants)

    @property
    def strategies(self) -> tuple[StrategyDefinition, ...]:
        return tuple(self._strategies.values())

    @property
    def variants(self) -> tuple[StrategyVariant, ...]:
        return tuple(self._variants.values())

    def get(self, identifier: str) -> StrategyDefinition:
        try:
            return self._strategies[identifier]
        except KeyError as exc:
            raise StrategyError(f"Unknown strategy: {identifier}") from exc

    def compatible_variants(self, strategy_id: str) -> tuple[StrategyVariant, ...]:
        self.get(strategy_id)
        return tuple(
            variant for variant in self.variants
            if strategy_id in variant.compatible_strategy_ids
        )

    def resolve(self, strategy_id: str, variant_ids: tuple[str, ...] = ()) -> ResolvedStrategy:
        definition = self.get(strategy_id)
        if len(set(variant_ids)) != len(variant_ids):
            raise StrategyError("A strategy variant cannot be applied more than once")
        for variant_id in variant_ids:
            try:
                variant = self._variants[variant_id]
            except KeyError as exc:
                raise StrategyError(f"Unknown strategy variant: {variant_id}") from exc
            if strategy_id not in variant.compatible_strategy_ids:
                raise StrategyError(f"Variant {variant_id} is not compatible with {strategy_id}")
            definition = _apply_variant(definition, variant)
        return ResolvedStrategy(definition, variant_ids)

    def _validate_references(self) -> None:
        for variant in self._variants.values():
            for strategy_id in variant.compatible_strategy_ids:
                strategy = self._strategies.get(strategy_id)
                if strategy is None:
                    raise StrategyError(
                        f"Variant {variant.identifier} references unknown strategy {strategy_id}"
                    )
                known_steps = {step.identifier for step in strategy.sequence}
                unknown = {patch.step_id for patch in variant.patches} - known_steps
                if unknown:
                    raise StrategyError(
                        f"Variant {variant.identifier} references unknown steps for {strategy_id}: "
                        f"{', '.join(sorted(unknown))}"
                    )


def to_optimization_request(
    strategy: ResolvedStrategy,
    *,
    request_id: str,
    catalog_version: str,
) -> OptimizationRequest:
    """Compile the generic strategy shape into the existing neutral request contract."""

    definition = strategy.definition
    scenarios = tuple(
        {
            "step_id": step.identifier,
            "function": step.function.identifier,
            "function_parameters": dict(step.function.parameters),
            **dict(step.context.values),
        }
        for step in definition.sequence
    )
    constraints: list[Constraint] = []
    objectives: list[Objective] = []
    for step in definition.sequence:
        constraints.append(
            Constraint(
                identifier=f"{step.identifier}:active_assignment",
                subject={"kind": "active_club_assignment", "step_id": step.identifier, "role": step.active_role},
                operator="exists",
                expected=True,
                provenance=f"strategy:{definition.identifier}",
            )
        )
        constraints.extend(
            Constraint(
                identifier=f"{step.identifier}:{requirement.identifier}",
                subject={**dict(requirement.subject), "step_id": step.identifier},
                operator=requirement.operator,
                expected=requirement.expected,
                provenance=f"strategy:{definition.identifier}",
                required_data=requirement.required_data,
            )
            for requirement in step.requirements
            if requirement.mandatory
        )
        objectives.extend(
            Objective(
                priority=objective.priority,
                operation=objective.operation,
                metric=objective.metric,
                scenario_selector={"step_id": step.identifier},
                tie_behavior=objective.tie_behavior,
            )
            for objective in step.local_objectives
        )
    reference = definition.identifier
    if strategy.applied_variant_ids:
        reference += "+" + "+".join(strategy.applied_variant_ids)
    return OptimizationRequest(
        schema_version="1.0.0",
        request_id=request_id,
        provenance=RequestProvenance("strategy_registry", reference, catalog_version),
        scope=SearchScope(
            inventory_selector={"kind": "owned_clubs", "unlocked": True},
            bag_size=definition.bag_size,
            ordered=True,
            scenarios=scenarios,
        ),
        constraints=tuple(constraints),
        objectives=tuple(objectives),
        comparison_policy="constraints_then_local_pareto",
        uncertainty_policy=definition.uncertainty_policy,
    )


def render_strategy_list(registry: StrategyRegistry) -> str:
    lines = ["Stratégies disponibles", "=" * 72]
    for strategy in registry.strategies:
        variants = registry.compatible_variants(strategy.identifier)
        suffix = ", ".join(item.identifier for item in variants) or "aucune"
        lines.append(
            f"- {strategy.identifier}: {strategy.user_name} — "
            f"{len(strategy.sequence)} coups, {strategy.available_support_clubs} supports disponibles; "
            f"variantes: {suffix}"
        )
    return "\n".join(lines)


def render_strategy(strategy: ResolvedStrategy, compatible_variants: tuple[StrategyVariant, ...]) -> str:
    definition = strategy.definition
    lines = [
        f"{definition.user_name} ({definition.identifier})",
        "=" * 72,
        definition.description,
        f"Version: {definition.version}",
        f"Origine: {definition.origin}",
        f"Politique d'incertitude: {definition.uncertainty_policy}",
        f"Rôles actifs: {', '.join(definition.expected_active_roles)}",
        f"Clubs support disponibles: {definition.available_support_clubs}",
        f"Variantes appliquées: {', '.join(strategy.applied_variant_ids) or 'aucune'}",
        "",
        "Séquence",
    ]
    for index, step in enumerate(definition.sequence, start=1):
        lines.extend(
            [
                f"{index}. {step.name} [{step.active_role}]",
                f"   Fonction: {step.function.identifier}",
                f"   Contexte: {json.dumps(step.context.values, ensure_ascii=False, sort_keys=True)}",
                "   Exigences: " + "; ".join(item.description for item in step.requirements),
                "   Objectifs locaux: " + "; ".join(item.description for item in step.local_objectives),
            ]
        )
    lines.extend(
        [
            "",
            "Variantes compatibles: " + (", ".join(item.identifier for item in compatible_variants) or "aucune"),
            "Données manquantes pour une évaluation complète: "
            + (", ".join(strategy.missing_evaluation_data) or "aucune"),
        ]
    )
    return "\n".join(lines)


def _step_from_dict(value: Mapping[str, Any]) -> ShotStep:
    function = value["function"]
    context = value.get("context", {})
    return ShotStep(
        identifier=str(value["identifier"]),
        name=str(value["name"]),
        active_role=str(value["active_role"]),
        function=ShotFunction(str(function["identifier"]), dict(function.get("parameters", {}))),
        context=StepContext(
            dict(context.get("values", {})),
            tuple(str(item) for item in context.get("required_data", ())),
        ),
        requirements=tuple(_requirement_from_dict(item) for item in value.get("requirements", ())),
        local_objectives=tuple(_objective_from_dict(item) for item in value.get("local_objectives", ())),
    )


def _requirement_from_dict(value: Mapping[str, Any]) -> OutcomeRequirement:
    return OutcomeRequirement(
        identifier=str(value["identifier"]),
        subject=dict(value["subject"]),
        operator=str(value["operator"]),
        expected=value.get("expected"),
        description=str(value["description"]),
        required_data=tuple(str(item) for item in value.get("required_data", ())),
        mandatory=bool(value.get("mandatory", True)),
    )


def _objective_from_dict(value: Mapping[str, Any]) -> LocalObjective:
    return LocalObjective(
        priority=int(value["priority"]),
        operation=str(value["operation"]),
        metric=str(value["metric"]),
        description=str(value["description"]),
        required_data=tuple(str(item) for item in value.get("required_data", ())),
        tie_behavior=str(value.get("tie_behavior", "continue")),
    )


def _validate_strategy(strategy: StrategyDefinition) -> None:
    if not strategy.sequence:
        raise StrategyError(f"Strategy {strategy.identifier} has no shot sequence")
    step_ids = tuple(step.identifier for step in strategy.sequence)
    if len(set(step_ids)) != len(step_ids):
        raise StrategyError(f"Strategy {strategy.identifier} contains duplicate step identifiers")
    roles = tuple(dict.fromkeys(step.active_role for step in strategy.sequence))
    if roles != strategy.expected_active_roles:
        raise StrategyError(
            f"Strategy {strategy.identifier} active roles do not match its sequence: {roles!r}"
        )
    expected_support = strategy.bag_size - len(roles)
    if strategy.available_support_clubs != expected_support or expected_support < 0:
        raise StrategyError(f"Strategy {strategy.identifier} has an inconsistent support-club count")


def _insert_unique(target: dict[str, Any], key: str, value: Any, path: Path) -> None:
    if key in target:
        raise StrategyError(f"Duplicate identifier {key!r} while loading {path}")
    target[key] = value


def _apply_variant(strategy: StrategyDefinition, variant: StrategyVariant) -> StrategyDefinition:
    patches = {patch.step_id: patch for patch in variant.patches}
    steps: list[ShotStep] = []
    for step in strategy.sequence:
        patch = patches.get(step.identifier)
        if patch is None:
            steps.append(step)
            continue
        context_values = {**dict(step.context.values), **dict(patch.context_updates)}
        required_data = tuple(dict.fromkeys((*step.context.required_data, *patch.required_context_data)))
        steps.append(
            replace(
                step,
                context=StepContext(context_values, required_data),
                requirements=(*step.requirements, *patch.add_requirements),
                local_objectives=(*step.local_objectives, *patch.add_local_objectives),
            )
        )
    return replace(strategy, sequence=tuple(steps))
