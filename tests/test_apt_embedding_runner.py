"""Synthetic end-to-end qualification; only registration is mocked."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from experiments.apt_final.native_graph import pilot
from experiments.apt_final.embedding_baseline import runner


class EmbeddingRunnerTests(unittest.TestCase):
    def test_full_synthetic_prior_and_embedding_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            (data / "cadets").mkdir(parents=True)
            n = 120
            src = np.arange(n - 1, dtype=np.int64)
            dst = np.arange(1, n, dtype=np.int64)
            inventory = []
            for name in ("train0", "train1", "train2", "train3", "test0"):
                path = data / "cadets" / f"{name}.npz"
                if name == "test0":
                    y = np.zeros(n, dtype=np.int8)
                    y[-10:] = 1
                else:
                    # Loading these labels with allow_pickle=False raises. Both actual
                    # pipelines must complete without reading training/calibration y.
                    y = np.array([{"must_not_read": name}] * n, dtype=object)
                np.savez(path, node_type=np.arange(n, dtype=np.int64) % 2,
                         src=src, dst=dst, relation=np.arange(n - 1, dtype=np.int64) % 2, y=y)
                inventory.append({"npz": f"cadets/{name}.npz", "npz_sha256": pilot.sha256(path)})
            pilot.write_json(data / "MANIFEST.json", {
                "status": "STATIC_DEVELOPMENT_ONLY", "synthetic": True,
                "datasets": [{"dataset": "cadets", "graphs": inventory,
                              "metadata": {"node_feature_dim": 2, "edge_feature_dim": 2}}]})
            prior_config = {
                "scope": "DEVELOPMENT_ONLY", "seeds": [101], "hidden_dim": 8,
                "bottleneck_dim": 3, "epochs": 2, "learning_rate": 0.001,
                "weight_decay": 0.0001, "feature_mask_rate": 0.15,
                "max_loss_nodes": 24, "cpu_threads": 1,
                "isolation_trees": 5, "isolation_max_samples": 32,
                "forest_fit_nodes": 64, "calibration_fpr": 0.01,
                "gate_min_degree": 2, "drop_rates": [0.0, 0.5],
                "mask_seeds": [20260920], "train_graphs": ["train0", "train1", "train2"],
                "calibration_graph": "train3", "evaluation_graph": "test0",
            }
            prior_config_path = root / "prior_config.json"
            registration_path = root / "SYNTHETIC_REGISTRATION.json"
            pilot.write_json(prior_config_path, prior_config)
            pilot.write_json(registration_path, {"synthetic_test_only": True})
            prior_root = root / "prior"
            with mock.patch("experiments.apt_final.native_graph.provenance.verify_registration",
                            return_value={"git_commit": "SYNTHETIC_TEST_ONLY"}) as old_registration:
                old_result = pilot.run_pilot(prior_config_path, data, "cadets", prior_root / "cadets",
                                            "cpu", registration_path)
                old_registration.assert_called_once()
            masks = [("clean", np.ones(len(src), dtype=bool)),
                     ("drop_0.5_mask_20260920", np.random.default_rng(20260920).random(len(src)) >= 0.5)]
            pilot.write_json(prior_root / "INDEPENDENT_RESULT_AUDIT.json", {
                "status": "SYNTHETIC_FIXTURE_ONLY", "datasets": [{"dataset": "cadets", "conditions": [
                    {"seed": 101, "scenario": name,
                     "input_mask_sha256": hashlib.sha256(mask.tobytes()).hexdigest()}
                    for name, mask in masks]}]})
            before = {str(p.relative_to(prior_root)): pilot.sha256(p)
                      for p in prior_root.rglob("*") if p.is_file()}
            config = {
                "scope": "DEVELOPMENT_ONLY", "datasets": ["cadets"], "seeds": [101],
                "train_graphs": ["train0", "train1", "train2"],
                "calibration_graph": "train3", "evaluation_graph": "test0",
                "bank_size": 32, "bank_seed_offset": 20260920, "neighbors": 3,
                "scale_floor": 0.001, "query_chunk_size": 17, "embedding_batch_size": 32,
                "deduplicate_queries": True, "cpu_threads": 1, "calibration_fpr": 0.01,
                "drop_rates": [0.0, 0.5], "mask_seeds": [20260920], "gate_min_degree": 2,
                "readiness_min_recall": 0.5, "readiness_max_fpr": 0.02,
                "minimum_mean_f1_improvement": 0.05, "confirmation_claim": False,
            }
            config_path = root / "config.json"
            pilot.write_json(config_path, config)
            output = root / "embedding_output"
            with mock.patch.object(runner, "verify_registration",
                                   return_value={"git_commit": "SYNTHETIC_TEST_ONLY"}) as new_registration:
                result = runner.run(config_path, data, prior_root, "cadets", output,
                                    "cpu", registration_path)
                new_registration.assert_called_once()
            self.assertEqual(result["status"], "COMPLETE_DEVELOPMENT_ONLY")
            self.assertFalse(result["encoder_weights_retrained"])
            self.assertTrue(result["test_outcomes_previously_inspected"])
            self.assertEqual(len(result["records"]), 2)
            expected_arms = {"local_knn", "mlp_knn", "gin_knn", "quality_gate", "confidence_selector",
                             *("prior_" + name for name in runner.PRIOR_ARMS)}
            for record in result["records"]:
                self.assertEqual(set(record["metrics"]), expected_arms)
                self.assertEqual(len(record["metrics"]), 11)
                old_record = next(item for item in old_result["records"] if item["name"] == record["name"])
                for arm in runner.PRIOR_ARMS:
                    self.assertEqual(record["metrics"]["prior_" + arm], old_record["metrics"][arm])
                with np.load(output / "private" / f"predictions_101_{record['name']}.npz", allow_pickle=False) as prediction:
                    self.assertEqual(int(prediction["y"].sum()), 10)
                    for arm in expected_arms:
                        self.assertEqual(prediction["score_" + arm].shape, (n,))
                        self.assertTrue(np.all(np.isfinite(prediction["score_" + arm])))
            freeze_path = output / "FIT_FREEZE.json"
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            self.assertFalse(freeze["fit_labels_used"])
            self.assertIn("FROZEN_BEFORE_THIS_RUN_EVALUATION_LABEL_ACCESS", freeze["status"])
            self.assertEqual(pilot.sha256(freeze_path), result["fit_freeze_sha256"])
            for name, digest in freeze["artifacts"].items():
                self.assertEqual(pilot.sha256(output / "private" / name), digest)
            with np.load(output / "private" / "bank_indices_101.npz", allow_pickle=False) as selection:
                self.assertEqual(set(selection.files), {"train0", "train1", "train2"})
                self.assertEqual(sum(len(selection[name]) for name in selection.files), 32)
                for name in selection.files:
                    self.assertTrue(np.all((selection[name] >= 0) & (selection[name] < n)))
                    self.assertEqual(len(np.unique(selection[name])), len(selection[name]))
            with np.load(output / "private" / "bank_101.npz", allow_pickle=False) as bank:
                for arm in runner.NEW_ARMS:
                    self.assertEqual(bank[arm + "_bank_raw"].shape[0], 32)
                    np.testing.assert_allclose(bank[arm + "_mean"], bank[arm + "_bank_raw"].mean(axis=0))
            with np.load(output / "private" / "calibration_101.npz", allow_pickle=False) as calibration:
                self.assertEqual(set(calibration.files), set(runner.NEW_ARMS))
                self.assertTrue(all(calibration[arm].shape == (n,) for arm in runner.NEW_ARMS))
            self.assertTrue((output / "RESULTS.partial.json").exists())
            self.assertFalse(result["development_decision"]["confirmation_or_novelty_established"])
            after = {str(p.relative_to(prior_root)): pilot.sha256(p)
                     for p in prior_root.rglob("*") if p.is_file()}
            self.assertEqual(after, before, "frozen predecessor files must not change")

    def test_direct_run_missing_registration_refuses_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "must-not-exist"
            with self.assertRaises((FileNotFoundError, ValueError, RuntimeError)):
                runner.run(root / "config.json", root / "data", root / "prior", "cadets", output,
                           "cpu", root / "missing_registration.json")
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
