"""Qualify author host logs without exposing message text or using stage labels.

Writes private, numeric/event-kind-only arrays. Windows exported times require
same-file UTC anchors; no timezone is inferred from model scores or stage labels.
"""
from __future__ import annotations

import argparse
import collections
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import numpy as np

KIND_NAMES = (
    "linux_auth_success", "linux_auth_failure", "linux_login_success",
    "linux_login_failure", "linux_session_start", "linux_session_end",
    "windows_logon_network_success", "windows_logon_remoteinteractive_success",
    "windows_logon_other_success", "windows_logon_failure",
    "windows_explicit_credentials_attempt",
)
KIND_INDEX = {v: i for i, v in enumerate(KIND_NAMES)}
STAGES = {"Benign", "Reconnaissance", "Establish Foothold", "Maintain Access",
          "Lateral Movement", "Data Exfiltration", "Cover up", "Cover-Up"}
WIN_START = re.compile(
    r"(?m)^([^,\r\n]+),(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [AP]M),"
    r"([^,\r\n]+),(\d+),"
)
AUDIT_START = re.compile(
    r"^(?:node=\S+\s+)?type=([A-Z_0-9]+)\s+msg=audit\((\d+(?:\.\d+)?):(\d+)\)"
)
PILOT_START_MS = datetime(2021, 6, 21, tzinfo=timezone.utc).timestamp() * 1000
PILOT_END_MS = datetime(2021, 7, 7, tzinfo=timezone.utc).timestamp() * 1000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean_line(line: str) -> str:
    """Remove only the known author wrapper; never emit its labels as features."""
    value = line.rstrip("\r\n")
    parts = value.rsplit(",", 4)
    if (len(parts) == 5 and parts[-3] in STAGES
            and parts[-2] in {"Benign", "Detected", "Mitigated"}
            and parts[-1].strip('"') in {"None", "APT", "AA", "SH", "nan"}):
        value = parts[0]
    # Unicode directional marks obstruct the UTC timestamp in these exports.
    return "".join(c for c in value if unicodedata.category(c) != "Cf").strip()


def host_from_name(path: Path) -> str:
    match = re.match(r"(\d+_\d+_\d+_\d+)-", path.name)
    if not match:
        raise ValueError(f"No host key in source filename: {path.name}")
    return match[1].replace("_", ".")


