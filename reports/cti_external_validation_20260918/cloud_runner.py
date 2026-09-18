"""Prepare, or explicitly launch, one frozen CTI attempt and verify shutdown.

All configuration, generated shell, attempt records, and results remain beside
--settings. The bundle must contain the exact committed protocol/runtime freeze.
This helper never retries inference or provisions infrastructure. Credentials
come from cti_cloud_controller.Controller's normal named AWS profile.
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

import cti_cloud_controller as cloud


RUNNER = "reports/cti_external_validation_20260918/run_cloud.sh"
POLL_SECONDS = 10
BOOT_SECONDS = 240
MIN_SEND_SECONDS = 600
MAX_ARCHIVE_BYTES = 512 * 1024**2
RUNTIME_ROOT = "reports/cti_external_validation_20260918"
WORKER = RUNTIME_ROOT + "/inference_worker.py"
CONTROLLER_SHA256 = "75a43e4c62233b62a04768ec1366b9a9a54d34b685337116b6dc830b390473f4"
PROVENANCE_CONTROLLER_SHA256 = "b1739c6fa9b8cac8bf8740f4fe2b2cde140cede5eae3125ed36de86419f32257"



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
    """Validate all committed runtime/input bytes, then reject extra archive files."""
    if cloud.digest(Path(cloud.__file__)) != CONTROLLER_SHA256:
        raise ValueError("CTI controller bytes differ from the reviewed adaptation")
    if cloud.digest(Path(__file__).with_name("trusted_cloud_controller.py")) != PROVENANCE_CONTROLLER_SHA256:
        raise ValueError("Original controller provenance bytes differ from the reviewed source")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha):
        raise ValueError("--bundle-sha256 requires a hexadecimal SHA-256")
    expected_sha = expected_sha.lower()
    bundle = Path(bundle).resolve(strict=True)
    if bundle.stat().st_size > MAX_ARCHIVE_BYTES or cloud.digest(bundle) != expected_sha:
        raise ValueError("Bundle size or SHA-256 validation failed")
    identities = {"protocol": cloud.committed_identity(protocol), "freeze": cloud.committed_identity(freeze)}
    if identities["protocol"]["commit"] != identities["freeze"]["commit"]:
        raise ValueError("Protocol and freeze must be from the same Git HEAD")
    frozen = json.loads(Path(freeze).read_text(encoding="utf-8"))
    hashes = frozen.get("files")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Freeze must contain a nonempty files mapping")
    hashes = {name: value.get("sha256") if isinstance(value, dict) else value for name, value in hashes.items()}
    for name, value in hashes.items():
        if not isinstance(name, str) or "\\" in name or ":" in name or any(p in {"", ".", ".."} for p in name.split("/")):
            raise ValueError("Frozen paths must be safe repository-relative paths")
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Frozen file SHA-256 must be lowercase hexadecimal")
    required = {RUNNER, WORKER, RUNTIME_ROOT + "/cloud_runner.py", RUNTIME_ROOT + "/cti_cloud_controller.py",
                RUNTIME_ROOT + "/trusted_cloud_controller.py"}
    if not required <= set(hashes):
        raise ValueError("Freeze must pin launcher, both controllers, supervisor, and inference worker")
    worker_args = frozen.get("worker_args")
    if not isinstance(worker_args, list) or len(worker_args) != 4 or worker_args[::2] != ["--inputs", "--qualification"]:
        raise ValueError("Frozen worker_args must be --inputs PATH --qualification PATH")
    if any(not isinstance(p, str) or p not in hashes for p in worker_args[1::2]):
        raise ValueError("Worker inputs must be pinned bundle files")
    # Derive the repo through the already verified committed protocol.
    repo = Path(protocol).resolve()
    for _ in identities["protocol"]["path"].split("/"):
        repo = repo.parent
    for name, expected in hashes.items():
        ident = cloud.committed_identity(repo / name)
        if ident["commit"] != identities["freeze"]["commit"] or ident["sha256"] != expected:
            raise ValueError("Runtime/input file differs from committed freeze: " + name)
    if cloud.digest(Path(__file__)) != hashes[RUNTIME_ROOT + "/cloud_runner.py"]:
        raise ValueError("Executing launcher differs from frozen launcher")
    hashes.update({ident["path"]: ident["sha256"] for ident in identities.values()})
    with tempfile.TemporaryDirectory(prefix="bundle-review-", dir=private) as temporary:
        files = safe_extract(bundle, temporary, allowed_roots=("reports",), required_files=hashes)
        actual_files = {name for name in files if (Path(temporary) / name).is_file()}
        if actual_files != set(hashes):
            raise ValueError("Bundle regular files must exactly equal the frozen manifest plus protocol/freeze")
        if b"\r" in (Path(temporary) / RUNNER).read_bytes():
            raise ValueError("Supervisor must use LF line endings")
    return {"bundle_sha256": expected_sha, "bundle_bytes": bundle.stat().st_size,
            "bundle_entries": len(files), "identities": identities,
            "required_files": hashes, "freeze_path": identities["freeze"]["path"],
            "worker_args": worker_args, "controller_sha256": CONTROLLER_SHA256,
            "provenance_controller_sha256": PROVENANCE_CONTROLLER_SHA256}


def timeout_plan(started, now):
    deadline = cloud.parse_stamp(started["worker_deadline_utc"])
    remaining = (deadline - now).total_seconds()
    # Twenty extra seconds leave room for Controller.send's final read-only APIs.
    send_seconds = min(cloud.MAX_COMMAND_SECONDS, math.floor(remaining - 130) - 20)
    outer_seconds = min(send_seconds - 30, math.floor(remaining - 160) - 20)
    if send_seconds < MIN_SEND_SECONDS or outer_seconds < MIN_SEND_SECONDS - 30:
        raise ValueError("Insufficient absolute-deadline budget for bounded setup and inference")
    outer_stop = min(math.floor(now.timestamp()) + outer_seconds, math.floor(deadline.timestamp()) - 160)
    return {"send_seconds": send_seconds, "outer_seconds": outer_seconds,
            "controller_deadline_epoch": math.floor(deadline.timestamp()),
            # run_cloud.sh reserves its 160-second evidence/publication margin
            # relative to this actual outer timeout, not the later SSM deadline.
            "deadline_epoch": outer_stop,
            # Fixed before send; delivery delays consume this budget on the host.
            "outer_stop_epoch": outer_stop}


def build_bootstrap(settings, active, timing, bundle_sha, review):
    run_id = active["run_id"]
    if not re.fullmatch(r"[0-9a-f]{32}", run_id) or not re.fullmatch(r"[0-9a-f]{64}", bundle_sha):
        raise ValueError("Invalid immutable bootstrap identity")
    runroot = "/opt/dlami/nvme/praxis-cti-" + run_id
    bundle_uri = "s3://" + settings["bucket"] + "/" + settings["prefix"] + "bundle/CTI_RUNTIME.tar.gz"
    sha_uri = "s3://" + settings["bucket"] + "/" + settings["prefix"] + "bundle/CTI_RUNTIME.sha256"
    result_uri = "s3://" + settings["bucket"] + "/" + settings["prefix"] + "results"
    extraction_source = inspect.getsource(safe_extract)
    # Every variable assignment containing settings is shell-quoted as data.
    assignments = "\n".join([
        "export CTI_RUNROOT=" + shlex.quote(runroot),
        "export CTI_FREEZE_REL=" + shlex.quote(review["freeze_path"]),
        "export CTI_HF_SECRET_ID=" + shlex.quote(settings["hf_secret_id"]),
        "export CTI_PERSIST_ROOT=" + shlex.quote("/var/lib/praxis-cti-evidence/" + run_id),
        "export CTI_S3_RESULT_PREFIX=" + shlex.quote(result_uri),
        "export CTI_DEADLINE_EPOCH=" + str(timing["deadline_epoch"]),
        "export AWS_DEFAULT_REGION=" + shlex.quote(settings["region"]),
        "CTI_OUTER_STOP_EPOCH=" + str(timing["outer_stop_epoch"]),
        "export CTI_BUNDLE_URI=" + shlex.quote(bundle_uri),
        "export CTI_BUNDLE_SHA_URI=" + shlex.quote(sha_uri),
        "export CTI_EXPECTED_BUNDLE_SHA=" + shlex.quote(bundle_sha),
    ])
    return """bash -s <<'CTI_BOOTSTRAP'
