"""Synthetic-only boundary checks for separately frozen stronger tree controls."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.tree import DecisionTreeClassifier

from experiments.apt_benchmark.tabular_batch import run_e1
from experiments.apt_benchmark.tabular_followup import run_strong_baselines as followup


class RecordingClassifier(ClassifierMixin, BaseEstimator):
    fits = []

    def fit(self, X, y):
        type(self).fits.append(np.asarray(X).copy())
        self.classes_ = np.unique(y)
        return self

    def predict(self, X):
        return np.full(len(X), self.classes_[0])


def synthetic_data():
    classes = np.asarray(["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"])
    counts = [50, 50, 50, 1060, 50, 50]
    y = np.repeat(np.arange(6), counts)
    split = np.concatenate([np.r_[np.zeros(count - 10), np.ones(5), np.full(5, 2)] for count in counts]).astype(np.int8)
    rng = np.random.default_rng(77)
    X = np.c_[y + rng.normal(0, .1, len(y)), np.arange(len(y), dtype=float), np.full(len(y), np.nan)]
    X[::7, 1] = np.nan
    X[split > 0, 1] = 1e8
    return {"X": X, "y": y.astype(np.int32), "split": split, "classes": classes,
            "group_sha256": np.asarray([f"{index:064x}" for index in range(len(y))]),
            "feature_names": np.asarray(["signal", "numeric", "empty"])}


class StrongBaselineTests(unittest.TestCase):
    def test_budgets_preserve_exact_original_support_and_isolate_fit(self):
        data = synthetic_data()
        original = run_e1.select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=20260921, budget=32)
        equal = followup.select_support(data, 20260921, followup.CONDITIONS[0])
        abundant = followup.select_support(data, 20260921, followup.CONDITIONS[1])
        np.testing.assert_array_equal(equal, original)
        np.testing.assert_array_equal(abundant[:192], original)
        np.testing.assert_array_equal(np.bincount(data["y"][abundant]), [32, 32, 32, 1024, 32, 32])
        self.assertTrue(np.all(data["split"][abundant] == 0))
        self.assertEqual(len(np.unique(abundant)), 1184)
        self.assertTrue(np.all(data["y"][abundant[192:]] == 3))

    def test_support_stable_to_source_order_and_heldout_changes(self):
        data = synthetic_data()
        expected = followup.select_support(data, 20260921, followup.CONDITIONS[1])
        permutation = np.random.default_rng(19).permutation(len(data["y"]))
        shuffled = {key: (value[permutation] if key in {"X", "y", "split", "group_sha256"} else value) for key, value in data.items()}
        shuffled["X"][shuffled["split"] > 0] = -9e8
        selected = followup.select_support(shuffled, 20260921, followup.CONDITIONS[1])
        np.testing.assert_array_equal(data["group_sha256"][expected], shuffled["group_sha256"][selected])

    def test_abundant_budget_cannot_be_filled_from_heldout_rows(self):
        data = synthetic_data()
        normal_fit = np.flatnonzero((data["y"] == 3) & (data["split"] == 0))
        data["split"][normal_fit[1000:]] = 2
        with self.assertRaisesRegex(ValueError, "Insufficient benign fit"):
            followup.select_support(data, 20260921, followup.CONDITIONS[1])

    def test_imputer_fit_inside_each_cv_fold_and_grid_ties_stable(self):
        X = np.c_[np.arange(66.0), np.full(66, np.nan)]
        X[::4, 0] = np.nan
        y = np.tile([0, 1, 2], 22)
        RecordingClassifier.fits = []
        with patch.object(followup, "make_tree", return_value=RecordingClassifier()):
            cv = followup.tune_tree("xgboost", X, y, 77, [{"choice": 0}, {"choice": 1}], 4)
        for observed, (train, _) in zip(RecordingClassifier.fits[:3], followup.inner_folds(y, 77)):
            expected = X[train].copy()
            expected[np.isnan(expected[:, 0]), 0] = np.nanmedian(expected[:, 0])
            expected[:, 1] = 0
            np.testing.assert_array_equal(observed, expected)
        self.assertEqual(cv["selected_candidate_index"], 0)
        self.assertEqual(len(RecordingClassifier.fits), 6)

    def test_family_selection_ignores_test_scores_and_rejects_mismatches(self):
        cells = [{"model": name, "comparison_binding": "same", "inner_cv": {"selected_mean_macro_f1": cv},
                  "metrics": {"test": {"macro_f1": test}}} for name, cv, test in [("xgboost", .8, .2), ("lightgbm", .8, .95), ("random_forest", .9, .1)]]
        self.assertEqual(followup.select_family(cells, ["xgboost", "lightgbm"])["model"], "xgboost")
        self.assertEqual(followup.select_family(cells, followup.MODELS)["model"], "random_forest")
        cells[1]["comparison_binding"] = "other support"
        with self.assertRaises(ValueError):
            followup.select_family(cells, ["xgboost", "lightgbm"])

    def make_inputs(self, root):
        data = synthetic_data()
        data_path = root / "DATA.npz"
        np.savez(data_path, **data)
        run_e1.write_json(root / "MANIFEST.json", {"data_npz_sha256": run_e1.sha256_file(data_path), "evaluation_scope": "Synthetic software check only"})
        original = json.loads(Path(run_e1.__file__).with_name("protocol.json").read_text())
        original.update(study_kind="synthetic_smoke", seeds=[20260921], data_npz_sha256=run_e1.sha256_file(data_path), manifest_sha256=run_e1.sha256_file(root / "MANIFEST.json"))
        original_path = root / "ORIGINAL.json"
        run_e1.write_json(original_path, original)
        protocol = json.loads(Path(followup.__file__).with_name("protocol_strong_baselines.json").read_text())
        protocol.update(status="FROZEN_BEFORE_FOLLOWUP_MODEL_FITS", study_kind="synthetic_smoke", seeds=[20260921],
                        e1_protocol_sha256=run_e1.sha256_file(original_path), data_npz_sha256=original["data_npz_sha256"], manifest_sha256=original["manifest_sha256"])
        protocol_path = root / "PROTOCOL.json"
        run_e1.write_json(protocol_path, protocol)
        return data, data_path, original_path, protocol_path, protocol

    def test_protocol_requires_freeze_exact_grid_and_bound_original(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, original, _, protocol = self.make_inputs(Path(directory))
            followup.validate_protocol(protocol, original)
            changed = copy.deepcopy(protocol)
            changed["status"] = "DRAFT_REQUIRES_FREEZE"
            with self.assertRaises(ValueError):
                followup.validate_protocol(changed, original)
            changed = copy.deepcopy(protocol)
            changed["model_grids"]["xgboost"][0]["max_depth"] = 99
            with self.assertRaises(ValueError):
                followup.validate_protocol(changed, original)
            with original.open("a") as stream:
                stream.write("\n")
            with self.assertRaises(ValueError):
                followup.validate_protocol(protocol, original)

    def test_prepare_only_records_supports_folds_and_all_query_rows_without_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, path, original, protocol, _ = self.make_inputs(root)
            with patch.object(followup, "make_tree", side_effect=AssertionError("Preparation must not fit")):
                result = followup.run(path, protocol, root / "output", e1_protocol_path=original,
                                      models=followup.MODELS, conditions=followup.CONDITIONS, prepare_only=True)
            self.assertEqual(result["status"], "PREPARED_ONLY")
            receipt = json.loads((root / "output/PREFIT_RECEIPT.json").read_text())
            np.testing.assert_array_equal(receipt["execution"]["test_query"]["indices"], np.flatnonzero(data["split"] == 2))
            for condition in followup.CONDITIONS:
                support = receipt["execution"]["supports"][condition]["20260921"]
                self.assertTrue(np.all(data["split"][support["indices"]] == 0))
                for fold in support["inner_folds_support_positions"]:
                    self.assertFalse(set(fold["train"]) & set(fold["validation"]))
                    self.assertEqual(len(fold["train"]) + len(fold["validation"]), len(support["indices"]))

    def test_synthetic_end_to_end_receipt_resume_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, path, original, protocol, _ = self.make_inputs(root)
            output = root / "output"
            def tiny_synthetic_model(*args):
                self.assertTrue((output / "PREFIT_RECEIPT.json").exists())
                self.assertTrue((output / "cells/equal_32_per_class/random_forest/20260921/STARTED.json").exists())
                return DecisionTreeClassifier(max_depth=3, random_state=1)
            kwargs = {"e1_protocol_path": original, "models": ["random_forest"], "conditions": [followup.CONDITIONS[0]]}
            with patch.object(followup, "make_tree", side_effect=tiny_synthetic_model):
                result = followup.run(path, protocol, output, **kwargs)
            self.assertEqual(result["completed_cells"], 1)
            self.assertEqual(result["status"], "INCOMPLETE")
            cell_dir = output / "cells/equal_32_per_class/random_forest/20260921"
            with np.load(cell_dir / "PREDICTIONS.npz", allow_pickle=False) as arrays:
                support = arrays["selected_fit_indices"]
                self.assertAlmostEqual(arrays["imputer_statistics"][1], np.nanmedian(data["X"][support, 1]))
                self.assertEqual(arrays["imputer_statistics"][2], 0)
                np.testing.assert_array_equal(arrays["test_indices"], np.flatnonzero(data["split"] == 2))
            with patch.object(followup, "make_tree", side_effect=AssertionError("Completed run must not refit")):
                followup.run(path, protocol, output, **kwargs)
            with (output / "RESULTS.json").open("a") as stream:
                stream.write("\n")
            with self.assertRaisesRegex(ValueError, "Completed run artifact hash"):
                followup.run(path, protocol, output, **kwargs)

    def test_partial_cell_and_tampered_start_receipt_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            cell = Path(directory)
            original = b"Interrupted fit receipt"
            (cell / "STARTED.json").write_bytes(original)
            with self.assertRaisesRegex(ValueError, "Incomplete nonempty cell"):
                followup.validate_completed(cell, "execution", "comparison")
            self.assertEqual((cell / "STARTED.json").read_bytes(), original)
            with patch.object(run_e1, "validate_completed", return_value={"started_receipt_sha256": "wrong"}):
                with self.assertRaisesRegex(ValueError, "start receipt has changed"):
                    followup.validate_completed(cell, "execution", "comparison")


if __name__ == "__main__":
    unittest.main()
