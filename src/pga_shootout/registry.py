"""Extensible mechanism registry for declarative effects."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Effect, GameState

Mechanism = Callable[[dict[str, float], Effect, GameState], dict[str, float]]


class UnknownMechanismError(LookupError):
    pass


class MechanismRegistry:
    def __init__(self) -> None:
        self._mechanisms: dict[str, Mechanism] = {}

    def register(self, name: str, mechanism: Mechanism) -> None:
        if name in self._mechanisms:
            raise ValueError(f"Mechanism already registered: {name}")
        self._mechanisms[name] = mechanism

    def execute(self, effect: Effect, stats: dict[str, float], state: GameState) -> dict[str, float]:
        try:
            mechanism = self._mechanisms[effect.mechanism]
        except KeyError as exc:
            raise UnknownMechanismError(effect.mechanism) from exc
        return mechanism(dict(stats), effect, state)


def _add_stat(stats: dict[str, float], effect: Effect, _state: GameState) -> dict[str, float]:
    stat = str(effect.parameters["stat"])
    if stat not in stats:
        raise ValueError(f"Unknown stat: {stat}")
    stats[stat] += float(effect.parameters["amount"])
    return stats


def _add_all_stats(stats: dict[str, float], effect: Effect, _state: GameState) -> dict[str, float]:
    amount = float(effect.parameters["amount"])
    return {name: value + amount for name, value in stats.items()}


def default_mechanism_registry() -> MechanismRegistry:
    registry = MechanismRegistry()
    registry.register("add_stat", _add_stat)
    registry.register("add_all_stats", _add_all_stats)
    return registry
