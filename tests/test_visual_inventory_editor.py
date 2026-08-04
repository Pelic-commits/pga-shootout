from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from pga_shootout.inventory_editor import (
    BRAND_ORDER,
    CLUB_TYPE_ORDER,
    InventoryEditorApp,
    InventoryRow,
    InventoryEditorService,
    UNKNOWN_CALCULATION,
    cards_required_for_next_level,
)
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


def catalog_row(club_id: str, name: str, brand: str, club_type: str) -> InventoryRow:
    return InventoryRow(
        club_id=club_id,
        name=name,
        brand=brand,
        club_type=club_type,
        rarity="Common",
        unlock_level=1,
        allowed_levels=tuple(range(1, 13)),
        examined=True,
        owned=True,
        current_level=8,
        cards_owned=0,
        cards_required=None,
    )


def fake_edit_app(rows: tuple[InventoryRow, ...]):
    class FakeEntry:
        def __init__(self):
            self.value = ""
            self.bindings = {}
            self.destroyed = False
            self.selection = None

        def insert(self, _index, value):
            self.value = value

        def get(self):
            return self.value

        def place(self, **_kwargs):
            pass

        def focus_set(self):
            pass

        def selection_range(self, start, end):
            self.selection = (start, end)

        def icursor(self, _position):
            pass

        def bind(self, event, callback):
            self.bindings[event] = callback

        def destroy(self):
            self.destroyed = True

    class FakeTree:
        def __init__(self):
            self.selected = []
            self.focused = None
            self.has_focus = False

        def exists(self, item):
            return item in app.rows

        def bbox(self, _item, _column):
            return 0, 0, 100, 20

        def selection_set(self, item):
            self.selected.append(item)

        def see(self, _item):
            pass

        def focus(self, item):
            self.focused = item

        def focus_set(self):
            self.has_focus = True

    entries = []

    def entry_factory(_parent):
        entry = FakeEntry()
        entries.append(entry)
        return entry

    app = InventoryEditorApp.__new__(InventoryEditorApp)
    app.rows = {row.club_id: row for row in rows}
    app.errors = {}
    app.tree = FakeTree()
    app.ttk = SimpleNamespace(Entry=entry_factory)
    app.root = SimpleNamespace(after_idle=lambda callback: callback())
    app._visible_rows = lambda: tuple(app.rows.values())
    app._refresh = lambda: None
    return app, entries


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


def test_adds_blacksmith_with_calculated_progression_and_real_zero_cards(tmp_path):
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
    assert blacksmith.next_threshold == 2
    assert blacksmith.progression == "0 / 2"
    assert blacksmith.cards_remaining == 2
    assert blacksmith.upgrade_available is False
    assert blacksmith.complete
    assert dashboard.blacksmith_owned


def test_multiple_clubs_save_once_preserves_bags_and_catalog(tmp_path):
    editor = service(tmp_path)
    original = editor.load_rows()
    bags_before = editor.database.load_user_bundle().bags
    catalog_before = catalog_snapshot(editor)
    meteor_level = next(row.allowed_levels[0] for row in original if row.club_id == "meteor")
    changed = edit(original, "blacksmith", owned=True, current_level=9, cards_owned=0)
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


@pytest.mark.parametrize(
    ("rarity", "level", "expected"),
    (
        ("Common", 8, 500),
        ("Rare", 6, 50),
        ("Epic", 6, 25),
        ("Legendary", 7, 2),
        ("Mythical", 9, 2),
        ("Common", 12, None),
        ("Mythical", None, None),
    ),
)
def test_card_threshold_is_calculated_from_rarity_and_current_level(rarity, level, expected):
    assert cards_required_for_next_level(rarity, level) == expected


def test_existing_threshold_is_preserved_only_while_level_is_unknown(tmp_path):
    editor = service(tmp_path)
    cyclotron = next(row for row in editor.load_rows() if row.club_id == "cyclotron")
    assert cyclotron.current_level is None
    assert cyclotron.next_threshold == 50
    known = replace(cyclotron, current_level=6)
    assert known.next_threshold == 50
    changed_level = replace(cyclotron, current_level=7)
    assert changed_level.next_threshold == 100


def test_calculated_columns_react_to_cards_and_never_go_negative(tmp_path):
    editor = service(tmp_path, without_blacksmith=True)
    row = next(row for row in editor.load_rows() if row.club_id == "blacksmith")
    row = replace(row, examined=True, owned=True, current_level=9, cards_owned=1)
    assert row.progression == "1 / 2"
    assert row.cards_remaining == 1
    assert row.upgrade_available is False
    upgraded = replace(row, cards_owned=3)
    assert upgraded.progression == "3 / 2"
    assert upgraded.cards_remaining == 0
    assert upgraded.upgrade_available is True
    assert upgraded.as_change()["cards_required_for_next_upgrade"] == 2


def test_only_progression_inputs_are_editable_and_keyboard_navigation_is_stable():
    assert InventoryEditorApp.EDITABLE_COLUMNS == {7: "current_level", 8: "cards_owned"}
    assert "required" in InventoryEditorApp.COLUMNS
    assert "progression" in InventoryEditorApp.COLUMNS
    assert "remaining" in InventoryEditorApp.COLUMNS
    assert "upgrade" in InventoryEditorApp.COLUMNS
    visible = ("alpha", "beta", "gamma")
    assert InventoryEditorApp.next_edit_target(visible, "alpha", 7, "next_cell") == ("alpha", 8)
    assert InventoryEditorApp.next_edit_target(visible, "alpha", 8, "next_cell") == ("beta", 7)
    assert InventoryEditorApp.next_edit_target(visible, "alpha", 7, "stay") is None
    assert InventoryEditorApp.next_edit_target(visible, "gamma", 8, "next_cell") is None


