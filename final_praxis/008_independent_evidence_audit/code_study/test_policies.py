"""Controls for information boundaries, pairing, budgets and finite-pool math."""
import itertools
import math
import unittest
from policies import (POLICIES, canonical, derived_seed, features, fingerprint,
                      miss_bound, partition_tool_pool, select, supplier_acquisition, testimony)


class PolicyControls(unittest.TestCase):
    def setUp(self):
        self.pool = [{"id": fingerprint([x]), "args": [x]} for x in range(-20, 21)]
        self.original = "def f(x):\n return x < 0\n"
        self.proposal = "def f(x):\n return x <= 1\n"

    def test_information_boundary(self):
        for field in ("expected", "passed", "gold", "canonical_solution"):
            bad = [{**self.pool[0], field: True}]
            with self.assertRaises(ValueError):
                select(bad, self.original, self.proposal, [], "hybrid", "x")

    def test_unique_pool_required(self):
        for duplicate in (self.pool[0], {"id": "different", "args": self.pool[0]["args"]}):
            with self.assertRaises(ValueError):
                partition_tool_pool(self.pool + [duplicate], "x")

    def test_disjoint_supplier_independent(self):
        w, a = partition_tool_pool(self.pool, "x")
        self.assertEqual(len(w), 20)
        self.assertEqual(len(a), 21)
        self.assertFalse({r["id"] for r in w} & {r["id"] for r in a})
        self.assertEqual(partition_tool_pool(self.pool[::-1], "x"), (w, a))

    def test_all_selectors_budget_determinism(self):
        for policy in POLICIES:
            x = select(self.pool, self.original, self.proposal, [[-1], [-2]], policy, "x")
            self.assertEqual(len(x["ids"]), 8)
            self.assertEqual(len(set(x["ids"])), 8)
            self.assertEqual(x, select(self.pool[::-1], self.original, self.proposal, [[-1], [-2]], policy, "x"))
            if policy in ("edit", "complement", "hybrid"):
                self.assertTrue(all(r["probability"] >= 0.5 / r["remaining"] for r in x["draws"]))

    def test_small_and_empty_pools(self):
        for n in (0, 1, 3):
            x = select(self.pool[:n], self.original, self.proposal, [], "hybrid", "x")
            self.assertEqual(x["actual_budget"], n)

    def test_supplier_cannot_read_unacquired_results(self):
        acquired = supplier_acquisition(self.pool, "x")
        results = {r["id"]: True for r in acquired}
        results["unacquired"] = False
        with self.assertRaises(ValueError):
            testimony(acquired, results, "selected", "x")

    def test_selected_witnesses_are_authentic_passing(self):
        acquired = supplier_acquisition(self.pool, "x")
        results = {r["id"]: r["args"][0] < 0 for r in acquired}
        selected = testimony(acquired, results, "selected", "x")
        self.assertEqual(selected["shown"], 2)
        self.assertTrue(all(results[i] for i in selected["ids"]))
        no_pass = testimony(acquired, {r["id"]: False for r in acquired}, "selected", "x")
        self.assertFalse(no_pass["fully_feasible"])
        self.assertEqual(no_pass["ids"], [])

    def test_uniform_testimony_independent_of_results(self):
        acquired = supplier_acquisition(self.pool, "x")
        a = testimony(acquired, {r["id"]: True for r in acquired}, "uniform", "x")
        b = testimony(acquired, {r["id"]: False for r in acquired}, "uniform", "x")
        self.assertEqual(a, b)

    def test_static_fallback_and_no_execution(self):
        x = select(self.pool, "import os\nos.remove('DO_NOT_EXECUTE')", "invalid !", [], "hybrid", "x")
        self.assertEqual(x["static_support"], "unparseable_static_fallback")
        self.assertTrue(all(r["boundary"] == 0 for r in x["draws"]))

    def test_count_feature_types(self):
        tags, nums = features([False, [1, 1], "A1 "])
        self.assertIn("type:bool", tags)
        self.assertIn("sequence_unique:repeated", tags)
        self.assertIn("string_has:space", tags)

    def test_finite_pool_bound(self):
        for n in range(1, 9):
            for bad in range(n + 1):
                for k in range(n + 1):
                    exact = math.comb(n - bad, k) / math.comb(n, k) if k <= n - bad else 0
                    self.assertAlmostEqual(miss_bound(n, bad, k, 1), exact)
                    self.assertGreaterEqual(miss_bound(n, bad, k, 0.5) + 1e-14, exact)
                    self.assertTrue(0 <= miss_bound(n, bad, k) <= 1)


if __name__ == "__main__":
    unittest.main()
