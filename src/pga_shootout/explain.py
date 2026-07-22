"""Explain journal helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable

from .models import Effect, ExplainEntry


def explain_entry(
    effect: Effect,
    *,
    applied: bool,
    before: dict[str, float],
    after: dict[str, float],
    message: str = "",
) -> ExplainEntry:
    modification = {
        name: after.get(name, 0.0) - before.get(name, 0.0)
        for name in before.keys() | after.keys()
    }
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


def render_explain_entries(entries: Iterable[ExplainEntry]) -> str:
    """Render a stable, human-readable Explain trace suitable for golden tests."""
    blocks = []
    for entry in entries:
        lines = [entry.mechanism]
        if entry.inputs:
            lines.append(f"Inputs: {json.dumps(entry.inputs, ensure_ascii=False, sort_keys=True)}")
        if entry.outputs:
            lines.append(f"Outputs: {json.dumps(entry.outputs, ensure_ascii=False, sort_keys=True)}")
        lines.extend(
            [
                f"Applied: {'yes' if entry.applied else 'no'}",
                f"Before: {json.dumps(entry.before, sort_keys=True)}",
                f"Change: {json.dumps(entry.modification, sort_keys=True)}",
                f"After: {json.dumps(entry.after, sort_keys=True)}",
            ]
        )
        if entry.message:
            lines.append(f"Detail: {entry.message}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
