"""Explain journal helpers."""

from __future__ import annotations

from .models import Effect, ExplainEntry


def explain_entry(
    effect: Effect,
    *,
    applied: bool,
    before: dict[str, float],
    after: dict[str, float],
    message: str = "",
) -> ExplainEntry:
    modification = {name: after[name] - before[name] for name in before}
    condition = effect.condition.description or effect.condition.kind
    return ExplainEntry(
        source=effect.source,
        mechanism=effect.mechanism,
        condition=condition,
        applied=applied,
        before=dict(before),
        modification=modification,
        after=dict(after),
        message=message,
    )
