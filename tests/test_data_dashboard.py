from pathlib import Path
import shutil

from pga_shootout.data_dashboard import build_data_dashboard, render_dashboard_markdown
from pga_shootout.storage import PgaDatabase, USER_FILENAMES


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_separates_catalog_inventory_and_optimization(tmp_path):
    user = tmp_path / "user"
    user.mkdir()
    for name in USER_FILENAMES:
        shutil.copy2(ROOT / "data/user" / name, user / name)
    database = PgaDatabase(tmp_path / "app.sqlite")
    database.initialize_catalog(ROOT / "data/catalog/versions.json")
    database.migrate_json_user(user)
    report = build_data_dashboard(database.path, normalized_dir=ROOT / "data/normalized", raw_catalog_path=ROOT / "data/raw/pga_club_stats_extract_v2_2026-07-21.json")
    assert report.catalog["clubs"] == 88
    assert report.catalog["changes_from_previous"]["changed"] is False
    assert report.inventory["owned_clubs"] == 21
    assert report.inventory["blacksmith"]["owned"] is True
    assert "real carry or distance without a validated physics model" in report.optimization["not_honestly_calculable"]
    assert "## Catalogue" in render_dashboard_markdown(report)
