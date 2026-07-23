import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.inventory_status import (
    ABILITY_STATUSES,
    analyze_inventory_status,
    render_inventory_json,
    render_inventory_markdown,
    render_inventory_status,
    render_project_status_markdown,
    write_inventory_reports,
)


ROOT = Path(__file__).resolve().parents[1]


class InventoryStatusTests(unittest.TestCase):
    def report(self):
        return analyze_inventory_status(
            user_dir=ROOT / "data" / "user",
            normalized_dir=ROOT / "data" / "normalized",
            raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
        )

    def test_totals_are_derived_and_inventory_is_distinct_from_catalog(self):
        report = self.report()
        self.assertEqual(report.inventory_clubs, 20)
        self.assertFalse(report.inventory_complete)
        self.assertEqual(report.official_abilities, 35)
        self.assertEqual(report.simulated_abilities, 23)
        self.assertEqual(report.unresolved_abilities, 12)
        self.assertEqual(report.fully_simulated_clubs, 10)
        self.assertEqual(report.known_user_levels, 0)
        self.assertEqual((report.global_clubs, report.global_abilities), (88, 162))
        self.assertEqual((report.global_simulated_groups, report.global_simulated_abilities), (28, 48))

    def test_every_owned_ability_occurs_exactly_once(self):
        report = self.report()
        occurrence_ids = [ability.occurrence_id for club in report.clubs for ability in club.abilities]
        self.assertEqual(len(occurrence_ids), report.official_abilities)
        self.assertEqual(len(set(occurrence_ids)), report.official_abilities)
        self.assertEqual(sum(club.official_abilities for club in report.clubs), report.official_abilities)
        self.assertEqual(sum(club.simulated_abilities for club in report.clubs), report.simulated_abilities)

    def test_statuses_distinguish_level_context_history_physics_and_ambiguity(self):
        report = self.report()
        abilities = {
            ability.occurrence_id: ability
            for club in report.clubs
            for ability in club.abilities
        }
        self.assertEqual(abilities["homestead__brand_loyalty_x"].status, "missing_user_level")
        self.assertTrue(abilities["homestead__brand_loyalty_x"].engine_supported)
        self.assertEqual(abilities["high_flight__wind_resist_75"].status, "scenario_required")
        self.assertEqual(abilities["kinship__chains_into_willoughsby"].status, "history_required")
        self.assertEqual(abilities["neon_impulse__power_shot"].status, "physics_required")
        self.assertEqual(abilities["cyclotron__bounce_reduction_boost"].status, "missing_user_level")
        self.assertLessEqual({ability.status for ability in abilities.values()}, ABILITY_STATUSES)

    def test_supported_metrics_are_exposed_from_declarative_programs(self):
        report = self.report()
        abilities = {
            ability.occurrence_id: ability
            for club in report.clubs
            for ability in club.abilities
        }
        self.assertEqual(abilities["homestead__brand_loyalty_x"].metrics, ("power",))
        self.assertEqual(
            abilities["steadfast__bag_rarity_boost"].metrics,
            ("control", "power", "spin"),
        )
        self.assertEqual(
            abilities["into_the_breach__bag_recklessness"].metrics,
            ("control", "power", "spin"),
        )
        self.assertEqual(
            abilities["cloudcatcher__bounce_reduction"].metrics,
            ("bounce_reduction_percent",),
        )
        self.assertEqual(
            abilities["lodestar__fade_draw_x2"].metrics,
            ("fade_draw_multiplier",),
        )

    def test_current_incomplete_inventory_is_supported_without_treating_absence_as_locked(self):
        report = self.report()
        self.assertFalse(report.inventory_complete)
        self.assertNotIn("meteor", {club.club_id for club in report.clubs})
        self.assertEqual(report.inventory_clubs, len(report.clubs))

    def test_reference_bags_remain_secondary_regression_measurements(self):
        report = self.report()
        coverage = {
            item.bag_id: (item.simulated_abilities, item.official_abilities)
            for item in report.reference_bags
        }
        self.assertEqual(coverage["par3_divebomb"], (5, 8))
        self.assertEqual(coverage["par3_high_flight"], (7, 9))

    def test_recommendations_are_inventory_driven_and_exclude_meteor(self):
        report = self.report()
        self.assertEqual(len(report.next_lots), 3)
        self.assertEqual(
            tuple(item.identifier for item in report.next_lots),
            ("wind_resistance", "chains", "terrain_conditions"),
        )
        self.assertNotIn("meteor", {club_id for lot in report.next_lots for club_id in lot.club_ids})
        self.assertEqual(tuple(item.expected_ability_gain for item in report.next_lots), (2, 3, 2))

    def test_human_json_and_markdown_outputs_are_stable(self):
        first = self.report()
        second = self.report()
        self.assertEqual(render_inventory_status(first), render_inventory_status(second))
        self.assertEqual(render_inventory_json(first), render_inventory_json(second))
        self.assertEqual(render_inventory_markdown(first), render_inventory_markdown(second))
        self.assertEqual(render_project_status_markdown(first), render_project_status_markdown(second))
        payload = json.loads(render_inventory_json(first))
        self.assertEqual(payload["inventory_clubs"], 20)
        self.assertEqual(len(payload["clubs"]), 20)

    def test_written_reports_share_the_same_audit(self):
        report = self.report()
        self.assertEqual(
            (ROOT / "docs" / "INVENTORY_STATUS.md").read_text(encoding="utf-8"),
            render_inventory_markdown(report),
        )
        self.assertEqual(
            (ROOT / "docs" / "PROJECT_STATUS.md").read_text(encoding="utf-8"),
            render_project_status_markdown(report),
        )
        with tempfile.TemporaryDirectory() as directory:
            inventory_path = Path(directory) / "inventory.md"
            project_path = Path(directory) / "project.md"
            write_inventory_reports(report, inventory_path, project_path)
            self.assertEqual(inventory_path.read_text(encoding="utf-8"), render_inventory_markdown(report))
            self.assertEqual(project_path.read_text(encoding="utf-8"), render_project_status_markdown(report))


if __name__ == "__main__":
    unittest.main()
