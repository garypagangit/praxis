import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_px056_model_registry_extractor_pilot.py"
CONFIG_PATH = REPO_ROOT / "configs" / "px056_model_registry_extractor_pilot_20260721.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("px056_extractor_pilot", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def expected_set(fixture):
    return {
        (item["registry"], item["kind"], item["identifier"])
        for item in fixture.get("expected", [])
    }


def observed_set(records):
    return {
        (record["registry"], record["kind"], record["identifier"])
        for record in records
    }


class Px056ExtractorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_fixture_extraction_contract(self):
        for fixture in self.config["fixtures"]:
            with self.subTest(fixture=fixture["id"]):
                records = self.runner.extract_identifiers(fixture["text"], fixture["id"])
                self.assertEqual(observed_set(records), expected_set(fixture))

    def test_json_field_extraction(self):
        text = '{"pretrained_model_name_or_path": "google-bert/bert-base-uncased", "dataset_name": "squad"}'
        records = self.runner.extract_identifiers(text, "json_two_fields")

        self.assertEqual(
            observed_set(records),
            {
                ("hf", "model", "google-bert/bert-base-uncased"),
                ("hf", "dataset", "squad"),
            },
        )

    def test_local_and_malformed_exclusions(self):
        text = "\n".join(
            [
                'AutoModel.from_pretrained("./checkpoints/latest")',
                'AutoModel.from_pretrained("not/a/valid/too-deep")',
                "model_id: C:\\models\\local-policy",
            ]
        )

        self.assertEqual(self.runner.extract_identifiers(text, "nulls"), [])


if __name__ == "__main__":
    unittest.main()
