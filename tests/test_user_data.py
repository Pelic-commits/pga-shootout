import dataclasses
import unittest
from pathlib import Path

from pga_shootout.user_data import (
    ClubCatalogIndex,
    Inventory,
    InventoryEntry,
    UserDataBundle,
    load_user_data,
    serialize_stable,
    validate_user_data,
)


ROOT = Path(__file__).resolve().parents[1]
USER_DIR = ROOT / "data" / "user"
CATALOG_PATH = ROOT / "data" / "normalized" / "clubs_official.json"


class UserDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_user_data(USER_DIR)
        cls.catalog = ClubCatalogIndex.load(CATALOG_PATH)
        cls.report = validate_user_data(cls.bundle, cls.catalog)

    def test_loads_all_five_user_files(self):
        self.assertEqual(self.bundle.account.player_name, "Pierre")
        self.assertEqual(len(self.bundle.inventory.entries), 20)
        self.assertEqual(len(self.bundle.preferences.priorities), 7)
        self.assertEqual(len(self.bundle.bags), 2)
        self.assertEqual(len(self.bundle.observations), 10)

    def test_all_official_club_references_resolve(self):
        self.assertTrue(self.report.valid)
        self.assertEqual(self.report.unknown_references, ())
        self.assertEqual(self.catalog.resolve("Neon Impulse"), "neon_impulse")
        self.assertEqual(self.catalog.resolve("meteor"), "meteor")

    def test_inventory_is_partial_and_absence_does_not_mean_locked(self):
        self.assertFalse(self.bundle.inventory.inventory_complete)
        self.assertIsNone(self.bundle.inventory.get("meteor"))

    def test_unknown_levels_remain_none(self):
        self.assertTrue(all(entry.current_level is None for entry in self.bundle.inventory.entries))

    def test_upgrade_availability_is_calculated(self):
        self.assertEqual(
            self.report.upgrade_available,
            ("groundskeep", "sandsend", "neon_impulse", "rook", "mirage", "green_demon", "outset", "conqueror"),
        )

    def test_saved_bags_have_five_clubs_and_preserve_order(self):
        self.assertTrue(all(len(bag.club_ids) == 5 for bag in self.bundle.bags))
        self.assertEqual(
            self.bundle.bags[0].club_ids,
            ("divebomb", "jumpstart", "steadfast", "ember", "sunstorm"),
        )
        self.assertEqual(
            self.bundle.bags[1].club_ids,
            ("high_flight", "cyclotron", "ember", "maelstrom", "sunstorm"),
        )

    def test_preferences_have_no_invented_numeric_weights(self):
        self.assertTrue(all(item.weight is None for item in self.bundle.preferences.priorities))

    def test_unresolved_observation_is_preserved(self):
        unresolved = [item for item in self.bundle.observations if item.status == "unresolved_note"]
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0].unresolved_reference, "un sand wedge PALO")
        self.assertEqual(unresolved[0].club_ids, ())

    def test_duplicate_and_unknown_inventory_references_are_reported(self):
        original = self.bundle.inventory.entries[0]
        unknown = InventoryEntry(
            club_id="not_a_club",
            display_name="Unknown",
            unlocked=True,
            current_level=None,
            cards_owned=0,
            cards_required_for_next_upgrade=1,
            observed_at="2026-07-21",
            source="test",
        )
        inventory = Inventory(False, "2026-07-21", "test", (*self.bundle.inventory.entries, original, unknown))
        changed = dataclasses.replace(self.bundle, inventory=inventory)
        report = validate_user_data(changed, self.catalog)
        self.assertFalse(report.valid)
        self.assertEqual(report.duplicate_references, ("homestead",))
        self.assertEqual(report.unknown_references, ("not_a_club",))

    def test_serialization_is_stable(self):
        self.assertEqual(serialize_stable(self.report), serialize_stable(self.report))
        self.assertTrue(serialize_stable(self.report).endswith("\n"))


if __name__ == "__main__":
    unittest.main()
