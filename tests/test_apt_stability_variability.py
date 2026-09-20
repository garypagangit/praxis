"""Independent, hand-calculated crossed-factor checks for descriptive analysis."""
import copy
import hashlib
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest

from experiments.apt_final.normal_stability.analysis import variability as analysis


def fixture():
    config = {"datasets": ["tiny"], "folds": [{"name": x} for x in "ABCD"],
              "strategies": {"clean": {}}, "representations": ["local_knn", "gin_knn"],
              "conditions": {"clean": 0.0}, "encoder_seeds": [11, 22, 33], "bank_seeds": [41, 42, 43]}
    # Column ranges: .2, .4, .5. Row ranges: .3, .4, .6.
    matrix = [[.1, .2, .4], [.2, .5, .6], [.3, .6, .9]]
    result = {"status": "COMPLETE_FIXED_FAMILY_DEVELOPMENT", "normal_records": [], "attack_records": []}
    for f, arm, e, b in product(range(4), config["representations"], range(3), range(3)):
        value = (matrix[e][b] if arm == "gin_knn" else .1 + b * .1) + f * .01
        identity = {"dataset": "tiny", "fold": "ABCD"[f], "strategy": "clean", "representation": arm,
                    "condition": "clean", "encoder_seed": config["encoder_seeds"][e],
                    "bank_seed": config["bank_seeds"][b],
                    "duplicate_of_encoder_seed": 11 if arm == "local_knn" and e else None}
        result["normal_records"].append({**identity, "metrics": {"false_positive_rate": value}})
        result["attack_records"].append({**identity, "metrics": {"false_positive_rate": value / 2,
                                                                   "recall": value, "f1": value / 4}})
    return result, config


class FactorVariability(unittest.TestCase):
    def test_conditional_ranges_match_hand_computation_without_pseudoreplication(self):
        result, config = fixture()
        report = analysis.summarize(result, config)
        rows = {(r["phase"], r["representation"], r["metric"]): r for r in report["fold_summaries"]}
        neural = rows["normal", "gin_knn", "false_positive_rate"]
        self.assertAlmostEqual(neural["mean_encoder_range"], 1.1 / 3)
        self.assertAlmostEqual(neural["mean_bank_range"], 1.3 / 3)
        self.assertEqual(neural["unique_cases"], 36)
        self.assertAlmostEqual(rows["attack", "gin_knn", "f1"]["mean_encoder_range"], 1.1 / 12)
        local = rows["normal", "local_knn", "false_positive_rate"]
        self.assertEqual(local["mean_encoder_range"], 0)
        self.assertAlmostEqual(local["mean_bank_range"], .2)
        self.assertEqual(local["unique_cases"], 12)
        self.assertEqual(local["duplicate_local_copies_excluded"], 24)
        self.assertEqual(report["phase_counts"]["normal"]["unique_records"], 48)
        self.assertFalse(report["causal_attribution"])
        self.assertFalse(report["independent_campaign_inference"])

    def test_each_range_holds_fold_fixed(self):
        result, config = fixture()
        report = analysis.summarize(result, config)
        local = [r for r in report["conditional_groups"] if r["phase"] == "normal" and r["representation"] == "local_knn"]
        self.assertEqual(len(local), 4)
        for group in local:
            self.assertEqual(len(group["bank_ranges_at_fixed_encoder"]), 1)
            self.assertAlmostEqual(group["mean_bank_range"], .2)
        self.assertAlmostEqual(local[-1]["metric_summary"]["minimum"] - local[0]["metric_summary"]["minimum"], .03)

    def test_missing_or_duplicate_cell_is_rejected(self):
        for corruption in ("missing", "duplicate"):
            result, config = fixture()
            if corruption == "missing":
                result["attack_records"].pop()
            else:
                result["normal_records"].append(copy.deepcopy(result["normal_records"][0]))
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                analysis.summarize(result, config)

    def test_local_copies_must_match_metrics_and_duplicate_marker(self):
        for corruption in ("metric", "marker"):
            result, config = fixture()
            row = next(r for r in result["normal_records"] if r["duplicate_of_encoder_seed"] is not None)
            if corruption == "metric":
                row["metrics"]["false_positive_rate"] += .001
            else:
                row["duplicate_of_encoder_seed"] = None
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                analysis.summarize(result, config)

    def test_nonfinite_or_invalid_rates_are_rejected(self):
        for bad in (float("nan"), float("inf"), -.1, 1.1, True):
            result, config = fixture()
            row = next(r for r in result["attack_records"] if r["representation"] == "gin_knn")
            row["metrics"]["recall"] = bad
            with self.subTest(value=bad), self.assertRaisesRegex(ValueError, "finite rates"):
                analysis.summarize(result, config)

    def test_report_binds_exact_inputs_and_never_overwrites(self):
        result, config = fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cfg, res = root / "config.json", root / "RESULTS.json"
            cfg.write_text(json.dumps(config), encoding="utf-8")
            result["config_sha256"] = hashlib.sha256(cfg.read_bytes()).hexdigest()
            res.write_text(json.dumps(result), encoding="utf-8")
            report = analysis.write_report(res, cfg, root / "analysis")
            self.assertEqual(report["provenance"]["results_sha256"], analysis.digest(res))
            self.assertEqual(report["provenance"]["script_sha256"], analysis.digest(analysis.__file__))
            text = (root / "analysis" / "FACTOR_VARIABILITY.md").read_text(encoding="utf-8")
            self.assertIn("36.67 / 43.33", text)
            self.assertIn("0.00 / 20.00", text)
            with self.assertRaises(FileExistsError):
                analysis.write_report(res, cfg, root / "analysis")
            cfg.write_text(cfg.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Configuration hash"):
                analysis.write_report(res, cfg, root / "new")


if __name__ == "__main__":
    unittest.main()
