"""Test both real Git chains and opaque checkpoint transport bindings.

Checkpoint semantic/transport-member qualification has separate end-to-end
tests. Only that expensive qualifier is stubbed here; source, data, staged
bytes, archive construction, worker invocation and refusal checks are real.
"""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.normal_stability_continuation import launch, provenance, worker


class ContinuationProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments/apt_final/normal_stability_continuation"
        self.original = self.here.parent / "normal_stability"
        self.native = self.here.parent / "native_graph"
        self.embedding = self.here.parent / "embedding_baseline"
        for directory in (self.here, self.original, self.native, self.embedding):
            directory.mkdir(parents=True)
        runtime_settings = provenance.runtime_settings()
        self.config = self.original / "config.json"
        self.original_registration = self.original / "REGISTRATION.json"
        self.registration = self.root / "CONTINUATION.json"
        self.write_json(self.config, {"scope": "DEVELOPMENT_ONLY", "neighbors": 10})
        for name in ("PROTOCOL.md", "PROTOCOL_REVIEW.md", "PINNED_BASELINES.json", "engine.py", "scoring.py",
                     "runner.py", "provenance.py", "launch.py", "worker.py", "run_cloud.sh"):
            (self.original / name).write_text("synthetic original " + name, encoding="utf-8")
        for name in ("data.py", "pilot.py", "provenance.py", "cloud_control.py"):
            (self.native / name).write_text("synthetic native " + name, encoding="utf-8")
        for name in ("engine.py", "scoring.py"):
            (self.embedding / name).write_text("synthetic embedding " + name, encoding="utf-8")
        for name in ("PROTOCOL.md", "checkpoints.py", "runner.py", "provenance.py", "launch.py", "worker.py", "run_cloud.sh"):
            (self.here / name).write_text("synthetic continuation " + name, encoding="utf-8")
        self.write_json(self.here / "config.json", runtime_settings)
        self.data = self.root / "data"
        (self.data / "cadets").mkdir(parents=True)
        self.array = self.data / "cadets/train0.npz"
        self.array.write_bytes(b"opaque normalized graph")
        self.write_json(self.data / "MANIFEST.json", {
            "schema": "apt-final-native-graph-data-v1", "status": "STATIC_DEVELOPMENT_ONLY",
            "adapter_sha256": provenance.digest(self.native / "data.py"),
            "datasets": [{"dataset": "cadets", "status": "STATIC_DEVELOPMENT_ONLY",
                          "matches_upstream_git_blob": True,
                          "graphs": [{"npz": "cadets/train0.npz", "npz_sha256": provenance.digest(self.array)}]}],
        })
        for module, mapping in (
            (provenance, {"HERE": self.here, "ORIGINAL": self.original, "NATIVE": self.native, "REPO": self.repo}),
            (provenance.original, {"HERE": self.original, "NATIVE": self.native,
                                   "EMBEDDING": self.embedding, "REPO": self.repo}),
        ):
            for name, value in mapping.items():
                patcher = mock.patch.object(module, name, value)
                patcher.start()
                self.addCleanup(patcher.stop)
        qualifier = mock.patch.object(provenance, "verify_reuse", return_value={"status": "FROZEN_VERIFIED_ENCODER_CACHE_REUSE"})
        self.qualifier = qualifier.start()
        self.addCleanup(qualifier.stop)
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "user.name", "Synthetic continuation fixture")
        self.git("add", "experiments")
        self.git("commit", "-q", "-m", "Synthetic source chains")
        self.original_record = provenance.original.register(self.config, self.data, self.original_registration)
        self.git("add", "experiments")
        self.git("commit", "-q", "-m", "Bind original scientific registration")
        self.reuse = self.root / "reuse"
        checkpoint = self.reuse / "checkpoints/cadets/A/encoder_101"
        checkpoint.mkdir(parents=True)
        self.checkpoint = checkpoint / "mlp_101.pt"
        self.checkpoint.write_bytes(b"opaque checkpoint; never deserialized in these tests")
        (checkpoint / "MANIFEST.json").write_bytes(b"opaque qualified checkpoint metadata")
        inventory = {path.relative_to(self.reuse).as_posix(): provenance.digest(path)
                     for path in checkpoint.iterdir()}
        self.reuse_manifest = {
            "schema": "normal-stability-checkpoint-reuse-v1", "status": "FROZEN_VERIFIED_ENCODER_CACHE_REUSE",
            "original_config_sha256": provenance.digest(self.config),
            "original_registration_sha256": provenance.digest(self.original_registration),
            "inventory": inventory,
        }
        self.write_json(self.reuse / "REUSE_MANIFEST.json", self.reuse_manifest)
        self.record = provenance.register(self.config, self.data, self.original_registration, self.reuse, self.registration)

    @staticmethod
    def write_json(path, value):
        Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.PIPE, text=True)

    def verify(self):
        return provenance.verify_registration(self.config, self.data, self.original_registration, self.reuse, self.registration)

    def rewrite_record(self, edit):
        record = provenance.read(self.registration)
        edit(record)
        self.write_json(self.registration, record)

    def remote_context(self, marker):
        original = Path.exists
        def exists(path):
            return False if path == self.repo / ".git" else original(path)
        return mock.patch.object(Path, "exists", exists), mock.patch.dict(os.environ, {"APT_FROZEN_BUNDLE_SHA256": marker})

    def test_original_and_continuation_commits_and_staged_bytes_are_bound(self):
        result = self.verify()
        self.assertEqual(result["status"], "FROZEN_NORMAL_STABILITY_CONTINUATION")
        self.assertFalse(result["scientific_settings_changed"])
        self.assertEqual(result["reuse_files"], self.reuse_manifest["inventory"])
        for relative in self.original_record["code_hashes"]:
            self.assertIn(relative, result["code_hashes"])
        self.assertIn(self.original_registration.relative_to(self.repo).as_posix(), result["code_hashes"])
        self.qualifier.assert_called_with(self.reuse, self.config, self.data, self.original_registration)

    def test_changed_original_configuration_is_refused(self):
        self.write_json(self.config, {"scope": "DEVELOPMENT_ONLY", "neighbors": 200})
        with self.assertRaisesRegex(ValueError, "Original scientific configuration"):
            self.verify()

    def test_changed_original_registration_is_refused(self):
        self.write_json(self.original_registration, {**self.original_record, "status": "changed"})
        with self.assertRaisesRegex(ValueError, "Original scientific registration"):
            self.verify()

    def test_changed_original_source_is_refused(self):
        (self.original / "runner.py").write_text("changed science", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Registered source changed"):
            self.verify()

    def test_changed_continuation_config_protocol_or_wrapper_is_refused(self):
        for filename in ("config.json", "PROTOCOL.md", "runner.py", "checkpoints.py"):
            path = self.here / filename
            before = path.read_bytes()
            path.write_bytes(before + b"changed")
            try:
                with self.assertRaisesRegex(ValueError, "continuation source changed"):
                    self.verify()
            finally:
                path.write_bytes(before)

    def test_added_continuation_module_invalidates_inventory(self):
        (self.here / "late_helper.py").write_text("unregistered helper", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source inventory"):
            self.verify()

    def test_missing_source_receipt_is_refused(self):
        self.rewrite_record(lambda record: record["code_hashes"].pop(next(iter(record["code_hashes"]))))
        with self.assertRaisesRegex(ValueError, "source inventory"):
            self.verify()

    def test_forged_new_source_hash_does_not_bypass_commit_binding(self):
        path = self.here / "runner.py"
        path.write_text("uncommitted wrapper", encoding="utf-8")
        self.rewrite_record(lambda record: record["code_hashes"].update({path.relative_to(self.repo).as_posix(): provenance.digest(path)}))
        with self.assertRaisesRegex(ValueError, "recorded commit"):
            self.verify()

    def test_changed_graph_and_changed_data_reference_are_refused(self):
        original = self.array.read_bytes()
        self.array.write_bytes(b"changed source graph")
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()
        self.array.write_bytes(original)
        self.rewrite_record(lambda record: record["data_files"].update({"cadets/train0.npz": "0" * 64}))
        with self.assertRaisesRegex(ValueError, "data references"):
            self.verify()

    def test_changed_reuse_manifest_is_refused(self):
        self.write_json(self.reuse / "REUSE_MANIFEST.json", {**self.reuse_manifest, "changed": True})
        with self.assertRaisesRegex(ValueError, "Reuse manifest changed"):
            self.verify()

    def test_changed_checkpoint_bytes_are_refused(self):
        self.checkpoint.write_bytes(b"replacement weights")
        with self.assertRaisesRegex(ValueError, "checkpoint bytes changed"):
            self.verify()

    def test_extra_reuse_files_are_refused(self):
        (self.checkpoint.parent / "ATTACK_SCORES.npz").write_bytes(b"unexpected prior scores")
        with self.assertRaisesRegex(ValueError, "unregistered or missing checkpoint files"):
            self.verify()

    def test_changed_registered_checkpoint_inventory_is_refused(self):
        self.rewrite_record(lambda record: record["reuse_files"].pop(next(iter(record["reuse_files"]))))
        with self.assertRaisesRegex(ValueError, "checkpoint inventory changed"):
            self.verify()

    def test_escaping_and_aliased_checkpoint_paths_are_refused(self):
        for relative in ("../outside.pt", "C:/outside.pt", "/outside.pt", "checkpoints/../outside.pt", "checkpoints\\outside.pt"):
            self.write_json(self.reuse / "REUSE_MANIFEST.json", {"inventory": {relative: "0" * 64}})
            with self.assertRaisesRegex(ValueError, "escaping graph path"):
                provenance.reuse_inventory(self.reuse)

    def test_noncheckpoint_tree_or_empty_inventory_is_refused(self):
        for inventory in ({"other/file.pt": "0" * 64}, {}):
            self.write_json(self.reuse / "REUSE_MANIFEST.json", {"inventory": inventory})
            with self.assertRaises(ValueError):
                provenance.reuse_inventory(self.reuse)

    def test_checkpoint_semantic_qualification_failure_is_not_bypassed(self):
        self.qualifier.side_effect = ValueError("invalid completed checkpoint")
        with self.assertRaisesRegex(ValueError, "invalid completed checkpoint"):
            self.verify()

    def test_no_overwrite_of_registration(self):
        before = self.registration.read_bytes()
        with self.assertRaises(FileExistsError):
            provenance.register(self.config, self.data, self.original_registration, self.reuse, self.registration)
        self.assertEqual(self.registration.read_bytes(), before)

    def test_uncommitted_continuation_protocol_cannot_be_registered(self):
        (self.here / "PROTOCOL.md").write_text("uncommitted protocol", encoding="utf-8")
        target = self.root / "NEW.json"
        with self.assertRaisesRegex(ValueError, "Commit exact continuation"):
            provenance.register(self.config, self.data, self.original_registration, self.reuse, target)
        self.assertFalse(target.exists())

    def test_wrong_status_and_invalid_git_commit_are_refused(self):
        self.rewrite_record(lambda record: record.update(status="FROZEN_NORMAL_STABILITY"))
        with self.assertRaisesRegex(ValueError, "runtime-only"):
            self.verify()
        self.write_json(self.registration, {**self.record, "git_commit": "HEAD"})
        with self.assertRaisesRegex(ValueError, "complete Git commit"):
            self.verify()

    def test_receipt_cannot_claim_changed_science_or_a_different_original_commit(self):
        for key, value in (("scientific_settings_changed", True), ("all_banks_and_calibration_recomputed", False),
                           ("all_attack_conditions_replayed", False), ("confirmation_registered", True)):
            self.write_json(self.registration, {**self.record, key: value})
            with self.assertRaisesRegex(ValueError, "unchanged-science contract"):
                self.verify()
        self.write_json(self.registration, {**self.record, "original_source_commit": "0" * 40})
        with self.assertRaisesRegex(ValueError, "Original source commit reference"):
            self.verify()

    def test_remote_requires_external_marker_for_both_source_chains(self):
        git_patch, env_patch = self.remote_context("")
        with git_patch, env_patch:
            with self.assertRaisesRegex(ValueError, "externally hash-verified"):
                self.verify()
        git_patch, env_patch = self.remote_context("a" * 64)
        with git_patch, env_patch:
            self.assertEqual(self.verify()["status"], "FROZEN_NORMAL_STABILITY_CONTINUATION")

    def test_remote_marker_does_not_bypass_changed_wrapper(self):
        (self.here / "runner.py").write_text("changed remote wrapper", encoding="utf-8")
        git_patch, env_patch = self.remote_context("a" * 64)
        with git_patch, env_patch:
            with self.assertRaisesRegex(ValueError, "continuation source changed"):
                self.verify()

    def test_bundle_contains_exact_original_data_sources_and_qualified_reuse_files(self):
        target = self.root / "bundle.tar.gz"
        with mock.patch.object(launch, "REPO", self.repo):
            sha = launch.build_bundle(self.config, self.data, self.original_registration, self.reuse, self.registration, target)
        self.assertEqual(sha, provenance.digest(target))
        with tarfile.open(target, "r:gz") as archive:
            names = set(archive.getnames())
        expected = {"repo/" + rel for rel in self.record["code_hashes"]}
        expected |= {"data/" + rel for rel in self.record["data_files"]}
        expected |= {"reuse/" + rel for rel in self.record["reuse_files"]}
        expected |= {"data/MANIFEST.json", "reuse/REUSE_MANIFEST.json",
                     "repo/experiments/apt_final/normal_stability_continuation/REGISTRATION.json"}
        self.assertEqual(names, expected)
        with mock.patch.object(launch, "REPO", self.repo), self.assertRaises(FileExistsError):
            launch.build_bundle(self.config, self.data, self.original_registration, self.reuse, self.registration, target)

    def test_input_bundle_enforces_registered_member_and_byte_bounds(self):
        for bounds in ({"archive_max_members": 1, "archive_max_bytes": 4_000_000_000},
                       {"archive_max_members": 2000, "archive_max_bytes": 1}):
            target = self.root / "oversized.tar.gz"
            with mock.patch.object(launch, "REPO", self.repo), mock.patch.object(launch, "runtime_settings", return_value=bounds):
                with self.assertRaisesRegex(ValueError, "archive bound"):
                    launch.build_bundle(self.config, self.data, self.original_registration, self.reuse, self.registration, target)
            self.assertFalse(target.exists())


class ContinuationWorkerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.args = ["--data-dir", str(self.root / "data"), "--output", str(self.root / "outputs"),
                     "--original-registration", str(self.root / "ORIGINAL.json"),
                     "--reuse-dir", str(self.root / "reuse"), "--registration", str(self.root / "CONTINUATION.json")]

    def test_registration_checked_before_output_or_execution(self):
        with mock.patch.object(worker, "verify_registration", side_effect=ValueError("unregistered")), \
                mock.patch.object(worker.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "unregistered"):
                worker.main(self.args)
        self.assertFalse((self.root / "outputs").exists())
        execute.assert_not_called()

    def test_one_cuda_wrapper_call_receives_both_registrations_and_reuse_dir(self):
        with mock.patch.object(worker, "verify_registration", return_value={}), \
                mock.patch.object(worker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as execute:
            self.assertEqual(worker.main(self.args), 0)
        execute.assert_called_once()
        command = execute.call_args.args[0]
        self.assertIn("experiments.apt_final.normal_stability_continuation.runner", command)
        self.assertEqual(command[-2:], ["--device", "cuda"])
        for argument in ("--original-registration", "--registration", "--reuse-dir"):
            self.assertIn(argument, command)
        self.assertNotIn("--dataset", command)
        self.assertEqual(provenance.read(self.root / "outputs/WORKER_STATUS.json")["status"], "COMPLETE")

    def test_failure_remains_incomplete_and_cannot_overwrite_attempt(self):
        with mock.patch.object(worker, "verify_registration", return_value={}), \
                mock.patch.object(worker.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as execute:
            self.assertEqual(worker.main(self.args), 7)
            status = self.root / "outputs/WORKER_STATUS.json"
            original = status.read_bytes()
            self.assertEqual(provenance.read(status)["status"], "INCOMPLETE")
            with self.assertRaises(FileExistsError):
                worker.main(self.args)
            self.assertEqual(status.read_bytes(), original)
        execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
