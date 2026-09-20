"""New calibrated freeze/launcher gates; no GPU, AWS, or scientific changes."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.magic_calibrated import launch, provenance
from experiments.apt_final.magic_reproduction.analysis.audit import OPERATIVE
from experiments.apt_final.magic_reproduction.analysis.compact_audit import COMPACT_FILES


class CalibratedProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments/apt_final/magic_calibrated"
        self.original, self.compact = self.here.parent / "magic_reproduction", self.here.parent / "magic_compact"
        self.data, self.source, self.wheels = (self.root / n for n in ("data", "source", "wheels"))
        own = {"experiments/apt_final/magic_calibrated/" + name for name in
               ("PROTOCOL.md", "config.json", "worker.py", "provenance.py", "launch.py", "run_cloud.sh")}
        for relative in OPERATIVE | COMPACT_FILES | own:
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic source: " + relative + "\n", encoding="utf-8")
        for path in (self.data, self.source, self.wheels): path.mkdir()
        self.write(self.original / "REGISTRATION.json", {"synthetic": "original"})
        self.write(self.compact / "REGISTRATION.json", {"synthetic": "compact"})
        self.write(self.here / "config.json", {"seeds": [0, 101, 211], "datasets": ["theia", "cadets"]})
        (self.wheels / "synthetic.whl").write_bytes(b"verified synthetic wheel")
        self.write(self.original / "RUNTIME.json", {"wheel": "synthetic.whl", "wheel_sha256": provenance.digest(self.wheels / "synthetic.whl")})
        self.write(self.data / "MANIFEST.json", {"synthetic": True})
        (self.source / "author.py").write_text("pass\n", encoding="utf-8")
        self.write(self.source / "SOURCE_MANIFEST.json", {"synthetic": True})
        self.prior = {"source_commit": "1" * 40, "upstream_commit": "3" * 40,
                      "code_hashes": {r: provenance.digest(self.repo / r) for r in OPERATIVE},
                      "data_files": {"MANIFEST.json": provenance.digest(self.data / "MANIFEST.json")},
                      "upstream_files": {"author.py": provenance.digest(self.source / "author.py")},
                      "source_manifest_sha256": provenance.digest(self.source / "SOURCE_MANIFEST.json")}
        self.amendment = {"source_commit": "2" * 40, "code_hashes": {r: provenance.digest(self.repo / r) for r in COMPACT_FILES}}
        for module, name, value in ((provenance, "HERE", self.here), (provenance, "REPO", self.repo),
                                  (provenance, "ORIGINAL", self.original), (provenance, "COMPACT", self.compact),
                                  (launch, "HERE", self.here), (launch, "REPO", self.repo), (launch, "ORIGINAL", self.original)):
            patch = mock.patch.object(module, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(provenance.compact, "verify", return_value=(self.amendment, self.prior))
        self.parent_verification = patch.start()
        self.addCleanup(patch.stop)
        for args in (("init", "-q"), ("config", "core.autocrlf", "false"), ("config", "user.name", "Synthetic qualification"),
                     ("config", "user.email", "test@example.invalid"), ("add", "."), ("commit", "-qm", "Synthetic source")):
            subprocess.run(["git", *args], cwd=self.repo, capture_output=True, check=True)
        self.registration = self.root / "REGISTRATION.json"
        self.record = provenance.register(self.data, self.source, self.registration)

    @staticmethod
    def write(path, value):
        Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def verify(self):
        return provenance.verify_runtime(self.registration, self.data, self.source)

    def test_exact_twenty_three_sources_and_two_parent_registrations_in_bundle(self):
        record = self.verify()
        self.assertEqual(len(record["code_hashes"]), 23)
        self.assertEqual(len(record["parent_registrations"]), 2)
        self.assertFalse(record["confirmation_claimed"])
        destination = self.root / "bundle.tar.gz"
        sha = launch.build_bundle(self.data, self.source, self.wheels, self.registration, destination)
        self.assertEqual(sha, provenance.digest(destination))
        with tarfile.open(destination) as archive:
            names = set(archive.getnames())
            self.assertEqual(len(names), len(archive.getmembers()))
        self.assertTrue({"repo/" + r for r in record["code_hashes"] | record["parent_registrations"]}.issubset(names))
        self.assertIn("repo/experiments/apt_final/magic_calibrated/REGISTRATION.json", names)
        self.assertIn("upstream/author.py", names)

    def test_deleted_source_data_parent_and_upstream_entries_are_rejected(self):
        for field in ("code_hashes", "data_files", "parent_registrations", "upstream_files"):
            with self.subTest(field=field):
                record = json.loads(json.dumps(self.record))
                record[field].pop(next(iter(record[field])))
                self.write(self.registration, record)
                with self.assertRaisesRegex(ValueError, "chain or scope changed"):
                    self.verify()

    def test_parent_identities_and_exposed_data_scope_cannot_change(self):
        for field, value in (("original_source_commit", "0" * 40), ("compact_source_commit", "0" * 40),
                             ("upstream_commit", "0" * 40), ("test_previously_exposed", False),
                             ("confirmation_claimed", True), ("novelty_claimed", True)):
            with self.subTest(field=field):
                self.write(self.registration, {**self.record, field: value})
                with self.assertRaisesRegex(ValueError, "chain or scope changed"):
                    self.verify()

    def test_parent_verification_failure_propagates_and_parent_receipt_change_is_rejected(self):
        self.parent_verification.side_effect = ValueError("parent frozen source changed")
        with self.assertRaisesRegex(ValueError, "parent frozen source changed"):
            self.verify()
        self.parent_verification.side_effect = None
        self.write(self.compact / "REGISTRATION.json", {"synthetic": "changed"})
        with self.assertRaisesRegex(ValueError, "chain or scope changed"):
            self.verify()

    def test_config_edit_requires_new_committed_registration(self):
        (self.here / "config.json").write_text("changed partitions", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "chain or scope changed"):
            self.verify()
        new = self.root / "new.json"
        with self.assertRaisesRegex(ValueError, "Commit exact calibrated"):
            provenance.register(self.data, self.source, new)
        self.assertFalse(new.exists())

    def test_failed_final_verification_does_not_leave_registration(self):
        new = self.root / "failed.json"
        with mock.patch.object(provenance, "verify_runtime", side_effect=ValueError("injected final validation")):
            with self.assertRaisesRegex(ValueError, "injected"):
                provenance.register(self.data, self.source, new)
        self.assertFalse(new.exists())
        self.assertFalse(new.with_suffix(".tmp").exists())


class CalibratedLauncherTests(unittest.TestCase):
    def test_collection_requires_registration_bundle_and_both_datasets(self):
        execution = {"registration_sha256": "a" * 64, "bundle_sha256": "b" * 64, "datasets": ["theia", "cadets"]}
        for change in (None, "registration_sha256", "bundle_sha256", "selected_datasets"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                private = root / "private"
                private.mkdir()
                (private / "EXECUTION.json").write_text(json.dumps(execution), encoding="utf-8")
                result = {"status": "INCOMPLETE_CALIBRATION_OR_EVALUATION", "selected_datasets": ["theia", "cadets"],
                          "bindings": {"registration_sha256": "a" * 64, "bundle_sha256": "b" * 64}}
                if change == "selected_datasets": result[change] = ["theia"]
                elif change: result["bindings"][change] = "0" * 64
                archive = root / "result.tar.gz"
                with tarfile.open(archive, "w:gz") as pack:
                    payload = json.dumps(result).encode()
                    member = tarfile.TarInfo("outputs/RESULTS.json")
                    member.size = len(payload)
                    pack.addfile(member, io.BytesIO(payload))
                marker = root / "result.sha256"
                marker.write_text(provenance.digest(archive), encoding="ascii")
                controller = mock.Mock(settings={"prefix": "synthetic/"})
                controller.transfer.side_effect = lambda _, destination, key: shutil.copyfile(
                    marker if key.endswith(".sha256") else archive, destination)
                if change is None:
                    self.assertEqual(launch.collect(controller, private)["worker"], result)
                else:
                    with self.assertRaisesRegex(ValueError, "binding mismatch"):
                        launch.collect(controller, private)

    def test_dataset_selector_cannot_drop_a_registered_dataset(self):
        argv = ["launcher", "--settings", "settings", "--data-dir", "data", "--registration", "registration",
                "--source-dir", "source", "--wheel-dir", "wheel", "--datasets", "theia"]
        with mock.patch("sys.argv", argv), mock.patch("sys.stderr", new_callable=io.StringIO), \
             mock.patch.object(launch, "Controller") as controller:
            with self.assertRaises(SystemExit) as error:
                launch.main()
            self.assertEqual(error.exception.code, 2)
            controller.assert_not_called()

    def test_bootstrap_syntax_and_storage_guards_match_qualified_parent(self):
        root = Path(__file__).resolve().parents[1] / "experiments/apt_final"
        old = (root / "magic_compact/run_cloud.sh").read_text(encoding="utf-8")
        new = (root / "magic_calibrated/run_cloud.sh").read_text(encoding="utf-8")
        def guards(value):
            return value.split("# BEGIN_STABLE_STORAGE_GUARDS", 1)[1].split("# END_STABLE_STORAGE_GUARDS", 1)[0]
        self.assertEqual(guards(old), guards(new))
        self.assertIn('[[ "$datasets" == "theia,cadets" ]]', new)
        bash = Path("C:/Program Files/Git/bin/bash.exe")
        command = str(bash) if bash.exists() else shutil.which("bash")
        if command is None: self.skipTest("No Bash for syntax qualification")
        subprocess.run([command, "-n", str(root / "magic_calibrated/run_cloud.sh")], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
