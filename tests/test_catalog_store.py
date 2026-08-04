from pathlib import Path

from pga_shootout.catalog_store import catalog_mapping, catalog_versions, diff_catalog_versions, initialize_catalog_database


ROOT = Path(__file__).resolve().parents[1]


def test_versioned_catalog_retains_old_version_and_has_reproducible_zero_diff(tmp_path):
    database = tmp_path / "catalog.sqlite"
    versions = initialize_catalog_database(database, ROOT / "data/catalog/versions.json")
    assert [item.club_count for item in versions] == [88, 88]
    assert versions[0].is_current is False
    assert versions[1].is_current is True
    assert len(catalog_versions(database)) == 2
    diff = diff_catalog_versions(database, versions[0].version_id, versions[1].version_id)
    assert diff.changed is False
    assert diff.added_clubs == ()
    assert diff.stat_changes == ()
    assert diff.ability_text_changes == ()


def test_blacksmith_is_imported_as_an_ordinary_official_club(tmp_path):
    database = tmp_path / "catalog.sqlite"
    initialize_catalog_database(database, ROOT / "data/catalog/versions.json")
    club = catalog_mapping(database)["clubs"]["blacksmith"]
    assert club["name"] == "Blacksmith"
    assert club["brand"]["name"] == "Mythical"
    assert club["club_type"]["name"] == "Iron"
    assert club["levels"]["9"]["stats"] == {"power": 10, "control": 7, "spin": 5}
