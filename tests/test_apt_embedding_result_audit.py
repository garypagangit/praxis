"""Negative checks for independent saved-bank and distance-score auditing."""
import unittest

import numpy as np

from experiments.apt_final.embedding_baseline.analysis.verify_results import (
    bank_scaling_check, brute_force_score_sample, check_bank_indices, check_local_queries, observed_local_features,
)
from experiments.apt_final.native_graph.analysis.verify_results import AuditFailure


class EmbeddingResultAuditTests(unittest.TestCase):
    def setUp(self):
        self.raw = np.array([[0.], [0.], [2.], [4.]])
        self.mean = self.raw.mean(axis=0)
        self.scale = self.raw.std(axis=0)

    def test_direct_distance_check_preserves_duplicate_reference_rows(self):
        unique = np.array([[0.], [3.]])
        inverse = np.array([1, 0, 1])
        # k=2: two bank zeros give zero at query0; query3 has distances1,1.
        score = np.array([1 / self.scale[0], 0., 1 / self.scale[0]])
        result = brute_force_score_sample((self.raw, self.mean, self.scale), unique, inverse, score, 2)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["sampled_unique_queries"], 2)
        self.assertTrue(result["full_query_distance_reexecution"])
        wrong = score.copy()
        wrong[[0, 2]] += .01
        with self.assertRaises(AuditFailure):
            brute_force_score_sample((self.raw, self.mean, self.scale), unique, inverse, wrong, 2)

    def test_duplicate_queries_must_have_identical_saved_scores(self):
        with self.assertRaisesRegex(AuditFailure, "different scores"):
            brute_force_score_sample((self.raw, self.mean, self.scale), np.array([[0.]]),
                                     np.array([0, 0]), np.array([0., .1]), 2)

    def test_saved_scaler_cannot_be_changed_to_query_statistics(self):
        bank = {"a_bank_raw": self.raw, "a_mean": self.mean, "a_scale": self.scale,
                "a_bank_scaled": (self.raw - self.mean) / self.scale}
        bank_scaling_check(bank, "a", 1e-3)
        bank["a_mean"] = self.mean + 1
        with self.assertRaisesRegex(AuditFailure, "mean"):
            bank_scaling_check(bank, "a", 1e-3)

    def test_training_bank_forbids_calibration_or_duplicate_rows(self):
        cfg = {"train_graphs": ["train0", "train1"], "bank_seed_offset": 1, "bank_size": 100}
        sizes = {"train0": 2, "train1": 3}
        indices = {"train0": np.array([0, 1]), "train1": np.array([0, 1, 2])}
        self.assertEqual(check_bank_indices(indices, sizes, 7, cfg), 5)
        with self.assertRaises(AuditFailure):
            check_bank_indices({**indices, "train3": np.array([0])}, sizes, 7, cfg)
        indices["train0"] = np.array([0, 0])
        with self.assertRaises(AuditFailure):
            check_bank_indices(indices, sizes, 7, cfg)

    def test_independent_local_feature_reconstruction_obeys_removed_edges(self):
        graph = {"node_type": np.array([0, 1]), "src": np.array([0, 0, 1]),
                 "dst": np.array([0, 1, 0]), "relation": np.array([0, 0, 1])}
        mean, scale = np.zeros(6, dtype=np.float32), np.ones(6, dtype=np.float32)
        value = observed_local_features(graph, 2, 2, mean, scale, np.array([True, False, False]))
        expected = np.array([[1., 0., np.log(2), 0., np.log(2), 0.], [0., 1., 0., 0., 0., 0.]], dtype=np.float32)
        np.testing.assert_allclose(value, expected, rtol=1e-7)

    def test_local_query_reconstruction_accepts_rounding_but_refuses_wrong_rows(self):
        expected = np.array([[1., .5], [0., 2.]], dtype=np.float32)
        queries = {"local_knn_unique": expected.copy(), "local_knn_inverse": np.array([0, 1])}
        queries["local_knn_unique"][0, 1] += np.float32(1e-7)
        check_local_queries(queries, expected)
        queries["local_knn_inverse"] = np.array([1, 0])
        with self.assertRaises(AuditFailure):
            check_local_queries(queries, expected)


if __name__ == "__main__":
    unittest.main()
