"""Condition evaluation, kept separate from effect execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Condition, GameState

ConditionEvaluator = Callable[[GameState, dict[str, float], dict[str, Any]], bool]


class UnknownConditionError(LookupError):
    pass


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
    registry.register(
        "state_equals",
        lambda state, _stats, params: getattr(state, str(params["field"]), None) == params.get("value"),
    )
    registry.register(
        "current_club_attribute_equals",
        lambda state, _stats, params: getattr(state.current_entry.club, str(params["field"]), None)
        == params.get("value"),
    )
    return registry
