"""Temporary synthetic review fixtures only; no actual human review is claimed."""
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.cert_gate.score_review import run


class ReviewValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic_review_test_")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.key_path = self.directory / "fixture_key.json"
        self.response_path = self.directory / "fixture_responses.json"
        self.output = self.directory / "fixture_result.json"
        self.key = {f"fixture-case-{i:02d}": "Attack" for i in range(50)}

    def submission(self, agreements=45, unable=0):
        answers = []
        for i, case_id in enumerate(self.key):
            decision = ("Attack" if i < agreements else
                        "Unable to verify" if i < agreements + unable else "Non-Attack")
            answers.append({"case_id": case_id, "decision": decision,
                            "reason": "SYNTHETIC TEST RESPONSE - no human review"})
        return {"reviewer": "SYNTHETIC TEST FIXTURE", "responses": answers}

    def write(self, key, submission):
        self.key_path.write_text(json.dumps(key), encoding="utf-8")
        self.response_path.write_text(json.dumps(submission), encoding="utf-8")

    def score(self):
        with redirect_stdout(io.StringIO()):
            run(self.key_path, self.response_path, self.output)
        return json.loads(self.output.read_text(encoding="utf-8"))

    def test_point_gate_threshold_and_hashes_use_actual_input_bytes(self):
        for agreements, expected in [(44, False), (45, True)]:
            with self.subTest(agreements=agreements):
                self.output = self.directory / f"fixture_result_{agreements}.json"
                self.write(self.key, self.submission(agreements))
                result = self.score()
                self.assertEqual(result["agreements"], agreements)
                self.assertEqual(result["label_agreement_point_gate_pass"], expected)
                self.assertEqual(result["agreement"], agreements / 50)
                self.assertEqual(result["answer_key_file_sha256"],
                                 hashlib.sha256(self.key_path.read_bytes()).hexdigest())
                self.assertEqual(result["response_file_sha256"],
                                 hashlib.sha256(self.response_path.read_bytes()).hexdigest())
                self.assertEqual(result["status"], "SUBMITTED_REVIEW_SCORED_NOT_FULL_G0_APPROVAL")

    def test_unable_to_verify_remains_in_denominator(self):
        self.write(self.key, self.submission(45, unable=3))
        result = self.score()
        self.assertEqual(result["unable_to_verify"], 3)
        self.assertEqual(result["responses"], 50)
        self.assertEqual(result["agreement"], .9)
        self.assertLess(result["agreement_exact_95pct_interval"][0], .9)

    def test_invalid_keys_submissions_and_duplicate_ids_are_rejected(self):
        base = self.submission()
        variants = []
        bad_key = dict(self.key)
        bad_key["fixture-case-00"] = "Unable to verify"
        variants.append((bad_key, base))
        variants.append((dict(list(self.key.items())[:-1]), base))
        for field, value in [("reviewer", " "), ("responses", []), ("responses", {})]:
            variants.append((self.key, {**base, field: value}))
        for field, value in [("case_id", "fixture-case-01"), ("case_id", "unknown-case"),
                             ("case_id", []), ("decision", "Maybe"),
                             ("decision", []), ("reason", " ")]:
            changed = copy.deepcopy(base)
            changed["responses"][0][field] = value
            variants.append((self.key, changed))
        variants.append((self.key, []))
        for i, (key, submission) in enumerate(variants):
            with self.subTest(variant=i):
                self.write(key, submission)
                with self.assertRaises(ValueError):
                    self.score()
                self.assertFalse(self.output.exists())

    def test_duplicate_json_key_cannot_silently_change_the_answer_key(self):
        self.write(self.key, self.submission())
        duplicated = json.dumps(self.key)[:-1] + ',"fixture-case-00":"Non-Attack"}'
        self.key_path.write_text(duplicated, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            self.score()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        self.write(self.key, self.submission())
        original = b"existing fixture output must survive"
        self.output.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.score()
        self.assertEqual(self.output.read_bytes(), original)

    def test_validation_remains_active_under_python_optimization(self):
        self.write(self.key, self.submission())
        submission = self.submission()
        submission["responses"].pop()
        self.response_path.write_text(json.dumps(submission), encoding="utf-8")
        module = Path(__file__).resolve().parents[1] / "score_review.py"
        completed = subprocess.run(
            [sys.executable, "-O", str(module), "--answer-key", str(self.key_path),
             "--responses", str(self.response_path), "--output", str(self.output)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ValueError", completed.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
