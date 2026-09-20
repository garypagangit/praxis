"""Independent post-run audit regressions using real worker-generated tiny artifacts.

The author model is a CPU linear fixture. Production input registration is mocked
only for these deliberately tiny two-epoch graphs; no production-design evidence
is inferred. The auditor's threshold, metrics, hashes, safe tensor loading,
full-bank distances, six-case freeze and runtime receipt checks execute normally.
"""
from __future__ import annotations

import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.apt_final.magic_calibrated import worker
from experiments.apt_final.magic_calibrated.analysis import audit

spec = importlib.util.spec_from_file_location("calibrated_worker_test_fixture", Path(__file__).with_name("test_apt_magic_calibrated.py"))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def save(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.base_temp.name)
        helper = fixture.Tests()
        helper.root = cls.base
        config, hashes = helper.config(), helper.data()
        save(cls.base / "config.json", config)
        registration = cls.base / "REGISTRATION.json"
        record = {"source_commit": "a" * 40, "upstream_commit": "b" * 40, "source_manifest_sha256": "c" * 64,
                  "original_source_commit": "d" * 40, "compact_source_commit": "e" * 40,
                  "data_files": {"MANIFEST.json": "f" * 64}}
        save(registration, record)
        runtime = audit.read(audit.ORIGINAL / "RUNTIME.json")
        out = cls.base / "output"
        out.mkdir()
        environment = {"python": "3.10.0 synthetic receipt only", "cuda": "12.1", **{k: runtime[k] for k in ("torch", "dgl", "numpy")}, "sklearn": runtime["scikit_learn"]}
        save(out / "WORKER_ENVIRONMENT.json", environment)
        save(out / "ENVIRONMENT.json", {"python": "3.10.0 synthetic receipt only", "dependency_versions": {k: v for k, v in runtime.items() if k not in {"python", "wheel", "wheel_sha256", "wheel_url"}}})
        save(out / "RUNTIME_QUALIFICATION.json", {"status": "PASS", "forward_backward_qualified": True,
            "encoder_normalizations": ["NoneType"] * 3, "normalization_fix_applied": False, "determinism_fix_applied": False,
            "mask_target_alias_probe": {"shared_feature_storage": True, "masked_rows": 2, "original_rows_changed": 2}})
        bindings = {"config_sha256": audit.digest(cls.base / "config.json"), "registration_sha256": audit.digest(registration),
            "source_commit": record["source_commit"], "upstream_commit": record["upstream_commit"], "source_manifest_sha256": record["source_manifest_sha256"],
            "environment_sha256": audit.digest(out / "WORKER_ENVIRONMENT.json"), "bundle_sha256": "1" * 64,
            "original_source_commit": record["original_source_commit"], "compact_source_commit": record["compact_source_commit"], "data_manifest_sha256": "f" * 64}
        with redirect_stdout(io.StringIO()):
            cases, frozen = worker.execute_cases(fixture.fake_author(), config, cls.base, hashes, out, torch.device("cpu"),
                SimpleNamespace(remaining=lambda: 100000., check=lambda: None), bindings)
        assert all(c["evaluation_complete"] for c in cases), cases
        result = {"status": "COMPLETE_CALIBRATED_EVALUATION", "scope": "PREVIOUSLY_EXPOSED_DEVELOPMENT_DATA", "bindings": bindings,
            "cases": cases, "selected_datasets": ["theia", "cadets"], "scientific_completion": True,
            "all_selected_evaluations_complete": True, "all_registered_evaluations_complete_in_this_attempt": True,
            "decision": "NO_GO_FIXED_CALIBRATED_METHOD", "global_freeze_sha256": frozen,
            "normal_phase_all_cases_before_any_test": True, "novelty_claimed": False,
            "independent_campaign_confirmation": False, "independent_normal_validation": False}
        cls.refresh(out, result)
        cls.config, cls.record, cls.runtime = config, record, runtime
        cls.manifest = {"datasets": [{"dataset": d, "graphs": [{"npz": f"{d}/{g}.npz", "n_nodes": 15 if g == "test0" else 12,
            "n_edges": 15 if g == "test0" else 12} for g in ("train0", "train1", "train2", "train3", "test0")]} for d in ("theia", "cadets")]}

    @classmethod
    def tearDownClass(cls):
        cls.base_temp.cleanup()

    @staticmethod
    def refresh(out, result=None):
        result = result or audit.read(out / "RESULTS.json")
        result["private_artifacts"] = {p.relative_to(out).as_posix(): audit.digest(p) for p in out.rglob("*")
            if p.is_file() and p.relative_to(out).as_posix() not in audit.core.OPERATIONAL | {"RESULTS.json"}}
        save(out / "RESULTS.json", result)
        failed = result["status"] == "FAILED_RUNTIME"
        save(out / "WORKER_STATUS.json", {"status": "FAILED" if failed else ("COMPLETE" if result["scientific_completion"] else "RESOURCE_HOLD"),
            "scientific_completion": result["scientific_completion"], "decision": result["decision"], "results_sha256": audit.digest(out / "RESULTS.json")})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "fixture"
        shutil.copytree(self.base, self.root)
        self.output = self.root / "output"

    def tearDown(self):
        self.temp.cleanup()

    def run_audit(self, **kwargs):
        with patch.object(audit, "verify_inputs", return_value=(self.record, self.manifest, self.config, self.runtime)), patch.object(audit, "HERE", self.root):
            return audit.audit(self.output, self.root, self.root, self.root / "REGISTRATION.json", **kwargs)

    def test_actual_six_case_evidence_checks_pass_and_negative_is_complete(self):
        report = self.run_audit()
        self.assertEqual(report["status"], "VERIFIED_FIXED_NORMAL_CALIBRATION")
        self.assertTrue(report["scientific_completion"])
        self.assertTrue(report["all_six_normal_freezes_verified"])
        self.assertFalse(report["bounded_development_gate_pass"])
        self.assertEqual(report["independent_decision"], "NO_GO_FIXED_CALIBRATED_METHOD")
        self.assertEqual(len(report["cases"]), 6)
        for case in report["cases"]:
            self.assertEqual(case["qualification_distances"]["verified_queries"], 4)
            self.assertEqual(case["calibration_distances"]["verified_queries"], 8)
            self.assertEqual(case["test_distances"]["verified_queries"], 8)
            self.assertEqual(case["test_distances"]["reference_rows_per_query"], 36)
            self.assertEqual(len(case["checkpoint_checks"]), 2)

    def test_hand_computed_strict_rank_ties_and_metric_values(self):
        threshold = audit.threshold_from_scores([0., 1., 1., 2.], .4)
        self.assertEqual(threshold["rank_one_based"], 3)
        self.assertEqual(threshold["threshold"], 1)
        self.assertEqual(threshold["calibration_ties_at_threshold"], 2)
        predictions, metrics = audit.fixed_metrics([0, 1, 0, 1], [0., 1., 1., 2.], threshold)
        np.testing.assert_array_equal(predictions, [False, False, False, True])
        self.assertEqual(metrics["auroc"], .875)
        self.assertAlmostEqual(metrics["average_precision"], 5 / 6)
        self.assertEqual(metrics["recall"], .5)
        self.assertEqual(metrics["false_positive_rate"], 0)
        self.assertAlmostEqual(metrics["f1"], 2 / 3)
        tiny = audit.threshold_from_scores([1., 2.], .01)
        self.assertTrue(tiny["no_alerts"])
        self.assertIsNone(tiny["threshold"])
        self.assertFalse(audit.fixed_metrics([0, 1], [1e20, 1e30], tiny)[0].any())

    def test_missing_final_result_is_incomplete_without_negative_conclusion(self):
        (self.output / "RESULTS.json").unlink()
        report = self.run_audit()
        self.assertEqual(report["status"], "INCOMPLETE_EVIDENCE")
        self.assertIsNone(report["bounded_development_gate_pass"])

    def test_one_ulp_threshold_tampering_refused_despite_rehashed_receipts(self):
        result = audit.read(self.output / "RESULTS.json")
        case = result["cases"][0]
        directory = self.output / case["case"]
        original_threshold = case["threshold"]["threshold"]
        changed = float(np.nextafter(original_threshold, -np.inf))
        # This change passes ordinary numerical tolerance but turns exact ties
        # into alerts. It must never be treated as a rounding discrepancy.
        audit.core.close(changed, original_threshold, "old tolerance counterexample")
        self.assertTrue(original_threshold > changed)
        threshold = {**case["threshold"], "threshold": changed}
        freeze = audit.read(directory / "FIT_CALIBRATION_FREEZE.json")
        freeze["threshold"] = threshold
        save(directory / "FIT_CALIBRATION_FREEZE.json", freeze)
        freeze_hash = audit.digest(directory / "FIT_CALIBRATION_FREEZE.json")
        for name in ("NORMAL_RESULT.json", "STATUS.json"):
            value = audit.read(directory / name)
            value.update(threshold=threshold, freeze_sha256=freeze_hash)
            save(directory / name, value)
        case.update(threshold=threshold, freeze_sha256=freeze_hash)
        evaluation_path = directory / "EVALUATION.npz"
        with np.load(evaluation_path, allow_pickle=False) as archive:
            arrays = dict(archive)
        arrays["predicted"], case["metrics"] = audit.fixed_metrics(arrays["y"], arrays["scores"], threshold)
        case["readiness"] = bool(case["metrics"]["recall"] >= .5 and case["metrics"]["false_positive_rate"] <= .02)
        np.savez_compressed(evaluation_path, **arrays)
        case["evaluation_sha256"] = audit.digest(evaluation_path)
        global_record = audit.read(self.output / "GLOBAL_CALIBRATION_FREEZE.json")
        for name in ("FIT_CALIBRATION_FREEZE.json", "NORMAL_RESULT.json"):
            global_record["artifacts"][case["case"] + "/" + name] = audit.digest(directory / name)
        save(self.output / "GLOBAL_CALIBRATION_FREEZE.json", global_record)
        global_hash = audit.digest(self.output / "GLOBAL_CALIBRATION_FREEZE.json")
        result["global_freeze_sha256"] = global_hash
        for item in result["cases"]:
            item["global_freeze_sha256"] = global_hash
            save(self.output / item["case"] / "CASE_RESULT.json", item)
        progress = audit.read(self.output / "NORMAL_PROGRESS.json")
        progress["cases"][0] = audit.read(directory / "NORMAL_RESULT.json")
        save(self.output / "NORMAL_PROGRESS.json", progress)
        save(self.output / "EVALUATION_PROGRESS.json", {"cases": result["cases"], "global_freeze_sha256": global_hash})
        self.refresh(self.output, result)
        with self.assertRaisesRegex(audit.core.AuditError, "Exact normal threshold mismatch: threshold"):
            self.run_audit()

    def test_threshold_integer_fields_reject_float_or_boolean_substitutes(self):
        expected = audit.threshold_from_scores([0., 1., 2., 3.], .4)
        for key in ("n", "rank_one_based", "calibration_alerts", "calibration_ties_at_threshold"):
            for value in (float(expected[key]), True):
                altered = {**expected, key: value}
                with self.assertRaisesRegex(audit.core.AuditError, "Exact threshold integer"):
                    audit.verify_threshold(altered, expected)

    def test_missing_or_duplicate_case_refused(self):
        original = audit.read(self.output / "RESULTS.json")
        for cases in (original["cases"][:-1], original["cases"][:-1] + [original["cases"][0]]):
            result = copy.deepcopy(original)
            result["cases"] = cases
            self.refresh(self.output, result)
            with self.assertRaisesRegex(audit.core.AuditError, "registered case"):
                self.run_audit()

    def test_unlisted_nested_operational_name_is_scientific_and_refused(self):
        (self.output / "theia/seed_0/worker.log").write_text("unlisted")
        with self.assertRaisesRegex(audit.core.AuditError, "inventory/hash"):
            self.run_audit()

    def test_checkpoint_nan_refused_even_after_top_inventory_rehash(self):
        path = self.output / "theia/seed_0/epoch_001.pt"
        value = torch.load(path, weights_only=True)
        next(iter(value["model"].values())).view(-1)[0] = float("nan")
        torch.save(value, path)
        self.refresh(self.output)
        with self.assertRaisesRegex(audit.core.AuditError, "Nonfinite checkpoint"):
            self.run_audit()

    def test_normal_artifact_tampering_refused_after_top_rehash(self):
        path = self.output / "theia/seed_0/CALIBRATION.npz"
        with np.load(path, allow_pickle=False) as z:
            arrays = dict(z)
        arrays["scores"][0] += 100
        np.savez_compressed(path, **arrays)
        self.refresh(self.output)
        with self.assertRaisesRegex(audit.core.AuditError, "Hash mismatch: CALIBRATION"):
            self.run_audit()

    def test_global_omission_refused_after_top_rehash(self):
        path = self.output / "GLOBAL_CALIBRATION_FREEZE.json"
        global_record = audit.read(path)
        global_record["artifacts"].pop(next(iter(global_record["artifacts"])))
        save(path, global_record)
        result = audit.read(self.output / "RESULTS.json")
        result["global_freeze_sha256"] = audit.digest(path)
        self.refresh(self.output, result)
        with self.assertRaisesRegex(audit.core.AuditError, "Global six-case freeze"):
            self.run_audit()

    def test_metrics_cannot_be_promoted_by_rehashing_results(self):
        result = audit.read(self.output / "RESULTS.json")
        case = result["cases"][0]
        case["metrics"]["recall"] = 1.
        save(self.output / case["case"] / "CASE_RESULT.json", case)
        self.refresh(self.output, result)
        with self.assertRaisesRegex(audit.core.AuditError, "metric recall"):
            self.run_audit()

    def test_evaluation_score_tampering_caught_by_full_reference_sample(self):
        result = audit.read(self.output / "RESULTS.json")
        case = result["cases"][0]
        path = self.output / case["case"] / "EVALUATION.npz"
        with np.load(path, allow_pickle=False) as z:
            arrays = dict(z)
        arrays["scores"][0] += 20
        np.savez_compressed(path, **arrays)
        case["evaluation_sha256"] = audit.digest(path)
        save(self.output / case["case"] / "CASE_RESULT.json", case)
        self.refresh(self.output, result)
        with self.assertRaisesRegex(audit.core.AuditError, "test raw mean distances"):
            self.run_audit()

    def test_source_labels_preserve_original_indices(self):
        path = self.root / "theia/test0.npz"
        with np.load(path, allow_pickle=False) as z:
            arrays = dict(z)
        arrays["y"] = np.roll(arrays["y"], 1)
        np.savez_compressed(path, **arrays)
        with self.assertRaisesRegex(audit.core.AuditError, "original row indices"):
            self.run_audit()

    def test_resource_arithmetic_uses_prior_case_test_reserves(self):
        q = audit.read(self.output / "theia/seed_101/QUALIFICATION.json")
        prior = q["resource_gate"]["prior_cases_reserved_test_seconds"]
        self.assertGreater(prior, 0)
        audit.resource_gate(q, self.config["dataset_specs"]["theia"], self.config, prior)
        with self.assertRaisesRegex(audit.core.AuditError, "prior_cases_reserved"):
            audit.resource_gate(q, self.config["dataset_specs"]["theia"], self.config, 0)

    def test_runtime_changed_and_bundle_changed_refused(self):
        runtime_path = self.output / "RUNTIME_QUALIFICATION.json"
        probe = audit.read(runtime_path)
        probe["mask_target_alias_probe"]["shared_feature_storage"] = False
        save(runtime_path, probe)
        self.refresh(self.output)
        with self.assertRaisesRegex(audit.core.AuditError, "mask-target alias"):
            self.run_audit()
        bundle = self.root / "bundle.tar.gz"
        bundle.write_bytes(b"changed")
        with self.assertRaisesRegex(audit.core.AuditError, "bundle bytes"):
            self.run_audit(bundle=bundle)

    def test_fully_unrun_resource_hold_is_incomplete_not_negative(self):
        result = audit.read(self.output / "RESULTS.json")
        for dataset in ("theia", "cadets"):
            shutil.rmtree(self.output / dataset)
        for name in ("GLOBAL_CALIBRATION_FREEZE.json", "EVALUATION_PROGRESS.json"):
            (self.output / name).unlink()
        cases = [{"case": c["case"], "dataset": c["dataset"], "seed": c["seed"], "status": "NOT_RUN_RESOURCE_HOLD",
            "normal_complete": False, "evaluation_complete": False, "completed_epochs": 0, "test_arrays_loaded": False, "test_labels_loaded": False} for c in result["cases"]]
        result.update(status="INCOMPLETE_CALIBRATION_OR_EVALUATION", cases=cases, scientific_completion=False,
            all_selected_evaluations_complete=False, all_registered_evaluations_complete_in_this_attempt=False,
            decision="PENDING_INCOMPLETE", global_freeze_sha256=None)
        save(self.output / "NORMAL_PROGRESS.json", {"cases": cases, "pending_test_reserve_seconds": 0})
        self.refresh(self.output, result)
        report = self.run_audit()
        self.assertEqual(report["status"], "VERIFIED_INCOMPLETE_EVALUATION")
        self.assertEqual(report["independent_decision"], "PENDING_INCOMPLETE")
        self.assertIsNone(report["bounded_development_gate_pass"])
        self.assertFalse(report["all_six_normal_freezes_verified"])


if __name__ == "__main__":
    unittest.main()
