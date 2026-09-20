"""Bounded, standard-library E0 audit. This does not certify campaign independence.

Raw telemetry stays outside the experiment repository. Output contains aggregate
statistics, field names, hashes, and public dataset-relative file paths only.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time

VERSION = "1.0.0"
MIN_EPOCH = 946684800.0
MAX_EPOCH = 4102444800.0
HOST_RE = re.compile(r"^(\d{1,3}(?:_\d{1,3}){3})-")
AUDIT_RE = re.compile(r"audit\((\d{10}(?:\.\d+)?):")
OFFSET_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})")
STAGES = {"benign", "reconnaissance", "establish foothold", "lateral movement", "data exfiltration", "cover up", "cover-up", "maintain access"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def epoch_seconds(value: str | float, unit: str) -> float:
    """Convert only an explicit unit; reject likely unit errors and nonfinite data."""
    if unit not in {"s", "ms"}:
        raise ValueError("An explicit s or ms timestamp unit is required")
    result = float(value) / (1000 if unit == "ms" else 1)
    if not math.isfinite(result) or not MIN_EPOCH <= result <= MAX_EPOCH:
        raise ValueError("Timestamp outside 2000-2100; check units and source")
    return result


def host_timestamp(message: str) -> tuple[float | None, str]:
    audit = AUDIT_RE.search(message)
    if audit:
        return epoch_seconds(audit.group(1), "s"), "audit_epoch_seconds"
    offset = OFFSET_RE.search(message)
    if offset:
        parsed = datetime.fromisoformat(offset.group().replace("Z", "+00:00"))
        return epoch_seconds(parsed.timestamp(), "s"), "explicit_timezone_iso"
    return None, "no_unambiguous_absolute_time"


def interval_candidates(flows: list[dict], events: list[dict], tolerance: float = 0.0) -> dict:
    """Count candidate coincidences, never claim these are validated causal joins.

    Event IDs must be unique. Multiple candidates remain ambiguous; one arbitrary
    candidate is never picked. A source/destination host appearing twice is deduped.
    """
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Nonnegative finite tolerance required")
    by_host: dict[str, list] = defaultdict(list)
    seen_events = set()
    for event in events:
        if event["id"] in seen_events:
            raise ValueError("Duplicate event IDs invalidate candidate counts")
        seen_events.add(event["id"])
        by_host[event["host"]].append((event["time"], event["id"]))
    for values in by_host.values():
        values.sort()
    seen_flows = set()
    multiplicity = Counter()
    pairs = 0
    matched_events = set()
    for flow in flows:
        if flow["id"] in seen_flows:
            raise ValueError("Duplicate flow IDs invalidate candidate counts")
        seen_flows.add(flow["id"])
        if flow["end"] < flow["start"]:
            raise ValueError("Negative flow interval")
        candidates = set()
        for host in set(flow["hosts"]):
            values = by_host.get(host, [])
            left = bisect_left(values, (flow["start"] - tolerance, ""))
            right = bisect_right(values, (flow["end"] + tolerance, chr(0x10FFFF)))
            candidates.update(item[1] for item in values[left:right])
        multiplicity["none" if not candidates else "one" if len(candidates) == 1 else "multiple"] += 1
        pairs += len(candidates)
        matched_events.update(candidates)
    return {
        "eligible_sampled_flows": len(flows),
        "eligible_sampled_host_events": len(events),
        "flow_candidate_multiplicity": dict(multiplicity),
        "candidate_pairs": pairs,
        "distinct_candidate_events": len(matched_events),
        "candidate_overlap_fraction": (len(flows) - multiplicity["none"]) / len(flows) if flows else None,
        "validated_join_rate": None,
        "timestamp_skew_distribution": None,
        "meaning": "Descriptive coincidence in nonrepresentative prefix samples; not a join success rate or clock-skew estimate.",
    }


def stage_group_counts(rows: list[dict]) -> dict:
    """Keep row counts separate from evidence-backed independent groups."""
    row_counts, groups = Counter(), defaultdict(set)
    for row in rows:
        key = (row["split"], str(row["label"]))
        row_counts[key] += 1
        if row.get("group_id"):
            groups[key].add(row["group_id"])
    return {f"{split}/{label}": {"rows": n, "distinct_group_ids": len(groups[(split, label)])}
            for (split, label), n in sorted(row_counts.items())}


def hold_reasons(*, join_verified: bool, clock_verified: bool, campaign_verified: bool,
                 independent_stage_counts_verified: bool) -> list[str]:
    checks = {
        "JOIN_INTEGRITY_UNVERIFIED": join_verified,
        "CLOCK_ALIGNMENT_UNVERIFIED": clock_verified,
        "CAMPAIGN_INDEPENDENCE_UNVERIFIED": campaign_verified,
        "INDEPENDENT_STAGE_SUPPORT_UNVERIFIED": independent_stage_counts_verified,
    }
    return [name for name, passed in checks.items() if not passed]


def raw_samples(root: Path, limit: int, byte_limit: int) -> tuple[list, list, list, list]:
    receipts, summaries, flows, events = [], [], [], []
    for family in ("network-flows", "host-logs"):
        for path in sorted((root / family).rglob("*")):
            if not path.is_file():
                continue
            with path.open("rb") as stream:
                prefix = stream.read(byte_limit)
            # Discard a final partial physical line in bounded prefixes.
            complete = len(prefix) == path.stat().st_size
            parse_bytes = prefix if complete else prefix[:prefix.rfind(b"\n") + 1]
            text = parse_bytes.decode("utf-8-sig", errors="replace")
            relative = path.relative_to(root).as_posix()
            source_id = hashlib.sha256(relative.encode()).hexdigest()[:20]
            receipt = {"relative_path": relative, "family": family,
                       "source_bytes": path.stat().st_size, "source_mtime_ns": path.stat().st_mtime_ns,
                       "prefix_bytes_read": len(prefix), "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                       "full_source_hashed": complete, "sample_strategy": "first_records_from_byte_bounded_prefix"}
            row_count, malformed, time_kinds, stages = 0, 0, Counter(), Counter()
            lines = text.splitlines()
            header = next(csv.reader(lines[:1]), [])
            host_match = HOST_RE.match(path.name)
            host = host_match.group(1).replace("_", ".") if host_match else None
            if family == "host-logs" and header == ["LogEvent", "Activity", "Stage", "DefenderResponse", "Signature"]:
                # These source records may contain unquoted commas. The four
                # documented rightmost labels are parsed only when Stage matches.
                for index, line in enumerate(lines[1:limit + 1], 1):
                    row_count += 1
                    parts = line.rsplit(",", 4)
                    if len(parts) != 5 or parts[2].strip().lower() not in STAGES:
                        malformed += 1
                        continue
                    stages[parts[2].strip().lower()] += 1
                    try:
                        stamp, kind = host_timestamp(parts[0])
                    except (ValueError, OverflowError):
                        stamp, kind = None, "invalid_timestamp"
                    time_kinds[kind] += 1
                    if host and stamp is not None:
                        events.append({"id": f"{source_id}:{index}", "host": host, "time": stamp})
                mode = "physical_lines_rightmost_four_labels; no multiline recovery"
            else:
                reader = csv.DictReader(io.StringIO(text))
                for index, row in enumerate(reader, 1):
                    if index > limit:
                        break
                    row_count += 1
                    if None in row or any(value is None for value in row.values()):
                        malformed += 1
                    label = (row.get("Stage") or "").strip().lower()
                    stages[label or "undeclared_or_empty_label"] += 1
                    if family == "network-flows":
                        try:
                            start = epoch_seconds(row["bidirectional_first_seen_ms"], "ms")
                            end = epoch_seconds(row["bidirectional_last_seen_ms"], "ms")
                            if end < start:
                                raise ValueError("Negative interval")
                            flows.append({"id": f"{source_id}:{index}", "start": start, "end": end,
                                          "hosts": [row["src_ip"], row["dst_ip"]]})
                            time_kinds["explicit_epoch_ms_interval"] += 1
                        except (ValueError, TypeError, KeyError):
                            time_kinds["invalid_or_missing_interval"] += 1
                    else:
                        time_kinds["naive_or_undeclared_time_not_joined"] += 1
                mode = "csv_records; extra undeclared fields not treated as labels"
            receipt["records_examined"] = row_count
            receipts.append(receipt)
            summaries.append({"relative_path": relative, "family": family, "fields": header,
                              "records_examined": row_count, "schema_or_label_failures": malformed,
                              "timestamp_kinds": dict(time_kinds), "sample_stage_counts": dict(stages),
                              "parser": mode, "host_identifier_from_documented_filename_convention": bool(host)})
    return receipts, summaries, flows, events


def cache_counts(workspace: Path) -> tuple[dict, list]:
    cache = workspace / "data/processed/unraveled_v02/benchmark_cache.csv"
    metadata = cache.with_name("benchmark_cache_metadata.json")
    old_split = workspace / "runs/praxisv03-unraveled-verify-stagebalanced-reset-deltas-20260423/preprocess-summary.json"
    receipts = [{"relative_path": str(path.relative_to(workspace)).replace("\\", "/"),
                 "source_bytes": path.stat().st_size, "sha256": sha256(path), "hash_scope": "full_file"}
                for path in (cache, metadata, old_split)]
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    summary = json.loads(old_split.read_text(encoding="utf-8"))
    membership = {}
    for split, values in summary["stage_balanced_split"]["split_groups"].items():
        for value in values:
            if value in membership:
                raise ValueError("Duplicate capture-day split membership")
            membership[value] = split
    stages, split_stages, day_counts, signature_counts = Counter(), defaultdict(Counter), Counter(), Counter()
    split_sensors, split_signatures, day_stages = defaultdict(set), defaultdict(Counter), defaultdict(Counter)
    label_missing = unmapped = count = 0
    with cache.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        for row in reader:
            count += 1
            stage = row["StageClean"].strip().lower()
            label_missing += not bool(stage)
            stages[stage] += 1
            day = row["capture_day"]
            day_counts[day] += 1
            day_stages[day][stage] += 1
            split = membership.get(day, "UNMAPPED")
            unmapped += split == "UNMAPPED"
            split_stages[split][stage] += 1
            split_sensors[split].add(row["sensor"])
            signature = row["Signature"].strip() or "EMPTY"
            signature_counts[signature] += 1
            split_signatures[split][signature] += 1
    observed_splits = sorted(split_sensors)
    sensor_overlap = {f"{a}/{b}": len(split_sensors[a] & split_sensors[b])
                      for i, a in enumerate(observed_splits) for b in observed_splits[i + 1:]}
    min_per_stage = {stage: min(values.get(stage, 0) for values in split_stages.values()) for stage in stages}
    return {
        "rows_scanned": count, "metadata_rows": meta["rows"], "metadata_row_count_matches": count == meta["rows"],
        "stage_counts": dict(stages), "metadata_stage_counts_match": dict(stages) == meta["stage_counts"],
        "labelled_rows": count - label_missing, "label_coverage_fraction": (count - label_missing) / count if count else None,
        "cached_sampling": {k: meta["settings"].get(k) for k in ("benign_keep_rate", "min_benign_per_file", "include_cover_up", "split_mode")},
        "cached_data_is_raw_population": False,
        "cached_columns": columns, "capture_day_bins": len(day_counts),
        "legacy_split_row_stage_counts": dict(split_stages), "minimum_legacy_rows_per_stage_across_splits": min_per_stage,
        "legacy_split_sensor_overlap_counts": sensor_overlap, "legacy_split_signature_counts": dict(split_signatures),
        "signature_counts": dict(signature_counts), "unmapped_legacy_split_rows": unmapped,
        "capture_day_stage_counts": dict(day_stages), "independent_campaign_counts": None,
        "qualified_hypothesis_stages": [],
        "interpretation": "Legacy stage-balanced capture-day partitions have many rows, but are not evidence of campaign independence or chronological prospective evaluation. Signature denotes attacker group, not campaign. All stages remain unqualified for new hypotheses.",
    }, receipts


def run(workspace: Path, output: Path, sample_per_file: int = 128, max_bytes_per_file: int = 2097152) -> dict:
    if sample_per_file <= 0 or max_bytes_per_file < 4096:
        raise ValueError("Positive sample count and at least 4096 byte prefix required")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use an empty output directory; audit results are immutable")
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    root = workspace / "imports/unraveled/data"
    receipts, summaries, flows, events = raw_samples(root, sample_per_file, max_bytes_per_file)
    print(f"Sampled {len(receipts)} source files; recounting cached rows", flush=True)
    counts, full_receipts = cache_counts(workspace)
    for relative in ("imports/unraveled/README.md", "imports/unraveled/data/README.md"):
        path = workspace / relative
        full_receipts.append({"relative_path": relative, "source_bytes": path.stat().st_size,
                              "sha256": sha256(path), "hash_scope": "full_file"})
    candidates = interval_candidates(flows, events)
    reasons = hold_reasons(join_verified=False, clock_verified=False, campaign_verified=False,
                           independent_stage_counts_verified=False)
    result = {
        "audit_version": VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HOLD_DATA_CONTRACT", "modelling_authorized_by_e0": False,
        "audit_execution": "COMPLETED", "hold_reasons": reasons,
        "raw_source_file_counts": dict(Counter(item["family"] for item in receipts)),
        "sampling": {"strategy": "nonrepresentative prefix", "records_per_file_limit": sample_per_file,
                     "bytes_per_file_limit": max_bytes_per_file, "total_bytes_read": sum(r["prefix_bytes_read"] for r in receipts)},
        "candidate_linkage": candidates, "cached_rows_recounted": counts["rows_scanned"],
        "validated_join_rate": None, "validated_timestamp_skew_seconds": None,
        "label_coverage_scope": "complete legacy sampled cache only, not all raw flow or host logs",
        "independent_campaigns_per_split": None, "minimum_independent_positive_units_per_stage_per_split": None,
        "included_labels": [], "confirmation_ready": False, "raw_telemetry_published": False,
        "implementation_sha256": sha256(Path(__file__)), "elapsed_seconds": round(time.perf_counter() - start, 3),
    }
    write_json(output / "RAW_SAMPLE_SCHEMAS.json", summaries)
    write_json(output / "CACHE_COUNTS.json", counts)
    write_json(output / "SOURCE_MANIFEST.json", {"raw_prefix_receipts": receipts, "full_file_receipts": full_receipts,
                                               "scope": "Full hashes only for files fully read; prefix hashes do not authenticate unsampled raw bytes."})
    result["artifact_sha256"] = {p.name: sha256(p) for p in sorted(output.glob("*.json"))}
    write_json(output / "E0_RESULT.json", result)
    stages = "\n".join(f"| {stage} | {n:,} |" for stage, n in sorted(counts["stage_counts"].items()))
    report = f"""# E0: Unraveled data verification

