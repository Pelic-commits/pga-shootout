from __future__ import annotations

from pathlib import Path
import json

from pga_shootout.capability_audit import analyze_capability_audit, render_capability_audit_markdown
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]


def audit():
    return analyze_capability_audit(
        user_dir=ROOT / "data" / "pga_shootout.sqlite",
        normalized_dir=ROOT / "data" / "normalized",
        raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
    )


def test_audit_partitions_every_official_occurrence_without_loss():
    report = audit()
    assert report.catalog_clubs == 88
    assert report.catalog_occurrences == 162
    assert (
        report.global_fully_supported_occurrences
        + report.global_partial_occurrences
        + report.global_unresolved_occurrences
    ) == report.catalog_occurrences
    assert len(report.occurrences) == report.global_partial_occurrences + report.global_unresolved_occurrences
    assert sum(report.class_counts.values()) == len(report.occurrences)


def test_owned_state_comes_from_current_sqlite_and_is_partitioned():
    report = audit()
    bundle = load_user_data(ROOT / "data" / "pga_shootout.sqlite")
    owned_ids = {item.club_id for item in bundle.inventory.entries}
    catalog = json.loads((ROOT / "data" / "normalized" / "clubs_official.json").read_text(encoding="utf-8"))
    assert report.owned_clubs == len(owned_ids)
    assert report.owned_occurrences == sum(len(catalog["clubs"][identifier]["abilities"]) for identifier in owned_ids)
    assert (
        report.owned_fully_supported_occurrences
        + report.owned_partial_occurrences
        + report.owned_unresolved_occurrences
    ) == report.owned_occurrences
    assert report.owned_fully_simulated_clubs + report.owned_clubs_with_unresolved_ability == len(owned_ids)


def test_current_qualification_contains_no_unvalidated_direct_implementation():
    report = audit()
    assert report.class_counts["A"] == 0
    assert report.class_counts["B"] == 0
    assert report.owned_class_counts["H"] == 2
    assert all(item.provenance == "official_versioned_catalog_and_qualified_semantic_map" for item in report.occurrences)


def test_wave_and_gearshift_reflect_current_real_state():
    report = audit()
    shoreline = next(item for item in report.occurrences if item.occurrence_id == "wave__shoreline_rush")
    assert shoreline.owned and shoreline.current_level == 7
    assert shoreline.current_level_value == "125%"
    assert shoreline.audit_class == "E"
    assert all(item.club_id != "gearshift" for item in report.occurrences)


def test_report_is_reproducible_and_contains_full_level_tables():
    first = render_capability_audit_markdown(audit())
    second = render_capability_audit_markdown(audit())
    assert first == second
    assert "Wave — Shoreline Rush" in first
    assert "7: 125%" in first
    assert "Gearshift" not in first
