"""Tiny end-to-end runner qualification and independent decision-boundary tests.

Only registration verification is mocked: provenance has its own test suite.
Actual model fitting, caching, bank sampling, scoring, calibration, freezing,
attack replay, and decisions run on synthetic CPU graphs here.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from experiments.apt_final.normal_stability import runner


class StabilityRunnerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.data = cls.root / "data"
        cls.data.mkdir()
        cls.out = cls.root / "output"
        actual_config = runner.read(Path(runner.__file__).with_name("config.json"))
        cls.config = {**actual_config, "datasets": ["cadets"], "encoder_seeds": [11, 19],
                      "bank_seeds": [71, 73], "hidden_dim": 8, "bottleneck_dim": 3,
                      "epochs": 1, "max_loss_nodes": 8, "cpu_threads": 1,
                      "embedding_batch_size": 3, "bank_size": 12, "neighbors": 2,
                      "query_chunk_size": 4}
        cls.config_path = cls.root / "config.json"
        cls.config_path.write_text(json.dumps(cls.config), encoding="utf-8")
        (cls.root / "PINNED_BASELINES.json").write_text(json.dumps({
            "records": {"cadets": {"original_best_fixed_mean_clean_f1": .1}}}), encoding="utf-8")
        cls.registration = cls.root / "REGISTRATION.json"
        cls.registration.write_text('{"synthetic_test_only":true}', encoding="utf-8")
        graphs = []
        for i, name in enumerate(["train0", "train1", "train2", "train3", "test0"]):
            path = cls.data / (name + ".npz")
            types = np.asarray([(j + i) % 3 for j in range(8)], dtype=np.int64)
            src = np.asarray([0, 1, 2, 3, 4, 5, i % 3], dtype=np.int64)
            dst = np.asarray([1, 2, 3, 4, 5, 6, 7], dtype=np.int64)
            rel = np.asarray([(j + i) % 2 for j in range(len(src))], dtype=np.int64)
            labels = (np.asarray([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int8) if name == "test0"
                      else np.asarray([{"must_never_be_read": name}], dtype=object))
            np.savez_compressed(path, node_type=types, src=src, dst=dst, relation=rel, y=labels)
            graphs.append({"npz": path.name, "npz_sha256": runner.digest(path)})
        (cls.data / "MANIFEST.json").write_text(json.dumps({"datasets": [{"dataset": "cadets",
            "metadata": {"node_feature_dim": 3, "edge_feature_dim": 2}, "graphs": graphs}]}), encoding="utf-8")
        cls.label_reads = []
        original_load = np.load

        class GuardedArchive:
            def __init__(self, archive, name):
                self.archive, self.name = archive, name

            def __getattr__(self, name):
                return getattr(self.archive, name)

            def __getitem__(self, name):
                if name == "y":
                    if self.name != "test0.npz":
                        raise AssertionError("Normal target labels were accessed")
                    freeze = runner.read(cls.out / "NORMAL_FREEZE.json")
                    normal = runner.read(cls.out / "NORMAL_RESULTS.json")
                    if normal["status"] != "NORMAL_PHASE_COMPLETE" or len(normal["records"]) != 288:
                        raise AssertionError("Test labels accessed before all normal experiments completed")
                    if freeze["normal_results_sha256"] != runner.digest(cls.out / "NORMAL_RESULTS.json"):
                        raise AssertionError("Normal result was not frozen before test labels")
                    score_files = [p for p in freeze["private_files"] if p.endswith("NORMAL_SCORES.npz")]
                    if len(score_files) != 16:
                        raise AssertionError("Some encoder-fold/bank calibration scores were not frozen")
                    cls.label_reads.append({"name": self.name, "normal_records": len(normal["records"]),
                                            "freeze_sha256": runner.digest(cls.out / "NORMAL_FREEZE.json")})
                return self.archive[name]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.archive.close()

        def guarded_load(path, *args, **kwargs):
            result = original_load(path, *args, **kwargs)
            if isinstance(path, (str, Path)) and Path(path).parent.resolve() == cls.data.resolve():
                return GuardedArchive(result, Path(path).name)
            return result

        with (mock.patch.object(runner, "verify_registration", return_value={"git_commit": "synthetic-qualification"}),
              mock.patch.object(np, "load", side_effect=guarded_load), contextlib.redirect_stdout(io.StringIO())):
            cls.result = runner.run(cls.config_path, cls.data, cls.out, cls.registration, "cpu")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_entire_registered_small_grid_runs_and_is_counted_correctly(self):
        result = self.result
        self.assertEqual(result["status"], "COMPLETE_FIXED_FAMILY_DEVELOPMENT")
        self.assertEqual(len(result["normal_records"]), 288)
        self.assertEqual(len(result["attack_records"]), 288)
        self.assertEqual(result["unique_records_per_phase"], 240)
        for phase in ("normal_records", "attack_records"):
            self.assertEqual({r["strategy"] for r in result[phase]}, set(self.config["strategies"]))
            self.assertEqual({r["fold"] for r in result[phase]}, {"A", "B", "C", "D"})
            original = [r for r in result[phase] if r["representation"] == "local_knn" and r["duplicate_of_encoder_seed"] is None]
            duplicated = [r for r in result[phase] if r["representation"] == "local_knn" and r["duplicate_of_encoder_seed"] is not None]
            self.assertEqual(len(original), 48)
            self.assertEqual(len(duplicated), 48)
            runner.verify_duplicates(result[phase])

    def test_test_labels_wait_until_every_normal_bank_and_threshold_is_frozen(self):
        self.assertEqual(len(self.label_reads), 1)
        self.assertEqual(self.label_reads[0]["normal_records"], 288)
        self.assertEqual(self.label_reads[0]["freeze_sha256"], self.result["normal_freeze_sha256"])
        freeze = runner.read(self.out / "NORMAL_FREEZE.json")
        self.assertFalse(freeze["test_labels_accessed_this_run"])
        for relative, expected in freeze["private_files"].items():
            self.assertEqual(runner.digest(self.out / "private" / relative), expected)

    def test_every_bank_uses_only_the_two_fit_roles(self):
        for fold in self.config["folds"]:
            for seed in self.config["encoder_seeds"]:
                root = self.out / "private" / "cadets" / fold["name"] / f"encoder_{seed}"
                frozen = runner.read(root / "FIT_FREEZE.json")
                self.assertEqual(frozen["roles"]["fit"], fold["fit"])
                for bank_seed in self.config["bank_seeds"]:
                    with np.load(root / f"bank_{bank_seed}" / "ROW_SELECTION.npz", allow_pickle=False) as selected:
                        self.assertEqual(set(selected.files), set(fold["fit"]))
                        self.assertNotIn(fold["calibration"], selected.files)
                        self.assertNotIn(fold["validation"], selected.files)
                        self.assertEqual(sum(len(selected[name]) for name in selected.files), 12)

    def test_same_completed_output_cannot_be_reused(self):
        with mock.patch.object(runner, "verify_registration", return_value={"git_commit": "synthetic-qualification"}):
            with self.assertRaises(FileExistsError):
                runner.run(self.config_path, self.data, self.out, self.registration, "cpu")

    def test_changed_duplicate_metrics_are_refused(self):
        records = copy.deepcopy(self.result["normal_records"])
        duplicate = next(r for r in records if r["duplicate_of_encoder_seed"] is not None)
        duplicate["metrics"]["alerts"] += 1
        with self.assertRaisesRegex(ValueError, "duplicate has changed"):
            runner.verify_duplicates(records)


class StabilityDecisionBoundaries(unittest.TestCase):
    def make_family(self):
        config = {"datasets": ["tiny"], "representations": ["local_knn", "mlp_knn", "gin_knn"],
                  "strategies": {"clean": {}, "pooled_calibration": {}, "pooled_reference_calibration": {}},
                  "readiness_max_fpr": .02, "readiness_min_recall": .5,
                  "minimum_mean_f1_improvement": .05}
        normal, attack = [], []
        for strategy in config["strategies"]:
            for arm in config["representations"]:
                for condition in ("clean", "masked"):
                    identity = {"dataset": "tiny", "strategy": strategy, "representation": arm,
                                "condition": condition, "duplicate_of_encoder_seed": None}
                    normal.append({**identity, "metrics": {"false_positive_rate": .02}})
                    f1 = .6 if condition == "clean" or strategy != "clean" else .4
                    attack.append({**identity, "metrics": {"false_positive_rate": .02, "recall": .5, "f1": f1}})
        baseline = {"records": {"tiny": {"original_best_fixed_mean_clean_f1": .2}}}
        return config, normal, attack, baseline

    def test_inclusive_readiness_limits_and_positive_repair_require_all_gates(self):
        config, normal, attack, baseline = self.make_family()
        answer = runner.decide(normal, attack, config, baseline)
        candidate = answer["datasets"]["tiny"]["candidates"]["pooled_calibration/gin_knn"]
        self.assertTrue(candidate["ready"])
        self.assertTrue(candidate["positive_repair"])
        self.assertFalse(answer["novelty_established"])
        self.assertFalse(answer["confirmation"])
        # One adverse case cannot be concealed by averaging favorable cases.
        row = next(r for r in normal if r["strategy"] == "pooled_calibration" and r["representation"] == "gin_knn")
        row["metrics"]["false_positive_rate"] = .0201
        bad = runner.decide(normal, attack, config, baseline)["datasets"]["tiny"]["candidates"]["pooled_calibration/gin_knn"]
        self.assertFalse(bad["normal_ready"])
        self.assertFalse(bad["positive_repair"])

    def test_repair_must_beat_strongest_clean_strategy_not_only_own_arm(self):
        config, normal, attack, baseline = self.make_family()
        strongest = next(r for r in attack if r["strategy"] == "clean" and r["representation"] == "gin_knn" and r["condition"] == "masked")
        strongest["metrics"]["f1"] = .8
        answer = runner.decide(normal, attack, config, baseline)
        candidate = answer["datasets"]["tiny"]["candidates"]["pooled_calibration/mlp_knn"]
        self.assertTrue(candidate["ready"])
        self.assertLess(candidate["masked_f1_gain_vs_strongest_clean_strategy"], 0)
        self.assertFalse(candidate["positive_repair"])

    def test_low_recall_is_not_rescued_by_low_false_positive_rate(self):
        config, normal, attack, baseline = self.make_family()
        for row in attack:
            row["metrics"]["false_positive_rate"] = 0.
            row["metrics"]["recall"] = .49
        answer = runner.decide(normal, attack, config, baseline)
        self.assertEqual(answer["status"], "NO_GO_FIXED_REPAIR_FAMILY")
        self.assertEqual(answer["general_ready_candidates"], [])


if __name__ == "__main__":
    unittest.main()
