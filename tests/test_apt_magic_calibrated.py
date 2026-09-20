"""Normal-only calibration, phase isolation, and partial-evidence regressions."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.apt_final.magic_calibrated import worker
from experiments.apt_final.magic_reproduction import model_adapter as adapter


class FakeGraph:
    def __init__(self, edges, num_nodes):
        self.edges, self.num_nodes = edges, num_nodes
        self.ndata, self.edata = {}, {}

    def to(self, device):
        self.ndata = {k: v.to(device) for k, v in self.ndata.items()}
        self.edata = {k: v.to(device) for k, v in self.edata.items()}
        return self


class TinyModel(torch.nn.Module):
    def __init__(self, width):
        super().__init__()
        self.linear = torch.nn.Linear(width, 64)

    def embed(self, graph):
        return self.linear(graph.ndata["attr"])

    def forward(self, graph):
        return self.embed(graph).square().mean()


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def fake_author():
    return SimpleNamespace(dgl=SimpleNamespace(graph=FakeGraph),
        model=SimpleNamespace(build_model=lambda args: TinyModel(args.n_dim)),
        utilities=SimpleNamespace(set_random_seed=set_seed,
            create_optimizer=lambda name, model, lr, wd: torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)))


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def config(self):
        config = json.loads((worker.HERE / "config.json").read_text())
        config["training"]["epochs"] = 2
        config["calibration"]["alpha"] = .2
        config["knn"].update(query_batch_size=3, reference_batch_size=2, qualification_queries=4)
        config["resources"].update(safety_seconds=0, minimum_qualification_remaining_seconds=0)
        for spec in config["dataset_specs"].values():
            spec.update(node_types=3, edge_types=2, k=13, expected_calibration_nodes=12, expected_test_nodes=15)
        return config

    def data(self):
        hashes = {}
        for dataset in ("theia", "cadets"):
            (self.root / dataset).mkdir()
            for graph in ("train0", "train1", "train2", "train3", "test0"):
                n = 15 if graph == "test0" else 12
                path = self.root / dataset / (graph + ".npz")
                np.savez(path, node_type=np.arange(n) % 3, src=np.arange(n), dst=(np.arange(n) + 1) % n,
                    relation=np.arange(n) % 2, y=(np.arange(n) < 3).astype(np.int64) if graph == "test0" else np.zeros(n, dtype=np.int64))
                hashes[f"{dataset}/{graph}.npz"] = adapter.digest(path)
        return hashes

    def test_registered_config_and_role_changes(self):
        config = json.loads((worker.HERE / "config.json").read_text())
        worker.validate_config(config)
        for mutation in (lambda c: c["seeds"].reverse(),
                         lambda c: c["dataset_specs"]["theia"]["train_graphs"].append("train3"),
                         lambda c: c["dataset_specs"]["cadets"].update(calibration_graph="test0"),
                         lambda c: c["calibration"].update(alpha=.02)):
            invalid = copy.deepcopy(config)
            mutation(invalid)
            with self.assertRaises(ValueError):
                worker.validate_config(invalid)

    def test_rank_strict_ties_and_small_sample_no_alerts(self):
        scores = np.arange(1000, dtype=np.float64)
        receipt = worker.threshold_from_normal(scores, .01)
        self.assertEqual(receipt["rank_one_based"], 991)
        self.assertEqual(receipt["threshold"], 990)
        self.assertEqual(receipt["calibration_alerts"], 9)
        tied = worker.threshold_from_normal(np.ones(1000), .01)
        self.assertEqual(tied["calibration_ties_at_threshold"], 1000)
        np.testing.assert_array_equal(worker.predict([1, 1.1], tied), [False, True])
        small = worker.threshold_from_normal([1, 2], .01)
        self.assertTrue(small["no_alerts"])
        self.assertIsNone(small["threshold"])
        self.assertFalse(worker.predict([1e100], small).any())

    def test_empirical_tail_and_positive_normalizer_equivalence(self):
        rng = np.random.default_rng(42)
        for n in (99, 100, 101, 1000, 2345):
            scores = rng.integers(0, 40, n).astype(float)
            receipt = worker.threshold_from_normal(scores, .01)
            self.assertLessEqual(worker.predict(scores, receipt).mean(), .01)
            scaled = worker.threshold_from_normal(scores / 7.25, .01)
            queries = rng.normal(20, 30, 51)
            np.testing.assert_array_equal(worker.predict(queries, receipt), worker.predict(queries / 7.25, scaled))

    def test_invalid_scores_and_receipts_refused(self):
        for values in ([], [np.nan], [[1]], [np.inf]):
            with self.assertRaises(ValueError):
                worker.threshold_from_normal(values, .01)
        receipt = worker.threshold_from_normal(np.arange(100), .01)
        receipt["comparison"] = "greater_or_equal"
        with self.assertRaises(ValueError):
            worker.predict([0], receipt)

    def test_metrics_use_fixed_threshold_not_label_oracle(self):
        receipt = worker.threshold_from_normal(np.arange(5), .5)
        measured = worker.metrics([0, 1, 0, 1], [2, 2, 4, 5], receipt)
        self.assertEqual({k: measured[k] for k in ("tp", "fp", "tn", "fn")}, {"tp": 1, "fp": 1, "tn": 1, "fn": 1})
        self.assertEqual(measured["recall"], .5)
        self.assertEqual(measured["false_positive_rate"], .5)
        self.assertFalse(measured["threshold_selected_using_test_labels"])
        self.assertEqual(receipt["threshold"], 2)

    def test_resource_gate_reserves_earlier_tests(self):
        config = self.config()
        args = ({"seconds": 2}, {"seconds": 3, "graphs": [{"seconds": 1, "nodes": 12}], "rows": 36},
                {"seconds": .01, "query_rows": 4}, .1, .1, config["dataset_specs"]["theia"], config, 100)
        passed = worker.estimate_resource(*args, 0)
        held = worker.estimate_resource(*args, 99)
        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(held["status"], "NOT_RUN_RESOURCE_HOLD")
        self.assertEqual(held["available_after_prior_test_reserve"], 1)
        self.assertEqual(passed["author_normalizer_queries"], 0)
        self.assertFalse(passed["test_arrays_or_labels_accessed"])

    def test_any_incomplete_normal_case_prevents_every_test(self):
        config = self.config()
        output = self.root / "output"
        output.mkdir()
        def normal(author, config, dataset, seed, *args):
            return {"case": f"{dataset}/seed_{seed}", "normal_complete": seed != 101,
                    "evaluation_complete": False, "status": "NOT_RUN_RESOURCE_HOLD" if seed == 101 else "NORMAL_COMPLETE_FROZEN"}
        with patch.object(worker, "normal_case", side_effect=normal), patch.object(worker, "evaluate_case") as test, patch.object(worker, "global_freeze") as freeze:
            cases, frozen = worker.execute_cases(None, config, self.root, {}, output, torch.device("cpu"),
                SimpleNamespace(remaining=lambda: 100000., check=lambda: None), {})
        self.assertEqual(len(cases), 6)
        self.assertIsNone(frozen)
        test.assert_not_called()
        freeze.assert_not_called()

    def test_actual_six_case_phase_order_safe_checkpoints_and_partial_access(self):
        config, hashes = self.config(), self.data()
        output = self.root / "output"
        output.mkdir()
        bindings = {"test": "synthetic_only", "config_sha256": "synthetic"}
        accesses, training_graphs = [], []
        def load(*args, **kwargs):
            graph_name = args[2]
            if graph_name == "test0":
                frozen = json.loads((output / "GLOBAL_CALIBRATION_FREEZE.json").read_text())
                self.assertEqual(len(frozen["cases"]), 6)
                self.assertEqual(len(list(output.glob("*/seed_*/NORMAL_RESULT.json"))), 6)
                accesses.append(args[1])
            else:
                self.assertFalse(kwargs.get("labels", False))
            return adapter.load_arrays(*args, **kwargs)
        def fit_load(*args, **kwargs):
            training_graphs.append(args[2])
            self.assertIn(args[2], ("train0", "train1", "train2"))
            return load(*args, **kwargs)
        budget = SimpleNamespace(remaining=lambda: 100000., check=lambda: None)
        with patch.object(worker, "load_arrays", side_effect=load), patch.object(worker.original, "load_arrays", side_effect=fit_load):
            cases, global_hash = worker.execute_cases(fake_author(), config, self.root, hashes, output, torch.device("cpu"), budget, bindings)
        self.assertEqual(len(cases), 6)
        self.assertTrue(all(c["evaluation_complete"] for c in cases), cases)
        self.assertEqual(accesses, ["theia"] * 3 + ["cadets"] * 3)
        self.assertEqual(set(training_graphs), {"train0", "train1", "train2"})
        for case in cases:
            directory = output / case["case"]
            checkpoint = torch.load(directory / "epoch_050.pt", weights_only=True)
            self.assertEqual(checkpoint["completed_epochs"], 2)
            self.assertEqual(checkpoint["bindings"]["seed"], case["seed"])
            with np.load(directory / "FIT_EMBEDDINGS.npz", allow_pickle=False) as archive:
                self.assertEqual(archive["raw"].shape, (36, 64))
                np.testing.assert_array_equal(archive["graph_sizes"], [12, 12, 12])
        preservation = os.environ.get("APT_CALIBRATED_SYNTHETIC_OUTPUT")
        if preservation:
            destination = Path(preservation)
            destination.mkdir(parents=True, exist_ok=False)
            for item in self.root.iterdir():
                if item.is_dir():
                    shutil.copytree(item, destination / item.name)
            (destination / "config.json").write_text(json.dumps(config, indent=2))
            (destination / "SYNTHETIC_CONTEXT.json").write_text(json.dumps({"bindings": bindings, "hashes": hashes, "cases": cases, "global_freeze_sha256": global_hash, "synthetic_only": True}, indent=2))
        normal = json.loads((output / cases[0]["case"] / "NORMAL_RESULT.json").read_text())
        self.assertFalse(normal["test_arrays_loaded"])
        original_embed = TinyModel.embed
        def fail_after_load(model, graph):
            if graph.num_nodes == 15:
                raise worker.ResourceDeadline("synthetic deadline after actual test load")
            return original_embed(model, graph)
        with patch.object(TinyModel, "embed", new=fail_after_load):
            with self.assertRaises(worker.ResourceDeadline):
                worker.evaluate_case(fake_author(), config, normal, self.root, hashes, output, torch.device("cpu"), budget, bindings, global_hash)
        self.assertTrue(normal["test_access_attempted"])
        self.assertTrue(normal["test_arrays_loaded"])
        self.assertTrue(normal["test_labels_loaded"])
        self.assertFalse(normal["evaluation_complete"])

    def test_global_freeze_refuses_incomplete_inventory(self):
        with self.assertRaisesRegex(ValueError, "All six"):
            worker.global_freeze(self.root, [{"case": "theia/seed_0", "normal_complete": False}], ["theia/seed_0"], {})


if __name__ == "__main__":
    unittest.main()
