"""Independent evidence audits, including semantic tampering after hash refresh."""
from __future__ import annotations

import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

from experiments.apt_final.magic_reproduction.analysis import audit as a
from experiments.apt_final.magic_reproduction.analysis import compact_audit as compact


class IndependentMathTests(unittest.TestCase):
    def test_ties_have_known_auc_average_precision_and_threshold_counts(self):
        # Ascending tie groups: negative; positive+negative; positive.
        actual = a.independent_metrics([0, 1, 0, 1], [0., 1., 1., 2.], .99)
        self.assertAlmostEqual(actual["auroc"], .875)
        self.assertAlmostEqual(actual["average_precision"], 5 / 6)
        row = actual["author_recall_rule"]
        self.assertEqual((row["tp"], row["fp"], row["tn"], row["fn"]), (2, 1, 1, 0))
        self.assertEqual(row["threshold"], 1.)
        self.assertAlmostEqual(row["f1"], .8)

    def test_all_tied_scores_reproduce_prevalence_not_perfect_separation(self):
        actual = a.independent_metrics([0, 1, 0, 1], [4., 4., 4., 4.], .99996)
        self.assertEqual(actual["auroc"], .5)
        self.assertEqual(actual["average_precision"], .5)
        self.assertEqual(actual["author_recall_rule"]["false_positive_rate"], 1.)

    def test_full_bank_tiles_keep_duplicate_multiplicity_and_late_neighbors(self):
        bank = np.array([[100., 0.], [100., 0.], [3., 4.], [0., 0.], [0., 0.]])
        distances = a.exact_distances(bank, [[0., 0.], [3., 4.]], k=2, block=2)
        np.testing.assert_array_equal(distances, [0., 2.5])


class EvidenceFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments/apt_final/magic_reproduction"
        self.data, self.source, self.output = (self.root / n for n in ("data", "source", "output"))
        for directory in (self.here, self.data / "theia", self.source / "model", self.output):
            directory.mkdir(parents=True)
        self.registration = self.root / "REGISTRATION.json"
        self.write = lambda path, value: Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        self.config = {"datasets": ["theia", "cadets"], "allow_full_run": True,
                       "training": {"epochs": 50, "seed": 0, "hidden_dim": 64},
                       "knn": {"qualification_queries": 64, "numerical_rtol": 1e-6, "numerical_atol": 1e-8},
                       "resources": {"estimate_multiplier": 1.25, "safety_seconds": 180},
                       "dataset_specs": {"theia": {"train_graphs": [f"train{i}" for i in range(4)],
                           "test_graph": "test0", "expected_test_nodes": 8, "k": 2, "author_recall_target": .99996}}}
        self.runtime = {"python": "3.10", "torch": "2.5.1+cu121", "dgl": "1.1.3+cu121",
                        "numpy": "1.26.4", "scipy": "1.14.1", "scikit_learn": "1.5.2",
                        "joblib": "1.4.2", "threadpoolctl": "3.5.0", "networkx": "3.3", "tqdm": "4.66.5", "psutil": "6.0.0",
                        "wheel": "synthetic.whl", "wheel_url": "https://example.invalid/synthetic.whl", "wheel_sha256": "0" * 64}
        for rel in a.OPERATIVE:
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic source\n", encoding="utf-8")
        self.write(self.here / "config.json", self.config)
        self.write(self.here / "RUNTIME.json", self.runtime)
        graphs = []
        for name in [f"train{i}" for i in range(4)] + ["test0"]:
            rows = 8 if name == "test0" else 4
            np.savez_compressed(self.data / "theia" / (name + ".npz"),
                                node_type=np.zeros(rows, dtype=np.int64), src=np.array([0, 1]), dst=np.array([1, 2]),
                                relation=np.zeros(2, dtype=np.int64), y=np.arange(rows, dtype=np.int8) % 2)
            rel = "theia/" + name + ".npz"
            graphs.append({"npz": rel, "npz_sha256": a.digest(self.data / rel), "n_nodes": rows, "n_edges": 2})
        self.manifest = {"datasets": [{"dataset": "theia", "graphs": graphs}]}
        self.write(self.data / "MANIFEST.json", self.manifest)
        self.data_sha = a.digest(self.data / "MANIFEST.json")
        (self.source / "model/autoencoder.py").write_text("synthetic exact source\n", encoding="utf-8")
        source_manifest = {"commit": a.UPSTREAM, "files": {"model/autoencoder.py": a.digest(self.source / "model/autoencoder.py")}}
        self.write(self.source / "SOURCE_MANIFEST.json", source_manifest)
        self.record = {"status": "FROZEN_MAGIC_DEVELOPMENT_REPRODUCTION", "upstream_commit": a.UPSTREAM,
                       "source_commit": "1" * 40, "novelty_claimed": False, "confirmation_claimed": False,
                       "test_previously_exposed": True, "code_hashes": {rel: a.digest(self.repo / rel) for rel in a.OPERATIVE},
                       "data_files": {"MANIFEST.json": self.data_sha, **{g["npz"]: g["npz_sha256"] for g in graphs}},
                       "source_manifest_sha256": a.digest(self.source / "SOURCE_MANIFEST.json"), "upstream_files": source_manifest["files"]}
        self.write(self.registration, self.record)
        for name, value in (("HERE", self.here), ("REPO", self.repo), ("DATA_MANIFEST", self.data_sha)):
            patch = mock.patch.object(a, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        environment = {"python": "3.10.12 synthetic", "torch": self.runtime["torch"], "dgl": self.runtime["dgl"],
                       "numpy": self.runtime["numpy"], "sklearn": self.runtime["scikit_learn"], "cuda": "12.1",
                       "historical_runtime_reproduced": False}
        self.write(self.output / "WORKER_ENVIRONMENT.json", environment)
        self.write(self.output / "ENVIRONMENT.json", {"python": "3.10.12 synthetic", "dependency_versions": {
            k: v for k, v in self.runtime.items() if k not in {"python", "wheel", "wheel_url", "wheel_sha256"}}})
        self.bindings = {"config_sha256": a.digest(self.here / "config.json"), "registration_sha256": a.digest(self.registration),
                         "author_source_manifest_sha256": self.record["source_manifest_sha256"],
                         "worker_environment_sha256": a.digest(self.output / "WORKER_ENVIRONMENT.json"),
                         "source_commit": self.record["source_commit"], "upstream_commit": a.UPSTREAM,
                         "data_manifest_sha256": self.data_sha}
        self.write(self.output / "RUNTIME_QUALIFICATION.json", {"bindings": self.bindings, "author": {
            "status": "PASS", "forward_backward_qualified": True, "encoder_normalizations": ["NoneType"] * 3,
            "normalization_fix_applied": False, "determinism_fix_applied": False,
            "mask_target_alias_probe": {"shared_feature_storage": True, "masked_rows": 10, "original_rows_changed": 10}},
            "synthetic_exact_knn": {"status": "PASS"}})
        self.case = self.output / "theia"
        self.case.mkdir()
        self.epoch = {"seconds": 4., "epoch_loss": 1., "graphs": [
            {"graph": f"train{i}", "nodes": 4, "edges": 2, "scaled_loss": .25, "seconds": 1.} for i in range(4)]}
        rng = np.random.default_rng(731)
        self.raw = rng.normal(size=(16, 64)).astype(np.float32)
        self.mean, self.scale = self.raw.mean(axis=0), self.raw.std(axis=0)
        self.bank = (self.raw - self.mean) / self.scale
        rng = np.random.default_rng(90210)
        indices, small_bank = rng.choice(16, 16, replace=False), rng.choice(16, 16, replace=False)
        distances = self.reference(self.bank, self.bank[indices], 2)
        path = self.case / "QUALIFICATION_TRAIN_EMBEDDINGS.npz"
        np.savez_compressed(path, raw=self.raw, mean=self.mean, scale=self.scale, sample_indices=indices,
                            sample_distances=distances, numerical_bank_indices=small_bank)
        components = {"remaining_training": 196., "final_training_embeddings": 4., "evaluation_embeddings": 4.,
                      "full_reference_normalizer": .016, "full_evaluation_scoring": .008,
                      "reference_transfer": .01, "artifact_serialization": .15}
        self.gate = {"status": "NOT_RUN_RESOURCE_HOLD", "remaining_seconds": 300.,
                     "predicted_remaining_seconds": sum(components.values()) * 1.25 + 180,
                     "components_seconds_before_multiplier": components, "estimate_multiplier": 1.25, "safety_seconds": 180,
                     "measured_full_epoch_seconds": 4., "measured_sample_queries": 16, "measured_sample_seconds": .016,
                     "normalizer_queries": 16, "planned_evaluation_queries": 8, "reference_rows": 16,
                     "reference_sampling": False, "qualification_uses_evaluation_arrays_or_labels": False}
        self.qualification = {"dataset": "theia", "source_mode": "source_original", "bindings": self.bindings,
            "test_arrays_loaded": False, "test_labels_loaded": False, "epoch": self.epoch,
            "training_embeddings": {"seconds": 4., "rows": 16, "graphs": [
                {"graph": f"train{i}", "nodes": 4, "seconds": 1.} for i in range(4)]},
            "saved_embeddings": {"file": path.name, "sha256": a.digest(path), "seconds": .1, "rows": 16, "dimension": 64},
            "full_reference_sample_timing": {"seconds": .016, "query_rows": 16, "reference_rows": 16, "k": 2, "reference_sampling": False},
            "real_training_numeric_qualification": {"status": "PASS"}, "resource_gate": self.gate}
        self.write(self.case / "QUALIFICATION.json", self.qualification)
        self.status = {"dataset": "theia", "status": "NOT_RUN_RESOURCE_HOLD", "completed_epochs": 1,
                       "test_arrays_loaded": False, "test_labels_loaded": False, "evaluation_complete": False,
                       "training_complete": False, "source_mode": "source_original", "bindings": self.bindings,
                       "epochs": [{"epoch": 1, **self.epoch}], "latest_checkpoint": self.make_checkpoint(1),
                       "qualification_sha256": a.digest(self.case / "QUALIFICATION.json"), "resource_gate": self.gate}
        self.results = {"status": "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION",
                        "scope": "EXPOSED_DATA_DEVELOPMENT_REPRODUCTION", "bindings": self.bindings,
                        "selected_datasets": ["theia"], "unselected_datasets": ["cadets"], "datasets": {"theia": self.status},
                        "novelty_claimed": False, "deployment_readiness_claimed": False,
                        "all_selected_evaluations_complete": False, "all_registered_evaluations_complete_in_this_attempt": False}
        self.refresh()

    @staticmethod
    def reference(bank, query, k):
        distance = np.linalg.norm(np.asarray(query, dtype=np.float64)[:, None] - np.asarray(bank, dtype=np.float64)[None], axis=2)
        return np.sort(distance, axis=1)[:, :k].mean(axis=1)

    def make_checkpoint(self, epoch):
        path = self.case / f"epoch_{epoch:03d}.pt"
        torch.save({"completed_epochs": epoch, "bindings": self.bindings, "source_mode": "source_original",
                    "model": {"synthetic_weight": torch.tensor([float(epoch)])}, "optimizer": {},
                    "rng": {"dgl_rng_state_captured": False, "checkpoint_continuation_qualified": False}}, path)
        return {"file": path.name, "sha256": a.digest(path), "completed_epochs": epoch}

    def refresh(self):
        self.write(self.case / "STATUS.json", self.status)
        self.results["datasets"]["theia"] = self.status
        self.results["private_artifacts"] = {p.relative_to(self.output).as_posix(): a.digest(p)
            for p in self.output.rglob("*") if p.is_file() and p.name not in a.OPERATIONAL | {"RESULTS.json", "RUN_STATUS.json"}}
        self.write(self.output / "RESULTS.json", self.results)
        self.write(self.output / "RUN_STATUS.json", self.results)
        complete = self.results["all_selected_evaluations_complete"]
        self.write(self.output / "WORKER_STATUS.json", {"status": "COMPLETE" if complete else "RESOURCE_HOLD",
            "selected_datasets": ["theia"], "scientific_completion": complete, "results_sha256": a.digest(self.output / "RESULTS.json")})

    def run_audit(self):
        return a.audit(self.output, self.data, self.source, self.registration)

    def qualify_changes(self):
        self.write(self.case / "QUALIFICATION.json", self.qualification)
        self.status["qualification_sha256"] = a.digest(self.case / "QUALIFICATION.json")
        self.refresh()

    def complete_case(self):
        self.gate.update(status="PASS", remaining_seconds=600.)
        self.qualify_changes()
        self.status.update(status="COMPLETE_SOURCE_ORIGINAL_DEVELOPMENT_REPRODUCTION", completed_epochs=50,
                           training_complete=True, evaluation_complete=True, test_arrays_loaded=True, test_labels_loaded=True,
                           epochs=[{"epoch": i, **self.epoch} for i in range(1, 51)])
        for epoch in range(2, 51):
            self.status["latest_checkpoint"] = self.make_checkpoint(epoch)
        path = self.case / "TRAIN_EMBEDDINGS.npz"
        np.savez_compressed(path, raw=self.raw, mean=self.mean, scale=self.scale)
        freeze = {"dataset": "theia", "bindings": self.bindings, "completed_epochs": 50,
                  "checkpoint": self.status["latest_checkpoint"], "test_arrays_loaded": False, "test_labels_loaded": False,
                  "training_embeddings": {"file": path.name, "sha256": a.digest(path), "rows": 16, "dimension": 64}}
        self.write(self.case / "FIT_FREEZE.json", freeze)
        self.status["fit_freeze_sha256"] = a.digest(self.case / "FIT_FREEZE.json")
        raw = np.random.default_rng(313).normal(size=(8, 64)).astype(np.float32)
        raw[1::2] += 1.
        y = np.arange(8, dtype=np.int8) % 2
        shuffled = list(range(16))
        random.Random(0).shuffle(shuffled)
        normalizer = self.reference(self.bank, self.bank[shuffled], 2)
        distances = self.reference(self.bank, (raw - self.mean) / self.scale, 2)
        scores = distances / normalizer.mean()
        np.savez_compressed(self.case / "EVALUATION.npz", raw=raw, y=y, distances=distances, scores=scores,
                            normalizer_indices=np.asarray(shuffled), normalizer_distances=normalizer, mean_distance=normalizer.mean())
        metrics = a.independent_metrics(y, scores, .99996)
        for arm in ("author_recall_rule", "supplemental_max_f1_oracle"):
            metrics[arm].update(threshold_uses_test_labels=True, deployment_readiness=False)
        metrics["author_recall_rule"]["target_recall"] = .99996
        metrics.update(all_threshold_metrics_label_selected=True, novelty_claimed=False, operational_threshold_evaluated=False)
        self.status.update(metrics=metrics, evaluation_sha256=a.digest(self.case / "EVALUATION.npz"),
                           reference_rows=16, test_rows=8, test_labels_selected_thresholds=True)
        self.results.update(status="COMPLETE_SELECTED_REPRODUCTIONS", all_selected_evaluations_complete=True)
        self.refresh()

    def change_npz(self, filename, change):
        path = self.case / filename
        with np.load(path, allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in archive.files}
        change(arrays)
        np.savez_compressed(path, **arrays)

    def test_resource_hold_is_verified_incomplete_not_negative_science(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "VERIFIED_INCOMPLETE_EVALUATION")
        self.assertTrue(result["evidence_audit_passed"])
        self.assertFalse(result["scientific_completion"])
        self.assertFalse(result["negative_scientific_conclusion"])
        check = result["datasets"]["theia"]["qualification_distance_check"]
        self.assertEqual(check["verified_queries"], 16)
        self.assertEqual(check["saved_queries"], 16)
        self.assertEqual(check["reference_rows_per_query"], 16)

    def test_complete_case_checks_all_checkpoints_labels_scores_and_oracles(self):
        self.complete_case()
        result = self.run_audit()
        self.assertEqual(result["status"], "VERIFIED_DESCRIPTIVE_EVALUATION")
        self.assertTrue(result["scientific_completion"])
        self.assertFalse(result["all_registered_evaluations_complete_in_this_attempt"])
        case = result["datasets"]["theia"]
        self.assertEqual(len(case["checkpoints_checked"]), 50)
        self.assertTrue(case["normalizer_shuffle_and_original_labels_verified"])
        self.assertEqual(case["test_distance_check"]["verified_queries"], 8)

    def test_missing_final_result_is_explicitly_incomplete(self):
        (self.output / "RESULTS.json").unlink()
        result = self.run_audit()
        self.assertEqual(result["status"], "INCOMPLETE_EVIDENCE")
        self.assertFalse(result["scientific_completion"])
        self.assertFalse(result["negative_scientific_conclusion"])

    def test_private_artifact_tampering_is_detected(self):
        with (self.case / "epoch_001.pt").open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(a.AuditError, "inventory/hash"):
            self.run_audit()

    def test_checkpoint_nan_is_detected_even_after_receipt_hashes_are_refreshed(self):
        path = self.case / "epoch_001.pt"
        saved = torch.load(path, map_location="cpu", weights_only=True)
        saved["model"]["synthetic_weight"][0] = float("nan")
        torch.save(saved, path)
        self.status["latest_checkpoint"]["sha256"] = a.digest(path)
        self.refresh()
        with self.assertRaisesRegex(a.AuditError, "Nonfinite checkpoint"):
            self.run_audit()

    def test_forged_resource_gate_arithmetic_is_detected_after_hash_refresh(self):
        self.gate["predicted_remaining_seconds"] -= 100.
        self.qualify_changes()
        with self.assertRaisesRegex(a.AuditError, "predicted resource budget"):
            self.run_audit()

    def test_corrupt_sample_distance_is_detected_after_hash_refresh(self):
        self.change_npz("QUALIFICATION_TRAIN_EMBEDDINGS.npz", lambda arrays: arrays["sample_distances"].__setitem__(0, 999.))
        self.qualification["saved_embeddings"]["sha256"] = a.digest(self.case / "QUALIFICATION_TRAIN_EMBEDDINGS.npz")
        self.qualify_changes()
        with self.assertRaisesRegex(a.AuditError, "qualification distances"):
            self.run_audit()

    def test_training_scaler_change_is_detected_after_hash_refresh(self):
        self.change_npz("QUALIFICATION_TRAIN_EMBEDDINGS.npz", lambda arrays: arrays["mean"].__setitem__(0, 99.))
        self.qualification["saved_embeddings"]["sha256"] = a.digest(self.case / "QUALIFICATION_TRAIN_EMBEDDINGS.npz")
        self.qualify_changes()
        with self.assertRaisesRegex(a.AuditError, "training mean"):
            self.run_audit()

    def test_evaluation_labels_cannot_be_replaced_after_hash_refresh(self):
        self.complete_case()
        self.change_npz("EVALUATION.npz", lambda arrays: arrays["y"].__setitem__(0, 1))
        self.status["evaluation_sha256"] = a.digest(self.case / "EVALUATION.npz")
        self.refresh()
        with self.assertRaisesRegex(a.AuditError, "original row indices"):
            self.run_audit()

    def test_normalizer_shuffle_and_metrics_tampering_are_detected(self):
        self.complete_case()
        self.status["metrics"]["auroc"] = -1.
        self.refresh()
        with self.assertRaisesRegex(a.AuditError, "auroc"):
            self.run_audit()
        self.change_npz("EVALUATION.npz", lambda arrays: arrays.__setitem__("normalizer_indices", arrays["normalizer_indices"][::-1]))
        self.status["evaluation_sha256"] = a.digest(self.case / "EVALUATION.npz")
        self.refresh()
        with self.assertRaisesRegex(a.AuditError, "shuffled normalizer"):
            self.run_audit()

    def test_claim_of_fifty_epochs_requires_fifty_actual_checkpoint_files(self):
        self.complete_case()
        (self.case / "epoch_024.pt").unlink()
        self.refresh()
        with self.assertRaises((a.AuditError, FileNotFoundError)):
            self.run_audit()

    def test_registered_code_data_source_and_runtime_are_bound(self):
        for path in (self.here / "worker.py", self.data / "theia/train0.npz", self.source / "model/autoencoder.py"):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                try:
                    with self.assertRaisesRegex(a.AuditError, "Hash mismatch"):
                        self.run_audit()
                finally:
                    path.write_bytes(original)
        env = a.read(self.output / "WORKER_ENVIRONMENT.json")
        env["torch"] = "wrong"
        self.write(self.output / "WORKER_ENVIRONMENT.json", env)
        self.refresh()
        with self.assertRaisesRegex(a.AuditError, "bindings mismatch"):
            self.run_audit()

    def test_extra_artifact_is_not_silently_ignored(self):
        (self.output / "unlisted-scientific-array.npz").write_bytes(b"unexpected")
        with self.assertRaisesRegex(a.AuditError, "inventory/hash"):
            self.run_audit()

    def test_nested_operational_name_cannot_hide_unlisted_scientific_artifact(self):
        (self.case / "worker.log").write_bytes(b"unexpected nested artifact")
        with self.assertRaisesRegex(a.AuditError, "inventory/hash"):
            self.run_audit()

    def test_audit_cli_writes_new_artifacts_and_refuses_evidence_directory(self):
        argv = ["--output-dir", str(self.output), "--data-dir", str(self.data), "--source-dir", str(self.source),
                "--registration", str(self.registration), "--audit-output", str(self.root / "audit")]
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(a.main(argv), 0)
        self.assertTrue((self.root / "audit/AUDIT.json").is_file())
        self.assertTrue((self.root / "audit/AUDIT.md").is_file())
        with self.assertRaises(FileExistsError):
            a.main(argv)
        with self.assertRaisesRegex(a.AuditError, "outside evidence"):
            a.main(argv[:-1] + [str(self.output / "audit")])

    def add_compact_chain(self):
        for relative in compact.COMPACT_FILES:
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic compact source\n", encoding="utf-8")
        self.compact_registration = self.root / "COMPACT_REGISTRATION.json"
        amendment = {"status": "FROZEN_EXACT_MULTIPLICITY_RUNTIME", "source_commit": "2" * 40,
                     "code_hashes": {r: a.digest(self.repo / r) for r in compact.COMPACT_FILES},
                     "original_registration_sha256": a.digest(self.registration),
                     "original_source_commit": self.record["source_commit"], "science_changed": False,
                     "exact_duplicate_storage_only": True, "checkpoint_reuse": False, "novelty_claimed": False}
        self.write(self.compact_registration, amendment)
        timing = self.qualification["full_reference_sample_timing"]
        timing.update(original_reference_rows=16, unique_reference_rows=16, reference_occurrences_preserved=16,
                      duplicate_fraction=0., construction_seconds=.01, unique_construction_seconds=.005,
                      reference_duplicates_preserved=True, integer_multiplicities_preserved=True,
                      search="exact", distance="direct_float64_euclidean")
        self.qualify_changes()
        self.bundle = self.root / "bundle.tar.gz"
        self.bundle.write_bytes(b"opaque original frozen bundle identity")
        self.compact_receipt = {"status": "COMPACT_RUNTIME_RECORDED", "compact_registration_sha256": a.digest(self.compact_registration),
            "original_registration_sha256": a.digest(self.registration), "source_commit": "2" * 40,
            "original_source_commit": self.record["source_commit"], "source_original_unchanged": True,
            "source_mode": "exact_multiplicity_runtime", "substitutions": compact.SUBSTITUTIONS,
            "results_sha256": a.digest(self.output / "RESULTS.json"), "bundle_sha256": a.digest(self.bundle),
            "selected_datasets": ["theia"], "exit_code": 0, "novelty_claimed": False, "checkpoint_reuse": False}
        self.write(self.output / compact.RECEIPT, self.compact_receipt)

    def run_compact_audit(self):
        return compact.audit(self.output, self.data, self.source, self.registration, self.compact_registration, bundle=self.bundle)

    def test_compact_chain_runs_original_audit_without_hiding_new_artifacts(self):
        self.add_compact_chain()
        with self.assertRaisesRegex(a.AuditError, "inventory/hash"):
            self.run_audit()
        result = self.run_compact_audit()
        self.assertTrue(result["evidence_audit_passed"])
        self.assertEqual(result["status"], "VERIFIED_INCOMPLETE_EVALUATION")
        self.assertTrue(result["compact_chain"]["input_bundle_bytes_independently_checked"])
        self.assertEqual(result["datasets"]["theia"]["compression_inventory"]["QUALIFICATION_TRAIN_EMBEDDINGS.npz"]["sum_integer_multiplicities"], 16)
        (self.output / "unlisted.npz").write_bytes(b"not a receipt")
        with self.assertRaisesRegex(a.AuditError, "inventory/hash"):
            self.run_compact_audit()

    def test_compact_receipt_substitution_and_result_tampering_are_refused(self):
        self.add_compact_chain()
        for field, value in (("results_sha256", "0" * 64), ("substitutions", {}), ("exit_code", 1),
                             ("source_original_unchanged", False), ("compact_registration_sha256", "0" * 64)):
            with self.subTest(field=field):
                changed = {**self.compact_receipt, field: value}
                self.write(self.output / compact.RECEIPT, changed)
                with self.assertRaises(a.AuditError):
                    self.run_compact_audit()

    def test_compact_source_and_bundle_changes_are_refused(self):
        self.add_compact_chain()
        self.bundle.write_bytes(b"different bundle")
        with self.assertRaisesRegex(a.AuditError, "bundle hash"):
            self.run_compact_audit()
        self.bundle.write_bytes(b"opaque original frozen bundle identity")
        path = self.repo / "experiments/apt_final/magic_compact/scoring.py"
        path.write_text("changed distance algorithm\n", encoding="utf-8")
        with self.assertRaisesRegex(a.AuditError, "Hash mismatch"):
            self.run_compact_audit()

    def test_compact_population_claim_is_independently_counted(self):
        self.add_compact_chain()
        self.qualification["full_reference_sample_timing"]["unique_reference_rows"] = 1
        self.qualify_changes()
        # Remove receipt from the original worker's pre-receipt artifact inventory.
        self.results["private_artifacts"].pop(compact.RECEIPT)
        self.write(self.output / "RESULTS.json", self.results)
        self.write(self.output / "RUN_STATUS.json", self.results)
        worker = a.read(self.output / "WORKER_STATUS.json")
        worker["results_sha256"] = a.digest(self.output / "RESULTS.json")
        self.write(self.output / "WORKER_STATUS.json", worker)
        self.compact_receipt["results_sha256"] = a.digest(self.output / "RESULTS.json")
        self.write(self.output / compact.RECEIPT, self.compact_receipt)
        with self.assertRaisesRegex(a.AuditError, "multiplicity/population"):
            self.run_compact_audit()


if __name__ == "__main__":
    unittest.main()
