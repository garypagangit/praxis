"""Synthetic transfer tests; no scientific target fitting or model execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from experiments.apt_benchmark.tabular_followup import run_sandworm_transfer as transfer


class TransferTests(unittest.TestCase):
    def fixture(self, root, *, baselines=False):
        from experiments.apt_benchmark.tests.test_tabular_followup_strong_baselines import StrongBaselineTests
        source_dir = root / "source"
        source_dir.mkdir()
        source, source_path, original_path, _, _ = StrongBaselineTests().make_inputs(source_dir)
        original = json.loads(original_path.read_text())
        target = {"X": np.full((6, 3), 9e7), "y_binary": np.asarray([0, 0, 0, 1, 1, 1]),
                  "procedure_labels": np.asarray(["Normal", "Normal", "Normal", "CredentialDump", "CredentialDump", "RemoteExecution"]),
                  "group_sha256": np.asarray([f"{10000 + row:064x}" for row in range(6)]),
                  "feature_names": source["feature_names"], "raw_to_unique": np.asarray([0, 1, 2, 3, 4, 5, 0, 2])}
        target_dir = root / "target"
        target_dir.mkdir()
        target_path = target_dir / "DATA.npz"
        np.savez(target_path, **target)
        transfer.run_e1.write_json(target_dir / "MANIFEST.json", {"target_data_npz_sha256": transfer.run_e1.sha256_file(target_path)})
        protocol = {"schema_version": 1, "experiment": "SANDWORM_BINARY_TRANSFER", "study_kind": "synthetic_smoke",
                    "status": "FROZEN_BEFORE_TARGET_MODEL_FITS", "seeds": [20260921], "samples_per_class": 32,
                    "foundation_model": "tabicl_v2", "tree_models": ["xgboost", "lightgbm"], "foundation_n_estimators": 4,
                    "prediction_chunk_rows": 1024, "cpu_threads": 4, "tabicl_n_jobs": 1, "device": "cpu",
                    "no_target_fit": True, "no_target_calibration": True, "no_target_threshold_tuning": True,
                    "primary_rule": "source_argmax_is_not_NormalTraffic", "ranking_score": "1_minus_source_NormalTraffic_probability",
                    "e1_protocol_sha256": transfer.run_e1.sha256_file(original_path),
                    "source_data_npz_sha256": original["data_npz_sha256"], "source_manifest_sha256": original["manifest_sha256"],
                    "target_data_npz_sha256": transfer.run_e1.sha256_file(target_path),
                    "target_manifest_sha256": transfer.run_e1.sha256_file(target_dir / "MANIFEST.json"),
                    "expected_unique_rows": 6, "expected_raw_rows": 8,
                    "expected_unique_attack_rows": 3, "expected_unique_normal_rows": 3}
        protocol_path = root / "TRANSFER.json"
        transfer.run_e1.write_json(protocol_path, protocol)
        baseline_root = root / "baseline"
        if baselines:
            with patch.object(transfer.run_e1, "make_tree", return_value=DecisionTreeClassifier(max_depth=3, random_state=1)):
                transfer.run_e1.run(source_path, original_path, baseline_root, transfer.BASELINES, device="cpu", model_cache=root / "cache")
        return source, target, source_path, target_path, original_path, baseline_root, protocol_path, protocol

    def rewrite_target(self, target, target_path, protocol):
        np.savez(target_path, **target)
        protocol["target_data_npz_sha256"] = transfer.run_e1.sha256_file(target_path)
        transfer.run_e1.write_json(target_path.with_name("MANIFEST.json"), {"target_data_npz_sha256": protocol["target_data_npz_sha256"]})
        protocol["target_manifest_sha256"] = transfer.run_e1.sha256_file(target_path.with_name("MANIFEST.json"))

    def test_primary_binary_argmax_differs_from_half_attack_score(self):
        classes = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]
        target = {"y_binary": np.asarray([0, 1]), "procedure_labels": np.asarray(["Normal", "AttackProcedure"])}
        # Row 0 has attack mass 0.65, but Normal is the largest individual class.
        probabilities = np.asarray([[.2, .15, .1, .35, .1, .1], [.7, .1, .05, .05, .05, .05]])
        result = transfer.binary_metrics(probabilities, classes, target, np.asarray([1, 1]))
        self.assertEqual(result["confusion_matrix_normal_attack"], [[1, 0], [0, 1]])
        self.assertEqual(result["attack_recall"], 1)

    def test_raw_sensitivity_weights_counts_without_new_inference(self):
        target = {"y_binary": np.asarray([0, 0, 1, 1]), "procedure_labels": np.asarray(["Normal", "Normal", "A", "B"])}
        probabilities = np.asarray([[.9, .1], [.1, .9], [.2, .8], [.7, .3]])
        primary = transfer.binary_metrics(probabilities, ["NormalTraffic", "Attack"], target, np.ones(4, dtype=np.int64))
        weighted = transfer.binary_metrics(probabilities, ["NormalTraffic", "Attack"], target, np.asarray([4, 2, 1, 1]))
        self.assertEqual(primary["confusion_matrix_normal_attack"], [[1, 1], [1, 1]])
        self.assertEqual(weighted["confusion_matrix_normal_attack"], [[4, 2], [1, 1]])
        self.assertEqual(weighted["represented_rows"], 8)
        self.assertEqual(weighted["per_procedure_attack_recall"]["B"]["missed"], 1)
        self.assertAlmostEqual(weighted["normal_false_positive_rate"], 2 / 6)

    def test_target_gate_rejects_feature_order_overlap_and_bad_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target, _, path, _, _, _, protocol = self.fixture(Path(directory))
            loaded, _ = transfer.load_target(path, protocol, source)
            self.assertEqual(loaded["raw_multiplicity"].tolist(), [2, 1, 2, 1, 1, 1])
            for field, value in [("feature_names", target["feature_names"][::-1]),
                                 ("raw_to_unique", np.asarray([0, 1, 2, 3, 4, 9])),
                                 ("group_sha256", np.asarray([source["group_sha256"][0], *target["group_sha256"][1:]]))]:
                changed = copy.deepcopy(target)
                changed[field] = value
                self.rewrite_target(changed, path, protocol)
                with self.assertRaises(ValueError):
                    transfer.load_target(path, protocol, source)

    def test_protocol_rejects_unfrozen_or_target_adaptation(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, _, original, _, _, protocol = self.fixture(Path(directory))
            transfer.validate_protocol(protocol, original)
            for key, value in [("status", "DRAFT_REQUIRES_FREEZE"), ("no_target_fit", False), ("tabicl_n_jobs", 4), ("primary_rule", "attack_score_above_half")]:
                changed = copy.deepcopy(protocol)
                changed[key] = value
                with self.assertRaises(ValueError):
                    transfer.validate_protocol(changed, original)

    def test_prepare_only_audits_source_receipts_without_target_model_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, path, target_path, original, baselines, protocol_path, protocol = self.fixture(root, baselines=True)
            output = root / "transfer"
            with patch.object(transfer.run_e1, "make_tree", side_effect=AssertionError("No transfer fit allowed")):
                result = transfer.run(path, target_path, protocol_path, original, baselines, output, root / "cache",
                                      models=["selected_gbdt"], prepare_only=True)
            self.assertEqual(result["status"], "PREPARED_ONLY")
            receipt = json.loads((output / "PREFIT_RECEIPT.json").read_text())
            selection = receipt["execution"]["source_selections"]["20260921"]
            self.assertEqual(len(selection["support"]["indices"]), 192)
            self.assertTrue(np.all(source["split"][selection["support"]["indices"]] == 0))
            self.assertEqual(receipt["execution"]["target_query_fingerprints"], target["group_sha256"].tolist())
            self.assertEqual(receipt["execution"]["target_training_labels_used"], 0)
            (baselines / "cells/lightgbm/20260921/PREDICTIONS.npz").write_bytes(b"tampered source")
            with self.assertRaises(ValueError):
                transfer.run(path, target_path, protocol_path, original, baselines, output, root / "cache", models=["selected_gbdt"], prepare_only=True)

    def test_end_to_end_refit_uses_source_only_no_hpo_and_preserves_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, path, target_path, original, baselines, protocol_path, _ = self.fixture(root, baselines=True)
            output = root / "transfer"
            observed = []
            class RecordTree(DecisionTreeClassifier):
                def fit(self, X, y, **kwargs):
                    observed.append(np.asarray(X).copy())
                    return super().fit(X, y, **kwargs)
            def make(*args):
                self.assertTrue((output / "PREFIT_RECEIPT.json").exists())
                self.assertTrue((output / "cells/selected_gbdt/20260921/STARTED.json").exists())
                return RecordTree(max_depth=3, random_state=1)
            kwargs = {"models": ["selected_gbdt"]}
            with patch.object(transfer.run_e1, "make_tree", side_effect=make), patch.object(transfer.run_e1, "tune_tree", side_effect=AssertionError("Transfer must not retune")):
                result = transfer.run(path, target_path, protocol_path, original, baselines, output, root / "cache", **kwargs)
            self.assertEqual(len(observed), 1)
            self.assertEqual(observed[0].shape, (192, 3))
            self.assertLess(float(np.max(observed[0])), 9e7)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["decision"], "DESCRIPTIVE_ONLY_NO_PASS_GATE")
            folder = output / "cells/selected_gbdt/20260921"
            with np.load(folder / "PREDICTIONS.npz", allow_pickle=False) as saved:
                rows = saved["selected_fit_indices"]
                self.assertEqual(saved["target_probabilities"].shape, (6, 6))
                self.assertAlmostEqual(saved["imputer_statistics"][1], np.nanmedian(source["X"][rows, 1]))
                self.assertEqual(saved["imputer_statistics"][2], 0)
            with patch.object(transfer.run_e1, "make_tree", side_effect=AssertionError("Completed cell cannot refit")):
                transfer.run(path, target_path, protocol_path, original, baselines, output, root / "cache", **kwargs)
            with (folder / "PREDICTIONS.npz").open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaises(ValueError):
                transfer.run(path, target_path, protocol_path, original, baselines, output, root / "cache", **kwargs)


if __name__ == "__main__":
    unittest.main()
