"""Meaningful data, numerical, and train-before-test guards for MAGIC reproduction."""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.apt_final.magic_reproduction import model_adapter as adapter
from experiments.apt_final.magic_reproduction import qualification as qualify
from experiments.apt_final.magic_reproduction import worker


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


def seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def fake_author():
    return SimpleNamespace(dgl=SimpleNamespace(graph=FakeGraph),
        model=SimpleNamespace(build_model=lambda args: TinyModel(args.n_dim)),
        utilities=SimpleNamespace(set_random_seed=seed,
            create_optimizer=lambda name, model, lr, wd: torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)))


class Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.settings = {"query_batch_size": 2, "reference_batch_size": 3,
                         "numerical_rtol": 1e-6, "numerical_atol": 1e-8, "qualification_queries": 4}

    def tearDown(self):
        self.temporary.cleanup()

    def source(self):
        files = {}
        for relative in ("model/autoencoder.py", "model/gat.py", "model/loss_func.py", "utils/utils.py"):
            path = self.root / relative
            path.parent.mkdir(exist_ok=True)
            path.write_text("# bound source\n", encoding="utf-8")
            files[relative] = adapter.digest(path)
        (self.root / "SOURCE_MANIFEST.json").write_text(json.dumps({"commit": adapter.UPSTREAM_COMMIT, "files": files}), encoding="utf-8")

    def data(self):
        (self.root / "theia").mkdir()
        hashes = {}
        for graph in ("train0", "train1", "train2", "train3", "test0"):
            path = self.root / "theia" / (graph + ".npz")
            np.savez(path, node_type=np.arange(12) % 3, src=np.arange(12), dst=(np.arange(12) + 1) % 12,
                     relation=np.arange(12) % 2, y=(np.arange(12) < 3).astype(np.int64) if graph == "test0" else np.zeros(12, dtype=np.int64))
            hashes["theia/" + graph + ".npz"] = adapter.digest(path)
        return hashes

    def config(self):
        return {"training": {"seed": 0, "epochs": 2, "hidden_dim": 64, "num_layers": 3,
                    "learning_rate": .001, "weight_decay": .0005, "mask_rate": .5, "alpha_l": 3., "negative_slope": .2},
                "dataset_specs": {"theia": {"node_types": 3, "edge_types": 2, "k": 17,
                    "train_graphs": ["train0", "train1", "train2", "train3"], "test_graph": "test0",
                    "expected_test_nodes": 12, "author_recall_target": .99996}},
                "knn": {**self.settings, "query_batch_size": 8, "reference_batch_size": 16},
                "resources": {"estimate_multiplier": 1.25, "safety_seconds": 0}, "allow_full_run": True}

    def test_source_hash_mismatch_refused(self):
        self.source()
        adapter.verify_source(self.root)
        (self.root / "model/gat.py").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            adapter.verify_source(self.root)

    def test_extra_source_python_refused(self):
        self.source()
        (self.root / "extra.py").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            adapter.verify_source(self.root)

    def test_qualification_cannot_read_test_or_labels(self):
        with self.assertRaisesRegex(ValueError, "Qualification"):
            adapter.load_arrays(self.root, "theia", "test0", {})
        with self.assertRaisesRegex(ValueError, "Qualification"):
            adapter.load_arrays(self.root, "theia", "train0", {}, labels=True)

    def test_array_hash_binding_and_invalid_indices(self):
        hashes = self.data()
        wrong = {**hashes, "theia/train0.npz": "0" * 64}
        with self.assertRaisesRegex(ValueError, "hash"):
            adapter.load_arrays(self.root, "theia", "train0", wrong)
        path = self.root / "theia/train0.npz"
        np.savez(path, node_type=np.array([0]), src=np.array([0]), dst=np.array([1]), relation=np.array([0]))
        hashes["theia/train0.npz"] = adapter.digest(path)
        with self.assertRaisesRegex(ValueError, "endpoint"):
            adapter.load_arrays(self.root, "theia", "train0", hashes)

    def test_exact_onehot_direction_and_isolate_preservation(self):
        arrays = {"node_type": np.array([2, 0, 1, 0]), "src": np.array([2, 0]),
                  "dst": np.array([0, 1]), "relation": np.array([1, 0])}
        graph = adapter.graph_from_arrays(fake_author(), arrays, {"node_types": 3, "edge_types": 2}, "cpu")
        self.assertEqual(graph.num_nodes, 4)
        np.testing.assert_array_equal(graph.edges[0], [2, 0])
        np.testing.assert_array_equal(graph.edges[1], [0, 1])
        np.testing.assert_array_equal(graph.ndata["attr"], np.eye(3)[[2, 0, 1, 0]])
        np.testing.assert_array_equal(graph.edata["attr"], [[0, 1], [1, 0]])
        self.assertEqual(graph.ndata["attr"].dtype, torch.float32)

    def test_exact_knn_chunks_duplicates_and_no_mutation(self):
        bank = np.array([[0., 0.]] * 6 + [[1., 0.], [3., 4.], [-1., 0.], [0., 2.]])
        query = np.array([[0., 0.], [2., 1.], [3., 4.]])
        old_bank, old_query = bank.copy(), query.copy()
        expected = np.sort(np.linalg.norm(query[:, None] - bank[None], axis=2), axis=1)[:, :7].mean(axis=1)
        actual, receipt = qualify.ExactFullReferenceKNN(bank, 7, "cpu", 2, 3).score(query)
        unchunked, _ = qualify.ExactFullReferenceKNN(bank, 7, "cpu", 99, 99).score(query)
        np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=1e-13)
        np.testing.assert_allclose(actual, unchunked, rtol=1e-13, atol=1e-13)
        np.testing.assert_array_equal(bank, old_bank)
        np.testing.assert_array_equal(query, old_query)
        self.assertEqual(receipt["reference_rows"], 10)
        self.assertFalse(receipt["reference_sampling"])

    def test_duplicate_zero_decisive_direct_oracle(self):
        bank = np.random.default_rng(4).normal(size=(37, 64)).astype(np.float32)
        bank[:24] = bank[0]
        result = qualify.numerical_check(bank, bank[:1], 10, "cpu", self.settings)
        self.assertEqual(result["max_absolute_error"], 0)
        self.assertTrue(result["sklearn_comparison_is_diagnostic"])

    def test_knn_invalid_and_deadline_refused(self):
        with self.assertRaises(ValueError):
            qualify.ExactFullReferenceKNN(np.ones((2, 3)), 3, "cpu")
        with self.assertRaises(ValueError):
            qualify.ExactFullReferenceKNN(np.array([[np.nan]]), 1, "cpu")
        scorer = qualify.ExactFullReferenceKNN(np.ones((3, 2)), 1, "cpu")
        with self.assertRaises(qualify.ResourceDeadline):
            scorer.score(np.ones((1, 2)), lambda: (_ for _ in ()).throw(qualify.ResourceDeadline()))

    def test_zero_variance_is_hold_not_floor(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_NUMERICAL_HOLD"):
            qualify.author_standardize(np.ones((8, 64), dtype=np.float32))

    def test_resource_gate_counts_full_bank_normalizer_and_remaining_epochs(self):
        kwargs = dict(epoch_seconds=10, embedding_seconds=12, test_embedding_seconds=4, query_seconds=2,
            sample_queries=64, reference_rows=1_000_000, test_rows=350_000, serialization_seconds=1,
            index_seconds=2, resources={"estimate_multiplier": 1.25, "safety_seconds": 180})
        held = qualify.resource_estimate(**kwargs, remaining_seconds=2400)
        self.assertEqual(held["status"], "NOT_RUN_RESOURCE_HOLD")
        self.assertEqual(held["components_seconds_before_multiplier"]["remaining_training"], 490)
        self.assertEqual(held["normalizer_queries"], 50000)
        self.assertEqual(held["components_seconds_before_multiplier"]["full_evaluation_scoring"], 10937.5)
        self.assertEqual(qualify.resource_estimate(**kwargs, remaining_seconds=100000)["status"], "PASS")

    def test_author_recall_rule_is_not_maximum_f1(self):
        y = np.array([0, 0, 0, 1, 0, 1])
        score = np.array([.1, .2, .3, .4, .5, .6])
        result = qualify.oracle_metrics(y, score, .99996)
        self.assertEqual(result["author_recall_rule"]["threshold"], .4)
        self.assertEqual(result["author_recall_rule"]["tp"], 2)
        self.assertEqual(result["author_recall_rule"]["fp"], 1)
        self.assertTrue(result["all_threshold_metrics_label_selected"])
        self.assertFalse(result["operational_threshold_evaluated"])
        with self.assertRaises(ValueError):
            qualify.oracle_metrics(y, score, 0.)

    def test_dataset_selector_cannot_reorder_or_add(self):
        config = {"datasets": ["theia", "cadets"]}
        self.assertEqual(worker.select_datasets(config, "cadets"), ["cadets"])
        for invalid in ("cadets,theia", "trace", "theia,theia"):
            with self.assertRaises(ValueError):
                worker.select_datasets(config, invalid)

    def test_small_complete_driver_freezes_before_test_and_safe_checkpoints(self):
        hashes, config = self.data(), self.config()
        output = self.root / "output"
        original_load = adapter.load_arrays
        test_accesses = []
        def guarded_load(*args, **kwargs):
            if args[2] == "test0":
                self.assertTrue((output / "FIT_FREEZE.json").exists())
                freeze = json.loads((output / "FIT_FREEZE.json").read_text())
                self.assertEqual(freeze["completed_epochs"], 2)
                test_accesses.append(args[2])
            return original_load(*args, **kwargs)
        budget = SimpleNamespace(check=lambda: None, remaining=lambda: 100000.)
        with patch.object(worker, "load_arrays", side_effect=guarded_load):
            result = worker.run_dataset(fake_author(), config, "theia", self.root, hashes, output,
                                        torch.device("cpu"), budget, {"test": "synthetic"})
        self.assertEqual(result["status"], "COMPLETE_SOURCE_ORIGINAL_DEVELOPMENT_REPRODUCTION", result)
        self.assertEqual(test_accesses, ["test0"])
        state = torch.load(output / "epoch_002.pt", map_location="cpu", weights_only=True)
        self.assertEqual(state["completed_epochs"], 2)
        self.assertFalse(state["rng"]["checkpoint_continuation_qualified"])
        with np.load(output / "TRAIN_EMBEDDINGS.npz", allow_pickle=False) as data:
            self.assertEqual(data["raw"].shape, (48, 64))

    def test_resource_hold_never_loads_test(self):
        hashes, config = self.data(), self.config()
        config["resources"]["safety_seconds"] = 1_000_000
        output = self.root / "output"
        original_load = adapter.load_arrays
        accesses = []
        def guarded_load(*args, **kwargs):
            accesses.append(args[2])
            return original_load(*args, **kwargs)
        with patch.object(worker, "load_arrays", side_effect=guarded_load):
            result = worker.run_dataset(fake_author(), config, "theia", self.root, hashes, output,
                torch.device("cpu"), SimpleNamespace(check=lambda: None, remaining=lambda: 100.), {"test": "synthetic"})
        self.assertEqual(result["status"], "NOT_RUN_RESOURCE_HOLD", result)
        self.assertEqual(result["completed_epochs"], 1)
        self.assertFalse(result["test_labels_loaded"])
        self.assertNotIn("test0", accesses)
        self.assertFalse((output / "FIT_FREEZE.json").exists())

    def test_zero_author_normalizer_stays_numerical_hold(self):
        hashes, config = self.data(), self.config()
        config["dataset_specs"]["theia"]["k"] = 2  # Each type has sixteen identical bank rows.
        result = worker.run_dataset(fake_author(), config, "theia", self.root, hashes, self.root / "output",
            torch.device("cpu"), SimpleNamespace(check=lambda: None, remaining=lambda: 100000.), {"test": "synthetic"})
        self.assertEqual(result["status"], "SOURCE_NUMERICAL_HOLD")
        self.assertEqual(result["completed_epochs"], 2)
        self.assertFalse(result["evaluation_complete"])
        self.assertIn("zero/nonfinite author distance normalizer", result["reason"])


if __name__ == "__main__":
    unittest.main()
