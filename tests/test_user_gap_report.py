import tempfile
import unittest
from pathlib import Path

from pga_shootout.user_gap_report import (
    ALLOWED_STATUSES,
    analyze_user_gaps,
    generate_user_gap_report,
    render_user_gap_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


class UserGapReportTests(unittest.TestCase):
    def report(self):
        return analyze_user_gaps(
            user_dir=ROOT / "data" / "user",
            normalized_dir=ROOT / "data" / "normalized",
            raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
        )

    def test_every_known_inventory_club_and_official_ability_is_present(self):
        report = self.report()
        self.assertEqual(report.inventory_clubs, 20)
        self.assertEqual(report.ability_occurrences, 35)
        self.assertEqual(len({club.club_id for club in report.clubs}), 20)
        self.assertEqual(
            len({ability.occurrence_id for club in report.clubs for ability in club.abilities}),
            35,
        )

    def test_report_uses_exact_official_text_and_known_bag_membership(self):
        report = self.report()
        cloudcatcher = next(club for club in report.clubs if club.club_id == "cloudcatcher")
        bounce = next(item for item in cloudcatcher.abilities if item.occurrence_id.endswith("bounce_reduction"))
        self.assertEqual(bounce.official_text, "Your ball bounces X% less against all terrain")
        self.assertEqual(bounce.pattern, "static_modifier_targets")
        self.assertEqual(bounce.status, "implemented")
        high_flight = next(club for club in report.clubs if club.club_id == "high_flight")
        self.assertEqual(high_flight.saved_bag_ids, ("par3_high_flight",))

    def test_status_vocabulary_is_closed_and_cyclotron_is_implemented(self):
        report = self.report()
        statuses = {ability.status for club in report.clubs for ability in club.abilities}
        self.assertLessEqual(statuses, ALLOWED_STATUSES)
        cyclotron = next(club for club in report.clubs if club.club_id == "cyclotron")
        bounce = next(item for item in cyclotron.abilities if item.label == "Bounce Reduction Boost")
        self.assertEqual(bounce.status, "implemented")
        self.assertEqual(bounce.pattern, "static_modifier_targets")

    def test_generation_is_reproducible(self):
        report = self.report()
        self.assertEqual(render_user_gap_markdown(report), render_user_gap_markdown(self.report()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "gaps.md"
            generated = generate_user_gap_report(
                output,
                user_dir=ROOT / "data" / "user",
                normalized_dir=ROOT / "data" / "normalized",
                raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
            )
            self.assertEqual(output.read_text(encoding="utf-8"), render_user_gap_markdown(generated))


if __name__ == "__main__":
    unittest.main()
