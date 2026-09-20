"""Synthetic aggregation and exact-replication guards; no model fitting."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.robustness.run import summarize
from experiments.apt_benchmark.robustness_v2.compare import compare


ARMS = ["semantic_event", "entity_context", "random_dropout", "type_dropout", "mixed_dropout", "observed_router"]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def fixture(root, version=2):
    root.mkdir()
    arms = ARMS if version == 2 else ["generic_event", "semantic_event", "entity_context", "context_dropout"]
    conditions = [{"name": "clean", "kind": "clean", "deadline": 0},
                  {"name": "random_50", "kind": "random", "drop_probability": .5, "deadline": 0}]
    if version == 2:
        conditions.append({"name": "execve_absent", "kind": "channel_absent", "channels": ["EXECVE"], "deadline": 0})
    protocol = {"models": arms, "seeds": [1, 2, 3], "conditions": conditions, "datasets": {"synthetic": {"targets": ["T1"]}}}
    provenance = {"input_sha256": "a" * 64, "manifest_sha256": "b" * 64, "protocol_sha256": str(version) * 64}
    receipt = {**provenance, "protocol": protocol}
    if version == 1:
        # Original v1 bound the event/protocol hashes in the prefit receipt;
        # its source-manifest hash lives in RESULTS.json only.
        del receipt["manifest_sha256"]
    write_json(root / "PRE_FIT_RECEIPT.json", receipt)
    labels = np.asarray([1, 0, 1, 0, 0, 0], dtype=np.int8)
    runs = np.asarray(["positive_a", "positive_a", "positive_b", "positive_b", "negative_only", "negative_only"])
    ids = np.asarray(["private_event_" + str(i) for i in range(6)])
    np.savez_compressed(root / "PRIVATE_TARGET_ROSTER.npz", event_ids=ids, run_ids=runs)
    support = {"n": 6, "positive": 2, "negative": 4}
    target = {"status": "COMPLETE", "support": {role: support.copy() for role in ("fit", "development", "calibration", "test")},
              "models": {}, "results": [], "primary_screen": {"status": "FAIL"}}
    for arm in arms:
        threshold = .75 if arm == "mixed_dropout" else .6
        target["models"][arm] = {"threshold": {"threshold_kind": "finite", "threshold_value": threshold,
                                                "decision_rule": "class_1_score > threshold"}}
        for condition in conditions:
            for seed in [1, 2, 3] if condition["kind"] == "random" else [1]:
                scores = np.asarray([.7, .4, .65, .7, .1, .2] if arm == "mixed_dropout" else [.8, .7, .4, .3, .8, .1])
                observed = np.ones(6, dtype=bool)
                row = {"arm": arm, "condition": condition["name"], "seed": seed, "deadline_seconds": 0,
                       "fixed_0_5": summarize(labels, scores, observed, .5),
                       "calibrated": summarize(labels, scores, observed, threshold), "by_run": {}}
                for run in sorted(set(runs)):
                    mask = runs == run
                    row["by_run"][run] = {"fixed_0_5": summarize(labels[mask], scores[mask], observed[mask], .5),
                                          "calibrated": summarize(labels[mask], scores[mask], observed[mask], threshold)}
                target["results"].append(row)
                np.savez_compressed(root / f"PRIVATE_T1_{arm}_{condition['name']}_{seed}.npz", y=labels, score=scores, observed=observed)
    result = {"status": "COMPLETE", "dataset": "synthetic", **provenance, "targets": {"T1": target}}
    write_json(root / "RESULTS.json", result)
    return result


class ComparisonGuards(unittest.TestCase):
    def test_exact_replication_and_positive_run_votes_are_separate_by_point(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root / "v2")
            fixture(root / "v1", 1)
            report = compare(root / "v2", root / "comparison", root / "v1")
            replication = report["baseline_replication"]
            self.assertEqual(replication["status"], "PASS")
            self.assertEqual(replication["targets"]["T1"]["prediction_files_checked"], 12)
            self.assertEqual(replication["targets"]["T1"]["thresholds_equal"], 3)
            target = report["targets"]["T1"]
            self.assertEqual(target["positive_bearing_test_runs"], 2)
            self.assertEqual(target["excluded_zero_positive_test_runs"], 1)
            fixed = target["conditions"]["clean"]["arms"]["mixed_dropout"]["fixed_0_5"]
            calibrated = target["conditions"]["clean"]["arms"]["mixed_dropout"]["calibrated"]
            self.assertEqual([fixed["paired_positive_runs"]["f1"][x] for x in ("wins", "ties", "losses")], [2, 0, 0])
            self.assertEqual([calibrated["paired_positive_runs"]["f1"][x] for x in ("wins", "ties", "losses")], [0, 1, 1])
            self.assertGreater(fixed["delta_vs_random_dropout"]["f1"], 0)
            self.assertLess(calibrated["delta_vs_random_dropout"]["f1"], 0)
            self.assertEqual(report["v2_provenance"]["results_sha256"], hashlib.sha256((root / "v2/RESULTS.json").read_bytes()).hexdigest())
            self.assertEqual(set(path.name for path in (root / "comparison").iterdir()), {"COMPARISONS.json", "COMPARISONS.md"})
            self.assertNotIn("private_event_", (root / "comparison/COMPARISONS.json").read_text())

    def test_seed_votes_count_runs_once_and_lower_flag_rate_is_a_win(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root / "v2")
            report = compare(root / "v2", root / "comparison")
            point = report["targets"]["T1"]["conditions"]["random_50"]["arms"]["mixed_dropout"]["fixed_0_5"]
            votes = point["paired_positive_runs"]["f1"]
            self.assertEqual(votes["wins"] + votes["ties"] + votes["losses"], 2)
            # RunA removes a negative flag, RunB adds one: one win and one loss.
            flags = point["paired_positive_runs"]["negative_label_flag_rate"]
            self.assertEqual((flags["wins"], flags["ties"], flags["losses"]), (1, 0, 1))
            self.assertEqual(report["baseline_replication"]["status"], "NOT_REQUESTED")

    def test_numerically_changed_private_prediction_is_diagnostic_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root / "v2")
            fixture(root / "v1", 1)
            path = root / "v2/PRIVATE_T1_random_dropout_clean_1.npz"
            with np.load(path, allow_pickle=False) as arrays:
                values = {key: arrays[key].copy() for key in arrays.files}
            values["score"][0] = np.nextafter(values["score"][0], 1)
            np.savez_compressed(path, **values)
            report = compare(root / "v2", root / "comparison", root / "v1")
            self.assertEqual(report["status"], "COMPLETE_DESCRIPTIVE_COMPARISON")
            self.assertEqual(report["baseline_replication"]["status"], "FAIL")
            self.assertTrue(any(f["check"] == "exact_predictions:T1:random_dropout:clean:1" for f in report["baseline_replication"]["failures"]))
            self.assertTrue((root / "v2/RESULTS.json").exists())
            self.assertTrue((root / "comparison/COMPARISONS.json").exists())

    def test_missing_private_prediction_is_diagnostic_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root / "v2")
            fixture(root / "v1", 1)
            (root / "v1/PRIVATE_T1_context_dropout_clean_1.npz").unlink()
            report = compare(root / "v2", root / "comparison", root / "v1")
            self.assertEqual(report["baseline_replication"]["status"], "FAIL")
            self.assertTrue(any(f.get("reason") == "MISSING_OR_INVALID_PRIVATE_NPZ" for f in report["baseline_replication"]["failures"]))

    def test_threshold_or_roster_difference_is_diagnostic_fail(self):
        for mode in ("threshold", "roster"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture(root / "v2")
                old = fixture(root / "v1", 1)
                if mode == "threshold":
                    old["targets"]["T1"]["models"]["context_dropout"]["threshold"]["threshold_value"] = .60001
                    write_json(root / "v1/RESULTS.json", old)
                else:
                    path = root / "v1/PRIVATE_TARGET_ROSTER.npz"
                    with np.load(path, allow_pickle=False) as arrays:
                        ids, runs = arrays["event_ids"][::-1], arrays["run_ids"][::-1]
                    np.savez_compressed(path, event_ids=ids, run_ids=runs)
                report = compare(root / "v2", root / "comparison", root / "v1")
                self.assertEqual(report["baseline_replication"]["status"], "FAIL")

    def test_changed_support_or_missing_seed_rejected_without_output(self):
        for mode in ("support", "seed", "duplicate"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = fixture(root / "v2")
                rows = result["targets"]["T1"]["results"]
                if mode == "support":
                    rows[0]["by_run"]["positive_a"]["fixed_0_5"]["positive"] = 9
                elif mode == "seed":
                    rows.pop()
                else:
                    rows.append(copy.deepcopy(rows[0]))
                write_json(root / "v2/RESULTS.json", result)
                with self.assertRaises(ValueError):
                    compare(root / "v2", root / "comparison")
                self.assertFalse((root / "comparison").exists())

    def test_source_mismatch_is_replication_fail_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root / "v2")
            old = fixture(root / "v1", 1)
            old["input_sha256"] = "c" * 64
            write_json(root / "v1/RESULTS.json", old)
            receipt = json.loads((root / "v1/PRE_FIT_RECEIPT.json").read_text())
            receipt["input_sha256"] = "c" * 64
            write_json(root / "v1/PRE_FIT_RECEIPT.json", receipt)
            report = compare(root / "v2", root / "comparison", root / "v1")
            self.assertEqual(report["baseline_replication"]["status"], "FAIL")
            self.assertEqual(report["baseline_replication"]["failures"][0]["check"], "same_dataset_and_frozen_source")
            with self.assertRaises(FileExistsError):
                compare(root / "v2", root / "comparison", root / "v1")

    def test_incomplete_v2_rejected_but_unsupported_target_not_scored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = fixture(root / "v2")
            result["status"] = "RUNNING"
            write_json(root / "v2/RESULTS.json", result)
            with self.assertRaisesRegex(ValueError, "completed"):
                compare(root / "v2", root / "comparison")
            result["status"] = "COMPLETE"
            target = result["targets"]["T1"]
            target.update(status="UNSUPPORTED_BOTH_CLASSES_REQUIRED", results=[], models={})
            write_json(root / "v2/RESULTS.json", result)
            report = compare(root / "v2", root / "comparison")
            self.assertEqual(report["targets"]["T1"]["conditions"], {})


if __name__ == "__main__":
    unittest.main()
