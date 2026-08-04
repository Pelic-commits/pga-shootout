"""Versioned SQLite storage for official catalog data and reproducible diffs."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .loader import load_raw_json


@dataclass(frozen=True)
class CatalogVersionInfo:
    version_id: str
    source_url: str
    source_last_updated: str
    captured_at: str
    verified_at: str | None
    catalog_sha256: str
    raw_sha256: str
    club_count: int
    is_current: bool
    confidence: str


@dataclass(frozen=True)
class CatalogDiff:
    old_version: str
    new_version: str
    added_clubs: tuple[str, ...]
    missing_clubs: tuple[str, ...]
    renamed_clubs: tuple[tuple[str, str, str], ...]
    metadata_changes: tuple[dict[str, Any], ...]
    stat_changes: tuple[dict[str, Any], ...]
    added_abilities: tuple[str, ...]
    removed_abilities: tuple[str, ...]
    ability_text_changes: tuple[dict[str, Any], ...]
    ability_value_changes: tuple[dict[str, Any], ...]
    data_now_missing: tuple[dict[str, Any], ...]
    anomalies: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return any(
            (
                self.added_clubs,
                self.missing_clubs,
                self.renamed_clubs,
                self.metadata_changes,
                self.stat_changes,
                self.added_abilities,
                self.removed_abilities,
                self.ability_text_changes,
                self.ability_value_changes,
                self.data_now_missing,
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"changed": self.changed}


CATALOG_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS catalog_sources (
    source_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    page_last_updated TEXT NOT NULL,
    UNIQUE(url, page_last_updated)
);
CREATE TABLE IF NOT EXISTS catalog_versions (
    version_id TEXT PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES catalog_sources(source_id),
    captured_at TEXT NOT NULL,
    verified_at TEXT,
    catalog_sha256 TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL,
    club_count INTEGER NOT NULL,
    is_current INTEGER NOT NULL CHECK(is_current IN (0, 1)),
    confidence TEXT NOT NULL,
    verification_json TEXT,
    content_json TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_current_catalog ON catalog_versions(is_current) WHERE is_current = 1;
CREATE TABLE IF NOT EXISTS brands (
    brand_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS club_types (
    type_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rarities (
    rarity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clubs (
    version_id TEXT NOT NULL REFERENCES catalog_versions(version_id),
    club_id TEXT NOT NULL,
    name TEXT NOT NULL,
    brand_id TEXT NOT NULL REFERENCES brands(brand_id),
    type_id TEXT NOT NULL REFERENCES club_types(type_id),
    rarity_id TEXT NOT NULL REFERENCES rarities(rarity_id),
    elite INTEGER NOT NULL,
    unlocks_at INTEGER,
    image_url TEXT,
    source_status TEXT,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(version_id, club_id)
);
CREATE TABLE IF NOT EXISTS club_levels (
    version_id TEXT NOT NULL,
    club_id TEXT NOT NULL,
    level_key TEXT NOT NULL,
    level_order INTEGER NOT NULL,
    available INTEGER NOT NULL,
    power REAL,
    control REAL,
    spin REAL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(version_id, club_id, level_key),
    FOREIGN KEY(version_id, club_id) REFERENCES clubs(version_id, club_id)
);
CREATE TABLE IF NOT EXISTS abilities (
    version_id TEXT NOT NULL,
    occurrence_id TEXT NOT NULL,
    club_id TEXT NOT NULL,
    label_id TEXT NOT NULL,
    official_name TEXT NOT NULL,
    official_text TEXT,
    mechanic_id TEXT,
    qualification_status TEXT NOT NULL,
    ambiguity TEXT,
    values_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY(version_id, occurrence_id),
    FOREIGN KEY(version_id, club_id) REFERENCES clubs(version_id, club_id)
);
CREATE TABLE IF NOT EXISTS catalog_anomalies (
    version_id TEXT NOT NULL REFERENCES catalog_versions(version_id),
    anomaly_id TEXT NOT NULL,
    category TEXT NOT NULL,
    detail TEXT NOT NULL,
    payload_json TEXT,
    PRIMARY KEY(version_id, anomaly_id)
);
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _official_texts(raw_club: Mapping[str, Any]) -> dict[str, str]:
    expanded_html = raw_club.get("expanded_html")
    if not isinstance(expanded_html, str) or ">Abilities</h4>" not in expanded_html:
        return {}
    ability_html = expanded_html.split(">Abilities</h4>", 1)[1]
    descriptions: dict[str, str] = {}
    for raw_label, raw_description in re.findall(
        r"<p\b[^>]*>(.*?)</p>\s*<div\b[^>]*>(.*?)</div>", ability_html, re.DOTALL
    ):
        label = html.unescape(re.sub(r"<[^>]+>", "", raw_label)).strip()
        description = html.unescape(re.sub(r"<[^>]+>", "", raw_description)).strip()
        descriptions[label] = description
    return descriptions


def initialize_catalog_database(
    database_path: str | Path,
    manifest_path: str | Path = "data/catalog/versions.json",
) -> tuple[CatalogVersionInfo, ...]:
    database = Path(database_path)
    manifest_file = Path(manifest_path)
    project_root = manifest_file.resolve().parents[2]
    manifest = load_raw_json(manifest_file)
    versions = manifest.get("versions") if isinstance(manifest, Mapping) else None
    if not isinstance(versions, list):
        raise ValueError("Catalog version manifest must contain a versions list")
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.executescript(CATALOG_SCHEMA)
        for item in versions:
            _import_version(connection, item, project_root)
        connection.commit()
        return catalog_versions(connection)


def _import_version(connection: sqlite3.Connection, item: Mapping[str, Any], project_root: Path) -> None:
    version_id = str(item["version_id"])
    if connection.execute("SELECT 1 FROM catalog_versions WHERE version_id = ?", (version_id,)).fetchone():
        return
    catalog_path = project_root / str(item["catalog_path"])
    raw_path = project_root / str(item["raw_path"])
    semantic_path = project_root / str(item["semantic_map_path"])
    if _sha256(catalog_path) != str(item["catalog_sha256"]):
        raise ValueError(f"Catalog hash mismatch for {version_id}")
    if _sha256(raw_path) != str(item["raw_sha256"]):
        raise ValueError(f"Raw catalog hash mismatch for {version_id}")
    catalog = load_raw_json(catalog_path)
    raw = load_raw_json(raw_path)
    semantics = load_raw_json(semantic_path)
    clubs = catalog.get("clubs") if isinstance(catalog, Mapping) else None
    if not isinstance(clubs, Mapping) or len(clubs) != int(item["club_count"]):
        raise ValueError(f"Catalog count mismatch for {version_id}")
    raw_clubs = {
        str(club["name"]): club
        for club in raw.get("clubs", [])
        if isinstance(club, Mapping) and isinstance(club.get("name"), str)
    }
    semantic_entries = semantics.get("entries", {}) if isinstance(semantics, Mapping) else {}
    connection.execute(
        "INSERT OR IGNORE INTO catalog_sources(url, page_last_updated) VALUES (?, ?)",
        (str(item["source_url"]), str(item["source_last_updated"])),
    )
    source_id = connection.execute(
        "SELECT source_id FROM catalog_sources WHERE url = ? AND page_last_updated = ?",
        (str(item["source_url"]), str(item["source_last_updated"])),
    ).fetchone()[0]
    if bool(item.get("is_current")):
        connection.execute("UPDATE catalog_versions SET is_current = 0")
    connection.execute(
        """INSERT INTO catalog_versions(
            version_id, source_id, captured_at, verified_at, catalog_sha256, raw_sha256,
            club_count, is_current, confidence, verification_json, content_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            version_id,
            source_id,
            str(item["captured_at"]),
            item.get("verified_at"),
            str(item["catalog_sha256"]),
            str(item["raw_sha256"]),
            int(item["club_count"]),
            int(bool(item.get("is_current"))),
            str(item["confidence"]),
            _json(item.get("verification", {})),
            _json(catalog),
        ),
    )
    for club_id, club in clubs.items():
        brand = club["brand"]
        club_type = club["club_type"]
        rarity = club["rarity"]
        connection.execute("INSERT OR IGNORE INTO brands VALUES (?, ?)", (brand["id"], brand["name"]))
        connection.execute("INSERT OR IGNORE INTO club_types VALUES (?, ?)", (club_type["id"], club_type["name"]))
        connection.execute("INSERT OR IGNORE INTO rarities VALUES (?, ?)", (rarity["id"], rarity["name"]))
        connection.execute(
            "INSERT INTO clubs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version_id,
                club_id,
                club["name"],
                brand["id"],
                club_type["id"],
                rarity["id"],
                int(bool(club.get("elite"))),
                club.get("unlocks_at"),
                club.get("image_url"),
                club.get("source_capture", {}).get("status"),
                _json(club),
            ),
        )
        for order, level_key in enumerate(club.get("level_order", [])):
            level = club["levels"][level_key]
            stats = level.get("stats", {})
            connection.execute(
                "INSERT INTO club_levels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    version_id,
                    club_id,
                    level_key,
                    order,
                    int(bool(level.get("available"))),
                    stats.get("power"),
                    stats.get("control"),
                    stats.get("spin"),
                    _json(level),
                ),
            )
        raw_club = raw_clubs.get(str(club["name"]), {})
        raw_rows = raw_club.get("tables", [{}])[0].get("rows", []) if raw_club else []
        official_names = [str(row[0]) for row in raw_rows[4:] if row]
        descriptions = _official_texts(raw_club)
        for index, ability in enumerate(club.get("abilities", [])):
            label_id = str(ability["label_id"])
            official_name = official_names[index] if index < len(official_names) else label_id.replace("_", " ").title()
            semantic = semantic_entries.get(f"label:{label_id}", {})
            connection.execute(
                "INSERT INTO abilities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    version_id,
                    ability["occurrence_id"],
                    club_id,
                    label_id,
                    official_name,
                    descriptions.get(official_name),
                    semantic.get("mechanic_id"),
                    semantic.get("validation_status") or semantic.get("interpretation_status") or "uninterpreted",
                    None,
                    _json(ability.get("values_by_level", {})),
                    _json(ability),
                ),
            )
    limitations = item.get("verification", {}).get("limitations", [])
    for index, detail in enumerate(limitations, start=1):
        connection.execute(
            "INSERT INTO catalog_anomalies VALUES (?, ?, ?, ?, ?)",
            (version_id, f"source-limitation-{index}", "source_limitation", str(detail), None),
        )


