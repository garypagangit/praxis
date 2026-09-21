"""Timer-source integrity checks; never execute fits or timing benchmarks."""
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_benchmark.tabular_batch.audit_e2 import timer_source_check


SOURCE = Path(__file__).resolve().parents[1] / "tabular_batch"


class E2AuditTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((SOURCE / "protocol_e2_latency.json").read_text(encoding="utf-8"))
        self.text = (SOURCE / "run_e2_latency.py").read_text(encoding="utf-8")

    def check_mutation(self, text, expected_message):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.py"
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, expected_message):
                timer_source_check(path, self.protocol)

    def test_actual_bound_timer_source_has_both_real_prediction_blocks(self):
        result = timer_source_check(SOURCE / "run_e2_latency.py", self.protocol)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["prediction_call_lines"]), 2)

    def test_cached_probabilities_cannot_replace_measured_inference(self):
        changed = self.text.replace("np.asarray(models[name].predict_proba(imputer.transform(query)))",
                                    "cached_probabilities")
        self.assertNotEqual(changed, self.text)
        self.check_mutation(changed, "do not call predict_proba")

    def test_transform_outside_measurement_is_rejected(self):
        changed = self.text.replace("models[name].predict_proba(imputer.transform(query))",
                                    "models[name].predict_proba(transformed_query)")
        self.assertNotEqual(changed, self.text)
        self.check_mutation(changed, "no timed transform")

    def test_wrong_elapsed_measurement_is_rejected(self):
        changed = self.text.replace("elapsed = clock() - started", "elapsed = 0.01")
        self.check_mutation(changed, "not followed by timer end")


if __name__ == "__main__":
    unittest.main()
