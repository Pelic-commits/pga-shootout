import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pga_shootout.coverage import analyze_coverage, generate_coverage_report, render_coverage_markdown


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "data" / "normalized"
REPORT_PATH = ROOT / "docs" / "MECHANIC_COVERAGE.md"


class MechanicCoverageTests(unittest.TestCase):
    def test_report_covers_every_group_and_occurrence(self):
        report = analyze_coverage(NORMALIZED)
        occurrences = json.loads((NORMALIZED / "ability_occurrences.json").read_text(encoding="utf-8"))["occurrences"]
        groups = json.loads((NORMALIZED / "mechanics_catalog.json").read_text(encoding="utf-8"))["groups"]

        self.assertEqual(report.total_groups, len(groups))
        self.assertEqual(len(report.groups), len(groups))
        self.assertEqual({group.group_id for group in report.groups}, set(groups))
        self.assertEqual(sum(group.occurrences for group in report.groups), len(occurrences))
        self.assertEqual(report.total_groups, 125)
        self.assertEqual(report.total_occurrences, 162)

    def test_current_coverage_reflects_qualified_pipelines(self):
        report = analyze_coverage(NORMALIZED)
        self.assertEqual(report.registered_handlers, ("add_stat", "add_all_stats", "dsl_pipeline"))
        self.assertEqual(report.implemented_groups, 25)
        self.assertEqual(report.occurrence_coverage_percent, 27.78)
        self.assertEqual(report.club_coverage_percent, 37.5)
        self.assertEqual(report.unclassified_groups, 100)

    def test_ranking_is_reproducible_and_uses_real_gain(self):
        first = analyze_coverage(NORMALIZED)
        second = analyze_coverage(NORMALIZED)
        self.assertEqual(first, second)
        self.assertEqual(first.groups[0].source_label_id, "terrain_resist_50")
        implemented = {
            group.source_label_id: group
            for group in first.groups
            if group.source_label_id in {"brand_loyalty", "brand_loyalty_x"}
        }
        self.assertEqual(set(implemented), {"brand_loyalty", "brand_loyalty_x"})
        self.assertTrue(all(group.handler_exists for group in implemented.values()))
        self.assertTrue(all(group.estimated_gain_occurrences == 0 for group in implemented.values()))

    def test_handler_detection_comes_from_semantic_map_and_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for filename in (
                "ability_occurrences.json",
                "ability_labels.json",
                "mechanics_catalog.json",
                "semantic_map.json",
            ):
                shutil.copyfile(NORMALIZED / filename, target / filename)
            semantic_path = target / "semantic_map.json"
            semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
            first_group_id = next(iter(semantic["entries"]))
            semantic["entries"][first_group_id].update(
                mechanic_id="add_stat",
                complexity="generic",
                dependencies=[],
                interpretation_status="validated",
            )
            semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

            report = analyze_coverage(target, handler_names=("add_stat",))

        implemented = [group for group in report.groups if group.handler_exists]
        self.assertEqual(len(implemented), 1)
        self.assertEqual(implemented[0].mechanic_id, "add_stat")
        self.assertEqual(implemented[0].coverage_percent, 100.0)

    def test_markdown_generation_is_byte_reproducible(self):
        expected = render_coverage_markdown(analyze_coverage(NORMALIZED))
        self.assertEqual(REPORT_PATH.read_text(encoding="utf-8"), expected)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.md"
            second = Path(directory) / "second.md"
            generate_coverage_report(NORMALIZED, first)
            generate_coverage_report(NORMALIZED, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
