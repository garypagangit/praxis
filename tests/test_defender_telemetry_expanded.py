import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded


def row(index, label="human", session="s0", amount=1):
    values = {name: 0 for name in base.FEATURES["combined"] + expanded.EXTRA_FEATURES + expanded.BIN_COLUMNS}
    values["security_4624"] = amount
    values["bin_security_0"] = amount
    return {"session": session, "label": label, "window": f"login_{index}", **values}


class ExpandedTelemetryTests(unittest.TestCase):
    def test_aggregation_requires_all_aligned_windows(self):
        data = [row(0), row(1), row(2), row(4), row(5)]
        result = expanded.aggregate(data, 60)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["security_4624"], 2)
        self.assertAlmostEqual(result[0]["security_active_fraction"], 2 / 12)
        self.assertAlmostEqual(result[0]["security_peak_fraction"], 0.5)
        self.assertEqual(len(expanded.aggregate(data, 120)), 0)

    def test_timing_and_extra_event_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.gz"
            records = [
                {"timestamp": t * 1000, "message": f"<Event><EventID>{event}</EventID>"
                 "<CommandLine>not a feature</CommandLine></Event>"}
                for t, event in ((0, 100), (5, 999), (30, 100))
            ]
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                for record in records:
                    stream.write(json.dumps(record) + "\n")
            windows = [{"start": 0, "end": 30,
                        "extra": {name: 0 for name in expanded.EXTRA_FEATURES + expanded.BIN_COLUMNS}}]
            self.assertEqual(expanded.timing_stream(path, windows, "extra", extra_channel="tasks"), 2)
            self.assertEqual(windows[0]["extra"]["tasks_100"], 1)
            self.assertEqual(windows[0]["extra"]["tasks_other"], 1)
            self.assertEqual(windows[0]["extra"]["bin_extra_0"], 1)
            self.assertEqual(windows[0]["extra"]["bin_extra_1"], 1)
            self.assertNotIn("not a feature", repr(windows))

    def test_models_with_and_without_training_fold_smote(self):
        data = []
        for s in range(9):
            for i in range(3 if s < 4 else 6):
                data.append(row(i, "ai" if s < 4 else "human", f"s{s}", 10 if s < 4 else 0))
        data = expanded.aggregate(data, 30)
        ai = tuple(f"s{i}" for i in range(4))
        for model, smote in (("logistic", False), ("xgboost", False), ("xgboost", True)):
            score, predictions, probabilities = expanded.model_score(
                data, ("security_4624",), ai, model, smote
            )
            self.assertGreater(score, 0.9)
            self.assertEqual(len(predictions), len(data))
            self.assertEqual(len(probabilities), len(data))


if __name__ == "__main__":
    unittest.main()
