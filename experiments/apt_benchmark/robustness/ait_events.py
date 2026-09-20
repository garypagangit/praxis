"""Deterministic, label-blind AIT audit-event representation for development.

No log content is executed. Audit event time is the only clock available here;
``available_at`` is an idealized complete-event clock, not measured arrival.
Event labels are the union of exact, original-line author annotations.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re

from ..ait_adapter import normalized_text
from ..contracts import sha256_file, split_index


SCHEMA_VERSION = "ait-audit-events-v1"
HOST = "intranet_server"
_EVENT = re.compile(r"\bmsg=audit\(([0-9]+(?:\.[0-9]+)?):([0-9]+)\)")
_KV = re.compile(r'''(?<![\w-])([A-Za-z_][\w-]*)=("[^"\n]*"|'[^'\n]*'|[^\s]+)''')
_UNSET = {"-1", "4294967295", "18446744073709551615", "unset", "(unset)",
          "(null)", "(none)", "?", "unknown", "(unknown)"}
_PRIVILEGES = ("uid", "auid", "gid", "euid", "egid", "suid", "sgid", "fsuid", "fsgid",
               "old-auid", "old-uid", "acct", "id")
# A fixed, general command vocabulary avoids carrying arbitrary account names,
# attacker filenames, paths, addresses, timestamps, or free-form payloads.
_PROGRAMS = frozenset("sh bash dash zsh sudo su passwd useradd usermod userdel groupadd "
    "groups id whoami who w last login ssh sshd scp sftp cron crond systemd systemctl "
    "service journalctl modprobe insmod rmmod lsmod apparmor_parser dhclient python "
    "python2 python3 perl ruby php php-fpm apache2 httpd curl wget nc netcat ncat socat "
    "cat head tail grep egrep fgrep sed awk tee echo printf ls find locate xargs stat "
    "chmod chown chgrp getfacl setfacl cp mv rm mkdir rmdir touch dd mount umount "
    "tar gzip gunzip unzip zip ps top kill pkill pgrep sleep timeout env export "
    "ip ifconfig route netstat ss iptables ip6tables nft ufw ping traceroute dig "
    "nslookup nmap dirb wpscan uname hostname crontab at bashlogin dpkg apt apt-get "
    "yum rpm make gcc cc git docker passwd chage visudo mysql mysqld psql "
    "pam_unix systemd-logind systemd-timesyncd rsyslogd auditd".split())
_FLAGS = frozenset(("-c", "-i", "-l", "-p", "-r", "-s", "-u", "-v", "-w", "-x",
                    "--help", "--version", "--user", "--system", "--force", "--recursive"))
_ACTIONS = frozenset("accounting setcred session_open session_close authentication "
    "grantors acct_mgmt profile_replace profile_load profile_remove exec open read "
    "write connect accept bind listen create unlink rename mount umount ptrace "
    "mmap truncate ioctl load unload enable disable start stop restart reload "
    "add delete replace register unregister denied allowed status success failed failure".split())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fields(raw: str) -> dict[str, str]:
    """Parse quoted nested audit msg fields without interpreting their contents."""
    values: dict[str, str] = {}
    for match in _KV.finditer(raw):
        key, value = match.groups()
        key = key.lower()
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        if key == "msg":
            if value.startswith("audit("):
                continue
            nested = _fields(value)
            for nested_key, nested_value in nested.items():
                if nested_key in values:
                    raise ValueError("Repeated audit field is ambiguous")
                values[nested_key] = nested_value
        else:
            if key in values:
                raise ValueError("Repeated audit field is ambiguous")
            values[key] = value
    return values


def _privilege(value: str) -> str:
    value = value.casefold()
    if value in _UNSET:
        return "unset"
    return "root" if value in {"0", "root"} else "nonroot"


def _program(value: str) -> str:
    basename = value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].casefold()
    return basename if basename in _PROGRAMS else "other"


def decode_command(value: str) -> tuple[str, str]:
    """Decode bounded audit hex bytes, never shell/eval/exec the result."""
    if len(value) > 16384:
        return "", "overlength"
    if re.fullmatch(r"[0-9A-Fa-f]+", value):
        if len(value) % 2:
            return "", "invalid_hex"
        try:
            decoded = bytes.fromhex(value).decode("utf-8", errors="strict")
        except (ValueError, UnicodeDecodeError):
            return "", "invalid_encoding"
        status = "hex"
    else:
        decoded, status = value, "plain"
    if any(ord(char) < 32 and char not in "\x00\t\n\r" for char in decoded):
        return "", "invalid_control"
    return decoded.replace("\x00", " "), status


def semantic_text(fields: dict[str, str]) -> tuple[str, dict[str, int]]:
    """Use typed audit semantics; do not copy arbitrary free text or metadata."""
    channel = fields.get("type", "")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", channel):
        raise ValueError("Missing or invalid audit record type")
    tokens = ["source_audit", "record_" + channel.lower()]
    diagnostics: Counter = Counter()
    for key in _PRIVILEGES:
        if key in fields:
            tokens.append(key.replace("-", "_") + "=" + _privilege(fields[key]))
    for key in ("exe", "comm"):
        if key in fields:
            tokens.append(key + "=" + _program(fields[key]))
    for key in ("op", "operation", "apparmor"):
        if key in fields:
            # PAM:session_open becomes action_session_open; unknown values do not
            # become arbitrary identifiers in the model's vocabulary.
            value = fields[key].casefold().split(":")[-1]
            tokens.append(key + "=" + (value if value in _ACTIONS else "other"))
    for key in ("res", "success"):
        if key in fields:
            value = fields[key].casefold()
            result = "success" if value in {"1", "yes", "success", "successful"} else (
                "failure" if value in {"0", "no", "failed", "failure", "denied"} else "unknown")
            tokens.append(key + "=" + result)
    if "arch" in fields:
        arch = fields["arch"].casefold()
        tokens.append("arch=" + (arch if re.fullmatch(r"[0-9a-f]{8}", arch) else "unknown"))
    for key in ("syscall", "mode", "family", "capability"):
        if key in fields:
            value = fields[key]
            tokens.append(key + "=" + (value if re.fullmatch(r"[0-9]{1,6}", value) else "unknown"))
    if "exit" in fields:
        value = fields["exit"]
        if re.fullmatch(r"-?[0-9]+", value):
            number = int(value)
            result = "zero" if number == 0 else ("positive" if number > 0 else "errno_" + str(min(abs(number), 4096)))
        else:
            result = "unknown"
        tokens.append("exit=" + result)
    for key in ("tty", "terminal"):
        if key in fields:
            value = fields[key].casefold()
            terminal = "unset" if value in _UNSET else (
                "pts" if re.fullmatch(r"(?:/dev/)?pts/?[0-9]+", value) else (
                "tty" if re.fullmatch(r"(?:/dev/)?tty[0-9]+", value) else (
                "cron" if value == "cron" else "other")))
            tokens.append(key + "=" + terminal)
    for key in ("cmd", "proctitle"):
        if key not in fields:
            continue
        command, status = decode_command(fields[key])
        diagnostics[key + "_" + status] += 1
        tokens.append(key + "_encoding=" + status)
        words = re.findall(r"[^\s\"'`;|&()<>]+", command)
        if words:
            tokens.append(key + "_program=" + _program(words[0]))
            # Known executable names/options can occur in a shell's command
            # argument; arbitrary literal arguments and path basenames cannot.
            for word in words[1:128]:
                program = _program(word)
                if program != "other":
                    tokens.append(key + "_word=" + program)
                elif word in _FLAGS:
                    tokens.append(key + "_flag=" + word)
        if len(words) > 128:
            diagnostics["command_token_limit"] += 1
    return " ".join(tokens), dict(diagnostics)


def fragment_entity_keys(fields: dict[str, str], run_id: str, host_id: str) -> list[str]:
    keys = set()
    for field, kind in (("pid", "process"), ("ppid", "process"), ("ses", "session"), ("session", "session")):
        value = fields.get(field)
        if value is None or value.casefold() in _UNSET or not re.fullmatch(r"[0-9]+", value):
            continue
        number = int(value)
        if kind == "process" and number == 0:
            continue
        keys.add(f"{run_id}/{host_id}/{kind}/" + _digest(str(number)))
    return sorted(keys)


def parse_fragment(raw: str, *, run_id: str, host_id: str = HOST) -> dict:
    matches = list(_EVENT.finditer(raw))
    if len(matches) != 1:
        raise ValueError("Each audit fragment needs exactly one explicit epoch/serial")
    epoch, serial = matches[0].groups()
    timestamp = float(epoch)
    if not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError("Invalid audit epoch")
    fields = _fields(raw)
    text, diagnostics = semantic_text(fields)
    # A source node, if present, disambiguates hosts privately. It never enters
    # either semantic text or an unmasked model feature.
    scoped_host = host_id + ("/node_" + _digest(fields["node"]) if "node" in fields else "")
    event_key = (run_id, scoped_host, format(Decimal(epoch).normalize(), "f"), str(int(serial)))
    return {"event_key": event_key, "timestamp": timestamp, "channel": fields["type"],
            "text": text, "baseline_text": normalized_text(raw, "audit"),
            "entity_keys": fragment_entity_keys(fields, run_id, scoped_host),
            "diagnostics": diagnostics}


def assemble_events(records: list[dict]) -> tuple[list[dict], dict]:
    """Assemble supplied fragments only; no neighboring event content is used."""
    groups: dict[tuple, list] = defaultdict(list)
    for record in records:
        if record["split"] not in {"fit", "development", "calibration", "test"}:
            raise ValueError("Unknown split")
        if not isinstance(record["labels"], list) or any(not isinstance(x, str) or not x for x in record["labels"]):
            raise ValueError("Invalid fragment labels")
        groups[tuple(record["event_key"])].append(record)
    events, mixed_events, changed_target_fragments = [], 0, 0
    for key, members in groups.items():
        roles = {member["split"] for member in members}
        if len(roles) != 1:
            raise ValueError("Event spans split roles")
        timestamps = [member["timestamp"] for member in members]
        if any(not math.isfinite(t) or t != float(key[2]) for t in timestamps):
            raise ValueError("Fragment clock disagrees with its event key")
        labels = sorted({label for member in members for label in member["labels"]})
        label_sets = {tuple(sorted(set(member["labels"]))) for member in members}
        mixed_events += int(len(label_sets) > 1)
        changed_target_fragments += sum(member["labels"] != labels for member in members)
        fragments = [{name: member[name] for name in ("channel", "text", "baseline_text", "timestamp", "entity_keys")}
                     for member in members]
        events.append({"event_id": "ait:" + _digest(json.dumps(key, separators=(",", ":"))),
            "run_id": key[0], "split": next(iter(roles)), "timestamp": min(timestamps),
            "available_at": max(timestamps),
            "entity_keys": sorted({entity for member in members for entity in member["entity_keys"]}),
            "labels": labels, "fragments": fragments})
    events.sort(key=lambda event: (event["run_id"], event["timestamp"], event["event_id"]))
    return events, {"events_with_different_fragment_annotations": mixed_events,
                    "fragments_whose_label_set_differs_from_event_union": changed_target_fragments}


def _read_annotations(path: Path) -> dict[int, list[str]]:
    annotations = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("Invalid annotation")
        number, labels = value.get("line"), value.get("labels")
        if type(number) is not int or number < 1 or number in annotations:
            raise ValueError("Invalid/duplicate original annotation ordinal")
        if not isinstance(labels, list) or not labels or any(not isinstance(x, str) or not x.strip() for x in labels):
            raise ValueError("An explicit empty/unknown annotation cannot be made benign")
        annotations[number] = sorted(set(labels))
    return annotations


def build_dataset(source_root: Path, protocol_path: Path, output_dir: Path) -> dict:
    source_root, protocol_path, output_dir = map(Path, (source_root, protocol_path, output_dir))
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite an existing adapter output")
    roles = split_index(json.loads(protocol_path.read_text(encoding="utf-8")))
    receipt_path = source_root / "ACQUISITION.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("record") != 19483937:
        raise ValueError("Expected pinned AIT-LDS acquisition record")
    acquired = {}
    for scenario in receipt["scenarios"]:
        for member in scenario["members"]:
            key = (scenario["scenario"], member["local_relative_path"])
            if key in acquired:
                raise ValueError("Duplicate acquired member")
            acquired[key] = member
    records, files, decode_counts = [], [], Counter()
    for run_id, role in roles.items():
        scenario_root = source_root / run_id
        label_root = scenario_root / "labels" / HOST / "logs"
        label_paths = sorted(path for path in label_root.rglob("*") if path.is_file()
                             and re.fullmatch(r"audit\.log(?:\.[0-9]+)?", path.name))
        if not label_paths:
            raise ValueError("Missing author-paired audit source")
        for label_path in label_paths:
            relative = label_path.relative_to(scenario_root / "labels")
            raw_path = scenario_root / "gather" / relative
            hashes = {}
            for kind, path in (("source", raw_path), ("labels", label_path)):
                relative_member = path.relative_to(scenario_root).as_posix()
                member = acquired.get((run_id, relative_member))
                actual = sha256_file(path)
                if member is None or member.get("crc32_verified") is not True or member.get("sha256") != actual:
                    raise ValueError("Source/label bytes do not match verified acquired member")
                hashes[kind + "_sha256"] = actual
            annotations = _read_annotations(label_path)
            line_count = 0
            with raw_path.open(encoding="utf-8", errors="strict") as stream:
                for number, raw in enumerate(stream, 1):
                    line_count = number
                    record = parse_fragment(raw, run_id=run_id)
                    record.update(split=role, labels=annotations.get(number, []))
                    decode_counts.update(record["diagnostics"])
                    records.append(record)
            if annotations and max(annotations) > line_count:
                raise ValueError("Original annotation is beyond the source file")
            files.append({"run_id": run_id, "split": role, "source": relative.as_posix(),
                          "rows": line_count, "annotated_rows": len(annotations), **hashes})
    events, label_scope = assemble_events(records)
    if len({event["event_id"] for event in events}) != len(events):
        raise ValueError("Nonunique event identifier")
    per_run = {}
    for run_id, role in roles.items():
        selected = [event for event in events if event["run_id"] == run_id]
        times = [event["timestamp"] for event in selected]
        per_run[run_id] = {"split": role, "events": len(selected),
            "fragments": sum(len(event["fragments"]) for event in selected),
            "annotated_events": sum(bool(event["labels"]) for event in selected),
            "multifragment_events": sum(len(event["fragments"]) > 1 for event in selected),
            "events_with_link_keys": sum(bool(event["entity_keys"]) for event in selected),
            "timestamp_min": min(times), "timestamp_max": max(times),
            "observation_span_seconds": max(times) - min(times),
            "distinct_link_keys": len({key for event in selected for key in event["entity_keys"]}),
            "label_event_counts": dict(sorted(Counter(label for event in selected for label in event["labels"]).items()))}
    output_dir.mkdir(parents=True)
    event_path = output_dir / "EVENTS.jsonl"
    with event_path.open("w", encoding="utf-8", newline="\n") as stream:
        for event in events:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    manifest = {"schema_version": SCHEMA_VERSION, "status": "QUALIFIED_DEVELOPMENT_EVENT_ADAPTER",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": "https://zenodo.org/records/19483937", "source_release": "AIT-LDS v2.1",
        "license": receipt.get("license"), "model_fit_or_inference_performed": False,
        "protocol_sha256": sha256_file(protocol_path), "acquisition_sha256": sha256_file(receipt_path),
        "adapter_sha256": sha256_file(Path(__file__)),
        "baseline_normalizer_sha256": sha256_file(Path(__file__).parents[1] / "ait_adapter.py"),
        "events_sha256": sha256_file(event_path), "events_file": event_path.name,
        "events": len(events), "fragments": len(records), "source_pairs": len(files),
        "annotated_events": sum(bool(event["labels"]) for event in events),
        "annotated_fragments": sum(bool(record["labels"]) for record in records),
        "channel_counts": dict(sorted(Counter(record["channel"] for record in records).items())),
        "fragment_count_distribution": dict(sorted(Counter(len(event["fragments"]) for event in events).items())),
        "decoding_counts": dict(sorted(decode_counts.items())), "per_run": per_run, "sources": files,
        "label_scope": {**label_scope,
            "exact_original_1_based_line_join": True,
            "event_target": "Union of existing source-step labels across fragments sharing run/host/epoch/serial",
            "negative_basis": "No annotation in an acquired, author-covered paired audit file under the author's closed-world rule",
            "independent_analyst_adjudication": False,
            "review": "Author rule/time/identity scope may differ from visible action semantics; unchanged actions may have different labels. Grouping changes the target unit, so all compared arms must use the same event target. Labels are overlapping source steps, not ordered kill-chain states."},
        "semantic_policy": {"label_blind": True, "free_text_copied": False,
            "preserved": ["record type", "typed root/nonroot/unset privilege", "action/result", "architecture/syscall/mode/family/capability", "exit zero/positive/errno", "fixed command vocabulary from bounded safe hex decode"],
            "excluded_from_text": ["event timestamp/serial", "PID/PPID/session identifiers", "host/address/account names", "arbitrary paths and command literal arguments", "untyped syscall pointer/argument fields"],
            "baseline_text": "Exact previous generic normalizer for representation control; its documented unstructured username/path/payload identity limitations remain"},
        "limitations": [
            "All eight runs and previous test outcomes are exposed development data; no untouched confirmation claim.",
            "Only the selected intranet host's paired audit logs; no claim of complete enterprise telemetry.",
            "Same audit epoch is the event clock, not ingestion or record arrival. available_at=max included epoch is idealized; no measured closure delay or complete-event delivery guarantee.",
            "Simulated drops/delays must use visible fragment entity_keys only, never event-wide union keys; labels and dropped fragment metadata are forbidden features.",
            "Link keys namespace explicit PID/PPID/session by run/host but do not establish PID lifetime or process ancestry; PID reuse can create spurious links.",
            "Source min/max are observed event span, not continuous benign-host-hour exposure.",
            "Repeated fragments/events/runs are correlated, not independent attacks or campaigns.",
            "Semantic representation is deliberately lossy and fixed; no model superiority or robustness claim is established by this adapter."]}
    (output_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build_dataset(args.source_root, args.protocol, args.output)
    print(json.dumps({key: result[key] for key in ("status", "events", "fragments", "source_pairs", "annotated_events", "events_sha256")}))


if __name__ == "__main__":
    main()
