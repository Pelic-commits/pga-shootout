import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.main_menu import PgaShootoutAssistant
from pga_shootout.user_management import (
    BagAssistant,
    InventoryAssistant,
    USER_FILENAMES,
    UserDataStore,
    UserManagementError,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "normalized" / "clubs_official.json"


class AnswerStream:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self, _prompt):
        return next(self.values)


class FakeRecommendation:
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.calls.append(kwargs)

    def run(self):
        self.kwargs["output_fn"]("Analyse de remplacement exécutée.")
        return 0


class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.user_dir = Path(self.temporary.name) / "user"
        self.store = UserDataStore(self.user_dir, CATALOG)
        self.store.ensure_files()

    def add_clubs(self, count=6):
        club_ids = ("cyclotron", "high_flight", "ember", "maelstrom", "sunstorm", "steadfast")
        for index, club_id in enumerate(club_ids[:count], start=1):
            self.store.save_inventory_entry(
                club_id,
                current_level=10 + index,
                cards_owned=index,
                cards_required=10,
            )
        return club_ids[:count]

    def test_creates_all_missing_user_files_as_valid_empty_data(self):
        self.assertEqual({item.name for item in self.user_dir.glob("*.json")}, set(USER_FILENAMES))
        report = self.store.validation()
        self.assertTrue(report.valid)
        self.assertEqual(report.inventory_entries, 0)
        self.assertEqual(report.saved_bags, 0)

    def test_existing_file_is_not_overwritten_when_another_is_missing(self):
        account = self.user_dir / "account.json"
        original = account.read_bytes()
        (self.user_dir / "observations.json").unlink()
        created = self.store.ensure_files()
        self.assertEqual(created, ("observations.json",))
        self.assertEqual(account.read_bytes(), original)

    def test_backup_precedes_inventory_modification(self):
        before = json.loads((self.user_dir / "inventory.json").read_text(encoding="utf-8"))
        backup, _ = self.store.save_inventory_entry(
            "cyclotron", current_level=12, cards_owned=46, cards_required=50
        )
        backed_up = json.loads((backup / "inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(backed_up, before)
        self.assertTrue(self.store.validation().valid)

    def test_searches_official_clubs_by_display_name_without_accents_or_identifier(self):
        self.assertEqual(self.store.search_clubs("High Flight"), (("high_flight", "High Flight"),))
        self.assertEqual(self.store.search_clubs("flight"), (("high_flight", "High Flight"),))
        self.assertEqual(self.store.search_clubs("does not exist"), ())

    def test_adds_then_modifies_club_and_calculates_upgrade_availability(self):
        _, upgrade = self.store.save_inventory_entry(
            "cyclotron", current_level=12, cards_owned=46, cards_required=50
        )
        self.assertFalse(upgrade)
        _, upgrade = self.store.save_inventory_entry(
            "cyclotron", current_level=13, cards_owned=50, cards_required=50
        )
        entry = self.store.inventory_documents()[0]
        self.assertTrue(upgrade)
        self.assertTrue(entry["upgrade_available"])
        self.assertEqual(entry["current_level"], 13)
        self.assertEqual(len(self.store.inventory_documents()), 1)

    def test_unknown_level_remains_null(self):
        self.store.save_inventory_entry(
            "cyclotron", current_level=None, cards_owned=0, cards_required=1
        )
        self.assertIsNone(self.store.inventory_documents()[0]["current_level"])

    def test_can_mark_not_owned_or_delete_an_accidental_entry(self):
        self.store.save_inventory_entry(
            "cyclotron", current_level=None, cards_owned=0, cards_required=1
        )
        self.store.mark_not_owned("cyclotron")
        self.assertFalse(self.store.inventory_documents()[0]["unlocked"])
        self.store.delete_inventory_entry("cyclotron")
        self.assertEqual(self.store.inventory_documents(), [])

    def test_creates_and_modifies_ordered_five_club_bag(self):
        clubs = self.add_clubs()
        _, bag_id = self.store.save_bag("Mon sac", clubs[:5])
        bag = self.store.bag_documents()[0]
        self.assertEqual(bag["club_ids"], list(clubs[:5]))
        self.store.save_bag("Mon sac modifié", tuple(reversed(clubs[1:6])), bag_id=bag_id)
        changed = self.store.bag_documents()[0]
        self.assertEqual(changed["name"], "Mon sac modifié")
        self.assertEqual(changed["club_ids"], list(reversed(clubs[1:6])))
        self.assertTrue(self.store.validation().valid)

    def test_rejects_duplicate_or_non_owned_bag_clubs_before_writing(self):
        clubs = self.add_clubs(5)
        before = (self.user_dir / "bags.json").read_bytes()
        with self.assertRaisesRegex(UserManagementError, "cinq clubs différents"):
            self.store.save_bag("Doublon", (clubs[0], clubs[0], *clubs[1:4]))
        with self.assertRaisesRegex(UserManagementError, "marqués comme possédés"):
            self.store.save_bag("Inconnu", (*clubs[:4], "rook"))
        self.assertEqual((self.user_dir / "bags.json").read_bytes(), before)

    def test_deletes_bag_only_after_service_request_and_keeps_valid_data(self):
        clubs = self.add_clubs(5)
        _, bag_id = self.store.save_bag("Temporaire", clubs)
        backup = self.store.delete_bag(bag_id)
        self.assertTrue((backup / "bags.json").exists())
        self.assertEqual(self.store.bag_documents(), [])
        self.assertTrue(self.store.validation().valid)

    def test_inventory_assistant_handles_invalid_search_and_unknown_level(self):
        output = []
        assistant = InventoryAssistant(
            self.store,
            AnswerStream(("introuvable", "Cyclotron", "1", "", "x", "46", "0", "50")),
            output.append,
        )
        self.assertTrue(assistant.edit_club())
        rendered = "\n".join(output)
        self.assertIn("Aucun club trouvé", rendered)
        self.assertIn("Saisie invalide", rendered)
        self.assertIsNone(self.store.inventory_documents()[0]["current_level"])

    def test_bag_assistant_prevents_duplicate_selection_by_removing_previous_choices(self):
        self.add_clubs(6)
        output = []
        assistant = BagAssistant(
            self.store,
            AnswerStream(("Sac guidé", "1", "1", "1", "1", "1")),
            output.append,
        )
        self.assertTrue(assistant.create_or_edit())
        clubs = self.store.bag_documents()[0]["club_ids"]
        self.assertEqual(len(clubs), len(set(clubs)))
        self.assertIn("Position 5", "\n".join(output))


class MainMenuTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.user_dir = Path(self.temporary.name) / "user"
        self.store = UserDataStore(self.user_dir, CATALOG)
        self.store.ensure_files()
        self.clubs = ("cyclotron", "high_flight", "ember", "maelstrom", "sunstorm", "steadfast")
        for club_id in self.clubs:
            self.store.save_inventory_entry(
                club_id, current_level=12, cards_owned=0, cards_required=1
            )
        self.store.save_bag("Sac test", self.clubs[:5])
        FakeRecommendation.calls.clear()

    def app(self, answers, output):
        return PgaShootoutAssistant(
            user_dir=self.user_dir,
            catalog_path=CATALOG,
            input_fn=AnswerStream(answers),
            output_fn=output.append,
            recommendation_factory=FakeRecommendation,
        )

    def test_returns_to_main_menu_after_inventory_menu(self):
        output = []
        self.assertEqual(self.app(("2", "5", "6"), output).run(), 0)
        rendered = "\n".join(output)
        self.assertIn("Gestion de mes clubs", rendered)
        self.assertGreaterEqual(rendered.count("Que souhaitez-vous faire ?"), 2)

    def test_uses_existing_recommendation_engine_from_main_menu(self):
        output = []
        self.assertEqual(self.app(("1", "6"), output).run(), 0)
        self.assertEqual(len(FakeRecommendation.calls), 1)
        self.assertIsNone(FakeRecommendation.calls[0]["forced_mode"])
        self.assertIn("Retour au menu principal", "\n".join(output))

    def test_scenario_shortcut_forces_scenario_mode(self):
        output = []
        self.assertEqual(self.app(("5", "6"), output).run(), 0)
        self.assertEqual(FakeRecommendation.calls[0]["forced_mode"], "scenario")

    def test_first_launch_creates_files_and_can_defer_setup(self):
        fresh_dir = Path(self.temporary.name) / "fresh"
        output = []
        app = PgaShootoutAssistant(
            user_dir=fresh_dir,
            catalog_path=CATALOG,
            input_fn=AnswerStream(("2", "6")),
            output_fn=output.append,
            recommendation_factory=FakeRecommendation,
        )
        self.assertEqual(app.run(), 0)
        self.assertEqual({item.name for item in fresh_dir.glob("*.json")}, set(USER_FILENAMES))
        self.assertIn("fichiers personnels manquants", "\n".join(output))

    def test_invalid_existing_data_is_replaced_only_after_confirmation_and_is_backed_up(self):
        invalid = b"not valid json"
        (self.user_dir / "inventory.json").write_bytes(invalid)
        output = []
        app = self.app(("1", "2", "6"), output)
        self.assertEqual(app.run(), 0)
        backups = sorted((self.user_dir / "backups").iterdir())
        inventory_backups = [item / "inventory.json" for item in backups if (item / "inventory.json").exists()]
        self.assertTrue(any(item.read_bytes() == invalid for item in inventory_backups))
        self.assertTrue(UserDataStore(self.user_dir, CATALOG).validation().valid)
        rendered = "\n".join(output)
        self.assertIn("ne peuvent pas être utilisées", rendered)
        self.assertIn("anciens fichiers ont été sauvegardés", rendered)

    def test_complete_first_setup_adds_clubs_creates_bag_runs_recommendation_and_returns(self):
        fresh_dir = Path(self.temporary.name) / "complete-first-run"
        answers = ["1"]
        for name in ("Cyclotron", "High Flight", "Ember", "Maelstrom", "Sunstorm"):
            answers.extend((name, "1", "12", "0", "1"))
        answers.extend(("Mon premier sac", "1", "1", "1", "1", "1", "1", "6"))
        output = []
        app = PgaShootoutAssistant(
            user_dir=fresh_dir,
            catalog_path=CATALOG,
            input_fn=AnswerStream(answers),
            output_fn=output.append,
            recommendation_factory=FakeRecommendation,
        )
        self.assertEqual(app.run(), 0)
        completed = UserDataStore(fresh_dir, CATALOG)
        self.assertEqual(len(completed.owned_inventory()), 5)
        self.assertEqual(len(completed.bag_documents()), 1)
        self.assertTrue(completed.validation().valid)
        self.assertEqual(len(FakeRecommendation.calls), 1)
        rendered = "\n".join(output)
        self.assertIn("Cyclotron a été enregistré", rendered)
        self.assertIn("Mon premier sac", rendered)
        self.assertIn("Analyse de remplacement exécutée", rendered)
        self.assertIn("Retour au menu principal", rendered)

    def test_management_layer_does_not_import_or_reference_rule_engine(self):
        sources = [
            (ROOT / "src" / "pga_shootout" / "user_management.py").read_text(encoding="utf-8"),
            (ROOT / "src" / "pga_shootout" / "main_menu.py").read_text(encoding="utf-8"),
        ]
        self.assertTrue(all("RuleEngine" not in source and "from .engine" not in source for source in sources))

    def test_windows_launcher_contains_all_first_run_safeguards(self):
        launcher = (ROOT / "DEMARRER_PGA_SHOOTOUT.bat").read_text(encoding="utf-8")
        for expected in (
            'cd /d "%~dp0"',
            "sys.version_info >= (3, 11)",
            "-m venv .venv",
            "PYTHONUTF8=1",
            "-m pip install -e .",
            "-m pga_shootout.cli assistant",
            "pause",
        ):
            self.assertIn(expected, launcher)


if __name__ == "__main__":
    unittest.main()
