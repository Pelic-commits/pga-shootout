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
            user_dir=ROOT / "data" / "pga_shootout.sqlite",
            normalized_dir=ROOT / "data" / "normalized",
            raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
        )

    def test_totals_are_derived_and_inventory_is_distinct_from_catalog(self):
        report = self.report()
        self.assertEqual(report.inventory_clubs, 75)
        self.assertEqual(report.baseline_inventory_clubs, 21)
        self.assertEqual(len(report.newly_added_club_names), 54)
        self.assertFalse(report.inventory_complete)
        self.assertEqual(report.official_abilities, 138)
        self.assertEqual(report.simulated_abilities, 56)
        self.assertEqual(report.unresolved_abilities, 82)
        self.assertEqual(report.fully_simulated_clubs, 25)
        self.assertEqual(report.known_user_levels, 72)
        self.assertEqual(
            (report.fully_comparable_clubs, report.warning_comparable_clubs, report.non_comparable_clubs),
            (24, 14, 37),
        )
        self.assertEqual((report.global_clubs, report.global_abilities), (88, 162))
        self.assertEqual((report.global_simulated_groups, report.global_simulated_abilities), (35, 57))
        self.assertEqual(report.global_simulated_clubs, 39)

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
        self.assertEqual(abilities["homestead__brand_loyalty_x"].status, "simulated_no_effect_in_current_bag")
        self.assertTrue(abilities["homestead__brand_loyalty_x"].engine_supported)
        self.assertEqual(abilities["high_flight__wind_resist_75"].status, "simulated")
        self.assertEqual(abilities["kinship__chains_into_willoughsby"].status, "simulated_no_effect_in_current_bag")
        self.assertEqual(abilities["neon_impulse__power_shot"].status, "physics_required")
        self.assertEqual(abilities["cyclotron__bounce_reduction_boost"].status, "simulated")
        self.assertEqual(abilities["blacksmith__texas_tee"].status, "simple_context_required")
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
        self.assertEqual(
            abilities["rook__bag_wind_resist"].metrics,
            ("wind_resistance_percent",),
        )
        self.assertEqual(
            abilities["kinship__chains_into_willoughsby"].metrics,
            ("control", "power", "spin"),
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
        self.assertEqual(coverage["par3_divebomb"], (6, 8))
        self.assertEqual(coverage["par3_high_flight"], (8, 9))

    def test_recommendations_are_inventory_driven_and_exclude_meteor(self):
        report = self.report()
        self.assertEqual(len(report.next_lots), 3)
        self.assertEqual(
            tuple(item.identifier for item in report.next_lots),
            ("wind_resistance", "chains", "terrain_conditions"),
        )
        self.assertNotIn("meteor", {club_id for lot in report.next_lots for club_id in lot.club_ids})
        self.assertEqual(tuple(item.expected_ability_gain for item in report.next_lots), (7, 4, 13))

    def test_real_inventory_eligibility_and_texas_tee_are_explainable(self):
        report = self.report()
        clubs = {club.club_id: club for club in report.clubs}
        blacksmith = clubs["blacksmith"]
        self.assertEqual(blacksmith.current_level, 9)
        self.assertTrue(blacksmith.fully_simulated)
        self.assertEqual(blacksmith.comparison_eligibility, "comparable_with_warning")
        self.assertEqual(blacksmith.eligibility_reasons, ("blacksmith__texas_tee:context:terrain",))
        texas = blacksmith.abilities[0]
        self.assertEqual(texas.metrics, ("power",))
        self.assertEqual(texas.importance, "high")
        self.assertEqual(texas.reusable_primitives, ("SELECT_SELF", "READ_LEVEL_VALUE", "ADD_STAT"))
        self.assertIsNone(texas.required_primitive)
        self.assertEqual(
            texas.similar_occurrence_ids,
            ("sidewinder__tee_off_power", "blacksmith__texas_tee"),
        )
        self.assertEqual(clubs["pantheon"].comparison_eligibility, "not_comparable")

    def test_human_json_and_markdown_outputs_are_stable(self):
        first = self.report()
        second = self.report()
        self.assertEqual(render_inventory_status(first), render_inventory_status(second))
        self.assertEqual(render_inventory_json(first), render_inventory_json(second))
        self.assertEqual(render_inventory_markdown(first), render_inventory_markdown(second))
        self.assertEqual(render_project_status_markdown(first), render_project_status_markdown(second))
        payload = json.loads(render_inventory_json(first))
        self.assertEqual(payload["inventory_clubs"], 75)
        self.assertEqual(len(payload["clubs"]), 75)

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
