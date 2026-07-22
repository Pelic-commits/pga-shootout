"""Lossless JSON loading plus explicit mapping helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DataLoadError(ValueError):
    pass


def load_raw_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataLoadError(f"Cannot load JSON from {source}: {exc}") from exc


def summarize_raw_json(data: Any) -> dict[str, Any]:
    """Describe raw shape without assuming the not-yet-mapped official schema."""
    if isinstance(data, dict):
        return {"root_type": "object", "keys": sorted(data), "item_count": len(data)}
    if isinstance(data, list):
        return {"root_type": "array", "item_count": len(data)}
    return {"root_type": type(data).__name__, "item_count": None}
