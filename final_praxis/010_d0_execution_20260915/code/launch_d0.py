"""Launch one frozen D0 attempt, collect its evidence, and verify host shutdown.

All configuration, generated shell, attempt records, and results remain beside
--settings. The bundle must contain the exact committed protocol/runtime freeze.
This helper never retries inference or provisions infrastructure. Credentials
come from cloud_d0.Controller's normal named AWS profile.
"""
from __future__ import annotations

import argparse
import datetime as dt
import inspect
import json
import math
from pathlib import Path
import re
import shlex
import tempfile
import time
import uuid

import cloud_d0 as cloud


RUNNER = "final_praxis/010_d0_execution_20260915/code/run_cloud.sh"
POLL_SECONDS = 10
BOOT_SECONDS = 240
MIN_SEND_SECONDS = 600
MAX_ARCHIVE_BYTES = 512 * 1024**2
BUNDLE_ASSETS = {
    "assets/source.csv": "e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584",
    "assets/timesfm_source.zip": "ecb62c7cc793937991bbaf4a481d60ac74e84724db3e9d6ea457b2b350f11692",
}


def emit(event, **fields):
    print(json.dumps({"event": event, **fields}, default=str), flush=True)


def safe_extract(archive_path, destination, required_prefix=None, allowed_roots=None, required_files=None):
    """Extract only bounded regular files/directories, without following links.

    Kept self-contained so the identical code can run on the Linux bootstrap.
    Validation completes before any archive content is written.
    """
    import hashlib
    import os
    from pathlib import Path, PurePosixPath
    import shutil
    import tarfile

    root = Path(destination).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Archive destination must be empty")
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(member.size for member in members) > 2 * 1024**3:
            raise ValueError("Archive exceeds the file-count or unpacked-size limit")
        names = set()
        directories = set()
        validated = []
        for member in members:
            name = member.name.rstrip("/")
            parts = name.split("/")
            if not name or "\\" in name or ":" in name or any(part in {"", ".", ".."} for part in parts):
                raise ValueError("Unsafe archive path")
            if PurePosixPath(name).is_absolute() or not (member.isdir() or member.isfile()):
                raise ValueError("Archive links, special files, and absolute paths are prohibited")
            if member.size < 0:
                raise ValueError("Negative archive member size")
            if name in names:
                raise ValueError("Duplicate archive path")
            if required_prefix is not None and not (name == required_prefix or name.startswith(required_prefix + "/")):
                raise ValueError("Unexpected archive root")
            if allowed_roots is not None and parts[0] not in allowed_roots:
                raise ValueError("Unexpected archive root")
            target = root.joinpath(*parts)
            if not target.resolve().is_relative_to(root):
                raise ValueError("Archive path escapes destination")
            names.add(name)
            if member.isdir():
                directories.add(name)
            validated.append((member, target))
        for name in required_files or {}:
            if name not in names or name in directories:
                raise ValueError("Required pinned archive file is missing")
        for name in names:
            for parent in PurePosixPath(name).parents:
                parent_name = parent.as_posix()
                if parent_name in names and parent_name not in directories:
                    raise ValueError("Archive file conflicts with a directory")
        for member, target in validated:
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open("xb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
            os.chmod(target, 0o700 if member.mode & 0o111 else 0o600)
        for name, expected_hash in (required_files or {}).items():
            with root.joinpath(*name.split("/")).open("rb") as handle:
                actual_hash = hashlib.sha256()
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    actual_hash.update(block)
            if actual_hash.hexdigest() != expected_hash:
                raise ValueError("Required pinned archive file hash mismatch")
    return sorted(names)


def validate_bundle(bundle, expected_sha, protocol, freeze, private):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha):
        raise ValueError("--bundle-sha256 requires a 64-digit hexadecimal SHA-256")
    expected_sha = expected_sha.lower()
    bundle = Path(bundle).resolve(strict=True)
    if bundle.stat().st_size > MAX_ARCHIVE_BYTES or cloud.digest(bundle) != expected_sha:
        raise ValueError("Bundle size or SHA-256 validation failed")
    identities = {"protocol": cloud.committed_identity(protocol), "freeze": cloud.committed_identity(freeze)}
    if identities["protocol"]["commit"] != identities["freeze"]["commit"]:
        raise ValueError("Protocol and freeze must be from the same Git HEAD")
    with tempfile.TemporaryDirectory(prefix="bundle-review-", dir=private) as temporary:
        files = safe_extract(bundle, temporary, allowed_roots=("final_praxis", "assets"), required_files=BUNDLE_ASSETS)
        asset_files = {name for name in files if name.startswith("assets/") and (Path(temporary) / name).is_file()}
        if asset_files != set(BUNDLE_ASSETS):
            raise ValueError("Bundle assets must be exactly the pinned source CSV and ZIP")
        for key in ("protocol", "freeze"):
            archived = Path(temporary) / identities[key]["path"]
            if not archived.is_file() or cloud.digest(archived) != identities[key]["sha256"]:
                raise ValueError("Bundle does not contain the exact committed " + key)
        runner = Path(temporary) / RUNNER
        if not runner.is_file() or b"\r" in runner.read_bytes():
            raise ValueError("Bundle requires an LF-only run_cloud.sh at the prescribed path")
    return {"bundle_sha256": expected_sha, "bundle_bytes": bundle.stat().st_size,
            "bundle_entries": len(files), "identities": identities}


