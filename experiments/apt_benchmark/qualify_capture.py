"""Qualify cAPTure metadata without fitting models or publishing packet content.

Acquisition hashes establish local byte consistency, not author authenticity.
All columns are read as text; no pickle or author code is executed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

METADATA_COLUMNS = ("phase_name", "sequence_id", "label", "timestamp")
FEATURE_COLUMNS = (
    "layers_mqtt_mqtt.hdrflags", "layers_tcp_tcp.seq",
    "layers_tcp_tcp.completeness", "layers_tcp_tcp.len",
    "layers_frame_frame.protocols", "layers_tcp_tcp.ack",
    "layers_tcp_tcp.window_size", "layers_tcp_tcp.nxtseq",
    "layers_tcp_tcp.hdr_len", "layers_mqtt_mqtt.msgid",
    "layers_tcp_tcp.analysis_tcp.analysis.push_bytes_sent",
    "layers_ip_ip.version", "layers_eth_eth.dst_tree_eth.dst.ig",
    "layers_eth_eth.type", "layers_mqtt_mqtt.hdrflags_tree_mqtt.msgtype",
    "layers_tcp_tcp.flags_tree_tcp.flags.str", "layers_ip_ip.len",
    "layers_eth_eth.dst_tree_eth.addr", "layers_tcp_tcp.payload",
    "layers_tcp_tcp.analysis_tcp.analysis.initial_rtt",
    "layers_mqtt_mqtt.hdrflags_tree_mqtt.qos", "layers_ip_ip.flags",
    "layers_tcp_tcp.window_size_value", "layers_frame_frame.len",
    "layers_tcp_tcp.analysis_tcp.analysis.bytes_in_flight",
)
EXPECTED_COLUMNS = FEATURE_COLUMNS + METADATA_COLUMNS
PHASES = frozenset({"RECONNAISSANCE", "BRUTE_FORCE", "DISCOVERY", "INSTALLATION", "EXPLOIT"})
ATTACK_LABELS = frozenset({
    "nmap_10_T5", "brute_force_malformed", "mqtt_cat", "nmap_mqtt",
    "scp_inst", "dollar_char", "nmap_banner", "nmap_sub", "sftp_inst",
    "empty_conn", "empty_conn_ddos", "nmap_10_T4", "pub_exf", "sftp_exf",
    "qos_mid", "qos_mid_ddos", "brute_force_timing", "slash_char",
    "scp_exf", "user_prop_ddos",
})
FILES = ("train_set_reduced.csv", "test_set_reduced.csv")
LIMITATIONS = [
    "Reduced 25-feature selection and row-generation provenance remain unverified.",
    "Rows, step IDs and scenario templates are not independent real-world campaigns.",
    "Separate data license not verified; do not redistribute raw data.",
    "TCP completeness and tcp.analysis fields quarantined until causal availability is established.",
    "Author phase labels are not asserted to map one-to-one to all ATT&CK tactics.",
    "Timeline is shifted/concatenated emulation time, not real calendar-time coverage.",
    "Metadata consistency is not a human ground-truth audit or detector-efficacy result.",
]


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def qualify_file(path: Path, receipt_path: Path | None = None, chunksize: int = 100_000) -> dict:
    """Return aggregate validation; invalid/missing labels never become benign.

    Raises only for unreadable/malformed files or invalid invocation. Content
    validation failures are recorded, and the CLI returns nonzero after saving.
    """
    path = Path(path)
    if chunksize < 1:
        raise ValueError("chunksize must be positive")
    receipt_path = receipt_path or path.with_name(path.name + ".receipt.json")
    before = path.stat()
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    actual_hash = _sha256(path)
    issues = []
    if receipt.get("file") != path.name:
        issues.append("receipt_filename_mismatch")
    if receipt.get("bytes") != before.st_size:
        issues.append("receipt_size_mismatch")
    if receipt.get("sha256") != actual_hash:
        issues.append("receipt_sha256_mismatch")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    result = {
        "file": path.name, "bytes": before.st_size, "sha256": actual_hash,
        "receipt_sha256": _sha256(Path(receipt_path)),
        "source_receipt_verified": not issues,
        "schema_exact": tuple(header) == EXPECTED_COLUMNS,
        "column_count": len(header), "feature_column_count": len(FEATURE_COLUMNS),
        "metadata_excluded_from_features": list(METADATA_COLUMNS),
        "sequence_id_dtype": "string", "issues": issues,
    }
    if tuple(header) != EXPECTED_COLUMNS:
        issues.append("unexpected_schema")
        result["validation_ok"] = False
        return result
    labels, phases, missing, invalid = Counter(), Counter(), Counter(), Counter()
    seq_pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    numeric_ids: dict[Decimal, set[str]] = defaultdict(set)
    row_count = attack_count = normal_count = unknown_count = 0
    regressions = equal_timestamps = 0
    prior_time = None
    first_time = last_time = None
    for chunk in pd.read_csv(path, dtype=str, keep_default_na=False,
                             na_filter=False, chunksize=chunksize):
        row_count += len(chunk)
        label, phase, seq = chunk["label"], chunk["phase_name"], chunk["sequence_id"]
        for column in METADATA_COLUMNS:
            missing[column] += int(chunk[column].str.strip().eq("").sum())
        labels.update(label.where(label.ne(""), "<missing>").value_counts().to_dict())
        phases.update(phase.where(phase.ne(""), "<missing>").value_counts().to_dict())
        normal = label.eq("normal")
        attack = label.isin(ATTACK_LABELS)
        unknown = ~(normal | attack)
        normal_count += int(normal.sum())
        attack_count += int(attack.sum())
        unknown_count += int(unknown.sum())
        invalid["unknown_or_missing_label"] += int(unknown.sum())
        invalid["attack_missing_or_unknown_phase"] += int((attack & ~phase.isin(PHASES)).sum())
        invalid["attack_missing_sequence_id"] += int((attack & seq.str.strip().eq("")).sum())
        invalid["normal_with_phase"] += int((normal & phase.ne("")).sum())
        invalid["normal_with_sequence_id"] += int((normal & seq.ne("")).sum())
        for row in chunk.loc[attack & seq.ne(""), ["sequence_id", "label", "phase_name"]].drop_duplicates().itertuples(index=False, name=None):
            sid, step, stage = row
            seq_pairs[sid].add((step, stage))
            if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", sid):
                numeric_ids[Decimal(sid)].add(sid)
        stamp = chunk["timestamp"]
        aware = stamp.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True)
        parsed = pd.to_datetime(stamp, utc=True, errors="coerce", format="mixed")
        invalid["invalid_or_naive_timestamp"] += int((parsed.isna() | ~aware).sum())
        valid = parsed[parsed.notna() & aware]
        if len(valid):
            values = valid.astype("int64").to_numpy()
            regressions += int((values[1:] < values[:-1]).sum())
            equal_timestamps += int((values[1:] == values[:-1]).sum())
            if prior_time is not None:
                regressions += int(values[0] < prior_time)
                equal_timestamps += int(values[0] == prior_time)
            prior_time = int(values[-1])
            first_time = first_time or valid.iloc[0].isoformat()
            last_time = valid.iloc[-1].isoformat()
    invalid["timestamp_regressions"] = regressions
    invalid["sequence_label_or_phase_conflicts"] = sum(len(pairs) > 1 for pairs in seq_pairs.values())
    if not row_count:
        issues.append("empty_table")
    issues.extend(name for name, count in invalid.items() if count)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        issues.append("source_changed_during_qualification")
    result.update({
        "rows": row_count, "label_counts": dict(sorted(labels.items())),
        "phase_counts": dict(sorted(phases.items())),
        "normal_rows": normal_count, "recognized_attack_rows": attack_count,
        "unknown_label_rows": unknown_count,
        "missing_counts": dict(sorted(missing.items())),
        "invalid_counts": dict(sorted(invalid.items())),
        "distinct_attack_step_ids_as_strings": len(seq_pairs),
        "numeric_equivalence_collision_groups": sum(len(ids) > 1 for ids in numeric_ids.values()),
        "timestamp_monotone_nondecreasing_utc": regressions == 0 and not invalid["invalid_or_naive_timestamp"],
        "equal_adjacent_timestamps": equal_timestamps,
        "first_timestamp_utc": first_time, "last_timestamp_utc": last_time,
        "validation_ok": not issues,
    })
    return result


def qualify_directory(root: Path, output: Path, chunksize: int = 100_000) -> dict:
    results = []
    for filename in FILES:
        result = qualify_file(root / filename, chunksize=chunksize)
        results.append(result)
        print(f"{filename}: rows={result.get('rows', 0)}, validation_ok={result['validation_ok']}", flush=True)
    report = {
        "schema_version": 1, "dataset": "cAPTure",
        "script_sha256": _sha256(Path(__file__)),
        "status": "CONSISTENCY_CHECKS_PASS_WITH_LIMITS" if all(r["validation_ok"] for r in results) else "CONSISTENCY_CHECKS_FAILED",
        "files": results, "limitations": LIMITATIONS,
        "model_fitted": False, "human_label_audit": False,
        "independent_campaign_count": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunksize", type=int, default=100_000)
    args = parser.parse_args()
    report = qualify_directory(args.data_dir, args.output, args.chunksize)
    return 0 if report["status"] == "CONSISTENCY_CHECKS_PASS_WITH_LIMITS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
