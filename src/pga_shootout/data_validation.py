"""Structural validation for immutable official and normalized data layers."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .loader import load_raw_json


class DataValidationError(ValueError):
    """Raised when official data layers are inconsistent."""


@dataclass(frozen=True)
class OfficialDataReport:
    raw_sha256: str
    normalized_sha256: str
    clubs: int
    brands: int
    ability_occurrences: int
    unique_club_ids: int
    unique_occurrence_ids: int
    converted_ability_values: int
    schema_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _club_list(normalized: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    clubs = normalized.get("clubs")
    if isinstance(clubs, dict):
        club_order = normalized.get("club_order")
        if list(clubs) != club_order:
            raise DataValidationError("clubs keys do not match club_order")
        return list(clubs.values())
    if isinstance(clubs, list):
        return clubs
    raise DataValidationError("normalized clubs must be an object or array")


def validate_official_data(
    raw_path: str | Path,
    normalized_path: str | Path,
) -> OfficialDataReport:
    raw = load_raw_json(raw_path)
    normalized = load_raw_json(normalized_path)
    if not isinstance(raw, dict) or not isinstance(normalized, dict):
        raise DataValidationError("official data roots must be JSON objects")

    raw_clubs = raw.get("clubs")
    raw_brands = raw.get("brands")
    if not isinstance(raw_clubs, list) or not isinstance(raw_brands, list):
        raise DataValidationError("raw clubs and brands must be arrays")

    collector = raw.get("collector", {})
    if collector.get("captured_clubs") != len(raw_clubs):
        raise DataValidationError("raw captured_clubs does not match clubs length")
    if collector.get("status_counts", {}).get("captured") != len(raw_clubs):
        raise DataValidationError("raw captured status count does not match clubs length")

    raw_hash = sha256_file(raw_path)
    declared_hash = str(normalized.get("source", {}).get("source_sha256", "")).lower()
    if declared_hash != raw_hash:
        raise DataValidationError("normalized source_sha256 does not match raw file")

    clubs = _club_list(normalized)
    club_ids = [str(club.get("id")) for club in clubs]
    occurrence_ids = [
        str(ability.get("occurrence_id"))
        for club in clubs
        for ability in club.get("abilities", [])
    ]
    converted_values = sum(
        value is not None
        for club in clubs
        for ability in club.get("abilities", [])
        for value in ability.get("values_by_level", {}).values()
    )
    brands = {str(club.get("brand", {}).get("id")) for club in clubs}

    if len(clubs) != len(raw_clubs):
        raise DataValidationError("normalized club count does not match raw club count")
    if len(brands) != len(raw_brands):
        raise DataValidationError("normalized brand count does not match raw brand count")
    if len(set(club_ids)) != len(club_ids):
        raise DataValidationError("normalized club identifiers are not unique")
    if len(set(occurrence_ids)) != len(occurrence_ids):
        raise DataValidationError("ability occurrence identifiers are not unique")

    return OfficialDataReport(
        raw_sha256=raw_hash,
        normalized_sha256=sha256_file(normalized_path),
        clubs=len(clubs),
        brands=len(brands),
        ability_occurrences=len(occurrence_ids),
        unique_club_ids=len(set(club_ids)),
        unique_occurrence_ids=len(set(occurrence_ids)),
        converted_ability_values=converted_values,
        schema_version=str(normalized.get("schema_version", "")),
    )
