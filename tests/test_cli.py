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


if __name__ == "__main__":
    unittest.main()