def timeout_plan(started, now):
    deadline = cloud.parse_stamp(started["worker_deadline_utc"])
    remaining = (deadline - now).total_seconds()
    # Twenty extra seconds leave room for Controller.send's final read-only APIs.
    send_seconds = min(cloud.MAX_COMMAND_SECONDS, math.floor(remaining - 130) - 20)
    outer_seconds = min(send_seconds - 30, math.floor(remaining - 160) - 20)
    if send_seconds < MIN_SEND_SECONDS or outer_seconds < MIN_SEND_SECONDS - 30:
        raise ValueError("Insufficient absolute-deadline budget for cold setup and the complete screen")
    outer_stop = min(math.floor(now.timestamp()) + outer_seconds, math.floor(deadline.timestamp()) - 160)
    return {"send_seconds": send_seconds, "outer_seconds": outer_seconds,
            "controller_deadline_epoch": math.floor(deadline.timestamp()),
            # run_cloud.sh reserves its 160-second audit/publication margin
            # relative to this actual outer timeout, not the later SSM deadline.
            "deadline_epoch": outer_stop,
            # Fixed before send; delivery delays consume this budget on the host.
            "outer_stop_epoch": outer_stop}


def build_bootstrap(settings, active, timing, bundle_sha):
    run_id = active["run_id"]
    if not re.fullmatch(r"[0-9a-f]{32}", run_id) or not re.fullmatch(r"[0-9a-f]{64}", bundle_sha):
        raise ValueError("Invalid immutable bootstrap identity")
    runroot = "/opt/dlami/nvme/praxis-d0-" + run_id
    bundle_uri = "s3://" + settings["bucket"] + "/" + settings["prefix"] + "bundle/D0_RUNTIME.tar.gz"
    sha_uri = "s3://" + settings["bucket"] + "/" + settings["prefix"] + "bundle/D0_RUNTIME.sha256"
    result_uri = "s3://" + settings["bucket"] + "/" + settings["prefix"] + "results"
    extraction_source = inspect.getsource(safe_extract)
    # Every variable assignment containing settings is shell-quoted as data.
    assignments = "\n".join([
        "export D0_RUNROOT=" + shlex.quote(runroot),
        "export D0_PERSIST_ROOT=" + shlex.quote("/var/lib/praxis-d0-evidence/" + run_id),
        "export D0_S3_RESULT_PREFIX=" + shlex.quote(result_uri),
        "export D0_DEADLINE_EPOCH=" + str(timing["deadline_epoch"]),
        "export AWS_DEFAULT_REGION=" + shlex.quote(settings["region"]),
        "D0_OUTER_STOP_EPOCH=" + str(timing["outer_stop_epoch"]),
        "export D0_BUNDLE_URI=" + shlex.quote(bundle_uri),
        "export D0_BUNDLE_SHA_URI=" + shlex.quote(sha_uri),
        "export D0_EXPECTED_BUNDLE_SHA=" + shlex.quote(bundle_sha),
    ])
    return """bash -s <<'D0_BOOTSTRAP'
set -Eeuo pipefail
bootstrap_finish() {
  code=$?
  trap - EXIT TERM INT
  set +e
  echo "D0 bootstrap exit=$code; scheduling guest stop in one minute"
  /sbin/shutdown -h +1
  exit "$code"
}
trap bootstrap_finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
""" + assignments + """
remaining=$((D0_OUTER_STOP_EPOCH - $(date -u +%s)))
if [ "$remaining" -lt 30 ]; then echo 'D0 bootstrap arrived after its deadline'; exit 75; fi
timeout --signal=TERM --kill-after=20 "$remaining" bash -s <<'D0_PAYLOAD'
set -Eeuo pipefail
test "$(readlink -f /opt/dlami/nvme)" = /opt/dlami/nvme
mountpoint -q /opt/dlami/nvme
available=$(df -B1 --output=avail /opt/dlami/nvme | tail -n 1 | tr -d ' ')
case "$available" in ''|*[!0-9]*) echo 'Invalid disk availability'; exit 74;; esac
if [ "$available" -lt 12884901888 ]; then echo 'D0 needs at least 12 GiB free NVMe space'; exit 74; fi
test ! -e "$D0_RUNROOT"
mkdir -m 700 -- "$D0_RUNROOT"
mkdir -m 700 -- "$D0_RUNROOT/staging" "$D0_RUNROOT/extracted" "$D0_RUNROOT/tmp"
export TMPDIR="$D0_RUNROOT/tmp"
aws s3 cp "$D0_BUNDLE_URI" "$D0_RUNROOT/staging/bundle.tar.gz" --only-show-errors
aws s3 cp "$D0_BUNDLE_SHA_URI" "$D0_RUNROOT/staging/bundle.sha256" --only-show-errors
test "$(tr -d '\\r\\n' < "$D0_RUNROOT/staging/bundle.sha256")" = "$D0_EXPECTED_BUNDLE_SHA"
printf '%s  %s\\n' "$D0_EXPECTED_BUNDLE_SHA" "$D0_RUNROOT/staging/bundle.tar.gz" | sha256sum -c -
python3 - "$D0_RUNROOT/staging/bundle.tar.gz" "$D0_RUNROOT/extracted" <<'D0_SAFE_EXTRACT'
""" + extraction_source + """
import sys
safe_extract(sys.argv[1], sys.argv[2], allowed_roots=('final_praxis', 'assets'), required_files=""" + repr(BUNDLE_ASSETS) + """)
D0_SAFE_EXTRACT
export D0_RUNROOT="$D0_RUNROOT/extracted"
bash "$D0_RUNROOT/final_praxis/010_d0_execution_20260915/code/run_cloud.sh"
D0_PAYLOAD
D0_BOOTSTRAP
"""


