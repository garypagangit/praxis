import gzip
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


path = Path(__file__).resolve().parents[1] / "scripts" / "defender_telemetry_experiment.py"
spec = importlib.util.spec_from_file_location("defender_telemetry_experiment", path)
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def windows():
    return [
        {"start": start, "end": start + 30,
         "values": {name: 0 for name in experiment.FEATURES["combined"]},
         "covered": set(), "skipped_flow": False}
        for start in (0, 30)
    ]


def write_records(path, records):
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")


class DefenderTelemetryTests(unittest.TestCase):
    def test_windows_event_ids_and_half_open_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "security.jsonl.gz"
            records = [
                {"timestamp": time * 1000, "message": f"<Event><EventID>{event_id}</EventID>"
                 "<CommandLine>not a feature</CommandLine></Event>"}
                for time, event_id in ((0, 4624), (30, 4688), (60, 4624))
            ]
            write_records(path, records)
            samples = windows()
            counts = experiment.windows_stream(path, samples, "dc01", "security")
            self.assertEqual(counts["in_window"], 2)
            self.assertEqual(samples[0]["values"]["security_4624"], 1)
            self.assertEqual(samples[1]["values"]["security_4688"], 1)
            self.assertIn("dc01/security", samples[0]["covered"])
            self.assertNotIn("not a feature", repr(samples))

    def test_flow_uses_end_time_and_excludes_skipdata_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flow.jsonl.gz"
            messages = [
                "2 account eni src dst 1 2 6 3 400 0 30 ACCEPT OK",
                "2 account eni - - - - - - - 29 31 - SKIPDATA",
                "2 account eni - - - - - - - 31 60 - NODATA",
            ]
            write_records(path, [{"message": message} for message in messages])
            samples = windows()
            experiment.flow_stream(path, samples)
            self.assertEqual(samples[0]["values"]["flow_records"], 0)
            self.assertEqual(samples[1]["values"]["flow_records"], 1)
            self.assertEqual(samples[1]["values"]["flow_bytes"], 400)
            self.assertTrue(all(w["skipped_flow"] for w in samples))
            self.assertTrue(all("flow" in w["covered"] for w in samples))

    def test_invalid_in_window_event_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "security.jsonl.gz"
            write_records(path, [{"timestamp": 1000, "message": "unexpected format"}])
            with self.assertRaisesRegex(ValueError, "Cannot parse"):
                experiment.windows_stream(path, windows(), "dc01", "security")

    def test_zero_duration_skipdata_marks_containing_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flow.jsonl.gz"
            write_records(path, [
                {"message": "2 account eni - - - - - - - 0 60 - NODATA"},
                {"message": "2 account eni - - - - - - - 30 30 - SKIPDATA"},
            ])
            samples = windows()
            counts = experiment.flow_stream(path, samples)
            self.assertFalse(samples[0]["skipped_flow"])
            self.assertTrue(samples[1]["skipped_flow"])
            self.assertEqual(counts["zero_duration_skipdata_records"], 1)

    def test_holm_adjustment(self):
        self.assertEqual(experiment.holm([0.03, 0.01, 0.04, 0.5]), [0.09, 0.04, 0.09, 0.5])

    def test_end_to_end_permutation_uses_all_session_labelings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "features.csv"
            columns = ["session", "label", "window"] + list(experiment.FEATURES["combined"])
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
                writer.writeheader()
                for session in range(9):
                    for window in range(3):
                        features = {key: 0 for key in experiment.FEATURES["combined"]}
                        features["security_4624"] = 10 if session < 4 else 0
                        writer.writerow({"session": f"s{session}", "label": "ai" if session < 4 else "human",
                                         "window": str(window), **features})
            manifest = {
                "features_sha256": experiment.sha256(path),
                "script_sha256": experiment.sha256(Path(experiment.__file__)),
                "feature_sets": experiment.FEATURES,
                "total_full_windows": 27, "eligible_windows": 27,
                "eligible_by_class": {"human": 15, "ai": 12},
                "excluded_skipdata": 0, "excluded_missing_coverage": 0,
            }
            (root / "extraction.json").write_text(json.dumps(manifest), encoding="utf-8")
            experiment.evaluate(root, True)
            result = json.loads((root / "results.json").read_text(encoding="utf-8"))
            self.assertIn("0.0079", (root / "RESULTS.md").read_text(encoding="utf-8"))
            self.assertEqual(result["results"]["security"]["macro_f1"], 1.0)
            self.assertEqual(result["results"]["security"]["permutation_p"], 1 / 126)
            for entry in result["results"].values():
                self.assertEqual(entry["permutations"], 126)
                self.assertGreaterEqual(entry["holm_p"], entry["permutation_p"])
                self.assertEqual(len(entry["session_bootstrap_95_interval"]), 2)


if __name__ == "__main__":
    unittest.main()
