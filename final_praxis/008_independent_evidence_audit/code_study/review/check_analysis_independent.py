"""Manually specified, outcome-free independent accounting controls.

No benchmark data, model outputs, programs or network are accessed. Run after the
analysis source is frozen; the receipt binds the exact source files inspected.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import analysis as model
import offline_analysis as offline


def decision(task, arm, accept=False, kind="harmful", **kw):
    y0, y1 = {"harmful": (True, False), "useful": (False, True),
              "unknown": (True, None)}[kind]
    value = dict(task_id=str(task), split="heldout", cohort="native",
                 reviewer="r1", proposer=None, intent="native_" + kind,
                 proposal_id="native_" + kind, arm=arm, replicate=0,
                 y0=y0, y1=y1, direction=kind, eligible=True,
                 eligibility_reasons=[], proposal_status="native",
                 model_valid=True, authenticated_failure=False,
                 decision="accept" if accept else "keep")
    value.update(kw)
    return value


def observation(task, policy, detected, replicate=0, proposal="p", **kw):
    value = dict(task_id=str(task), split="heldout", cohort="native",
                 proposer=None, intent="native_harmful", proposal_id=proposal,
                 direction="harmful", policy=policy, replicate=replicate,
                 budget=8, eligible=True, eligibility_reasons=[],
                 detected=detected, logical_supplier_executions=16,
                 logical_independent_executions=8)
    value.update(kw)
    return value


def recommendation_fixture():
    values = []
    for reviewer in ("r1", "r2"):
        for task in range(40):
            for kind in ("harmful", "useful"):
                for arm in ("uniform_a", "edit", "hybrid"):
                    yes = arm != "hybrid" if kind == "harmful" else True
                    if kind == "useful" and task == 0 and arm == "uniform_a":
                        yes = False  # One useful improvement; avoids all-zero CI.
                    values.append(decision(task, arm, yes, kind, reviewer=reviewer))
    return values


class IndependentControls(unittest.TestCase):
    def test_exact_tail_six_favorable_two_unfavorable(self):
        # C(8,6)+C(8,7)+C(8,8) = 28+8+1.
        self.assertEqual(model.exact_paired_p(6, 2), 37 / 256)

    def test_holm_unsorted_four(self):
        actual = model.holm_adjust([.04, .01, .001, .07])
        for a, b in zip(actual, [.08, .03, .004, .08]):
            self.assertAlmostEqual(a, b)

    def test_pair_direction_and_cell_counts(self):
        pairs = [(True, False)] * 3 + [(False, True)] + [(True, True)] * 2
        rows = [decision(t, arm, yes) for t, pair in enumerate(pairs)
                for arm, yes in zip(("selected_w", "uniform_w"), pair)]
        result = model.paired_comparison(model.prepare_rows(rows)[0],
                                        "selected_w", "uniform_w", "reviewer_only", 50)
        harm = result["directions"]["harmful"]
        self.assertEqual(harm["paired_cells"], dict(both_accept=2, left_only_accept=3,
                                                  right_only_accept=1, neither_accept=0))
        self.assertEqual(harm["difference"], 1 / 3)
        self.assertEqual(harm["one_sided_exact_p"], 5 / 16)

    def test_unknown_keep_retains_known_original(self):
        rows = model.prepare_rows([decision("a", "hybrid", kind="unknown"),
                                   decision("b", "hybrid", True, kind="unknown")])[0]
        out = model.summarize_arm(rows)["layers"]["enforced"]
        self.assertEqual(out["final_reserved_suite_unknown"], 1)
        self.assertEqual(out["final_reserved_suite_confirmed_pass_all_assigned"],
                         dict(numerator=1, denominator=2, rate=.5))

    def test_duplicate_assignment_rejected(self):
        row = decision("x", "hybrid")
        with self.assertRaises(ValueError):
            model.prepare_rows([row, row])

    def test_development_and_repeat_cannot_enlarge_primary(self):
        rows = [decision("h", arm, arm == "selected_w") for arm in ("selected_w", "uniform_w")]
        extra = [{**r, "replicate": 1} for r in rows]
        extra += [decision("d", arm, arm == "uniform_w", split="dev")
                  for arm in ("selected_w", "uniform_w")]
        first = model.analyze(rows, ("r1", "r2"), bootstrap_samples=20)
        second = model.analyze(rows + extra, ("r1", "r2"), bootstrap_samples=20)
        self.assertEqual(first["primary_hypotheses"], second["primary_hypotheses"])
        self.assertEqual(len(second["primary_hypotheses"]), 4)
        self.assertEqual(second["accounting"]["assigned_rows"], 6)

    def test_ineligible_rows_remain_assigned(self):
        rows = [decision("h", "selected_w", True, eligible=False,
                         eligibility_reasons=["source_incompatible"])]
        result = model.analyze(rows, ("r1", "r2"), bootstrap_samples=20)
        self.assertEqual(result["accounting"]["ineligible_rows"], 1)
        self.assertEqual(result["accounting"]["assigned_rows"], 1)
        self.assertTrue(all(h["family_p"] == 1 for h in result["primary_hypotheses"]))

    def test_joint_cluster_bootstrap_preserves_directions(self):
        rows = [decision(t, arm, arm == ("uniform_a" if t == "a" else "hybrid"), kind)
                for t in ("a", "b") for kind in ("harmful", "useful")
                for arm in ("uniform_a", "hybrid")]
        result = model.paired_comparison(model.prepare_rows(rows)[0], "uniform_a", "hybrid", "enforced", 100)
        self.assertEqual(result["directions"]["harmful"]["ci95"], result["directions"]["useful"]["ci95"])
        self.assertEqual(result["independent_task_clusters"], 2)

    def test_missing_assignment_blocks_recommendation(self):
        expected = recommendation_fixture()
        complete = model.analyze(expected, ("r1", "r2"), bootstrap_samples=100)
        self.assertTrue(all(g["bounded_policy_criteria_met"] for g in complete["policy_gates"]))
        observed = [r for r in expected if not (r["task_id"] == "1" and r["arm"] == "hybrid" and r["direction"] == "harmful")]
        result = model.analyze(observed, ("r1", "r2"), expected, bootstrap_samples=100)
        self.assertEqual(result["accounting"]["missing_rows_materialized"], 2)
        self.assertFalse(any(g["bounded_policy_criteria_met"] for g in result["policy_gates"]))

    def test_offline_tasks_equal_weight_despite_proposal_multiplicity(self):
        rows = []
        for task, proposals, right_wins in (("a", ["a1"], True), ("b", ["b1", "b2", "b3"], False)):
            for proposal in proposals:
                for rep in (0, 1):
                    for policy in ("uniform", "hybrid"):
                        rows.append(observation(task, policy, right_wins == (policy == "hybrid"), rep, proposal))
        result = offline.compare(offline.prepare_rows(rows)[0], "uniform", expected_replicates=(0, 1), bootstrap_samples=50)
        self.assertEqual(result["difference"], 0)  # Source-task means +1,-1; not row mean -0.5.
        self.assertEqual(result["independent_tasks"], 2)
        self.assertEqual(result["paired_rows"], 8)

    def test_offline_unknown_is_miss_but_separately_labeled(self):
        rows = [observation("a", "uniform", None), observation("a", "hybrid", True)]
        result = offline.compare(offline.prepare_rows(rows)[0], "uniform", expected_replicates=(0,), bootstrap_samples=10)
        self.assertEqual(result["difference"], 1)
        self.assertEqual(result["missing_detection_pairs"], 1)
        self.assertIsNone(result["known_detection_only_difference"])

    def test_offline_missing_seed_blocks_complete(self):
        rows = [observation("a", p, p == "hybrid") for p in ("uniform", "hybrid")]
        result = offline.compare(offline.prepare_rows(rows)[0], "uniform", bootstrap_samples=10)
        self.assertEqual(result["missing_paired_replicates"], 19)
        self.assertFalse(result["complete_arm_and_replicate_pairing"])

    def test_offline_cross_budget_pooling_rejected(self):
        rows = [observation("a", "uniform", False), observation("a", "hybrid", True, budget=4)]
        with self.assertRaises(ValueError):
            offline.compare(offline.prepare_rows(rows)[0], "uniform", bootstrap_samples=10)

    def test_equal_overbudget_execution_cannot_pass(self):
        rows = [observation(task, policy, policy == "hybrid", rep, logical_independent_executions=9)
                for task in range(40) for rep in range(20)
                for policy in ("uniform", "edit", "hybrid")]
        result = offline.analyze(rows, bootstrap_samples=20)
        self.assertFalse(any(g["bounded_offline_criteria_met"] for g in result["recommendation_gates"]))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = dict(scope="Independent manually specified synthetic controls only; no study outcomes read",
                   tests_run=result.testsRun, passed=result.testsRun-len(result.failures)-len(result.errors),
                   failures=[str(test) for test, _ in result.failures], errors=[str(test) for test, _ in result.errors],
                   source_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in ("analysis.py", "offline_analysis.py")},
                   control_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    Path(__file__).with_name("ANALYSIS_INDEPENDENT_REVIEW.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
