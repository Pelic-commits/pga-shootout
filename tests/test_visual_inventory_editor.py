from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from pga_shootout.inventory_editor import InventoryEditorService
from pga_shootout.storage import USER_FILENAMES


ROOT = Path(__file__).resolve().parents[1]


def service(tmp_path: Path, *, without_blacksmith: bool = False) -> InventoryEditorService:
    user = tmp_path / "user"
    user.mkdir()
    for name in USER_FILENAMES:
        shutil.copy2(ROOT / "data/user" / name, user / name)
    if without_blacksmith:
        path = user / "inventory.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["entries"] = [item for item in document["entries"] if item["club_id"] != "blacksmith"]
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = InventoryEditorService(
        tmp_path / "app.sqlite",
        catalog_path=ROOT / "data/normalized/clubs_official.json",
        manifest_path=ROOT / "data/catalog/versions.json",
        legacy_user_dir=user,
        normalized_dir=ROOT / "data/normalized",
        raw_catalog_path=ROOT / "data/raw/pga_club_stats_extract_v2_2026-07-21.json",
    )
    result.initialize()
    return result


def edit(rows, club_id, **changes):
    return tuple(replace(row, examined=True, **changes) if row.club_id == club_id else row for row in rows)


def catalog_snapshot(editor: InventoryEditorService):
    with editor.database.connect() as connection:
        return (
            tuple(connection.execute("SELECT * FROM catalog_versions ORDER BY version_id")),
            tuple(connection.execute("SELECT * FROM clubs ORDER BY version_id, club_id")),
            tuple(connection.execute("SELECT * FROM club_levels ORDER BY version_id, club_id, level_key")),
            tuple(connection.execute("SELECT * FROM abilities ORDER BY version_id, occurrence_id")),
        )


def test_loads_all_88_catalog_clubs_and_filters_by_display_metadata(tmp_path):
    editor = service(tmp_path)
    rows = editor.load_rows()
    assert len(rows) == 88
    assert [row.name for row in editor.filter_rows(rows, search="BLACKsmith")] == ["Blacksmith"]
    assert all(row.brand == "Mythical" for row in editor.filter_rows(rows, brand="Mythical"))
    assert all(row.club_type == "Iron" for row in editor.filter_rows(rows, club_type="Iron"))
    assert all(row.rarity == "Epic" for row in editor.filter_rows(rows, rarity="Epic"))
    assert all(row.owned for row in editor.filter_rows(rows, ownership="Possédés"))
    assert all(not row.complete for row in editor.filter_rows(rows, incomplete_only=True))


def test_adds_blacksmith_with_unknown_values_and_real_zero_cards(tmp_path):
    editor = service(tmp_path, without_blacksmith=True)
    original = editor.load_rows()
    changed = edit(original, "blacksmith", owned=True, current_level=9, cards_owned=0, cards_required=None)
    backup, summary, dashboard = editor.save(original, changed)
    blacksmith = next(row for row in editor.load_rows() if row.club_id == "blacksmith")
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT 1 FROM user_clubs WHERE club_id = 'blacksmith'").fetchone() is None
    assert summary.added == ("Blacksmith",)
    assert blacksmith.owned and blacksmith.current_level == 9
    assert blacksmith.cards_owned == 0
    assert blacksmith.cards_required is None
    assert blacksmith.upgrade_available is None
    assert not blacksmith.complete
    assert dashboard.blacksmith_owned


def test_multiple_clubs_save_once_preserves_bags_and_catalog(tmp_path):
    editor = service(tmp_path)
    original = editor.load_rows()
    bags_before = editor.database.load_user_bundle().bags
    catalog_before = catalog_snapshot(editor)
    meteor_level = next(row.allowed_levels[0] for row in original if row.club_id == "meteor")
    changed = edit(original, "blacksmith", owned=True, current_level=9, cards_owned=0, cards_required=10)
    changed = edit(changed, "meteor", owned=True, current_level=meteor_level, cards_owned=None, cards_required=None)
    backup, summary, _dashboard = editor.save(original, changed)
    loaded = {row.club_id: row for row in editor.load_rows()}
    assert backup.is_file()
    assert len(editor.changed_rows(original, changed)) == 2
    assert summary.added == ("Meteor",)
    assert loaded["blacksmith"].upgrade_available is False
    assert loaded["meteor"].owned and loaded["meteor"].current_level == meteor_level
    assert editor.database.load_user_bundle().bags == bags_before
    assert catalog_snapshot(editor) == catalog_before


def test_cancel_is_a_pure_draft_and_writes_nothing(tmp_path):
    editor = service(tmp_path)
    original = editor.load_rows()
    bundle_before = editor.database.load_user_bundle()
    _discarded = edit(original, "blacksmith", owned=True, current_level=9)
    assert editor.database.load_user_bundle() == bundle_before
    assert editor.load_rows() == original


def test_duplicate_catalog_row_is_reported_before_any_write(tmp_path):
    editor = service(tmp_path)
    rows = editor.load_rows()
    errors = editor.validate((*rows, rows[0]))
    assert errors[rows[0].club_id] == "Ce club apparaît plusieurs fois."


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"owned": True, "current_level": 1}, "Niveau indisponible"),
        ({"owned": True, "current_level": 9, "cards_owned": -1}, "positives ou égales à zéro"),
        ({"owned": True, "current_level": 9, "cards_required": 0}, "strictement positif"),
    ),
)
def test_invalid_blacksmith_row_rolls_back_whole_session(tmp_path, changes, message):
    editor = service(tmp_path, without_blacksmith=True)
    original = editor.load_rows()
    bundle_before = editor.database.load_user_bundle()
    changed = edit(original, "blacksmith", **changes)
    with pytest.raises(ValueError, match=message):
        editor.save(original, changed)
    assert editor.database.load_user_bundle() == bundle_before


def test_non_owned_club_cannot_keep_level_or_cards(tmp_path):
    editor = service(tmp_path)
    rows = editor.load_rows()
    changed = edit(rows, "blacksmith", owned=False, current_level=9, cards_owned=0, cards_required=None)
    errors = editor.validate(changed)
    assert "blacksmith" in errors
    assert "non possédé" in errors["blacksmith"]


def test_launcher_opens_visual_editor_directly_without_main_menu():
    launcher = (ROOT / "GERER_MON_INVENTAIRE.bat").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0"' in launcher
    assert "-m venv .venv" in launcher
    assert "-m pip install -e ." in launcher
    assert "root=tk.Tk(); root.withdraw(); root.destroy()" in launcher
    assert 'pythonw.exe" -m pga_shootout.inventory_editor' in launcher
    assert "pga_shootout.cli assistant" not in launcher
