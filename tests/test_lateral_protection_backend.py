"""Boundary and leakage checks on synthetic data only; no research dataset fits."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from experiments.apt_benchmark.lateral_protection_experiment import backend


class RecordingClassifier:
    def __init__(self, parameters, n_classes, records, *, reverse_columns=False, bad_probabilities=False):
        self.parameters = parameters
        self.n_classes = n_classes
        self.records = records
        self.reverse_columns = reverse_columns
        self.bad_probabilities = bad_probabilities

    def fit(self, X, y, sample_weight):
        self.classes_ = np.arange(self.n_classes)
        if self.reverse_columns:
            self.classes_ = self.classes_[::-1]
        self.record = {"X_train": X.copy(), "y_train": y.copy(), "sample_weight": sample_weight.copy(),
                       "parameters": copy.deepcopy(self.parameters)}
        self.records.append(self.record)
        return self

    def predict(self, X):
        raise AssertionError("CV must score the fixed-column probability argmax, not predict().")

    def predict_proba(self, X):
        self.record["X_validation"] = X.copy()
        probabilities = np.zeros((len(X), self.n_classes))
        probabilities[:, 0] = 1.0
        if self.bad_probabilities:
            probabilities[0, 0] = np.nan
        return probabilities


def fixture():
    # Unequal non-multiples of three ensure each fold has distinct class counts.
    y = np.repeat(np.arange(3), [5, 7, 11])
    rows = np.arange(len(y), dtype=float)
    feature = rows**2
    feature[::3] = np.nan
    X = np.column_stack([rows, feature, np.full(len(y), np.nan)])
    return X, y


class WeightTests(unittest.TestCase):
    def test_natural_balanced_and_lateral_weight_mass(self):
        y = np.repeat(np.arange(3), [3, 7, 10])
        np.testing.assert_array_equal(backend.training_weights(y, "natural", 3, 1), np.ones(20))
        for scheme, mass_ratios in [("balanced", [1, 1, 1]), ("lateral2", [1, 2, 1]), ("lateral4", [1, 4, 1])]:
            with self.subTest(scheme=scheme):
                weights = backend.training_weights(y, scheme, 3, 1)
                self.assertAlmostEqual(weights.mean(), 1.0)
                sums = np.bincount(y, weights=weights)
                np.testing.assert_allclose(sums / sums[0], mass_ratios)
                for label in range(3):
                    self.assertEqual(len(np.unique(weights[y == label])), 1)

    def test_missing_noninteger_and_invalid_labels_rejected(self):
        for y in [[0, 0, 1], [0, 1, 3], [-1, 0, 1], [0.0, 1.0, 2.0], [[0, 1, 2]], [], [True, False]]:
            with self.subTest(y=y), self.assertRaises(ValueError):
                backend.training_weights(y, "balanced", 3, 1)
        for kwargs in [dict(scheme="unknown"), dict(n_classes=1), dict(n_classes=True), dict(lateral_index=3)]:
            args = {"scheme": "natural", "n_classes": 3, "lateral_index": 1, **kwargs}
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                backend.training_weights(np.arange(3), **args)

    def test_malformed_weight_vectors_rejected(self):
        malformed = [[], [1, 1], [[1, 1, 1]], [0, 1, 2], [-1, 2, 2], [1, np.nan, 1],
                     [1, np.inf, 1], [2, 2, 2], ["1", "1", "1"], [True, True, True]]
        for weights in malformed:
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                backend.validate_weight_vector(weights, 3)


class FittingTests(unittest.TestCase):
    def run_recorded(self, *, grid=None, reverse_columns=False, bad_probabilities=False):
        X, y = fixture()
        records = []
        calls = []

        def factory(model, seed, parameters, n_classes, threads):
            calls.append((model, seed, n_classes, threads))
            return RecordingClassifier(parameters, n_classes, records,
                                       reverse_columns=reverse_columns, bad_probabilities=bad_probabilities)

        grid = grid if grid is not None else [{"max_depth": 2}, {"max_depth": 3}]
        with patch.object(backend, "make_tree", side_effect=factory), patch.object(backend, "package_versions", return_value={"test": "synthetic"}):
            result = backend.fit_model("xgboost", X, y, 123, grid, "lateral2", 0, 1, 3, threads=2)
        return X, y, records, calls, result

    def test_fold_local_imputation_weights_and_final_recomputation(self):
        X, y, records, calls, result = self.run_recorded()
        classifier, imputer, metadata, timing = result
        folds = list(StratifiedKFold(3, shuffle=True, random_state=123).split(X, y))
        self.assertEqual(len(records), 7)  # Two candidates x three folds, then a single final refit.
        self.assertEqual(calls, [("xgboost", 123, 3, 2)] * 7)
        global_median = np.array([np.median(X[:, 0]), np.nanmedian(X[:, 1]), 0.0])
        global_weights = backend.training_weights(y, "lateral2", 3, 1)
        fold_weight_difference = False
        fold_median_difference = False
        for candidate in range(2):
            for fold_number, (train, validation) in enumerate(folds):
                record = records[candidate * 3 + fold_number]
                fold_medians = np.array([np.median(X[train, 0]), np.nanmedian(X[train, 1]), 0.0])
                expected_train = np.where(np.isnan(X[train]), fold_medians, X[train])
                expected_validation = np.where(np.isnan(X[validation]), fold_medians, X[validation])
                np.testing.assert_allclose(record["X_train"], expected_train)
                np.testing.assert_allclose(record["X_validation"], expected_validation)
                np.testing.assert_array_equal(record["y_train"], y[train])
                # Derive fold weights independently, not by subsetting the full-data vector.
                counts = np.bincount(y[train], minlength=3)
                expected = np.array([len(train) / (3 * counts[label]) * (2 if label == 1 else 1) for label in y[train]])
                expected /= expected.mean()
                np.testing.assert_allclose(record["sample_weight"], expected)
                fold_weight_difference |= not np.allclose(expected, global_weights[train] / global_weights[train].mean())
                fold_median_difference |= not np.allclose(fold_medians, global_median)
                saved = metadata["folds"][fold_number]
                self.assertEqual(saved["train_support_positions"], train.tolist())
                self.assertEqual(saved["validation_support_positions"], validation.tolist())
                np.testing.assert_allclose(saved["imputer_statistics"], fold_medians)
        self.assertTrue(fold_weight_difference, "Fixture must detect globally computed weights leaking into CV.")
        self.assertTrue(fold_median_difference, "Fixture must detect full-support medians leaking into CV.")
        np.testing.assert_allclose(records[-1]["X_train"], np.where(np.isnan(X), global_median, X))
        np.testing.assert_allclose(records[-1]["sample_weight"], global_weights)
        np.testing.assert_allclose(imputer.statistics_, global_median)
        self.assertIs(classifier.record, records[-1])
        self.assertEqual(metadata["versions"], {"test": "synthetic"})
        self.assertTrue(all(value >= 0 for value in timing.values()))
        json.dumps(metadata, allow_nan=False)

    def test_argmax_macro_f1_all_classes_and_first_candidate_tie(self):
        X, y, _, _, (_, _, metadata, _) = self.run_recorded()
        expected = []
        for _, validation in StratifiedKFold(3, shuffle=True, random_state=123).split(X, y):
            expected.append(f1_score(y[validation], np.zeros(len(validation), dtype=int),
                                     labels=np.arange(3), average="macro", zero_division=0))
        for candidate in metadata["candidates"]:
            np.testing.assert_allclose(candidate["fold_macro_f1"], expected)
        self.assertEqual(metadata["selected_candidate_index"], 0)
        self.assertEqual(metadata["selected_parameters"], {"max_depth": 2})
        backend.validate_cv_metadata(metadata, [{"max_depth": 2}, {"max_depth": 3}])

    def test_grid_is_detached_and_weight_runtime_overrides_are_forbidden(self):
        grid = [{"max_depth": 2}]
        _, _, _, _, (_, _, metadata, _) = self.run_recorded(grid=grid)
        grid[0]["max_depth"] = 99
        self.assertEqual(metadata["selected_parameters"], {"max_depth": 2})
        X, y = fixture()
        for key in ["class_weight", "sample_weight", "scale_pos_weight", "is_unbalance", "classifier__class_weight",
                    "random_state", "seed", "n_jobs", "device", "objective"]:
            with self.subTest(key=key), patch.object(backend, "make_tree") as factory, self.assertRaises(ValueError):
                backend.fit_model("lightgbm", X, y, 1, [{key: None}], "natural", 0, 1, 3)
            factory.assert_not_called()

    def test_inadequate_or_invalid_input_fails_before_model_fit(self):
        X, y = fixture()
        cases = [dict(model="random_forest"), dict(y_fit=np.where(y == 2, 1, y)),
                 dict(X_fit=X[:5]), dict(grid=[]), dict(grid=[{"learning_rate": np.inf}]),
                 dict(seed=True), dict(threads=0), dict(normal_index=1), dict(weight_scheme="unknown")]
        X_inf = X.copy(); X_inf[0, 0] = np.inf
        cases += [dict(X_fit=X_inf), dict(X_fit=np.zeros((6, 2)), y_fit=np.repeat(np.arange(3), 2))]
        for changed in cases:
            args = dict(model="xgboost", X_fit=X, y_fit=y, seed=1, grid=[{}], weight_scheme="balanced",
                        normal_index=0, lateral_index=1, n_classes=3, threads=1)
            args.update(changed)
            with self.subTest(changed=list(changed)), patch.object(backend, "make_tree") as factory, self.assertRaises(ValueError):
                backend.fit_model(**args)
            factory.assert_not_called()

    def test_bad_generated_weights_and_probability_columns_rejected(self):
        X, y = fixture()
        with patch.object(backend, "training_weights", return_value=np.zeros(len(y))), self.assertRaises(ValueError):
            backend.fit_model("xgboost", X, y, 1, [{}], "natural", 0, 1, 3)
        with self.assertRaisesRegex(ValueError, "class order"):
            self.run_recorded(reverse_columns=True)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            self.run_recorded(bad_probabilities=True)

    def test_cv_receipt_rejects_mean_and_tie_selection_tampering(self):
        _, _, _, _, (_, _, metadata, _) = self.run_recorded()
        grid = [{"max_depth": 2}, {"max_depth": 3}]
        wrong = copy.deepcopy(metadata); wrong["candidates"][0]["mean_macro_f1"] += 0.1
        with self.assertRaisesRegex(ValueError, "mean"):
            backend.validate_cv_metadata(wrong, grid)
        wrong = copy.deepcopy(metadata); wrong["selected_candidate_index"] = 1; wrong["selected_parameters"] = grid[1]
        with self.assertRaisesRegex(ValueError, "winner"):
            backend.validate_cv_metadata(wrong, grid)

    @unittest.skipUnless(importlib.util.find_spec("xgboost") and importlib.util.find_spec("lightgbm"), "Optional tree libraries unavailable")
    def test_real_library_weighted_multiclass_smoke_on_synthetic_data(self):
        rng = np.random.default_rng(71)
        y = np.repeat(np.arange(3), [9, 12, 18])
        X = rng.normal(size=(len(y), 4)); X[:, 0] += y
        X[::4, 1] = np.nan; X[:, 3] = np.nan
        grids = {"xgboost": [{"n_estimators": 3, "max_depth": 2}],
                 "lightgbm": [{"n_estimators": 3, "num_leaves": 3, "min_child_samples": 2}]}
        for model, grid in grids.items():
            with self.subTest(model=model):
                classifier, imputer, metadata, _ = backend.fit_model(model, X, y, 123, grid, "lateral4", 0, 1, 3, threads=1)
                probabilities = classifier.predict_proba(imputer.transform(X))
                self.assertEqual(probabilities.shape, (len(y), 3))
                self.assertTrue(np.isfinite(probabilities).all())
                np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)
                self.assertEqual(imputer.statistics_[-1], 0.0)
                backend.validate_cv_metadata(metadata, grid)


if __name__ == "__main__":
    unittest.main()
