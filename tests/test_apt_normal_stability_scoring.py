"""Role exclusion, equal entity budgets, and dependent-view calibration."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from experiments.apt_final.normal_stability.scoring import (
    ARMS, build_view_banks, empirical_tail_margin, fit_detectors,
    pool_calibration, select_fit_rows,
)


class NormalStabilityScoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sizes = {"train0": 40, "train1": 60, "train2": 20, "train3": 30, "test0": 1000}

    def caches(self, duplicate=False):
        result = {}
        for name in ("train0", "train1"):
            size = self.sizes[name]
            base = np.arange(size, dtype=np.float32) + (100 if name == "train1" else 0)
            result[name] = {}
            for condition in ("clean", "masked"):
                arrays = {"node_type": np.arange(size, dtype=np.int64) % 3,
                          "degree": np.full(size, 2 if condition == "clean" else 1, dtype=np.int64)}
                for arm_index, arm in enumerate(ARMS):
                    values = np.ones((size, 2), dtype=np.float32) if duplicate else np.column_stack((base, base + arm_index))
                    if condition == "masked":
                        values += 1000
                    arrays[arm + "_unique"], arrays[arm + "_inverse"] = np.unique(values, axis=0, return_inverse=True)
                path = self.root / (name + "_" + condition + ".npz")
                np.savez(path, **arrays)
                result[name][condition] = path
        return result

    def rows(self, cap=40, seed=3011):
        return select_fit_rows(self.sizes, ["train0", "train1"], "train2", "train3", cap, seed)

    def change_cache(self, path, key, transform):
        with np.load(path, allow_pickle=False) as data:
            arrays = {name: data[name] for name in data.files}
        arrays[key] = transform(arrays[key])
        np.savez(path, **arrays)

    def test_sampling_excludes_all_held_out_graphs_and_is_order_independent(self):
        rows = self.rows(40)
        repeat = select_fit_rows(dict(reversed(list(self.sizes.items()))), ["train1", "train0"], "train2", "train3", 40, 3011)
        self.assertEqual(set(rows), {"train0", "train1"})
        self.assertEqual(sum(map(len, rows.values())), 40)
        for name in rows:
            np.testing.assert_array_equal(rows[name], repeat[name])
            self.assertEqual(len(rows[name]), len(np.unique(rows[name])))
            self.assertTrue(np.all(rows[name] < self.sizes[name]))
        # Capping by eligible population never draws from held-out graphs.
        all_rows = self.rows(8192)
        self.assertEqual(sum(map(len, all_rows.values())), 100)
        np.testing.assert_array_equal(all_rows["train1"], np.arange(60))

    def test_role_overlap_test_graph_and_incomplete_partition_are_rejected(self):
        roles = [(["train0", "train0"], "train2", "train3"),
                 (["train0", "train1"], "train1", "train3"),
                 (["train0", "test0"], "train2", "train3"),
                 (["train0", "train1"], "train2", "train2"),
                 (["train0"], "train2", "train3")]
        for fit, cal, val in roles:
            with self.subTest(roles=(fit, cal, val)), self.assertRaises(ValueError):
                select_fit_rows(self.sizes, fit, cal, val)
        for seed in (-1, True, 1.2):
            with self.assertRaises(ValueError):
                self.rows(seed=seed)

    def test_pooled_budget_is_disjoint_same_rows_and_allocation_for_every_arm(self):
        caches, rows = self.caches(), self.rows()
        bank, metadata = build_view_banks(caches, rows, 3011)
        self.assertEqual(metadata["bank_rows"], 40)
        self.assertEqual(metadata["clean_rows"], 20)
        self.assertEqual(metadata["masked_rows"], 20)
        mask = metadata["pooled_is_masked"]
        identities = list(zip(metadata["bank_row_graph"], metadata["bank_row_id"]))
        self.assertEqual(len(set(identities)), 40)
        for arm in ARMS:
            np.testing.assert_array_equal(bank["pooled"][arm][~mask], bank["clean"][arm][~mask])
            np.testing.assert_array_equal(bank["pooled"][arm][mask], bank["clean"][arm][mask] + 1000)
            self.assertEqual(bank["clean"][arm].dtype, np.float32)
        again, meta_again = build_view_banks(dict(reversed(list(caches.items()))), dict(reversed(list(rows.items()))), 3011)
        np.testing.assert_array_equal(mask, meta_again["pooled_is_masked"])
        for arm in ARMS:
            np.testing.assert_array_equal(bank["pooled"][arm], again["pooled"][arm])

    def test_duplicate_vectors_retain_each_entity_and_inputs_are_unchanged(self):
        caches, rows = self.caches(duplicate=True), self.rows(41)
        original_rows = {name: row.copy() for name, row in rows.items()}
        before = {path: path.read_bytes() for views in caches.values() for path in views.values()}
        banks, metadata = build_view_banks(caches, rows, 3011)
        self.assertEqual(metadata["clean_rows"], 20)
        self.assertEqual(metadata["masked_rows"], 21)
        for arm in ARMS:
            self.assertEqual(len(banks["clean"][arm]), 41)
            self.assertEqual(len(np.unique(banks["clean"][arm], axis=0)), 1)
            self.assertEqual(len(np.unique(banks["pooled"][arm], axis=0)), 2)
        for name in rows:
            np.testing.assert_array_equal(rows[name], original_rows[name])
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_row_and_cache_alignment_corruption_is_rejected(self):
        for name, key, transform in (
            ("row order", "node_type", lambda a: np.roll(a, 1)),
            ("inverse range", "gin_knn_inverse", lambda a: np.full_like(a, 10000)),
            ("inverse length", "local_knn_inverse", lambda a: a[:-1]),
            ("inverse type", "mlp_knn_inverse", lambda a: a.astype(np.float32)),
            ("nonfinite", "gin_knn_unique", lambda a: np.full_like(a, np.nan)),
            ("negative degree", "degree", lambda a: -a),
        ):
            with self.subTest(name=name):
                caches = self.caches()
                self.change_cache(caches["train0"]["masked"], key, transform)
                with self.assertRaises(ValueError):
                    build_view_banks(caches, self.rows())
        caches = self.caches()
        rows = self.rows()
        for bad in ({**rows, "test0": np.array([0])},
                    {**rows, "train0": np.array([1, 1])},
                    {**rows, "train0": np.array([10000])}):
            with self.assertRaises(ValueError):
                build_view_banks(caches, bad)
        with self.assertRaises(ValueError):
            build_view_banks({**caches, "train2": caches["train0"]}, rows)

    def test_reference_bank_scaling_and_exact_query_distance_are_strategy_specific(self):
        banks, _ = build_view_banks(self.caches(), self.rows())
        detectors = fit_detectors(banks, k=10)
        for kind in ("clean", "pooled"):
            for arm in ARMS:
                reference = banks[kind][arm].astype(np.float64)
                query = np.array([[17., 22.], [1200., 1200.]])
                mean, scale = reference.mean(0), np.maximum(reference.std(0), .001)
                distance = np.sqrt(np.sum((((query[:, None, :] - mean) / scale) -
                                           ((reference[None, :, :] - mean) / scale)) ** 2, axis=2))
                expected = np.sort(distance, axis=1)[:, :10].mean(axis=1)
                actual, _ = detectors[kind][arm].score(query)
                np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=1e-13)
        with self.assertRaises(ValueError):
            fit_detectors(banks, k=41)

    def test_pooled_calibration_keeps_equal_dependent_view_mass_and_ties(self):
        clean, masked = np.array([0., 1., 1., 2.]), np.array([1., 1., 2., 5.])
        pooled = pool_calibration(clean, masked)
        np.testing.assert_array_equal(pooled, [0, 1, 1, 2, 1, 1, 2, 5])
        query = np.array([-1., 0., 1., 2., 5., 6.])
        margin, probability = empirical_tail_margin(pooled, query, alpha=.2)
        expected = np.array([(1 + np.count_nonzero(pooled >= x)) / 9 for x in query])
        np.testing.assert_array_equal(probability, expected)
        np.testing.assert_allclose(margin, np.log(.2 / expected), rtol=0, atol=0)
        np.testing.assert_array_equal(margin >= 0, expected <= .2)
        pooled[:] = 999
        np.testing.assert_array_equal(clean, [0, 1, 1, 2])
        np.testing.assert_array_equal(masked, [1, 1, 2, 5])

    def test_one_percent_tail_keeps_boundary_and_duplicate_scores_conservative(self):
        calibration = np.arange(99, dtype=np.float64)
        margin, probability = empirical_tail_margin(calibration, np.array([98., 99., 100.]))
        np.testing.assert_array_equal(probability, [.02, .01, .01])
        np.testing.assert_array_equal(margin >= 0, [False, True, True])
        tied = np.ones(10000)
        _, p = empirical_tail_margin(tied, np.array([1., 2.]))
        self.assertEqual(p[0], 1.)
        self.assertEqual(p[1], 1 / 10001)

    def test_calibration_guards_and_empty_queries(self):
        for clean, masked in (([], []), ([1], [1, 2]), ([np.inf], [1]), ([[1]], [[1]])):
            with self.assertRaises(ValueError):
                pool_calibration(np.asarray(clean), np.asarray(masked))
        for alpha in (0, 1, -1, np.inf, np.nan, True):
            with self.assertRaises(ValueError):
                empirical_tail_margin(np.array([1.]), np.array([2.]), alpha)
        for cal, query in ((np.array([]), np.array([1.])), (np.array([1.]), np.array([np.nan]))):
            with self.assertRaises(ValueError):
                empirical_tail_margin(cal, query)
        margin, p = empirical_tail_margin(np.array([1.]), np.array([]))
        self.assertEqual(len(margin), 0)
        self.assertEqual(len(p), 0)


if __name__ == "__main__":
    unittest.main()
