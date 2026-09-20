"""Independent exact-distance and training-bank contract checks."""
import unittest

import numpy as np

from experiments.apt_final.embedding_baseline.scoring import ExactKNN, sample_bank_indices


def brute_force(bank, query, k, floor=1e-3):
    mean = bank.mean(axis=0)
    scale = np.maximum(bank.std(axis=0, ddof=0), floor)
    bank_z, query_z = (bank - mean) / scale, (query - mean) / scale
    distances = np.sqrt(np.sum((query_z[:, None, :] - bank_z[None, :, :]) ** 2, axis=2))
    return np.sort(distances, axis=1)[:, :k].mean(axis=1)


class ExactScoringTests(unittest.TestCase):
    def test_exact_distances_match_brute_force_with_ties_and_duplicate_reference(self):
        bank = np.array([[0., 0.], [0., 0.], [2., 0.], [2., 0.], [1., 2.]])
        query = np.array([[0., 0.], [1., 0.], [3., 3.], [0., 0.]])
        model = ExactKNN(bank, k=2)
        score, metadata = model.score(query)
        np.testing.assert_allclose(score, brute_force(bank, query, 2), rtol=1e-13, atol=1e-13)
        self.assertEqual(score[0], 0.0)
        self.assertEqual(metadata["reference_rows"], 5)
        self.assertEqual(metadata["query_duplicates_reused"], 1)

    def test_chunk_size_and_query_dedup_do_not_change_scores_or_order(self):
        rng = np.random.default_rng(901)
        bank = rng.normal(size=(47, 8))
        query = np.vstack([rng.normal(size=(19, 8)), np.zeros((5, 8))])
        rng.shuffle(query)
        model = ExactKNN(bank, k=10)
        expected = brute_force(bank, query, 10)
        for chunk, dedup in ((1, False), (7, True), (100, False)):
            with self.subTest(chunk=chunk, dedup=dedup):
                score, _ = model.score(query, chunk, dedup)
                np.testing.assert_allclose(score, expected, rtol=1e-13, atol=1e-13)

    def test_bank_scaler_frozen_and_inputs_not_mutated(self):
        bank = np.array([[1., 2.], [3., 2.], [5., 2.]])
        query = np.array([[100., -20.], [1., 2.]])
        before_bank, before_query = bank.copy(), query.copy()
        model = ExactKNN(bank, k=2)
        original = model.artifact_arrays()
        model.score(query)
        np.testing.assert_array_equal(bank, before_bank)
        np.testing.assert_array_equal(query, before_query)
        for key, value in original.items():
            np.testing.assert_array_equal(getattr(model, key), value)
        self.assertEqual(model.scale[1], 1e-3)
        bank[:] = 999
        np.testing.assert_array_equal(model.bank_raw, before_bank)
        original["mean"][:] = 999
        self.assertFalse(np.any(model.mean == 999))

    def test_finite_shapes_parameters_and_small_bank_are_guarded(self):
        for bank in (np.array([[np.nan]]), np.array([[np.inf]]), np.ones(4), np.ones((2, 0)), np.array([[1j]])):
            with self.subTest(bank=repr(bank)), self.assertRaises(ValueError):
                ExactKNN(bank, k=1)
        for k in (0, True, 4):
            with self.subTest(k=k), self.assertRaises(ValueError):
                ExactKNN(np.ones((3, 2)), k=k)
        for floor in (0, -1, np.nan, np.inf):
            with self.subTest(floor=floor), self.assertRaises(ValueError):
                ExactKNN(np.ones((3, 2)), k=1, epsilon=floor)
        model = ExactKNN(np.ones((3, 2)), k=1)
        for query in (np.ones((3, 3)), np.array([[0., np.inf]])):
            with self.assertRaises(ValueError):
                model.score(query)
        with self.assertRaises(ValueError):
            model.score(np.ones((1, 2)), chunk_size=0)

    def test_global_uniform_bank_sampling_is_reproducible_and_not_per_graph_balanced(self):
        sizes = {"train0": 100, "train1": 900}
        first = sample_bank_indices(sizes, 100, 73)
        second = sample_bank_indices(dict(reversed(list(sizes.items()))), 100, 73)
        for name in sizes:
            np.testing.assert_array_equal(first[name], second[name])
            self.assertEqual(len(first[name]), len(set(first[name])))
            self.assertTrue(np.all((first[name] >= 0) & (first[name] < sizes[name])))
        self.assertEqual(sum(map(len, first.values())), 100)
        self.assertGreater(len(first["train1"]), 70)
        self.assertLess(len(first["train0"]), 30)
        self.assertEqual(sizes, {"train0": 100, "train1": 900})

    def test_bank_cap_larger_than_population_preserves_all_original_row_ids(self):
        result = sample_bank_indices({"train0": 2, "train1": 3}, 8192, 7)
        np.testing.assert_array_equal(result["train0"], [0, 1])
        np.testing.assert_array_equal(result["train1"], [0, 1, 2])
        for sizes, cap, seed in (({}, 10, 1), ({"a": 0}, 10, 1), ({"a": 5}, 0, 1), ({"a": 5}, 2, -1)):
            with self.assertRaises(ValueError):
                sample_bank_indices(sizes, cap, seed)


if __name__ == "__main__":
    unittest.main()
