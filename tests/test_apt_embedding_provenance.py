"""Exercise real Git binding and tamper refusals in isolated synthetic fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.embedding_baseline import provenance


class EmbeddingProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments" / "apt_final" / "embedding_baseline"
        self.native = self.here.parent / "native_graph"
        self.here.mkdir(parents=True)
        self.native.mkdir()
        self.data = self.root / "data"
        self.data.mkdir()
        self.prior = self.root / "prior"
        (self.prior / "cadets" / "private").mkdir(parents=True)
        self.config = self.here / "config.json"
        self.registration = self.root / "REGISTRATION.json"
        self.write_json(self.config, {"scope": "DEVELOPMENT_ONLY", "neighbors": 10})
        for name in ("PROTOCOL.md", "LITERATURE_AND_DESIGN.md", "provenance.py", "runner.py", "run_cloud.sh"):
            (self.here / name).write_text("synthetic fixture: " + name + "\n", encoding="utf-8")
        for name in ("data.py", "pilot.py", "provenance.py", "cloud_control.py"):
            (self.native / name).write_text("synthetic native fixture: " + name + "\n", encoding="utf-8")
        self.prior_files = {
            "cadets/private/mlp_101.pt": b"synthetic checkpoint bytes; never deserialized",
            "cadets/private/predictions_101_clean.npz": b"synthetic prior prediction bytes",
            "cadets/private/calibration_101.npz": b"synthetic calibration bytes",
        }
        for rel, data in self.prior_files.items():
            (self.prior / rel).write_bytes(data)
        self.write_json(self.here / "PREDECESSOR.json", {
            "files": {rel: hashlib.sha256(data).hexdigest() for rel, data in self.prior_files.items()}})
        # The registration guard verifies bytes and provenance, not NPZ parsing.
        self.array_path = self.data / "cadets" / "train0.npz"
        self.array_path.parent.mkdir()
        self.array_path.write_bytes(b"synthetic normalized array fixture")
        self.manifest = {
            "schema": "apt-final-native-graph-data-v1", "status": "STATIC_DEVELOPMENT_ONLY",
            "adapter_sha256": provenance.digest(self.native / "data.py"),
            "datasets": [{"dataset": "cadets", "status": "STATIC_DEVELOPMENT_ONLY",
                          "matches_upstream_git_blob": True,
                          "graphs": [{"npz": "cadets/train0.npz",
                                      "npz_sha256": provenance.digest(self.array_path)}]}],
        }
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        for name, value in (("HERE", self.here), ("NATIVE", self.native), ("REPO", self.repo)):
            patcher = mock.patch.object(provenance, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "user.email", "synthetic-fixture@example.invalid")
        self.git("config", "user.name", "Synthetic provenance fixture")
        self.git("add", "experiments")
        self.git("commit", "-q", "-m", "Synthetic committed source")
        self.record = provenance.register(self.config, self.data, self.registration, self.prior)

    @staticmethod
    def write_json(path, obj):
        Path(path).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.PIPE, text=True)

    def verify(self):
        return provenance.verify_registration(self.config, self.data, self.registration, self.prior)

    def rewrite_record(self, edit):
        record = provenance.read(self.registration)
        edit(record)
        self.write_json(self.registration, record)

    def test_exact_committed_sources_and_bound_prior_artifacts_verify(self):
        result = self.verify()
        self.assertEqual(result["status"], "FROZEN_EMBEDDING_SCORING")
        self.assertEqual(result["prior_files"], provenance.prior_inventory(self.prior))
        self.assertTrue(result["test_outcomes_previously_inspected"])

    def test_configuration_tampering_is_refused(self):
        self.write_json(self.config, {"scope": "DEVELOPMENT_ONLY", "neighbors": 200})
        with self.assertRaisesRegex(ValueError, "Configuration changed"):
            self.verify()

    def test_source_tampering_is_refused(self):
        with (self.here / "runner.py").open("a", encoding="utf-8") as stream:
            stream.write("changed after freeze\n")
        with self.assertRaisesRegex(ValueError, "Registered source changed"):
            self.verify()

    def test_hand_editing_hash_cannot_bypass_committed_source_binding(self):
        path = self.here / "runner.py"
        path.write_text("uncommitted changed source\n", encoding="utf-8")
        rel = path.relative_to(self.repo).as_posix()
        self.rewrite_record(lambda record: record["code_hashes"].update({rel: provenance.digest(path)}))
        with self.assertRaisesRegex(ValueError, "recorded commit"):
            self.verify()

    def test_new_runtime_module_invalidates_source_inventory(self):
        (self.here / "late_helper.py").write_text("late code\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source inventory"):
            self.verify()

    def test_missing_source_binding_is_refused(self):
        self.rewrite_record(lambda record: record["code_hashes"].pop(next(iter(record["code_hashes"]))))
        with self.assertRaisesRegex(ValueError, "source inventory"):
            self.verify()

    def test_changed_checkpoint_is_refused(self):
        (self.prior / "cadets/private/mlp_101.pt").write_bytes(b"replacement checkpoint")
        with self.assertRaisesRegex(ValueError, "Predecessor artifact changed"):
            self.verify()

    def test_changed_prior_predictions_are_refused(self):
        (self.prior / "cadets/private/predictions_101_clean.npz").write_bytes(b"relabelled predictions")
        with self.assertRaisesRegex(ValueError, "Predecessor artifact changed"):
            self.verify()

    def test_changed_prior_calibration_is_refused(self):
        (self.prior / "cadets/private/calibration_101.npz").write_bytes(b"threshold retune")
        with self.assertRaisesRegex(ValueError, "Predecessor artifact changed"):
            self.verify()

    def test_hand_editing_prior_receipt_cannot_replace_predecessor_binding(self):
        self.rewrite_record(lambda record: record["prior_files"].update({"cadets/private/mlp_101.pt": "0" * 64}))
        with self.assertRaisesRegex(ValueError, "Predecessor inventory changed"):
            self.verify()

    def test_changed_array_bytes_are_refused(self):
        self.array_path.write_bytes(b"changed normalized graph")
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_changed_manifest_is_refused(self):
        self.manifest["post_freeze_edit"] = True
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            self.verify()

    def test_extra_unregistered_array_is_refused(self):
        (self.data / "cadets" / "extra.npz").write_bytes(b"unregistered array")
        with self.assertRaisesRegex(ValueError, "audited graph inventory"):
            self.verify()

    def test_escaping_graph_manifest_path_is_refused(self):
        outside = self.root / "outside.npz"
        outside.write_bytes(b"outside graph bytes")
        self.manifest["datasets"][0]["graphs"][0] = {
            "npz": "../outside.npz", "npz_sha256": provenance.digest(outside)}
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "escaping graph path"):
            provenance.validate_manifest(self.data)

    def test_duplicate_graph_manifest_path_is_refused(self):
        self.manifest["datasets"][0]["graphs"].append(self.manifest["datasets"][0]["graphs"][0])
        self.write_json(self.data / "MANIFEST.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            provenance.validate_manifest(self.data)

    def test_escaping_predecessor_path_is_refused_before_reading(self):
        outside = self.root / "outside-checkpoint.pt"
        outside.write_bytes(b"outside checkpoint")
        self.write_json(self.here / "PREDECESSOR.json", {"files": {"../outside-checkpoint.pt": provenance.digest(outside)}})
        with self.assertRaisesRegex(ValueError, "Predecessor artifact changed"):
            provenance.prior_inventory(self.prior)

    def test_register_refuses_uncommitted_protocol(self):
        (self.here / "PROTOCOL.md").write_text("changed operating point\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Commit exact"):
            provenance.register(self.config, self.data, self.root / "NEW.json", self.prior)
        self.assertFalse((self.root / "NEW.json").exists())

    def test_register_does_not_overwrite_existing_receipt(self):
        before = self.registration.read_bytes()
        with self.assertRaises(FileExistsError):
            provenance.register(self.config, self.data, self.registration, self.prior)
        self.assertEqual(self.registration.read_bytes(), before)

    def test_remote_verification_requires_external_bundle_marker(self):
        original_exists = Path.exists

        def without_git(path):
            return False if path == self.repo / ".git" else original_exists(path)

        with mock.patch.object(Path, "exists", without_git), mock.patch.dict(os.environ, {"APT_FROZEN_BUNDLE_SHA256": ""}):
            with self.assertRaisesRegex(ValueError, "externally hash-verified bundle marker"):
                self.verify()

    def test_remote_marker_does_not_bypass_changed_code(self):
        original_exists = Path.exists

        def without_git(path):
            return False if path == self.repo / ".git" else original_exists(path)

        (self.here / "runner.py").write_text("remote code tamper\n", encoding="utf-8")
        with mock.patch.object(Path, "exists", without_git), mock.patch.dict(os.environ, {"APT_FROZEN_BUNDLE_SHA256": "a" * 64}):
            with self.assertRaisesRegex(ValueError, "Registered source changed"):
                self.verify()


if __name__ == "__main__":
    unittest.main()
