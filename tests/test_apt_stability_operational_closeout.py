"""Bounded independent qualification of sanitized operational closeout."""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from experiments.apt_final.normal_stability_continuation.analysis import build_operational_closeout as closeout


class OperationalCloseout(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.attempt = self.root / "cloud_attempt1"
        self.receipts = self.attempt / "receipts"
        self.receipts.mkdir(parents=True)
        private = {"account": "123456789012", "instance": "i-secret12345", "bucket": "private-bucket-123",
                   "stop_role_arn": "arn:aws:iam::123456789012:role/private-role", "prefix": "private/prefix123",
                   "region": "us-east-1"}
        self.active = {**private, "stage": "closed", "start_request_utc": "2026-09-20T00:00:00+00:00",
                       "stopped_observed_utc": "2026-09-20T00:30:00+00:00", "identities": {"test": "frozen"},
                       "usd_per_hour": 1.2, "elapsed_to_stopped_observation_seconds": 1800,
                       "approximate_compute_usd": .6, "incidental_allowance_usd": 5, "total_reserve_usd": 10}
        self.settings = {**private, "usd_per_hour": 1.2}
        self.start = {"action": "start", "status": "START_SUBMITTED_WATCHDOG_VERIFIED", "active_run": self.active}
        self.stop = {"action": "stop", "status": "STOP_REQUESTED_WATCHDOG_RETAINED", "instance_state": "running"}
        self.final = {"action": "finalize", "status": "CLOSED_VERIFIED_STOPPED", "instance_state": "stopped",
                      "stopped_observed_utc": self.active["stopped_observed_utc"], "elapsed_seconds": 1800,
                      "approximate_compute_usd": .6, "incidental_allowance_usd": 5,
                      "approximate_total_with_allowance_usd": 5.6, "within_reserve": True,
                      "host_time_cap_observed": True, "is_invoice": False,
                      "watchdog_cleanup": "deleted_own_schedule_after_stopped", "gate_failed": False}
        self.execution = {"scope": "DEVELOPMENT_ONLY",
                          "start": {"receipt": str(self.receipts / "start.json"), "status": self.start["status"]},
                          "stop": {"receipt": str(self.receipts / "stop.json"), "status": self.stop["status"], "instance_state": "running"},
                          "finalize": {"receipt": str(self.receipts / "final.json"), "status": self.final["status"], "instance_state": "stopped"}}
        self.save()

    def tearDown(self):
        self.temporary.cleanup()

    def save(self):
        for path, record in ((self.attempt / "ACTIVE_RUN.json", self.active),
                             (self.attempt / "settings.json", self.settings),
                             (self.attempt / "EXECUTION.json", self.execution),
                             (self.receipts / "start.json", self.start),
                             (self.receipts / "stop.json", self.stop),
                             (self.receipts / "final.json", self.final)):
            path.write_text(json.dumps(record), encoding="utf-8")

    def summary(self):
        with mock.patch.object(closeout, "verify_bundle", return_value=({}, None)):
            return closeout.summarize_attempt(self.root, 1, set())[0]

    def test_stop_request_does_not_establish_stopped_but_exact_final_receipt_does(self):
        row = self.summary()
        self.assertTrue(row["stopped_verified"])
        self.assertEqual(row["stopped_observed_utc"], self.final["stopped_observed_utc"])
        del self.execution["finalize"]
        self.save()
        self.assertFalse(self.summary()["stopped_verified"])

    def test_compute_is_recomputed_and_inconsistent_cost_or_time_is_rejected(self):
        row = self.summary()
        self.assertAlmostEqual(row["approximate_compute_usd"], 1800 / 3600 * 1.2)
        self.assertEqual(row["incidental_budget_allowance_usd"], 5)
        self.assertFalse(row["allowance_is_measured_spending"])
        self.final["approximate_compute_usd"] = .7
        self.save()
        with self.assertRaisesRegex(ValueError, "Compute estimate mismatch"):
            self.summary()
        self.final["approximate_compute_usd"] = .6
        self.final["elapsed_seconds"] = 1700
        self.save()
        with self.assertRaisesRegex(ValueError, "Elapsed time estimate mismatch"):
            self.summary()

    def test_final_closeout_rejects_pending_expected_attempt(self):
        row = self.summary()
        with mock.patch.object(closeout, "summarize_attempt", return_value=(row, None, {})):
            draft = closeout.build(self.root, through=1, expected_attempts=2)
            self.assertEqual(draft["status"], "DRAFT_PENDING_ATTEMPT_CLOSEOUT")
            self.assertEqual(draft["closed_attempt_count"], 1)
            self.assertAlmostEqual(draft["approximate_compute_usd_for_closed_attempts"], .6)
            with self.assertRaisesRegex(ValueError, "verified stopped receipt for every"):
                closeout.build(self.root, through=1, expected_attempts=2, require_closed=True)

    def test_public_output_excludes_infrastructure_values_and_guard_rejects_leak(self):
        with mock.patch.object(closeout, "verify_bundle", return_value=({}, None)):
            result = closeout.build(self.root, expected_attempts=1, require_closed=True)
        serialized = json.dumps(result) + closeout.markdown(result)
        for secret in closeout.private_values(self.active):
            self.assertNotIn(secret, serialized)
        row = self.summary()
        row["outcome"] = self.active["instance"]
        def leaking(*args):
            args[2].add(self.active["instance"])
            return row, None, {}
        with mock.patch.object(closeout, "summarize_attempt", side_effect=leaking):
            with self.assertRaisesRegex(ValueError, "Private infrastructure value leaked"):
                closeout.build(self.root, expected_attempts=1)

    def test_receipt_tampering_and_escape_are_rejected(self):
        self.final["status"] = "STOP_REQUESTED_WATCHDOG_RETAINED"
        self.save()
        with self.assertRaisesRegex(ValueError, "Execution summary differs"):
            self.summary()
        self.execution["finalize"]["receipt"] = str(self.root / "outside.json")
        self.save()
        with self.assertRaisesRegex(ValueError, "Receipt escapes"):
            self.summary()

    def test_tiny_bundle_binds_registered_source_even_if_transport_hash_is_updated(self):
        original = closeout.ORIGINAL
        code = {original + "config.json": b"{}", original + "PROTOCOL.md": b"protocol",
                "repo/experiments/apt_final/native_graph/cloud_control.py": b"controller"}
        manifest = b'{"synthetic":true}'
        registration = {"git_commit": "a" * 40,
                        "code_hashes": {name.removeprefix("repo/"): closeout.digest_bytes(body) for name, body in code.items()},
                        "data_manifest_sha256": closeout.digest_bytes(manifest),
                        "data_files": {"tiny.npz": closeout.digest_bytes(b"data")},
                        "config_sha256": closeout.digest_bytes(b"{}")}
        registration_bytes = json.dumps(registration).encode()
        members = {**code, original + "REGISTRATION.json": registration_bytes, "data/MANIFEST.json": manifest,
                   "data/tiny.npz": b"data"}
        archive = self.attempt / "bundle.tar.gz"
        def pack():
            with tarfile.open(archive, "w:gz") as stream:
                for name, body in members.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(body)
                    stream.addfile(info, io.BytesIO(body))
            return {"bundle_sha256": closeout.digest(archive), "bundle_bytes": archive.stat().st_size,
                    "controller_sha256": closeout.digest_bytes(b"controller")}
        active = {"identities": {"runtime_freeze": {"sha256": closeout.digest_bytes(registration_bytes), "commit": "b" * 40},
                                "protocol": {"sha256": closeout.digest_bytes(b"protocol"), "commit": "b" * 40}}}
        public, reuse = closeout.verify_bundle(self.attempt, pack(), active, 1)
        self.assertTrue(public["exact_bundle_inventory_verified"])
        self.assertIsNone(reuse)
        members[original + "PROTOCOL.md"] = b"tampered protocol"
        with self.assertRaisesRegex(ValueError, "Registered source differs"):
            closeout.verify_bundle(self.attempt, pack(), active, 1)


if __name__ == "__main__":
    unittest.main()
