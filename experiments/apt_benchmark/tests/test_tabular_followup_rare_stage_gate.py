"""Synthetic-only policy tests. No model fits, inference, or real outcomes."""
import copy
import json
from pathlib import Path
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_followup import run_rare_stage_gate as gate

PROTOCOL = json.loads((Path(gate.__file__).parent / "protocol_rare_stage_gate.json").read_text(encoding="utf-8"))
CLASSES = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]


class RareStageGateTests(unittest.TestCase):
    def test_exact_order_statistic_and_strict_ties(self):
        # ceil((9+1)*.9)=9, with no floating-point spuriously tenth rank.
        q = gate.benign_threshold(np.arange(9) / 10, .1)
        self.assertEqual(q["rank"], 9)
        self.assertEqual(q["value"], .8)
        np.testing.assert_array_equal(gate.above(np.array([.79, .8, .81]), q), [False, False, True])
        q95 = gate.benign_threshold(np.zeros(14), .05)
        self.assertEqual(q95["rank"], 15)
        self.assertTrue(q95["infinite"])
        self.assertFalse(gate.above(np.array([0., 1.]), q95).any())

    def test_zero_scores_and_empty_calibration_are_conservative(self):
        q = gate.benign_threshold(np.zeros(300), .005)
        self.assertEqual(q["value"], 0)
        self.assertFalse(gate.above(np.zeros(10), q).any())
        self.assertTrue(gate.benign_threshold([], .01)["infinite"])
        p = np.tile([0., 0., 0., 1., 0., 0.], (300, 1))
        calibrated = gate.calibrate_policy(p, p, CLASSES, PROTOCOL)
        self.assertFalse(gate.route_policy(p, p, CLASSES, PROTOCOL, calibrated)["candidate"].any())
        # A zero normal and zero rare probability gives 0/epsilon, not NaN.
        other = np.array([[0., 0., 1., 0., 0., 0.]])
        attack, rescue = gate.stage_scores(other, CLASSES, PROTOCOL)
        self.assertEqual(attack[0], 1)
        self.assertEqual(rescue[0], 0)

    def test_joint_rescue_can_route_a_case_missed_by_common_channel(self):
        benign = np.tile([.02, .02, .01, .93, .01, .01], (400, 1))
        calibrated = gate.calibrate_policy(benign, benign, CLASSES, PROTOCOL)
        foundation = np.array([[.001, .001, .001, .995, .001, .001]])
        tree = np.array([[.1, .7, .025, .1, .025, .05]])
        flags = gate.route_policy(foundation, tree, CLASSES, PROTOCOL, calibrated)
        self.assertFalse(flags["common_channel"][0])
        self.assertTrue(flags["rescue_only"][0])
        self.assertTrue(flags["candidate"][0])
        self.assertFalse(flags["two_channel_tabicl_only"][0])

    def test_nonbenign_calibration_labels_and_scores_do_not_select_gate(self):
        rng = np.random.default_rng(71)
        ycal = np.r_[np.full(400, 3), np.tile([0, 1, 2, 4, 5], 20)]
        ytest = np.arange(6)
        f = {"calibration_y": ycal, "test_y": ytest,
             "calibration_probabilities": rng.dirichlet(np.ones(6), len(ycal)),
             "test_probabilities": rng.dirichlet(np.ones(6), len(ytest))}
        t = copy.deepcopy(f)
        original, flags = gate.evaluate_pair(f, t, CLASSES, PROTOCOL)
        changed_f, changed_t = copy.deepcopy(f), copy.deepcopy(t)
        for changed in (changed_f, changed_t):
            changed["calibration_y"][400:] = 0  # All rare-stage names erased.
            changed["calibration_probabilities"][400:] = rng.dirichlet(np.ones(6), 100)
        after, other_flags = gate.evaluate_pair(changed_f, changed_t, CLASSES, PROTOCOL)
        self.assertEqual(original["thresholds"], after["thresholds"])
        self.assertEqual(original["policies"], after["policies"])
        np.testing.assert_array_equal(flags["candidate"], other_flags["candidate"])

    def test_conformal_mapping_keeps_empty_and_rare_sets_in_review(self):
        sets = np.array([[False, False, True], [True, False, True], [False, False, False], [True, False, False]])
        np.testing.assert_array_equal(gate.conformal_review_flags(sets, 2), [False, True, True, True])

    def rows(self):
        rows = []
        for seed in PROTOCOL["seeds"]:
            policies = {}
            for name, rare_recall in [("candidate", .8), ("single_tabicl", .7), ("single_tree", .6)]:
                policies[name] = {"benign_fpr": .01, "per_stage": {stage: {"routing_fraction": rare_recall if stage in PROTOCOL["rare_classes"] else .7} for stage in CLASSES}}
            rows.append({"seed": seed, "policies": policies})
        return rows

    def test_gate_beats_both_controls_and_requires_all_pairs(self):
        rows = self.rows()
        result = gate.compare_policies(rows, PROTOCOL, CLASSES)
        self.assertEqual(result["status"], "DEVELOPMENT_PROMISING")
        self.assertAlmostEqual(result["mean_minimum_rare_recall_deltas"]["single_tabicl"], .1)
        self.assertEqual(gate.compare_policies(rows[:-1], PROTOCOL, CLASSES)["status"], "INCOMPLETE")
        for row in rows:
            for name in PROTOCOL["rare_classes"]:
                row["policies"]["single_tree"]["per_stage"][name]["routing_fraction"] = .85
        self.assertEqual(gate.compare_policies(rows, PROTOCOL, CLASSES)["status"], "DEVELOPMENT_NEGATIVE")

    def test_fpr_each_seed_and_all_stage_damage_are_enforced(self):
        rows = self.rows()
        rows[0]["policies"]["candidate"]["benign_fpr"] = .016
        self.assertEqual(gate.compare_policies(rows, PROTOCOL, CLASSES)["status"], "DEVELOPMENT_NEGATIVE")
        rows = self.rows()
        for row in rows:
            row["policies"]["candidate"]["per_stage"]["Pivoting"]["routing_fraction"] = .6
        self.assertEqual(gate.compare_policies(rows, PROTOCOL, CLASSES)["status"], "DEVELOPMENT_NEGATIVE")

    def test_review_counts_do_not_claim_stage_classification(self):
        metrics = gate.routing_metrics(np.array([True, False, True, False]), np.array([1, 1, 3, 3]), CLASSES, "NormalTraffic")
        self.assertEqual(metrics["reviewed"], 2)
        self.assertEqual(metrics["benign_fpr"], .5)
        self.assertEqual(metrics["per_stage"]["InitialCompromise"]["routing_fraction"], .5)
        self.assertEqual(metrics["review_queue_attack_precision"], .5)
        self.assertIn("Routing", metrics["interpretation"])

    def test_frozen_protocol_hash_matches_root_commit(self):
        path = Path(gate.__file__).parent / "protocol_rare_stage_gate.json"
        self.assertEqual(gate.analyze_e1.file_hash(path), gate.FROZEN_PROTOCOL_SHA256)
        self.assertEqual(PROTOCOL["status"], "FROZEN_BEFORE_GATE_OUTCOMES")


if __name__ == "__main__":
    unittest.main()