def test_catalog_sort_uses_exact_brand_then_type_order():
    rows = tuple(
        catalog_row(f"{brand}-{club_type}", f"{brand} {club_type}", brand, club_type)
        for brand in reversed(BRAND_ORDER)
        for club_type in reversed(CLUB_TYPE_ORDER)
    )
    ordered = InventoryEditorService.filter_rows(rows)
    observed_brands = tuple(dict.fromkeys(row.brand for row in ordered))
    assert observed_brands == BRAND_ORDER
    for brand in BRAND_ORDER:
        assert tuple(row.club_type for row in ordered if row.brand == brand) == CLUB_TYPE_ORDER


def test_catalog_sort_places_future_categories_last_and_sorts_them_alphabetically():
    rows = (
        catalog_row("zeta", "Zeta", "Zéphyr", "Utility"),
        catalog_row("known", "Known", "Corvid", "Putter"),
        catalog_row("accent", "Accent", "Éclipse", "Chipper"),
        catalog_row("alpha", "Alpha", "Eagle", "Approach"),
    )
    ordered = InventoryEditorService.filter_rows(rows)
    assert [row.club_id for row in ordered] == ["known", "alpha", "accent", "zeta"]


def test_real_catalog_uses_requested_brand_order_including_uppercase_palo(tmp_path):
    editor = service(tmp_path)
    rows = editor.load_rows()
    observed = tuple(dict.fromkeys(row.brand for row in rows))
    assert observed == (
        "Corvid",
        "Forester",
        "Nautilus",
        "PALO",
        "Phoenix",
        "Ryusei",
        "Stanchion",
        "Willoughsby",
        "Mythical",
    )


def test_known_brand_matching_ignores_case_and_surrounding_spaces():
    rows = (
        catalog_row("palo", "Palo", "  PALO  ", "Putter"),
        catalog_row("mythical", "Mythical", "mythical", "Putter"),
        catalog_row("future", "Future", "Zephyr", "Putter"),
    )
    assert [row.club_id for row in InventoryEditorService.filter_rows(rows)] == ["palo", "mythical", "future"]


def test_catalog_sort_names_is_case_and_accent_insensitive_and_survives_filtering():
    rows = (
        catalog_row("zulu", "zulu", "Corvid", "Putter"),
        catalog_row("eclair", "Éclair", "Corvid", "Putter"),
        catalog_row("alpha", "alpha", "Corvid", "Putter"),
        catalog_row("other", "Other", "Forester", "Driver"),
    )
    assert [row.club_id for row in InventoryEditorService.filter_rows(rows)] == ["alpha", "eclair", "zulu", "other"]
    filtered = InventoryEditorService.filter_rows(rows, brand="Corvid")
    assert [row.club_id for row in filtered] == ["alpha", "eclair", "zulu"]


def test_existing_cell_text_is_selected_for_immediate_replacement():
    class FakeEntry:
        def __init__(self):
            self.calls = []

        def selection_range(self, start, end):
            self.calls.append(("selection", start, end))

        def icursor(self, position):
            self.calls.append(("cursor", position))

    entry = FakeEntry()
    InventoryEditorApp.select_existing_text(entry)
    assert entry.calls == [("selection", 0, "end"), ("cursor", "end")]


def test_enter_validates_recalculates_and_returns_focus_to_same_row():
    first = catalog_row("first", "First", "Corvid", "Putter")
    second = catalog_row("second", "Second", "Corvid", "Driver")
    app, entries = fake_edit_app((first, second))
    app._begin_edit("first", 7)
    assert entries[0].selection == (0, "end")
    entries[0].value = "9"
    assert entries[0].bindings["<Return>"](None) == "break"
    assert app.rows["first"].current_level == 9
    assert app.rows["first"].next_threshold == 1_000
    assert len(entries) == 1
    assert app.tree.selected[-1] == "first"
    assert app.tree.focused == "first"
    assert app.tree.has_focus


def test_tab_opens_next_editable_cell_and_escape_discards_its_value():
    first = catalog_row("first", "First", "Corvid", "Putter")
    second = catalog_row("second", "Second", "Corvid", "Driver")
    app, entries = fake_edit_app((first, second))
    app._begin_edit("first", 7)
    entries[0].value = "9"
    assert entries[0].bindings["<Tab>"](None) == "break"
    assert app.rows["first"].current_level == 9
    assert len(entries) == 2
    assert entries[1].value == "0"
    entries[1].value = "999"
    entries[1].bindings["<Escape>"]()
    assert app.rows["first"].cards_owned == 0
    assert entries[1].destroyed


def test_level_12_threshold_is_explicitly_unknown_and_never_persisted(tmp_path):
    editor = service(tmp_path, without_blacksmith=True)
    before = editor.database.load_user_bundle()
    row = next(row for row in editor.load_rows() if row.club_id == "blacksmith")
    row = replace(row, examined=True, owned=True, current_level=12, cards_owned=4, cards_required=999)
    assert row.next_threshold is None
    assert row.as_change()["cards_required_for_next_upgrade"] is None
    app = InventoryEditorApp.__new__(InventoryEditorApp)
    app.errors = {}
    values = app._values(row)
    assert values[8:12] == (UNKNOWN_CALCULATION,) * 4
    assert editor.database.load_user_bundle() == before


def test_launcher_opens_visual_editor_directly_without_main_menu():
    launcher = (ROOT / "GERER_MON_INVENTAIRE.bat").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0"' in launcher
    assert "-m venv .venv" in launcher
    assert "-m pip install -e ." in launcher
    assert "root=tk.Tk(); root.withdraw(); root.destroy()" in launcher
    assert 'pythonw.exe" -m pga_shootout.inventory_editor' in launcher
    assert "pga_shootout.cli assistant" not in launcher
