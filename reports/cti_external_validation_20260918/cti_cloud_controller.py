"""One-attempt CTI cloud control; account settings and receipts stay private.

No provisioning, IAM mutation, model API, or scientific decisions occur here.
The start gate requires the protocol and executable freeze to equal Git HEAD.
Call finalize repeatedly while stopping; it removes only this run's watchdog,
and only after a fresh observation that the selected instance is stopped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import uuid


TOTAL_SECONDS = 3600
WATCHDOG_SECONDS = 3360
WORKER_DEADLINE_SECONDS = 3120
MAX_COMMAND_SECONDS = 3000
INCIDENTAL_ALLOWANCE_USD = 5.0
TOTAL_RESERVE_USD = 10.0
STOP_TARGET = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
RETRY_POLICY = {"MaximumRetryAttempts": 1, "MaximumEventAgeInSeconds": 60}
TERMINAL_FAILURES = {"Failed", "TimedOut", "Cancelled", "Cancelling"}
TERMINAL_STATES = {"Success", "Failed", "TimedOut", "Cancelled"}


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def stamp(value):
    return value.astimezone(dt.timezone.utc).isoformat()


def parse_stamp(value):
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Operational timestamps must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def committed_identity(path):
    path = Path(path).resolve(strict=True)
    repo = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=path.parent, text=True
    ).strip()).resolve()
    relative = path.relative_to(repo).as_posix()
    committed = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=repo)
    if committed != path.read_bytes():
        raise ValueError("Exact committed bytes required: " + relative)
    return {
        "path": relative,
        "sha256": hashlib.sha256(committed).hexdigest(),
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
    }


def validate_settings(settings):
    needed = ["profile", "region", "account", "instance", "bucket", "prefix", "stop_role_arn"]
    if any(not isinstance(settings.get(key), str) or not settings[key] for key in needed):
        raise ValueError("Settings require nonempty profile, region, account, instance, bucket, prefix, stop_role_arn")
    if not re.fullmatch(r"\d{12}", settings["account"]):
        raise ValueError("Invalid expected account")
    if not re.fullmatch(r"i-[0-9a-f]{17}", settings["instance"]):
        raise ValueError("Invalid designated instance")
    if not settings["stop_role_arn"].startswith("arn:aws:iam::" + settings["account"] + ":role/"):
        raise ValueError("Stop role must belong to the expected account")
    prefix = settings["prefix"]
    if not prefix.endswith("/") or prefix.startswith("/") or any(x in {"", ".", ".."} for x in prefix[:-1].split("/")):
        raise ValueError("A distinct nonempty S3 prefix ending in slash is required")
    rate = float(settings.get("usd_per_hour", 1.006))
    if not math.isfinite(rate) or rate <= 0 or rate * TOTAL_SECONDS / 3600 + INCIDENTAL_ALLOWANCE_USD > TOTAL_RESERVE_USD:
        raise ValueError("Compute bound plus incidental allowance exceeds the $10 reserve")
    return rate


def validate_key(settings, key):
    if not isinstance(key, str) or not key.startswith(settings["prefix"]):
        raise ValueError("Transfer key must be inside this run's S3 prefix")
    if any(part in {"", ".", ".."} for part in key.split("/")) or "\\" in key:
        raise ValueError("Invalid transfer key")
    return key


def verify_schedule(schedule, active, settings):
    expected_time = "at(" + parse_stamp(active["scheduled_stop_utc"]).strftime("%Y-%m-%dT%H:%M:%S") + ")"
    expected_arn = "arn:aws:scheduler:" + settings["region"] + ":" + settings["account"] + ":schedule/default/" + active["schedule"]
    checks = {
        "name": schedule.get("Name") == active["schedule"],
        "arn": schedule.get("Arn") == expected_arn,
        "enabled": schedule.get("State") == "ENABLED",
        "deadline": schedule.get("ScheduleExpression") == expected_time,
        "timezone": schedule.get("ScheduleExpressionTimezone") == "UTC",
        "no_flexible_window": schedule.get("FlexibleTimeWindow", {}).get("Mode") == "OFF",
        "auto_delete": schedule.get("ActionAfterCompletion") == "DELETE",
        "action": schedule.get("Target", {}).get("Arn") == STOP_TARGET,
        "role": schedule.get("Target", {}).get("RoleArn") == settings["stop_role_arn"],
        "input": json.loads(schedule.get("Target", {}).get("Input", "null")) == {"InstanceIds": [settings["instance"]]},
        "retry_window": schedule.get("Target", {}).get("RetryPolicy") == RETRY_POLICY,
    }
    if not all(checks.values()):
        raise ValueError("Watchdog verification failed: " + ", ".join(key for key, value in checks.items() if not value))
    return checks


class Controller:
    def __init__(self, settings_path, session=None, clock=utc_now):
        self.settings_path = Path(settings_path).resolve(strict=True)
        self.settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.rate = validate_settings(self.settings)
        self.private = self.settings_path.parent
        self.active_path = self.private / "ACTIVE_RUN.json"
        self.receipts = self.private / "receipts"
        self.receipts.mkdir(exist_ok=True)
        self.clock = clock
        if session is None:
            import boto3
            session = boto3.Session(profile_name=self.settings["profile"], region_name=self.settings["region"])
        self.session = session
        self._clients = {}

    def client(self, name):
        if name not in self._clients:
            from botocore.config import Config
            self._clients[name] = self.session.client(name, config=Config(
                connect_timeout=10, read_timeout=20, retries={"total_max_attempts": 2}
            ))
        return self._clients[name]

    def record(self, action, value):
        record = {"recorded_utc": stamp(self.clock()), "action": action, **value}
        path = self.receipts / (self.clock().strftime("%Y%m%dT%H%M%S") + "-" + action + "-" + uuid.uuid4().hex[:8] + ".json")
        path.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
        return {"receipt": str(path), **{key: record[key] for key in ("status", "instance_state", "command_id", "response_code", "approximate_total_with_allowance_usd", "host_time_cap_observed", "within_reserve", "gate_failed") if key in record}}

    def save_active(self, active):
        temporary = self.private / (".ACTIVE_RUN-" + uuid.uuid4().hex + ".tmp")
        temporary.write_text(json.dumps(active, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.active_path)

    def active(self):
        active = json.loads(self.active_path.read_text(encoding="utf-8"))
        if any(active[key] != self.settings[key] for key in ("account", "region", "instance", "bucket", "prefix", "stop_role_arn")):
            raise ValueError("Active-run settings identity changed")
        return active

    def verify_account(self):
        observed = self.client("sts").get_caller_identity()["Account"]
        if observed != self.settings["account"]:
            raise ValueError("AWS account differs from designated account")
        return observed

    def instance(self):
        reservations = self.client("ec2").describe_instances(InstanceIds=[self.settings["instance"]])["Reservations"]
        items = [item for reservation in reservations for item in reservation["Instances"]]
        if len(items) != 1 or items[0]["InstanceId"] != self.settings["instance"]:
            raise ValueError("Expected exactly the designated instance")
        if any(reservation.get("OwnerId") != self.settings["account"] for reservation in reservations):
            raise ValueError("Instance owner account mismatch")
        if items[0]["InstanceType"] != "g5.xlarge":
            raise ValueError("Designated instance must remain g5.xlarge")
        return items[0]

    def status(self):
        self.verify_account()
        item = self.instance()
        information = self.client("ssm").describe_instance_information(Filters=[
            {"Key": "InstanceIds", "Values": [self.settings["instance"]]}
        ])["InstanceInformationList"]
        detail = {"instance_state": item["State"]["Name"], "instance_type": item["InstanceType"],
                  "ssm": [{"ping": value["PingStatus"], "platform": value.get("PlatformName")} for value in information]}
        if self.active_path.exists():
            active = self.active()
            elapsed = (self.clock() - parse_stamp(active["start_request_utc"])).total_seconds()
            detail.update(elapsed_seconds=elapsed, total_cap_seconds=TOTAL_SECONDS,
                          worker_seconds_remaining=(parse_stamp(active["worker_deadline_utc"]) - self.clock()).total_seconds(),
                          gate_failed=active.get("gate_failed", False), stage=active["stage"])
            if elapsed >= WORKER_DEADLINE_SECONDS:
                active["worker_deadline_passed"] = True
                self.save_active(active)
        return self.record("status", detail)

    def start(self, protocol, freeze):
        if self.active_path.exists():
            raise ValueError("This execution already has a start attempt; restart is prohibited")
        identities = {"protocol": committed_identity(protocol), "runtime_freeze": committed_identity(freeze)}
        if identities["protocol"]["commit"] != identities["runtime_freeze"]["commit"]:
            raise ValueError("Protocol and runtime freeze must belong to the same committed runtime")
        self.verify_account()
        if self.instance()["State"]["Name"] != "stopped":
            raise ValueError("Refuse to take over a host that is not stopped")
        behavior = self.client("ec2").describe_instance_attribute(
            InstanceId=self.settings["instance"], Attribute="instanceInitiatedShutdownBehavior"
        )
        if behavior["InstanceInitiatedShutdownBehavior"]["Value"] != "stop":
            raise ValueError("Guest shutdown must stop the host")
        now = self.clock()
        active = {key: self.settings[key] for key in ("account", "region", "instance", "bucket", "prefix", "stop_role_arn")}
        active.update(run_id=uuid.uuid4().hex, stage="preparing_watchdog", gate_failed=False,
                      start_request_utc=stamp(now), scheduled_stop_utc=stamp(now + dt.timedelta(seconds=WATCHDOG_SECONDS)),
                      worker_deadline_utc=stamp(now + dt.timedelta(seconds=WORKER_DEADLINE_SECONDS)),
                      total_deadline_utc=stamp(now + dt.timedelta(seconds=TOTAL_SECONDS)),
                      usd_per_hour=self.rate, rate_source=self.settings.get("rate_source", "Pinned AWS verified 2026-09-14 estimate; not an invoice"),
                      incidental_allowance_usd=INCIDENTAL_ALLOWANCE_USD, total_reserve_usd=TOTAL_RESERVE_USD,
                      identities=identities, commands=[])
        active["schedule"] = "praxis-cti-" + now.strftime("%Y%m%d") + "-" + active["run_id"][:16]
        # Exclusive creation prevents concurrent starts and makes an attempt irreversible.
        with self.active_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(active, indent=2) + "\n")
        try:
            scheduler = self.client("scheduler")
            scheduler.create_schedule(
                Name=active["schedule"], GroupName="default", State="ENABLED",
                ScheduleExpression="at(" + parse_stamp(active["scheduled_stop_utc"]).strftime("%Y-%m-%dT%H:%M:%S") + ")",
                ScheduleExpressionTimezone="UTC", FlexibleTimeWindow={"Mode": "OFF"},
                ActionAfterCompletion="DELETE", ClientToken=active["run_id"],
                Target={"Arn": STOP_TARGET, "RoleArn": self.settings["stop_role_arn"],
                        "Input": json.dumps({"InstanceIds": [self.settings["instance"]]}), "RetryPolicy": RETRY_POLICY},
                Description="Single CTI validation host stop; 60-minute total cap with stop margin",
            )
            active["watchdog_checks"] = verify_schedule(scheduler.get_schedule(Name=active["schedule"], GroupName="default"), active, self.settings)
            active["stage"] = "watchdog_verified"
            self.save_active(active)
            # Recheck state and timing after watchdog API calls, before incurring compute.
            if self.instance()["State"]["Name"] != "stopped":
                raise ValueError("Host state changed during preflight")
            if (self.clock() - now).total_seconds() > 120:
                raise ValueError("Start preflight is stale; retain watchdog and do not start")
            active["stage"] = "start_submitted"
            active["ec2_start_submitted_utc"] = stamp(self.clock())
            self.save_active(active)
            response = self.client("ec2").start_instances(InstanceIds=[self.settings["instance"]])
            if [value["InstanceId"] for value in response["StartingInstances"]] != [self.settings["instance"]]:
                raise ValueError("Unexpected start response")
            active["stage"] = "started"
            self.save_active(active)
            return self.record("start", {"status": "START_SUBMITTED_WATCHDOG_VERIFIED", "active_run": active})
        except Exception as error:
            # Never remove protection when an API result is ambiguous.
            active["gate_failed"] = True
            active["stage"] = "start_failed_or_ambiguous"
            active["failure_type"] = type(error).__name__
            self.save_active(active)
            self.record("start_failure", {"status": "HOLD_WATCHDOG_RETAINED", "failure_type": type(error).__name__, "active_run": active})
            raise

    def send(self, script, timeout):
        active = self.active()
        if active.get("gate_failed") or active["stage"] != "started":
            raise ValueError("Run has a failed gate or is not eligible for worker execution")
        if not 30 <= timeout <= MAX_COMMAND_SECONDS:
            raise ValueError("Command timeout must be between 30 and 3000 seconds")
        if active["commands"] and active["commands"][-1]["status"] not in TERMINAL_STATES:
            raise ValueError("A prior SSM command is still active or its submission is ambiguous")
        text = Path(script).read_text(encoding="utf-8")
        if len(text.encode()) > 23000:
            raise ValueError("Use a hash-checked S3 bundle for scripts over 23000 bytes")
        self.verify_account()
        if self.instance()["State"]["Name"] != "running":
            raise ValueError("Host must be running before command submission")
        verify_schedule(self.client("scheduler").get_schedule(Name=active["schedule"], GroupName="default"), active, self.settings)
        remaining = (parse_stamp(active["worker_deadline_utc"]) - self.clock()).total_seconds()
        # Include delivery timeout plus API overhead; all must end by minute 52.
        if timeout + 130 >= remaining:
            raise ValueError("Command and delivery allowance do not fit the absolute minute-52 deadline")
        entry = {"script_sha256": digest(script), "timeout_seconds": timeout, "submitted_utc": stamp(self.clock()), "status": "SubmissionUnknown"}
        active["commands"].append(entry)
        self.save_active(active)
        try:
            response = self.client("ssm").send_command(
                InstanceIds=[self.settings["instance"]], DocumentName="AWS-RunShellScript",
                Parameters={"commands": [text], "executionTimeout": [str(timeout)]}, TimeoutSeconds=120,
                Comment="Authorized CTI bounded worker: " + Path(script).name[:55],
                OutputS3BucketName=self.settings["bucket"], OutputS3KeyPrefix=self.settings["prefix"] + "ssm",
            )
            entry.update(command_id=response["Command"]["CommandId"], status="Pending")
            self.save_active(active)
            return self.record("send", {"status": "SUBMITTED", **entry})
        except Exception as error:
            active["gate_failed"] = True
            self.save_active(active)
            self.record("send_failure", {"status": "HOLD_SUBMISSION_AMBIGUOUS", "failure_type": type(error).__name__})
            raise

    def poll(self, command_id):
        active = self.active()
        entries = [entry for entry in active["commands"] if entry.get("command_id") == command_id]
        if len(entries) != 1:
            raise ValueError("Command does not belong to this execution")
        self.verify_account()
        result = self.client("ssm").get_command_invocation(CommandId=command_id, InstanceId=self.settings["instance"])
        entries[0]["status"] = result["Status"]
        entries[0]["response_code"] = result.get("ResponseCode")
        if result["Status"] in TERMINAL_FAILURES or (result["Status"] == "Success" and result.get("ResponseCode") != 0):
            active["gate_failed"] = True
        self.save_active(active)
        return self.record("poll", {"command_id": command_id, "status": result["Status"],
            "response_code": result.get("ResponseCode"), "elapsed": result.get("ExecutionElapsedTime"),
            "stdout": result.get("StandardOutputContent"), "stderr": result.get("StandardErrorContent"),
            "stdout_url": result.get("StandardOutputUrl"), "stderr_url": result.get("StandardErrorUrl")})

    def transfer(self, action, path, key):
        key = validate_key(self.settings, key)
        self.verify_account()
        path = Path(path).resolve()
        if action == "upload":
            if self.active_path.exists():
                active = self.active()
                if active.get("gate_failed") or self.clock() >= parse_stamp(active["worker_deadline_utc"]):
                    raise ValueError("Upload after a failed gate or worker deadline is prohibited")
            self.client("s3").upload_file(str(path), self.settings["bucket"], key)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.client("s3").download_file(self.settings["bucket"], key, str(path))
        return self.record(action, {"status": "COMPLETE", "key": key, "path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})

    def stop(self):
        active = self.active()
        self.verify_account()
        state = self.instance()["State"]["Name"]
        if state not in {"stopped", "stopping"}:
            if state not in {"running", "pending"}:
                raise ValueError("Unexpected host state; no mutation performed: " + state)
            response = self.client("ec2").stop_instances(InstanceIds=[self.settings["instance"]])
            if [value["InstanceId"] for value in response["StoppingInstances"]] != [self.settings["instance"]]:
                raise ValueError("Unexpected stop response")
        active["stop_request_utc"] = active.get("stop_request_utc", stamp(self.clock()))
        active["stage"] = "stop_requested"
        self.save_active(active)
        return self.record("stop", {"status": "STOP_REQUESTED_WATCHDOG_RETAINED", "instance_state": state})

    def finalize(self):
        active = self.active()
        self.verify_account()
        state = self.instance()["State"]["Name"]
        if state != "stopped":
            return self.record("finalize", {"status": "PENDING_HOST_NOT_STOPPED_WATCHDOG_RETAINED", "instance_state": state})
        observed = self.clock()
        active["stopped_observed_utc"] = active.get("stopped_observed_utc", stamp(observed))
        elapsed = max(0.0, (parse_stamp(active["stopped_observed_utc"]) - parse_stamp(active["start_request_utc"])).total_seconds())
        scheduler = self.client("scheduler")
        cleanup = "already_absent"
        try:
            schedule = scheduler.get_schedule(Name=active["schedule"], GroupName="default")
        except scheduler.exceptions.ResourceNotFoundException:
            schedule = None
        if schedule is not None:
            # Ownership and exact target/deadline remain mandatory for deletion.
            verify_schedule(schedule, active, self.settings)
            scheduler.delete_schedule(Name=active["schedule"], GroupName="default")
            cleanup = "deleted_own_schedule_after_stopped"
        estimate = elapsed / 3600 * active["usd_per_hour"]
        active.update(stage="closed", watchdog_cleanup=cleanup, elapsed_to_stopped_observation_seconds=elapsed,
                      host_time_cap_observed=elapsed <= TOTAL_SECONDS,
                      approximate_compute_usd=estimate, approximate_total_with_allowance_usd=estimate + INCIDENTAL_ALLOWANCE_USD)
        self.save_active(active)
        return self.record("finalize", {"status": "CLOSED_VERIFIED_STOPPED", "instance_state": state,
            "stopped_observed_utc": active["stopped_observed_utc"], "elapsed_seconds": elapsed,
            "host_time_cap_observed": active["host_time_cap_observed"], "watchdog_cleanup": cleanup,
            "approximate_compute_usd": estimate, "incidental_allowance_usd": INCIDENTAL_ALLOWANCE_USD,
            "approximate_total_with_allowance_usd": estimate + INCIDENTAL_ALLOWANCE_USD,
            "within_reserve": estimate + INCIDENTAL_ALLOWANCE_USD <= TOTAL_RESERVE_USD,
            "is_invoice": False, "rate_source": active["rate_source"], "gate_failed": active["gate_failed"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "start", "upload", "send", "poll", "download", "stop", "finalize"])
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--command-id")
    parser.add_argument("--path", type=Path)
    parser.add_argument("--key")
    args = parser.parse_args()
    required = {"start": ["protocol", "freeze"], "send": ["script"], "poll": ["command_id"], "upload": ["path", "key"], "download": ["path", "key"]}
    if any(getattr(args, key) is None for key in required.get(args.action, [])):
        parser.error("Missing required arguments for " + args.action)
    try:
        controller = Controller(args.settings)
        if args.action == "start":
            result = controller.start(args.protocol, args.freeze)
        elif args.action == "send":
            result = controller.send(args.script, args.timeout)
        elif args.action == "poll":
            result = controller.poll(args.command_id)
        elif args.action in {"upload", "download"}:
            result = controller.transfer(args.action, args.path, args.key)
        else:
            result = getattr(controller, args.action)()
        print(json.dumps(result))
        return 2 if result.get("status", "").startswith("PENDING_") else 0
    except Exception as error:
        # SDK error strings and full remote output belong outside terminal output.
        message = str(error) if isinstance(error, (ValueError, FileNotFoundError)) else "See private operational receipts and AWS session state"
        print(json.dumps({"status": "ERROR", "error_type": type(error).__name__, "message": message}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
