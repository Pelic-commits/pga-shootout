from pathlib import Path
import shutil

from pga_shootout.bag_evaluation import evaluate_saved_bag
from pga_shootout.models import EvaluationMode
from pga_shootout.storage import PgaDatabase, USER_FILENAMES, migration_preview
from pga_shootout.user_data import load_user_data


ROOT = Path(__file__).resolve().parents[1]


def copied_user_data(tmp_path: Path) -> Path:
    destination = tmp_path / "user"
    destination.mkdir()
    for name in USER_FILENAMES:
        shutil.copy2(ROOT / "data/user" / name, destination / name)
    return destination


def test_json_migration_is_backed_up_lossless_and_engine_compatible(tmp_path):
    user_dir = copied_user_data(tmp_path)
    before = load_user_data(user_dir)
    preview = migration_preview(user_dir)
    database = PgaDatabase(tmp_path / "app.sqlite")
    database.initialize_catalog(ROOT / "data/catalog/versions.json")
    result = database.migrate_json_user(user_dir)
    after = database.load_user_bundle()
    assert result.migrated and result.validation_messages == ()
    assert Path(result.backup_path).is_dir()
    assert preview.inventory_entries == 21
    assert before == after
    assert load_user_data(database.path) == before
    legacy_result = evaluate_saved_bag("par3_divebomb", level=12, mode=EvaluationMode.PARTIAL, user_dir=user_dir)
    sqlite_result = evaluate_saved_bag("par3_divebomb", level=12, mode=EvaluationMode.PARTIAL, user_dir=database.path)
    assert sqlite_result == legacy_result


def test_batch_update_backup_and_export_preserve_unknown_values(tmp_path):
    user_dir = copied_user_data(tmp_path)
    database = PgaDatabase(tmp_path / "app.sqlite")
    database.initialize_catalog(ROOT / "data/catalog/versions.json")
    database.migrate_json_user(user_dir)
    backup = database.apply_inventory_batch(({
        "club_id": "blacksmith", "display_name": "Blacksmith", "unlocked": True,
        "current_level": None, "cards_owned": None, "cards_required_for_next_upgrade": None,
    },))
    assert backup.is_file()
    blacksmith = database.load_user_bundle().inventory.get("blacksmith")
    assert blacksmith.current_level is None and blacksmith.cards_owned is None
    exported = database.export_user_json(tmp_path / "export")
    assert {path.name for path in exported} == set(USER_FILENAMES)

