"""Synthetic-only tests of case-control weighting and baseline provenance."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch import run_e1
from experiments.apt_benchmark.tabular_batch import run_e1_cpu_prescreen as screen


class PrescreenTests(unittest.TestCase):
    def data(self):
        y = np.repeat(np.arange(3), 42)
        split = np.tile(np.r_[np.zeros(35), np.ones(2), np.full(5, 2)], 3).astype(int)
        return {"X": np.arange(len(y) * 2, dtype=float).reshape(-1, 2), "y": y, "split": split,
                "group_sha256": np.asarray([f"{i:064x}" for i in range(len(y))]),
                "classes": np.asarray(["DataExfiltration", "InitialCompromise", "NormalTraffic"]),
                "feature_names": np.asarray(["a", "b"])}

    def test_query_keeps_every_attack_and_restores_original_prevalence(self):
        data = self.data()
        query, weights, description = screen.query_design(data, normal_count=3)
        self.assertEqual(description["rows"], 13)
        self.assertEqual(description["attack_rows"], 10)
        self.assertEqual(description["original_test_normal_rows"], 5)
        self.assertAlmostEqual(weights.sum(), 15)
        all_attacks = np.flatnonzero((data["split"] == 2) & (data["y"] != 2))
        self.assertEqual(set(query[data["y"][query] != 2]), set(all_attacks))
        permutation = np.random.default_rng(7).permutation(len(data["y"]))
        shuffled = {key: value[permutation] if key in ("X", "y", "split", "group_sha256") else value for key, value in data.items()}
        other, other_weights, _ = screen.query_design(shuffled, normal_count=3)
        np.testing.assert_array_equal(data["group_sha256"][query], shuffled["group_sha256"][other])
        np.testing.assert_array_equal(weights, other_weights)

    def test_weighted_scores_equal_explicitly_replicated_rows(self):
        y = np.asarray([0, 0, 1, 1])
        probabilities = np.asarray([[.8, .2], [.6, .4], [.8, .2], [.1, .9]])
        weights = np.asarray([1., 1., 3., 3.])
        names = ["Attack", "NormalTraffic"]
        result = screen.evaluate(y, probabilities, names, weights)
        weighted = result["prevalence_weighted_estimated_metrics"]
        expanded = np.repeat(np.arange(len(y)), weights.astype(int))
        expected = run_e1.probability_metrics(y[expanded], probabilities[expanded], names)
        for key in ("macro_f1", "accuracy", "roc_auc_ovr_macro", "average_precision_ovr_macro"):
            self.assertAlmostEqual(weighted[key], expected[key])
        self.assertEqual(weighted["confusion_matrix"], [[2., 0.], [3., 3.]])
        self.assertEqual(result["sampled_benign_false_positives"], 1)
        self.assertEqual(result["estimated_original_test_benign_false_positives"], 3)
        self.assertEqual(weighted["per_stage"]["Attack"]["recall"], result["query_unweighted_metrics"]["per_stage"]["Attack"]["recall"])

    def fake_cell(self, model, seed, f1, cv=None, recall=.8):
        return {"model": model, "seed": seed, "inner_cv_selected_macro_f1": cv,
                "prevalence_weighted_estimated_metrics": {"macro_f1": f1,
                    "per_stage": {name: {"recall": recall} for name in screen.RISKY}}}

    def test_primary_remains_tabicl_and_comparator_uses_original_cv(self):
        cells = []
        for seed in screen.SEEDS:
            cells += [self.fake_cell("xgboost", seed, .4, cv=.9), self.fake_cell("lightgbm", seed, .9, cv=.8),
                      self.fake_cell("tabicl_v2", seed, .5), self.fake_cell("tabpfn_2_5_synthetic", seed, .99)]
        result = screen.primary_summary(cells)
        self.assertEqual(result["status"], "PRELIMINARY_PROMISING")
        self.assertAlmostEqual(result["mean_weighted_estimated_macro_f1_delta"], .1)
        self.assertTrue(all(pair["comparator_selected_by_e1_inner_cv"] == "xgboost" for pair in result["pairs"]))
        cells[2]["prevalence_weighted_estimated_metrics"]["macro_f1"] = 0
        self.assertEqual(screen.primary_summary(cells)["status"], "PRELIMINARY_NEGATIVE")
        self.assertEqual(screen.primary_summary(cells[:-4])["status"], "INCOMPLETE")

    def test_high_risk_guard_can_reject_a_large_estimated_f1_gain(self):
        cells = []
        for seed in screen.SEEDS:
            cells += [self.fake_cell("xgboost", seed, .2, cv=.9, recall=.9),
                      self.fake_cell("lightgbm", seed, .2, cv=.8), self.fake_cell("tabicl_v2", seed, .8, recall=.7)]
        self.assertEqual(screen.primary_summary(cells)["status"], "PRELIMINARY_NEGATIVE")
        with self.assertRaises(ValueError):
            screen.primary_summary(cells + [cells[0]])

    def test_protocol_must_be_frozen_and_preserve_exact_scope(self):
        source = Path(screen.__file__).parent
        protocol = json.loads((source / "protocol_e1_cpu_prescreen.json").read_text())
        protocol["status"] = "DRAFT"
        with self.assertRaises(ValueError):
            screen.validate_protocol(protocol, source / "protocol.json")
        protocol["status"] = "FROZEN_BEFORE_FOUNDATION_CLASSIFICATION_OUTCOMES"
        screen.validate_protocol(protocol, source / "protocol.json")
        protocol["normal_query_rows"] = 1000
        with self.assertRaises(ValueError):
            screen.validate_protocol(protocol, source / "protocol.json")

    def test_reused_baseline_rows_and_class_order_are_verified_even_with_valid_file_hashes(self):
        data = self.data()
        query, weights, _ = screen.query_design(data, normal_count=3)
        source = Path(screen.__file__).parent
        e1_path = source / "protocol.json"
        e1_protocol = json.loads(e1_path.read_text())
        names = ("run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt")
        common = {"data_sha256": e1_protocol["data_npz_sha256"], "manifest_sha256": e1_protocol["manifest_sha256"],
                  "protocol_sha256": run_e1.sha256_file(e1_path), "code_sha256": {name: run_e1.sha256_file(source / name) for name in names}}
        support = {}
        for seed in screen.SEEDS:
            rows = run_e1.select_fit_indices(data["y"], data["split"], data["group_sha256"], seed=seed, budget=32)
            support[str(seed)] = {"indices": rows.tolist(), "fingerprints": data["group_sha256"][rows].tolist()}
        execution = {**common, "models": screen.BASELINES, "supports": support}
        execution_binding = run_e1.canonical_hash(execution)
        test_ids = np.flatnonzero(data["split"] == 2)
        probabilities = np.eye(3)[data["y"][test_ids]]
        full_metrics = run_e1.probability_metrics(data["y"][test_ids], probabilities, data["classes"].tolist())
        with tempfile.TemporaryDirectory(prefix="apt-prescreen-baseline-") as temporary:
            root = Path(temporary)
            run_e1.write_json(root / "PREFIT_RECEIPT.json", {"execution": execution, "execution_binding": execution_binding})
            for seed in screen.SEEDS:
                for model in screen.BASELINES:
                    directory = root / "cells" / model / str(seed)
                    directory.mkdir(parents=True)
                    roster = support[str(seed)]
                    binding = run_e1.canonical_hash({**common, "seed": seed, "support": roster})
                    np.savez_compressed(directory / "PREDICTIONS.npz", test_probabilities=probabilities, test_y=data["y"][test_ids],
                                        test_indices=test_ids, classes=data["classes"], selected_fit_indices=np.asarray(roster["indices"]),
                                        selected_fit_fingerprints=np.asarray(roster["fingerprints"]))
                    cv = None
                    if model != "random_forest":
                        grid = e1_protocol["model_grids"][model]
                        cv = {"candidates": [{"parameters": params, "fold_macro_f1": [.5, .5, .5], "mean_macro_f1": .5} for params in grid],
                              "selected_candidate_index": 0, "selected_parameters": grid[0], "selected_mean_macro_f1": .5,
                              "selection_data": "selected fit support only"}
                    cell = {"model": model, "seed": seed, "common_binding": common, "execution_binding": execution_binding,
                            "comparison_binding": binding, "prefit_receipt_sha256": run_e1.sha256_file(root / "PREFIT_RECEIPT.json"),
                            "prediction_sha256": run_e1.sha256_file(directory / "PREDICTIONS.npz"),
                            "selected_fit_fingerprints_sha256": run_e1.canonical_hash(roster["fingerprints"]),
                            "inner_cv": cv, "metrics": {"test": full_metrics}}
                    run_e1.write_json(directory / "CELL.json", cell)
                    run_e1.write_json(directory / "COMPLETE.json", {"execution_binding": execution_binding, "comparison_binding": binding,
                                      "file_sha256": {name: run_e1.sha256_file(directory / name) for name in ("CELL.json", "PREDICTIONS.npz")}})
            cells, _, extracted = screen.extract_baselines(root, data, e1_protocol, e1_path, query, weights)
            self.assertEqual(len(cells), 9)
            np.testing.assert_array_equal(extracted["xgboost_20260921"], np.eye(3)[data["y"][query]])
            directory = root / "cells" / "xgboost" / "20260921"
            with np.load(directory / "PREDICTIONS.npz", allow_pickle=False) as z:
                changed = {key: z[key] for key in z.files}
            changed["classes"] = changed["classes"][::-1]
            np.savez_compressed(directory / "PREDICTIONS.npz", **changed)
            cell = json.loads((directory / "CELL.json").read_text())
            cell["prediction_sha256"] = run_e1.sha256_file(directory / "PREDICTIONS.npz")
            run_e1.write_json(directory / "CELL.json", cell)
            complete = json.loads((directory / "COMPLETE.json").read_text())
            complete["file_sha256"] = {name: run_e1.sha256_file(directory / name) for name in ("CELL.json", "PREDICTIONS.npz")}
            run_e1.write_json(directory / "COMPLETE.json", complete)
            with self.assertRaisesRegex(ValueError, "row/class/support"):
                screen.extract_baselines(root, data, e1_protocol, e1_path, query, weights)


if __name__ == "__main__":
    unittest.main()
