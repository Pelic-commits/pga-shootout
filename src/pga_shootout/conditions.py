"""Condition evaluation, kept separate from effect execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Condition, GameState

ConditionEvaluator = Callable[[GameState, dict[str, float], dict[str, Any]], bool]


class UnknownConditionError(LookupError):
    pass


class MissingConditionContextError(UnknownConditionError):
    pass


def _state_equals(state: GameState, _stats: dict[str, float], params: dict[str, Any]) -> bool:
    field = str(params["field"])
    actual = getattr(state, field, None)
    if actual is None and bool(params.get("required", False)):
        raise MissingConditionContextError(f"Missing required scenario context: {field}")
    return actual == params.get("value")


def _state_membership(
    state: GameState,
    _stats: dict[str, float],
    params: dict[str, Any],
    *,
    negate: bool,
) -> bool:
    field = str(params["field"])
    actual = getattr(state, field, None)
    if actual is None and bool(params.get("required", False)):
        raise MissingConditionContextError(f"Missing required scenario context: {field}")
    values = params.get("values", ())
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise UnknownConditionError(f"Condition values for {field} must be a collection")
    matched = actual in values
    return not matched if negate else matched


def _bag_position_equals(state: GameState, _stats: dict[str, float], params: dict[str, Any]) -> bool:
    source = str(params["source_club_id"])
    expected = str(params["position"])
    ordered = tuple(entry.club.identifier for entry in state.bag.entries)
    if source not in ordered:
        return False
    if expected == "leftmost":
        return ordered[0] == source
    if expected == "rightmost":
        return ordered[-1] == source
    raise UnknownConditionError(f"Unknown bag position: {expected}")


class ConditionRegistry:
    def __init__(self) -> None:
        self._evaluators: dict[str, ConditionEvaluator] = {}

    def register(self, kind: str, evaluator: ConditionEvaluator) -> None:
        if kind in self._evaluators:
            raise ValueError(f"Condition already registered: {kind}")
        self._evaluators[kind] = evaluator

    def evaluate(self, condition: Condition, state: GameState, stats: dict[str, float]) -> bool:
        try:
            evaluator = self._evaluators[condition.kind]
        except KeyError as exc:
            raise UnknownConditionError(condition.kind) from exc
        return evaluator(state, stats, dict(condition.parameters))


def default_condition_registry() -> ConditionRegistry:
    registry = ConditionRegistry()
    registry.register("always", lambda _state, _stats, _params: True)
    registry.register("state_equals", _state_equals)
    registry.register("state_in", lambda state, stats, params: _state_membership(state, stats, params, negate=False))
    registry.register("state_not_in", lambda state, stats, params: _state_membership(state, stats, params, negate=True))
    registry.register("bag_position_equals", _bag_position_equals)
    registry.register(
        "current_club_attribute_equals",
        lambda state, _stats, params: getattr(state.current_entry.club, str(params["field"]), None)
        == params.get("value"),
    )
    registry.register(
        "current_club_attribute_in",
        lambda state, _stats, params: getattr(state.current_entry.club, str(params["field"]), None)
        in tuple(params.get("values", ())),
    )
    return registry
