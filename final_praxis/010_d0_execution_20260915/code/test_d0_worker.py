"""Engineering controls only: synthetic arrays and pinned evaluator routing.

No checkpoint is loaded, and stub predictions are never research observations.
Run: python test_d0_worker.py --source-root CACHE/timesfm_full
"""
import argparse
import ast
from collections.abc import Iterator
from dataclasses import dataclass
import math
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

import d0_worker as worker

SOURCE_ROOT = None
EVALUATOR_HASH = "4ad0ddc5e264206cf6db706b493c2b4f20bf6698e89b990a4c37c15089971af2"


def source_evaluator():
    """Execute the exact pinned evaluator class against a recording parent API."""
    path = SOURCE_ROOT / "src/timesfm3/torch/evaluator.py"
    worker.require(worker.digest(path) == EVALUATOR_HASH, "Pinned evaluator source changed")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.Assign))]

    @dataclass
    class ForecastOutput:
        ts_id: str | None = None
        forecast: np.ndarray | None = None
        quantiles: np.ndarray | None = None

    class RecordingForecaster:
        def __init__(self):
            self.calls = []

        def predict_batch(self, contexts, **options):
            self.calls.append((contexts, options))
            for index, context in enumerate(contexts):
                values = np.asarray(context)
                forecast = values[..., -1:]
                quantiles = np.repeat(forecast[..., None], 9, axis=-1)
                yield ForecastOutput(ts_id=(options.get("ts_ids") or [None] * len(contexts))[index],
                                     forecast=forecast, quantiles=quantiles)

    ns = dict(TimesFM3Forecaster=RecordingForecaster, ForecastOutput=ForecastOutput,
              np=np, math=math, Iterator=Iterator)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), ns)
    return ns["TimesFM3Evaluator"]()


class ConstructionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Synthetic arithmetic fixture; no public series or model outcomes.
        cls.values = np.arange(1007, dtype=np.float64) + np.sin(np.arange(1007, dtype=np.float64))
        cls.arrays, cls.commissioning = worker.construct(cls.values)

    def test_origin_boundaries_and_no_target_in_context(self):
        self.assertEqual(self.arrays["origins"].tolist(), [384 + (j * 622) // 31 for j in range(32)])
        self.assertEqual(int(self.arrays["origins"][-1]), 1006)
        for j, e in enumerate(self.arrays["origins"]):
            np.testing.assert_array_equal(self.arrays["targets"][j], self.arrays["derived"][e - 4])
            np.testing.assert_array_equal(self.arrays["inputs"][0, j, 0],
                                          self.arrays["derived"][e - 132:e - 4].T.astype(np.float32))

    def test_population_commissioning_and_noise_order(self):
        self.assertEqual(self.commissioning["mean"], self.values[:256].mean())
        self.assertEqual(self.commissioning["population_sd"], self.values[:256].std(ddof=0))
        noise = np.random.Generator(np.random.PCG64(20260915)).standard_normal((1007, 3)) * 0.01
        np.testing.assert_array_equal(self.arrays["noise"], noise)
        z = (self.values - self.values[:256].mean()) / self.values[:256].std(ddof=0)
        t = 489
        expected = [z[t] + noise[t, 0], 0.8*z[t] + 0.2*z[t-1] + noise[t, 1],
                    0.6*z[t] + 0.4*z[t-4] + noise[t, 2]]
        np.testing.assert_array_equal(self.arrays["derived"][t - 4], expected)

    def test_float64_perturbations_then_single_input_cast(self):
        for j, e in enumerate(self.arrays["origins"]):
            base = self.arrays["derived"][e - 132:e - 4].T.copy()
            for s, amplitude in [(1,1), (2,3), (3,6), (4,1), (5,3), (6,6)]:
                expected = base.copy()
                expected[0, -64:] += amplitude if s <= 3 else np.linspace(0, amplitude, 64)
                np.testing.assert_array_equal(self.arrays["inputs"][0,j,s], expected.astype(np.float32))
                np.testing.assert_array_equal(self.arrays["inputs"][1,j,s], expected.astype(np.float32))

    def test_clipping_uses_own_clean_and_preserves_other_channels(self):
        for j, e in enumerate(self.arrays["origins"]):
            for s in [0, 3, 6, 7]:
                expected = self.arrays["derived"][e - 132:e - 4].T.copy()
                if s == 3:
                    expected[0, -64:] += 6.0
                elif s == 6:
                    expected[0, -64:] += np.linspace(0, 6, 64)
                expected[0] = np.clip(expected[0], -3, 3)
                np.testing.assert_array_equal(self.arrays["inputs"][2,j,s], expected.astype(np.float32))
        protected = self.arrays["inputs"][..., 1:, :]
        np.testing.assert_array_equal(protected, np.broadcast_to(protected[0,:,0][None,:,None], protected.shape))

    def test_sma_is_causal_and_restarts_at_context_boundary(self):
        j = 7
        e = self.arrays["origins"][j]
        for s in [0, 1, 6, 7]:
            base = self.arrays["derived"][e - 132:e - 4].T.copy()
            if s == 1:
                base[0,-64:] += 1
            elif s == 6:
                base[0,-64:] += np.linspace(0,6,64)
            for k in [0,1,4,5,63,64,65,127]:
                expected = np.float32(np.mean(base[0,max(0,k-4):k+1], dtype=np.float64))
                self.assertEqual(self.arrays["inputs"][3,j,s,0,k], expected)

    def test_clean_repeats_identities_and_dtypes(self):
        np.testing.assert_array_equal(self.arrays["inputs"][:,:,0], self.arrays["inputs"][:,:,7])
        self.assertEqual(self.arrays["inputs"].dtype, np.float32)
        self.assertEqual(self.arrays["targets"].dtype, np.float64)
        rows = worker.identities(self.arrays)
        self.assertEqual(len(rows), 1024)
        self.assertEqual(len({(r["pi"],r["oi"],r["si"]) for r in rows}), 1024)
        self.assertEqual(rows[-1]["evaluation_index"], 1023)
        self.assertEqual(rows[-1]["state"], "clean_repeat")

    def test_nonfinite_and_near_constant_inputs_fail_closed(self):
        for value in [np.nan,np.inf,-np.inf]:
            values = self.values.copy()
            values[0] = value
            with self.assertRaises(RuntimeError):
                worker.construct(values)
        with self.assertRaises(RuntimeError):
            worker.construct(np.ones(1007,dtype=np.float64))
        with self.assertRaises(RuntimeError):
            worker.construct(self.values.astype(np.float32))

    def test_reader_does_not_parse_labels_or_future_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.csv"
            path.write_text("Data,Label\n" + "".join(f"{i}.5,invalid-label-token\n" for i in range(1007))
                            + "do-not-parse-future,do-not-parse-label\n", encoding="utf-8")
            with mock.patch.object(worker, "CSV_SHA256", worker.digest(path)):
                values = worker.read_values(path)
            np.testing.assert_array_equal(values, np.arange(1007,dtype=np.float64)+0.5)

    def test_modified_canonical_source_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.csv"
            path.write_text("Data,Label\n0,0\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                worker.read_values(path)

    def test_atomic_arrays_roundtrip_and_hash_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.npz"
            worker.save_npz(path, **self.arrays)
            with np.load(path, allow_pickle=False) as loaded:
                for key in loaded.files:
                    self.assertEqual(worker.describe(loaded[key]), worker.describe(self.arrays[key]))
            changed = self.arrays["inputs"].copy()
            changed.flat[0] += 1
            self.assertNotEqual(worker.array_digest(changed), worker.array_digest(self.arrays["inputs"]))


class SourceRoutingControls(unittest.TestCase):
    def test_pinned_native_decode_reaches_expected_forward_tensor_shape(self):
        try:
            import torch
        except ImportError:
            self.skipTest("CPU Torch required for optional source-decode shape control; no weights loaded")
        path = SOURCE_ROOT / "src/timesfm3/torch/model.py"
        self.assertEqual(worker.digest(path), "474b8035db514d852e6358c73ebd1ba90dcd25f17d1ecf4e5bb884ca788e7dbf")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TimesFM3Torch")
        decode = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "decode")
        ns = dict(torch=torch, math=math, Any=object)
        exec(compile(ast.Module(body=[decode], type_ignores=[]), str(path), "exec"), ns)
        observed = []

        class ForwardReached(Exception):
            pass

        def record_forward(inputs, **kwargs):
            observed.append(list(inputs["values"].shape))
            raise ForwardReached()

        receiver = types.SimpleNamespace(input_patch_len=32, output_patch_len=64,
                                         use_stitching=True, _stitching_extract_len=64, rolls=2,
                                         use_linear_detrending=True, linear_detrending_threshold=0.5,
                                         use_frozen_running_stats=False, forward=record_forward)
        for channels in [3,1]:
            target = torch.arange(128*channels,dtype=torch.float32).reshape(1,channels,128)
            with self.assertRaises(ForwardReached):
                ns["decode"](receiver,target=target,horizon=64)
        self.assertEqual(observed, [[1,3,6,32], [1,1,6,32]])

    def test_pinned_joint_path_receives_one_three_variate_context(self):
        evaluator = source_evaluator()
        context = np.arange(384,dtype=np.float32).reshape(3,128)
        results = list(evaluator.predict_batch([context], ts_ids=["joint"], univariate=False, **worker.OPTIONS))
        self.assertEqual(len(evaluator.calls), 1)
        contexts, options = evaluator.calls[0]
        self.assertEqual(len(contexts), 1)
        np.testing.assert_array_equal(contexts[0], context)
        self.assertEqual(options["padding_mode"], "none")
        self.assertFalse(options["use_znorm"])
        self.assertFalse(options["use_symmetric_averaging"])
        self.assertFalse(options["make_positive"])
        self.assertTrue(options["sort_quantiles"])
        self.assertEqual(results[0].forecast.shape, (3,1))

    def test_pinned_independent_path_unrolls_exact_channel_order(self):
        evaluator = source_evaluator()
        context = np.arange(384,dtype=np.float32).reshape(3,128)
        results = list(evaluator.predict_batch([context], ts_ids=["independent"], univariate=True, **worker.OPTIONS))
        self.assertEqual(len(evaluator.calls), 1)
        contexts, options = evaluator.calls[0]
        self.assertEqual(len(contexts), 3)
        for c in range(3):
            self.assertEqual(contexts[c].shape, (128,))
            np.testing.assert_array_equal(contexts[c], context[c])
        self.assertEqual(options["padding_mode"], "none")
        self.assertIsNone(options["past_only_covariates"])
        self.assertIsNone(options["past_future_covariates"])
        self.assertEqual(results[0].ts_id, "independent")
        self.assertEqual(results[0].forecast.shape, (3,1))
        self.assertEqual(results[0].quantiles.shape, (3,1,9))

    def test_source_declares_native_quantiles_and_batch_size_unroll(self):
        path = SOURCE_ROOT / "src/timesfm3/torch/timesfm3_forecaster.py"
        self.assertEqual(worker.digest(path), "33870c9676be6aab4e62c45a0a89bc1d6c49ca3149ddc46a19c6d9e2c23e0037")
        source = path.read_text(encoding="utf-8")
        self.assertIn("default_factory=lambda: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]", source)
        self.assertIn("median_quantile_index: int = 4", source)
        self.assertIn("batch_size = self.config.per_core_batch_size", source)
        self.assertIn("num_batches = math.ceil(num_queries / batch_size)", source)
        self.assertIn("out_logits = self.model.decode(", source)


class ExecutionControls(unittest.TestCase):
    def test_native_counter_observes_direct_forward_without_changing_result(self):
        class Tensor:
            def __init__(self, values):
                self.values = values
                self.shape = values.shape
                self.dtype = "torch.float32"
            def detach(self):
                return self
            def cpu(self):
                return self
            def numpy(self):
                return self.values

        class Native:
            def decode(self, target, horizon):
                return self.forward({"values": Tensor(target.values.reshape(1, target.shape[1], 4, 32))})
            def forward(self, inputs):
                return "unchanged sentinel"

        native = Native()
        counter = worker.NativeCounter(native)
        context = np.arange(384,dtype=np.float32).reshape(1,3,128)
        self.assertEqual(native.decode(target=Tensor(context), horizon=64), "unchanged sentinel")
        for channel in range(3):
            self.assertEqual(native.decode(target=Tensor(context[:,channel:channel+1]), horizon=64), "unchanged sentinel")
        self.assertEqual(counter.forward_calls, 4)
        self.assertEqual(counter.tensor_batch_sequences, 4)
        self.assertEqual(counter.tensor_channel_sequences, 6)
        self.assertEqual(counter.decode_rows[0]["target_sha256"], worker.array_digest(context))
        self.assertEqual(counter.decode_rows[1]["target_shape"], [1,1,128])
        self.assertEqual(counter.forward_rows[0]["values_shape"], [1,3,4,32])

    def test_deadline_fails_closed(self):
        with mock.patch.object(worker.time, "monotonic", return_value=12):
            with self.assertRaises(RuntimeError):
                worker.check_deadline(10,2)
            worker.check_deadline(10,3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    SOURCE_ROOT = args.source_root
    unittest.main(argv=[__file__] + remaining)