def utc_ms(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000


def windows_records(path: Path):
    text = "\n".join(clean_line(v) for v in path.read_text(encoding="utf-8-sig").splitlines())
    matches = list(WIN_START.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        local_ms = datetime.strptime(match[2], "%m/%d/%Y %I:%M:%S %p").replace(
            tzinfo=timezone.utc).timestamp() * 1000
        payload = text[match.end():end].strip()
        yield {"local_ms": local_ms, "event_id": int(match[4]),
               "provider": match[3], "keyword": match[1], "payload": payload}


def qualify_windows_clock(records: list[dict]) -> dict:
    anchors = []
    for record in records:
        if record["event_id"] != 4616:
            continue
        match = re.search(r"New Time:\s*([0-9T:.\-]+Z)", record["payload"])
        if not match:
            continue
        new_ms = utc_ms(match[1])
        old = re.search(r"Previous Time:\s*([0-9T:.\-]+Z)", record["payload"])
        offset_ms = round((new_ms - record["local_ms"]) / 60000) * 60000
        anchors.append({"utc_new_ms": new_ms, "displayed_local_ms": record["local_ms"],
                        "offset_ms": offset_ms,
                        "fractional_residual_ms": new_ms - record["local_ms"] - offset_ms,
                        "clock_change_ms": new_ms - utc_ms(old[1]) if old else None})
    if len(anchors) < 3 or len({int(x["utc_new_ms"] // 86400000) for x in anchors}) < 2:
        raise ValueError("Windows clock has insufficient independent UTC anchors")
    offsets = {x["offset_ms"] for x in anchors}
    if len(offsets) != 1 or any(abs(x["fractional_residual_ms"]) > 1001 for x in anchors):
        raise ValueError("Windows clock has inconsistent export offsets")
    pilot = [x for x in anchors if PILOT_START_MS <= x["utc_new_ms"] < PILOT_END_MS]
    return {"status": "PASS_EXPORT_TIMEZONE", "utc_offset_added_ms": offsets.pop(),
            "availability_guard_ms": 1000, "anchor_count": len(anchors),
            "minimum_anchor_utc_ms": min(x["utc_new_ms"] for x in anchors),
            "maximum_anchor_utc_ms": max(x["utc_new_ms"] for x in anchors),
            "maximum_abs_fractional_residual_ms": max(abs(x["fractional_residual_ms"]) for x in anchors),
            "maximum_abs_clock_change_ms": max((abs(x["clock_change_ms"]) for x in anchors if x["clock_change_ms"] is not None), default=0),
            "pilot_maximum_abs_clock_change_ms": max((abs(x["clock_change_ms"]) for x in pilot if x["clock_change_ms"] is not None), default=0),
            "anchors": anchors,
            "meaning": "Exported local-time representation qualified; collection/export latency and absolute host synchronization are not certified."}


def windows_kind(record: dict) -> str | None:
    event_id = record["event_id"]
    if event_id == 4624:
        match = re.search(r"\bLogon Type:\s*(\d+)\b", record["payload"])
        if not match:
            raise ValueError("Successful logon lacks a parseable Logon Type")
        return {3: "windows_logon_network_success", 10: "windows_logon_remoteinteractive_success"}.get(
            int(match[1]), "windows_logon_other_success")
    if event_id == 4625:
        return "windows_logon_failure"
    if event_id == 4648:
        return "windows_explicit_credentials_attempt"
    return None


def linux_kind(event_type: str, result: str | None) -> str | None:
    if event_type in {"USER_AUTH", "USER_LOGIN"}:
        if result not in {"success", "failed"}:
            raise ValueError("Authentication record has unknown outcome")
        prefix = "linux_auth_" if event_type == "USER_AUTH" else "linux_login_"
        return prefix + ("success" if result == "success" else "failure")
    if event_type in {"USER_START", "USER_END"} and result == "success":
        return "linux_session_start" if event_type == "USER_START" else "linux_session_end"
    return None


def linux_records(path: Path):
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            text = clean_line(line).lstrip('"')
            match = AUDIT_START.match(text)
            if not match:
                if text.startswith("type="):
                    raise ValueError(f"Malformed audit event header in {path.name}")
                continue  # Author header and translated-account continuation lines.
            result = re.search(r"\bres=(success|failed)\b", text)
            event_type = match[1]
            yield {"record_time_ms": float(match[2]) * 1000,
                   "event_type": event_type, "serial": match[3],
                   "result": result[1] if result else None,
                   "kind": linux_kind(event_type, result[1] if result else None)}


def strict_earlier_window_count(times_ms: np.ndarray, query_ms: float, window_ms: float) -> int:
    """Reference boundary rule: [query-window, query), including no equal-time row."""
    times = np.asarray(times_ms, dtype=np.float64)
    if len(times) > 1 and np.any(times[1:] < times[:-1]):
        raise ValueError("History timestamps must be sorted")
    return int(np.searchsorted(times, query_ms, side="left") -
               np.searchsorted(times, query_ms - window_ms, side="left"))


def write_arrays(path: Path, rows: list[dict], event_only: bool):
    ordered = sorted(rows, key=lambda r: (r["time_ms"], r["host"], r["event_sha256"]))
    arrays = {"host": np.asarray([r["host"] for r in ordered], dtype=str),
              "time_ms": np.asarray([r["time_ms"] for r in ordered], dtype=np.float64),
              "record_time_ms": np.asarray([r["record_time_ms"] for r in ordered], dtype=np.float64),
              "family": np.asarray([r["family"] for r in ordered], dtype=str),
              "event_sha256": np.asarray([r["event_sha256"] for r in ordered], dtype=str)}
    if event_only:
        arrays["kind"] = np.asarray([KIND_INDEX[r["kind"]] for r in ordered], dtype=np.int16)
        arrays["kind_names"] = np.asarray(KIND_NAMES, dtype=str)
    assert all(v.dtype.kind != "O" for v in arrays.values())
    np.savez_compressed(path, **arrays)


def qualify(root: Path, out: Path, linux_only: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    observed = {}
    sources = []
    clocks = {}
    type_counts = collections.defaultdict(collections.Counter)
    for path in sorted((root / "audit").glob("*audit*")):
        host = host_from_name(path)
        count = duplicates = 0
        for parsed in linux_records(path):
            count += 1
            type_counts[host][parsed["event_type"]] += 1
            identity = f"{host}|linux_audit|{parsed['record_time_ms']:.3f}|{parsed['serial']}|{parsed['event_type']}"
            key = hashlib.sha256(identity.encode()).hexdigest()
            row = {"host": host, "time_ms": parsed["record_time_ms"],
                   "record_time_ms": parsed["record_time_ms"], "family": "linux_audit",
                   "event_sha256": key, "kind": parsed["kind"]}
            if key in observed:
                if observed[key] != row:
                    raise ValueError("Conflicting audit record identity")
                duplicates += 1
            else:
                observed[key] = row
        sources.append({"source_file": path.relative_to(root).as_posix(), "host": host,
                        "family": "linux_audit", "sha256": sha256(path), "bytes": path.stat().st_size,
                        "parsed_records": count, "duplicate_records": duplicates})
    for path in sorted((root / "windows").glob("*security*")):
        host = host_from_name(path)
        records = list(windows_records(path))
        clock = qualify_windows_clock(records)
        clocks[path.name] = clock
        duplicates = 0
        for record in records:
            if record["provider"] != "Microsoft-Windows-Security-Auditing" and record["event_id"] not in {1100, 1101, 1108}:
                raise ValueError("Unexpected Windows Security provider")
            type_counts[host][str(record["event_id"])] += 1
            kind = windows_kind(record)
            canonical = json.dumps([host, record["local_ms"], record["event_id"],
                                    record["provider"], record["keyword"], record["payload"]],
                                   ensure_ascii=False, separators=(",", ":"))
            key = hashlib.sha256(canonical.encode()).hexdigest()
            record_ms = record["local_ms"] + clock["utc_offset_added_ms"]
            row = {"host": host, "record_time_ms": record_ms,
                   "time_ms": record_ms + clock["availability_guard_ms"],
                   "family": "windows_security", "event_sha256": key, "kind": kind}
            if key in observed:
                if observed[key] != row:
                    raise ValueError("Conflicting Windows canonical event")
                duplicates += 1
            else:
                observed[key] = row
        sources.append({"source_file": path.relative_to(root).as_posix(), "host": host,
                        "family": "windows_security", "sha256": sha256(path), "bytes": path.stat().st_size,
                        "parsed_records": len(records), "duplicate_records": duplicates})
    rows = list(observed.values())
    excluded = [r for r in rows if linux_only and r["family"] == "windows_security"]
    rows = [r for r in rows if not linux_only or r["family"] == "linux_audit"]
    events = [r for r in rows if r["kind"] is not None]
    write_arrays(out / "EVENTS.npz", events, True)
    write_arrays(out / "OBSERVED.npz", rows, False)
    host_summary = {}
    for host in sorted({r["host"] for r in rows}):
        rr = [r for r in rows if r["host"] == host]
        tt = np.sort(np.asarray([r["time_ms"] for r in rr]))
        daily_observed = collections.Counter(datetime.fromtimestamp(r["time_ms"] / 1000, timezone.utc).date().isoformat() for r in rr)
        daily_events = collections.defaultdict(collections.Counter)
        for r in rr:
            if r["kind"]:
                daily_events[datetime.fromtimestamp(r["time_ms"] / 1000, timezone.utc).date().isoformat()][r["kind"]] += 1
        host_summary[host] = {"family": rr[0]["family"], "observed_records": len(rr),
                              "auth_context_records": sum(r["kind"] is not None for r in rr),
                              "kind_counts": dict(collections.Counter(r["kind"] for r in rr if r["kind"])),
                              "minimum_time_ms": float(tt[0]), "maximum_time_ms": float(tt[-1]),
                              "maximum_between_record_gap_seconds": float(np.diff(tt).max() / 1000) if len(tt) > 1 else None,
                              "daily_observed_counts": dict(sorted(daily_observed.items())),
                              "daily_kind_counts": {k: dict(v) for k, v in sorted(daily_events.items())},
                              "raw_type_counts_before_dedup": dict(type_counts[host])}
    receipt = {"schema_version": 1, "status": "QUALIFIED_LINUX_RECORD_TIME_REPLAY_WINDOWS_EXCLUDED" if linux_only else "PARSED_CLOCK_QUALIFIED_PENDING_CONTINUITY_REVIEW",
               "approved_for_event_time_replay": linux_only,
               "source_root": str(root.resolve()),
               "excluded_after_dedup": len(excluded),
               "excluded_by_host": dict(collections.Counter(r["host"] for r in excluded)),
               "scope_gate": "All Windows records excluded from predictors. Export timezone anchors do not resolve large host-clock changes or establish cross-host synchronization. Linux audit epoch records support only retrospective recorded-time replay; absolute synchronization and ingestion latency remain unverified." if linux_only else "Clock continuity and cross-clock joins unresolved.",
               "parser_sha256": sha256(Path(__file__)), "sources": sources,
               "windows_clocks": clocks, "host_summary": host_summary,
               "observed_records": len(rows), "auth_context_records": len(events),
               "kind_names": list(KIND_NAMES), "artifact_sha256": {n: sha256(out / n) for n in ["EVENTS.npz", "OBSERVED.npz"]},
               "time_policy": {"linux_audit": "Explicit Unix epoch milliseconds.",
                               "windows_security": "Same-file4616UTC anchors determine export offset; time_ms adds1000ms to second-resolution record_time_ms.",
                               "query": "time_ms < flow first packet; window left boundary inclusive.",
                               "latency": "No ingestion or exporter delay measured; event-time replay only."},
               "coverage": "A prior observed event is evidence of past visibility only; gaps/absence are not proof of complete collection or zero activity.",
               "dedup": {"linux": "host, exact epoch, audit serial and type; inconsistent semantic identity fails.",
                         "windows": "host, export time, provider, keyword, event ID and complete normalized message excluding author annotations; no exported EventRecordID available. Identical same-second events are conservatively indistinguishable."},
               "labels_or_credentials_in_arrays": False, "model_fits": 0}
    (out / "QUALIFICATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--linux-only", action="store_true", help="Exclude every Windows record from predictors; retain clock audit evidence")
    args = parser.parse_args()
    receipt = qualify(args.source, args.out, args.linux_only)
    print(json.dumps({k: receipt[k] for k in ["status", "observed_records", "auth_context_records", "artifact_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
