"""Controls for the E3 adaptation; synthetic fixtures only, never SCVIC fits."""
import copy
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch.run_e3 import (
    DEFAULT_PROTOCOL, apply_treatment, classification_metrics, fit_treatment,
    gradient_statistic, identify_candidates, inject_symmetric_noise, learner_config,
    posthoc_treatment_metrics, select_fit_indices, summarize,
)


def protocol():
    return json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))


class LabelNoiseTests(unittest.TestCase):
    def test_subset_is_fit_only_deterministic_and_class_capped(self):
        y = np.asarray([0, 0, 0, 1, 1, 1])
        split = np.asarray([0, 1, 2, 0, 0, 2])
        groups = np.asarray([f"group{index}" for index in range(6)])
        first = select_fit_indices(y, split, groups, 1, 9, 2)
        second = select_fit_indices(y, split, groups, 1, 9, 2)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(len(first), 2)
        self.assertTrue(np.all(split[first] == 0))
        np.testing.assert_array_equal(np.bincount(y[first]), [1, 1])
        full = select_fit_indices(y, split, groups, 20, 9, 2)
        self.assertEqual(len(full), 3)

    def test_noise_is_exact_distinct_and_shared_by_seed(self):
        labels = np.arange(103) % 6
        noisy, mask = inject_symmetric_noise(labels, 0.2, 6, 20)
        self.assertEqual(int(mask.sum()), 20)
        self.assertTrue(np.all(noisy[mask] != labels[mask]))
        self.assertTrue(np.all((noisy >= 0) & (noisy < 6)))
        repeat, _ = inject_symmetric_noise(labels, 0.2, 6, 20)
        np.testing.assert_array_equal(repeat, noisy)
        pristine, zero_mask = inject_symmetric_noise(labels, 0, 6, 20)
        np.testing.assert_array_equal(pristine, labels)
        self.assertFalse(zero_mask.any())
        np.testing.assert_array_equal(labels, np.arange(103) % 6)

    def test_gradient_history_is_hand_calculated(self):
        history = [np.asarray([[0.8, 0.2], [0.7, 0.3]]),
                   np.asarray([[0.6, 0.4], [0.9, 0.1]])]
        np.testing.assert_allclose(gradient_statistic(history, np.asarray([0, 1])), [0.3, 0.8])
        with self.assertRaises(ValueError):
            gradient_statistic([], np.asarray([0]))

    def test_degenerate_gradient_distribution_does_not_remove_everything(self):
        values = np.ones(8) * 0.5
        selected = identify_candidates(values, np.ones(8, bool), np.zeros(8, bool),
                                       9, protocol()["treatment"])
        self.assertFalse(selected.any())

    def test_gmm_candidates_use_high_error_component_without_noise_rate(self):
        values = np.asarray([0.01, 0.02, 0.01, 0.02, 0.8, 0.81, 0.8, 0.82])
        selected = identify_candidates(values, np.ones(8, bool), np.zeros(8, bool),
                                       9, protocol()["treatment"])
        np.testing.assert_array_equal(selected, [False] * 4 + [True] * 4)
        parameters = inspect.signature(identify_candidates).parameters
        self.assertNotIn("noise_rate", parameters)
        self.assertNotIn("true_labels", parameters)

    def test_removal_cap_and_observed_class_floor_hold(self):
        assigned = np.asarray([0] * 4 + [1] * 4 + [2])
        active, treated = np.ones(9, bool), np.zeros(9, bool)
        statistic = np.arange(9, dtype=float)
        probabilities = np.ones((9, 3)) / 3
        changed = apply_treatment("gradient_gmm_removal_adaptation", np.ones(9, bool),
                                  statistic, probabilities, assigned, active, treated, 0.5)
        self.assertEqual(int(changed.sum()), 4)
        self.assertTrue(active[8])
        self.assertTrue(np.all(np.bincount(assigned[active], minlength=3) >= 1))
        changed_again = apply_treatment("gradient_gmm_removal_adaptation", np.ones(9, bool),
                                        statistic, probabilities, assigned, active, treated, 0.5)
        self.assertFalse(changed_again.any())

    def test_relabel_is_one_time_and_does_not_touch_same_label_candidate(self):
        assigned = np.asarray([0, 1, 1])
        active, treated = np.ones(3, bool), np.zeros(3, bool)
        probabilities = np.asarray([[0.1, 0.9], [0.2, 0.8], [0.8, 0.2]])
        changed = apply_treatment("gradient_gmm_relabel_adaptation", np.ones(3, bool),
                                  np.ones(3), probabilities, assigned, active, treated, 0.8)
        np.testing.assert_array_equal(assigned, [1, 1, 0])
        np.testing.assert_array_equal(changed, [True, False, True])
        reverse = probabilities[:, ::-1].copy()
        apply_treatment("gradient_gmm_relabel_adaptation", np.ones(3, bool), np.ones(3),
                        reverse, assigned, active, treated, 0.8)
        self.assertEqual(assigned[0], 1)
        self.assertEqual(assigned[2], 0)

    def test_hidden_label_audit_distinguishes_detection_repair_and_damage(self):
        clean = np.asarray([0, 0, 1, 1])
        noisy = np.asarray([0, 1, 1, 0])
        state = {"assigned_labels": np.asarray([1, 0, 1, 0]),
                 "active": np.asarray([True, True, True, False]),
                 "treated": np.asarray([True, True, False, True]),
                 "ever_candidate": np.asarray([True, True, True, True])}
        result = posthoc_treatment_metrics(clean, noisy, state, ["a", "b"])
        self.assertEqual(result["injected_noise_count"], 2)
        self.assertEqual(result["candidate_detection"]["precision"], 0.5)
        self.assertEqual(result["actual_treatment"]["precision"], 2 / 3)
        self.assertEqual(result["originally_clean_removed_or_mislabeled"], 1)
        self.assertEqual(result["noisy_labels_corrected_and_retained"], 1)
        self.assertEqual(result["noisy_examples_removed"], 1)
        self.assertEqual(result["per_stage"]["a"]["clean_damage_fraction"], 1)

    def test_macro_metrics_include_all_declared_classes(self):
        result = classification_metrics(np.asarray([0, 0, 1]),
                                        np.asarray([[0.9, 0.1, 0], [0.9, 0.1, 0], [0.1, 0.9, 0]]),
                                        ["a", "b", "c"])
        self.assertAlmostEqual(result["macro_f1"], 2 / 3)
        self.assertEqual(result["per_stage"]["c"]["support"], 0)
        self.assertIsNone(result["per_stage"]["c"]["roc_auc"])

    def test_gate_requires_recovery_and_all_damage_guards(self):
        settings = protocol()
        rows = []
        for seed in settings["seeds"]:
            for rate in settings["noise_rates"]:
                for arm in settings["arms"]:
                    score = 0.5
                    if arm != "no_correction":
                        score += 0.03 if rate else -0.02
                    rows.append({"seed": seed, "noise_rate": rate, "arm": arm,
                                 "test": {"macro_f1": score,
                                          "per_stage": {settings["rare_stage"]: {"recall": 0.5}}}})
        result = summarize(rows, settings)
        self.assertEqual(result["screen_status"], "NEGATIVE_DEVELOPMENT")
        for screen in result["screens"].values():
            self.assertTrue(screen["guards"]["noisy_macro_f1_recovery"])
            self.assertFalse(screen["guards"]["clean_macro_f1_preserved"])
        with self.assertRaises(ValueError):
            summarize(rows[:-1], settings)

    def test_synthetic_booster_integration_uses_no_holdout_or_hidden_mask(self):
        import xgboost as xgb
        settings = protocol()
        settings["classes"] = ["a", "b", "c"]
        settings["boosting_rounds"] = 20
        settings["model_parameters"]["num_class"] = 3
        generator = np.random.default_rng(920)
        X = generator.normal(size=(45, 4)).astype(np.float32)
        observed = np.arange(45) % 3
        original = observed.copy()
        for arm in settings["arms"]:
            model, state = fit_treatment(X, observed, arm=arm, seed=2, config=learner_config(settings))
            probabilities = model.predict(xgb.DMatrix(X[:4]))
            self.assertEqual(probabilities.shape, (4, 3))
            np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)
            np.testing.assert_array_equal(observed, original)
            self.assertTrue(np.all(state["active"] | state["treated"]))
            if arm == "no_correction":
                self.assertEqual(state["trace"], [])
                np.testing.assert_array_equal(state["assigned_labels"], observed)
                baseline = xgb.train(dict(settings["model_parameters"], seed=2),
                                     xgb.DMatrix(X, label=observed), num_boost_round=20)
                np.testing.assert_allclose(probabilities, baseline.predict(xgb.DMatrix(X[:4])), atol=1e-7)
            else:
                self.assertEqual([entry["after_round"] for entry in state["trace"]], [15])
        parameters = inspect.signature(fit_treatment).parameters
        for forbidden in ("noise_rate", "clean_labels", "corruption_mask", "test", "calibration"):
            self.assertNotIn(forbidden, parameters)
        self.assertNotIn("noise_rates", learner_config(settings))
        with self.assertRaises(ValueError):
            fit_treatment(X, observed, arm="no_correction", seed=2, config=settings)


if __name__ == "__main__":
    unittest.main()