def object_exists(controller, key):
    from botocore.exceptions import ClientError
    try:
        controller.client("s3").head_object(Bucket=controller.settings["bucket"], Key=key)
        return True
    except ClientError as error:
        if str(error.response.get("Error", {}).get("Code")) in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def verify_stop_role(controller):
    """Optional read-only IAM check in addition to controller target verification."""
    settings = controller.settings
    role_name = settings["stop_role_arn"].rsplit("/", 1)[-1]
    iam = controller.client("iam")
    role = iam.get_role(RoleName=role_name)["Role"]
    if role["Arn"] != settings["stop_role_arn"]:
        raise ValueError("Stop-role ARN mismatch")
    trusted = False
    for statement in role["AssumeRolePolicyDocument"].get("Statement", []):
        principal = statement.get("Principal", {})
        services = principal.get("Service", []) if isinstance(principal, dict) else []
        services = [services] if isinstance(services, str) else services
        actions = statement.get("Action", [])
        actions = [actions] if isinstance(actions, str) else actions
        trusted |= statement.get("Effect") == "Allow" and "scheduler.amazonaws.com" in services and "sts:AssumeRole" in actions
    if not trusted:
        raise ValueError("Existing stop role does not explicitly trust EventBridge Scheduler")
    resource = "arn:aws:ec2:" + settings["region"] + ":" + settings["account"] + ":instance/" + settings["instance"]
    decisions = iam.simulate_principal_policy(PolicySourceArn=settings["stop_role_arn"],
        ActionNames=["ec2:StopInstances"], ResourceArns=[resource])["EvaluationResults"]
    if len(decisions) != 1 or decisions[0]["EvalDecision"] != "allowed" or decisions[0].get("MissingContextValues"):
        raise ValueError("IAM simulation does not allow the selected instance stop")
    return controller.record("stop_role_review", {"status": "READ_ONLY_ROLE_CHECK_PASSED",
        "scope": "Explicit Scheduler trust and simulated selected-host StopInstances; live AWS execution remains external"})