**Result: HOLD_DATA_CONTRACT.** The audit completed; E1–E4 cannot claim validated real-data results yet.

## What was actually examined

- {result['raw_source_file_counts'].get('network-flows', 0)} network-flow files and {result['raw_source_file_counts'].get('host-logs', 0)} host-log files, each using at most {sample_per_file} records from a {max_bytes_per_file:,}-byte prefix.
- All {counts['rows_scanned']:,} rows in the existing processed cache were recounted; metadata totals and stages agree: {counts['metadata_row_count_matches'] and counts['metadata_stage_counts_match']}.
- Samples are the beginning of files, not probability samples. Raw row totals and population join rates cannot be inferred from them.
- No raw events, event text, credentials, downloaded datasets, or model outputs were copied into this result folder.

## Required three numbers

1. **Validated join rate: unavailable.** The deterministic interval search found {candidates['candidate_pairs']:,} candidate pairs among {candidates['eligible_sampled_flows']:,} timestamp-valid sampled flows and {candidates['eligible_sampled_host_events']:,} sampled host events. Host/time coincidence is not proof that the records describe the same action. Zero candidates would not demonstrate an unjoinable dataset.
2. **Lifecycle label coverage:** all cached rows have StageClean labels; the full-cache counts are below. This cache retained about 5% of benign traffic (with a per-file minimum) and omitted cover-up; it is not the raw population or evidence of host-label completeness.
3. **Minimum positive test support per independent stage/campaign: unavailable.** Old split row counts exist, but no evidence-backed independent campaign mapping exists. No stage is yet included in a new hypothesis test.

