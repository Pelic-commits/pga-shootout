"""Deterministic, lossless structural normalization of official abilities.

No gameplay mechanic is inferred here. Grouping relies only on the exact
``label_id`` already present in ``clubs_official.json``.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .loader import load_raw_json


class NormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizationSummary:
    occurrences: int
    unique_labels: int
    groups: int
    ambiguities: int
    converted_values: int


OUTPUT_FILENAMES = (
    "ability_occurrences.json",
    "ability_labels.json",
    "mechanics_catalog.json",
    "semantic_map.json",
    "normalization_report.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def normalize_catalog(source_path: str | Path, output_dir: str | Path) -> NormalizationSummary:
    source = Path(source_path)
    destination = Path(output_dir)
    existing_semantic_entries: dict[str, Any] = {}
    existing_semantic_patterns: dict[str, Any] = {}
    semantic_path = destination / "semantic_map.json"
    if semantic_path.exists():
        existing_semantic = load_raw_json(semantic_path)
        if isinstance(existing_semantic, dict) and isinstance(existing_semantic.get("entries"), dict):
            existing_semantic_entries = existing_semantic["entries"]
            if isinstance(existing_semantic.get("patterns"), dict):
                existing_semantic_patterns = existing_semantic["patterns"]
    catalog = load_raw_json(source)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("clubs"), dict):
        raise NormalizationError("clubs_official.json must contain clubs keyed by stable identifier")

    clubs: dict[str, dict[str, Any]] = catalog["clubs"]
    club_order = catalog.get("club_order")
    if club_order != list(clubs):
        raise NormalizationError("club_order must exactly match the ordered club keys")

    occurrence_records: dict[str, dict[str, Any]] = {}
    occurrence_order: list[str] = []
    labels: dict[str, dict[str, Any]] = {}
    missing_label_ids: list[str] = []
    prefix_mismatches: list[str] = []
    converted_values = 0

    for club_index, (club_id, club) in enumerate(clubs.items()):
        for ability_index, ability in enumerate(club.get("abilities", [])):
            occurrence_id = str(ability.get("occurrence_id", ""))
            label_id = str(ability.get("label_id", ""))
            if not occurrence_id:
                raise NormalizationError(f"club {club_id} contains an ability without occurrence_id")
            if occurrence_id in occurrence_records:
                raise NormalizationError(f"duplicate occurrence_id: {occurrence_id}")
            if not label_id:
                missing_label_ids.append(occurrence_id)
            if not occurrence_id.startswith(f"{club_id}__"):
                prefix_mismatches.append(occurrence_id)

            official_payload = copy.deepcopy(ability)
            converted_values += sum(value is not None for value in ability.get("values_by_level", {}).values())
            occurrence_order.append(occurrence_id)
            occurrence_records[occurrence_id] = {
                "occurrence_id": occurrence_id,
                "label_id": label_id,
                "club": {
                    "id": club_id,
                    "name": club.get("name"),
                    "brand": copy.deepcopy(club.get("brand")),
                    "club_type": copy.deepcopy(club.get("club_type")),
                    "rarity": copy.deepcopy(club.get("rarity")),
                },
                "source_position": {"club_index": club_index, "ability_index": ability_index},
                "official_payload": official_payload,
                "interpretation_status": "uninterpreted",
            }
            label = labels.setdefault(
                label_id,
                {
                    "label_id": label_id,
                    "grouping_basis": "exact_source_label_id",
                    "occurrence_ids": [],
                    "club_ids": [],
                    "official_text_available": False,
                },
            )
            label["occurrence_ids"].append(occurrence_id)
            if club_id not in label["club_ids"]:
                label["club_ids"].append(club_id)

    for label in labels.values():
        label["occurrence_count"] = len(label["occurrence_ids"])
        label["club_count"] = len(label["club_ids"])

    groups: dict[str, dict[str, Any]] = {}
    semantic_entries: dict[str, dict[str, Any]] = {}
    for label_id, label in labels.items():
        group_id = f"label:{label_id}"
        groups[group_id] = {
            "group_id": group_id,
            "grouping_basis": "exact_source_label_id",
            "source_label_id": label_id,
            "occurrence_ids": list(label["occurrence_ids"]),
            "club_ids": list(label["club_ids"]),
            "occurrence_count": label["occurrence_count"],
            "club_count": label["club_count"],
            "mechanic_id": None,
            "interpretation_status": "uninterpreted",
        }
        placeholder = {
            "group_id": group_id,
            "mechanic_id": None,
            "complexity": None,
            "dependencies": None,
            "priority": None,
            "interpretation_status": "uninterpreted",
            "validation_status": "not_started",
            "notes": [],
        }
        existing = existing_semantic_entries.get(group_id)
        if isinstance(existing, dict):
            placeholder.update(copy.deepcopy(existing))
            placeholder["group_id"] = group_id
        semantic_entries[group_id] = placeholder

    source_info = {
        "filename": source.name,
        "sha256": _sha256(source),
        "schema_version": catalog.get("schema_version"),
    }
    ambiguity_records: list[dict[str, Any]] = []
    limitations = [
        {
            "code": "official_ability_text_unavailable",
            "affected_occurrences": len(occurrence_records),
            "detail": "Source abilities contain label_id and values_by_level, but no official title, description or icon.",
        }
    ]
    shared_labels = Counter(record["label_id"] for record in occurrence_records.values())

    destination.mkdir(parents=True, exist_ok=True)
    _write_json(
        destination / "ability_occurrences.json",
        {
            "schema_version": "1.0.0",
            "layer": "structural_ability_occurrences",
            "source": source_info,
            "occurrence_order": occurrence_order,
            "occurrences": occurrence_records,
        },
    )
    _write_json(
        destination / "ability_labels.json",
        {
            "schema_version": "1.0.0",
            "layer": "exact_label_groups",
            "source": source_info,
            "label_order": list(labels),
            "labels": labels,
        },
    )
    _write_json(
        destination / "mechanics_catalog.json",
        {
            "schema_version": "1.0.0",
            "layer": "uninterpreted_capability_groups",
            "source": source_info,
            "warning": "Group names are structural labels, not validated gameplay mechanics.",
            "group_order": list(groups),
            "groups": groups,
        },
    )
    _write_json(
        destination / "semantic_map.json",
        {
            "schema_version": "1.0.0",
            "layer": "semantic_interpretation_placeholders",
            "source": source_info,
            "patterns": existing_semantic_patterns,
            "entries": semantic_entries,
        },
    )
    report = {
        "schema_version": "1.0.0",
        "source": source_info,
        "counts": {
            "clubs": len(clubs),
            "ability_occurrences": len(occurrence_records),
            "unique_label_ids": len(labels),
            "structural_groups": len(groups),
            "converted_level_values": converted_values,
            "labels_shared_by_multiple_occurrences": sum(count > 1 for count in shared_labels.values()),
        },
        "integrity": {
            "source_ability_count_matches": len(occurrence_records)
            == sum(len(club.get("abilities", [])) for club in clubs.values()),
            "unique_occurrence_ids": len(occurrence_records) == len(occurrence_order),
            "missing_label_ids": missing_label_ids,
            "occurrence_club_prefix_mismatches": prefix_mismatches,
            "all_groups_uninterpreted": all(group["mechanic_id"] is None for group in groups.values()),
        },
        "ambiguities": ambiguity_records,
        "source_limitations": limitations,
    }
    _write_json(destination / "normalization_report.json", report)
    return NormalizationSummary(
        occurrences=len(occurrence_records),
        unique_labels=len(labels),
        groups=len(groups),
        ambiguities=len(ambiguity_records),
        converted_values=converted_values,
    )
