"""Synthetic unit tests only; never read or create scientific run outcomes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import analyze_external as analysis


class PolicyArithmeticTests(unittest.TestCase):
    def setUp(self):
        # Columns are Llama/Qwen. The first condition helps one question and
        # harms another for each model; routing trades these off differently.
        self.base = np.array([[False, True], [True, False], [True, True], [False, False]])
        self.evidence = np.array([[True, True], [False, True], [True, False], [False, False]])
        self.weights = np.repeat(np.full((1, 4), .25), 20, axis=0)

    def test_route_reconstructs_accuracy_and_discordant_cases(self):
        result = analysis.summarize_policy(self.base, self.evidence,
                                           np.array([True, False, True, False]), self.weights)
        self.assertEqual(result["evidence_use_n"], 2)
        self.assertEqual(result["evidence_use_pct"], 50)
        llama, qwen = result["models"]["llama"], result["models"]["qwen"]
        self.assertEqual((llama["correct"], llama["accuracy_pct"], llama["delta_vs_vanilla_pp"]), (3, 75, 25))
        self.assertEqual((llama["recovered_answers"], llama["induced_errors"], llama["prevented_errors"], llama["lost_improvements"]), (1, 0, 1, 0))
        self.assertEqual((qwen["correct"], qwen["accuracy_pct"], qwen["delta_vs_vanilla_pp"]), (1, 25, -25))
        self.assertEqual((qwen["recovered_answers"], qwen["induced_errors"], qwen["prevented_errors"], qwen["lost_improvements"]), (0, 1, 0, 1))
        self.assertEqual(result["mean_delta_vs_vanilla_pp"], 0)
        np.testing.assert_allclose(result["mean_delta_ci95_pp"], [0, 0])

    def test_never_evidence_preserves_baseline_and_counts_lost_benefits(self):
        result = analysis.summarize_policy(self.base, self.evidence, np.zeros(4, bool), self.weights)
        self.assertEqual(result["evidence_use_n"], 0)
        for model in result["models"].values():
            self.assertEqual((model["correct"], model["delta_vs_vanilla_pp"]), (2, 0))
            self.assertEqual((model["recovered_answers"], model["induced_errors"], model["prevented_errors"], model["lost_improvements"]), (0, 0, 1, 1))

    def test_always_evidence_net_zero_does_not_hide_one_harm_and_one_recovery(self):
        result = analysis.summarize_policy(self.base, self.evidence, np.ones(4, bool), self.weights)
        self.assertEqual(result["evidence_use_n"], 4)
        for model in result["models"].values():
            self.assertEqual(model["delta_vs_vanilla_pp"], 0)
            self.assertEqual((model["recovered_answers"], model["induced_errors"], model["prevented_errors"], model["lost_improvements"]), (1, 1, 0, 0))

    def test_matched_ranking_uses_score_then_id_without_outcomes(self):
        scores, ids = np.array([.5, .5, .2]), ["z", "a", "m"]
        self.assertEqual(analysis.matched_selection(scores, ids, 1).tolist(), [False, True, False])
        self.assertEqual(analysis.matched_selection(scores, ids, 2).tolist(), [True, True, False])
        self.assertFalse(analysis.matched_selection(scores, ids, 0).any())
        self.assertTrue(analysis.matched_selection(scores, ids, 3).all())

    def test_matched_ranking_rejects_nonfinite_scores_and_duplicate_ids(self):
        with self.assertRaises(ValueError):
            analysis.matched_selection([float("nan"), .5], ["a", "b"], 1)
        with self.assertRaises(ValueError):
            analysis.matched_selection([.2, .5], ["a", "a"], 1)
        with self.assertRaises(ValueError):
            analysis.matched_selection([.2, .5], ["a", "b"], 3)


class BootstrapTests(unittest.TestCase):
    def test_source_counts_are_fixed_and_resampling_is_deterministic(self):
        source = np.array(["alpha", "beta", "alpha", "beta", "beta"])
        first = analysis.bootstrap_weights(source)
        second = analysis.bootstrap_weights(source)
        self.assertEqual(first.shape, (5000, 5))
        np.testing.assert_array_equal(first, second)
        np.testing.assert_allclose(first.sum(axis=1), 1, atol=1e-7)
        np.testing.assert_allclose(first[:, source == "alpha"].sum(axis=1), .4, atol=1e-7)
        np.testing.assert_allclose(first[:, source == "beta"].sum(axis=1), .6, atol=1e-7)

    def test_same_question_weights_preserve_paired_two_model_cancellation(self):
        weights = analysis.bootstrap_weights(np.array(["alpha", "alpha", "beta", "beta"]))
        changes = np.array([[1, -1], [-1, 1], [0, 0], [1, -1]])
        draws = weights @ changes
        np.testing.assert_allclose(draws.mean(axis=1), 0, atol=1e-9)


class ReceiptSafetyTests(unittest.TestCase):
    @staticmethod
    def write_jsonl(path, values):
        path.write_text("".join(json.dumps(r) + "\n" for r in values), encoding="utf-8")

    def test_incomplete_runtime_never_writes_results(self):
        # Inputs below are deliberately synthetic and live only in a temporary
        # test directory. Mocking freeze validation isolates the completion gate.
        with tempfile.TemporaryDirectory(prefix="cti_analysis_unit_") as directory:
            root = Path(directory)
            output = root / "synthetic_outputs"
            output.mkdir()
            self.write_jsonl(root / "sealed_labels.jsonl", [{"id": f"synthetic_{i}", "answer": "A"} for i in range(1247)])
            self.write_jsonl(root / "policy_predictions.jsonl", [{"id": f"synthetic_{i}"} for i in range(1247)])
            (output / "runtime.json").write_text(json.dumps({"status": "FAILED_OR_INCOMPLETE"}), encoding="utf-8")
            with patch.object(analysis, "check_frozen", return_value={}):
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    analysis.evaluate(root, output)
            self.assertFalse((root / "RESULTS.json").exists())
            self.assertFalse((root / "scored_records.jsonl").exists())

    def test_changed_frozen_label_file_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="cti_freeze_unit_") as directory:
            root = Path(directory)
            names = ["analyze_external.py", "PROTOCOL.md", "sealed_labels.jsonl", "policy_predictions.jsonl",
                     "generator_inputs.jsonl", "qualification_inputs.jsonl", "inference_worker.py", "frozen_inference.py"]
            digest = hashlib.sha256(b"frozen").hexdigest()
            for name in names:
                (root / name).write_bytes(b"frozen")
            (root / "SCIENTIFIC_FREEZE.json").write_text(json.dumps({"files": {n: digest for n in names}}), encoding="utf-8")
            (root / "sealed_labels.jsonl").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "frozen file changed"):
                analysis.check_frozen(root)

    def test_missing_essential_freeze_bindings_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="cti_freeze_unit_") as directory:
            root = Path(directory)
            (root / "analyze_external.py").write_bytes(b"frozen")
            (root / "SCIENTIFIC_FREEZE.json").write_text(json.dumps({"files": {
                "analyze_external.py": hashlib.sha256(b"frozen").hexdigest()}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Essential scientific files"):
                analysis.check_frozen(root)

    def test_complete_status_cannot_bypass_incomplete_prediction_inventory(self):
        with tempfile.TemporaryDirectory(prefix="cti_analysis_unit_") as directory:
            root = Path(directory)
            output = root / "synthetic_outputs"
            output.mkdir()
            self.write_jsonl(root / "sealed_labels.jsonl", [{"id": f"synthetic_{i}", "answer": "A"} for i in range(1247)])
            self.write_jsonl(root / "policy_predictions.jsonl", [{"id": f"synthetic_{i}"} for i in range(1247)])
            prompts = [{"id": f"qualification_{i}", "vanilla_prompt": "synthetic vanilla",
                        "evidence_prompt": "synthetic evidence"} for i in range(8)]
            self.write_jsonl(root / "qualification_inputs.jsonl", prompts)
            self.write_jsonl(root / "generator_inputs.jsonl", [{"id": "synthetic_0", "vanilla_prompt": "synthetic vanilla", "evidence_prompt": "synthetic evidence"}])
            for name in ("inference_worker.py", "frozen_inference.py"):
                (root / name).write_bytes(b"unit fixture, never executable")
            qualification = []
            for row in prompts:
                for model, model_id, revision in analysis.MODELS:
                    for condition, field in (("vanilla", "vanilla_prompt"), ("relationship_evidence", "evidence_prompt")):
                        qualification.append({"id": row["id"], "model": model, "model_id": model_id, "revision": revision,
                            "condition": condition, "phase": "qualification", "raw_output": "Answer: A", "parsed_answer": "A",
                            "valid": True, "input_tokens": 10, "prompt_sha256": "0" * 64,
                            "input_prompt_sha256": hashlib.sha256(row[field].encode()).hexdigest()})
            self.write_jsonl(output / "qualification.jsonl", qualification)
            self.write_jsonl(output / "predictions.jsonl", [{"id": "synthetic_0", "model": "llama", "condition": "vanilla"}])
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            runtime = {"status": "COMPLETE", "inputs_sha256": digest(root / "generator_inputs.jsonl"),
                       "qualification_sha256": digest(root / "qualification_inputs.jsonl"),
                       "worker_sha256": digest(root / "inference_worker.py"),
                       "frozen_inference_sha256": digest(root / "frozen_inference.py"),
                       "predictions_sha256": digest(output / "predictions.jsonl"),
                       "qualification_outputs_sha256": digest(output / "qualification.jsonl"),
                       "decoding": {"batch_size": 2, "dtype": "float16", "do_sample": False,
                                    "max_input_tokens": 4096, "max_new_tokens": 8}}
            (output / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
            with patch.object(analysis, "check_frozen", return_value={}):
                with self.assertRaisesRegex(ValueError, "Fresh prediction inventory mismatch"):
                    analysis.evaluate(root, output)
            self.assertFalse((root / "RESULTS.json").exists())
            self.assertFalse((root / "scored_records.jsonl").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
