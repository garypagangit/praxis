"""Transport/copy/runtime chain checks; model metrics have a separate audit suite."""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.normal_stability_continuation.analysis import verify_chain as audit


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class ChainAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prior, self.reuse_dir, self.output, self.data = [self.root / name for name in ("prior", "reuse", "output", "data")]
        for directory in (self.prior, self.reuse_dir, self.output, self.data):
            directory.mkdir()
        self.config = {"datasets": ["cadets"], "encoder_seeds": [11], "folds": [
            {"name": "A", "fit": ["train0", "train1"], "calibration": "train2", "validation": "train3"},
            {"name": "B", "fit": ["train1", "train2"], "calibration": "train3", "validation": "train0"}]}
        self.config_path = self.root / "config.json"
        save(self.config_path, self.config)
        self.manifest = {"datasets": [{"dataset": "cadets", "metadata": {"node_feature_dim": 3, "edge_feature_dim": 2},
                         "graphs": [{"npz": name + ".npz", "npz_sha256": hashlib.sha256(name.encode()).hexdigest()}
                                    for name in ("train0", "train1", "train2", "train3", "test0")]}]}
        save(self.data / "MANIFEST.json", self.manifest)
        self.original_registration = self.root / "ORIGINAL_REGISTRATION.json"
        self.original = {"git_commit": "a" * 40, "data_manifest_sha256": audit.digest(self.data / "MANIFEST.json")}
        save(self.original_registration, self.original)
        source_status = {"config_sha256": audit.digest(self.config_path), "registration_sha256": audit.digest(self.original_registration),
                         "source_commit": self.original["git_commit"], "data_manifest_sha256": self.original["data_manifest_sha256"], "device": "cpu"}
        save(self.prior / "RUN_STATUS.json", source_status)
        self.relative = "cadets/A/encoder_11"
        inventory, files = {}, {}
        for filename in audit.checkpoint_names(11):
            content = ("synthetic chain-only bytes " + filename).encode()
            sha = hashlib.sha256(content).hexdigest()
            for base, relative in ((self.prior, "private/" + self.relative), (self.reuse_dir, "checkpoints/" + self.relative),
                                   (self.output, "private/" + self.relative)):
                path = base / relative / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            files[filename] = sha
            inventory["checkpoints/" + self.relative + "/" + filename] = sha
        normal_hashes = {Path(g["npz"]).stem: g["npz_sha256"] for g in self.manifest["datasets"][0]["graphs"] if g["npz"].startswith("train")}
        entries = []
        for fold in self.config["folds"]:
            entries.append({"dataset": "cadets", "fold": fold["name"], "encoder_seed": 11,
                            "roles": {"fit": fold["fit"], "calibration": fold["calibration"], "normal_validation": fold["validation"]},
                            "node_types": 3, "relations": 2, "input_graph_sha256": normal_hashes})
        entries[0].update(directory="checkpoints/" + self.relative, files=files)
        entries[1]["reason"] = "NO_COMPLETED_ENCODER_CACHE_MANIFEST_REFIT_FROM_SCRATCH"
        self.members = {"outputs/private/" + self.relative + "/" + name: sha for name, sha in files.items()}
        self.members["outputs/RUN_STATUS.json"] = audit.digest(self.prior / "RUN_STATUS.json")
        self.archive = self.root / "result.tar.gz"
        with tarfile.open(self.archive, "w:gz") as archive:
            archive.add(self.prior, arcname="outputs")
        self.stop_path = self.root / "receipts" / "finalize.json"
        stop = {"action": "finalize", "status": "CLOSED_VERIFIED_STOPPED", "instance_state": "stopped",
                "host_time_cap_observed": True, "within_reserve": True, "gate_failed": False,
                "stopped_observed_utc": "2026-09-20T00:00:00+00:00", "recorded_utc": "2026-09-20T00:01:00+00:00"}
        save(self.stop_path, stop)
        self.execution_path = self.root / "EXECUTION.json"
        save(self.execution_path, {"finalize": {**stop, "receipt": str(self.stop_path)},
                                  "collection": {"transport_sha256": audit.digest(self.archive)}})
        self.reuse = {"schema": "normal-stability-checkpoint-reuse-v1", "status": "FROZEN_VERIFIED_ENCODER_CACHE_REUSE",
                      "created_utc": "2026-09-20T01:00:00+00:00", "original_config_sha256": audit.digest(self.config_path),
                      "original_registration_sha256": audit.digest(self.original_registration), "original_source_commit": self.original["git_commit"],
                      "data_manifest_sha256": self.original["data_manifest_sha256"], "source_device": "cpu",
                      "checkpoint_file_count_each": 21, "completed_manifest_is_authority": True, "completed_encoder_folds_counter_used": False,
                      "prior_banks_or_results_reused": False, "all_banks_calibration_and_scores_rebuilt": True, "scientific_settings_changed": False,
                      "entries": [entries[0]], "skipped": [entries[1]], "inventory": inventory,
                      "source_output_receipts": {"RUN_STATUS.json": audit.digest(self.prior / "RUN_STATUS.json")},
                      "transport_receipt_sha256": audit.digest(self.execution_path), "transport_receipt_filename": self.execution_path.name,
                      "transport": {"archive_sha256": audit.digest(self.archive), "archive_filename": self.archive.name,
                                    "archive_bytes": self.archive.stat().st_size, "verified_member_sha256": self.members,
                                    "selected_checkpoint_bytes_compared_to_archive_members": True}}
        save(self.reuse_dir / "REUSE_MANIFEST.json", self.reuse)
        self.continuation_registration = self.root / "CONTINUATION_REGISTRATION.json"
        self.continuation = {"git_commit": "b" * 40, "created_utc": "2026-09-20T02:00:00+00:00"}
        save(self.continuation_registration, self.continuation)
        fresh_manifest = self.output / "private/cadets/B/encoder_11/MANIFEST.json"
        save(fresh_manifest, {"synthetic_fresh": True})
        save(self.output / "RESULTS.json", {"device": "cpu", "started_utc": "2026-09-20T03:00:00+00:00"})
        save(self.output / "NORMAL_FREEZE.json", {"synthetic_science_only": True})
        self.qualification = {"device": "cpu", "reexecuted_in_continuation_process": True, "reused_prior_qualification": False,
                              "qualification": {"status": "CPU_SELECTED", "cuda_parity_executed": False}}
        save(self.output / "RUNTIME_QUALIFICATION.json", self.qualification)
        self.scientific_audit = self.root / "SCIENTIFIC_AUDIT.json"
        save(self.scientific_audit, {"status": "PASS", "results_sha256": audit.digest(self.output / "RESULTS.json"),
                                   "normal_freeze_sha256": audit.digest(self.output / "NORMAL_FREEZE.json"),
                                   "registration_sha256": audit.digest(self.original_registration),
                                   "auditor_sha256": audit.digest(Path(audit.science.__file__))})
        decisions = [{"relative": self.relative, "action": audit.REUSED,
                      "manifest_sha256": files["MANIFEST.json"]},
                     {"relative": "cadets/B/encoder_11", "action": audit.FRESH, "manifest_sha256": audit.digest(fresh_manifest)}]
        self.receipt = {"status": "COMPLETE_RUNTIME_CONTINUATION_ORIGINAL_SCIENTIFIC_SETTINGS",
                        "continuation_registration_sha256": audit.digest(self.continuation_registration),
                        "reuse_manifest_sha256": audit.digest(self.reuse_dir / "REUSE_MANIFEST.json"),
                        "original_results_sha256": audit.digest(self.output / "RESULTS.json"),
                        "runtime_device_qualification_sha256": audit.digest(self.output / "RUNTIME_QUALIFICATION.json"),
                        "reused_checkpoint_count": 1, "fresh_checkpoint_count": 1, "decisions": decisions,
                        "all_banks_calibration_and_scores_rebuilt": True, "original_runner_all_normal_before_attack_labels_preserved": True,
                        "scientific_settings_changed": False}
        save(self.output / "CONTINUATION_RECEIPT.json", self.receipt)
        self.partial = {"reuse_manifest_sha256": self.receipt["reuse_manifest_sha256"], "decisions": decisions}
        save(self.output / "REUSE_DECISIONS.partial.json", self.partial)

    def content(self, reuse=None):
        return audit.check_reuse_content(self.config, self.manifest, reuse or self.reuse, self.reuse_dir, self.prior, self.output)

    def test_archive_actual_member_bytes_and_missing_or_wrong_transport_are_checked(self):
        result = audit.check_archive(self.archive, audit.digest(self.archive), self.members)
        self.assertEqual(result["verified_required_members"], 22)
        for sha, members in (("0" * 64, self.members), (audit.digest(self.archive), {**self.members, "outputs/missing": "0" * 64}),
                             (audit.digest(self.archive), {**self.members, "outputs/RUN_STATUS.json": "0" * 64})):
            with self.assertRaises(audit.AuditFailure):
                audit.check_archive(self.archive, sha, members)

    def test_transport_rejects_duplicate_names_and_symbolic_links(self):
        for kind in ("duplicate", "link"):
            path = self.root / (kind + ".tar.gz")
            with tarfile.open(path, "w:gz") as archive:
                item = tarfile.TarInfo("outputs/file")
                item.size = 1
                archive.addfile(item, io.BytesIO(b"x"))
                if kind == "duplicate":
                    archive.addfile(item, io.BytesIO(b"x"))
                else:
                    link = tarfile.TarInfo("outputs/link")
                    link.type, link.linkname = tarfile.SYMTYPE, "../../elsewhere"
                    archive.addfile(link)
            with self.assertRaises(audit.AuditFailure):
                audit.check_archive(path, audit.digest(path), {})

    def test_reused_bytes_match_prior_staging_and_destination_and_no_bank_is_staged(self):
        expected, reused, skipped, members = self.content()
        self.assertEqual(len(expected), 2)
        self.assertEqual(len(reused), len(skipped))
        self.assertEqual(members, self.members)
        target = self.output / "private" / self.relative / "PREPROCESSING.npz"
        original = target.read_bytes()
        target.write_bytes(original + b"bad")
        with self.assertRaisesRegex(audit.AuditFailure, "checkpoint bytes differ"):
            self.content()
        target.write_bytes(original)
        extra = self.reuse_dir / "checkpoints" / self.relative / "bank_71" / "NORMAL_SCORES.npz"
        extra.parent.mkdir()
        extra.write_bytes(b"must not reuse scores")
        with self.assertRaisesRegex(audit.AuditFailure, "unregistered files"):
            self.content()

    def test_wrong_roles_and_selectively_skipped_completed_checkpoint_are_rejected(self):
        bad = copy.deepcopy(self.reuse)
        bad["entries"][0]["roles"]["fit"] = ["train2", "train3"]
        with self.assertRaisesRegex(audit.AuditFailure, "role/seed/data identity"):
            self.content(bad)
        save(self.prior / "private/cadets/B/encoder_11/MANIFEST.json", {"completed": True})
        with self.assertRaisesRegex(audit.AuditFailure, "completed checkpoint was excluded"):
            self.content()

    def test_decision_actions_counts_and_full_grid_are_checked(self):
        expected, reused, _, _ = self.content()
        counts = audit.check_decisions(self.receipt, self.partial, expected, reused, self.output)
        self.assertEqual(counts, {"reused_checkpoints": 1, "fresh_checkpoints": 1, "total_checkpoints": 2})
        for name in ("action", "count", "missing"):
            bad = copy.deepcopy(self.receipt)
            if name == "action":
                bad["decisions"][0]["action"] = audit.FRESH
            elif name == "count":
                bad["reused_checkpoint_count"] = 2
            else:
                bad["decisions"].pop()
            with self.subTest(name=name), self.assertRaises(audit.AuditFailure):
                audit.check_decisions(bad, self.partial, expected, reused, self.output)

    def test_current_runtime_qualification_cannot_be_replaced_with_old_receipt(self):
        self.assertEqual(audit.check_qualification(self.qualification, "cpu")["qualification_status"], "CPU_SELECTED")
        old = {**self.qualification, "reused_prior_qualification": True}
        with self.assertRaises(audit.AuditFailure):
            audit.check_qualification(old, "cpu")
        with self.assertRaises(audit.AuditFailure):
            audit.check_qualification(self.qualification, "cuda")

    def test_prior_verified_shutdown_must_precede_staging(self):
        _, report = audit.check_shutdown(self.execution_path, self.stop_path, self.reuse["created_utc"])
        self.assertTrue(report["stopped_before_staging"])
        with self.assertRaisesRegex(audit.AuditFailure, "preceded verified shutdown"):
            audit.check_shutdown(self.execution_path, self.stop_path, "2026-09-19T23:59:00+00:00")
        stop = audit.read(self.stop_path)
        stop["instance_state"] = "running"
        save(self.stop_path, stop)
        with self.assertRaisesRegex(audit.AuditFailure, "shutdown is not verified"):
            audit.check_shutdown(self.execution_path, self.stop_path, self.reuse["created_utc"])

    def timeout_evidence(self, archived_exit=124):
        """Build an interrupted synthetic attempt without changing reused state."""
        source = audit.read(self.prior / "RUN_STATUS.json")
        source["status"] = "NORMAL_PHASE_RUNNING"
        save(self.prior / "RUN_STATUS.json", source)
        (self.prior / "WORKER_EXIT.txt").write_text(str(archived_exit) + "\n", encoding="ascii")
        with tarfile.open(self.archive, "w:gz") as archive:
            archive.add(self.prior, arcname="outputs")
        stop = audit.read(self.stop_path)
        stop["gate_failed"] = True
        save(self.stop_path, stop)
        execution = audit.read(self.execution_path)
        execution["finalize"]["gate_failed"] = True
        execution["last_poll"] = {"status": "Failed", "response_code": 124}
        execution["collection"]["transport_sha256"] = audit.digest(self.archive)
        save(self.execution_path, execution)
        self.members["outputs/RUN_STATUS.json"] = audit.digest(self.prior / "RUN_STATUS.json")
        self.reuse["source_output_receipts"]["RUN_STATUS.json"] = self.members["outputs/RUN_STATUS.json"]
        self.reuse["transport_receipt_sha256"] = audit.digest(self.execution_path)
        self.reuse["transport"].update(archive_sha256=audit.digest(self.archive), archive_bytes=self.archive.stat().st_size,
                                       verified_member_sha256=self.members)
        save(self.reuse_dir / "REUSE_MANIFEST.json", self.reuse)
        self.receipt["reuse_manifest_sha256"] = audit.digest(self.reuse_dir / "REUSE_MANIFEST.json")
        save(self.output / "CONTINUATION_RECEIPT.json", self.receipt)
        self.partial["reuse_manifest_sha256"] = self.receipt["reuse_manifest_sha256"]
        save(self.output / "REUSE_DECISIONS.partial.json", self.partial)

    def test_expected_worker_timeout_passes_and_preserves_true_gate_failed_flag(self):
        self.timeout_evidence()
        before = {path: path.read_bytes() for path in (self.execution_path, self.stop_path, self.reuse_dir / "REUSE_MANIFEST.json")}
        result = self.full_audit()
        self.assertEqual(result["status"], "PASS_CONTINUATION_CHAIN")
        shutdown = result["prior_shutdown"]
        self.assertTrue(shutdown["gate_failed"])
        self.assertEqual(shutdown["worker_failure_classification"], "EXPECTED_BOUNDED_WORKER_TIMEOUT")
        self.assertEqual(shutdown["bounded_timeout_evidence"]["worker_exit_code"], 124)
        self.assertTrue(shutdown["worker_exit_verified_against_archive"])
        self.assertEqual(result["source_transport"]["verified_required_members"], 23)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_other_worker_failures_missing_exit_and_completed_science_are_refused(self):
        self.timeout_evidence()
        execution = audit.read(self.execution_path)
        for label, status, code, exit_code, phase in (
            ("other failure", "Failed", 1, 1, "NORMAL_PHASE_RUNNING"),
            ("wrong status", "Success", 124, 124, "NORMAL_PHASE_RUNNING"),
            ("missing exit", "Failed", 124, None, "NORMAL_PHASE_RUNNING"),
            ("wrong exit", "Failed", 124, 137, "NORMAL_PHASE_RUNNING"),
            ("already complete", "Failed", 124, 124, "COMPLETE_FIXED_FAMILY_DEVELOPMENT"),
        ):
            execution["last_poll"] = {"status": status, "response_code": code}
            save(self.execution_path, execution)
            with self.subTest(label=label), self.assertRaises(audit.AuditFailure):
                audit.check_shutdown(self.execution_path, self.stop_path, self.reuse["created_utc"],
                                     source_status={"status": phase}, worker_exit_code=exit_code)

    def test_timeout_cannot_override_resource_bounds(self):
        self.timeout_evidence()
        stop, execution = audit.read(self.stop_path), audit.read(self.execution_path)
        stop["within_reserve"] = execution["finalize"]["within_reserve"] = False
        save(self.stop_path, stop)
        save(self.execution_path, execution)
        with self.assertRaisesRegex(audit.AuditFailure, "resource bound failed"):
            audit.check_shutdown(self.execution_path, self.stop_path, self.reuse["created_utc"],
                                 source_status={"status": "NORMAL_PHASE_RUNNING"}, worker_exit_code=124)

    def test_local_timeout_exit_must_match_the_archived_exit_bytes(self):
        self.timeout_evidence(archived_exit=1)
        (self.prior / "WORKER_EXIT.txt").write_text("124\n", encoding="ascii")
        with self.assertRaisesRegex(audit.AuditFailure, "differs from archived bytes"):
            self.full_audit()

    def full_audit(self):
        with mock.patch.object(audit, "bind_registrations", return_value=(self.config, self.original, self.continuation, self.manifest, self.reuse)):
            return audit.audit(self.config_path, self.data, self.original_registration, self.continuation_registration, self.reuse_dir,
                               self.prior, self.archive, self.execution_path, self.stop_path, self.output, self.scientific_audit)

    def test_complete_chain_supplements_related_scientific_audit(self):
        result = self.full_audit()
        self.assertEqual(result["status"], "PASS_CONTINUATION_CHAIN")
        self.assertEqual(result["counts"]["reused_checkpoints"], 1)
        self.assertTrue(result["all_copied_checkpoint_bytes_equal_prior_archive"])
        self.assertFalse(result["scientific_settings_changed"])

    def test_unrelated_scientific_audit_is_rejected(self):
        report = audit.read(self.scientific_audit)
        report["results_sha256"] = "0" * 64
        save(self.scientific_audit, report)
        with self.assertRaisesRegex(audit.AuditFailure, "scientific audit is missing, stale or unrelated"):
            self.full_audit()


if __name__ == "__main__":
    unittest.main()
