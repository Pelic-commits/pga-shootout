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


def _select_self(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    club_id = _club_id(inputs["source_club_id"])
    state.bag.get(club_id)
    return PrimitiveResult({"club": club_id}, stats, f"selected source club {club_id}")


def _read_level_value(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], _state: GameState) -> PrimitiveResult:
    value = inputs["level_value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DslExecutionError(f"Expected a numeric level value, received {value!r}")
    numeric = float(value)
    return PrimitiveResult({"value": numeric}, stats, f"read level value {numeric:g}")


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
    offsets = {"left": -distance, "right": distance}
    for direction in directions:
        if direction not in offsets:
            raise DslExecutionError(f"Unknown adjacent direction: {direction}")
        candidate = index + offsets[direction]
        if 0 <= candidate < len(ordered):
            selected.append(ordered[candidate])
    return PrimitiveResult({"clubs": tuple(selected)}, stats, f"selected adjacent clubs {selected}")


def _match_brand(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    if parameters.get("operator", "equals") != "equals":
        raise DslExecutionError("MATCH_BRAND currently requires the equals operator")
    source = state.bag.get(_club_id(inputs["source"])).club
    clubs = tuple(_club_id(value) for value in inputs.get("clubs", ()))
    matches = tuple(club_id for club_id in clubs if state.bag.get(club_id).club.brand == source.brand)
    return PrimitiveResult({"clubs": matches}, stats, f"matched brand {source.brand}: {list(matches)}")


def _count(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], _state: GameState) -> PrimitiveResult:
    items = inputs.get("items", ())
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise DslExecutionError("COUNT requires a sequence")
    count = len(items)
    return PrimitiveResult({"value": count}, stats, f"counted {count} item(s)")


def _scale(inputs: Mapping[str, Any], _parameters: Mapping[str, Any], stats: dict[str, float], _state: GameState) -> PrimitiveResult:
    amount = float(inputs["amount"])
    factor = float(inputs["factor"])
    value = amount * factor
    return PrimitiveResult({"value": value}, stats, f"scaled {amount:g} by {factor:g} = {value:g}")


def _add_stat(inputs: Mapping[str, Any], parameters: Mapping[str, Any], stats: dict[str, float], state: GameState) -> PrimitiveResult:
    target = _club_id(inputs["target"])
    stat = str(parameters["stat"])
    if stat not in stats:
        raise DslExecutionError(f"Unknown stat: {stat}")
    if target != state.current_club_id:
        return PrimitiveResult({}, stats, f"target {target} is not the current club; stat unchanged", applied=False)
    delta = float(inputs["delta"])
    stats[stat] += delta
    return PrimitiveResult({"value": stats[stat]}, stats, f"added {delta:g} to {stat} on {target}")


def default_dsl_registry() -> DslPrimitiveRegistry:
    registry = DslPrimitiveRegistry()
    registry.register("SELECT_SELF", _select_self)
    registry.register("READ_LEVEL_VALUE", _read_level_value)
    registry.register("SELECT_ADJACENT", _select_adjacent)
    registry.register("MATCH_BRAND", _match_brand)
    registry.register("COUNT", _count)
    registry.register("SCALE", _scale)
    registry.register("ADD_STAT", _add_stat)
    return registry


def _resolve(value: Any, outputs: Mapping[str, Mapping[str, Any]], effect: Effect) -> Any:
    if isinstance(value, Mapping) and set(value) == {"from"}:
        reference = str(value["from"])
        if reference.startswith("effect."):
            key = reference.removeprefix("effect.")
            try:
                return effect.parameters[key]
            except KeyError as exc:
                raise DslExecutionError(f"Missing effect input: {key}") from exc
        try:
            node_id, output_name = reference.split(".", 1)
            return outputs[node_id][output_name]
        except (KeyError, ValueError) as exc:
            raise DslExecutionError(f"Unknown DSL output reference: {reference}") from exc
    if isinstance(value, list):
        return [_resolve(item, outputs, effect) for item in value]
    if isinstance(value, Mapping):
        return {key: _resolve(item, outputs, effect) for key, item in value.items()}
    return value


def execute_dsl_pipeline(stats: dict[str, float], effect: Effect, state: GameState) -> MechanismExecution:
    program = effect.parameters.get("program")
    nodes = program.get("nodes") if isinstance(program, Mapping) else None
    if not isinstance(nodes, list):
        raise DslExecutionError("dsl_pipeline requires a program containing a nodes list")

    registry = default_dsl_registry()
    outputs: dict[str, Mapping[str, Any]] = {}
    journal: list[ExplainEntry] = []
    current = dict(stats)
    for node in nodes:
        if not isinstance(node, Mapping):
            raise DslExecutionError("Every DSL node must be an object")
        node_id = str(node["id"])
        operation = str(node["operation"])
        if node_id in outputs:
            raise DslExecutionError(f"Duplicate DSL node id: {node_id}")
        inputs = _resolve(node.get("inputs", {}), outputs, effect)
        parameters = _resolve(node.get("parameters", {}), outputs, effect)
        before = dict(current)
        result = registry.execute(operation, inputs, parameters, current, state)
        current = result.stats
        outputs[node_id] = dict(result.outputs)
        journal.append(
            ExplainEntry(
                source=effect.source,
                mechanism=operation,
                condition=f"DSL node {node_id}",
                applied=result.applied,
                before=before,
                modification={name: current[name] - before[name] for name in before},
                after=dict(current),
                message=result.message,
            )
        )
    return MechanismExecution(current, tuple(journal))
