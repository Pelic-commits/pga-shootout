from pathlib import Path
import shutil

from pga_shootout.storage import PgaDatabase, USER_FILENAMES
from pga_shootout.user_management import InventorySyncAssistant, SqliteUserDataStore


ROOT = Path(__file__).resolve().parents[1]


def store(tmp_path):
    user = tmp_path / "user"
    user.mkdir()
    for name in USER_FILENAMES:
        shutil.copy2(ROOT / "data/user" / name, user / name)
    database = tmp_path / "app.sqlite"
    result = SqliteUserDataStore(database, ROOT / "data/normalized/clubs_official.json", legacy_user_dir=user, manifest_path=ROOT / "data/catalog/versions.json")
    result.ensure_files()
    return result


def test_search_and_metadata_filters_do_not_require_internal_ids(tmp_path):
    data = store(tmp_path)
    assert data.search_clubs("black") == (("blacksmith", "Blacksmith"),)
    mythical_irons = data.filter_clubs(brand="Mythical", club_type="Iron")
    assert any(item["display_name"] == "Blacksmith" for item in mythical_irons)
    assert len(data.filter_clubs(unexamined=True)) == 67
    assert any(item["display_name"] == "Blacksmith" for item in data.filter_clubs(incomplete=True))
    assert data.new_catalog_clubs() == ()


def test_cancelled_sync_makes_no_change(tmp_path):
    data = store(tmp_path)
    before = data.database.load_user_bundle()
    outputs = []
    answers = iter(["9"])
    InventorySyncAssistant(data, input_fn=lambda _: next(answers), output_fn=outputs.append).run()
    assert data.database.load_user_bundle() == before
    assert any("aucune donnée" in line for line in outputs)


def test_multiple_staged_clubs_are_written_in_one_confirmed_batch(tmp_path):
    data = store(tmp_path)
    changes = (
        {"club_id": "blacksmith", "display_name": "Blacksmith", "unlocked": True, "current_level": 9, "cards_owned": None, "cards_required_for_next_upgrade": None},
        {"club_id": "meteor", "display_name": "Meteor", "unlocked": False, "current_level": None, "cards_owned": None, "cards_required_for_next_upgrade": None},
    )
    backup = data.apply_inventory_batch(changes)
    assert backup.is_file()
    bundle = data.database.load_user_bundle()
    assert bundle.inventory.get("blacksmith").current_level == 9
    assert bundle.inventory.get("meteor").unlocked is False
