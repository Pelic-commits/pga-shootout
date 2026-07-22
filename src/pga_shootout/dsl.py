"""Generic, registry-driven execution for declarative DSL pipelines."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .models import Effect, ExplainEntry, GameState
from .registry import MechanismExecution, MechanismExecutionError


class DslExecutionError(MechanismExecutionError):
    pass


@dataclass(frozen=True)
class PrimitiveResult:
    outputs: Mapping[str, Any]
    stats: dict[str, float]
    message: str
    applied: bool = True
    explain_inputs: Mapping[str, Any] | None = None
    explain_outputs: Mapping[str, Any] | None = None
    continuations: tuple["PrimitiveContinuation", ...] = ()


@dataclass(frozen=True)
class PrimitiveContinuation:
    label: str
    bindings: Mapping[str, Any]
    nodes: tuple[Mapping[str, Any], ...]


Primitive = Callable[[Mapping[str, Any], Mapping[str, Any], dict[str, float], GameState], PrimitiveResult]


class DslPrimitiveRegistry:
    def __init__(self) -> None:
        self._primitives: dict[str, Primitive] = {}

    def register(self, name: str, primitive: Primitive) -> None:
        if name in self._primitives:
            raise ValueError(f"DSL primitive already registered: {name}")
        self._primitives[name] = primitive

    def execute(
        self,
        name: str,
        inputs: Mapping[str, Any],
        parameters: Mapping[str, Any],
        stats: dict[str, float],
        state: GameState,
    ) -> PrimitiveResult:
        try:
            primitive = self._primitives[name]
        except KeyError as exc:
            raise DslExecutionError(f"Unknown DSL primitive: {name}") from exc
        return primitive(inputs, parameters, dict(stats), state)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._primitives)


def _club_id(value: Any) -> str:
    if not isinstance(value, str):
        raise DslExecutionError(f"Expected a club identifier, received {value!r}")
    return value


def _club_name(state: GameState, club_id: str) -> str:
    return state.bag.get(club_id).club.name


def _select_self(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    club_id = _club_id(inputs["source_club_id"])
    name = _club_name(state, club_id)
    return PrimitiveResult(
        {"club": club_id},
        stats,
        f"selected source club {name}",
        explain_inputs={"source_club_id": club_id},
        explain_outputs={"club": name},
    )


def _read_level_value(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], _state: GameState) -> PrimitiveResult:
    value = inputs["level_value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DslExecutionError(f"Expected a numeric level value, received {value!r}")
    numeric = float(value)
    return PrimitiveResult(
        {"value": numeric},
        stats,
        f"read value {numeric:+g} at level {inputs.get('level', 'unknown')}",
        explain_inputs={"level": inputs.get("level")},
        explain_outputs={"value": numeric},
    )


def _select_adjacent(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    origin = _club_id(inputs["origin"])
    distance = int(parameters.get("distance", 1))
    directions = tuple(parameters.get("directions", ("left", "right")))
    if distance < 1:
        raise DslExecutionError("Adjacent distance must be at least one")
    ordered = [entry.club.identifier for entry in state.bag.entries]
    try:
        index = ordered.index(origin)
    except ValueError as exc:
        raise DslExecutionError(f"Club {origin!r} is not in the ordered bag") from exc
    selected: list[str] = []
    selected_by_direction: dict[str, str | None] = {}
    offsets = {"left": -distance, "right": distance}
    for direction in directions:
        if direction not in offsets:
            raise DslExecutionError(f"Unknown adjacent direction: {direction}")
        candidate = index + offsets[direction]
        if 0 <= candidate < len(ordered):
            selected.append(ordered[candidate])
            selected_by_direction[direction] = ordered[candidate]
        else:
            selected_by_direction[direction] = None
    named_directions = {
        direction: _club_name(state, club_id) if club_id is not None else None
        for direction, club_id in selected_by_direction.items()
    }
    return PrimitiveResult(
        {"clubs": tuple(selected), **selected_by_direction},
        stats,
        f"selected adjacent clubs {list(value for value in named_directions.values() if value is not None)}",
        explain_inputs={"origin": _club_name(state, origin), "directions": list(directions), "distance": distance},
        explain_outputs=named_directions,
    )


def _match_brand(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    if parameters.get("operator", "equals") != "equals":
        raise DslExecutionError("MATCH_BRAND currently requires the equals operator")
    source = state.bag.get(_club_id(inputs["source"])).club
    matches, evaluations, directional = _match_club_attribute(inputs, state, lambda club_id: state.bag.get(club_id).club.brand, source.brand)
    return PrimitiveResult(
        {"clubs": matches},
        stats,
        f"matched {len(matches)} club(s) against brand {source.brand}",
        explain_inputs={"source": source.name, "brand": source.brand, "candidates": [item["club"] for item in evaluations]},
        explain_outputs=directional,
    )


def _match_club_attribute(
    inputs: Mapping[str, Any],
    state: GameState,
    read_attribute: Callable[[str], str],
    expected: str,
) -> tuple[tuple[str, ...], list[dict[str, Any]], dict[str, dict[str, Any] | None]]:
    clubs = tuple(_club_id(value) for value in inputs.get("clubs", ()))
    matches = tuple(club_id for club_id in clubs if read_attribute(club_id) == expected)
    evaluations = [
        {"club": _club_name(state, club_id), "matches": club_id in matches}
        for club_id in clubs
    ]
    directional = {
        direction: (
            None
            if inputs.get(direction) is None
            else {
                "club": _club_name(state, _club_id(inputs[direction])),
                "matches": _club_id(inputs[direction]) in matches,
            }
        )
        for direction in ("left", "right")
    }
    return matches, evaluations, directional


def _match_type(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    if parameters.get("operator", "equals") != "equals":
        raise DslExecutionError("MATCH_TYPE currently requires the equals operator")
    expected = str(parameters["expected"])
    matches, evaluations, directional = _match_club_attribute(
        inputs,
        state,
        lambda club_id: state.bag.get(club_id).club.club_type,
        expected,
    )
    return PrimitiveResult(
        {"clubs": matches},
        stats,
        f"matched {len(matches)} club(s) against type {expected}",
        explain_inputs={"type": expected, "candidates": [item["club"] for item in evaluations]},
        explain_outputs=directional,
    )


def _count(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    items = inputs.get("items", ())
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise DslExecutionError("COUNT requires a sequence")
    count = len(items)
    displayed_items = []
    for item in items:
        if isinstance(item, str):
            try:
                displayed_items.append(_club_name(state, item))
                continue
            except KeyError:
                pass
        displayed_items.append(item)
    return PrimitiveResult(
        {"value": count},
        stats,
        f"counted {count} item(s)",
        explain_inputs={"items": displayed_items},
        explain_outputs={"count": count},
    )


def _scale(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], _state: GameState) -> PrimitiveResult:
    amount = float(inputs["amount"])
    factor = float(inputs["factor"])
    value = amount * factor
    return PrimitiveResult(
        {"value": value},
        stats,
        f"{amount:g} × {factor:g} = {value:g}",
        explain_inputs={"amount": amount, "factor": factor},
        explain_outputs={"value": value},
    )


def _for_each(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    items = inputs.get("items", ())
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise DslExecutionError("FOR_EACH requires a sequence")
    program = parameters.get("program")
    nodes = program.get("nodes") if isinstance(program, Mapping) else None
    if not isinstance(nodes, list) or not all(isinstance(node, Mapping) for node in nodes):
        raise DslExecutionError("FOR_EACH requires a program containing a nodes list")
    binding = str(parameters.get("binding", "item"))
    if not binding:
        raise DslExecutionError("FOR_EACH binding cannot be empty")
    displayed_items = []
    for item in items:
        if isinstance(item, str):
            try:
                displayed_items.append(_club_name(state, item))
                continue
            except KeyError:
                pass
        displayed_items.append(item)
    continuations = tuple(
        PrimitiveContinuation(str(index), {binding: item}, tuple(nodes))
        for index, item in enumerate(items)
    )
    return PrimitiveResult(
        {"count": len(items)},
        stats,
        f"executing sub-pipeline for {len(items)} item(s)",
        explain_inputs={"items": displayed_items, "binding": binding},
        explain_outputs={"iterations": len(items)},
        continuations=continuations,
    )


def _add_stat(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    stat = str(parameters["stat"])
    if stat not in stats:
        raise DslExecutionError(f"Unknown stat: {stat}")
    if inputs.get("target") is None:
        return PrimitiveResult(
            {},
            stats,
            "no target selected; stat unchanged",
            applied=False,
            explain_inputs={"target": None, "stat": stat, "delta": float(inputs["delta"])},
            explain_outputs={"value": stats[stat]},
        )
    target = _club_id(inputs["target"])
    if target != state.current_club_id:
        return PrimitiveResult(
            {},
            stats,
            f"target {_club_name(state, target)} is not the current club; stat unchanged",
            applied=False,
            explain_inputs={"target": _club_name(state, target), "stat": stat, "delta": float(inputs["delta"])},
            explain_outputs={"value": stats[stat]},
        )
    delta = float(inputs["delta"])
    before = stats[stat]
    stats[stat] += delta
    return PrimitiveResult(
        {"value": stats[stat]},
        stats,
        f"{stat.upper()} += {delta:g}",
        explain_inputs={"target": _club_name(state, target), "stat": stat, "delta": delta},
        explain_outputs={"before": before, "after": stats[stat]},
    )


def default_dsl_registry() -> DslPrimitiveRegistry:
    registry = DslPrimitiveRegistry()
    registry.register("SELECT_SELF", _select_self)
    registry.register("READ_LEVEL_VALUE", _read_level_value)
    registry.register("SELECT_ADJACENT", _select_adjacent)
    registry.register("MATCH_BRAND", _match_brand)
    registry.register("MATCH_TYPE", _match_type)
    registry.register("COUNT", _count)
    registry.register("SCALE", _scale)
    registry.register("FOR_EACH", _for_each)
    registry.register("ADD_STAT", _add_stat)
    return registry


def _resolve(
    value: Any,
    outputs: Mapping[str, Mapping[str, Any]],
    effect: Effect,
    bindings: Mapping[str, Any] | None = None,
) -> Any:
    if isinstance(value, Mapping) and set(value) == {"from"}:
        reference = str(value["from"])
        if reference.startswith("effect."):
            key = reference.removeprefix("effect.")
            try:
                return effect.parameters[key]
            except KeyError as exc:
                raise DslExecutionError(f"Missing effect input: {key}") from exc
        if reference.startswith("iteration."):
            key = reference.removeprefix("iteration.")
            if bindings is None or key not in bindings:
                return value
            return bindings[key]
        try:
            node_id, output_name = reference.split(".", 1)
            return outputs[node_id][output_name]
        except (KeyError, ValueError) as exc:
            raise DslExecutionError(f"Unknown DSL output reference: {reference}") from exc
    if isinstance(value, list):
        return [_resolve(item, outputs, effect, bindings) for item in value]
    if isinstance(value, Mapping):
        return {key: _resolve(item, outputs, effect, bindings) for key, item in value.items()}
    return value


def _execute_nodes(
    nodes: Sequence[Mapping[str, Any]],
    stats: dict[str, float],
    effect: Effect,
    state: GameState,
    registry: DslPrimitiveRegistry,
    *,
    outputs: Mapping[str, Mapping[str, Any]] | None = None,
    bindings: Mapping[str, Any] | None = None,
    scope: str = "",
) -> tuple[dict[str, float], list[ExplainEntry], dict[str, Mapping[str, Any]]]:
    resolved_outputs = dict(outputs or {})
    journal: list[ExplainEntry] = []
    current = stats
    for node in nodes:
        if not isinstance(node, Mapping):
            raise DslExecutionError("Every DSL node must be an object")
        node_id = str(node["id"])
        operation = str(node["operation"])
        if node_id in resolved_outputs:
            raise DslExecutionError(f"Duplicate DSL node id: {node_id}")
        inputs = _resolve(node.get("inputs", {}), resolved_outputs, effect, bindings)
        parameters = _resolve(node.get("parameters", {}), resolved_outputs, effect, bindings)
        before = dict(current)
        result = registry.execute(operation, inputs, parameters, current, state)
        current = result.stats
        resolved_outputs[node_id] = dict(result.outputs)
        scoped_node_id = f"{scope}.{node_id}" if scope else node_id
        journal.append(
            ExplainEntry(
                source=effect.source,
                mechanism=operation,
                condition=f"DSL node {scoped_node_id}",
                applied=result.applied,
                before=before,
                modification={name: current[name] - before[name] for name in before},
                after=dict(current),
                message=result.message,
                inputs=dict(result.explain_inputs if result.explain_inputs is not None else inputs),
                outputs=dict(result.explain_outputs if result.explain_outputs is not None else result.outputs),
            )
        )
        for continuation in result.continuations:
            current, nested_journal, _ = _execute_nodes(
                continuation.nodes,
                current,
                effect,
                state,
                registry,
                outputs=resolved_outputs,
                bindings=continuation.bindings,
                scope=f"{scoped_node_id}[{continuation.label}]",
            )
            journal.extend(nested_journal)
    return current, journal, resolved_outputs


def execute_dsl_pipeline(stats: dict[str, float], effect: Effect, state: GameState) -> MechanismExecution:
    program = effect.parameters.get("program")
    nodes = program.get("nodes") if isinstance(program, Mapping) else None
    if not isinstance(nodes, list):
        raise DslExecutionError("dsl_pipeline requires a program containing a nodes list")

    current, journal, _ = _execute_nodes(nodes, dict(stats), effect, state, default_dsl_registry())
    return MechanismExecution(current, tuple(journal))
