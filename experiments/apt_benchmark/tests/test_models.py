import json
import math
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from experiments.apt_benchmark.models import (
    MODEL_SPECS, build_binary_model, calibration_threshold, resolve_threshold, score_binary,
)


class ModelTests(unittest.TestCase):
    def test_fixed_model_contracts_and_pipeline_steps(self):
        for name in MODEL_SPECS:
            with self.subTest(name=name):
                model = build_binary_model(name, seed=7)
                self.assertTrue(model.named_steps['imputer'].keep_empty_features)
                self.assertEqual(model.named_steps['imputer'].strategy, 'median')
                self.assertEqual('scaler' in model.named_steps, name == 'logistic_regression')
                for key, value in MODEL_SPECS[name]['parameters'].items():
                    self.assertEqual(model.named_steps['classifier'].get_params()[key], value)
                self.assertEqual(model.named_steps['classifier'].random_state, 7)
        self.assertEqual(build_binary_model('dummy-prior').named_steps['classifier'].strategy, 'prior')
        self.assertFalse(build_binary_model('hist_gradient_boosting').named_steps['classifier'].early_stopping)
        with self.assertRaises(ValueError):
            build_binary_model('unknown')

    def test_synthetic_fit_all_models_finite_class_one_scores(self):
        x = np.column_stack([np.linspace(-3, 3, 40), np.full(40, np.nan)])
        y = (x[:, 0] > 0).astype(int)
        with threadpool_limits(limits=1):
            for name in MODEL_SPECS:
                with self.subTest(name=name):
                    model = build_binary_model(name, seed=9).fit(x, y)
                    scores = score_binary(model, x)
                    self.assertEqual(scores.shape, (40,))
                    self.assertTrue(np.isfinite(scores).all())
                    self.assertTrue(((scores >= 0) & (scores <= 1)).all())
                    self.assertEqual(model.named_steps['imputer'].transform(x).shape[1], 2)
                    if name == 'dummy_prior':
                        np.testing.assert_array_equal(scores, np.full(40, .5))

    def test_imputer_and_scaler_use_only_fit_statistics(self):
        model = build_binary_model('logistic_regression').fit([[1, np.nan], [3, np.nan], [np.nan, np.nan], [5, np.nan]], [0, 0, 1, 1])
        imputer_before = model.named_steps['imputer'].statistics_.copy()
        scaler_before = model.named_steps['scaler'].mean_.copy()
        score_binary(model, [[1000000, 12345], [np.nan, np.nan]])
        np.testing.assert_array_equal(imputer_before, [3, 0])
        np.testing.assert_array_equal(scaler_before, [3, 0])
        np.testing.assert_array_equal(model.named_steps['imputer'].statistics_, imputer_before)
        np.testing.assert_array_equal(model.named_steps['scaler'].mean_, scaler_before)

    def test_score_orientation_and_single_class_dummy(self):
        class Reversed:
            classes_ = np.array([1, 0])
            def predict_proba(self, x):
                return np.array([[.8, .2], [.1, .9]])
        np.testing.assert_array_equal(score_binary(Reversed(), [[0], [1]]), [.8, .1])
        for label in (0, 1):
            dummy = build_binary_model('dummy_prior').fit([[0], [1]], [label, label])
            np.testing.assert_array_equal(score_binary(dummy, [[0], [1]]), [label, label])

    def test_invalid_probability_or_class_contract_rejected(self):
        class Invalid:
            classes_ = np.array([0, 1])
            def predict_proba(self, x):
                return np.array([[.1, .1]])
        with self.assertRaises(ValueError):
            score_binary(Invalid(), [[0]])
        Invalid.classes_ = np.array(['benign', 'attack'])
        with self.assertRaises(ValueError):
            score_binary(Invalid(), [[0]])


class CalibrationTests(unittest.TestCase):
    def test_ties_strict_rule_and_empirical_budget(self):
        result = calibration_threshold([0, 0, 0, 0, 1, 1, 1], [.1, .5, .5, .9, .5, .6, 1], .25)
        self.assertEqual(resolve_threshold(result), .5)
        self.assertEqual(result['confusion'], dict(tp=2, fp=1, tn=3, fn=1))
        self.assertFalse(result['population_fpr_guarantee'])
        json.dumps(result, allow_nan=False)

    def test_selected_threshold_maximizes_recall_exhaustively(self):
        y = np.array([0] * 12 + [1] * 8)
        scores = np.array([.1, .1, .2, .3, .5, .5, .6, .7, .8, .8, .9, 1,
                           .2, .4, .5, .7, .8, 1, 1.2, 1.3])
        for budget in [0, .01, .25, .5, 1]:
            with self.subTest(budget=budget):
                result = calibration_threshold(y, scores, budget)
                candidates = [-math.inf, *np.unique(scores), math.inf]
                feasible = [(float(((scores > t) & (y == 1)).sum() / 8), t)
                            for t in candidates if ((scores > t) & (y == 0)).sum() <= result['allowed_false_positives']]
                self.assertEqual(result['observed_recall'], max(recall for recall, _ in feasible))
                self.assertLessEqual(result['observed_fpr'], budget)

    def test_support_boundary_and_decimal_floor(self):
        low = calibration_threshold([0] * 99 + [1], [0] * 99 + [1])
        adequate_resolution = calibration_threshold([0] * 100 + [1], [0] * 100 + [1])
        self.assertTrue(low['insufficient_benign_resolution'])
        self.assertFalse(adequate_resolution['insufficient_benign_resolution'])
        self.assertEqual(adequate_resolution['allowed_false_positives'], 1)
        self.assertEqual(calibration_threshold([0] * 100 + [1], [0] * 100 + [1], .29)['allowed_false_positives'], 29)

    def test_absent_classes_and_empty_input_are_explicit_no_alarm(self):
        for y, score, status in [([0, 0], [.2, .3], 'NO_ATTACK_CALIBRATION'),
                                 ([1, 1], [.2, .3], 'NO_BENIGN_CALIBRATION'),
                                 ([], [], 'EMPTY_CALIBRATION')]:
            with self.subTest(status=status):
                result = calibration_threshold(y, score)
                self.assertEqual(result['status'], status)
                self.assertFalse(result['both_classes_present'])
                self.assertEqual(resolve_threshold(result), math.inf)
                self.assertEqual(result['confusion']['tp'] + result['confusion']['fp'], 0)
                if status != 'NO_BENIGN_CALIBRATION':
                    self.assertIsNone(result['observed_recall'])
                json.dumps(result, allow_nan=False)

    def test_invalid_labels_scores_budget_and_serialization(self):
        for y, score, budget in [([0, -1], [0, 1], .1), ([0, 1], [0, np.inf], .1),
                                 ([0, 1], [0], .1), ([0, 1], [0, 1], -1),
                                 ([0, 1], [0, 1], np.nan), ([0, 1], [0, 1], True)]:
            with self.subTest(y=y, budget=budget), self.assertRaises(ValueError):
                calibration_threshold(y, score, budget)
        with self.assertRaises(ValueError):
            resolve_threshold({'threshold_kind': 'finite', 'threshold_value': math.inf})
        with self.assertRaises(ValueError):
            resolve_threshold({'threshold_kind': 'positive_infinity', 'threshold_value': 0})
        all_alarm = calibration_threshold([0, 1], [.1, .9], 1)
        self.assertEqual(resolve_threshold(all_alarm), -math.inf)
        json.dumps(all_alarm, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
