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


if __name__ == "__main__":
    unittest.main()
