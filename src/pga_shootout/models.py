"""Domain objects. They contain data, never club-specific execution logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class EvaluationMode(StrEnum):
    STRICT = "strict"
    PARTIAL = "partial"


@dataclass(frozen=True)
class Stats:
    power: float = 0.0
    control: float = 0.0
    spin: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {"power": self.power, "control": self.control, "spin": self.spin}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Stats":
        return cls(
            **{
                name: 0.0 if value.get(name) is None else float(value.get(name, 0.0))
                for name in ("power", "control", "spin")
            }
        )


@dataclass(frozen=True)
class Condition:
    kind: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class Effect:
    mechanism: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    condition: Condition = field(default_factory=lambda: Condition("always"))
    source: str = "unknown"


@dataclass(frozen=True)
class DelayedEffect:
    """One planned effect waiting for a compatible future evaluation."""

    identifier: str
    source: str
    source_club_id: str
    trigger: Condition
    effect: Effect
    consume_on_trigger: bool = True


@dataclass(frozen=True)
class Ability:
    identifier: str
    text: str = ""
    effects: tuple[Effect, ...] = ()


@dataclass(frozen=True)
class Club:
    identifier: str
    name: str
    brand: str
    club_type: str
    stats_by_level: Mapping[int, Stats]
    abilities: tuple[Ability, ...] = ()
    rarity: str | None = None
    available_stats_by_level: Mapping[int | str, frozenset[str]] = field(default_factory=dict)

    def stats_at(self, level: int | str) -> Stats:
        try:
            return self.stats_by_level[level]
        except KeyError as exc:
            raise ValueError(f"No stats for club {self.identifier!r} at level {level}") from exc

    def available_stats_at(self, level: int | str) -> frozenset[str]:
        return self.available_stats_by_level.get(level, frozenset(("power", "control", "spin")))


@dataclass(frozen=True)
class BagEntry:
    club: Club
    level: int | str | None


@dataclass(frozen=True)
class Bag:
    entries: tuple[BagEntry, ...] = ()

    def get(self, club_id: str) -> BagEntry:
        for entry in self.entries:
            if entry.club.identifier == club_id:
                return entry
        raise KeyError(club_id)


@dataclass
class GameState:
    bag: Bag
    current_club_id: str
    previous_club_id: str | None = None
    terrain: str | None = None
    wind: float | None = None
    distance: float | None = None
    shot_history: list[Mapping[str, Any]] = field(default_factory=list)
    active_bonuses: list[Effect] = field(default_factory=list)
    pending_effects: list[DelayedEffect] = field(default_factory=list)

    @property
    def current_entry(self) -> BagEntry:
        return self.bag.get(self.current_club_id)


@dataclass(frozen=True)
class ExplainEntry:
    source: str
    mechanism: str
    condition: str
    applied: bool
    before: Mapping[str, float]
    modification: Mapping[str, float]
    after: Mapping[str, float]
    message: str = ""
    inputs: Mapping[str, Any] = field(default_factory=dict)
    outputs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationResult:
    base_stats: Stats
    final_stats: Stats
    explain: tuple[ExplainEntry, ...]
    modifiers: Mapping[str, float] = field(default_factory=dict)
    unresolved: tuple[str, ...] = ()
    complete: bool = True
    scheduled_effects: tuple[DelayedEffect, ...] = ()
    pending_effects: tuple[DelayedEffect, ...] = ()
    consumed_effect_ids: tuple[str, ...] = ()
