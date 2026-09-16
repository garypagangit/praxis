"""Deliberate synthetic fault controls for the independent auditor.

These fixtures are invented mathematical cases, never TimesFM/D0 outcomes.
"""
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np

import audit_d0 as audit


def synthetic_points():
    return np.zeros((4, 32, 8, 3), dtype=np.float64), np.zeros((32, 3), dtype=np.float64)


def positive_case():
    points, target = synthetic_points()
    points[[0, 2, 3], :, 1:7, 1:] = 0.1
    return points, target


class DecisionControls(unittest.TestCase):
    def test_no_mechanism_holds_scale(self):
        result = audit.compute_metrics(*synthetic_points())
        self.assertEqual(result["decision"], "HOLD_CROSS_CHANNEL_HARM_SCALE_UP")

    def test_positive_only_qualifies_separate_d1(self):
        result = audit.compute_metrics(*positive_case())
        self.assertEqual(result["decision"], "ELIGIBLE_FOR_SEPARATE_D1_DESIGN_ONLY")
        self.assertEqual(len(result["qualifying_joint_variants"]), 6)

    def test_identity_of_same_qualifying_variants(self):
        points, targets = synthetic_points()
        points[0, :8, 1, 1:] = 0.06  # 8 displacements, mean inflation only .015
        points[0, :, 2, 1:] = 0.04  # mean inflation passes, no large displacements
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["qualifying_joint_variants"], [])
        self.assertEqual(result["decision"], "HOLD_CROSS_CHANNEL_HARM_SCALE_UP")

    def test_selected_context_denominator_bias_is_rejected(self):
        points, targets = synthetic_points()
        points[0, :8, 1:7, 1:] = 0.05
        result = audit.compute_metrics(points, targets)
        row = result["pipelines"][audit.PIPELINES[0]]["variants"]["step1"]
        self.assertEqual(row["contexts_with_practical_spillover_above_floor"], 8)
        self.assertAlmostEqual(row["mean_error_inflation"], 0.0125)
        self.assertEqual(result["qualifying_joint_variants"], [])

    def test_eight_and_mean_point_zero_two_are_inclusive(self):
        points, targets = synthetic_points()
        points[[0, 2, 3], :8, 1:3, 1:] = 0.08
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["qualifying_joint_variants"], ["step1", "step3"])

    def test_seven_contexts_do_not_qualify(self):
        points, targets = positive_case()
        points[0, 7:, 1:7, 1:] = 0
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["qualifying_joint_variants"], [])

    def test_single_variant_does_not_qualify(self):
        points, targets = positive_case()
        points[0, :, 2:7, 1:] = 0
        self.assertEqual(audit.compute_metrics(points, targets)["decision"], "HOLD_CROSS_CHANNEL_HARM_SCALE_UP")

    def test_movement_toward_target_is_not_harm(self):
        points, targets = positive_case()
        targets[:] = 1
        self.assertEqual(audit.compute_metrics(points, targets)["qualifying_joint_variants"], [])

    def test_independent_spillover_above_floor_is_operational_hold(self):
        points, targets = positive_case()
        points[1, 0, 1, 1:] = 1.0001e-5
        self.assertEqual(audit.compute_metrics(points, targets)["decision"], "HOLD_OPERATIONAL")

    def test_independent_spillover_equal_floor_is_allowed(self):
        points, targets = positive_case()
        points[1, 0, 1, 1:] = 1e-5
        self.assertEqual(audit.compute_metrics(points, targets)["decision"], "ELIGIBLE_FOR_SEPARATE_D1_DESIGN_ONLY")

    def test_independent_single_channel_failure_cannot_hide_in_channel_mean(self):
        points, targets = positive_case()
        points[1, 0, 1, 1] = 1.5e-5
        result = audit.compute_metrics(points, targets)
        self.assertLess(result["independent_maximum_spillover"], result["numerical_floor"])
        self.assertGreater(result["independent_maximum_scalar_displacement"], result["numerical_floor"])
        self.assertEqual(result["decision"], "HOLD_OPERATIONAL")

    def test_repeat_above_tolerance_is_operational_hold(self):
        points, targets = positive_case()
        points[2, 0, 7, 0] = 1.0001e-5
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["decision"], "HOLD_OPERATIONAL")
        self.assertAlmostEqual(result["numerical_floor"], 0.00010001)

    def test_repeat_equal_tolerance_is_allowed_and_scales_floor(self):
        points, targets = positive_case()
        points[2, 0, 7, 0] = 1e-5
        points[1, 0, 1, 1:] = 0.00005
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["decision"], "ELIGIBLE_FOR_SEPARATE_D1_DESIGN_ONLY")
        self.assertEqual(result["numerical_floor"], 0.0001)

    def test_simple_control_at_inflation_ceiling_holds_complex(self):
        points, targets = positive_case()
        points[2, :, 1:7, 1:] = 0.005
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["decision"], "HOLD_COMPLEX_DEFENSE")
        self.assertEqual(result["adequate_simple_controls"], [audit.PIPELINES[2]])

    def test_sma_alone_can_hold_complex(self):
        points, targets = positive_case()
        points[3, :, 1:7, 1:] = 0.004
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["decision"], "HOLD_COMPLEX_DEFENSE")
        self.assertEqual(result["adequate_simple_controls"], [audit.PIPELINES[3]])

    def test_simple_control_must_cover_every_joint_qualifying_variant(self):
        points, targets = positive_case()
        points[2, :, 1:6, 1:] = 0.004
        self.assertEqual(audit.compute_metrics(points, targets)["decision"], "ELIGIBLE_FOR_SEPARATE_D1_DESIGN_ONLY")

    def test_clean_mae_delta_ceiling_and_all_64_denominator(self):
        points, targets = positive_case()
        points[2, :, :, 1:] = 0.01
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["decision"], "HOLD_COMPLEX_DEFENSE")
        points[2, :, :, 1:] = 0.010001
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["decision"], "ELIGIBLE_FOR_SEPARATE_D1_DESIGN_ONLY")
        self.assertAlmostEqual(result["pipelines"][audit.PIPELINES[2]]["clean_off_channel_mae"], 0.010001)

    def test_each_pipeline_has_own_clean_reference(self):
        points, targets = positive_case()
        points[2, :, :, 1:] = 0.009
        result = audit.compute_metrics(points, targets)
        self.assertEqual(result["pipelines"][audit.PIPELINES[2]]["variants"]["step1"]["mean_error_inflation"], 0)
        self.assertEqual(result["decision"], "HOLD_COMPLEX_DEFENSE")

    def test_nonfinite_forecast_is_rejected(self):
        points, targets = positive_case()
        points[0, 0, 0, 0] = np.nan
        with self.assertRaisesRegex(audit.AuditError, "nonfinite"):
            audit.compute_metrics(points, targets)


class SavedEvidenceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = audit.reconstruct(np.linspace(-2.0, 8.0, 1007, dtype=np.float64))
        points = np.zeros((4, 32, 8, 3), dtype=np.float32)
        cls.forecasts = {"points": points, "quantiles": np.zeros((4, 32, 8, 3, 9), dtype=np.float32),
                         "completed": np.ones((4, 32, 8), dtype=bool)}
        cls.rows = []
        for pi in range(4):
            for oi in range(32):
                for si in range(8):
                    cls.rows.append({
                        "evaluation_index": pi * 256 + oi * 8 + si,
                        "pi": pi, "oi": oi, "si": si, "pipeline": audit.PIPELINES[pi],
                        "state": audit.STATES[si], "origin": int(cls.expected["origins"][oi]),
                        "input_sha256": audit.array_sha256(cls.expected["inputs"][pi, oi, si]),
                        "target_sha256": audit.array_sha256(cls.expected["targets"][oi]),
                        "forecast": [0., 0., 0.], "quantiles": [[0.] * 9 for _ in range(3)],
                        "forward_calls": 3 if pi == 1 else 1,
                        "tensor_batch_sequences": 3 if pi == 1 else 1,
                        "tensor_channel_sequences": 3, "elapsed_seconds": 0.1,
                        "univariate": pi == 1, "point_dtype": "float32", "quantile_dtype": "float32",
                        "decode_calls_detail": [
                            {"target_shape": [1, 1 if pi == 1 else 3, 128],
                             "target_sha256": audit.array_sha256(cls.expected["inputs"][pi, oi, si, ci:ci + 1][None]
                                                                 if pi == 1 else cls.expected["inputs"][pi, oi, si][None]),
                             "dtype": "torch.float32", "horizon": 64}
                            for ci in range(3 if pi == 1 else 1)],
                        "forward_calls_detail": [{"values_shape": [1, 1 if pi == 1 else 3, 6, 32], "dtype": "torch.float32"}
                                                 for _ in range(3 if pi == 1 else 1)],
                    })

    def test_exact_synthetic_source_reconstruction(self):
        audit.check_inputs(self.expected, self.expected)
        self.assertEqual(self.expected["origins"].tolist(), [384 + j * 622 // 31 for j in range(32)])

    def test_sma_context_boundary_has_no_external_or_future_values(self):
        base = self.expected["derived"][384 - 132:384 - 4, 0]
        sma = self.expected["inputs"][3, 0, 0, 0]
        for t in range(6):
            self.assertEqual(sma[t], np.float32(sum(base[max(0, t - 4):t + 1]) / min(t + 1, 5)))
        corrupted = {k: v.copy() for k, v in self.expected.items()}
        corrupted["inputs"][3, 0, 0, 0, 0] = np.float32(base[:5].mean())
        with self.assertRaisesRegex(audit.AuditError, "independent float64"):
            audit.check_inputs(corrupted, self.expected)

    def test_perturbation_boundaries_inclusive_ramp(self):
        base = self.expected["derived"][384 - 132:384 - 4, 0]
        step = self.expected["inputs"][0, 0, 3, 0]
        ramp = self.expected["inputs"][0, 0, 6, 0]
        self.assertEqual(step[63], np.float32(base[63]))
        self.assertEqual(step[64], np.float32(base[64] + 6))
        self.assertEqual(ramp[64], np.float32(base[64]))
        self.assertEqual(ramp[127], np.float32(base[127] + 6))

    def test_protected_channel_mutation_is_rejected(self):
        corrupted = {k: v.copy() for k, v in self.expected.items()}
        corrupted["inputs"][0, 0, 1, 1, -1] += 1
        with self.assertRaisesRegex(audit.AuditError, "inputs differs"):
            audit.check_inputs(corrupted, self.expected)

    def test_future_target_mutation_is_rejected(self):
        corrupted = {k: v.copy() for k, v in self.expected.items()}
        corrupted["targets"][0, 1] += 1
        with self.assertRaisesRegex(audit.AuditError, "targets differs"):
            audit.check_inputs(corrupted, self.expected)

    def test_premature_cast_is_rejected(self):
        corrupted = {k: v.copy() for k, v in self.expected.items()}
        base = corrupted["derived"][384 - 132:384 - 4].T.astype(np.float32)
        base[0, -64:] += np.float32(6)
        corrupted["inputs"][0, 0, 3] = base
        self.assertFalse(audit.exact_equal(corrupted["inputs"], self.expected["inputs"]))
        with self.assertRaises(audit.AuditError):
            audit.check_inputs(corrupted, self.expected)

    def test_complete_accounting(self):
        result = audit.check_observations(self.rows, self.expected, self.forecasts)
        self.assertEqual(result["evaluations"], 1024)
        self.assertEqual(result["forward_calls"], 1536)
        self.assertEqual(result["tensor_channel_sequences"], 3072)

    def test_identity_omission_is_rejected(self):
        with self.assertRaisesRegex(audit.AuditError, "1024"):
            audit.check_observations(self.rows[:-1], self.expected, self.forecasts)

    def test_duplicate_identity_substitution_is_rejected(self):
        with self.assertRaisesRegex(audit.AuditError, "duplicate"):
            audit.check_observations(self.rows[:-1] + [self.rows[0]], self.expected, self.forecasts)

    def test_wrong_independent_routing_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[256]["forward_calls"] = 1
        with self.assertRaisesRegex(audit.AuditError, "routing"):
            audit.check_observations(rows, self.expected, self.forecasts)

    def test_wrong_decode_input_with_correct_counts_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[256]["decode_calls_detail"][1]["target_sha256"] = rows[256]["decode_calls_detail"][0]["target_sha256"]
        with self.assertRaisesRegex(audit.AuditError, "routing mismatch"):
            audit.check_observations(rows, self.expected, self.forecasts)

    def test_joint_pipeline_cannot_claim_univariate_routing(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["univariate"] = True
        with self.assertRaisesRegex(audit.AuditError, "API routing"):
            audit.check_observations(rows, self.expected, self.forecasts)

    def test_changed_target_hash_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["target_sha256"] = "0" * 64
        with self.assertRaisesRegex(audit.AuditError, "target hash"):
            audit.check_observations(rows, self.expected, self.forecasts)

    def test_points_must_match_sorted_median(self):
        forecasts = {k: v.copy() for k, v in self.forecasts.items()}
        forecasts["points"][0, 0, 0, 0] = 1
        with self.assertRaisesRegex(audit.AuditError, "median"):
            audit.check_forecasts(forecasts)

    def test_missing_forecast_completion_is_rejected(self):
        forecasts = {k: v.copy() for k, v in self.forecasts.items()}
        forecasts["completed"][0, 0, 0] = False
        with self.assertRaisesRegex(audit.AuditError, "incomplete"):
            audit.check_forecasts(forecasts)

    def test_quantile_repeat_mutation_is_separate_technical_hold(self):
        quantiles = self.forecasts["quantiles"].copy()
        quantiles[0, 0, 7, 0, 8] = np.float32(2e-5)
        self.assertEqual(audit.compute_metrics(self.forecasts["points"], np.zeros((32, 3)))["maximum_clean_repeat_discrepancy"], 0)
        with self.assertRaisesRegex(audit.AuditError, "separate technical integrity"):
            audit.quantile_repeat_max(quantiles)


class ProvenanceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="d0_audit_synthetic_")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        names = ["RUN_STARTED.json", "MANIFEST.json", "runtime_freeze.json", "inputs.npz",
                 "forecasts.npz", "observations.jsonl", "COUNTERS.json", "PROGRESS.json"]
        for name in names:
            (self.directory / name).write_text("synthetic engineering fixture only", encoding="utf-8")
        self.manifest = {"worker_sha256": "f" * 64}
        self.freeze = {"packages": {"numpy": "2.2.6", "torch": "2.6.0+cu124"}, "python_major_minor": "3.10"}
        self.source_hashes = dict(audit.SOURCE_FILES)
        self.receipt = {
            "schema_version": 1, "source_revision": audit.SOURCE_REVISION,
            "model_revision": audit.MODEL_REVISION, "weights_sha256": audit.WEIGHTS_SHA256,
            "source_archive_sha256": audit.SOURCE_ARCHIVE_SHA256, "source_file_sha256": self.source_hashes,
            "total_assigned_evaluations": 1024, "hai_accessed": False, "median_quantile_index": 4,
            "quantile_levels": [i / 10 for i in range(1, 10)],
            "prepared_manifest_sha256": audit.sha256_file(self.directory / "MANIFEST.json"),
            "runtime_freeze_sha256": audit.sha256_file(self.directory / "runtime_freeze.json"),
            "worker_sha256": self.manifest["worker_sha256"], "status": "COMPLETE_PENDING_INDEPENDENT_AUDIT",
            "completed_evaluations": 1024,
            "model_config": {"use_variate_attention": True, "per_core_batch_size": 1, "device": "cuda",
                             "local_files_only": True, "checkpoint_path": "/synthetic/model.safetensors"},
            "native_use_variate_attention": True,
            "native_model_config": {"use_variate_attention": True, "input_patch_len": 32, "output_patch_len": 64,
                                    "quantiles": [i / 10 for i in range(1, 10)], "residual_block_config": {}, "transformer_config": {}},
            "forecast_config": {"horizon": 1, "return_quantiles": True, "use_symmetric_averaging": False,
                                "make_positive": False, "sort_quantiles": True, "use_znorm": False, "padding_mode": "none"},
            "routing": {pipeline: {"univariate": pi == 1} for pi, pipeline in enumerate(audit.PIPELINES)},
            "loaded_source_modules": {"timesfm3.torch." + Path(name).stem: {"path": name, "sha256": digest}
                                      for name, digest in self.source_hashes.items()},
            "model_parameter_dtypes": ["torch.float32"], "model_parameter_devices": ["cuda:0"],
            "environment": {"packages": self.freeze["packages"], "numpy": "2.2.6", "torch": "2.6.0+cu124",
                            "python": "3.10.12", "model_dtype": "float32", "deterministic_algorithms": True,
                            "tf32": False, "cudnn_benchmark": False, "cublas_workspace_config": ":4096:8",
                            "torch_threads": 4, "device": "synthetic-device-record"},
            "maximum_worker_seconds": 1200, "runtime_seconds": 1, "peak_allocated_gib": 0, "peak_reserved_gib": 0,
            "artifacts": {name: audit.sha256_file(self.directory / name) for name in names},
        }
        self.started = copy.deepcopy(self.receipt)
        self.started["status"] = "RUN_STARTED_NOT_COMPLETE"

    def check(self):
        audit.check_provenance(self.receipt, self.started, self.manifest, self.freeze, self.source_hashes, self.directory)

    def test_complete_synthetic_provenance_is_accepted(self):
        self.check()

    def test_changed_executed_api_hash_is_rejected(self):
        name = "timesfm3.torch.evaluator"
        self.receipt["loaded_source_modules"][name]["sha256"] = "0" * 64
        self.started["loaded_source_modules"][name]["sha256"] = "0" * 64
        with self.assertRaisesRegex(audit.AuditError, "pinned source archive"):
            self.check()

    def test_disabled_variate_attention_is_rejected(self):
        self.receipt["model_config"]["use_variate_attention"] = False
        self.started["model_config"]["use_variate_attention"] = False
        with self.assertRaisesRegex(audit.AuditError, "use_variate_attention"):
            self.check()

    def test_wrong_padding_mode_is_rejected(self):
        self.receipt["forecast_config"]["padding_mode"] = "edge"
        self.started["forecast_config"]["padding_mode"] = "edge"
        with self.assertRaisesRegex(audit.AuditError, "prediction API options"):
            self.check()

    def test_actual_native_attention_cannot_disagree_with_model_config(self):
        self.receipt["native_use_variate_attention"] = False
        self.started["native_use_variate_attention"] = False
        with self.assertRaisesRegex(audit.AuditError, "observed native variate attention"):
            self.check()

    def test_changed_runtime_package_is_rejected(self):
        self.receipt["environment"]["numpy"] = "2.4.6"
        self.started["environment"]["numpy"] = "2.4.6"
        with self.assertRaisesRegex(audit.AuditError, "production NumPy"):
            self.check()

    def test_changed_saved_artifact_is_rejected(self):
        (self.directory / "observations.jsonl").write_text("modified synthetic bytes", encoding="utf-8")
        with self.assertRaisesRegex(audit.AuditError, "artifact hash mismatch"):
            self.check()


if __name__ == "__main__":
    unittest.main(verbosity=2)