set -Eeuo pipefail
bootstrap_finish() {
  code=$?
  trap - EXIT TERM INT
  set +e
  echo "CTI bootstrap exit=$code; scheduling guest stop in one minute"
  /sbin/shutdown -h +1
  exit "$code"
}
trap bootstrap_finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
""" + assignments + """
remaining=$((CTI_OUTER_STOP_EPOCH - $(date -u +%s)))
if [ "$remaining" -lt 30 ]; then echo 'CTI bootstrap arrived after its deadline'; exit 75; fi
timeout --signal=TERM --kill-after=20 "$remaining" bash -s <<'CTI_PAYLOAD'
set -Eeuo pipefail
test "$(readlink -f /opt/dlami/nvme)" = /opt/dlami/nvme
mountpoint -q /opt/dlami/nvme
available=$(df -B1 --output=avail /opt/dlami/nvme | tail -n 1 | tr -d ' ')
case "$available" in ''|*[!0-9]*) echo 'Invalid disk availability'; exit 74;; esac
if [ "$available" -lt 68719476736 ]; then echo 'CTI needs at least 64 GiB free NVMe space'; exit 74; fi
test ! -e "$CTI_RUNROOT"
mkdir -m 700 -- "$CTI_RUNROOT"
mkdir -m 700 -- "$CTI_RUNROOT/staging" "$CTI_RUNROOT/extracted" "$CTI_RUNROOT/tmp"
export TMPDIR="$CTI_RUNROOT/tmp"
aws s3 cp "$CTI_BUNDLE_URI" "$CTI_RUNROOT/staging/bundle.tar.gz" --only-show-errors
aws s3 cp "$CTI_BUNDLE_SHA_URI" "$CTI_RUNROOT/staging/bundle.sha256" --only-show-errors
test "$(tr -d '\\r\\n' < "$CTI_RUNROOT/staging/bundle.sha256")" = "$CTI_EXPECTED_BUNDLE_SHA"
printf '%s  %s\\n' "$CTI_EXPECTED_BUNDLE_SHA" "$CTI_RUNROOT/staging/bundle.tar.gz" | sha256sum -c -
python3 - "$CTI_RUNROOT/staging/bundle.tar.gz" "$CTI_RUNROOT/extracted" <<'CTI_SAFE_EXTRACT'
""" + extraction_source + """
import sys
safe_extract(sys.argv[1], sys.argv[2], allowed_roots=('reports',), required_files=""" + repr(review['required_files']) + """)
CTI_SAFE_EXTRACT
export CTI_RUNROOT="$CTI_RUNROOT/extracted"
bash "$CTI_RUNROOT/reports/cti_external_validation_20260918/run_cloud.sh"
CTI_PAYLOAD
CTI_BOOTSTRAP
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
    """Read-only IAM check in addition to controller target verification."""
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


