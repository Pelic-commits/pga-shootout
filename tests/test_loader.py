import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.loader import DataLoadError, load_raw_json, summarize_raw_json


class LoaderTests(unittest.TestCase):
    def test_loader_preserves_raw_json(self):
        expected = {"clubs": [{"name": "Example", "levels": [1, 2]}], "brands": 1}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"
            path.write_text(json.dumps(expected), encoding="utf-8")
            self.assertEqual(load_raw_json(path), expected)
        self.assertEqual(
            summarize_raw_json(expected),
            {"root_type": "object", "keys": ["brands", "clubs"], "item_count": 2},
        )

    def test_loader_wraps_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(DataLoadError):
                load_raw_json(path)


if __name__ == "__main__":
    unittest.main()
