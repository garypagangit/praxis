"""Frozen-model extraction invariants; no APT results are generated here."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

from experiments.apt_final.embedding_baseline import engine
from experiments.apt_final.native_graph.pilot import ReconstructionModel, configure_reproducibility


class FrozenEmbeddingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_reproducibility(1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.x = np.asarray([[.1, .3, -.2, .8], [.5, -.9, .2, .6],
                             [-.3, .4, .5, .2], [.7, -.1, .8, -.4],
                             [.2, .2, -.4, -.7]], dtype=np.float32)
        self.src = np.asarray([0, 1, 0, 2, 4], dtype=np.int64)
        self.dst = np.asarray([1, 2, 2, 3, 1], dtype=np.int64)

    def checkpoint(self, arm="gin", mutate=None):
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(177)
            model = ReconstructionModel(4, 8, 3, graph=arm == "gin").eval()
        record = {"state_dict": model.state_dict(), "arm": arm, "input_dim": 4,
                  "hidden_dim": 8, "bottleneck_dim": 3, "seed": 177}
        if mutate:
            mutate(record)
        path = self.root / (arm + ".pt")
        torch.save(record, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return model, path, digest

    def load(self, arm="gin"):
        original, path, digest = self.checkpoint(arm)
        model, metadata = engine.load_frozen_checkpoint(path, digest, expected_arm=arm,
                                                        expected_input_dim=4, expected_seed=177)
        return original, model, metadata

    def test_redecoded_bottleneck_matches_original_full_model(self):
        for arm in ("mlp", "gin"):
            with self.subTest(arm=arm):
                original, model, metadata = self.load(arm)
                before = {key: value.clone() for key, value in model.state_dict().items()}
                z, receipt = engine.extract_embeddings(model, self.x, self.src, self.dst, "cpu", batch_size=99)
                with torch.no_grad():
                    expected = original(torch.from_numpy(self.x), torch.from_numpy(self.src), torch.from_numpy(self.dst))
                    decoded = original.decoder(torch.from_numpy(z))
                torch.testing.assert_close(decoded, expected, rtol=0, atol=0)
                self.assertTrue(receipt["decoder_reconstruction_exact"])
                self.assertEqual(metadata["trainable_parameters"], 0)
                self.assertTrue(all(not p.requires_grad for p in model.parameters()))
                for key, value in model.state_dict().items():
                    torch.testing.assert_close(value, before[key], rtol=0, atol=0)
                self.assertEqual(len(model.second_norm._forward_hooks), 0)

    def test_mlp_batching_preserves_representations(self):
        _, model, _ = self.load("mlp")
        large, large_receipt = engine.extract_embeddings(model, self.x, self.src, self.dst, batch_size=99)
        small, small_receipt = engine.extract_embeddings(model, self.x, self.src, self.dst, batch_size=2)
        np.testing.assert_allclose(small, large, rtol=1e-6, atol=1e-6)
        self.assertEqual(small_receipt["forward_calls"], 3)
        self.assertEqual(large_receipt["forward_calls"], 1)

    def test_gin_keeps_context_across_requested_batch_boundaries(self):
        _, model, _ = self.load("gin")
        z, receipt = engine.extract_embeddings(model, self.x, self.src, self.dst, batch_size=1)
        full, _ = engine.extract_embeddings(model, self.x, self.src, self.dst, batch_size=99)
        empty = np.empty(0, dtype=np.int64)
        self_only, _ = engine.extract_embeddings(model, self.x, empty, empty, batch_size=1)
        np.testing.assert_array_equal(z, full)
        self.assertEqual(receipt["forward_calls"], 1)
        self.assertGreater(float(np.max(np.abs(z - self_only))), 1e-4)

    def test_directed_edge_reversal_changes_gin_but_not_mlp(self):
        for arm in ("mlp", "gin"):
            _, model, _ = self.load(arm)
            forward, _ = engine.extract_embeddings(model, self.x, self.src, self.dst)
            reverse, _ = engine.extract_embeddings(model, self.x, self.dst, self.src)
            if arm == "gin":
                self.assertGreater(float(np.max(np.abs(forward - reverse))), 1e-4)
            else:
                np.testing.assert_array_equal(forward, reverse)

    def test_hash_tampering_refused_before_torch_deserialization(self):
        _, path, digest = self.checkpoint()
        path.write_bytes(path.read_bytes() + b"tamper")
        with mock.patch.object(engine.torch, "load", side_effect=AssertionError("must not deserialize")):
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                engine.load_frozen_checkpoint(path, digest)

    def test_nonfinite_or_mismatched_state_is_refused_even_with_current_hash(self):
        mutations = [
            lambda record: record["state_dict"]["first.weight"].fill_(float("nan")),
            lambda record: record.update(input_dim=5),
            lambda record: record.update(y=[0, 1]),
            lambda record: record["state_dict"].pop("second.bias"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=repr(mutate)):
                _, path, digest = self.checkpoint(mutate=mutate)
                with self.assertRaises(ValueError):
                    engine.load_frozen_checkpoint(path, digest)

    def test_expected_arm_seed_and_width_are_enforced(self):
        _, path, digest = self.checkpoint("gin")
        for kwargs in ({"expected_arm": "mlp"}, {"expected_seed": 999}, {"expected_input_dim": 999}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    engine.load_frozen_checkpoint(path, digest, **kwargs)

    def test_invalid_endpoint_and_nonfinite_feature_are_refused(self):
        _, model, _ = self.load()
        with self.assertRaises(ValueError):
            engine.extract_embeddings(model, self.x, np.asarray([99]), np.asarray([0]))
        with self.assertRaises(ValueError):
            engine.extract_embeddings(model, self.x, self.src.astype(float), self.dst)
        x = self.x.copy()
        x[0, 0] = np.nan
        with self.assertRaises(ValueError):
            engine.extract_embeddings(model, x, self.src, self.dst)

    def test_hook_removed_on_forward_failure(self):
        _, model, _ = self.load()
        with mock.patch.object(model, "forward", side_effect=RuntimeError("synthetic forward failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic forward failure"):
                engine.extract_embeddings(model, self.x, self.src, self.dst)
        self.assertEqual(len(model.second_norm._forward_hooks), 0)

    def test_loading_frozen_weights_does_not_advance_cpu_rng(self):
        _, path, digest = self.checkpoint()
        before = torch.get_rng_state().clone()
        engine.load_frozen_checkpoint(path, digest)
        self.assertTrue(torch.equal(torch.get_rng_state(), before))

    def test_loaded_parameters_cannot_change_before_extraction(self):
        _, model, _ = self.load()
        with torch.no_grad():
            model.first.bias[0].add_(0.1)
        with self.assertRaisesRegex(RuntimeError, "no longer match"):
            engine.extract_embeddings(model, self.x, self.src, self.dst)

    def test_cpu_device_qualification_uses_both_frozen_model_paths(self):
        receipt = engine.qualify_device("cpu")
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["cuda_parity_executed"])
        self.assertEqual({check["arm"] for check in receipt["checks"]}, {"gin", "mlp"})
        self.assertTrue(all(check["cpu_repeat_exact"] for check in receipt["checks"]))


if __name__ == "__main__":
    unittest.main()