def collect_partial_results(controller):
    """Retain checkpoints after failed publication, without calling them complete."""
    prefix = controller.settings["prefix"] + "results/partial/"
    objects = []
    pages = controller.client("s3").get_paginator("list_objects_v2")
    for page in pages.paginate(Bucket=controller.settings["bucket"], Prefix=prefix):
        objects.extend(page.get("Contents", []))
        if len(objects) > 1000 or sum(item["Size"] for item in objects) > MAX_ARCHIVE_BYTES:
            raise ValueError("Partial evidence exceeds collection limit")
    if not objects:
        return controller.record("collection", {"status": "NO_PUBLISHED_RESULT_MARKER_OR_CHECKPOINTS"})
    target = controller.private / "partial_collected"
    target.mkdir(exist_ok=False)
    manifest = {}
    for item in objects:
        name = item["Key"][len(prefix):]
        if not name or "\\" in name or ":" in name or any(part in {"", ".", ".."} for part in name.split("/")):
            raise ValueError("Unsafe partial-evidence object path")
        path = target.joinpath(*name.split("/"))
        if not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("Partial-evidence object escaped destination")
        controller.transfer("download", path, item["Key"])
        manifest[name] = {"sha256": cloud.digest(path), "bytes": path.stat().st_size}
    return controller.record("collection", {"status": "PARTIAL_EVIDENCE_COLLECTED_NO_FINAL_MARKER",
        "directory": str(target), "files": manifest,
        "scope": "Checkpoint JSONL may have an incomplete final line; no completeness or scientific success implied"})