| Cached stage | Rows |
|---|---:|
{stages}

## Why the hold is necessary

Flow timestamps have explicit millisecond units. Audit records use epoch seconds; some syslog records contain timezone-qualified timestamps. Other host records lack a timezone or year, or have mismatched CSV field counts. Those records were not silently assigned a timezone or extra labels. Clock skew needs manually or programmatically verified same-event pairs; a nearest timestamp distribution is not clock skew.

The source README describes one APT group operating across multiple weeks, plus amateur and skilled attacker groups. Signature identifies an attacker group, not independently repeated campaigns. Capture-day and file boundaries do not create new campaigns. All old train/validation/test partitions share six sensors; the old days are interleaved rather than a clean prospective timeline. Shared sensors alone do not invalidate campaign evaluation, but they do not demonstrate cross-environment generalization either.

The source data README also documents duplicate observations at subnet and gateway sensors, missing intra-subnet flow visibility, partial host logging, and host labeling described as unfinished in that README. These need explicit handling; the current on-disk files, not an old README claim, determine actual availability.

## Concrete next work

Use [DATA_CONTRACT.md](../../data/DATA_CONTRACT.md) and the [human handoff](../../data/HUMAN_HANDOFF.md). Establish event matching and clock provenance, independently review a stratified set of candidate/noncandidate pairs, resolve raw host schemas and labels, and supply evidence-backed campaign/group assignments. Deduplicate cross-sensor observations before splitting. If the dataset supplies only one complete APT realization, retain it for development and obtain separately documented DARPA TC/OpTC engagements for confirmation; changing a file name cannot fix independence.

The proposed 30 positive test rows per stage is only a minimum support screen. Repeated flows from one attack are not 30 independent attacks; report row counts and independent groups separately and plan uncertainty at the campaign level.

## Reproduce

`python experiments/apt_final/data_audit.py --workspace PATH_TO_EXISTING_WORKSPACE --output NEW_EMPTY_OUTPUT_FOLDER`

This is a local CPU audit and uses no network, AWS, API, or model. Full file and sampled-prefix hashes are in SOURCE_MANIFEST.json. The command returns success when the audit completes, including a scientific HOLD; downstream code must inspect E0_RESULT.json.status.
"""
    (output / "E0_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "rows": counts["rows_scanned"], "candidate_pairs": candidates["candidate_pairs"]}), flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-per-file", type=int, default=128)
    parser.add_argument("--max-bytes-per-file", type=int, default=2097152)
    args = parser.parse_args()
    run(args.workspace.resolve(), args.output.resolve(), args.sample_per_file, args.max_bytes_per_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
