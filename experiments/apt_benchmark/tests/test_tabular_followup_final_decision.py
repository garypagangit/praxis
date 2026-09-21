"""Synthetic final-report checks; no model execution or partial-result decisions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_benchmark.tabular_followup import report_final_decision as decision
from experiments.apt_benchmark.tests import test_tabular_followup_publication as publication_fixtures


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class FinalDecisionTests(unittest.TestCase):
    def manifest(self, root):
        for name in decision.FINAL_ARTIFACTS:
            write(root / name, {"synthetic": True})
        write(root / "STARTUP_RECEIPT.json", {"synthetic": True})
        manifest = {"status": "COMPLETE_AUDITED", "full_e1_cells": 50, "strong_cells": 60, "review_gate_pairs": 10, "external_cells": 20,
                    "no_model_fitting_or_inference_performed": True, "startup_receipt_sha256": decision.pub.sha(root / "STARTUP_RECEIPT.json"),
                    "artifact_sha256": {name: decision.pub.sha(root / name) for name in decision.FINAL_ARTIFACTS}}
        write(root / "RESULT_MANIFEST.json", manifest)
        return manifest

    def test_manifest_rejects_missing_counts_and_tampered_bound_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifest = self.manifest(root)
            decision.verify_manifest(root)
            changed = deepcopy(manifest); changed["full_e1_cells"] = 49
            write(root / "RESULT_MANIFEST.json", changed)
            with self.assertRaisesRegex(ValueError, "Incomplete manifest count"):
                decision.verify_manifest(root)
            write(root / "RESULT_MANIFEST.json", manifest)
            write(root / "gate/AGGREGATE.json", {"changed": True})
            with self.assertRaisesRegex(ValueError, "Final artifact changed"):
                decision.verify_manifest(root)

    def test_refusal_creates_no_public_decision(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "private"; manifest = self.manifest(root)
            manifest["status"] = "INCOMPLETE"; write(root / "RESULT_MANIFEST.json", manifest)
            output = Path(temp) / "tabular_followup_decision_v1"
            with self.assertRaisesRegex(ValueError, "not complete"):
                decision.generate(root, output, Path(temp) / "benign")
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, "separate"):
                decision.generate(root, root, Path(temp) / "benign")

    def test_external_diagnostic_requires_complete_distinct_model_seed_pairs(self):
        diagnostic = {"status": "COMPLETE_AUDITED", "pairs": [{"seed": seed} for seed in sorted(decision.pub.SEEDS)],
                      "per_seed": [{"model": model, "seed": seed} for model in ("tabicl_v2", "selected_gbdt") for seed in sorted(decision.pub.SEEDS)]}
        decision.verify_external_diagnostic({"source_threshold_diagnostic": diagnostic})
        changed = deepcopy(diagnostic); changed["status"] = "PENDING_MATCHING_FULL_SOURCE_CALIBRATION"
        with self.assertRaisesRegex(ValueError, "incomplete"):
            decision.verify_external_diagnostic({"source_threshold_diagnostic": changed})
        changed = deepcopy(diagnostic); changed["per_seed"][0] = deepcopy(changed["per_seed"][1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            decision.verify_external_diagnostic({"source_threshold_diagnostic": changed})

    def test_selected_tree_tradeoff_uses_fit_cv_and_binary_not_exact_stage(self):
        names = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]
        cells = []
        for condition in ("equal_32_per_class", "abundant_benign_1024"):
            for seed in sorted(decision.pub.SEEDS):
                for model in ("xgboost", "lightgbm"):
                    matrix = [[10 if i == j else 0 for j in range(6)] for i in range(6)]
                    # Two lateral errors are another attack stage: wrong stage, detected attack.
                    matrix[2][2] = 8; matrix[2][4] = 2
                    if condition == "abundant_benign_1024":
                        matrix[2][2] -= 1; matrix[2][3] = 1
                    cells.append({"model": model, "condition": condition, "seed": seed,
                                  "cv_macro_f1": .9 if model == "lightgbm" else .8,
                                  "metrics": {"classes": names, "confusion_matrix": matrix, "macro_f1": .6 if model == "lightgbm" else .99}})
        result = decision.selected_tree_tradeoffs({"cells": cells})
        a, b = (result[c]["mean"] for c in ("equal_32_per_class", "abundant_benign_1024"))
        self.assertAlmostEqual(a["macro_f1"], .6)
        self.assertEqual(a["binary_detection_by_stage"]["LateralMovement"], 1.)
        self.assertAlmostEqual(a["exact_stage_recall"]["LateralMovement"], .8)
        self.assertAlmostEqual(b["binary_detection_by_stage"]["LateralMovement"], .9)
        self.assertTrue(all(r["selected_model"] == "lightgbm" for r in result["equal_32_per_class"]["per_seed"]))

    def report_inputs(self):
        e1, comparison, gate, _ = publication_fixtures.synthetic_values()
        metrics = {"rare_stages": {"InitialCompromise": {"same_test_support": 15, "mean_routed_count": 12., "mean_routing_recall": .8},
                                    "DataExfiltration": {"same_test_support": 106, "mean_routed_count": 79.5, "mean_routing_recall": .75}},
                   "mean_review_queue_attack_precision": .5, "mean_reviewed": 600., "mean_review_fraction": .02,
                   "mean_benign_fpr": .01, "maximum_seed_benign_fpr": .014}
        evidence = {"registered_decisions": {"original_e1": "PASS", "original_e4": "FAIL", "strong_equal_label": "FAIL", "review_policy": "DEVELOPMENT_NEGATIVE"},
                    "review_diagnostics": {"tabicl_mean_minimum_rare_recall": .993333333333, "maximum_possible_gain_over_tabicl": .006666666667,
                                           "tree_addition_mean_attack_reviewed": 1.6, "tree_addition_mean_benign_reviewed": 30.1,
                                           "tree_addition_rare_recall_deltas": {"InitialCompromise": 0., "DataExfiltration": 0.}},
                    "review_absolute_metrics": {name: deepcopy(metrics) for name in decision.POLICIES},
                    "selected_tree_label_tradeoff": {
                        "equal_32_per_class": {"mean": {"macro_f1": .4421, "normal_fpr": .1004, "binary_attack_recall": .9840, "binary_detection_by_stage": {"LateralMovement": .9424}}},
                        "abundant_benign_1024": {"mean": {"macro_f1": .6543, "normal_fpr": .004, "binary_attack_recall": .9570, "binary_detection_by_stage": {"LateralMovement": .8306}}}}}
        transfer = publication_fixtures.PublicationTests().synthetic_transfer_report(complete_diagnostic=True)
        return evidence, e1, comparison, gate, transfer

    def test_report_states_actual_tolerances_workload_and_unequal_label_limit(self):
        text = decision.render(*self.report_inputs())
        for expected in ("+5 percentage points", "5 percentage points of mean recall loss", "1.5% in every seed", "both", "permits a limited average loss",
                         "Queue attack precision", "600.0", "12.00/15", "79.50/106", "95% class-conditional (Mondrian)",
                         "not a claim that 90% Mondrian", "No matched abundant-benign foundation-model arm", "not establish tree architecture superiority",
                         "98.40% to 95.70%", "94.24% to 83.06%", "strong_benign_controls_v1/REPORT.md", "No algorithmic novelty or independent attack-stage validation",
                         "BENIGN_LABEL_NOVELTY_NOTE.md", "distinguish publication status"):
            self.assertIn(expected, text)
        self.assertIn("did not meet its frozen development criteria", text)
        self.assertIn("At the primary argmax operating point", text)
        self.assertIn("separate source-threshold diagnostic", text)
        for expected in ("Ceiling limitation", "only 0.67 percentage points", "registered negative outcome is retained", "Second-model ablation", "+1.6", "+30.1", "not replacement success criteria"):
            self.assertIn(expected, text)

    def test_ceiling_uses_mean_of_per_seed_minima_and_signed_component_costs(self):
        def policy(attack, benign, initial, exfil):
            return {"attack_reviewed": attack, "benign_reviewed": benign, "per_stage": {
                "InitialCompromise": {"routing_fraction": initial}, "DataExfiltration": {"routing_fraction": exfil}}}
        gate = {"primary": {"paired_comparisons": [
                    {"control": "single_tabicl", "control_minimum_rare_routing_recall": .9},
                    {"control": "single_tabicl", "control_minimum_rare_routing_recall": .7},
                    {"control": "single_tree", "control_minimum_rare_routing_recall": .2}]},
                "rows": [{"policies": {"candidate": policy(10, 20, .9, .8), "two_channel_tabicl_only": policy(8, 15, .9, .8)}},
                         {"policies": {"candidate": policy(7, 9, .7, .6), "two_channel_tabicl_only": policy(8, 10, .7, .6)}}]}
        result = decision.review_diagnostics(gate)
        self.assertAlmostEqual(result["maximum_possible_gain_over_tabicl"], .2)
        self.assertEqual(result["tree_addition_mean_attack_reviewed"], .5)
        self.assertEqual(result["tree_addition_mean_benign_reviewed"], 2.)
        self.assertEqual(result["tree_addition_rare_recall_deltas"], {"InitialCompromise": 0., "DataExfiltration": 0.})

    def test_positive_candidate_language_does_not_assert_novel_or_validated_praxis(self):
        values = self.report_inputs()
        values[0]["registered_decisions"]["review_policy"] = "DEVELOPMENT_PROMISING"
        values[0]["registered_decisions"]["strong_equal_label"] = "PASS"
        text = decision.render(*values)
        self.assertIn("candidate for independent validation with attack-stage labels", text)
        self.assertIn("not a completed novel praxis claim", text)
        self.assertIn("No new success threshold", text)

    def test_private_paths_and_row_level_fields_rejected(self):
        for value in ({"model_path": "C:/private"}, {"test_y": [0, 1]}, "C:/private/results", {"target_probabilities": [[.5, .5]]}):
            with self.assertRaises(ValueError):
                decision.pub.aggregate_only(value)


if __name__ == "__main__":
    unittest.main()
