import tempfile
import unittest
from pathlib import Path

from pga_shootout.reference_gap_report import (
    REFERENCE_STATUSES,
    analyze_reference_gaps,
    generate_reference_gap_report,
    render_reference_gap_markdown,
)


ROOT = Path(__file__).resolve().parents[1]


class ReferenceGapReportTests(unittest.TestCase):
    def report(self):
        return analyze_reference_gaps(
            user_dir=ROOT / "data" / "user",
            normalized_dir=ROOT / "data" / "normalized",
            raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
        )

    def test_matrix_contains_every_unique_reference_club_and_ability(self):
        report = self.report()
        self.assertEqual(report.unique_clubs, 8)
        self.assertEqual(report.unique_ability_occurrences, 14)
        self.assertEqual(len({item.club_id for item in report.abilities}), 8)
        self.assertEqual(len({item.occurrence_id for item in report.abilities}), 14)
        self.assertTrue(all(item.official_text for item in report.abilities))
        self.assertTrue(all(item.user_level is None for item in report.abilities))
        self.assertLessEqual({item.status for item in report.abilities}, REFERENCE_STATUSES)

    def test_coverage_is_computed_from_saved_bags(self):
        coverage = {item.bag_id: item for item in self.report().bag_coverage}
        self.assertEqual((coverage["par3_divebomb"].implemented_occurrences, coverage["par3_divebomb"].ability_occurrences), (5, 8))
        self.assertEqual((coverage["par3_high_flight"].implemented_occurrences, coverage["par3_high_flight"].ability_occurrences), (6, 9))
        self.assertEqual(coverage["par3_high_flight"].coverage_percent, 66.67)

    def test_exact_maelstrom_text_is_implemented_but_cyclotron_remains_ambiguous(self):
        abilities = {item.occurrence_id: item for item in self.report().abilities}
        maelstrom = abilities["maelstrom__bag_bounce_reduction"]
        self.assertEqual(maelstrom.official_text, "Shots from Drivers, Woods, and Hybrids bounce X% less.")
        self.assertEqual(maelstrom.normalized_pattern, "filtered_static_modifier_targets")
        self.assertEqual(maelstrom.status, "implemented")
        self.assertEqual(maelstrom.confidence, "high")
        self.assertEqual(abilities["cyclotron__bounce_reduction_boost"].status, "ambiguous")
        self.assertEqual(abilities["sunstorm__plasma_arc_x"].normalized_pattern, "unique_farthest_multi_stat_bonus")
        self.assertEqual(abilities["sunstorm__plasma_arc_x"].status, "implemented")

    def test_report_generation_is_reproducible(self):
        expected = render_reference_gap_markdown(self.report())
        self.assertEqual(expected, render_reference_gap_markdown(self.report()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reference.md"
            generated = generate_reference_gap_report(
                output,
                user_dir=ROOT / "data" / "user",
                normalized_dir=ROOT / "data" / "normalized",
                raw_catalog_path=ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json",
            )
            self.assertEqual(output.read_text(encoding="utf-8"), render_reference_gap_markdown(generated))


if __name__ == "__main__":
    unittest.main()
