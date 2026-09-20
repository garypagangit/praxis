"""Synthetic-only qualification of independent v2 evidence verification."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy import sparse

from experiments.apt_benchmark.robustness_v2 import audit as subject


class V2AuditTests(unittest.TestCase):
    def test_direct_counts_include_invisible_positive(self):
        y = np.asarray([1, 1, 0, 0])
        scores = np.asarray([.8, 0, .8, .2])
        value = subject.metrics(y, scores, np.asarray([True, False, True, True]), .5)
        self.assertEqual((value["tp"], value["fp"], value["fn"], value["tn"]), (1, 1, 1, 1))
        self.assertEqual(value["f1"], .5)
        self.assertEqual(value["observation_coverage"], .75)
        self.assertEqual(value["unobserved_positive_targets"], 1)

    def test_no_positive_has_undefined_recall_and_auc(self):
        value = subject.metrics(np.zeros(2), np.asarray([.3, .7]), np.ones(2, dtype=bool), .5)
        self.assertIsNone(value["recall"])
        self.assertIsNone(value["roc_auc"])
        self.assertIsNone(value["average_precision"])
        self.assertEqual(value["f1"], 0)

    def test_strict_threshold_rejects_equal_score(self):
        value = subject.metrics(np.asarray([1, 0]), np.asarray([.2, .2]), np.ones(2, dtype=bool), .2)
        self.assertEqual(value["tp"] + value["fp"], 0)

    def test_labels_cannot_be_reordered(self):
        with self.assertRaisesRegex(subject.AuditFailure, "labels"):
            subject.validate_arrays(np.asarray([0, 1]), np.asarray([.2, .8]), np.ones(2, dtype=bool), np.asarray([1, 0]))

    def test_hidden_target_cannot_get_score(self):
        with self.assertRaisesRegex(subject.AuditFailure, "nonzero"):
            subject.validate_arrays(np.asarray([1]), np.asarray([.8]), np.asarray([False]), np.asarray([1]))

    def test_nonfinite_score_rejected(self):
        with self.assertRaisesRegex(subject.AuditFailure, "Invalid saved score"):
            subject.validate_arrays(np.asarray([1]), np.asarray([float("nan")]), np.asarray([True]), np.asarray([1]))

    def test_mask_must_be_boolean(self):
        with self.assertRaisesRegex(subject.AuditFailure, "boolean"):
            subject.validate_arrays(np.asarray([1]), np.asarray([.8]), np.asarray([1]), np.asarray([1]))

    def test_duplicate_condition_rejected(self):
        with self.assertRaisesRegex(subject.AuditFailure, "Duplicate protocol condition"):
            subject.expected_grid({"conditions": [{"name": "clean", "kind": "clean"}] * 2, "models": ["a"], "seeds": [7]})

    def test_source_label_subtechnique_collapse(self):
        events = [{"labels": ["T1548.003:control"]}, {"labels": ["T15480"]}, {"labels": ["T1548"]}]
        np.testing.assert_array_equal(subject.target_labels(events, "T1548"), [1, 0, 1])

    def test_route_counts_use_current_bits_and_observation_mask(self):
        matrix = np.zeros((5, 26))
        matrix[:, 18:20] = [[0, 0], [1, 0], [0, 1], [1, 1], [1, 1]]
        actual = subject.route_counts(sparse.csr_matrix(matrix), np.asarray([True, True, True, True, False]), 8)
        self.assertEqual(actual, {"0": 1, "1": 1, "2": 1, "3": 1})

    def screen_fixture(self):
        gates = {"command_records_absent_f1_delta_min": .05, "command_records_absent_recall_delta_min": -.02,
                 "command_records_absent_flag_rate_delta_max": .005, "clean_f1_delta_min": -.02,
                 "random_50_mean_f1_delta_min": -.02}
        protocol = {"primary_comparison": {"candidate": "mixed", "baseline": "random", "point": "calibrated", "per_target_gates": gates}}
        rows = []
        for arm in ("mixed", "random"):
            for condition in ("clean", "random_50", "command_records_absent"):
                f1 = (.6 if arm == "mixed" else .4) if condition == "command_records_absent" else .8
                rows.append({"arm": arm, "condition": condition,
                             "calibrated": {"f1": f1, "recall": .8, "negative_label_flag_rate": .01}})
        checks = {name: {"limit": limit, "passed": True, "delta": .2 if name == "command_records_absent_f1_delta_min" else 0.0}
                  for name, limit in gates.items()}
        return {"results": rows, "primary_screen": {"status": "PASS", "checks": checks}}, protocol

    def test_primary_screen_reproduced_independently(self):
        record, protocol = self.screen_fixture()
        self.assertEqual(subject.audit_primary_screen(record, protocol)["status"], "PASS")

    def test_primary_screen_cannot_hide_recall_loss(self):
        record, protocol = self.screen_fixture()
        record["results"][2]["calibrated"]["recall"] = .7
        with self.assertRaisesRegex(subject.AuditFailure, "command_records_absent_recall_delta_min"):
            subject.audit_primary_screen(record, protocol)

    def fixture(self, folder):
        """Complete tiny saved-evidence fixture; no model fitting or inference."""
        folder = Path(folder)
        run = folder / "run"
        run.mkdir()
        events = []
        for role in ("fit", "development", "calibration", "test"):
            for number, label in enumerate(("T1", "other")):
                events.append({"event_id": role + str(number), "run_id": role, "split": role,
                               "timestamp": float(number), "labels": [label], "target_eligible": True,
                               "fragments": [{"timestamp": float(number), "channel": "SYSCALL", "text": "command",
                                              "entity_keys": [role], "baseline_text": "event"}]})
        event_path = folder / "events.jsonl"
        event_path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
        manifest_path = folder / "manifest.json"
        manifest_path.write_text(json.dumps({"events_sha256": subject.sha(event_path)}), encoding="utf-8")
        protocol = {"datasets": {"fixture": {"targets": ["T1"]}}, "conditions": [{"name": "clean", "kind": "clean", "deadline": 0}],
                    "models": ["semantic_event"], "arms": {"semantic_event": {"family": "semantic_event", "views": ["clean"]}},
                    "seeds": [7], "classifier": {"random_state": 7}, "history": {"seconds": 120, "max_events": 32},
                    "text_features": {"hash_dimensions_per_block": 8}, "calibration": {"negative_label_fpr_budget": .01}}
        protocol_path = run / "PROTOCOL.json"
        protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
        score, y, observed = np.asarray([.8, .2]), np.asarray([1, 0]), np.ones(2, dtype=bool)
        np.savez_compressed(run / "PRIVATE_CAL_T1_semantic_event.npz", y=y, score=score, observed=observed)
        np.savez_compressed(run / "PRIVATE_T1_semantic_event_clean_7.npz", y=y, score=score, observed=observed)
        np.savez_compressed(run / "PRIVATE_TARGET_ROSTER.npz", event_ids=np.asarray(["test0", "test1"]), run_ids=np.asarray(["test", "test"]))
        model = run / "T1_semantic_event.joblib"
        model.write_bytes(b"SYNTHETIC FIXTURE ONLY; MODEL INFERENCE DISABLED")
        threshold = {"threshold_kind": "finite", "threshold_value": .2, "allowed_false_positives": 0,
                     "n_rows": 2, "n_attack": 1, "n_benign": 1, "max_fpr": .01,
                     "confusion": {"tp": 1, "fp": 0, "tn": 1, "fn": 0}, "observed_recall": 1.0, "observed_fpr": 0.0}
        expected = {"n": 2, "positive": 1, "negative": 1, "tp": 1, "fp": 0, "fn": 0, "tn": 1,
                    "precision": 1.0, "recall": 1.0, "f1": 1.0, "negative_label_flag_rate": 0.0, "roc_auc": 1.0,
                    "average_precision": 1.0, "observed_targets": 2, "observation_coverage": 1.0, "unobserved_positive_targets": 0}
        row = {"condition": "clean", "seed": 7, "arm": "semantic_event", "deadline_seconds": 0,
               "fixed_0_5": dict(expected), "calibrated": dict(expected), "by_run": {"test": {"fixed_0_5": dict(expected), "calibrated": dict(expected)}}}
        result = {"status": "COMPLETE", "dataset": "fixture", "input_sha256": subject.sha(event_path),
                  "manifest_sha256": subject.sha(manifest_path), "protocol_sha256": subject.sha(protocol_path),
                  "events": 8, "eligible_targets": 8, "targets": {"T1": {"status": "COMPLETE",
                  "support": {role: {"n": 2, "positive": 1, "negative": 1} for role in ("fit", "development", "calibration", "test")},
                  "models": {"semantic_event": {"threshold": threshold, "model_sha256": subject.sha(model)}}, "results": [row]}}}
        receipt = {"frozen_before_fit": True, "input_sha256": subject.sha(event_path), "protocol": protocol,
                   "protocol_sha256": subject.sha(protocol_path), "code_sha256": {"audit.py": subject.sha(subject.__file__)}}
        (run / "RESULTS.json").write_text(json.dumps(result), encoding="utf-8")
        (run / "PRE_FIT_RECEIPT.json").write_text(json.dumps(receipt), encoding="utf-8")
        return run, event_path, manifest_path, result

    def test_complete_synthetic_evidence_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            run, events, manifest, _ = self.fixture(folder)
            result = subject.audit(run, events, manifest, Path(folder) / "audit", calibration_inference=False)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["verified_result_rows"], 1)
            self.assertEqual(result["verified_calibration_thresholds"], 1)
            self.assertFalse(result["execution_scope"]["test_model_inference"])

    def test_tampered_test_metric_fails_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            run, events, manifest, result = self.fixture(folder)
            result["targets"]["T1"]["results"][0]["calibrated"]["tp"] = 2
            (run / "RESULTS.json").write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(subject.AuditFailure, "count/undefined mismatch tp"):
                subject.audit(run, events, manifest, Path(folder) / "audit", calibration_inference=False)

    def test_tampered_threshold_fails_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            run, events, manifest, result = self.fixture(folder)
            result["targets"]["T1"]["models"]["semantic_event"]["threshold"]["threshold_value"] = .3
            (run / "RESULTS.json").write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(subject.AuditFailure, "negative-score rank"):
                subject.audit(run, events, manifest, Path(folder) / "audit", calibration_inference=False)

    def test_removed_grid_row_fails_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            run, events, manifest, result = self.fixture(folder)
            result["targets"]["T1"]["results"] = []
            (run / "RESULTS.json").write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(subject.AuditFailure, "Incomplete frozen result grid"):
                subject.audit(run, events, manifest, Path(folder) / "audit", calibration_inference=False)

    def test_tampered_source_bytes_fail_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            run, events, manifest, _ = self.fixture(folder)
            with events.open("a", encoding="utf-8") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(subject.AuditFailure, "Hash mismatch: source_events"):
                subject.audit(run, events, manifest, Path(folder) / "audit", calibration_inference=False)


if __name__ == "__main__":
    unittest.main()