def collect_results(controller):
    prefix = controller.settings["prefix"] + "results/"
    if not object_exists(controller, prefix + "results.sha256"):
        return collect_partial_results(controller)
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
    files = safe_extract(archive, target, required_prefix="outputs")
    manifest = {path.relative_to(target).as_posix(): {"sha256": cloud.digest(path), "bytes": path.stat().st_size}
                for path in sorted(target.rglob("*")) if path.is_file()}
    supervisor = target / "outputs/SUPERVISOR_EXIT.txt"
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
        checksum = controller.private / "CTI_RUNTIME.sha256"
        checksum.write_text(review["bundle_sha256"] + "\n", encoding="ascii")
        emit("bundle_uploaded", **controller.transfer("upload", args.bundle, controller.settings["prefix"] + "bundle/CTI_RUNTIME.tar.gz"))
        emit("bundle_hash_uploaded", **controller.transfer("upload", checksum, controller.settings["prefix"] + "bundle/CTI_RUNTIME.sha256"))
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
        script = controller.private / "bootstrap_cti.sh"
        script.write_text(build_bootstrap(controller.settings, active, timing, review["bundle_sha256"], review), encoding="utf-8", newline="\n")
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
    supervisor_path = controller.private / "collected/outputs/SUPERVISOR_EXIT.txt"
    supervisor_ok = supervisor_path.is_file() and supervisor_path.read_text(encoding="ascii").strip() == "0"
    within_caps = attempt.get("closeout", {}).get("host_time_cap_observed") and attempt.get("closeout", {}).get("within_reserve")
    attempt["stage"] = "CLOSED_EVIDENCE_COLLECTED" if closed and collected else "HOLD_INCOMPLETE"
    attempt["supervisor_success"] = supervisor_ok
    attempt["overall_operational_pass"] = bool(failure is None and closed and collected and supervisor_ok and within_caps
                                               and not attempt.get("closeout", {}).get("gate_failed"))
    save_attempt()
    emit("launch_complete", status=attempt["stage"], operational_pass=attempt["overall_operational_pass"],
         attempt_record=str(attempt_path), supervisor_success=supervisor_ok,
         scientific_result="Requires independent completeness, qualification, and paired-score audit")
    return 0 if attempt["overall_operational_pass"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["prepare", "launch"], default="prepare")
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--bundle-sha256", required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--verify-stop-role", action="store_true", default=True)
    args = parser.parse_args()
    try:
        settings = json.loads(args.settings.read_text(encoding="utf-8"))
        cloud.validate_settings(settings)
        if settings.get("hf_secret_id") != "praxis/huggingface/token":
            raise ValueError("Use the already established Hugging Face secret name")
        if not settings["prefix"].startswith("final-praxis/cti-external-20260918/"):
            raise ValueError("A fresh CTI-specific S3 prefix is mandatory")
        if args.action == "prepare":
            review = validate_bundle(args.bundle, args.bundle_sha256, args.protocol, args.freeze, args.settings.parent)
            receipt = {"status": "READY_FROZEN_BUNDLE_NO_CLOUD_ACTION", "created_utc": cloud.stamp(cloud.utc_now()),
                       "cloud_requests": 0, "review": review,
                       "limits": {"total_seconds": cloud.TOTAL_SECONDS, "watchdog_seconds": cloud.WATCHDOG_SECONDS,
                                  "worker_deadline_seconds": cloud.WORKER_DEADLINE_SECONDS,
                                  "max_command_seconds": cloud.MAX_COMMAND_SECONDS,
                                  "publication_reserve_seconds": 160, "reserve_usd": cloud.TOTAL_RESERVE_USD}}
            target = args.settings.parent / "READY_RECEIPT.json"
            target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            emit("prepared", status=receipt["status"], receipt=str(target))
            return 0
        return launch(args)
    except BaseException as error:
        emit("launcher_error", error_type=type(error).__name__,
             message=str(error) if isinstance(error, (ValueError, FileNotFoundError)) else "Review private receipts and AWS session state")
        return 130 if isinstance(error, KeyboardInterrupt) else 1


if __name__ == "__main__":
    raise SystemExit(main())
