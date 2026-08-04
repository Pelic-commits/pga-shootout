"""Objective data-quality dashboard for catalog, inventory and optimization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import sqlite3
from pathlib import Path
from typing import Any

from .catalog_store import catalog_versions, current_catalog_version, diff_catalog_versions
from .inventory_status import analyze_inventory_status
from .storage import PgaDatabase


@dataclass(frozen=True)
class DataDashboard:
    catalog: dict[str, Any]
    inventory: dict[str, Any]
    optimization: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_data_dashboard(database_path: str | Path, *, normalized_dir: str | Path = "data/normalized", raw_catalog_path: str | Path = "data/raw/pga_club_stats_extract_v2_2026-07-21.json") -> DataDashboard:
    database = PgaDatabase(database_path)
    version = current_catalog_version(database.path)
    versions = catalog_versions(database.path)
    previous = versions[-2] if len(versions) > 1 else None
    diff = diff_catalog_versions(database.path, previous.version_id, version.version_id) if previous else None
    with sqlite3.connect(database.path) as connection:
        available_levels, complete_levels = connection.execute(
            "SELECT COUNT(*), SUM(CASE WHEN power IS NOT NULL AND control IS NOT NULL AND spin IS NOT NULL THEN 1 ELSE 0 END) FROM club_levels WHERE version_id = ? AND available = 1",
            (version.version_id,),
        ).fetchone()
        ability_count, described_count = connection.execute(
            "SELECT COUNT(*), SUM(CASE WHEN official_name <> '' AND official_text <> '' THEN 1 ELSE 0 END) FROM abilities WHERE version_id = ?",
            (version.version_id,),
        ).fetchone()
    bundle = database.load_user_bundle()
    examined = len(bundle.inventory.entries)
    owned = tuple(item for item in bundle.inventory.entries if item.unlocked)
    complete = sum(item.current_level is not None and item.cards_owned is not None and item.cards_required_for_next_upgrade is not None for item in owned)
    status = analyze_inventory_status(user_dir=database.path, normalized_dir=normalized_dir, raw_catalog_path=raw_catalog_path)
    blacksmith = next((item for item in bundle.inventory.entries if item.club_id == "blacksmith"), None)
    return DataDashboard(
        catalog={
            "version": version.version_id, "source_last_updated": version.source_last_updated,
            "verified_at": version.verified_at, "source": version.source_url, "clubs": version.club_count,
            "statistics_complete": complete_levels == available_levels,
            "statistics_levels_complete": complete_levels, "statistics_levels_available": available_levels,
            "abilities_complete": described_count == ability_count, "abilities_described": described_count,
            "abilities_total": ability_count, "confidence": version.confidence,
            "anomalies": list(diff.anomalies if diff else ()),
            "changes_from_previous": diff.as_dict() if diff else None,
        },
        inventory={
            "owned_clubs": len(owned), "known_levels": sum(item.current_level is not None for item in owned),
            "complete_owned_entries": complete, "examined_clubs": examined,
            "unexamined_clubs": version.club_count - examined, "saved_bags": len(bundle.bags),
            "recently_added_catalog_clubs": list(diff.added_clubs if diff else ()),
            "blacksmith": {"present_in_catalog": True, "examined": blacksmith is not None, "owned": bool(blacksmith and blacksmith.unlocked), "level": blacksmith.current_level if blacksmith else None},
            "engine_coverage": {"simulated": status.simulated_abilities, "official": status.official_abilities, "percent": status.inventory_coverage_percent},
        },
        optimization={
            "usable": ["official base stats by level", "deterministic implemented bag effects", "separate objective metrics", "bag order and composition"],
            "incomplete": ["user levels and cards", "inventory examination", "unresolved ability coverage"],
            "calculable_request_families": ["constraints and ordered objectives over validated engine metrics", "Pareto comparisons over validated metrics"],
            "partially_calculable": ["queries including unresolved abilities", "multi-scenario queries with only categorical known context"],
            "not_honestly_calculable": ["real carry or distance without a validated physics model", "course geometry optimization", "wind outcomes beyond objective wind-resistance comparison"],
        },
    )


def render_dashboard_markdown(report: DataDashboard) -> str:
    c, i, o = report.catalog, report.inventory, report.optimization
    lines = [
        "# Data Dashboard", "", "## Catalogue", "",
        f"- Version : `{c['version']}`", f"- Source : {c['source']}",
        f"- Dernière mise à jour annoncée : {c['source_last_updated']}", f"- Vérifié le : {c['verified_at']}",
        f"- Clubs : {c['clubs']}", f"- Niveaux statistiques complets : {c['statistics_levels_complete']}/{c['statistics_levels_available']}",
        f"- Capacités documentées : {c['abilities_described']}/{c['abilities_total']}", f"- Changements de contenu : {'oui' if c['changes_from_previous'] and c['changes_from_previous']['changed'] else 'aucun'}", "",
        "## Inventaire", "", f"- Clubs possédés : {i['owned_clubs']}", f"- Niveaux connus : {i['known_levels']}",
        f"- Entrées possédées complètes : {i['complete_owned_entries']}", f"- Clubs non examinés : {i['unexamined_clubs']}",
        f"- Sacs enregistrés : {i['saved_bags']}", f"- Blacksmith possédé : {'oui' if i['blacksmith']['owned'] else 'non/inconnu'} (niveau {i['blacksmith']['level'] or 'inconnu'})",
        f"- Couverture moteur : {i['engine_coverage']['simulated']}/{i['engine_coverage']['official']} ({i['engine_coverage']['percent']} %)", "",
        "## Optimisation", "", "### Exploitable", "", *[f"- {item}" for item in o["usable"]], "", "### Incomplet", "", *[f"- {item}" for item in o["incomplete"]], "", "### Impossible honnêtement aujourd'hui", "", *[f"- {item}" for item in o["not_honestly_calculable"]], "",
    ]
    return "\n".join(lines)


def write_dashboard(report: DataDashboard, markdown_path: str | Path, json_path: str | Path) -> None:
    markdown = Path(markdown_path)
    structured = Path(json_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    structured.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_dashboard_markdown(report), encoding="utf-8", newline="\n")
    structured.write_text(json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