def wait_until_online(controller, clock=cloud.utc_now, sleeper=time.sleep):
    active = controller.active()
    deadline = cloud.parse_stamp(active["start_request_utc"]) + dt.timedelta(seconds=BOOT_SECONDS)
    while clock() < deadline:
        record = controller.status()
        receipt = json.loads(Path(record["receipt"]).read_text(encoding="utf-8"))
        online = any(value["ping"] == "Online" for value in receipt["ssm"])
        emit("boot_status", instance_state=receipt["instance_state"], ssm_online=online)
        if receipt["instance_state"] == "running" and online:
            return
        if receipt["instance_state"] in {"stopping", "shutting-down", "terminated"}:
            raise ValueError("Selected host stopped before worker submission")
        sleeper(min(POLL_SECONDS, max(0, (deadline - clock()).total_seconds())))
    raise TimeoutError("SSM was not Online within four minutes of start request")


def monitor(controller, command_id, clock=cloud.utc_now, sleeper=time.sleep):
    from botocore.exceptions import ClientError
    active = controller.active()
    deadline = cloud.parse_stamp(active["worker_deadline_utc"])
    marker_key = controller.settings["prefix"] + "results/results.sha256"
    while clock() < deadline:
        if object_exists(controller, marker_key):
            emit("result_marker_published")
            return {"marker_seen": True, "ssm_status": "marker_precedes_terminal_poll"}
        try:
            record = controller.poll(command_id)
            emit("worker_status", status=record["status"], response_code=record.get("response_code"))
            if record["status"] in cloud.TERMINAL_STATES:
                return {"marker_seen": object_exists(controller, marker_key), "ssm_status": record["status"],
                        "response_code": record.get("response_code")}
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "InvocationDoesNotExist":
                raise
            emit("worker_status", status="awaiting_ssm_invocation")
        sleeper(min(POLL_SECONDS, max(0, (deadline - clock()).total_seconds())))
    return {"marker_seen": object_exists(controller, marker_key), "ssm_status": "ABSOLUTE_WORKER_DEADLINE_REACHED"}


def close_host(controller, clock=cloud.utc_now, sleeper=time.sleep):
    """Stop promptly, then observe STOPPED; keep the watchdog if AWS is unavailable."""
    active = controller.active()
    # A late API outage is reported, never represented as a successful closeout.
    limit = max(cloud.parse_stamp(active["total_deadline_utc"]) + dt.timedelta(seconds=180),
                clock() + dt.timedelta(seconds=180))
    last_stop = None
    while clock() < limit:
        try:
            if last_stop is None or (clock() - last_stop).total_seconds() >= 60:
                record = controller.stop()
                last_stop = clock()
                emit("stop_requested", **record)
            record = controller.finalize()
            emit("closeout_status", **record)
            if record["status"] == "CLOSED_VERIFIED_STOPPED":
                return record
        except Exception as error:
            emit("closeout_retry", error_type=type(error).__name__, watchdog="retained")
        sleeper(POLL_SECONDS)
    return controller.record("launch_closeout", {"status": "HOLD_STOPPED_STATE_UNVERIFIED_WATCHDOG_RETAINED"})


