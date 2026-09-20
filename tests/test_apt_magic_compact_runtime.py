"""Compact amendment freeze, wrapper restoration, and transport receipt gates."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.magic_compact import launch, provenance, worker


class CompactRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.here = self.repo / "experiments/apt_final/magic_compact"
        self.original = self.here.parent / "magic_reproduction"
        self.data, self.source, self.wheels = (self.root / n for n in ("data", "source", "wheels"))
        for directory in (self.here, self.original, self.data, self.source, self.wheels):
            directory.mkdir(parents=True)
        for name in ("PROTOCOL.md", "scoring.py", "worker.py", "provenance.py", "launch.py", "run_cloud.sh"):
            (self.here / name).write_text("synthetic compact bytes: " + name + "\n", encoding="utf-8")
        self.write_json(self.original / "REGISTRATION.json", {"source_commit": "1" * 40})
        self.write_json(self.original / "config.json", {"epochs": 50})
        (self.wheels / "synthetic.whl").write_bytes(b"synthetic wheel")
        self.write_json(self.original / "RUNTIME.json", {"wheel": "synthetic.whl",
            "wheel_sha256": provenance.digest(self.wheels / "synthetic.whl")})
        self.write_json(self.data / "MANIFEST.json", {"synthetic": True})
        self.write_json(self.source / "SOURCE_MANIFEST.json", {"synthetic": True})
        self.prior = {"source_commit": "1" * 40,
                      "code_hashes": {"experiments/apt_final/magic_reproduction/config.json": provenance.digest(self.original / "config.json")},
                      "data_files": {"MANIFEST.json": provenance.digest(self.data / "MANIFEST.json")}, "upstream_files": {}}
        for module, name, value in ((provenance, "HERE", self.here), (provenance, "REPO", self.repo),
                                  (provenance, "ORIGINAL", self.original), (launch, "HERE", self.here),
                                  (launch, "REPO", self.repo), (launch, "ORIGINAL", self.original),
                                  (worker, "ORIGINAL", self.original)):
            patch = mock.patch.object(module, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(provenance.original, "verify_runtime", return_value=self.prior)
        patch.start()
        self.addCleanup(patch.stop)
        for args in (("init", "-q"), ("config", "core.autocrlf", "false"),
                     ("config", "user.name", "Synthetic test"), ("config", "user.email", "test@example.invalid"),
                     ("add", "."), ("commit", "-qm", "Exact source bytes")):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        self.registration = self.root / "COMPACT_REGISTRATION.json"
        self.record = provenance.register(self.data, self.source, self.registration)

    @staticmethod
    def write_json(path, value):
        Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def verify(self):
        return provenance.verify(self.registration, self.data, self.source)

    def test_committed_amendment_and_both_registrations_are_bundled(self):
        record, prior = self.verify()
        self.assertEqual(record["code_hashes"], provenance.files())
        self.assertFalse(record["science_changed"])
        archive = self.root / "bundle.tar.gz"
        launch.build_bundle(self.data, self.source, self.wheels, self.registration, archive)
        with tarfile.open(archive) as pack:
            names = set(pack.getnames())
        self.assertIn("repo/experiments/apt_final/magic_compact/REGISTRATION.json", names)
        self.assertIn("repo/experiments/apt_final/magic_reproduction/REGISTRATION.json", names)
        self.assertTrue({"repo/" + r for r in record["code_hashes"]}.issubset(names))
        self.assertTrue({"repo/" + r for r in prior["code_hashes"]}.issubset(names))

    def test_missing_hash_changed_source_or_original_registration_are_refused(self):
        record = json.loads(json.dumps(self.record))
        record["code_hashes"].pop(next(iter(record["code_hashes"])))
        self.write_json(self.registration, record)
        with self.assertRaisesRegex(ValueError, "freeze changed"):
            self.verify()
        self.write_json(self.registration, self.record)
        path = self.here / "scoring.py"
        before = path.read_bytes()
        path.write_bytes(before + b"changed")
        with self.assertRaisesRegex(ValueError, "freeze changed"):
            self.verify()
        path.write_bytes(before)
        self.write_json(self.original / "REGISTRATION.json", {"source_commit": "2" * 40})
        with self.assertRaisesRegex(ValueError, "Original registration changed"):
            self.verify()

    def test_scientific_changes_reuse_and_invalid_source_commit_are_refused(self):
        for key, changed in (("science_changed", True), ("exact_duplicate_storage_only", False),
                             ("checkpoint_reuse", True), ("novelty_claimed", True), ("source_commit", "not-a-commit")):
            with self.subTest(field=key):
                self.write_json(self.registration, {**self.record, key: changed})
                with self.assertRaisesRegex(ValueError, "scope or source identity"):
                    self.verify()

    def test_registration_cannot_freeze_uncommitted_new_scoring(self):
        (self.here / "scoring.py").write_text("changed scorer", encoding="utf-8")
        target = self.root / "new.json"
        with self.assertRaisesRegex(ValueError, "Commit exact runtime"):
            provenance.register(self.data, self.source, target)
        self.assertFalse(target.exists())

    def argv(self, output):
        return ["--data-dir", str(self.data), "--source-dir", str(self.source), "--output", str(output),
                "--registration", str(self.registration), "--deadline-epoch", "9999999999", "--datasets", "theia"]

    def test_wrapper_substitutes_both_paths_preserves_original_args_and_restores(self):
        output = self.root / "outputs"
        output.mkdir()
        (output / "ENV_SELECTION.log").write_text("fresh startup", encoding="utf-8")
        old_worker, old_qualification = worker.original_worker.ExactFullReferenceKNN, worker.original_qualification.ExactFullReferenceKNN
        def fake_main(argv):
            self.assertIs(worker.original_worker.ExactFullReferenceKNN, worker.ExactMultiplicityKNN)
            self.assertIs(worker.original_qualification.ExactFullReferenceKNN, worker.ExactMultiplicityKNN)
            self.assertEqual(argv[argv.index("--config") + 1], str(self.original / "config.json"))
            self.assertEqual(argv[argv.index("--registration") + 1], str(self.original / "REGISTRATION.json"))
            self.write_json(output / "RESULTS.json", {"status": "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION"})
            return 0
        with mock.patch.object(worker.original_worker, "main", side_effect=fake_main), \
             mock.patch.dict("os.environ", {"APT_FROZEN_BUNDLE_SHA256": "a" * 64}):
            self.assertEqual(worker.main(self.argv(output)), 0)
        self.assertIs(worker.original_worker.ExactFullReferenceKNN, old_worker)
        self.assertIs(worker.original_qualification.ExactFullReferenceKNN, old_qualification)
        receipt = provenance.read(output / "COMPACT_RUNTIME_RECEIPT.json")
        self.assertEqual(receipt["results_sha256"], provenance.digest(output / "RESULTS.json"))
        self.assertEqual(receipt["compact_registration_sha256"], provenance.digest(self.registration))
        self.assertEqual(receipt["bundle_sha256"], "a" * 64)
        self.assertFalse(receipt["checkpoint_reuse"])
        self.assertEqual(len(receipt["substitutions"]), 2)

    def test_exception_restores_both_runtime_paths_and_records_failed_exit(self):
        output = self.root / "outputs"
        output.mkdir()
        old_worker, old_qualification = worker.original_worker.ExactFullReferenceKNN, worker.original_qualification.ExactFullReferenceKNN
        with mock.patch.object(worker.original_worker, "main", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                worker.main(self.argv(output))
        self.assertIs(worker.original_worker.ExactFullReferenceKNN, old_worker)
        self.assertIs(worker.original_qualification.ExactFullReferenceKNN, old_qualification)
        receipt = provenance.read(output / "COMPACT_RUNTIME_RECEIPT.json")
        self.assertEqual(receipt["exit_code"], 1)
        self.assertIsNone(receipt["results_sha256"])

    def test_existing_scientific_output_is_refused_before_substitution_or_receipt(self):
        output = self.root / "outputs"
        output.mkdir()
        self.write_json(output / "RESULTS.json", {"status": "old science"})
        with mock.patch.object(worker.original_worker, "main") as execute:
            with self.assertRaisesRegex(ValueError, "existing scientific"):
                worker.main(self.argv(output))
            execute.assert_not_called()
        self.assertFalse((output / "COMPACT_RUNTIME_RECEIPT.json").exists())


class CompactCollectionTests(unittest.TestCase):
    def test_real_tiny_archives_require_exact_amendment_bindings(self):
        result = {"status": "COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION", "selected_datasets": ["theia"]}
        result_bytes = json.dumps(result).encode()
        execution = {"compact_registration_sha256": "a" * 64, "bundle_sha256": "b" * 64, "datasets": ["theia"]}
        valid = {**execution, "selected_datasets": ["theia"], "source_original_unchanged": True,
                 "results_sha256": hashlib.sha256(result_bytes).hexdigest(), "exit_code": 0}
        cases = [(None, True), ("missing", False), ("compact_registration_sha256", False), ("bundle_sha256", False),
                 ("selected_datasets", False), ("source_original_unchanged", False), ("exit_code", False)]
        for change, passes in cases:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                private = root / "private"
                private.mkdir()
                (private / "EXECUTION.json").write_text(json.dumps(execution), encoding="utf-8")
                receipt = dict(valid)
                if change == "exit_code": receipt[change] = 1
                elif change == "selected_datasets": receipt[change] = ["cadets"]
                elif change == "source_original_unchanged": receipt[change] = False
                elif change not in {None, "missing"}: receipt[change] = "0" * 64
                archive = root / "result.tar.gz"
                with tarfile.open(archive, "w:gz") as pack:
                    contents = {"outputs/RESULTS.json": result_bytes}
                    if change != "missing": contents["outputs/COMPACT_RUNTIME_RECEIPT.json"] = json.dumps(receipt).encode()
                    for name, payload in contents.items():
                        member = tarfile.TarInfo(name)
                        member.size = len(payload)
                        pack.addfile(member, io.BytesIO(payload))
                marker = root / "result.sha256"
                marker.write_text(provenance.digest(archive), encoding="ascii")
                controller = mock.Mock(settings={"prefix": "synthetic/"})
                def transfer(_, destination, key):
                    shutil.copyfile(marker if key.endswith(".sha256") else archive, destination)
                controller.transfer.side_effect = transfer
                if passes:
                    self.assertEqual(launch.collect(controller, private)["worker"], result)
                else:
                    with self.assertRaises(ValueError):
                        launch.collect(controller, private)

    def test_bootstrap_syntax_and_inherited_storage_guard_are_unchanged(self):
        original = Path(__file__).resolve().parents[1] / "experiments/apt_final/magic_reproduction/run_cloud.sh"
        compact = original.parent.parent / "magic_compact/run_cloud.sh"
        start, end = "# BEGIN_STABLE_STORAGE_GUARDS", "# END_STABLE_STORAGE_GUARDS"
        def guard(path):
            return path.read_text(encoding="utf-8").split(start, 1)[1].split(end, 1)[0]
        self.assertEqual(guard(original), guard(compact))
        bash = Path("C:/Program Files/Git/bin/bash.exe")
        if not bash.exists():
            command = shutil.which("bash")
            if not command: self.skipTest("No Bash for syntax qualification")
        else:
            command = str(bash)
        subprocess.run([command, "-n", str(compact)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
