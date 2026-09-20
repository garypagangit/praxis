"""Tests for leakage boundaries and exact new-fold representation caches."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
import torch

from experiments.apt_final.normal_stability import engine
from experiments.apt_final.native_graph import pilot


class NormalFoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.paths = {}
        for graph_index in range(4):
            # Label payload cannot be opened with allow_pickle=False. Every
            # training/caching operation must succeed without ever accessing it.
            types = np.array([0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int64)
            if graph_index >= 2:
                types[:] = 2  # Held-out-only type must not affect fitted scaler.
            src = np.asarray([0, 1, 2, 3, 4, 5, graph_index], dtype=np.int64)
            dst = np.asarray([1, 2, 3, 4, 5, 6, 7], dtype=np.int64)
            rel = np.asarray([0, 1, 0, 1, 0, 1, graph_index % 2], dtype=np.int64)
            path = cls.root / f"train{graph_index}.npz"
            np.savez_compressed(path, node_type=types, src=src, dst=dst, relation=rel,
                                y=np.array([{"forbidden_label": graph_index}], dtype=object))
            cls.paths[f"train{graph_index}"] = path
        # Must remain entirely untouched, including file existence checks.
        cls.paths["test0"] = cls.root / "DOES_NOT_EXIST_ATTACK_FILE.npz"
        cls.config = {"hidden_dim": 8, "bottleneck_dim": 3, "epochs": 1,
                      "learning_rate": .001, "weight_decay": .0001,
                      "feature_mask_rate": .15, "max_loss_nodes": 8,
                      "cpu_threads": 1, "embedding_batch_size": 3,
                      "conditions": {"clean": 0., "masked": .5},
                      "mask_seeds": {f"train{i}": 1000 + i for i in range(4)}}
        cls.roles = {"calibration": "train2", "normal_validation": "train3"}
        cls.output = cls.root / "fold"
        cls.manifest = engine.train_and_cache(cls.paths, ["train0", "train1"], cls.roles,
                                              3, 2, cls.config, 101, "cpu", cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_fit_ignores_heldout_labels_and_attack_path(self):
        self.assertFalse(self.manifest["target_labels_accessed"])
        self.assertFalse(self.manifest["attack_graphs_accessed"])
        self.assertNotIn("test0", self.manifest["input_graph_sha256"])
        with np.load(self.output / "PREPROCESSING.npz", allow_pickle=False) as p:
            # The third type is only in calibration/validation data.
            self.assertEqual(float(p["mean"][2]), 0.)
            self.assertEqual(int(p["type_counts"][2]), 0)
            self.assertEqual(int(p["type_counts"].sum()), 16)

    def test_two_views_for_every_normal_graph_preserve_counts_and_hashes(self):
        self.assertEqual(self.manifest["cache_count"], 8)
        for name, views in self.manifest["caches"].items():
            self.assertEqual(set(views), {"clean", "masked"})
            for condition, entry in views.items():
                path = self.output / entry["cache_npz"]
                self.assertEqual(engine.digest(path), entry["cache_sha256"])
                with np.load(path, allow_pickle=False) as arrays:
                    self.assertNotIn("y", arrays.files)
                    self.assertEqual(len(arrays["node_type"]), 8)
                    self.assertEqual(int(arrays["degree"].sum()), 2 * entry["observed_edges"])
                    for arm in engine.REPRESENTATIONS:
                        self.assertEqual(len(arrays[arm + "_inverse"]), 8)
                        self.assertTrue(np.isfinite(arrays[arm + "_unique"]).all())
                expected = engine.condition_mask(entry["n_edges"], condition, self.config["mask_seeds"][name])
                self.assertEqual(int(expected.sum()), entry["observed_edges"])

    def test_unique_inverse_cache_recovers_direct_frozen_features_and_embeddings(self):
        models, mean, scale, _ = engine.load_fold(self.output)
        name, condition = "train3", "masked"
        source = pilot.load_graph(self.paths[name])
        keep = engine.condition_mask(len(source["src"]), condition, self.config["mask_seeds"][name])
        raw, degree, src, dst = pilot.observed_features(source, 3, 2, keep)
        values = {"local_knn": pilot.scale_features(raw, mean, scale)}
        for arm in ("mlp", "gin"):
            values[arm + "_knn"], _ = engine.embedding.extract_embeddings(
                models[arm], values["local_knn"], src, dst, "cpu", batch_size=3)
        entry = self.manifest["caches"][name][condition]
        with np.load(self.output / entry["cache_npz"], allow_pickle=False) as arrays:
            np.testing.assert_array_equal(degree, arrays["degree"])
            for arm, expected in values.items():
                restored = arrays[arm + "_unique"][arrays[arm + "_inverse"]]
                np.testing.assert_array_equal(restored, expected)

    def test_role_overlap_and_path_aliasing_are_rejected(self):
        with self.assertRaises(ValueError):
            engine.validate_roles(self.paths, ["train0", "train1"], {"calibration": "train1", "normal_validation": "train3"})
        paths = dict(self.paths, train3=self.paths["train0"])
        with self.assertRaises(ValueError):
            engine.validate_roles(paths, ["train0", "train1"], self.roles)

    def test_modified_mask_is_rejected(self):
        models, mean, scale, _ = engine.load_fold(self.output)
        wrong = ~engine.condition_mask(7, "masked", 1000)
        with self.assertRaisesRegex(ValueError, "fixed per-graph"):
            engine.cache_graph(self.paths["train0"], models, mean, scale, 3, 2, "cpu",
                               self.root / "bad_mask", keep=wrong, condition="masked", mask_seed=1000)

    def test_checkpoint_tampering_cannot_reload(self):
        target = self.root / "damaged_fold"
        target.mkdir(exist_ok=True)
        for name in ("MANIFEST.json", "FIT_FREEZE.json", "PREPROCESSING.npz", "mlp_101.pt", "gin_101.pt"):
            shutil.copyfile(self.output / name, target / name)
        with (target / "gin_101.pt").open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            engine.load_fold(target)

    def test_repeat_fit_same_seed_is_exact_and_mask_is_seed_independent(self):
        repeated = self.root / "repeated"
        manifest = engine.train_and_cache(self.paths, ["train0", "train1"], self.roles,
                                         3, 2, self.config, 101, "cpu", repeated)
        first_models, _, _, _ = engine.load_fold(self.output)
        repeat_models, _, _, _ = engine.load_fold(repeated)
        for arm in first_models:
            for key, value in first_models[arm].state_dict().items():
                torch.testing.assert_close(value, repeat_models[arm].state_dict()[key], rtol=0, atol=0)
        for name in self.manifest["caches"]:
            self.assertEqual(self.manifest["caches"][name]["masked"]["mask_sha256"],
                             manifest["caches"][name]["masked"]["mask_sha256"])


if __name__ == "__main__":
    unittest.main()