def collect_results(controller):
    prefix = controller.settings["prefix"] + "results/"
    if not object_exists(controller, prefix + "results.sha256"):
        return controller.record("collection", {"status": "NO_PUBLISHED_RESULT_MARKER"})
    marker = controller.private / "results.sha256"
    archive = controller.private / "results.tar.gz"
    target = controller.private / "collected"
    controller.transfer("download", marker, prefix + "results.sha256")
    expected = marker.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Malformed published SHA-256 marker")
    head = controller.client("s3").head_object(Bucket=controller.settings["bucket"], Key=prefix + "results.tar.gz")
    if head["ContentLength"] > MAX_ARCHIVE_BYTES:
        raise ValueError("Result archive exceeds size limit")
    controller.transfer("download", archive, prefix + "results.tar.gz")
    if cloud.digest(archive) != expected:
        raise ValueError("Published result archive SHA-256 mismatch")
    files = safe_extract(archive, target, required_prefix="output")
    manifest = {path.relative_to(target).as_posix(): {"sha256": cloud.digest(path), "bytes": path.stat().st_size}
                for path in sorted(target.rglob("*")) if path.is_file()}
    supervisor = target / "output/SUPERVISOR_EXIT.txt"
    supervisor_exit = supervisor.read_text(encoding="ascii").strip() if supervisor.is_file() else None
    return controller.record("collection", {"status": "RESULTS_HASH_VERIFIED_AND_COLLECTED",
        "archive_sha256": expected, "archive_bytes": archive.stat().st_size, "entries": len(files),
        "directory": str(target), "supervisor_exit": supervisor_exit, "files": manifest,
        "scope": "Transport and extraction verification; scientific audit and interpretation remain separate"})


