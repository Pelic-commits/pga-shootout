import json
import tempfile
import unittest
from pathlib import Path

from pga_shootout.normalization import OUTPUT_FILENAMES, normalize_catalog


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "normalized" / "clubs_official.json"
NORMALIZED = ROOT / "data" / "normalized"


class NormalizationPipelineTests(unittest.TestCase):
    def test_every_official_ability_is_represented_without_payload_loss(self):
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        generated = json.loads((NORMALIZED / "ability_occurrences.json").read_text(encoding="utf-8"))
        source_abilities = {
            ability["occurrence_id"]: ability
            for club in source["clubs"].values()
            for ability in club["abilities"]
        }

        self.assertEqual(len(source_abilities), 162)
        self.assertEqual(set(generated["occurrences"]), set(source_abilities))
        for occurrence_id, ability in source_abilities.items():
            self.assertEqual(generated["occurrences"][occurrence_id]["official_payload"], ability)

    def test_exact_label_grouping_covers_each_occurrence_once(self):
        occurrences = json.loads((NORMALIZED / "ability_occurrences.json").read_text(encoding="utf-8"))
        labels = json.loads((NORMALIZED / "ability_labels.json").read_text(encoding="utf-8"))
        grouped = [occurrence_id for label in labels["labels"].values() for occurrence_id in label["occurrence_ids"]]

        self.assertEqual(len(labels["labels"]), 125)
        self.assertEqual(len(grouped), 162)
        self.assertEqual(set(grouped), set(occurrences["occurrences"]))

    def test_only_explicitly_qualified_groups_have_interpretations(self):
        catalog = json.loads((NORMALIZED / "mechanics_catalog.json").read_text(encoding="utf-8"))
        semantic = json.loads((NORMALIZED / "semantic_map.json").read_text(encoding="utf-8"))

        self.assertEqual(len(catalog["groups"]), 125)
        self.assertTrue(all(group["mechanic_id"] is None for group in catalog["groups"].values()))
        qualified_ids = {
            "label:adjacent_power",
            "label:alloy",
            "label:bag_control",
            "label:bag_spin_bonus",
            "label:brand_loyalty",
            "label:brand_loyalty_x",
            "label:control_boost",
            "label:driver_loyalty",
            "label:forester_power",
            "label:nautilus_boost",
            "label:phoenix_power",
            "label:power_boost",
            "label:spin_boost",
            "label:stanchion_power",
        }
        for group_id in qualified_ids:
            qualified = semantic["entries"][group_id]
            self.assertEqual(qualified["mechanic_id"], "dsl_pipeline")
            self.assertEqual(qualified["complexity"], "parameterized")
        placeholders = [entry for group_id, entry in semantic["entries"].items() if group_id not in qualified_ids]
        self.assertTrue(all(entry["complexity"] is None for entry in placeholders))
        self.assertTrue(all(entry["dependencies"] is None for entry in placeholders))

    def test_regeneration_preserves_existing_semantic_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            normalize_catalog(SOURCE, target)
            semantic_path = target / "semantic_map.json"
            semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
            group_id = next(iter(semantic["entries"]))
            semantic["entries"][group_id].update(
                mechanic_id="example_pipeline",
                complexity="parameterized",
                dependencies=["ordered_bag"],
                program={"version": "test", "nodes": []},
            )
            semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

            normalize_catalog(SOURCE, target)
            regenerated = json.loads(semantic_path.read_text(encoding="utf-8"))

        self.assertEqual(regenerated["entries"][group_id]["mechanic_id"], "example_pipeline")
        self.assertEqual(regenerated["entries"][group_id]["program"], {"version": "test", "nodes": []})

    def test_regeneration_preserves_declarative_pattern_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            normalize_catalog(SOURCE, target)
            semantic_path = target / "semantic_map.json"
            semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
            semantic["patterns"]["fixture"] = {
                "program": {"version": "test", "nodes": []},
                "parameters": ["stat"],
            }
            semantic_path.write_text(json.dumps(semantic), encoding="utf-8")

            normalize_catalog(SOURCE, target)
            regenerated = json.loads(semantic_path.read_text(encoding="utf-8"))

        self.assertEqual(regenerated["patterns"], semantic["patterns"])

    def test_report_counts_are_reproducible(self):
        report = json.loads((NORMALIZED / "normalization_report.json").read_text(encoding="utf-8"))
        self.assertEqual(
            report["counts"],
            {
                "ability_occurrences": 162,
                "clubs": 88,
                "converted_level_values": 1333,
                "labels_shared_by_multiple_occurrences": 11,
                "structural_groups": 125,
                "unique_label_ids": 125,
            },
        )
        self.assertEqual(report["ambiguities"], [])
        self.assertTrue(report["integrity"]["all_groups_uninterpreted"])

    def test_regeneration_is_byte_for_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_summary = normalize_catalog(SOURCE, first)
            second_summary = normalize_catalog(SOURCE, second)
            self.assertEqual(first_summary, second_summary)
            for filename in OUTPUT_FILENAMES:
                self.assertEqual((Path(first) / filename).read_bytes(), (Path(second) / filename).read_bytes())


if __name__ == "__main__":
    unittest.main()
