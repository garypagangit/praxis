"""Runtime continuation reuses exact encoders while preserving scientific results."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest import mock

import numpy as np

from experiments.apt_final.normal_stability import engine
from experiments.apt_final.normal_stability import runner as original_runner
from experiments.apt_final.normal_stability_continuation import checkpoints, runner
from experiments.apt_final.normal_stability_continuation import provenance


class ContinuationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the independent tiny runner fixture, including unreadable normal
        # y objects. Its original scientific run is the comparison oracle.
        path = Path(__file__).with_name("test_apt_stability_runner.py")
        spec = importlib.util.spec_from_file_location("continuation_original_fixture", path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        cls.fixture = fixture.StabilityRunnerIntegration
        cls.fixture.setUpClass()
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.prior = cls.root / "prior"
        shutil.copytree(cls.fixture.out, cls.prior)
        cls.transport = cls.root / "TRANSPORT.json"
        cls.continuation_registration = cls.root / "CONTINUATION_REGISTRATION.json"
        cls.continuation_registration.write_text('{"synthetic_test_only":true}', encoding="utf-8")
        # This counter is deliberately wrong. Completed MANIFEST files are the
        # authority, so all eight checkpoints must still qualify.
        partial = cls.prior / "NORMAL_RESULTS.partial.json"
        partial.write_text('{"completed_encoder_folds":0}', encoding="utf-8")
        cls.archive = cls.root / "result.tar.gz"
        with tarfile.open(cls.archive, "w:gz") as archive:
            archive.add(cls.prior, arcname="outputs")
        cls.transport.write_text(json.dumps({"collection": {"transport_sha256": checkpoints.original.digest(cls.archive)}}), encoding="utf-8")
        with cls.original_provenance():
            cls.reuse = cls.root / "reuse"
            cls.reuse_manifest = checkpoints.prepare_reuse(cls.prior, cls.reuse, cls.fixture.config_path,
                cls.fixture.data, cls.fixture.registration, cls.transport, cls.archive)
            checkpoints.verify_reuse(cls.reuse, cls.fixture.config_path, cls.fixture.data, cls.fixture.registration)
        cls.all_reused_output = cls.root / "all_reused"
        cls.all_reused_output.mkdir()
        for name in runner.OPERATIONAL_STARTUP_FILES - {"WORKER_STATUS.json"}:
            (cls.all_reused_output / name).write_text("synthetic bootstrap diagnostic\n", encoding="utf-8")
        (cls.all_reused_output / "WORKER_STATUS.json").write_text(json.dumps({"status": "RUNNING",
            "runtime_continuation": True, "scientific_settings_changed": False, "runner_invocations": 1}), encoding="utf-8")
        cls.all_reused, cls.reused_fit_calls, cls.label_accesses = cls.execute(cls.reuse, cls.all_reused_output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        cls.fixture.tearDownClass()

    @classmethod
    def original_provenance(cls):
        return mock.patch.object(checkpoints.original, "verify_registration", return_value={"git_commit": "synthetic-qualification"})

    @classmethod
    def execute(cls, reuse, output):
        original_load = np.load
        label_accesses = []

        class Guarded:
            def __init__(self, archive, filename):
                self.archive, self.filename = archive, filename

            def __getattr__(self, key):
                return getattr(self.archive, key)

            def __getitem__(self, key):
                if key == "y":
                    if self.filename != "test0.npz":
                        raise AssertionError("Continuation opened a normal target label")
                    freeze = checkpoints.read(output / "NORMAL_FREEZE.json")
                    normal = checkpoints.read(output / "NORMAL_RESULTS.json")
                    if len(normal["records"]) != 288 or freeze["normal_results_sha256"] != checkpoints.original.digest(output / "NORMAL_RESULTS.json"):
                        raise AssertionError("Test labels were accessed before the full normal grid was frozen")
                    if len([p for p in freeze["private_files"] if p.endswith("NORMAL_SCORES.npz")]) != 16:
                        raise AssertionError("Continuation did not rebuild every normal bank/score file")
                    label_accesses.append(self.filename)
                return self.archive[key]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.archive.close()

        def guarded_load(path, *args, **kwargs):
            archive = original_load(path, *args, **kwargs)
            if isinstance(path, (str, Path)) and Path(path).parent.resolve() == cls.fixture.data.resolve():
                return Guarded(archive, Path(path).name)
            return archive

        with (cls.original_provenance(),
              mock.patch.object(original_runner, "verify_registration", return_value={"git_commit": "synthetic-qualification"}),
              mock.patch.object(provenance, "verify_registration", return_value={"synthetic_test_only": True}),
              mock.patch.object(original_runner, "train_and_cache", wraps=engine.train_and_cache) as fit,
              mock.patch.object(np, "load", side_effect=guarded_load),
              contextlib.redirect_stdout(io.StringIO())):
            result = runner.run(cls.fixture.config_path, cls.fixture.data, output, cls.fixture.registration,
                                reuse, cls.continuation_registration, "cpu")
        return result, fit.call_count, label_accesses

    def test_completed_manifest_overrides_lagging_counter_and_excludes_bank_files(self):
        self.assertEqual(len(self.reuse_manifest["entries"]), 8)
        self.assertEqual(len(self.reuse_manifest["skipped"]), 0)
        self.assertEqual(len(self.reuse_manifest["inventory"]), 8 * 21)
        self.assertFalse(self.reuse_manifest["completed_encoder_folds_counter_used"])
        self.assertEqual(self.reuse_manifest["transport_receipt_sha256"], checkpoints.original.digest(self.transport))
        for entry in self.reuse_manifest["entries"]:
            self.assertEqual(len(entry["files"]), 21)
            self.assertFalse(any("bank_" in path or "attack" in path.lower() for path in entry["files"]))

    def test_reuse_avoids_refitting_and_preserves_original_results_exactly(self):
        self.assertEqual(self.reused_fit_calls, 0)
        self.assertEqual(self.all_reused["normal_records"], self.fixture.result["normal_records"])
        self.assertEqual(self.all_reused["attack_records"], self.fixture.result["attack_records"])
        self.assertEqual(self.all_reused["decision"], self.fixture.result["decision"])
        receipt = checkpoints.read(self.all_reused_output / "CONTINUATION_RECEIPT.json")
        self.assertEqual(receipt["reused_checkpoint_count"], 8)
        self.assertEqual(receipt["fresh_checkpoint_count"], 0)

    def test_all_normal_scores_are_rebuilt_before_attack_label_access(self):
        self.assertEqual(self.label_accesses, ["test0.npz"])
        for entry in self.reuse_manifest["entries"]:
            root = self.all_reused_output / "private" / entry["directory"].removeprefix("checkpoints/")
            for name, expected in entry["files"].items():
                self.assertEqual(checkpoints.original.digest(root / name), expected)
            for bank in self.fixture.config["bank_seeds"]:
                self.assertTrue((root / f"bank_{bank}" / "NORMAL_SCORES.npz").is_file())

    def test_all_reused_path_qualifies_current_runtime_and_binds_receipt(self):
        qualification = self.all_reused_output / "RUNTIME_QUALIFICATION.json"
        actual = checkpoints.read(qualification)
        self.assertTrue(actual["reexecuted_in_continuation_process"])
        self.assertFalse(actual["reused_prior_qualification"])
        self.assertEqual(actual["qualification"]["status"], "CPU_SELECTED")
        receipt = checkpoints.read(self.all_reused_output / "CONTINUATION_RECEIPT.json")
        self.assertEqual(receipt["runtime_device_qualification_sha256"], checkpoints.original.digest(qualification))

    def test_missing_completion_manifest_is_refit_fresh_and_results_stay_identical(self):
        prior, reuse, output = self.root / "partial_prior", self.root / "partial_reuse", self.root / "partial_output"
        shutil.copytree(self.prior, prior)
        missing = prior / "private" / "cadets" / "A" / "encoder_11" / "MANIFEST.json"
        missing.unlink()  # Only the disposable fixture's completion marker.
        with self.original_provenance():
            record = checkpoints.prepare_reuse(prior, reuse, self.fixture.config_path, self.fixture.data,
                                               self.fixture.registration, self.transport, self.archive)
        self.assertEqual(len(record["entries"]), 7)
        self.assertEqual(len(record["skipped"]), 1)
        actual, fit_count, label_reads = self.execute(reuse, output)
        self.assertEqual(fit_count, 1)
        self.assertEqual(label_reads, ["test0.npz"])
        self.assertEqual(actual["normal_records"], self.fixture.result["normal_records"])
        self.assertEqual(actual["attack_records"], self.fixture.result["attack_records"])

    def test_changed_role_or_cache_bytes_are_rejected(self):
        for kind in ("role", "cache"):
            target = self.root / ("tampered_" + kind)
            shutil.copytree(self.reuse, target)
            if kind == "role":
                path = target / "REUSE_MANIFEST.json"
                record = checkpoints.read(path)
                record["entries"][0]["roles"]["fit"] = ["train2", "train3"]
                path.write_text(json.dumps(record), encoding="utf-8")
            else:
                path = target / "checkpoints" / "cadets" / "A" / "encoder_11" / "cache" / "train0" / "clean" / "CACHE.npz"
                with path.open("ab") as stream:
                    stream.write(b"tampered")
            with self.subTest(kind=kind), self.original_provenance(), self.assertRaises(ValueError):
                checkpoints.verify_reuse(target, self.fixture.config_path, self.fixture.data, self.fixture.registration)

    def test_source_identity_and_nonempty_staging_are_rejected(self):
        bad = self.root / "wrong_source"
        shutil.copytree(self.prior, bad)
        path = bad / "RUN_STATUS.json"
        record = checkpoints.read(path)
        record["config_sha256"] = "0" * 64
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.original_provenance(), self.assertRaisesRegex(ValueError, "Prior output"):
            checkpoints.prepare_reuse(bad, self.root / "never_staged", self.fixture.config_path,
                                      self.fixture.data, self.fixture.registration, self.transport, self.archive)
        with self.assertRaises(FileExistsError):
            checkpoints.prepare_reuse(self.prior, self.reuse, self.fixture.config_path,
                                      self.fixture.data, self.fixture.registration)

    def test_worker_created_directory_is_accepted_but_old_scientific_files_are_not(self):
        self.assertEqual(self.all_reused["status"], "COMPLETE_FIXED_FAMILY_DEVELOPMENT")
        self.assertTrue((self.all_reused_output / "WORKER_STATUS.json").is_file())
        for name in ("RUN_STATUS.json", "NORMAL_RESULTS.partial.json", "CONTINUATION_RECEIPT.json", "REUSE_DECISIONS.partial.json"):
            output = self.root / ("rejected_" + name)
            output.mkdir()
            (output / name).write_text("{}", encoding="utf-8")
            with self.subTest(name=name), self.assertRaises(FileExistsError):
                runner.validate_fresh_output(output)

    def test_matching_archive_hash_is_insufficient_when_selected_member_differs(self):
        archive_path = self.root / "unrelated.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            body = b"unrelated bytes"
            info = tarfile.TarInfo("outputs/RUN_STATUS.json")
            info.size = len(body)
            archive.addfile(info, io.BytesIO(body))
        with self.assertRaisesRegex(ValueError, "differs from its archive member"):
            checkpoints.verify_transport(archive_path, checkpoints.original.digest(archive_path),
                                          {"outputs/RUN_STATUS.json": checkpoints.original.digest(self.prior / "RUN_STATUS.json")})


if __name__ == "__main__":
    unittest.main()
