"""Compare compression directly to expanded-reference NumPy distances."""
import unittest

import numpy as np

from experiments.apt_final.magic_compact.scoring import ExactFullReferenceKNN


def expanded_reference(bank, queries, k):
    bank, queries = np.asarray(bank, dtype=np.float64), np.asarray(queries, dtype=np.float64)
    distances = np.sqrt(np.sum((queries[:, None, :] - bank[None, :, :]) ** 2, axis=2))
    return np.sort(distances, axis=1)[:, :k].mean(axis=1)


class Tests(unittest.TestCase):
    def check_case(self, bank, queries, k):
        expected = expanded_reference(bank, queries, k)
        for qchunk, rchunk in ((1, 1), (2, 3), (128, 16384)):
            with self.subTest(query_chunk=qchunk, reference_chunk=rchunk):
                scorer = ExactFullReferenceKNN(bank, k, "cpu", qchunk, rchunk)
                actual, receipt = scorer.score(queries)
                np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
                self.assertEqual(receipt["reference_rows"], len(bank))
                self.assertEqual(receipt["reference_occurrences_preserved"], len(bank))
                self.assertEqual(receipt["unique_reference_rows"], len(np.unique(bank, axis=0)))
                self.assertTrue(receipt["integer_multiplicities_preserved"])
                self.assertFalse(receipt["reference_sampling"])

    def test_k200_exceeds_unique_population(self):
        bank = np.repeat(np.array([[0., 0.], [1., 0.], [3., 4.], [-2., 0.]]), [175, 20, 40, 90], axis=0)
        self.check_case(bank, np.array([[0., 0.], [2., 1.], [3., 4.], [-1., 0.]]), 200)

    def test_all_identical_k200(self):
        bank = np.repeat(np.array([[1.5, -2., 4.]]), 300, axis=0)
        self.check_case(bank, np.array([[1.5, -2., 4.], [0., 0., 0.]]), 200)

    def test_exact_distance_ties_and_partial_multiplicity(self):
        bank = np.repeat(np.array([[1., 0.], [-1., 0.], [0., 1.], [0., -1.], [2., 2.]]), [1, 17, 3, 8, 9], axis=0)
        self.check_case(bank, np.array([[0., 0.], [.5, 0.], [2., 2.]]), 10)

    def test_near_duplicates_are_not_merged(self):
        row = np.array([1., 2., 3.], dtype=np.float32)
        close = row.copy()
        close[0] = np.nextafter(close[0], np.float32(2.))
        bank = np.stack([row, row, close, close, close, row * 2])
        scorer = ExactFullReferenceKNN(bank, 4, "cpu", 1, 1)
        self.assertEqual(scorer.unique_rows, 3)
        self.check_case(bank, np.stack([row, close]), 4)

    def test_random_bank_with_duplicates_and_k_all(self):
        rng = np.random.default_rng(17)
        unique = rng.normal(size=(23, 7))
        bank = np.repeat(unique, rng.integers(1, 8, size=23), axis=0)
        query = np.r_[unique[:3], rng.normal(size=(4, 7))]
        self.check_case(bank, query, 1)
        self.check_case(bank, query, 19)
        self.check_case(bank, query, len(bank))

    def test_input_unchanged_and_permutations_preserve_scores(self):
        bank = np.array([[0., 0.], [0., 0.], [1., 1.], [2., 2.]])
        query = np.array([[0., 0.], [1.5, 1.5]])
        before_bank, before_query = bank.copy(), query.copy()
        first, _ = ExactFullReferenceKNN(bank, 3, "cpu", 1, 2).score(query)
        second, _ = ExactFullReferenceKNN(bank[::-1], 3, "cpu", 2, 1).score(query[::-1])
        np.testing.assert_array_equal(bank, before_bank)
        np.testing.assert_array_equal(query, before_query)
        np.testing.assert_allclose(first, second[::-1], rtol=1e-12, atol=1e-12)

    def test_invalid_reference_query_and_budget(self):
        for bank, k in ((np.array([[np.nan]]), 1), (np.ones((2, 3)), 3), (np.ones((2, 3)), 1.5), (np.ones((2, 0)), 1)):
            with self.assertRaises(ValueError):
                ExactFullReferenceKNN(bank, k, "cpu")
        scorer = ExactFullReferenceKNN(np.ones((5, 2)), 3, "cpu")
        with self.assertRaises(ValueError):
            scorer.score(np.ones((2, 3)))
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            scorer.score(np.ones((2, 2)), lambda: (_ for _ in ()).throw(RuntimeError("deadline")))


if __name__ == "__main__":
    unittest.main()
