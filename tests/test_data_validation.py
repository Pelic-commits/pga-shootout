import copy
import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.data_validation import DataValidationError, validate_official_data
from pga_shootout.loader import load_raw_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "pga_club_stats_extract_v2_2026-07-21.json"
NORMALIZED_PATH = PROJECT_ROOT / "data" / "normalized" / "clubs_official.json"


class OfficialDataValidationTests(unittest.TestCase):
    def test_imported_official_data_matches_manifest_invariants(self):
        report = validate_official_data(RAW_PATH, NORMALIZED_PATH)

        self.assertEqual(report.raw_sha256, "449831121cada54114ac8175af38b99ab8bd6ecf15310600a1df9192ca703a14")
        self.assertEqual(report.normalized_sha256, "76d298789030964a32cd4b047cba2598cc5b647b61a90b13ca962767f3417a85")
        self.assertEqual(report.clubs, 88)
        self.assertEqual(report.brands, 9)
        self.assertEqual(report.ability_occurrences, 162)
        self.assertEqual(report.unique_club_ids, 88)
        self.assertEqual(report.unique_occurrence_ids, 162)
        self.assertEqual(report.converted_ability_values, 1333)

    def test_mismatched_source_hash_is_rejected(self):
        normalized = copy.deepcopy(load_raw_json(NORMALIZED_PATH))
        normalized["source"]["source_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clubs_official.json"
            path.write_text(json.dumps(normalized), encoding="utf-8")
            with self.assertRaisesRegex(DataValidationError, "source_sha256"):
                validate_official_data(RAW_PATH, path)


if __name__ == "__main__":
    unittest.main()
