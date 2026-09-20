"""Independent prelaunch tests using real Git freezes and tiny transport archives.

No AWS, author pickle/checkpoint execution, or model dependencies are needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.magic_reproduction import launch, provenance


class MagicProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments/apt_final/magic_reproduction"
        self.native = self.here.parent / "native_graph"
        self.data = self.root / "data"
        self.upstream_git = self.root / "upstream_git"
        self.source = self.root / "upstream"
        self.wheels = self.root / "wheels"
        for directory in (self.here, self.native, self.data / "theia",
                          self.upstream_git / "model", self.source, self.wheels):
            directory.mkdir(parents=True)
        self.registration = self.root / "REGISTRATION.json"
        for name in ("provenance.py", "model_adapter.py", "qualification.py", "worker.py",
                     "launch.py", "run_cloud.sh", "PROTOCOL.md"):
            (self.here / name).write_text("synthetic operative bytes: " + name + "\n", encoding="utf-8")
        for name in ("cloud_control.py", "data.py"):
            (self.native / name).write_text("synthetic dependency: " + name + "\n", encoding="utf-8")
        self.write_json(self.here / "config.json", {"epochs": 50, "seed": 0})
        wheel = self.wheels / "synthetic.whl"
        wheel.write_bytes(b"opaque wheel identity; never imported")
        self.write_json(self.here / "RUNTIME.json", {
            "wheel": wheel.name, "wheel_sha256": provenance.digest(wheel)})
        array = self.data / "theia/train0.npz"
        array.write_bytes(b"opaque normalized data; semantics tested separately")
        self.write_json(self.data / "MANIFEST.json", {"datasets": [{"dataset": "theia", "graphs": [
            {"npz": "theia/train0.npz", "npz_sha256": provenance.digest(array)}]}]})
        (self.upstream_git / "model/autoencoder.py").write_text("AUTHOR_SOURCE = True\n", encoding="utf-8")
        (self.upstream_git / "README.md").write_text("Synthetic author record\n", encoding="utf-8")
        (self.upstream_git / "requirements.txt").write_text("synthetic-runtime==1\n", encoding="utf-8")
        # Excluded author checkpoints must not enter the runnable source package.
        (self.upstream_git / "checkpoint.pt").write_bytes(b"excluded")
        self.init_git(self.repo)
        self.init_git(self.upstream_git)
        upstream_commit = self.git(self.upstream_git, "rev-parse", "HEAD").strip()
        upstream_inventory = {}
        for rel in ("model/autoencoder.py", "README.md", "requirements.txt"):
            target = self.source / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(
                ["git", "show", upstream_commit + ":" + rel], cwd=self.upstream_git))
            upstream_inventory[rel] = provenance.digest(target)
        self.write_json(self.source / "SOURCE_MANIFEST.json", {
            "commit": upstream_commit, "files": upstream_inventory})
        for module, name, value in (
            (provenance, "HERE", self.here), (provenance, "REPO", self.repo),
            (provenance, "UPSTREAM", upstream_commit),
            (provenance, "DATA_MANIFEST", provenance.digest(self.data / "MANIFEST.json")),
            (launch, "HERE", self.here), (launch, "REPO", self.repo),
        ):
            patcher = mock.patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.record = provenance.register(self.data, self.source, self.registration, self.upstream_git)

    @staticmethod
    def write_json(path, value):
        Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def git(repo, *arguments):
        return subprocess.check_output(["git", *arguments], cwd=repo, text=True, stderr=subprocess.PIPE)

    def init_git(self, repo):
        for command in (("init", "-q"), ("config", "core.autocrlf", "false"),
                        ("config", "user.email", "synthetic@example.invalid"),
                        ("config", "user.name", "Synthetic qualification"),
                        ("add", "."), ("commit", "-q", "-m", "Synthetic exact source")):
            self.git(repo, *command)

    def verify(self):
        return provenance.verify_runtime(self.registration, self.data, self.source)

    def rewrite_registration(self, change):
        record = provenance.read(self.registration)
        change(record)
        self.write_json(self.registration, record)

    def test_real_git_freeze_and_complete_bundle_inventory(self):
        verified = self.verify()
        self.assertEqual(verified["code_hashes"], provenance.source_files())
        self.assertEqual(set(verified["data_files"]), {"MANIFEST.json", "theia/train0.npz"})
        self.assertFalse(verified["confirmation_claimed"])
        self.assertTrue(verified["test_previously_exposed"])
        destination = self.root / "bundle.tar.gz"
        sha = launch.build_bundle(self.data, self.source, self.wheels, self.registration, destination)
        self.assertEqual(sha, provenance.digest(destination))
        expected = {"repo/" + rel for rel in verified["code_hashes"]}
        expected |= {"data/" + rel for rel in verified["data_files"]}
        expected |= {"upstream/" + rel for rel in verified["upstream_files"]}
        expected |= {"upstream/SOURCE_MANIFEST.json", "wheels/synthetic.whl",
                     "repo/experiments/apt_final/magic_reproduction/REGISTRATION.json"}
        with tarfile.open(destination) as archive:
            self.assertEqual(set(archive.getnames()), expected)
            self.assertTrue(all(member.isfile() for member in archive.getmembers()))
            self.assertFalse(any("checkpoint" in name for name in archive.getnames()))

    def test_omitting_one_source_or_data_entry_is_rejected(self):
        for key in ("code_hashes", "data_files"):
            with self.subTest(inventory=key):
                self.write_json(self.registration, self.record)
                self.rewrite_registration(lambda record: record[key].pop(next(iter(record[key]))))
                with self.assertRaisesRegex(ValueError, "inventory"):
                    self.verify()

    def test_mutating_each_operative_source_is_rejected(self):
        for rel in self.record["code_hashes"]:
            with self.subTest(source=rel):
                path = self.repo / rel
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                try:
                    with self.assertRaisesRegex(ValueError, "Frozen source changed"):
                        self.verify()
                finally:
                    path.write_bytes(original)

    def test_tampered_data_rejected_even_if_registration_hash_is_rewritten(self):
        array = self.data / "theia/train0.npz"
        array.write_bytes(b"different prepared rows")
        with self.assertRaisesRegex(ValueError, "Prepared bytes changed"):
            self.verify()
        self.rewrite_registration(lambda record: record["data_files"].update({
            "theia/train0.npz": provenance.digest(array)}))
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.verify()

    def test_modified_or_extra_upstream_python_is_rejected(self):
        path = self.source / "model/autoencoder.py"
        original = path.read_bytes()
        path.write_bytes(b"different architecture")
        with self.assertRaisesRegex(ValueError, "Upstream source changed"):
            self.verify()
        path.write_bytes(original)
        (self.source / "model/unregistered.py").write_text("pass\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unexpected upstream Python"):
            self.verify()

    def test_register_rejects_forged_upstream_manifest_claiming_correct_commit(self):
        target = self.source / "model/autoencoder.py"
        target.write_bytes(b"modified author implementation")
        manifest = provenance.read(self.source / "SOURCE_MANIFEST.json")
        manifest["files"]["model/autoencoder.py"] = provenance.digest(target)
        self.write_json(self.source / "SOURCE_MANIFEST.json", manifest)
        attempt = self.root / "FORGED_REGISTRATION.json"
        with self.assertRaisesRegex(ValueError, "pinned Git blobs"):
            provenance.register(self.data, self.source, attempt, self.upstream_git)
        self.assertFalse(attempt.exists())

    def test_register_rejects_uncommitted_source_and_leaves_no_receipt(self):
        (self.here / "config.json").write_text("changed\n", encoding="utf-8")
        attempt = self.root / "UNCOMMITTED.json"
        with self.assertRaisesRegex(ValueError, "Commit exact source"):
            provenance.register(self.data, self.source, attempt, self.upstream_git)
        self.assertFalse(attempt.exists())

    def test_failed_final_validation_leaves_no_registration_or_temporary_file(self):
        (self.data / "theia/train0.npz").write_bytes(b"changed after data manifest freeze")
        attempt = self.root / "FAILED.json"
        with self.assertRaisesRegex(ValueError, "Prepared bytes changed"):
            provenance.register(self.data, self.source, attempt, self.upstream_git)
        self.assertFalse(attempt.exists())
        self.assertFalse(attempt.with_suffix(".tmp").exists())

    def test_wrong_wheel_refused_before_bundle_creation(self):
        (self.wheels / "synthetic.whl").write_bytes(b"wrong wheel")
        destination = self.root / "bundle.tar.gz"
        with self.assertRaisesRegex(ValueError, "wheel hash"):
            launch.build_bundle(self.data, self.source, self.wheels, self.registration, destination)
        self.assertFalse(destination.exists())


class MagicCollectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.private = self.root / "private"
        self.private.mkdir()
        self.archive = self.root / "transport.tar.gz"
        self.marker = self.root / "transport.sha256"

    def make_archive(self, members):
        with tarfile.open(self.archive, "w:gz") as archive:
            for name, kind, payload in members:
                info = tarfile.TarInfo(name)
                if kind == "file":
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
                else:
                    info.type = tarfile.SYMTYPE
                    info.linkname = payload
                    archive.addfile(info)
        self.marker.write_text(provenance.digest(self.archive) + "\n", encoding="ascii")

    def controller(self):
        controller = mock.Mock()
        controller.settings = {"prefix": "synthetic/"}
        def transfer(direction, destination, key):
            self.assertEqual(direction, "download")
            source = self.marker if key.endswith(".sha256") else self.archive
            shutil.copyfile(source, destination)
        controller.transfer.side_effect = transfer
        return controller

    def test_verified_transport_collects_expected_worker_status(self):
        payload = b'{"status":"COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION","all_selected_evaluations_complete":false}'
        self.make_archive([("outputs/RESULTS.json", "file", payload)])
        result = launch.collect(self.controller(), self.private)
        self.assertEqual(result["transport_sha256"], provenance.digest(self.archive))
        self.assertEqual(result["worker"]["status"], "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION")
        self.assertFalse(result["worker"]["all_selected_evaluations_complete"])

    def test_legacy_worker_status_without_results_is_not_scientific_completion(self):
        self.make_archive([("outputs/WORKER_STATUS.json", "file",
                            b'{"status":"COMPLETE","scientific_completion":true}')])
        self.assertIsNone(launch.collect(self.controller(), self.private)["worker"])

    def test_transport_checksum_mismatch_stops_before_extract(self):
        self.make_archive([("outputs/valid.json", "file", b"{}")])
        self.marker.write_text("0" * 64, encoding="ascii")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            launch.collect(self.controller(), self.private)
        self.assertFalse((self.private / "collected").exists())

    def test_unsafe_archive_paths_and_links_are_refused(self):
        cases = [
            [("../outside", "file", b"x")],
            [("outputs/../inside_alias", "file", b"x")],
            [(str((self.private / "collected/absolute").resolve()).replace("\\", "/"), "file", b"x")],
            [("outputs\\alias", "file", b"x")],
            [("outputs/link", "link", "../outside")],
            [("outputs/a", "file", b"1"), ("outputs/a", "file", b"2")],
        ]
        for members in cases:
            with self.subTest(names=[member[0] for member in members]):
                shutil.rmtree(self.private / "collected", ignore_errors=True)
                self.make_archive(members)
                with self.assertRaises(ValueError):
                    launch.collect(self.controller(), self.private)

    def test_archive_member_limit_refused_before_extraction(self):
        self.make_archive([(f"outputs/{i}", "file", b"") for i in range(2001)])
        with self.assertRaisesRegex(ValueError, "bound"):
            launch.collect(self.controller(), self.private)
        self.assertFalse((self.private / "collected/outputs/0").exists())


class MagicLauncherClosureTests(unittest.TestCase):
    """Exercise actual orchestration with a fake controller and zero cloud calls."""

    def run_launch(self, result, final_status="CLOSED_VERIFIED_STOPPED"):
        with tempfile.TemporaryDirectory() as temporary:
            private = Path(temporary)
            here, native = private / "operative", private / "native"
            here.mkdir()
            native.mkdir()
            (here / "run_cloud.sh").write_text("echo synthetic-worker\n", encoding="utf-8")
            (native / "cloud_control.py").write_text("synthetic-control\n", encoding="utf-8")
            controller = mock.Mock()
            controller.settings = {"prefix": "synthetic/", "bucket": "synthetic", "instance": "synthetic"}
            controller.active_path = private / "ACTIVE_RUN.json"
            def start(*_):
                controller.active_path.write_text("{}", encoding="utf-8")
                return {"status": "START_REQUESTED"}
            controller.start.side_effect = start
            controller.instance.return_value = {"State": {"Name": "running"}}
            controller.client.return_value.describe_instance_information.return_value = {
                "InstanceInformationList": [{"PingStatus": "Online"}]}
            controller.active.return_value = {
                "worker_deadline_utc": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "run_id": "synthetic-run-id"}
            controller.send.return_value = {"command_id": "synthetic-command"}
            controller.poll.return_value = {"status": "Success"}
            controller.stop.return_value = {"status": "STOP_REQUESTED"}
            controller.finalize.return_value = {"status": final_status}
            def build(*args):
                Path(args[-1]).write_bytes(b"synthetic bundle")
                return "0" * 64
            argv = ["launcher", "--settings", str(private / "settings.json"),
                    "--data-dir", str(private), "--registration", str(private / "REGISTRATION.json"),
                    "--source-dir", str(private), "--wheel-dir", str(private), "--datasets", "theia"]
            with mock.patch.object(launch, "Controller", return_value=controller), \
                 mock.patch.object(launch, "HERE", here), mock.patch.object(launch, "NATIVE", native), \
                 mock.patch.object(launch, "build_bundle", side_effect=build), \
                 mock.patch.object(launch, "collect", return_value={"worker": result}), \
                 mock.patch.object(launch.time, "sleep"), mock.patch("sys.argv", argv), \
                 mock.patch("sys.stdout", new_callable=io.StringIO):
                code = launch.main()
            controller.stop.assert_called_once()
            return code, provenance.read(private / "EXECUTION.json")

    def test_scientific_completion_and_resource_hold_close_differently(self):
        cases = [
            ({"status": "COMPLETE_SELECTED_REPRODUCTIONS", "all_selected_evaluations_complete": True,
              "all_registered_evaluations_complete_in_this_attempt": False}, "COMPLETED_AND_STOPPED", True),
            ({"status": "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION", "all_selected_evaluations_complete": False,
              "all_registered_evaluations_complete_in_this_attempt": False}, "FEASIBILITY_COMPLETE_AND_STOPPED", False),
        ]
        for result, expected, complete in cases:
            with self.subTest(status=result["status"]):
                code, record = self.run_launch(result)
                self.assertEqual(code, 0)
                self.assertEqual(record["status"], expected)
                self.assertEqual(record["scientific_completion"], complete)
                self.assertFalse(record["all_registered_evaluations_complete_in_this_attempt"])

    def test_stop_request_without_verified_stopped_observation_cannot_close(self):
        code, record = self.run_launch({"status": "COMPLETE_SELECTED_REPRODUCTIONS",
                                      "all_selected_evaluations_complete": True}, "STOP_REQUESTED")
        self.assertEqual(code, 1)
        self.assertTrue(record["shutdown_unresolved"])
        self.assertNotEqual(record["status"], "COMPLETED_AND_STOPPED")

    def test_failed_worker_cannot_become_successful_closeout(self):
        code, record = self.run_launch({"status": "FAILED_RUNTIME", "all_selected_evaluations_complete": False})
        self.assertEqual(code, 1)
        self.assertFalse(record["scientific_completion"])
        self.assertNotIn(record["status"], {"COMPLETED_AND_STOPPED", "FEASIBILITY_COMPLETE_AND_STOPPED"})


if __name__ == "__main__":
    unittest.main()
