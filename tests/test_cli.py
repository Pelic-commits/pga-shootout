import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.cli import main


class CliTests(unittest.TestCase):
    def test_inspect_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"
            path.write_text(json.dumps([{"club": 1}]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["inspect", str(path)])
        self.assertEqual(result, 0)
        self.assertIn('"root_type": "array"', output.getvalue())

    def test_validate_data_cli(self):
        root = Path(__file__).resolve().parents[1]
        raw = root / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json"
        normalized = root / "data" / "normalized" / "clubs_official.json"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["validate-data", str(raw), str(normalized)])
        self.assertEqual(result, 0)
        self.assertIn('"clubs": 88', output.getvalue())

    def test_user_validation_and_reports_cli(self):
        root = Path(__file__).resolve().parents[1]
        common = [
            "--user-dir", str(root / "data" / "user"),
            "--catalog", str(root / "data" / "normalized" / "clubs_official.json"),
        ]
        expected = {
            "user-validate": '"valid": true',
            "user-account": '"player_name": "Pierre"',
            "user-inventory": '"club_id": "homestead"',
            "user-upgrades": '"club_id": "groundskeep"',
            "user-bags": '"par3_divebomb"',
        }
        for command, marker in expected.items():
            with self.subTest(command=command):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = main([command, *common])
                self.assertEqual(result, 0)
                self.assertIn(marker, output.getvalue())

    def test_evaluate_bag_cli_partial_and_strict(self):
        root = Path(__file__).resolve().parents[1]
        common = [
            "evaluate-bag", "par3_divebomb", "--level", "12",
            "--user-dir", str(root / "data" / "user"),
            "--catalog", str(root / "data" / "normalized" / "clubs_official.json"),
        ]
        partial_output = io.StringIO()
        with contextlib.redirect_stdout(partial_output):
            partial_result = main([*common, "--partial"])
        self.assertEqual(partial_result, 0)
        self.assertIn("Divebomb", partial_output.getvalue())
        self.assertIn("Partial mode: SUCCESS", partial_output.getvalue())
        self.assertIn("UNSUPPORTED", partial_output.getvalue())

        strict_output = io.StringIO()
        with contextlib.redirect_stdout(strict_output):
            strict_result = main([*common, "--strict"])
        self.assertEqual(strict_result, 1)
        self.assertIn("Strict mode: FAILED", strict_output.getvalue())

    def test_compare_bags_cli_explains_differences_without_ranking(self):
        root = Path(__file__).resolve().parents[1]
        common = [
            "compare-bags", "par3_divebomb", "par3_high_flight",
            "--level", "12", "--position", "1",
            "--user-dir", str(root / "data" / "user"),
            "--catalog", str(root / "data" / "normalized" / "clubs_official.json"),
        ]
        partial_output = io.StringIO()
        with contextlib.redirect_stdout(partial_output):
            partial_result = main([*common, "--partial"])
        self.assertEqual(partial_result, 0)
        self.assertIn("Bag comparison", partial_output.getvalue())
        self.assertIn("1. Divebomb != High Flight", partial_output.getvalue())
        self.assertIn("No aggregate score", partial_output.getvalue())

        strict_output = io.StringIO()
        with contextlib.redirect_stdout(strict_output):
            strict_result = main([*common, "--strict"])
        self.assertEqual(strict_result, 1)
        self.assertIn("Strict status: FAILED", strict_output.getvalue())

    def test_normalize_cli_regenerates_all_artifacts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "normalize",
                    "--source", str(root / "data" / "normalized" / "clubs_official.json"),
                    "--output-dir", directory,
                ])
            self.assertEqual(result, 0)
            self.assertIn('"occurrences": 162', output.getvalue())
            self.assertEqual(
                {path.name for path in Path(directory).iterdir()},
                {
                    "ability_occurrences.json",
                    "ability_labels.json",
                    "mechanics_catalog.json",
                    "semantic_map.json",
                    "normalization_report.json",
                },
            )

    def test_coverage_cli_regenerates_markdown_report(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "coverage.md"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "coverage",
                    "--normalized-dir", str(root / "data" / "normalized"),
                    "--output", str(report_path),
                ])
            self.assertEqual(result, 0)
            self.assertIn('"total_groups": 125', output.getvalue())
            self.assertIn("# Mechanic Coverage", report_path.read_text(encoding="utf-8"))

    def test_user_gaps_cli_regenerates_inventory_report(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "user-gaps.md"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "user-gaps",
                    "--user-dir", str(root / "data" / "user"),
                    "--normalized-dir", str(root / "data" / "normalized"),
                    "--raw-catalog", str(root / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json"),
                    "--output", str(report_path),
                ])
            self.assertEqual(result, 0)
            self.assertIn('"inventory_clubs": 20', output.getvalue())
            self.assertIn("# User Inventory Ability Gaps", report_path.read_text(encoding="utf-8"))

    def test_reference_gaps_cli_regenerates_saved_bag_matrix(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "reference-gaps.md"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "reference-gaps",
                    "--user-dir", str(root / "data" / "user"),
                    "--normalized-dir", str(root / "data" / "normalized"),
                    "--raw-catalog", str(root / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json"),
                    "--output", str(report_path),
                ])
            self.assertEqual(result, 0)
            self.assertIn('"unique_clubs": 8', output.getvalue())
            self.assertIn("# Reference Bag Ability Matrix", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
