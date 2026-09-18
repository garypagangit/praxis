"""Small scientific-contract tests, independent of any benchmark outcomes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import analyze_revision as a
import semantic_checker as s


def record(name, base="A", evidence="C", base_correct=False, evidence_correct=True):
    pair = {"vanilla": {"answer": base, "valid": base in list("ABCD"), "correct": base_correct},
            "evidence": {"answer": evidence, "valid": evidence in list("ABCD"), "correct": evidence_correct}}
    return {"id": name, "source_group": "test", "models": {m: copy.deepcopy(pair) for m in a.MODELS}}


def score(name, old, new):
    return {name: {"options": {"A": {"max_entailment": old}, "C": {"max_entailment": new}}}}


class RevisionTests(unittest.TestCase):
    def test_strict_margin_inclusive_support(self):
        rows = [record("x")]
        values = score("x", .25, .5)
        policy = {"always_baseline": False, "support": .5, "margin": .25}
        self.assertFalse(a.choose(rows, values, policy).any())
        policy["margin"] = .1
        self.assertTrue(a.choose(rows, values, policy).all())
        policy["support"] = .50001
        self.assertFalse(a.choose(rows, values, policy).any())

    def test_invalid_original_zero_support_invalid_evidence_rejected(self):
        rows = [record("valid_alternative", base="INVALID"),
                record("invalid_alternative", evidence="INVALID", evidence_correct=False),
                record("same", base="A", evidence="A")]
        values = score("valid_alternative", .99, .6)
        chosen = a.choose(rows, values, {"always_baseline": False, "support": .5, "margin": .5})
        self.assertEqual(chosen.tolist(), [[True, True], [False, False], [False, False]])

    def test_fixed_grid_picks_benefit_without_harm(self):
        rows = [record("benefit"), record("harm", base_correct=True, evidence_correct=False)]
        values = {**score("benefit", .2, .9), **score("harm", .1, .2)}
        winner, candidates = a.select_calibration(rows, values)
        self.assertEqual(len(candidates), 21)
        self.assertEqual(winner["policy"], {"always_baseline": False, "support": .9, "margin": .5})
        self.assertEqual(winner["metrics"]["pooled_net_corrections"], 2)
        self.assertEqual(winner["metrics"]["pooled_induced_errors"], 0)
        self.assertEqual(winner["metrics"]["mean_gain_pp"], 50.)

    def test_no_gain_tie_retains_baseline(self):
        rows = [record("x", base_correct=True, evidence_correct=True)]
        winner, _ = a.select_calibration(rows, score("x", .2, .9))
        self.assertTrue(winner["policy"]["always_baseline"])

    def test_lexicographic_ties(self):
        def candidate(net, harms, changes, support, margin):
            return {"metrics": {"pooled_net_corrections": net, "pooled_induced_errors": harms,
                    "pooled_accepted_changes": changes},
                    "policy": {"always_baseline": False, "support": support, "margin": margin}}
        items = [candidate(3, 2, 8, .9, .5), candidate(3, 1, 8, .9, .5),
                 candidate(3, 1, 7, .5, .5), candidate(3, 1, 7, .9, .1), candidate(3, 1, 7, .9, .5)]
        self.assertEqual(sorted(items, key=a.rank_calibration), items)

    def test_source_stratified_bootstrap_preserves_counts_and_pairing(self):
        weights = a.bootstrap_weights(["a", "a", "b"], replicates=100)
        np.testing.assert_allclose(weights.sum(axis=1), 1)
        np.testing.assert_allclose(weights[:, :2].sum(axis=1), 2/3)
        np.testing.assert_allclose(weights[:, 2], 1/3)
        paired = weights @ np.asarray([[1, -1], [0, 0], [0, 0]])
        np.testing.assert_allclose(paired[:, 0], -paired[:, 1])

    def test_routing_counts_and_recovery_harm_accounting(self):
        base = np.asarray([[False, True], [True, False]], dtype=bool)
        evidence = ~base
        use = np.asarray([[True, True], [False, False]])
        metrics = a.summarize(base, evidence, use, np.ones_like(base), np.array([[.5, .5]]))
        self.assertEqual(metrics["models"]["llama"]["recoveries"], 1)
        self.assertEqual(metrics["models"]["qwen"]["induced_errors"], 1)
        self.assertEqual(metrics["models"]["qwen"]["rejected_useful_corrections"], 1)
        self.assertEqual(metrics["mean_delta_vs_baseline_pp"], 0)

    def test_only_unrequested_empty_option_allowed_and_gold_rejected(self):
        row = {"id": "x", "question": "Which option?", "options": {"A": "one", "B": "two", "C": "three", "D": ""},
               "evidence": [{"text": "one"}], "required_options": ["A", "C"]}
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/"safe.jsonl"
            file.write_text(json.dumps(row)+"\n", encoding="utf-8")
            self.assertEqual(s.validate_inputs(file), [row])
            row["required_options"].append("D")
            file.write_text(json.dumps(row)+"\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                s.validate_inputs(file)
            row["required_options"] = ["A", "C"]
            row["answer"] = "A"
            file.write_text(json.dumps(row)+"\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                s.validate_inputs(file)


if __name__ == "__main__":
    unittest.main()