def catalog_versions(connection_or_path: sqlite3.Connection | str | Path) -> tuple[CatalogVersionInfo, ...]:
    owns_connection = not isinstance(connection_or_path, sqlite3.Connection)
    connection = sqlite3.connect(connection_or_path) if owns_connection else connection_or_path
    try:
        rows = connection.execute(
            """SELECT v.version_id, s.url, s.page_last_updated, v.captured_at, v.verified_at,
                      v.catalog_sha256, v.raw_sha256, v.club_count, v.is_current, v.confidence
               FROM catalog_versions v JOIN catalog_sources s USING(source_id)
               ORDER BY COALESCE(v.verified_at, v.captured_at)"""
        ).fetchall()
        return tuple(CatalogVersionInfo(*row[:8], bool(row[8]), row[9]) for row in rows)
    finally:
        if owns_connection:
            connection.close()


def current_catalog_version(database_path: str | Path) -> CatalogVersionInfo:
    versions = tuple(item for item in catalog_versions(database_path) if item.is_current)
    if len(versions) != 1:
        raise ValueError("Exactly one current catalog version is required")
    return versions[0]


def catalog_mapping(database_path: str | Path, version_id: str | None = None) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        if version_id is None:
            row = connection.execute("SELECT content_json FROM catalog_versions WHERE is_current = 1").fetchone()
        else:
            row = connection.execute("SELECT content_json FROM catalog_versions WHERE version_id = ?", (version_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown catalog version")
        return json.loads(row[0])


def diff_catalog_versions(database_path: str | Path, old_version: str, new_version: str) -> CatalogDiff:
    old = catalog_mapping(database_path, old_version)
    new = catalog_mapping(database_path, new_version)
    old_clubs = old["clubs"]
    new_clubs = new["clubs"]
    old_ids = set(old_clubs)
    new_ids = set(new_clubs)
    renamed: list[tuple[str, str, str]] = []
    metadata: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    missing_data: list[dict[str, Any]] = []
    old_abilities: dict[str, tuple[str, Mapping[str, Any]]] = {}
    new_abilities: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for club_id in sorted(old_ids & new_ids):
        old_club = old_clubs[club_id]
        new_club = new_clubs[club_id]
        if old_club["name"] != new_club["name"]:
            renamed.append((club_id, old_club["name"], new_club["name"]))
        for field in ("brand", "club_type", "rarity", "elite", "unlocks_at"):
            if old_club.get(field) != new_club.get(field):
                metadata.append({"club_id": club_id, "field": field, "before": old_club.get(field), "after": new_club.get(field)})
        level_keys = set(old_club.get("levels", {})) | set(new_club.get("levels", {}))
        for level in sorted(level_keys):
            before = old_club.get("levels", {}).get(level)
            after = new_club.get("levels", {}).get(level)
            if before != after:
                stats.append({"club_id": club_id, "level": level, "before": before, "after": after})
                if before is not None and after is None:
                    missing_data.append({"club_id": club_id, "level": level, "kind": "level"})
    for club_id, club in old_clubs.items():
        for ability in club.get("abilities", []):
            old_abilities[str(ability["occurrence_id"])] = (club_id, ability)
    for club_id, club in new_clubs.items():
        for ability in club.get("abilities", []):
            new_abilities[str(ability["occurrence_id"])] = (club_id, ability)
    common_abilities = set(old_abilities) & set(new_abilities)
    value_changes = tuple(
        {
            "occurrence_id": occurrence_id,
            "before": old_abilities[occurrence_id][1].get("values_by_level"),
            "after": new_abilities[occurrence_id][1].get("values_by_level"),
        }
        for occurrence_id in sorted(common_abilities)
        if old_abilities[occurrence_id][1].get("values_by_level") != new_abilities[occurrence_id][1].get("values_by_level")
    )
    with sqlite3.connect(database_path) as connection:
        old_text = dict(connection.execute("SELECT occurrence_id, COALESCE(official_text, '') FROM abilities WHERE version_id = ?", (old_version,)))
        new_text = dict(connection.execute("SELECT occurrence_id, COALESCE(official_text, '') FROM abilities WHERE version_id = ?", (new_version,)))
        anomalies = tuple(row[0] for row in connection.execute("SELECT detail FROM catalog_anomalies WHERE version_id = ? ORDER BY anomaly_id", (new_version,)))
    text_changes = tuple(
        {"occurrence_id": occurrence_id, "before": old_text.get(occurrence_id), "after": new_text.get(occurrence_id)}
        for occurrence_id in sorted(set(old_text) & set(new_text))
        if old_text.get(occurrence_id) != new_text.get(occurrence_id)
    )
    return CatalogDiff(
        old_version=old_version,
        new_version=new_version,
        added_clubs=tuple(sorted(new_ids - old_ids)),
        missing_clubs=tuple(sorted(old_ids - new_ids)),
        renamed_clubs=tuple(renamed),
        metadata_changes=tuple(metadata),
        stat_changes=tuple(stats),
        added_abilities=tuple(sorted(set(new_abilities) - set(old_abilities))),
        removed_abilities=tuple(sorted(set(old_abilities) - set(new_abilities))),
        ability_text_changes=text_changes,
        ability_value_changes=value_changes,
        data_now_missing=tuple(missing_data),
        anomalies=anomalies,
    )


def render_catalog_diff_markdown(diff: CatalogDiff) -> str:
    lines = [
        "# Catalog Version Diff",
        "",
        f"- Previous: `{diff.old_version}`",
        f"- Current: `{diff.new_version}`",
        f"- Content changed: **{'yes' if diff.changed else 'no'}**",
        "",
        "| Category | Count |",
        "|---|---:|",
        f"| Added clubs | {len(diff.added_clubs)} |",
        f"| Missing clubs | {len(diff.missing_clubs)} |",
        f"| Renamed clubs | {len(diff.renamed_clubs)} |",
        f"| Metadata changes | {len(diff.metadata_changes)} |",
        f"| Level/stat changes | {len(diff.stat_changes)} |",
        f"| Added abilities | {len(diff.added_abilities)} |",
        f"| Removed abilities | {len(diff.removed_abilities)} |",
        f"| Ability text changes | {len(diff.ability_text_changes)} |",
        f"| Ability value changes | {len(diff.ability_value_changes)} |",
        f"| Data now missing | {len(diff.data_now_missing)} |",
        "",
        "The official page still declares `Last Updated: June 14th, 2026`. The August 4 verification found the same 88 public club entries, so the verified version deliberately retains the byte-identical catalog payload.",
        "",
        "## Source limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in diff.anomalies)
    return "\n".join(lines).rstrip() + "\n"
