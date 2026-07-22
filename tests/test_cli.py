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


if __name__ == "__main__":
    unittest.main()
