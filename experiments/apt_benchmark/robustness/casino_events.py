"""Qualified CasinoLimit audit-event stream for controlled telemetry experiments.

The source's technique annotations describe processes and propagate to audit
events. They do not certify unannotated events as benign. This adapter uses one
onset target per annotation and host, retaining strictly causal nearby context.
No process summary, end time, later event, annotation text or identifier enters
the feature text. Audit timestamps are idealized availability; measured ingest
times are unavailable, so delay experiments must be described as synthetic.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import hashlib
import ipaddress
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import zipfile
import zlib

import requests

from ..acquire_ait import RangeReader, central_directory
from ..ait_adapter import normalized_text


RECORD = 17256954
SEED = "casino-robustness-v1:"
AUDIT = re.compile(r"msg=audit\(([0-9.]+):(\d+)\)")
FIELD = re.compile(r'(?<!\w)([A-Za-z][A-Za-z0-9_]*)=("[^"\n]*"|\'[^\'\n]*\'|[^\s]+)')
TARGET_IDS = ("T1068", "T1548", "T1105")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def machine_name(directory: str) -> str:
    name = "bastion" if directory.startswith("bastion.") else directory.rsplit("-", 1)[0]
    # The pinned event-label export calls the meetingcam host "meet".
    return "meet" if name == "meetingcam" else name


def select_instances(names: list[str], count: int = 114) -> dict[str, str]:
    if count not in (24, 114) or len(names) < count:
        raise ValueError("Qualified cohort must contain the complete requested24 or114 instances")
    ordered = sorted(names, key=lambda n: hashlib.sha256((SEED + n).encode()).hexdigest())[:count]
    fit, dev, cal = (12, 16, 20) if count == 24 else (60, 78, 96)
    return {name: "fit" if i < fit else "development" if i < dev else
            "calibration" if i < cal else "test" for i, name in enumerate(ordered)}


def _download(root: Path, metadata: dict, name: str) -> Path:
    item = next(x for x in metadata["files"] if x["key"] == name)
    dest = root / name
    if not dest.exists():
        url = f"https://zenodo.org/records/{RECORD}/files/{name}?download=1"
        with requests.get(url, stream=True, timeout=(30, 120)) as r:
            r.raise_for_status()
            with dest.with_suffix(".part").open("wb") as out:
                for block in r.iter_content(1024 * 1024):
                    out.write(block)
        dest.with_suffix(".part").replace(dest)
    if dest.stat().st_size != item["size"]:
        raise ValueError("Publisher archive length mismatch")
    h = hashlib.md5()
    with dest.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    if "md5:" + h.hexdigest() != item["checksum"]:
        raise ValueError("Publisher archive checksum mismatch")
    return dest


def _fetch_audit(reader: RangeReader, url: str, size: int, item: dict, root: Path) -> dict:
    relative = PurePosixPath(item["name"])
    if relative.is_absolute() or ".." in relative.parts or "\\" in item["name"]:
        raise ValueError("Unsafe archive path")
    dest = root.joinpath(*relative.parts)
    if root.resolve() not in dest.resolve().parents:
        raise ValueError("Archive path escapes root")
    if item["bytes"] > 1024 * 1024 * 1024 or item["compressed_bytes"] > 32 * 1024 * 1024:
        raise ValueError("Member exceeds acquisition bound")
    if item["flags"] & 1 or item["method"] not in (0, 8):
        raise ValueError("Unsupported archive member")
    if dest.exists():
        crc = 0
        with dest.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                crc = zlib.crc32(block, crc)
        if dest.stat().st_size == item["bytes"] and crc & 0xffffffff == item["crc32"]:
            return {**item, "sha256": sha256(dest), "crc32_verified": True, "reused": True}
        raise ValueError("Existing raw member has changed")
    offset = item["local_header_offset"]
    h = reader.get(url, size, offset, offset + 29)
    values = struct.unpack("<4s5H3L2H", h)
    if values[0] != b"PK\x03\x04" or values[2] != item["flags"] or values[3] != item["method"]:
        raise ValueError("Local ZIP header mismatch")
    name_len, extra_len = values[-2:]
    length = name_len + extra_len + item["compressed_bytes"]
    payload = reader.get(url, size, offset + 30, offset + 29 + length)
    if payload[:name_len].decode("utf-8") != item["name"]:
        raise ValueError("Local ZIP name mismatch")
    data = payload[name_len + extra_len:]
    decoder = zlib.decompressobj(-15) if item["method"] == 8 else None
    dest.parent.mkdir(parents=True, exist_ok=True)
    crc, n = 0, 0
    with dest.with_suffix(".part").open("wb") as f:
        for start in range(0, len(data), 65536):
            block = decoder.decompress(data[start:start + 65536], item["bytes"] - n + 1) if decoder else data[start:start + 65536]
            n += len(block)
            if n > item["bytes"] or (decoder and decoder.unconsumed_tail):
                raise ValueError("Oversized compressed member")
            crc = zlib.crc32(block, crc)
            f.write(block)
    if n != item["bytes"] or crc & 0xffffffff != item["crc32"] or (decoder and (not decoder.eof or decoder.unused_data)):
        raise ValueError("Member size, CRC or stream validation failed")
    dest.with_suffix(".part").replace(dest)
    return {**item, "sha256": sha256(dest), "crc32_verified": True, "reused": False}


def acquire(root: Path) -> dict:
    if (root / "FROZEN_EVENT_STREAM.json").exists():
        raise ValueError("Completed event evidence is immutable; use a fresh acquisition directory")
    root.mkdir(parents=True, exist_ok=True)
    response = requests.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60)
    response.raise_for_status()
    metadata = response.json()
    if metadata["id"] != RECORD or metadata["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Pinned record/license mismatch")
    (root / "ZENODO_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    labels = _download(root, metadata, "syslogs_labels.zip")
    output = _download(root, metadata, "output.zip")
    with zipfile.ZipFile(labels) as z, zipfile.ZipFile(output) as annotated:
        # The event export contains 140 machine instances, including 26 without
        # the richer process annotation/validation files. Sample the 114
        # author-annotated challenge executions, not all exported instances.
        eligible = [Path(n).stem for n in annotated.namelist()
                    if n.startswith("output/system_labels/") and n.endswith(".json")]
        roles = select_instances(eligible)
        hosts = {run: {host for value in json.loads(z.read(f"system_labels/{run}.json")).values()
                       for host in value["auditd_events"]} for run in roles}
    archive = next(x for x in metadata["files"] if x["key"] == "syslogs.zip")
    url = f"https://zenodo.org/records/{RECORD}/files/syslogs.zip?download=1"
    reader = RangeReader(640 * 1024 * 1024)
    entries, directory = central_directory(reader, url, archive["size"])
    chosen = []
    for item in entries:
        parts = item["name"].split("/")
        if len(parts) == 4 and parts[-1] == "audit.log" and parts[1] in roles and machine_name(parts[2]) in hosts[parts[1]]:
            chosen.append(item)
    selection = {"algorithm": "SHA256(casino-robustness-v1:instance), all114; splits60/18/18/18; annotated hosts only",
                 "splits": roles, "members": chosen}
    (root / "SELECTION.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    with ThreadPoolExecutor(max_workers=3) as pool:
        members = list(pool.map(lambda i: _fetch_audit(reader, url, archive["size"], i, root), chosen))
    receipt = {"record": RECORD, "source_url": url, "license": "CC-BY-4.0", "splits": roles,
               "central_directory": directory, "publisher_archive_checksum": archive["checksum"],
               "whole_syslogs_archive_checksum_verified": False, "members": members,
               "requested_range_bytes": reader.transferred,
               "label_archive_sha256": sha256(labels), "output_archive_sha256": sha256(output),
               "label_archive_publisher_md5_verified": True, "output_archive_publisher_md5_verified": True}
    (root / "ACQUISITION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"acquired_members": len(members), "range_bytes": reader.transferred}), flush=True)
    return receipt


def decode_value(value: str) -> str:
    if value.startswith(('"', "'")):
        return value[1:-1]
    if len(value) % 2 == 0 and len(value) >= 4 and re.fullmatch(r"[0-9a-fA-F]+", value):
        try:
            decoded = bytes.fromhex(value).decode("utf-8")
            if all(c.isprintable() or c in "\x00\t\r\n" for c in decoded):
                return decoded.replace("\x00", " ")
        except (ValueError, UnicodeDecodeError):
            pass
    return value


def fragment(raw: str, run: str, host: str, timestamp: float) -> dict:
    fields = dict(FIELD.findall(raw))
    local_identities = {value.casefold() for value in re.findall(
        r'(?<!\w)(?:AUID|UID|EUID|SUID|FSUID|acct)="([^"\n]+)"', raw)
        if value not in ("root", "unset", "?", "(unknown)") and not value.isdigit()}
    kind = fields.get("type", "UNKNOWN")
    keys = []
    for name, prefix in (("pid", "proc"), ("ppid", "proc"), ("ses", "session")):
        value = fields.get(name, "")
        if value.isdigit() and value not in ("0", "4294967295"):
            keys.append(f"{prefix}:{run}:{host}:{value}")
    parts = ["audit", kind.lower()]
    semantic = {"comm", "exe", "proctitle", "name", "cwd", "SYSCALL", "success", "res", "op", "terminal", "argc", "nametype"}
    for name, value in fields.items():
        if name in semantic or (kind == "EXECVE" and re.fullmatch(r"a\d+", name)):
            decoded = decode_value(value) if name in {"proctitle", "comm", "exe", "name", "cwd"} or kind == "EXECVE" else value.strip('"\'')
            decoded = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP", decoded)
            decoded = re.sub(r"\b(?:start|meetingcam|bastion|intranet)(?:[-.]\w+)*\b", "HOST", decoded)
            decoded = re.sub(r"\b(?:tbenedict|danny|rusty|linus|casino\w*)\b", "USER", decoded, flags=re.I)
            decoded = re.sub(r"/home/[^/\s]+", "/home/USER", decoded)
            decoded = re.sub(r"\b[A-Za-z_][\w.-]*@", "USER@", decoded)
            decoded = re.sub(r"((?:^|\s)(?:-u|--user|-l)(?:=|\s+))[A-Za-z_][\w.-]*", r"\1USER", decoded)
            decoded = re.sub(r"\b(?:flag|ctf|breizh)[a-z0-9_{}-]*\b", "CHALLENGE_MARKER", decoded, flags=re.I)
            decoded = re.sub(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", lambda m: "IDENTITY" if
                             m[0].casefold() == run.casefold() or m[0].casefold() in local_identities else m[0], decoded)
            def mask_ipv6(match):
                try:
                    ipaddress.IPv6Address(match[0])
                except ValueError:
                    return match[0]
                return "IP"
            decoded = re.sub(r"(?<![\w:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]+(?![\w:])", mask_ipv6, decoded)
            decoded = re.sub(r"\bT\d{4}(?:\.\d{3})?\b", "TECHNIQUE_MARKER", decoded, flags=re.I)
            decoded = re.sub(r"\b[0-9A-Fa-f]{16,}\b", "HEX", decoded)
            decoded = re.sub(r"\b\d+(?:\.\d+)?\b", "NUM", decoded)
            parts.append(name.lower() + "=" + decoded)
    for name in ("uid", "euid", "auid", "suid", "fsuid"):
        if name in fields:
            value = fields[name]
            parts.append(name + "=" + ("root" if value == "0" else "unset" if value == "4294967295" else "user"))
    return {"channel": kind.lower(), "text": " ".join(parts)[:8192],
            "baseline_text": normalized_text(raw, "audit"), "timestamp": timestamp,
            "available_at": timestamp, "entity_keys": sorted(set(keys))}


def _labels_for_host(labels: dict, host: str) -> tuple[dict, dict]:
    lookup = defaultdict(list)
    techniques = {}
    for annotation, value in labels.items():
        techniques[annotation] = value["technique"]
        for number in value["auditd_events"].get(host, []):
            lookup[str(number)].append(annotation)
    return lookup, techniques


def _raw_keys(raw: str, run: str, host: str) -> set[str]:
    return {f"{'session' if name == 'ses' else 'proc'}:{run}:{host}:{number}"
            for name, number in re.findall(r"(?<!\w)(pid|ppid|ses)=(\d+)", raw)
            if number not in ("0", "4294967295")}


def host_events(path: Path, run: str, host: str, role: str, labels: dict, lookback: float = 120.0):
    """Three streaming passes retain exactly replay-eligible prior context."""
    lookup, techniques = _labels_for_host(labels, host)
    earliest = {}
    earliest_keys = {}
    seen_ids = {}
    lines = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for raw in f:
            lines += 1
            match = AUDIT.search(raw)
            if not match:
                continue
            timestamp, number = float(match[1]), match[2]
            if number in lookup:
                if number in seen_ids and seen_ids[number] != timestamp:
                    raise ValueError("Label event ID is reused across different timestamps")
                seen_ids[number] = timestamp
                for annotation in lookup[number]:
                    candidate = (timestamp, int(number))
                    if annotation not in earliest or candidate < earliest[annotation]:
                        earliest[annotation] = candidate
                        earliest_keys[annotation] = _raw_keys(raw, run, host)
                    elif candidate == earliest[annotation]:
                        earliest_keys[annotation].update(_raw_keys(raw, run, host))
    targets = defaultdict(set)
    target_key_times = defaultdict(set)
    for annotation, (timestamp, number) in earliest.items():
        targets[(timestamp, str(number))].add(techniques[annotation])
        for key in earliest_keys[annotation]:
            target_key_times[key].add(timestamp)
    target_key_times = {key: sorted(times) for key, times in target_key_times.items()}
    target_times = sorted({t for t, _ in targets})
    candidates = set(targets)
    with path.open(encoding="utf-8", errors="replace") as f:
        for raw in f:
            match = AUDIT.search(raw)
            if not match:
                continue
            timestamp, number = float(match[1]), match[2]
            event_key = (timestamp, number)
            if event_key in candidates:
                continue
            position = bisect_left(target_times, timestamp)
            if position == len(target_times) or target_times[position] - timestamp > lookback:
                continue
            for key in _raw_keys(raw, run, host):
                times = target_key_times.get(key, [])
                position = bisect_left(times, timestamp)
                while position < len(times) and times[position] <= timestamp:
                    position += 1
                if position < len(times) and times[position] - timestamp <= lookback:
                    candidates.add(event_key)
                    break
    events = {}
    with path.open(encoding="utf-8", errors="replace") as f:
        for raw in f:
            match = AUDIT.search(raw)
            if not match:
                continue
            timestamp, number = float(match[1]), match[2]
            key = (timestamp, number)
            if key not in candidates:
                continue
            if key not in events:
                eligible = key in targets
                source_labels = sorted({techniques[a] for a in lookup.get(number, [])})
                # Supervision always uses all source technique memberships of
                # the selected onset event, including overlapping annotations.
                events[key] = {"event_id": f"casino:{run}:{host}:{number}:{timestamp}",
                               "run_id": run, "split": role, "timestamp": timestamp,
                               "available_at": timestamp, "entity_keys": [],
                               "labels": source_labels, "target_eligible": eligible,
                               "label_status": "source_annotated" if source_labels else "unlabeled_unknown",
                               "fragments": []}
            events[key]["fragments"].append(fragment(raw.rstrip(), run, host, timestamp))
    for event in events.values():
        event["entity_keys"] = sorted({key for frag in event["fragments"] for key in frag["entity_keys"]})
    stats = {"source_lines": lines, "annotated_audit_event_ids": len(lookup),
             "matched_annotated_audit_event_ids": len(seen_ids), "annotations_with_observed_onset": len(earliest),
             "target_events": len(targets), "retained_events": len(events),
             "retained_fragments": sum(len(e["fragments"]) for e in events.values())}
    return sorted(events.values(), key=lambda e: (e["timestamp"], e["event_id"])), stats


def _build_run(job: tuple) -> dict:
    root, run, role, members, staging = job
    with zipfile.ZipFile(root / "output.zip") as output, zipfile.ZipFile(root / "syslogs_labels.zip") as source_labels:
        labels = json.loads(source_labels.read(f"system_labels/{run}.json"))
        richer = json.loads(output.read(f"output/system_labels/{run}.json"))
    if not set(labels).issubset(richer):
        raise ValueError("Exported annotation IDs have no source process annotation")
    for annotation in labels:
        if labels[annotation]["technique"] != richer[annotation]["technique"]:
            raise ValueError("Exported technique disagrees with process annotation")
    doubtful = sum(bool(v.get("doubt")) for v in richer.values())
    labels = {k: v for k, v in labels.items() if not richer.get(k, {}).get("doubt", False)}
    events = []
    totals, counts, source_techniques = Counter(), Counter(), Counter()
    for item in members:
        parts = item["name"].split("/")
        path = root / item["name"]
        if sha256(path) != item["sha256"]:
            raise ValueError("Acquired source member changed")
        found, stats = host_events(path, run, machine_name(parts[2]), role, labels)
        totals.update(stats)
        events.extend(found)
    part = staging / (run + ".jsonl")
    with part.open("w", encoding="utf-8", newline="\n") as stream:
        for event in sorted(events, key=lambda e: (e["timestamp"], e["event_id"])):
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            counts["all_events"] += 1
            if event["target_eligible"]:
                counts["target_events"] += 1
                for label in event["labels"]:
                    source_techniques[label] += 1
                    counts[label.split(":", 1)[0]] += 1
    result = {"run": run, "split": role, "counts": dict(counts), "totals": dict(totals),
              "source_techniques": dict(source_techniques), "doubtful": doubtful,
              "part": str(part), "part_sha256": sha256(part), "part_bytes": part.stat().st_size}
    part.with_suffix(".stats.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def build(root: Path, destination: Path, workers: int = 2) -> dict:
    if destination.with_suffix(".receipt.json").exists() or (root / "FROZEN_EVENT_STREAM.json").exists():
        raise ValueError("Completed event evidence is immutable; use a fresh output and acquisition directory")
    acquisition = json.loads((root / "ACQUISITION.json").read_text(encoding="utf-8"))
    roles = acquisition["splits"]
    if workers not in (1, 2):
        raise ValueError("Use one or two bounded build workers")
    totals = Counter()
    split_counts = defaultdict(Counter)
    source_techniques = Counter()
    doubtful = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = root / "EVENT_BUILD_PARTS"
    staging.mkdir(exist_ok=True)
    jobs = [(root, run, role, [item for item in acquisition["members"] if item["name"].split("/")[1] == run], staging)
            for run, role in roles.items()]
    pending = destination.with_suffix(destination.suffix + ".part")
    pool = ProcessPoolExecutor(max_workers=workers) if workers == 2 else None
    results = pool.map(_build_run, jobs) if pool else map(_build_run, jobs)
    try:
        with pending.open("wb") as stream:
            for result in results:
                part = Path(result["part"])
                if sha256(part) != result["part_sha256"]:
                    raise ValueError("Completed worker part changed")
                with part.open("rb") as source:
                    shutil.copyfileobj(source, stream, 1024 * 1024)
                totals.update(result["totals"])
                split_counts[result["split"]].update(result["counts"])
                source_techniques.update(result["source_techniques"])
                doubtful += result["doubtful"]
                print(json.dumps({"run_complete": result["run"], "split": result["split"],
                                  "events": result["counts"].get("all_events", 0),
                                  "targets": result["counts"].get("target_events", 0)}), flush=True)
    finally:
        if pool:
            pool.shutdown(wait=True, cancel_futures=True)
    pending.replace(destination)
    receipt = {"dataset": "CasinoLimit", "record": RECORD, "paper_doi": "10.1109/RAID67961.2025.00039",
               "dataset_url": f"https://zenodo.org/records/{RECORD}", "license": "CC-BY-4.0",
               "acquisition_sha256": sha256(root / "ACQUISITION.json"), "events_sha256": sha256(destination),
               "adapter_sha256": sha256(Path(__file__)),
               "totals": dict(totals), "split_counts": {k: dict(v) for k, v in split_counts.items()},
               "source_techniques_on_targets": dict(source_techniques), "doubtful_annotations_excluded": doubtful,
               "selection": "All114 SHA256(casino-robustness-v1:instance), splits60/18/18/18; annotated hosts; first observed audit event per annotation+host is target; retain every complete event strictly within120s before a target sharing a full-event entitykey. Visible-fragment joins remain mandatory in replay.",
               "prefit_amendment": "Initial24-instance acquisition qualified but no Casino model fitted. ZeroT1068 and oneT1548 test source annotation triggered source-only support qualification of all114. Expanded cohort frozen before Casino fitting, preserving hash order and no model-performance selection.",
               "prediction_unit": "complete audit event at source annotation onset; target supervision inherited from process-technique annotation",
               "target_ids_frozen": list(TARGET_IDS), "splits": roles,
               "availability": "All audit fragments use source event epoch; no arrival time. This is idealized complete-event availability, with synthetic perturbation only.",
               "causal_context": "Consumer must use strictly earlier source timestamps and fragment-specific visible entity keys; event-wide keys metadata only.",
               "feature_policy": "Casino retains lexical command/path arguments after fixed syntax and fragment-local identity masking, plus run IDs, addresses, numbers, long hex and technique/challenge markers. No full-file identity dictionary. It differs from AIT fixed vocabulary; absolute scores are not directly comparable and shared challenge-template shortcuts or unrecognized identity syntax remain possible.",
               "annotation_join": "Exact label IDs and technique strings verified between direct event export and richer process annotations; source-doubt annotations excluded.",
               "limitations": ["One repeated CTF challenge; collected May2024, published2025.",
                               "Instance-held-out only: repeated players may cross splits; player mapping unavailable.",
                               "Source process annotations, not independent event gold labels; unannotated is unknown, never benign.",
                               "Selected host windows near source-annotated onsets; not continuous deployment or operational false-positive evaluation.",
                               "No natural collection/arrival timestamps; missing and delayed telemetry are controlled simulations.",
                               "Technique recognition and within-dataset replication; no named APT actor attribution or cross-dataset transfer claim."]}
    destination.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (root / "FROZEN_EVENT_STREAM.json").write_text(json.dumps({
        "event_path": str(destination.resolve()), "events_sha256": receipt["events_sha256"],
        "event_receipt_sha256": sha256(destination.with_suffix(".receipt.json")),
        "acquisition_sha256": receipt["acquisition_sha256"],
        "adapter_sha256": receipt["adapter_sha256"]}, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if args.acquire:
        acquire(args.root)
    if args.output:
        result = build(args.root, args.output, args.workers)
        print(json.dumps({"complete": True, "totals": result["totals"], "split_counts": result["split_counts"]}), flush=True)


if __name__ == "__main__":
    main()
