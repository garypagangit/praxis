"""Watch existing CPU jobs and finalize their audited evidence exactly once.

Never fits models, performs inference, starts AWS resources, changes power plans,
or kills worker processes. Run --once for one readiness check, or --watch for
30-second polling with a 12-hour deadline. A fresh private final_root is required.
The optional --keep-awake-on-ac holds system sleep only while plugged in, without
changing power plans/display behavior; battery loss can interrupt completion.
At the deadline an active read-only audit may finish its current step,
but no subsequent step starts. Partial evidence and errors are preserved.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import threading
import time
import traceback

import psutil

from ..tabular_batch.audit_e3 import digest, require

SEEDS = tuple(range(20260921, 20260931))
BASELINES = ("random_forest", "xgboost", "lightgbm")
CONDITIONS = ("equal_32_per_class", "abundant_benign_1024")
POLL_SECONDS = 30
DEADLINE_SECONDS = 12 * 60 * 60


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_config(path):
    raw = read(path)
    required = {"data", "original_cpu", "full_tabicl", "full_tabpfn", "strong_baselines", "final_root"}
    require(required <= set(raw) and set(raw) <= required | {"sandworm"}, "Unexpected/missing config keys")
    config = {name: Path(raw[name]).resolve() for name in required}
    if "sandworm" in raw:
        require(set(raw["sandworm"]) == {"run", "target_data", "checkpoint"}, "Sandworm config requires run, target_data, checkpoint")
        config["sandworm"] = {name: Path(value).resolve() for name, value in raw["sandworm"].items()}
    # The coordinator writes only the final_root; never put it inside a live run.
    for name in ("data", "original_cpu", "full_tabicl", "full_tabpfn", "strong_baselines"):
        require(not config["final_root"].is_relative_to(config[name]), "final_root must be separate from inputs/live runs")
    if "sandworm" in config:
        require(not config["final_root"].is_relative_to(config["sandworm"]["run"]), "final_root overlaps external live run")
    return config


def job_specs(config):
    specs = {}
    for job, models in (("original_cpu", BASELINES), ("full_tabicl", ("tabicl_v2",)), ("full_tabpfn", ("tabpfn_2_5_synthetic",))):
        specs[job] = {"root": config[job], "cells": [f"{model}/{seed}" for model in models for seed in SEEDS], "global_marker_required": False}
    specs["strong_baselines"] = {"root": config["strong_baselines"], "cells": [f"{condition}/{model}/{seed}" for condition in CONDITIONS for model in BASELINES for seed in SEEDS], "global_marker_required": True}
    if "sandworm" in config:
        specs["sandworm"] = {"root": config["sandworm"]["run"], "cells": [f"{model}/{seed}" for model in ("selected_gbdt", "tabicl_v2") for seed in SEEDS], "global_marker_required": True}
    return specs


def readiness(specs):
    """Cheap marker/count check; scientific hashes are checked by final audits."""
    jobs = {}
    for name, spec in specs.items():
        complete, missing, invalid = [], [], []
        for cell in spec["cells"]:
            folder = Path(spec["root"]) / "cells" / cell
            marker = folder / "COMPLETE.json"
            if not marker.is_file():
                missing.append(cell); continue
            try:
                receipt = read(marker)
                require(bool(receipt["execution_binding"]) and bool(receipt["comparison_binding"]), "Missing execution binding")
                require(set(receipt["file_sha256"]) == {"CELL.json", "PREDICTIONS.npz"}, "Wrong cell file roster")
                require(all((folder / file).is_file() for file in receipt["file_sha256"]), "Missing bound cell file")
                complete.append(cell)
            except (OSError, ValueError, KeyError, TypeError) as error:
                invalid.append({"cell": cell, "error": str(error)})
        global_ready = not spec["global_marker_required"] or (Path(spec["root"]) / "COMPLETE.json").is_file()
        jobs[name] = {"path": str(spec["root"]), "complete_cells": len(complete), "required_cells": len(spec["cells"]),
                      "missing_cells": missing, "invalid_cells": invalid, "global_marker_ready": global_ready,
                      "ready": len(complete) == len(spec["cells"]) and global_ready}
    return {"all_ready": bool(jobs) and all(job["ready"] for job in jobs.values()), "jobs": jobs,
            "note": "Readiness counts are not audit results; malformed receipts and missing cells remain visible."}


def capture_workers(mapping, specs, process_factory=psutil.Process):
    require(set(mapping) <= set(specs), "Unknown worker name; use original_cpu/full_tabicl/full_tabpfn/strong_baselines/sandworm")
    result = {}
    for name, pid in mapping.items():
        require(type(pid) is int and pid > 0, "Worker PID must be a positive integer")
        try:
            creation = process_factory(pid).create_time()
            result[name] = {"pid": pid, "create_time": creation, "identity_captured": True}
        except (psutil.NoSuchProcess, psutil.AccessDenied) as error:
            result[name] = {"pid": pid, "create_time": None, "identity_captured": False, "capture_error": type(error).__name__}
    return result


def worker_status(identities, progress, process_factory=psutil.Process):
    result, stopped = {}, []
    for name, identity in identities.items():
        if progress["jobs"][name]["ready"]:
            result[name] = {**identity, "status": "OUTPUT_COMPLETE"}; continue
        try:
            process = process_factory(identity["pid"])
            same = identity["identity_captured"] and process.create_time() == identity["create_time"]
            running = same and process.is_running() and process.status() not in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD)
            status = "RUNNING_SAME_IDENTITY" if running else "EXITED_OR_PID_REUSED"
        except psutil.NoSuchProcess:
            status = "EXITED"
        except psutil.AccessDenied:
            status = "STATUS_UNAVAILABLE"
        result[name] = {**identity, "status": status}
        if status in ("EXITED", "EXITED_OR_PID_REUSED"):
            stopped.append(name)
    return result, stopped


def battery_state():
    try:
        battery = psutil.sensors_battery()
        return {"available": False} if battery is None else {"available": True, "percent": battery.percent, "power_plugged": battery.power_plugged,
                "seconds_left": battery.secsleft, "note": "No power setting changed. Sleep, battery loss or process termination can interrupt completion."}
    except (AttributeError, OSError) as error:
        return {"available": False, "error": type(error).__name__}


def set_sleep_prevention(enabled):
    """Temporary request belonging to this calling thread; no power-plan edits."""
    if os.name != "nt":
        raise OSError("Windows system-awake request unavailable on this platform")
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel.SetThreadExecutionState
    function.argtypes = [wintypes.DWORD]; function.restype = wintypes.DWORD
    flags = 0x80000000 | (0x00000001 if enabled else 0)  # CONTINUOUS, SYSTEM_REQUIRED; no DISPLAY_REQUIRED.
    if function(flags) == 0:
        raise OSError(ctypes.get_last_error(), "SetThreadExecutionState failed")


def update_awake_hold(previous, enabled, battery, setter):
    desired = bool(enabled and battery.get("available") and battery.get("power_plugged") is True)
    result = {"requested": bool(enabled), "active": bool(previous.get("active")),
              "reason": "AC_CONNECTED" if desired else ("BATTERY_OR_POWER_STATUS_UNKNOWN" if enabled else "NOT_REQUESTED")}
    if desired != result["active"]:
        try:
            setter(desired)
            result["active"] = desired
        except OSError as error:
            result["error"] = str(error)
    return result


def snapshot(paths):
    return {str(Path(path).resolve()): digest(Path(path)) for path in paths}


def verify_snapshot(record):
    for path, expected in record.items():
        require(Path(path).is_file() and digest(Path(path)) == expected, "Frozen file changed: " + path)


def source_paths(config, config_path, publish_output, git_publish, worker_path):
    here = Path(__file__).resolve().parent; batch = here.parent / "tabular_batch"
    names = ["finish_followup.py", "audit_comparisons.py", "run_strong_baselines.py", "protocol_strong_baselines.json", "requirements_strong_baselines.txt",
             "run_rare_stage_gate.py", "audit_rare_stage_gate.py", "protocol_rare_stage_gate.json"]
    if "sandworm" in config:
        names += ["audit_sandworm_transfer.py", "run_sandworm_transfer.py", "protocol_sandworm_transfer.json", "prepare_sandworm.py"]
    if publish_output is not None: names.append("publish_followup.py")
    if git_publish: names.append("promote_publication.py")
    paths = [here / name for name in names] + [batch / name for name in ("protocol.json", "run_e1.py", "analyze_e1.py", "conformal.py", "audit_e3.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt")]
    paths += [Path(config_path)] + [Path(spec["root"]) / "PREFIT_RECEIPT.json" for spec in job_specs(config).values()]
    if worker_path is not None: paths.append(Path(worker_path))
    return paths


def require_complete_results(e1, comparisons, gate, audit, transfer=None):
    require(e1.get("audit_status") == "PASS" and e1.get("all_registered_cells_complete") is True and e1.get("completed_cell_count") == 50, "All 50 original cells must pass audit")
    require(comparisons.get("audit_status") == "PASS" and comparisons.get("strong_batch_complete") is True and comparisons.get("complete_strong_cells") == 60, "All 60 stronger cells must pass audit")
    require(audit.get("audit_status") == "PASS" and audit.get("run_status") == "COMPLETE" and audit.get("audited_pair_count") == 10, "All ten gate pairs must pass independent audit")
    require(not gate.get("missing_pairs") and gate["primary"]["paired_seed_count"] == 10 and gate["primary"]["status"] != "INCOMPLETE", "Gate incomplete")
    if transfer is not None:
        require(transfer.get("audit_status") == "PASS" and transfer.get("all_cells_complete") is True and transfer.get("verified_cells") == 20, "All 20 external cells must pass audit")
        require(transfer.get("source_threshold_diagnostic", {}).get("status") == "COMPLETE_AUDITED", "Source-only external threshold diagnostic incomplete")


def finalize(config, frozen, stage, publish_output=None, transfer_summary=None, git_publish=False, deadline_epoch=None):
    """Called once after readiness. Each step rechecks frozen code/protocols."""
    root = config["final_root"]; here = Path(__file__).resolve().parent; batch = here.parent / "tabular_batch"
    e1_roots = [config[name] for name in ("original_cpu", "full_tabicl", "full_tabpfn")]
    def enter(name):
        if deadline_epoch is not None and time.time() >= deadline_epoch:
            raise TimeoutError("Finalization deadline reached; current evidence preserved before " + name)
        verify_snapshot(frozen); stage(name)
    def module(name):
        return importlib.import_module("experiments.apt_benchmark.tabular_followup." + name)
    enter("AUDIT_FULL_E1")
    analyze = importlib.import_module("experiments.apt_benchmark.tabular_batch.analyze_e1")
    e1 = analyze.analyze(config["data"], batch / "protocol.json", e1_roots)
    require(e1["audit_status"] == "PASS" and e1["completed_cell_count"] == 50 and e1["all_registered_cells_complete"], "Full E1 analysis incomplete")
    write(root / "e1/ANALYSIS.json", e1)
    (root / "e1/REPORT.md").write_text(analyze.report_markdown(e1), encoding="utf-8")
    enter("AUDIT_STRONG_COMPARISONS")
    comparisons = module("audit_comparisons").run(config["data"], here / "protocol_strong_baselines.json", batch / "protocol.json", [config["strong_baselines"]], e1_roots)
    write(root / "COMPARISONS.json", comparisons)
    enter("EVALUATE_FROZEN_REVIEW_GATE")
    gate = module("run_rare_stage_gate").run(config["data"], here / "protocol_rare_stage_gate.json", batch / "protocol.json", e1_roots, root / "gate")
    enter("INDEPENDENTLY_AUDIT_REVIEW_GATE")
    gate_audit = module("audit_rare_stage_gate").audit(config["data"], root / "gate", here / "protocol_rare_stage_gate.json", batch / "protocol.json")
    write(root / "gate_audit/AUDIT.json", gate_audit)
    transfer = None; transfer_path = Path(transfer_summary) if transfer_summary is not None else None
    if "sandworm" in config:
        enter("AUDIT_EXTERNAL_AND_SOURCE_THRESHOLD")
        target = config["sandworm"]
        transfer = module("audit_sandworm_transfer").audit(target["run"], config["data"], target["target_data"], here / "protocol_sandworm_transfer.json",
                     batch / "protocol.json", config["original_cpu"], target["checkpoint"], root / "external", source_foundation_run=config["full_tabicl"])
        transfer_path = root / "external/TRANSFER_SUMMARY.json"
    elif transfer_path is not None:
        enter("VERIFY_SUPPLIED_EXTERNAL_SUMMARY")
        require(transfer_path.is_file(), "Requested external summary is missing; retain audited local results")
        transfer = read(transfer_path)
        write(root / "external/TRANSFER_SUMMARY.json", transfer)
        transfer_path = root / "external/TRANSFER_SUMMARY.json"
    enter("VERIFY_FINAL_COMPLETENESS")
    require_complete_results(e1, comparisons, gate, gate_audit, transfer)
    require(gate_audit["artifact_hashes"]["AGGREGATE.json"] == digest(root / "gate/AGGREGATE.json"), "Gate changed after audit")
    artifacts = ["e1/ANALYSIS.json", "e1/REPORT.md", "COMPARISONS.json", "gate/AGGREGATE.json", "gate/COMPLETE.json", "gate_audit/AUDIT.json"]
    if transfer_path is not None: artifacts.append("external/TRANSFER_SUMMARY.json")
    manifest = {"status": "COMPLETE_AUDITED", "completed_utc": utc(), "scientific_outcomes_may_be_negative": True,
                "full_e1_cells": 50, "strong_cells": 60, "review_gate_pairs": 10, "external_cells": 20 if transfer is not None else 0,
                "artifact_sha256": {name: digest(root / name) for name in artifacts}, "startup_receipt_sha256": digest(root / "STARTUP_RECEIPT.json"),
                "publication_status": "NOT_REQUESTED", "no_model_fitting_or_inference_performed": True}
    write(root / "RESULT_MANIFEST.json", manifest)
    if publish_output is not None:
        try:
            enter("PUBLISH_AGGREGATE_RESULTS")
            publication = module("publish_followup").publish(root, Path(publish_output), transfer_path)
            manifest["publication_status"] = "PUBLICATION_LOCAL_COMPLETE"
            manifest["publication_receipt"] = publication
            manifest["publication_output"] = str(Path(publish_output).resolve())
        except Exception as error:
            manifest["publication_status"] = "AUDITED_COMPLETE_PUBLICATION_PENDING"
            manifest["publication_error"] = {"type": type(error).__name__, "message": str(error)}
            write(root / "RESULT_MANIFEST.json", manifest)
            return manifest
        if git_publish:
            try:
                enter("PROMOTE_VERIFIED_PUBLICATION")
                repo = here.parents[2]
                promotion = module("promote_publication")
                require(Path(publish_output).resolve() == (repo / promotion.OUTPUT_RELATIVE).resolve(), "Git promotion only accepts its fixed reviewed results directory")
                manifest["git_publication"] = promotion.promote(repo)
                manifest["publication_status"] = "PUSHED_AND_VERIFIED"
            except Exception as error:
                manifest["publication_status"] = "PUBLICATION_LOCAL_COMPLETE_GIT_PENDING"
                manifest["git_error"] = {"type": type(error).__name__, "message": str(error)}
    write(root / "RESULT_MANIFEST.json", manifest)
    return manifest


def coordinate(config_path, *, watch, worker_path=None, publish_output=None, transfer_summary=None, git_publish=False, keep_awake_on_ac=False, awake_setter=None):
    require(not git_publish or publish_output is not None, "--git-publish requires --publish-output")
    config_path = Path(config_path).resolve(); config = load_config(config_path); root = config["final_root"]; specs = job_specs(config)
    startup = root / "STARTUP_RECEIPT.json"
    options = {"publish_output": str(Path(publish_output).resolve()) if publish_output is not None else None,
               "transfer_summary": str(Path(transfer_summary).resolve()) if transfer_summary is not None else None,
               "worker_path": str(Path(worker_path).resolve()) if worker_path is not None else None, "git_publish": git_publish,
               "keep_awake_on_ac": keep_awake_on_ac}
    require(not root.exists() or not any(root.iterdir()) or startup.exists(), "Existing final files lack a coordinator receipt; choose fresh final_root")
    if startup.exists():
        receipt = read(startup); verify_snapshot(receipt["frozen_files"])
        require(receipt["config_sha256"] == digest(config_path), "Coordinator config changed")
        require(receipt["options"] == options, "Coordinator options changed; use a fresh final_root so all requested code is frozen")
        identities = receipt["worker_identities"]
        if (root / "RESULT_MANIFEST.json").exists():
            completed = read(root / "RESULT_MANIFEST.json")
            require(completed["status"] == "COMPLETE_AUDITED", "Previous manifest is incomplete")
            for name, claimed in completed["artifact_sha256"].items(): require(digest(root / name) == claimed, "Audited result changed")
            return completed
        require(not (root / "FINALIZATION_STARTED.json").exists(), "Prior finalization attempt preserved; inspect ERROR.json and use a new final_root for a retry")
    else:
        identities = capture_workers(read(worker_path) if worker_path else {}, specs)
        frozen = snapshot(source_paths(config, config_path, publish_output, git_publish, worker_path))
        receipt = {"created_utc": utc(), "started_epoch": time.time(), "deadline_epoch": time.time() + DEADLINE_SECONDS,
                   "config_sha256": digest(config_path), "config_path": str(config_path), "frozen_files": frozen,
                   "worker_identities": identities, "poll_seconds": POLL_SECONDS, "deadline_hours": 12,
                   "publication_requested": publish_output is not None, "git_publication_requested": git_publish, "options": options}
        write(startup, receipt)
    frozen = receipt["frozen_files"]; state_lock = threading.Lock(); active_stage = {"name": "WAITING", "started_utc": utc()}
    def stage(name):
        with state_lock: active_stage.update(name=name, started_utc=utc())
    future = None
    executor = ThreadPoolExecutor(max_workers=1)
    awake_setter = awake_setter or set_sleep_prevention
    awake_hold = {"requested": False, "active": False, "reason": "NOT_REQUESTED"}
    try:
        while True:
            try:
                verify_snapshot(frozen)
                progress = readiness(specs)
                workers, stopped = worker_status(identities, progress)
            except Exception as error:
                write(root / "ERROR.json", {"stage": "VERIFY_FROZEN_INPUTS", "time_utc": utc(), "type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
                write(root / "STATE.json", {"status": "FAILED_FROZEN_INPUTS", "updated_utc": utc(), "error": str(error), "battery": battery_state()})
                raise
            with state_lock: current = dict(active_stage)
            battery = battery_state()
            awake_hold = update_awake_hold(awake_hold, watch and keep_awake_on_ac, battery, awake_setter)
            state = {"updated_utc": utc(), "status": "FINALIZING" if future else "WAITING", "stage": current, "progress": progress,
                     "workers": workers, "battery": battery, "system_awake_hold": awake_hold, "deadline_utc": datetime.fromtimestamp(receipt["deadline_epoch"], timezone.utc).isoformat(),
                     "seconds_remaining": max(0, receipt["deadline_epoch"] - time.time()), "automatic_refits_or_inference": False}
            if future is not None and future.done():
                try:
                    result = future.result()
                    state["status"] = result["publication_status"] if result["publication_status"] != "NOT_REQUESTED" else "COMPLETE_AUDITED"
                    state["result_manifest"] = str(root / "RESULT_MANIFEST.json")
                    write(root / "STATE.json", state)
                    return result
                except Exception as error:
                    state["status"] = "FAILED_FINALIZATION"; state["error"] = str(error)
                    write(root / "ERROR.json", {"time_utc": utc(), "stage": current, "type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
                    write(root / "STATE.json", state)
                    raise
            if future is None:
                if time.time() >= receipt["deadline_epoch"]:
                    state["status"] = "TIMED_OUT_INCOMPLETE"
                    write(root / "STATE.json", state); return state
                if progress["all_ready"]:
                    write(root / "FINALIZATION_STARTED.json", {"time_utc": utc(), "startup_receipt_sha256": digest(startup)})
                    future = executor.submit(finalize, config, frozen, stage, publish_output, transfer_summary, git_publish, receipt["deadline_epoch"])
                    state["status"] = "FINALIZING"
                elif stopped:
                    state["status"] = "STOPPED_INCOMPLETE"; state["stopped_incomplete_workers"] = stopped
                    write(root / "STATE.json", state); return state
                elif not watch:
                    state["status"] = "CHECK_ONLY_INCOMPLETE"
                    write(root / "STATE.json", state); return state
            write(root / "STATE.json", state)
            # If already ready, --once completes the one analysis sequence; no reruns.
            time.sleep(POLL_SECONDS)
    finally:
        # Executed on the coordinator main thread, the owner of its temporary hold.
        if awake_hold.get("active"):
            released = update_awake_hold(awake_hold, False, {}, awake_setter)
            if (root / "STATE.json").exists():
                final_state = read(root / "STATE.json")
                final_state["system_awake_hold"] = released
                write(root / "STATE.json", final_state)
        executor.shutdown(wait=True, cancel_futures=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true"); mode.add_argument("--watch", action="store_true")
    parser.add_argument("--worker-pids", type=Path)
    parser.add_argument("--publish-output", type=Path)
    parser.add_argument("--transfer-summary", type=Path)
    parser.add_argument("--git-publish", action="store_true")
    parser.add_argument("--keep-awake-on-ac", action="store_true", help="Temporary system-awake request only during --watch and AC power; clear on battery/exit")
    args = parser.parse_args()
    result = coordinate(args.config, watch=args.watch, worker_path=args.worker_pids, publish_output=args.publish_output,
                        transfer_summary=args.transfer_summary, git_publish=args.git_publish, keep_awake_on_ac=args.keep_awake_on_ac)
    print(json.dumps({"status": result["status"], "publication_status": result.get("publication_status")}))


if __name__ == "__main__":
    main()
