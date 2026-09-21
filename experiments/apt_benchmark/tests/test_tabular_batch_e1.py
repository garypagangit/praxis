"""Synthetic-only checks of support isolation, CV isolation and immutable resume."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import StratifiedKFold

from experiments.apt_benchmark.tabular_batch import run_e1


class RecordingClassifier(ClassifierMixin, BaseEstimator):
    fits = []

    def fit(self, X, y):
        type(self).fits.append(np.asarray(X).copy())
        self.classes_ = np.unique(y)
        return self

    def predict(self, X):
        return np.full(len(X), self.classes_[0])


class E1RunnerTests(unittest.TestCase):
    def test_support_sampling_never_uses_calibration_and_is_row_order_stable(self):
        y = np.repeat(np.arange(3), 50)
        split = np.tile(np.r_[np.zeros(40), np.ones(5), np.full(5, 2)], 3)
        fingerprints = np.asarray([f"{i:064x}" for i in range(len(y))])
        selected = run_e1.select_fit_indices(y, split, fingerprints, seed=10, budget=32)
        self.assertEqual(len(selected), 96)
        self.assertTrue(np.all(split[selected] == 0))
        np.testing.assert_array_equal(np.bincount(y[selected]), [32, 32, 32])
        permutation = np.random.default_rng(9).permutation(len(y))
        again = run_e1.select_fit_indices(y[permutation], split[permutation], fingerprints[permutation], seed=10, budget=32)
        np.testing.assert_array_equal(fingerprints[selected], fingerprints[permutation][again])

    def test_insufficient_fit_budget_is_rejected_despite_heldout_rows(self):
        y = np.repeat(np.arange(2), 100)
        split = np.ones(200, dtype=int)
        split[:10] = 0
        split[100:110] = 0
        with self.assertRaises(ValueError):
            run_e1.select_fit_indices(y, split, np.arange(200).astype(str), seed=1, budget=32)

    def test_imputation_is_refitted_inside_each_inner_fold(self):
        X = np.arange(64.0).reshape(-1, 1)
        X[::5] = np.nan
        y = np.tile([0, 1], 32)
        folds = list(StratifiedKFold(3, shuffle=True, random_state=8).split(X, y))
        RecordingClassifier.fits = []
        with patch.object(run_e1, "make_tree", return_value=RecordingClassifier()):
            result = run_e1.tune_tree("xgboost", X, y, 8, [{"choice": 1}, {"choice": 2}, {"choice": 3}], 3)
        for observed, (train, _) in zip(RecordingClassifier.fits[:3], folds):
            expected = X[train].copy()
            expected[np.isnan(expected)] = np.nanmedian(expected)
            np.testing.assert_array_equal(observed, expected)
        self.assertEqual(result["selected_candidate_index"], 0)
        self.assertEqual(len(RecordingClassifier.fits), 9)

    def test_probability_metrics_confusions_and_absent_class(self):
        y = np.asarray([0, 0, 1, 1])
        p = np.asarray([[.9, .1, 0], [.6, .4, 0], [.8, .2, 0], [.1, .9, 0]])
        result = run_e1.probability_metrics(y, p, ["a", "b", "c"])
        self.assertEqual(result["confusion_matrix"], [[2, 0, 0], [1, 1, 0], [0, 0, 0]])
        self.assertAlmostEqual(result["macro_f1"], (0.8 + 2 / 3) / 3)
        self.assertIsNone(result["roc_auc_ovr_macro"])
        self.assertIsNone(result["per_stage"]["c"]["average_precision_ovr"])
        with self.assertRaises(ValueError):
            run_e1.probability_metrics(y, p * 2, ["a", "b", "c"])

    def test_gbdt_family_selected_by_cv_even_when_test_prefers_other(self):
        cells = [
            {"model": "xgboost", "seed": 1, "comparison_binding": "same", "inner_cv": {"selected_mean_macro_f1": .9}, "metrics": {"test": {"macro_f1": .2}}},
            {"model": "lightgbm", "seed": 1, "comparison_binding": "same", "inner_cv": {"selected_mean_macro_f1": .8}, "metrics": {"test": {"macro_f1": .95}}},
            {"model": "tabicl_v2", "seed": 1, "comparison_binding": "same", "metrics": {"test": {"macro_f1": .5}}},
        ]
        result = run_e1.build_summary(cells)
        self.assertEqual(result["primary_comparisons"][0]["gbdt_selected_by_inner_cv"], "xgboost")
        self.assertAlmostEqual(result["mean_primary_delta_macro_f1"], .3)
        cells[0]["comparison_binding"] = "different"
        with self.assertRaises(ValueError):
            run_e1.build_summary(cells)

    def test_frozen_protocol_rejects_changed_grid(self):
        protocol = self.protocol()
        run_e1.validate_protocol(protocol)
        protocol["model_grids"]["xgboost"][0]["max_depth"] = 10
        with self.assertRaises(ValueError):
            run_e1.validate_protocol(protocol)

    def test_incomplete_cell_is_rejected_without_overwriting_evidence(self):
        with tempfile.TemporaryDirectory(prefix="apt-e1-incomplete-") as directory:
            cell_dir = Path(directory) / "cell"
            cell_dir.mkdir()
            artifact = cell_dir / "PREDICTIONS.tmp.npz"
            original = b"partial prediction evidence must survive resume"
            artifact.write_bytes(original)
            with self.assertRaisesRegex(ValueError, "Incomplete nonempty cell"):
                run_e1.validate_completed(cell_dir, "execution", "comparison")
            self.assertEqual(artifact.read_bytes(), original)
            self.assertEqual([path.name for path in cell_dir.iterdir()], [artifact.name])

    @staticmethod
    def protocol():
        return {"schema_version": 1, "experiment": "E1", "study_kind": "synthetic_smoke",
                "seeds": [20260921], "samples_per_class": 32, "n_splits": 3,
                "prediction_chunk_rows": 1024, "foundation_n_estimators": 4,
                "models": list(run_e1.MODELS), "model_grids": copy.deepcopy(run_e1.DEFAULT_GRIDS)}

    def test_end_to_end_synthetic_rf_receipt_resume_and_tamper_rejection(self):
        # This exercises one synthetic RF fit, never the SCVIC data or foundation models.
        with tempfile.TemporaryDirectory(prefix="apt-e1-synthetic-") as directory:
            root = Path(directory)
            data_dir = root / "input"
            data_dir.mkdir()
            rng = np.random.default_rng(13)
            y = np.repeat(np.arange(3), 60)
            X = np.c_[y + rng.normal(0, .1, len(y)), rng.normal(size=len(y)), np.full(len(y), np.nan)]
            split = np.tile(np.r_[np.zeros(40), np.ones(10), np.full(10, 2)], 3).astype(int)
            X[split == 1, 1] += 100000  # held-out values must not influence imputation.
            X[::7, 1] = np.nan
            data_path = data_dir / "DATA.npz"
            np.savez(data_path, X=X, y=y, split=split,
                     group_sha256=np.asarray([f"{i:064x}" for i in range(len(y))]),
                     classes=np.asarray(["a", "b", "c"]), feature_names=np.asarray(["f1", "f2", "empty"]))
            run_e1.write_json(data_dir / "MANIFEST.json", {"data_npz_sha256": run_e1.sha256_file(data_path), "evaluation_scope": "synthetic software smoke only"})
            protocol = self.protocol()
            protocol.update(data_npz_sha256=run_e1.sha256_file(data_path), manifest_sha256=run_e1.sha256_file(data_dir / "MANIFEST.json"))
            protocol_path = root / "PROTOCOL.json"
            run_e1.write_json(protocol_path, protocol)
            output = root / "output"
            original_make = run_e1.make_tree

            def require_prefit(*args, **kwargs):
                self.assertTrue((output / "PREFIT_RECEIPT.json").exists())
                return original_make(*args, **kwargs)

            with patch.object(run_e1, "make_tree", side_effect=require_prefit):
                result = run_e1.run(data_path, protocol_path, output, ["random_forest"], device="cpu", model_cache=root / "cache")
            self.assertEqual(result["completed_cells"], 1)
            cell_path = output / "cells" / "random_forest" / "20260921"
            with np.load(cell_path / "PREDICTIONS.npz", allow_pickle=False) as artifact:
                selected = artifact["selected_fit_indices"]
                self.assertEqual(artifact["test_probabilities"].shape, (30, 3))
                self.assertAlmostEqual(artifact["imputer_statistics"][1], np.nanmedian(X[selected, 1]))
                self.assertEqual(artifact["imputer_statistics"][2], 0)
            with patch.object(run_e1, "make_tree", side_effect=AssertionError("completed run refit")):
                resumed = run_e1.run(data_path, protocol_path, output, ["random_forest"], device="cpu", model_cache=root / "cache")
            self.assertEqual(resumed["completed_cells"], 1)
            with (cell_path / "PREDICTIONS.npz").open("ab") as stream:
                stream.write(b"tampering")
            with self.assertRaises(ValueError):
                run_e1.run(data_path, protocol_path, output, ["random_forest"], device="cpu", model_cache=root / "cache")


if __name__ == "__main__":
    unittest.main()
