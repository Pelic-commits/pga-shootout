"""Extensible mechanism registry for declarative effects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import DelayedEffect, Effect, ExplainEntry, GameState


@dataclass(frozen=True)
class MechanismExecution:
    stats: dict[str, float]
    explain: tuple[ExplainEntry, ...] = ()
    scheduled_effects: tuple[DelayedEffect, ...] = ()


Mechanism = Callable[[dict[str, float], Effect, GameState], dict[str, float] | MechanismExecution]


class UnknownMechanismError(LookupError):
    pass


class MechanismExecutionError(ValueError):
    pass


class MechanismRegistry:
    def __init__(self) -> None:
        self._mechanisms: dict[str, Mechanism] = {}

    def register(self, name: str, mechanism: Mechanism) -> None:
        if name in self._mechanisms:
            raise ValueError(f"Mechanism already registered: {name}")
        self._mechanisms[name] = mechanism

    def execute(self, effect: Effect, stats: dict[str, float], state: GameState) -> MechanismExecution:
        try:
            mechanism = self._mechanisms[effect.mechanism]
        except KeyError as exc:
            raise UnknownMechanismError(effect.mechanism) from exc
        result = mechanism(dict(stats), effect, state)
        return result if isinstance(result, MechanismExecution) else MechanismExecution(result)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._mechanisms)


def _add_stat(stats: dict[str, float], effect: Effect, state: GameState) -> dict[str, float]:
    stat = str(effect.parameters["stat"])
    if stat not in stats:
        raise ValueError(f"Unknown stat: {stat}")
    if stat in state.current_entry.club.available_stats_at(state.current_entry.level):
        stats[stat] += float(effect.parameters["amount"])
    return stats


def _add_all_stats(stats: dict[str, float], effect: Effect, state: GameState) -> dict[str, float]:
    amount = float(effect.parameters["amount"])
    available = state.current_entry.club.available_stats_at(state.current_entry.level)
    return {name: value + amount if name in available else value for name, value in stats.items()}


def default_mechanism_registry() -> MechanismRegistry:
    from .dsl import execute_dsl_pipeline

    registry = MechanismRegistry()
    registry.register("add_stat", _add_stat)
    registry.register("add_all_stats", _add_all_stats)
    registry.register("dsl_pipeline", execute_dsl_pipeline)
    return registry
