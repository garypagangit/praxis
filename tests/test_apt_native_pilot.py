import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

from experiments.apt_final.native_graph import pilot


class NativePilotTests(unittest.TestCase):
    def setUp(self):
        pilot.configure_reproducibility(1)
        self.graph = {"node_type": np.array([0, 1, 0, 1]),
                      "src": np.array([0, 0, 1, 2]), "dst": np.array([1, 2, 2, 3]),
                      "relation": np.array([0, 1, 0, 1])}

    def config(self):
        return {"hidden_dim": 8, "bottleneck_dim": 3, "epochs": 2,
                "learning_rate": 0.001, "weight_decay": 0.0001,
                "feature_mask_rate": 0.15, "max_loss_nodes": 4,
                "isolation_trees": 5, "isolation_max_samples": 4, "cpu_threads": 1}

    def test_edge_removal_recomputes_both_directions_and_degrees(self):
        original, degree, _, _ = pilot.observed_features(self.graph, 2, 2)
        damaged, remaining, src, dst = pilot.observed_features(self.graph, 2, 2,
                                                              np.array([True, False, False, False]))
        np.testing.assert_array_equal(original[:, :2], damaged[:, :2])
        np.testing.assert_array_equal(remaining, [1, 1, 0, 0])
        self.assertEqual(damaged[0, 4], np.log1p(np.float32(1)))
        self.assertEqual(damaged[1, 2], np.log1p(np.float32(1)))
        self.assertEqual(damaged[:, 2:].sum(), 2 * np.log1p(np.float32(1)))
        self.assertEqual(degree.sum(), 8)
        np.testing.assert_array_equal(src, [0])
        np.testing.assert_array_equal(dst, [1])

    def test_total_loss_preserves_node_type_and_removes_all_count_features(self):
        x, degree, src, dst = pilot.observed_features(self.graph, 2, 2, np.zeros(4, dtype=bool))
        self.assertTrue(np.all(x[:, 2:] == 0))
        self.assertTrue(np.all(degree == 0))
        self.assertEqual(len(src), 0)
        self.assertEqual(len(dst), 0)
        self.assertTrue(np.all(x[:, :2].sum(axis=1) == 1))

    def test_native_self_edge_is_preserved_and_counts_twice_in_degree(self):
        graph = {"node_type": np.array([0]), "src": np.array([0]), "dst": np.array([0]),
                 "relation": np.array([0])}
        x, degree, src, dst = pilot.observed_features(graph, 1, 1)
        np.testing.assert_array_equal(degree, [2])
        self.assertEqual(len(src), 1)
        self.assertTrue(np.all(x[:, 1:] > 0))

    def test_ties_cannot_be_split_to_manufacture_one_percent_fpr(self):
        calibration = np.ones(100)
        score = np.array([0.0, 1.0, 2.0])
        margin, p = pilot.margin_from_calibration(calibration, score, 0.01)
        np.testing.assert_array_equal(margin >= 0, [False, False, True])
        self.assertEqual(p[1], 1.0)
        self.assertEqual(pilot.strict_threshold(calibration, 0.01), 1.0)

    def test_too_small_calibration_cannot_support_requested_tail_level(self):
        calibration = np.arange(10.0)
        margin, _ = pilot.margin_from_calibration(calibration, [1e10], 0.01)
        self.assertLess(margin[0], 0)
        self.assertIsNone(pilot.strict_threshold(calibration, 0.01))

    def test_raw_threshold_matches_empirical_tail_on_tied_scores(self):
        calibration = np.repeat(np.arange(50.0), 4)
        score = np.arange(-1.0, 51.0, 0.25)
        margin, _ = pilot.margin_from_calibration(calibration, score, 0.05)
        threshold = pilot.strict_threshold(calibration, 0.05)
        np.testing.assert_array_equal(score > threshold, margin >= 0)

    def test_quality_gate_depends_only_on_observed_degree(self):
        gin = np.array([0.8, -0.4, 0.9, -0.1])
        mlp = np.array([-0.8, 0.5, -0.2, 0.6])
        result, gate = pilot.quality_selector([0, 1, 2, 3], gin, mlp, 2)
        np.testing.assert_array_equal(gate, [False, False, True, True])
        np.testing.assert_array_equal(result, [-0.8, 0.5, 0.9, -0.1])
        self.assertNotIn("drop_rate", inspect.signature(pilot.quality_selector).parameters)

    def test_confidence_gate_is_label_free_and_graph_wins_ties(self):
        result, gate = pilot.confidence_selector(np.array([1.0, 0.3, -2.0]),
                                                 np.array([-1.0, -0.9, 0.5]))
        np.testing.assert_array_equal(gate, [True, False, True])
        np.testing.assert_array_equal(result, [1.0, -0.9, -2.0])

    def test_corruption_masks_are_paired_nested_and_seeded(self):
        first = list(pilot.scenario_masks(100, [0, .25, .5, 1], [7, 9]))
        second = list(pilot.scenario_masks(100, [0, .25, .5, 1], [7, 9]))
        self.assertEqual(len(first), 7)
        self.assertIsNone(first[0][1])
        for (a, mask), (b, repeat) in zip(first[1:], second[1:]):
            self.assertEqual(a, b)
            np.testing.assert_array_equal(mask, repeat)
        self.assertTrue(np.all(~first[2][1] | first[1][1]))
        self.assertFalse(np.any(first[3][1]))

    def test_error_changes_distinguish_corrected_and_introduced(self):
        result = pilot.error_changes(np.array([1, 0, 1, 0]), [1, 1, 0, 0], [0, 0, 0, 0])
        self.assertEqual(result, {"corrected_errors": 1, "introduced_errors": 1, "both_wrong": 1})

    def test_explicit_cuda_does_not_silently_fall_back(self):
        with mock.patch.object(torch.cuda, "is_available", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "no CPU fallback"):
                pilot.select_device("cuda")
            self.assertEqual(pilot.select_device("auto").type, "cpu")
            self.assertEqual(pilot.select_device("cpu").type, "cpu")
        with self.assertRaises(ValueError):
            pilot.select_device("cuda:typo")

    def test_fit_never_reads_labels_and_models_score_finitely(self):
        # Object labels would raise under allow_pickle=False if fitting accessed them.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "train.npz"
            np.savez(path, **self.graph, y=np.array([{"secret_label": 1}] * 4, dtype=object))
            mean, scale, counts = pilot.fit_scaler([path], 2, 2)
            np.testing.assert_array_equal(counts, [2, 2])
            graph = pilot.load_graph(path)
            self.assertNotIn("y", graph)
            features, _, src, dst = pilot.observed_features(graph, 2, 2)
            features = pilot.scale_features(features, mean, scale)
            for arm in ("mlp", "gin"):
                model, receipt = pilot.fit_neural([path], 2, 2, mean, scale, self.config(),
                                                  101, arm, torch.device("cpu"))
                scores, seconds = pilot.score_neural(model, features, src, dst, torch.device("cpu"))
                self.assertTrue(np.all(np.isfinite(scores)))
                self.assertEqual(scores.shape, (4,))
                self.assertEqual(len(receipt["epoch_mean_loss"]), 2)
            forest, receipt = pilot.fit_forest([path], 2, 2, mean, scale, self.config(), 101)
            self.assertTrue(np.all(np.isfinite(forest.score_samples(features))))
            self.assertFalse(receipt["labels_used"])

    def test_cpu_training_repeatability(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "train.npz"
            np.savez(path, **self.graph)
            mean, scale, _ = pilot.fit_scaler([path], 2, 2)
            a, _ = pilot.fit_neural([path], 2, 2, mean, scale, self.config(), 7, "gin", torch.device("cpu"))
            b, _ = pilot.fit_neural([path], 2, 2, mean, scale, self.config(), 7, "gin", torch.device("cpu"))
            for name, value in a.state_dict().items():
                self.assertTrue(torch.equal(value, b.state_dict()[name]), name)

    def test_manifest_hash_refusal_and_disjoint_partition_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "train0.npz"
            np.savez(path, **self.graph)
            entry = {"npz": path.name, "npz_sha256": "0" * 64}
            manifest = {"status": "STATIC_DEVELOPMENT_ONLY",
                        "datasets": [{"dataset": "cadets", "graphs": [entry]}]}
            (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            config = {"train_graphs": ["train0"], "calibration_graph": "train3", "evaluation_graph": "test0"}
            with self.assertRaisesRegex(ValueError, "hash"):
                pilot.load_dataset_spec(root, "cadets", config)
            config["calibration_graph"] = "train0"
            with self.assertRaisesRegex(ValueError, "distinct"):
                pilot.load_dataset_spec(root, "cadets", config)

    def test_direct_run_refuses_absent_registration_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "never-created"
            with self.assertRaises((FileNotFoundError, ValueError, RuntimeError)):
                pilot.run_pilot(root / "missing-config.json", root / "data", "cadets", output,
                                "cpu", root / "missing-registration.json")
            self.assertFalse(output.exists())

    def test_end_to_end_synthetic_pipeline_saves_freeze_aggregates_and_private_predictions(self):
        # Registration is mocked only for explicitly synthetic test data; CLI has no bypass.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            (data / "cadets").mkdir(parents=True)
            inventory = []
            n = 120
            for name in ("train0", "train1", "train2", "train3", "test0"):
                path = data / "cadets" / f"{name}.npz"
                y = np.zeros(n, dtype=np.int8)
                if name == "test0":
                    y[-10:] = 1
                np.savez(path, node_type=np.arange(n) % 2, src=np.arange(n - 1),
                         dst=np.arange(1, n), relation=np.arange(n - 1) % 2, y=y)
                inventory.append({"npz": f"cadets/{name}.npz", "npz_sha256": pilot.sha256(path)})
            manifest = {"status": "STATIC_DEVELOPMENT_ONLY", "synthetic": True,
                        "datasets": [{"dataset": "cadets", "graphs": inventory,
                                      "metadata": {"node_feature_dim": 2, "edge_feature_dim": 2}}]}
            pilot.write_json(data / "MANIFEST.json", manifest)
            config = {**self.config(), "scope": "DEVELOPMENT_ONLY", "seeds": [101],
                      "train_graphs": ["train0", "train1", "train2"],
                      "calibration_graph": "train3", "evaluation_graph": "test0",
                      "calibration_fpr": 0.01, "gate_min_degree": 2,
                      "drop_rates": [0, 1], "mask_seeds": [123]}
            config_path = root / "config.json"
            pilot.write_json(config_path, config)
            registration_path = root / "registration.json"
            pilot.write_json(registration_path, {"synthetic_test_only": True})
            with mock.patch("experiments.apt_final.native_graph.provenance.verify_registration",
                            return_value={"git_commit": "SYNTHETIC_TEST_ONLY"}) as verify:
                result = pilot.run_pilot(config_path, data, "cadets", root / "output", "cpu", registration_path)
                verify.assert_called_once()
            self.assertEqual(result["status"], "COMPLETE_DEVELOPMENT_ONLY")
            self.assertEqual(len(result["records"]), 2)
            self.assertEqual(result["records"][1]["observed_edges"], 0)
            self.assertEqual(result["records"][1]["routing"]["quality_graph_fraction"], 0)
            self.assertTrue((root / "output" / "FIT_FREEZE.json").is_file())
            self.assertTrue((root / "output" / "RESULTS.partial.json").is_file())
            self.assertEqual(len(list((root / "output" / "private").glob("predictions_*.npz"))), 2)


if __name__ == "__main__":
    unittest.main()
