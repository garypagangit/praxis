"""Build a sanitized, hash-bound operational account of bounded GPU attempts.

No AWS calls, extraction, model loading, fitting, or scientific decision making.
Run with --through 3 --expected-attempts 4 for a draft; after the last attempt
closes, use --require-closed and a fresh --output-dir. Raw receipts stay private.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import tarfile


ORIGINAL = "repo/experiments/apt_final/normal_stability/"
CONTINUATION = "repo/experiments/apt_final/normal_stability_continuation/"
OUTPUT_JSON = {"outputs/" + name for name in (
    "WORKER_STATUS.json", "RUN_STATUS.json", "NORMAL_FREEZE.json", "CONTINUATION_RECEIPT.json")}
INPUT_JSON = {ORIGINAL + "REGISTRATION.json", CONTINUATION + "REGISTRATION.json",
              "data/MANIFEST.json", "reuse/REUSE_MANIFEST.json"}
PRIVATE_KEYS = {"account", "instance", "bucket", "stop_role_arn", "command_id", "run_id",
                "schedule", "prefix", "profile", "stdout_url", "stderr_url"}


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with Path(path).open("rb") as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), digest_bytes(raw)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def valid_hash(value, length=64):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(length) + "}", value),
            "Invalid digest or source commit")
    return value


def stamp(value):
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(date.tzinfo is not None, "Timestamp has no timezone")
    return date


def near(left, right):
    return math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-8)


def private_values(value):
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in PRIVATE_KEYS and isinstance(item, str) and len(item) >= 6:
                result.add(item)
            result.update(private_values(item))
    elif isinstance(value, list):
        for item in value:
            result.update(private_values(item))
    return result


def archive_inventory(path, selected):
    """Stream actual bytes once; retain only small, explicitly named JSON receipts."""
    hashes, records, seen, total = {}, {}, set(), 0
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            name = member.name
            parts = PurePosixPath(name)
            require(not parts.is_absolute() and ".." not in parts.parts and "\\" not in name,
                    "Unsafe archive member")
            require(name.casefold() not in seen and (member.isfile() or member.isdir()),
                    "Duplicate or unsupported archive member")
            seen.add(name.casefold())
            total += member.size
            require(len(seen) <= 2000 and total <= 4_000_000_000, "Archive exceeds frozen bounds")
            if not member.isfile():
                continue
            hasher, captured = hashlib.sha256(), []
            if name in selected:
                require(member.size <= 16_000_000, "Oversize selected JSON receipt")
            with archive.extractfile(member) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(block)
                    if name in selected:
                        captured.append(block)
            hashes[name] = hasher.hexdigest()
            if name in selected:
                records[name] = json.loads(b"".join(captured))
    return hashes, records


def receipt(attempt_dir, execution, key, expected_action, bindings, secrets):
    reference = execution.get(key)
    if reference is None:
        return None
    path = Path(reference["receipt"]).resolve()
    require(path.is_relative_to((attempt_dir / "receipts").resolve()), "Receipt escapes attempt directory")
    record, sha = read(path)
    require(record.get("action") == expected_action, "Controller receipt action mismatch")
    for field in ("status", "instance_state", "response_code", "command_id", "gate_failed",
                  "host_time_cap_observed", "within_reserve", "approximate_total_with_allowance_usd"):
        if field in reference:
            require(reference[field] == record.get(field), "Execution summary differs from its receipt")
    bindings[key + "_receipt_sha256"] = sha
    secrets.update(private_values(record))
    return record


def verify_bundle(attempt_dir, execution, active, number):
    bundle = attempt_dir / "bundle.tar.gz"
    sha = digest(bundle)
    require(sha == execution["bundle_sha256"], "Input bundle checksum mismatch")
    require(bundle.stat().st_size == execution["bundle_bytes"], "Input bundle size mismatch")
    hashes, records = archive_inventory(bundle, INPUT_JSON)
    original = records[ORIGINAL + "REGISTRATION.json"]
    module = ORIGINAL if number == 1 else CONTINUATION
    registration = records[module + "REGISTRATION.json"]
    for record in (original, registration):
        for rel, expected in record["code_hashes"].items():
            require(hashes.get("repo/" + rel) == expected, "Registered source differs inside bundle")
        require(hashes.get("data/MANIFEST.json") == record["data_manifest_sha256"],
                "Data manifest differs inside bundle")
        for rel, expected in record["data_files"].items():
            require(hashes.get("data/" + rel) == expected, "Registered data differs inside bundle")
    require(hashes.get(ORIGINAL + "config.json") == original["config_sha256"], "Original config mismatch")
    identities = active["identities"]
    require(hashes[module + "REGISTRATION.json"] == identities["runtime_freeze"]["sha256"],
            "Launch freeze does not match bundled registration")
    require(hashes[module + "PROTOCOL.md"] == identities["protocol"]["sha256"],
            "Launch protocol does not match bundled protocol")
    require(identities["runtime_freeze"]["commit"] == identities["protocol"]["commit"],
            "Protocol and registration launch commits differ")
    require(hashes["repo/experiments/apt_final/native_graph/cloud_control.py"] == execution["controller_sha256"],
            "Controller code digest differs")
    reuse = None
    if number > 1:
        reuse = records["reuse/REUSE_MANIFEST.json"]
        require(hashes["reuse/REUSE_MANIFEST.json"] == registration["reuse_manifest_sha256"],
                "Reuse manifest differs inside bundle")
        require(registration["original_registration_sha256"] == hashes[ORIGINAL + "REGISTRATION.json"],
                "Continuation original-registration binding differs")
        require(registration["original_source_commit"] == original["git_commit"], "Original source commit differs")
        require(registration["original_config_sha256"] == original["config_sha256"], "Original config binding differs")
        require(registration["scientific_settings_changed"] is False and
                registration["all_banks_and_calibration_recomputed"] is True and
                registration["all_attack_conditions_replayed"] is True, "Continuation scientific contract differs")
        require(registration["reuse_files"] == reuse["inventory"], "Reuse inventory bindings differ")
        for rel, expected in registration["reuse_files"].items():
            require(hashes.get("reuse/" + rel) == expected, "Reused checkpoint bytes differ")
    expected_members = {"repo/" + rel for rel in registration["code_hashes"]}
    expected_members.update("data/" + rel for rel in registration["data_files"])
    expected_members.update({module + "REGISTRATION.json", "data/MANIFEST.json"})
    if reuse:
        expected_members.add("reuse/REUSE_MANIFEST.json")
        expected_members.update("reuse/" + rel for rel in registration["reuse_files"])
    require(set(hashes) == expected_members, "Input bundle contains missing or unregistered files")
    public = {
        "bundle_sha256": sha, "bundle_bytes": bundle.stat().st_size,
        "exact_bundle_inventory_verified": True,
        "runtime_registration_sha256": hashes[module + "REGISTRATION.json"],
        "runtime_protocol_sha256": hashes[module + "PROTOCOL.md"],
        "registered_source_files_verified": len(registration["code_hashes"]),
        "registered_data_files_verified": len(registration["data_files"]),
        "source_commit": valid_hash(registration["git_commit"], 40),
        "launch_freeze_commit": valid_hash(identities["runtime_freeze"]["commit"], 40),
        "original_source_commit": valid_hash(original["git_commit"], 40),
        "original_registration_sha256": hashes[ORIGINAL + "REGISTRATION.json"],
        "original_config_sha256": valid_hash(original["config_sha256"]),
        "data_manifest_sha256": valid_hash(original["data_manifest_sha256"]),
    }
    if reuse:
        public.update(reuse_manifest_sha256=hashes["reuse/REUSE_MANIFEST.json"],
                      reused_checkpoint_files_verified=len(registration["reuse_files"]),
                      eligible_encoder_cache_sets=len(reuse["entries"]))
    return public, reuse


def summarize_attempt(root, number, secrets):
    attempt_dir = root / ("cloud_attempt" + str(number))
    execution_path = attempt_dir / "EXECUTION.json"
    if not execution_path.exists():
        return {"attempt": number, "outcome": "PENDING", "stopped_verified": False}, None, {}
    execution, execution_sha = read(execution_path)
    secrets.update(private_values(execution))
    require(execution.get("scope") == "DEVELOPMENT_ONLY", "Unexpected operational scope")
    active, active_sha = read(attempt_dir / "ACTIVE_RUN.json")
    settings, settings_sha = read(attempt_dir / "settings.json")
    secrets.update(private_values(active))
    secrets.update(private_values(settings))
    for key in ("account", "instance", "bucket", "stop_role_arn", "prefix", "region"):
        require(active[key] == settings[key], "Controller identity differs from settings")
    bindings = {"execution_snapshot_sha256": execution_sha, "controller_state_snapshot_sha256": active_sha,
                "settings_sha256": settings_sha}
    start = receipt(attempt_dir, execution, "start", "start", bindings, secrets)
    poll = receipt(attempt_dir, execution, "last_poll", "poll", bindings, secrets)
    receipt(attempt_dir, execution, "stop", "stop", bindings, secrets)
    final = receipt(attempt_dir, execution, "finalize", "finalize", bindings, secrets)
    require(start is not None, "Started attempt has no start receipt")
    require(start["active_run"]["start_request_utc"] == active["start_request_utc"], "Start timestamp changed")
    require(start["active_run"]["identities"] == active["identities"], "Launch source identities changed")
    source, reuse = verify_bundle(attempt_dir, execution, active, number)
    public = {"attempt": number, "outcome": "IN_PROGRESS_OR_INCOMPLETE",
              "host_start_requested_utc": stamp(active["start_request_utc"]).isoformat(),
              "stopped_verified": False, "source_freeze": source, "evidence": bindings,
              "sole_checkpoint_source": number == 1,
              "scientific_completion_worker_reported": False}
    if final and final.get("status") == "CLOSED_VERIFIED_STOPPED":
        require(final.get("instance_state") == "stopped" and active["stage"] == "closed",
                "Stopped status is not supported by controller state")
        require(active["stopped_observed_utc"] == final["stopped_observed_utc"], "Stopped timestamps differ")
        elapsed = max(0.0, (stamp(final["stopped_observed_utc"]) - stamp(active["start_request_utc"])).total_seconds())
        rate = float(active["usd_per_hour"])
        require(near(rate, settings["usd_per_hour"]), "Compute rate changed")
        estimate = elapsed / 3600 * rate
        require(near(elapsed, final["elapsed_seconds"]) and
                near(elapsed, active["elapsed_to_stopped_observation_seconds"]), "Elapsed time estimate mismatch")
        require(near(estimate, final["approximate_compute_usd"]) and
                near(estimate, active["approximate_compute_usd"]), "Compute estimate mismatch")
        require(final["is_invoice"] is False, "Estimate unexpectedly claims invoice status")
        require(final["host_time_cap_observed"] == (elapsed <= 3600), "Host time-cap flag differs")
        allowance = float(final["incidental_allowance_usd"])
        require(near(final["approximate_total_with_allowance_usd"], estimate + allowance), "Allowance total differs")
        require(near(allowance, active["incidental_allowance_usd"]), "Configured allowance differs")
        require(final["within_reserve"] == (estimate + allowance <= float(active["total_reserve_usd"])),
                "Reserve check differs")
        public.update(stopped_verified=True, stopped_observed_utc=stamp(final["stopped_observed_utc"]).isoformat(),
                      elapsed_to_stopped_observation_seconds=elapsed, configured_compute_usd_per_hour=rate,
                      approximate_compute_usd=estimate, host_time_cap_observed=bool(final["host_time_cap_observed"]),
                      within_per_attempt_reserve=bool(final["within_reserve"]),
                      incidental_budget_allowance_usd=allowance, allowance_is_measured_spending=False,
                      watchdog_removed_after_stop=final["watchdog_cleanup"] == "deleted_own_schedule_after_stopped",
                      controller_command_failed=bool(final["gate_failed"]))
    outputs, output_records = {}, {}
    if "collection" in execution:
        pack = attempt_dir / "result.tar.gz"
        pack_sha = digest(pack)
        marker = (attempt_dir / "result.sha256").read_text().strip()
        require(pack_sha == marker == execution["collection"]["transport_sha256"], "Output transport checksum mismatch")
        require(pack.stat().st_size == execution["collection"]["transport_bytes"], "Output transport size mismatch")
        outputs, output_records = archive_inventory(pack, OUTPUT_JSON)
        bindings.update(output_archive_sha256=pack_sha, output_archive_bytes=pack.stat().st_size,
                        output_checksum_marker_sha256=digest(attempt_dir / "result.sha256"))
        public["output_receipt_sha256"] = {PurePosixPath(name).name: outputs[name] for name in OUTPUT_JSON if name in outputs}
        worker = output_records.get("outputs/WORKER_STATUS.json")
        require(worker == execution["collection"].get("worker"), "Collected worker receipt differs from archive")
        completed = bool(worker and worker.get("status") == "COMPLETE")
        require(completed == execution["scientific_completion"], "Scientific completion summary differs")
        public.update(scientific_completion_worker_reported=completed,
                      normal_phase_freeze_present="outputs/NORMAL_FREEZE.json" in outputs,
                      partial_attack_results_present="outputs/ATTACK_RESULTS.partial.json" in outputs)
        if completed:
            public["outcome"] = "WORKER_COMPLETED"
    code = poll.get("response_code") if poll else None
    if code is not None:
        public["command_exit_code"] = int(code)
    if code == 124 and not public["scientific_completion_worker_reported"]:
        public["outcome"] = ("BOUNDED_WORKER_TIMEOUT_WITH_PARTIAL_SCIENCE" if "outputs/RUN_STATUS.json" in outputs
                             else "COMMAND_TIMEOUT_WITHOUT_COLLECTED_WORKER_EVIDENCE")
    failure_text = (poll or {}).get("stderr", "")
    bootstrap_failure = (code == 1 and "sha256sum: bundle.tar.gz: No such file or directory" in failure_text
                         and "outputs/WORKER_EXIT.txt: No such file or directory" in failure_text)
    if bootstrap_failure:
        require(not outputs and "collection" not in execution, "Bootstrap failure unexpectedly has scientific output")
        public.update(outcome="BOOTSTRAP_STORAGE_FAILURE_BEFORE_WORKER", worker_started=False,
                      storage_mount_change_is_unconfirmed=True)
    elif code not in (None, 0) and "STORAGE GUARD:" in failure_text and not outputs:
        require("collection" not in execution, "Pre-worker storage rejection unexpectedly has scientific output")
        low_space = "needs at least 10 GiB free before creating the run directory" in failure_text
        public["outcome"] = ("BOOTSTRAP_FREE_SPACE_GUARD_BEFORE_WORKER" if low_space else
                             "STORAGE_GUARD_FAILURE_WITHOUT_COLLECTED_WORKER_EVIDENCE")
        if low_space:
            public["required_free_space_bytes"] = 10 * 1024**3
            public["worker_started"] = False
        public["observed_error_text_sha256"] = digest_bytes(failure_text.encode("utf-8"))
    elif "outputs/WORKER_STATUS.json" in outputs:
        public["worker_started"] = True
    if bootstrap_failure:
        public["observed_error_text_sha256"] = digest_bytes(failure_text.encode("utf-8"))
    if (attempt_dir / "BOOT_CONSOLE_PRIVATE.json").exists():
        bindings["private_boot_console_sha256"] = digest(attempt_dir / "BOOT_CONSOLE_PRIVATE.json")
    return public, reuse, outputs


def build(root, through=None, expected_attempts=None, require_closed=False):
    root = Path(root).resolve()
    observed_numbers = [int(path.name[len("cloud_attempt"):]) for path in root.glob("cloud_attempt*")
                        if path.is_dir() and re.fullmatch("cloud_attempt[1-9][0-9]*", path.name)]
    if expected_attempts is None:
        expected_attempts = max([1] + observed_numbers)
    if through is None:
        through = expected_attempts
    require(1 <= through <= expected_attempts, "Invalid completed-through/expected-attempt counts")
    attempts, reuse_states, secrets, first_output_members = [], [], set(), {}
    for number in range(1, expected_attempts + 1):
        if number <= through:
            row, reuse, output_members = summarize_attempt(root, number, secrets)
        else:
            row, reuse, output_members = {"attempt": number, "outcome": "PENDING", "stopped_verified": False}, None, {}
        if number == 1:
            first_output_members = output_members
        attempts.append(row)
        if reuse is not None:
            reuse_states.append((row, reuse))
    original = attempts[0].get("source_freeze", {})
    archive_sha = attempts[0].get("evidence", {}).get("output_archive_sha256")
    for row, reuse in reuse_states:
        require(reuse["transport"]["archive_sha256"] == archive_sha, "Checkpoint source is not attempt 1 archive")
        require(reuse["original_registration_sha256"] == original["original_registration_sha256"],
                "Checkpoint source registration differs")
        require(reuse["transport"]["selected_checkpoint_bytes_compared_to_archive_members"] is True,
                "Checkpoint transport lacks byte verification")
        for member, expected in reuse["transport"]["verified_member_sha256"].items():
            require(first_output_members.get(member) == expected, "Checkpoint-source archive member changed")
        for rel, expected in reuse["inventory"].items():
            require(rel.startswith("checkpoints/"), "Unexpected reusable checkpoint path")
            source_member = "outputs/private/" + rel[len("checkpoints/"):]
            require(first_output_members.get(source_member) == expected,
                    "Reused checkpoint differs from original attempt archive bytes")
        require(reuse["prior_banks_or_results_reused"] is False and reuse["scientific_settings_changed"] is False,
                "Checkpoint source contains forbidden result reuse")
        require(row["source_freeze"]["original_registration_sha256"] == original["original_registration_sha256"],
                "Original experiment differs across attempts")
        require(row["source_freeze"]["original_config_sha256"] == original["original_config_sha256"],
                "Scientific settings differ across attempts")
    if len(reuse_states) > 1:
        require(len({row["source_freeze"]["reuse_manifest_sha256"] for row, _ in reuse_states}) == 1,
                "Retry changed checkpoint selection")
    all_stopped = all(row["stopped_verified"] for row in attempts)
    if require_closed:
        require(all_stopped, "Final closeout requires a verified stopped receipt for every expected attempt")
    measured = [row for row in attempts if row["stopped_verified"]]
    result = {
        "schema": "normal-stability-sanitized-operational-closeout-v1",
        "scope": "DEVELOPMENT_ONLY_OPERATIONAL_EVIDENCE",
        "status": "ALL_ATTEMPTS_VERIFIED_STOPPED" if all_stopped else "DRAFT_PENDING_ATTEMPT_CLOSEOUT",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generator_sha256": digest(__file__),
        "attempts": attempts,
        "checkpoint_source_attempt": 1,
        "original_science_unchanged_across_verified_bundles": bool(reuse_states),
        "expected_attempt_count": expected_attempts,
        "all_expected_attempts_verified_stopped": all_stopped,
        "latest_attempt_worker_completed": attempts[-1].get("scientific_completion_worker_reported", False),
        "closed_attempt_count": len(measured),
        "approximate_compute_usd_for_closed_attempts": sum(row["approximate_compute_usd"] for row in measured),
        "elapsed_seconds_for_closed_attempts": sum(row["elapsed_to_stopped_observation_seconds"] for row in measured),
        "compute_estimate_is_invoice": False,
        "cost_method": "Time from start request to first verified stopped observation, multiplied by the configured hourly rate.",
        "cost_exclusions": ["Persistent storage", "Object storage", "Data transfer", "Other services", "Taxes or billing adjustments"],
        "incidental_allowance_is_not_an_incurred_charge": True,
        "scientific_result_audit": "NOT_PERFORMED_BY_THIS_OPERATIONAL_HELPER",
        "interpretation": "A timeout or bootstrap failure is incomplete execution, not a scientific no-go; worker completion does not establish a positive research result.",
        "privacy": "Only approved operational fields and content hashes are published; cloud identifiers, receipt paths, command text, logs and raw infrastructure responses remain private.",
    }
    serialized = json.dumps(result, sort_keys=True)
    require(not any(secret in serialized for secret in secrets), "Private infrastructure value leaked into public closeout")
    return result


def markdown(result):
    lines = ["# GPU experiment operational closeout", "", "Status: **" + result["status"] + "**.", "",
             "| Attempt | Execution outcome | Verified stopped | Compute estimate |",
             "|---|---|---|---|"]
    for row in result["attempts"]:
        cost = "$%.6f" % row["approximate_compute_usd"] if row["stopped_verified"] else "Pending"
        lines.append(f"| {row['attempt']} | {row['outcome'].replace('_', ' ').lower()} | {'Yes' if row['stopped_verified'] else 'Pending'} | {cost} |")
    lines += ["", "**Estimated compute for verified closed attempts: $%.6f.**" % result["approximate_compute_usd_for_closed_attempts"],
              "This is elapsed-time arithmetic, not an invoice. It includes startup and stopping-observation time and excludes storage, transfer and other services. The $5 incidental allowance per attempt is a budget reserve, not measured spending.", "",
              "Attempt 1 is the sole source of reusable encoder and normal-cache checkpoints. Later attempts preserve the original scientific settings and rebuild all banks, calibration, normal metrics and attack replay. Attempt 2 failed during bootstrap; a startup mount/path change remains an unconfirmed explanation. Attempt 3 was rejected before science because root storage had less than the required 10 GiB free. Earlier evidence and source freezes are retained.", "",
              "The accompanying JSON binds each available execution/controller receipt, source freeze, input bundle and collected output archive by SHA-256. Stop requests alone are insufficient: closure is supported by the controller's observed stopped state, final receipt and matching elapsed-time record. Cloud account, host, storage, role and command identifiers remain private.", "",
              "A timeout or bootstrap failure does not establish scientific no-go. Scientific results, completeness checks and independent result audit belong in the research report; this operational closeout does not infer detector performance.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--through", type=int)
    parser.add_argument("--expected-attempts", type=int)
    parser.add_argument("--require-closed", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "Use a fresh output directory to retain earlier closeout snapshots")
    result = build(args.root, args.through, args.expected_attempts, args.require_closed)
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "AWS_CLOSEOUT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "AWS_CLOSEOUT.md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "closed_attempts": result["closed_attempt_count"],
                      "approximate_compute_usd": result["approximate_compute_usd_for_closed_attempts"]}))


if __name__ == "__main__":
    main()
