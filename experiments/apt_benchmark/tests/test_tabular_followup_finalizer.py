"""No-wait, no-fit tests for automated finalization and failure preservation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import psutil

from experiments.apt_benchmark.tabular_followup import finish_followup as finalizer


class FinalizerTests(unittest.TestCase):
    def create_cell(self, root, name):
        cell = root / "cells" / name
        cell.mkdir(parents=True)
        (cell / "CELL.json").write_text("{}", encoding="utf-8")
        (cell / "PREDICTIONS.npz").write_bytes(b"synthetic")
        finalizer.write(cell / "COMPLETE.json", {"execution_binding": "synthetic", "comparison_binding": "synthetic",
                        "file_sha256": {"CELL.json": "synthetic", "PREDICTIONS.npz": "synthetic"}})

    def test_readiness_requires_exact_roster_and_global_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec = {"strong_baselines": {"root": root, "cells": ["a/1", "b/1"], "global_marker_required": True}}
            self.create_cell(root, "a/1")
            state = finalizer.readiness(spec)
            self.assertFalse(state["all_ready"])
            self.assertEqual(state["jobs"]["strong_baselines"]["complete_cells"], 1)
            self.create_cell(root, "b/1")
            self.assertFalse(finalizer.readiness(spec)["all_ready"])
            finalizer.write(root / "COMPLETE.json", {})
            self.assertTrue(finalizer.readiness(spec)["all_ready"])
            (root / "cells/b/1/COMPLETE.json").write_text("broken", encoding="utf-8")
            state = finalizer.readiness(spec)
            self.assertFalse(state["all_ready"])
            self.assertEqual(len(state["jobs"]["strong_baselines"]["invalid_cells"]), 1)

    def test_job_contract_counts_are_50_plus_60_plus_20(self):
        config = {name: Path(name) for name in ("original_cpu", "full_tabicl", "full_tabpfn", "strong_baselines")}
        config["sandworm"] = {"run": Path("sandworm")}
        specs = finalizer.job_specs(config)
        self.assertEqual({name: len(spec["cells"]) for name, spec in specs.items()},
                         {"original_cpu": 30, "full_tabicl": 10, "full_tabpfn": 10, "strong_baselines": 60, "sandworm": 20})

    def test_source_change_is_rejected_before_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scientific.py"
            path.write_text("frozen", encoding="utf-8")
            hashes = finalizer.snapshot([path])
            finalizer.verify_snapshot(hashes)
            path.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Frozen file changed"):
                finalizer.verify_snapshot(hashes)

    def test_pid_reuse_is_terminal_only_for_incomplete_output(self):
        class Process:
            def __init__(self, pid): self.pid = pid
            def create_time(self): return 200.
            def is_running(self): return True
            def status(self): return psutil.STATUS_RUNNING
        identity = {"full_tabicl": {"pid": 73, "create_time": 100., "identity_captured": True}}
        progress = {"jobs": {"full_tabicl": {"ready": False}}}
        statuses, stopped = finalizer.worker_status(identity, progress, Process)
        self.assertEqual(stopped, ["full_tabicl"])
        self.assertEqual(statuses["full_tabicl"]["status"], "EXITED_OR_PID_REUSED")
        progress["jobs"]["full_tabicl"]["ready"] = True
        self.assertEqual(finalizer.worker_status(identity, progress, Process)[1], [])

    def test_awake_hold_is_ac_only_and_clears_when_battery(self):
        calls = []
        state = finalizer.update_awake_hold({"active": False}, True, {"available": True, "power_plugged": True}, calls.append)
        self.assertTrue(state["active"])
        state = finalizer.update_awake_hold(state, True, {"available": True, "power_plugged": True}, calls.append)
        self.assertEqual(calls, [True])
        state = finalizer.update_awake_hold(state, True, {"available": True, "power_plugged": False}, calls.append)
        self.assertFalse(state["active"])
        self.assertEqual(calls, [True, False])
        finalizer.update_awake_hold(state, True, {"available": False}, calls.append)
        self.assertEqual(calls, [True, False])

    def test_awake_hold_is_released_on_terminal_watcher_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            config, output = self.config(Path(temp)); calls = []
            with patch.object(finalizer, "source_paths", return_value=[config]), patch.object(finalizer, "worker_status", return_value=({}, ["full_tabicl"])), patch.object(finalizer, "battery_state", return_value={"available": True, "power_plugged": True}):
                result = finalizer.coordinate(config, watch=True, keep_awake_on_ac=True, awake_setter=calls.append)
            self.assertEqual(result["status"], "STOPPED_INCOMPLETE")
            self.assertEqual(calls, [True, False])
            self.assertFalse(finalizer.read(output / "STATE.json")["system_awake_hold"]["active"])

    def complete_results(self):
        return ({"audit_status": "PASS", "all_registered_cells_complete": True, "completed_cell_count": 50},
                {"audit_status": "PASS", "strong_batch_complete": True, "complete_strong_cells": 60},
                {"missing_pairs": [], "primary": {"paired_seed_count": 10, "status": "DEVELOPMENT_NEGATIVE"}},
                {"audit_status": "PASS", "run_status": "COMPLETE", "audited_pair_count": 10})

    def test_negative_science_can_complete_but_failed_audit_cannot(self):
        values = self.complete_results()
        finalizer.require_complete_results(*values)
        values[3]["audit_status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "independent audit"):
            finalizer.require_complete_results(*values)

    def test_external_threshold_diagnostic_is_required(self):
        transfer = {"audit_status": "PASS", "all_cells_complete": True, "verified_cells": 20,
                    "source_threshold_diagnostic": {"status": "PENDING"}}
        with self.assertRaisesRegex(ValueError, "threshold diagnostic"):
            finalizer.require_complete_results(*self.complete_results(), transfer)
        transfer["source_threshold_diagnostic"]["status"] = "COMPLETE_AUDITED"
        finalizer.require_complete_results(*self.complete_results(), transfer)

    def config(self, root):
        value = {name: str(root / name) for name in ("data", "original_cpu", "full_tabicl", "full_tabpfn", "strong_baselines", "final_root")}
        path = root / "config.json"; finalizer.write(path, value)
        return path, Path(value["final_root"])

    def test_once_incomplete_never_sleeps_or_starts_finalization(self):
        with tempfile.TemporaryDirectory() as temp:
            config, output = self.config(Path(temp))
            with patch.object(finalizer, "source_paths", return_value=[config]), patch.object(finalizer.time, "sleep") as sleep, patch.object(finalizer, "finalize") as run:
                result = finalizer.coordinate(config, watch=False)
            self.assertEqual(result["status"], "CHECK_ONLY_INCOMPLETE")
            self.assertFalse((output / "RESULT_MANIFEST.json").exists())
            sleep.assert_not_called(); run.assert_not_called()

    def test_dead_worker_stops_without_false_success(self):
        with tempfile.TemporaryDirectory() as temp:
            config, output = self.config(Path(temp))
            with patch.object(finalizer, "source_paths", return_value=[config]), patch.object(finalizer, "worker_status", return_value=({}, ["full_tabicl"])), patch.object(finalizer.time, "sleep") as sleep:
                result = finalizer.coordinate(config, watch=True)
            self.assertEqual(result["status"], "STOPPED_INCOMPLETE")
            self.assertFalse((output / "RESULT_MANIFEST.json").exists())
            sleep.assert_not_called()

    def test_deadline_stops_waiting_without_starting_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            config, output = self.config(Path(temp))
            with patch.object(finalizer, "source_paths", return_value=[config]), patch.object(finalizer.time, "time", return_value=100.):
                finalizer.coordinate(config, watch=False)
            with patch.object(finalizer.time, "time", return_value=100. + finalizer.DEADLINE_SECONDS), patch.object(finalizer.time, "sleep") as sleep, patch.object(finalizer, "finalize") as run:
                result = finalizer.coordinate(config, watch=True)
            self.assertEqual(result["status"], "TIMED_OUT_INCOMPLETE")
            self.assertFalse((output / "RESULT_MANIFEST.json").exists())
            sleep.assert_not_called(); run.assert_not_called()

    def test_failed_finalization_preserves_error_and_cannot_claim_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            config, output = self.config(Path(temp))
            progress = {"all_ready": True, "jobs": {}}
            with patch.object(finalizer, "source_paths", return_value=[config]), patch.object(finalizer, "readiness", return_value=progress), patch.object(finalizer.time, "sleep"), patch.object(finalizer, "finalize", side_effect=ValueError("synthetic audit failed")):
                with self.assertRaisesRegex(ValueError, "synthetic audit failed"):
                    finalizer.coordinate(config, watch=False)
            self.assertEqual(finalizer.read(output / "STATE.json")["status"], "FAILED_FINALIZATION")
            self.assertIn("synthetic audit failed", finalizer.read(output / "ERROR.json")["message"])
            self.assertFalse((output / "RESULT_MANIFEST.json").exists())
            with self.assertRaisesRegex(ValueError, "Prior finalization attempt preserved"):
                finalizer.coordinate(config, watch=False)


if __name__ == "__main__":
    unittest.main()
