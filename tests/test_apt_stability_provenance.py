"""Real synthetic Git freezes plus bounded worker and transport guard tests."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.normal_stability import launch, provenance, worker


class StabilityProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments/apt_final/normal_stability"
        self.native = self.here.parent / "native_graph"
        self.embedding = self.here.parent / "embedding_baseline"
        for directory in (self.here, self.native, self.embedding):
            directory.mkdir(parents=True)
        self.data = self.root / "data"
        (self.data / "cadets").mkdir(parents=True)
        self.config = self.here / "config.json"
        self.registration = self.root / "REGISTRATION.json"
        self.write_json(self.config, {"scope": "DEVELOPMENT_ONLY", "neighbors": 10})
        for name in ("PROTOCOL.md", "PROTOCOL_REVIEW.md", "provenance.py", "runner.py", "launch.py", "worker.py", "run_cloud.sh"):
            (self.here / name).write_text("synthetic fixture: " + name + "\n", encoding="utf-8")
        self.write_json(self.here / "PINNED_BASELINES.json", {"cadets": {"mean_f1": 0.001}})
        for name in ("data.py", "pilot.py", "provenance.py", "cloud_control.py"):
            (self.native / name).write_text("synthetic native: " + name + "\n", encoding="utf-8")
        for name in ("engine.py", "scoring.py"):
            (self.embedding / name).write_text("synthetic import: " + name + "\n", encoding="utf-8")
        # Guards bind opaque bytes; the scientific loader tests NPZ semantics separately.
        self.array = self.data / "cadets/train0.npz"
        self.array.write_bytes(b"synthetic normalized array bytes")
        self.manifest = {
            "schema": "apt-final-native-graph-data-v1", "status": "STATIC_DEVELOPMENT_ONLY",
            "adapter_sha256": provenance.digest(self.native / "data.py"),
            "datasets": [{"dataset": "cadets", "status": "STATIC_DEVELOPMENT_ONLY",
                          "matches_upstream_git_blob": True,
                          "graphs": [{"npz": "cadets/train0.npz", "npz_sha256": provenance.digest(self.array)}]}],
        }
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        for name, value in (("HERE", self.here), ("NATIVE", self.native),
                            ("EMBEDDING", self.embedding), ("REPO", self.repo)):
            patcher = mock.patch.object(provenance, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "user.name", "Synthetic provenance fixture")
        self.git("add", "experiments")
        self.git("commit", "-q", "-m", "Synthetic committed source")
        self.record = provenance.register(self.config, self.data, self.registration)

    @staticmethod
    def write_json(path, value):
        Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.PIPE, text=True)

    def verify(self):
        return provenance.verify_registration(self.config, self.data, self.registration)

    def rewrite_record(self, edit):
        record = provenance.read(self.registration)
        edit(record)
        self.write_json(self.registration, record)

    def remote_context(self, marker):
        original = Path.exists
        def exists(path):
            return False if path == self.repo / ".git" else original(path)
        return mock.patch.object(Path, "exists", exists), mock.patch.dict(os.environ, {"APT_FROZEN_BUNDLE_SHA256": marker})

    def test_committed_sources_and_data_verify_without_predecessor_weights(self):
        result = self.verify()
        self.assertEqual(result["status"], "FROZEN_NORMAL_STABILITY")
        self.assertFalse(result["predecessor_weights_used"])
        self.assertNotIn("prior_files", result)
        for path in (self.here / "PROTOCOL_REVIEW.md", self.here / "PINNED_BASELINES.json",
                     self.embedding / "engine.py", self.embedding / "scoring.py"):
            self.assertIn(path.relative_to(self.repo).as_posix(), result["code_hashes"])

    def test_configuration_tampering_is_refused(self):
        self.write_json(self.config, {"scope": "DEVELOPMENT_ONLY", "neighbors": 200})
        with self.assertRaisesRegex(ValueError, "Configuration changed"):
            self.verify()

    def test_source_protocol_baseline_and_import_tampering_are_refused(self):
        for path in (self.here / "runner.py", self.here / "PROTOCOL.md", self.here / "PROTOCOL_REVIEW.md",
                     self.here / "PINNED_BASELINES.json", self.native / "pilot.py",
                     self.embedding / "engine.py", self.embedding / "scoring.py"):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b"post-freeze edit")
                try:
                    with self.assertRaisesRegex(ValueError, "Registered source changed"):
                        self.verify()
                finally:
                    path.write_bytes(original)

    def test_receipt_hash_edit_cannot_bypass_committed_bytes(self):
        path = self.here / "runner.py"
        path.write_text("uncommitted source", encoding="utf-8")
        self.rewrite_record(lambda record: record["code_hashes"].update({path.relative_to(self.repo).as_posix(): provenance.digest(path)}))
        with self.assertRaisesRegex(ValueError, "recorded commit"):
            self.verify()

    def test_added_module_or_shell_script_invalidates_inventory(self):
        for suffix in ("py", "sh"):
            path = self.here / ("late_helper." + suffix)
            path.write_text("late source", encoding="utf-8")
            try:
                with self.assertRaisesRegex(ValueError, "source inventory"):
                    self.verify()
            finally:
                path.unlink()

    def test_missing_source_binding_is_refused(self):
        self.rewrite_record(lambda record: record["code_hashes"].pop(next(iter(record["code_hashes"]))))
        with self.assertRaisesRegex(ValueError, "source inventory"):
            self.verify()

    def test_outside_configuration_is_refused(self):
        outside = self.root / "outside.json"
        outside.write_bytes(self.config.read_bytes())
        with self.assertRaisesRegex(ValueError, "escapes the repository"):
            provenance.verify_registration(outside, self.data, self.registration)

    def test_wrong_registration_scope_or_status_is_refused(self):
        for key, value in (("scope", "CONFIRMATION"), ("status", "FROZEN_EMBEDDING_SCORING")):
            self.write_json(self.registration, {**self.record, key: value})
            with self.assertRaisesRegex(ValueError, "normal-stability"):
                self.verify()

    def test_non_digest_commit_reference_is_refused(self):
        self.rewrite_record(lambda record: record.update(git_commit="HEAD"))
        with self.assertRaisesRegex(ValueError, "complete Git commit"):
            self.verify()

    def test_changed_array_is_refused(self):
        self.array.write_bytes(b"changed graph")
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_changed_manifest_is_refused(self):
        self.manifest["post_freeze_edit"] = True
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.verify()

    def test_extra_unregistered_graph_is_refused(self):
        (self.data / "cadets/extra.npz").write_bytes(b"extra graph")
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_escaping_and_aliased_manifest_paths_are_refused(self):
        for relative in ("../outside.npz", "/outside.npz", "C:/outside.npz", "cadets/../train0.npz", "cadets\\train0.npz"):
            self.manifest["datasets"][0]["graphs"][0]["npz"] = relative
            self.write_json(self.data / "MANIFEST.json", self.manifest)
            with self.assertRaisesRegex(ValueError, "escaping graph path"):
                provenance.validate_manifest(self.data)

    def test_duplicate_manifest_graph_is_refused(self):
        self.manifest["datasets"][0]["graphs"].append(self.manifest["datasets"][0]["graphs"][0])
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            provenance.validate_manifest(self.data)

    def test_wrong_adapter_or_unqualified_source_is_refused(self):
        self.manifest["adapter_sha256"] = "0" * 64
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "matching native"):
            provenance.validate_manifest(self.data)
        self.manifest["adapter_sha256"] = provenance.digest(self.native / "data.py")
        self.manifest["datasets"][0]["matches_upstream_git_blob"] = False
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "source provenance"):
            provenance.validate_manifest(self.data)

    def test_edited_registered_data_inventory_is_refused(self):
        self.rewrite_record(lambda record: record["data_files"].update({"cadets/train0.npz": "0" * 64}))
        with self.assertRaisesRegex(ValueError, "Normalized graph bytes"):
            self.verify()

    def test_register_refuses_uncommitted_protocol_before_receipt(self):
        (self.here / "PROTOCOL.md").write_text("uncommitted protocol", encoding="utf-8")
        target = self.root / "NEW.json"
        with self.assertRaisesRegex(ValueError, "Commit exact"):
            provenance.register(self.config, self.data, target)
        self.assertFalse(target.exists())

    def test_register_never_overwrites_existing_receipt(self):
        original = self.registration.read_bytes()
        with self.assertRaises(FileExistsError):
            provenance.register(self.config, self.data, self.registration)
        self.assertEqual(self.registration.read_bytes(), original)

    def test_remote_verification_requires_valid_external_bundle_marker(self):
        for value in ("", "not-a-digest", "a" * 63):
            git_patch, env_patch = self.remote_context(value)
            with git_patch, env_patch:
                with self.assertRaisesRegex(ValueError, "externally hash-verified"):
                    self.verify()

    def test_remote_verified_bundle_can_check_all_registered_bytes(self):
        git_patch, env_patch = self.remote_context("a" * 64)
        with git_patch, env_patch:
            self.assertEqual(self.verify()["status"], "FROZEN_NORMAL_STABILITY")

    def test_remote_marker_does_not_bypass_source_tampering(self):
        (self.here / "runner.py").write_text("tampered remote code", encoding="utf-8")
        git_patch, env_patch = self.remote_context("a" * 64)
        with git_patch, env_patch:
            with self.assertRaisesRegex(ValueError, "Registered source changed"):
                self.verify()

    def test_bundle_contains_only_registered_sources_receipt_and_native_data(self):
        target = self.root / "bundle.tar.gz"
        with mock.patch.object(launch, "REPO", self.repo):
            sha = launch.build_bundle(self.config, self.data, self.registration, target)
        self.assertEqual(sha, provenance.digest(target))
        with tarfile.open(target, "r:gz") as archive:
            names = set(archive.getnames())
        expected = {"repo/" + relative for relative in self.record["code_hashes"]}
        expected.update({"data/" + relative for relative in self.record["data_files"]})
        expected.update({"data/MANIFEST.json", "repo/experiments/apt_final/normal_stability/REGISTRATION.json"})
        self.assertEqual(names, expected)
        self.assertFalse(any(name.startswith("prior/") or name.endswith(".pt") for name in names))
        with mock.patch.object(launch, "REPO", self.repo), self.assertRaises(FileExistsError):
            launch.build_bundle(self.config, self.data, self.registration, target)


class StabilityWorkerAndCollectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def arguments(self):
        return ["--data-dir", str(self.root / "data"), "--output", str(self.root / "outputs"),
                "--registration", str(self.root / "REGISTRATION.json")]

    def test_worker_checks_registration_before_output_or_subprocess(self):
        with mock.patch.object(worker, "verify_registration", side_effect=ValueError("unregistered")), \
                mock.patch.object(worker.subprocess, "run") as execute:
            with self.assertRaisesRegex(ValueError, "unregistered"):
                worker.main(self.arguments())
        self.assertFalse((self.root / "outputs").exists())
        execute.assert_not_called()

    def test_worker_invokes_cuda_runner_once_for_all_datasets(self):
        with mock.patch.object(worker, "verify_registration", return_value={}), \
                mock.patch.object(worker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as execute:
            self.assertEqual(worker.main(self.arguments()), 0)
        execute.assert_called_once()
        command = execute.call_args.args[0]
        self.assertIn("experiments.apt_final.normal_stability.runner", command)
        self.assertEqual(command[-2:], ["--device", "cuda"])
        self.assertNotIn("--dataset", command)
        self.assertNotIn("--prior-dir", command)
        self.assertEqual(provenance.read(self.root / "outputs/WORKER_STATUS.json")["status"], "COMPLETE")

    def test_worker_failure_stays_incomplete_and_attempt_cannot_overwrite(self):
        with mock.patch.object(worker, "verify_registration", return_value={}), \
                mock.patch.object(worker.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as execute:
            self.assertEqual(worker.main(self.arguments()), 7)
            path = self.root / "outputs/WORKER_STATUS.json"
            before = path.read_bytes()
            self.assertEqual(provenance.read(path)["status"], "INCOMPLETE")
            with self.assertRaises(FileExistsError):
                worker.main(self.arguments())
            self.assertEqual(path.read_bytes(), before)
        execute.assert_called_once()

    def prepare_archive(self, names):
        archive = self.root / "result.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            for name in names:
                member = tarfile.TarInfo(name)
                member.size = 1
                stream.addfile(member, io.BytesIO(b"x"))
        (self.root / "result.sha256").write_text(provenance.digest(archive), encoding="ascii")
        controller = mock.Mock()
        controller.settings = {"prefix": "synthetic/"}
        return controller

    def test_collection_refuses_escape_and_resolved_path_collision(self):
        for names in (["../escape"], ["outputs/x", "outputs/sub/../x"]):
            with self.subTest(names=names):
                controller = self.prepare_archive(names)
                with self.assertRaisesRegex(ValueError, "Unsafe or colliding"):
                    launch.collect(controller, self.root)
                (self.root / "collected").rmdir()

    def test_collection_enforces_member_limit(self):
        controller = self.prepare_archive(["outputs/file" + str(index) for index in range(2001)])
        with self.assertRaisesRegex(ValueError, "collection bound"):
            launch.collect(controller, self.root)

    def test_collection_refuses_changed_transport_checksum(self):
        controller = self.prepare_archive(["outputs/a"])
        (self.root / "result.sha256").write_text("0" * 64, encoding="ascii")
        with self.assertRaisesRegex(ValueError, "transport checksum"):
            launch.collect(controller, self.root)
        self.assertFalse((self.root / "collected").exists())


if __name__ == "__main__":
    unittest.main()