def launch(args):
    controller = cloud.Controller(args.settings)
    if controller.active_path.exists() or (controller.private / "LAUNCH_ATTEMPT.json").exists():
        raise ValueError("This private execution directory already has an attempt; automatic reruns are prohibited")
    controller.verify_account()
    if controller.instance()["State"]["Name"] != "stopped":
        raise ValueError("Selected host must be stopped before launch preparation")
    if args.verify_stop_role:
        emit("stop_role_review", **verify_stop_role(controller))
    review = validate_bundle(args.bundle, args.bundle_sha256, args.protocol, args.freeze, controller.private)
    if object_exists(controller, controller.settings["prefix"] + "results/results.sha256"):
        raise ValueError("Result marker already exists in this prefix; stale evidence cannot be reused")
    attempt = {"attempt_id": uuid.uuid4().hex, "created_utc": cloud.stamp(cloud.utc_now()),
               "stage": "preflight_passed", "bundle_review": review, "cloud_start_attempted": False}
    attempt_path = controller.private / "LAUNCH_ATTEMPT.json"
    # An exclusive lock also prevents two launch helpers targeting this directory.
    with attempt_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(attempt, indent=2) + "\n")

    def save_attempt():
        attempt_path.write_text(json.dumps(attempt, indent=2, default=str) + "\n", encoding="utf-8")

    start_attempted = False
    failure = None
    try:
        checksum = controller.private / "D0_RUNTIME.sha256"
        checksum.write_text(review["bundle_sha256"] + "\n", encoding="ascii")
        emit("bundle_uploaded", **controller.transfer("upload", args.bundle, controller.settings["prefix"] + "bundle/D0_RUNTIME.tar.gz"))
        emit("bundle_hash_uploaded", **controller.transfer("upload", checksum, controller.settings["prefix"] + "bundle/D0_RUNTIME.sha256"))
        # Recheck before entering finally-owned start handling.
        if controller.active_path.exists():
            raise ValueError("A separate controller created an active run during staging")
        start_attempted = True
        attempt["cloud_start_attempted"] = True
        attempt["stage"] = "starting"
        save_attempt()
        emit("host_start", **controller.start(args.protocol, args.freeze))
        wait_until_online(controller)
        active = controller.active()
        timing = timeout_plan(active, cloud.utc_now())
        script = controller.private / "bootstrap_d0.sh"
        script.write_text(build_bootstrap(controller.settings, active, timing, review["bundle_sha256"]), encoding="utf-8", newline="\n")
        attempt.update(stage="submitting_worker", timing=timing, bootstrap_sha256=cloud.digest(script))
        save_attempt()
        submitted = controller.send(script, timing["send_seconds"])
        emit("worker_submitted", **submitted)
        attempt.update(stage="monitoring", command_id=submitted["command_id"])
        save_attempt()
        attempt["monitor"] = monitor(controller, submitted["command_id"])
    except BaseException as error:
        failure = error
        attempt.update(stage="failure", failure_type=type(error).__name__)
        emit("launch_failure", error_type=type(error).__name__)
    finally:
        if start_attempted and controller.active_path.exists():
            try:
                attempt["closeout"] = close_host(controller)
            except BaseException as error:
                attempt["closeout"] = {"status": "HOLD_CLOSEOUT_UNVERIFIED_WATCHDOG_RETAINED", "error_type": type(error).__name__}
                emit("closeout_failure", **attempt["closeout"])
        save_attempt()
    # Download after verified stop, so transfer or local extraction cannot extend
    # billed host time. A failed scientific run is still collected if published.
    try:
        if start_attempted:
            attempt["collection"] = collect_results(controller)
    except Exception as error:
        attempt["collection"] = {"status": "HOLD_COLLECTION_FAILED", "error_type": type(error).__name__}
        emit("collection_failure", error_type=type(error).__name__)
        if failure is None:
            failure = error
    attempt["completed_utc"] = cloud.stamp(cloud.utc_now())
    closed = attempt.get("closeout", {}).get("status") == "CLOSED_VERIFIED_STOPPED"
    collected = attempt.get("collection", {}).get("status") == "RESULTS_HASH_VERIFIED_AND_COLLECTED"
    supervisor_path = controller.private / "collected/output/SUPERVISOR_EXIT.txt"
    supervisor_ok = supervisor_path.is_file() and supervisor_path.read_text(encoding="ascii").strip() == "0"
    within_caps = attempt.get("closeout", {}).get("host_time_cap_observed") and attempt.get("closeout", {}).get("within_reserve")
    attempt["stage"] = "CLOSED_EVIDENCE_COLLECTED" if closed and collected else "HOLD_INCOMPLETE"
    attempt["supervisor_success"] = supervisor_ok
    attempt["overall_operational_pass"] = bool(failure is None and closed and collected and supervisor_ok and within_caps
                                               and not attempt.get("closeout", {}).get("gate_failed"))
    save_attempt()
    emit("launch_complete", status=attempt["stage"], operational_pass=attempt["overall_operational_pass"],
         attempt_record=str(attempt_path), supervisor_success=supervisor_ok,
         scientific_result="Requires independent saved-array audit and interpretation")
    return 0 if attempt["overall_operational_pass"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--bundle-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--verify-stop-role", action="store_true", help="Read-only IAM trust and StopInstances simulation")
    args = parser.parse_args()
    try:
        return launch(args)
    except BaseException as error:
        emit("launcher_error", error_type=type(error).__name__,
             message=str(error) if isinstance(error, (ValueError, FileNotFoundError)) else "Review private receipts and AWS session state")
        return 130 if isinstance(error, KeyboardInterrupt) else 1


if __name__ == "__main__":
    raise SystemExit(main())
