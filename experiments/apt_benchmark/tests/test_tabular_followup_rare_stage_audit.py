"""Synthetic tampering tests for the independent review-policy auditor."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_followup import audit_rare_stage_gate as audit
from experiments.apt_benchmark.tabular_followup import run_rare_stage_gate as producer

PROTOCOL = json.loads((Path(producer.__file__).parent / "protocol_rare_stage_gate.json").read_text(encoding="utf-8"))
CLASSES = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]


class RareStageAuditTests(unittest.TestCase):
    def fixture(self):
        rng = np.random.default_rng(193)
        cal_y = np.r_[np.full(400, 3), np.tile([0, 1, 2, 4, 5], 14)]
        test_y = np.tile(np.arange(6), 4)
        packets = []
        for _ in range(2):
            packets.append({"calibration_y": cal_y, "test_y": test_y,
                            "calibration_probabilities": rng.dirichlet(np.ones(6), len(cal_y)),
                            "test_probabilities": rng.dirichlet(np.ones(6), len(test_y))})
        result, flags = producer.evaluate_pair(*packets, CLASSES, PROTOCOL)
        result["seed"] = PROTOCOL["seeds"][0]
        saved = {f"{name}_{result['seed']}": value.copy() for name, value in flags.items()}
        return result, packets, saved

    def test_valid_synthetic_producer_agrees_and_flag_tamper_fails(self):
        result, packets, saved = self.fixture()
        audit.verify_row(result, *packets, CLASSES, PROTOCOL, saved)
        key = f"candidate_{result['seed']}"
        saved[key][0] = ~saved[key][0]
        with self.assertRaisesRegex(ValueError, "Routing packet differs"):
            audit.verify_row(result, *packets, CLASSES, PROTOCOL, saved)

    def test_reported_threshold_rank_or_fpr_tamper_fails(self):
        result, packets, saved = self.fixture()
        changed = copy.deepcopy(result)
        changed["thresholds"]["rescue_joint"]["rank"] -= 1
        with self.assertRaisesRegex(ValueError, "thresholds"):
            audit.verify_row(changed, *packets, CLASSES, PROTOCOL, saved)
        changed = copy.deepcopy(result)
        changed["policies"]["candidate"]["benign_fpr"] += .01
        with self.assertRaisesRegex(ValueError, "routing metrics"):
            audit.verify_row(changed, *packets, CLASSES, PROTOCOL, saved)

    def test_rational_rank_and_ties_are_not_relaxed(self):
        self.assertEqual(audit.quantile_record(np.zeros(9), .1)["rank"], 9)
        record = audit.quantile_record(np.zeros(14), .05)
        self.assertEqual(record["rank"], 15)
        self.assertIsNone(record["value"])
        p = np.tile([.02, .02, .01, .93, .01, .01], (400, 1))
        model = {"calibration_y": np.full(400, 3), "test_y": np.array([3]),
                 "calibration_probabilities": p, "test_probabilities": p[:1]}
        _, flags = audit.reconstruct_row(model, model, CLASSES, PROTOCOL)
        self.assertFalse(flags["candidate"].any())
        self.assertFalse(flags["single_tabicl"].any())

    def test_ninety_five_class_conditional_infinite_rare_threshold_reviews_all(self):
        result, packets, saved = self.fixture()
        expected, _ = audit.verify_row(result, *packets, CLASSES, PROTOCOL, saved)
        cp = next(c for c in expected["conformal_controls"] if c["model"] == "tabicl_v2" and c["nominal_coverage"] == .95)
        self.assertTrue(cp["calibration"]["threshold_infinite"][CLASSES.index("InitialCompromise")])
        self.assertEqual(cp["routing_metrics"]["review_fraction"], 1.)

    def summary_rows(self):
        rows = []
        for index, seed in enumerate(PROTOCOL["seeds"]):
            policies = {}
            for name in ["candidate", *PROTOCOL["controls"]]:
                per_stage = {stage: {"routing_fraction": .7} for stage in CLASSES}
                if name == "candidate":
                    per_stage["InitialCompromise"]["routing_fraction"] = .9 if index % 2 else .5
                    per_stage["DataExfiltration"]["routing_fraction"] = .5 if index % 2 else .9
                else:
                    per_stage["InitialCompromise"]["routing_fraction"] = .4
                    per_stage["DataExfiltration"]["routing_fraction"] = .4
                policies[name] = {"per_stage": per_stage, "benign_fpr": .01}
            rows.append({"seed": seed, "policies": policies})
        return rows

    def test_summary_uses_minimum_before_seed_mean_and_catches_inflation(self):
        rows = self.summary_rows()
        expected = audit.primary_summary(rows, CLASSES, PROTOCOL)
        reported = producer.compare_policies(rows, PROTOCOL, CLASSES)
        audit.compare(reported, expected)
        self.assertAlmostEqual(expected["mean_minimum_rare_recall_deltas"]["single_tabicl"], .1)
        self.assertEqual(expected["status"], "DEVELOPMENT_PROMISING")
        changed = copy.deepcopy(reported)
        # Incorrectly taking min after averaging would claim .7-.4=.3.
        changed["mean_minimum_rare_recall_deltas"]["single_tabicl"] = .3
        with self.assertRaises(ValueError):
            audit.compare(changed, expected)
        rows[0]["policies"]["candidate"]["benign_fpr"] = .016
        self.assertEqual(audit.primary_summary(rows, CLASSES, PROTOCOL)["status"], "DEVELOPMENT_NEGATIVE")
        self.assertEqual(audit.primary_summary(rows[:-1], CLASSES, PROTOCOL)["status"], "INCOMPLETE")

    def test_changed_artifact_bytes_rejected_and_frozen_code_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = ["PREFIT_RECEIPT.json", "SOURCE_ANALYSIS.json", "AGGREGATE.json", "ROUTING_PRIVATE.npz"]
            for name in names:
                (root / name).write_bytes(b"synthetic fixture")
            completion = {"artifact_sha256": {name: audit.digest(root / name) for name in names}}
            audit.verify_artifacts(root, completion)
            (root / "ROUTING_PRIVATE.npz").write_bytes(b"changed synthetic fixture")
            with self.assertRaisesRegex(ValueError, "artifact hash differs"):
                audit.verify_artifacts(root, completion)
        self.assertEqual(audit.digest(Path(producer.__file__)), audit.RUNNER_HASH)
        self.assertEqual(audit.digest(Path(producer.__file__).parent / "protocol_rare_stage_gate.json"), audit.PROTOCOL_HASH)


if __name__ == "__main__":
    unittest.main()
