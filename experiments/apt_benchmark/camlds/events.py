"""Prepare CAM-LDS audit events with author manifestation-window supervision.

The prediction roster is the first source event per host in each fixed ten-second
UTC bin, selected before label lookup. Only roster events inside known author
manifestation windows are supervised. Windows include source padding and manual
adjustments; they are not literal attack activity times or malicious-event gold.
Unannotated events remain unknown context. Attacker logs never become features.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

from .acquire import COMMIT, digest
from ..robustness.casino_events import AUDIT, fragment as audit_fragment

SEED = "camlds-robustness-v2:"
BIN_SECONDS = 10
TARGETS = ("T1068", "T1548", "T1105")
ROLES = ("fit", "development", "calibration", "test")
FIXED_HOST_NAMES = ("videoserver", "inetfw", "lanfw", "wazuh", "attacker", "repositoryserver",
                    "fileserver", "workstation", "linuxshare", "corpdns", "reposerver")
FIXED_HOST_PATTERN = re.compile(r"\b(?:" + "|".join(FIXED_HOST_NAMES) + r")\b", re.I)


def mask_fixed_hostnames(text):
    """Fixed testbed names only; generic CLIENT variables/package terms remain."""
    return FIXED_HOST_PATTERN.sub("HOST", text)


def family_splits():
    ordered = sorted(("1", "2", "3", "4", "6"), key=lambda family:
                     hashlib.sha256((SEED + family).encode()).hexdigest())
    return {family: "fit" if i < 2 else ROLES[i - 1] for i, family in enumerate(ordered)}


def load_intervals(root):
    labels = json.loads((root / "labels.json").read_text(encoding="utf-8"))
    intervals = defaultdict(list)
    seen = set()
    occurrences = Counter()
    seen_intervals = set()
    with (root / "attack_times.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            key = row["scenario"] + "-" + row["event_id"]
            if key not in labels:
                raise ValueError("Unjoined source step")
            seen.add(key)
            source = labels[key]
            techniques = sorted(row["techniques"].split("_"))
            if techniques != sorted(source["metadata"]):
                raise ValueError("Source interval and author technique labels disagree")
            start, end = float(row["start"]), float(row["end"])
            if not all(math.isfinite(value) for value in (start, end)) or start >= end:
                raise ValueError("Invalid author interval")
            signature = (key, start, end)
            if signature in seen_intervals:
                raise ValueError("Duplicate source interval")
            seen_intervals.add(signature)
            occurrences[key] += 1
            # Authors reuse step identifiers for repeated executions. Preserve
            # every distinct interval instead of silently overwriting repeats.
            occurrence_id = key + ":occurrence" + str(occurrences[key])
            intervals[row["scenario"]].append({"step_id": occurrence_id, "source_step_id": key, "start": start, "end": end,
                                                "labels": techniques})
    if set(labels) != seen:
        raise ValueError("Unmatched source label steps")
    for values in intervals.values():
        values.sort(key=lambda item: (item["start"], item["end"], item["step_id"]))
    return dict(intervals)


def interval_labels(timestamp, intervals):
    """Author half-open endpoints; local overlap union avoids duplicate rows."""
    active = [item for item in intervals if item["start"] <= timestamp < item["end"]]
    return sorted({label for item in active for label in item["labels"]}), [item["step_id"] for item in active]


def fragment(raw, run, host, timestamp):
    # Uses the identical causal lexical representation as Casino, then masks
    # fixed public testbed identifiers. No corpus-derived identity dictionary.
    value = audit_fragment(raw, run, host, timestamp)
    for field in ("text", "baseline_text"):
        value[field] = re.sub(r"\b[\w.-]*attackbed\.[a-z]+\b", "HOST", value[field], flags=re.I)
        value[field] = mask_fixed_hostnames(value[field])
        value[field] = re.sub(r"\b" + re.escape(host) + r"\b", "HOST", value[field], flags=re.I)
        value[field] = re.sub(r"\bT\d{4}(?:\.\d{3})?\b", "TECHNIQUE_MARKER", value[field], flags=re.I)
        value[field] = re.sub(r"\bscenario_\w+\b", "SCENARIO_MARKER", value[field], flags=re.I)
    value["channel"] = value["channel"].upper()
    return value


def verify_source_anchors(root, run, members, labels):
    """Check published label anchors against raw attacker chronology, never features."""
    candidates = [member for member in members if member["name"].endswith("/attacker/logs/attackmate.json")]
    if len(candidates) != 1:
        raise ValueError("Exactly one source chronology is required")
    member = candidates[0]
    path = root / "raw" / member["name"]
    if digest(path) != member["sha256"]:
        raise ValueError("Source chronology changed after acquisition")
    with path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    def anchor(value):
        return value.get("start-datetime"), value.get("type"), value.get("cmd")
    anchors = {anchor(value) for value in records}
    selected = [value for value in labels.values() if value["scenario_variant"] == run]
    if any(anchor(value["attackmate"]) not in anchors for value in selected):
        raise ValueError("Published label anchor absent from pinned raw source")
    return {"chronology_records": len(records), "verified_label_anchors": len(selected),
            "chronology_sha256": member["sha256"]}


def build_host(root, run, host, members, intervals, role):
    events = {}
    line_count = malformed = outside = duplicate = 0
    channels = Counter()
    low = min(item["start"] for item in intervals) - 120.0
    high = max(item["end"] for item in intervals)
    for member in sorted(members, key=lambda item: item["name"]):
        path = root / "raw" / member["name"]
        if digest(path) != member["sha256"]:
            raise ValueError("Raw source member changed after acquisition")
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="strict") as handle:
            for number, raw in enumerate(handle, 1):
                line_count += 1
                match = AUDIT.search(raw)
                if not match:
                    malformed += 1
                    continue
                timestamp, serial = float(match[1]), match[2]
                if not math.isfinite(timestamp):
                    raise ValueError("Nonfinite audit timestamp")
                # Old machine-image log history cannot be within the 120-second
                # history of any target. Drop only outside the complete envelope.
                if timestamp < low or timestamp >= high:
                    outside += 1
                    continue
                key = (timestamp, serial)
                event = events.setdefault(key, {"event_id": f"camlds:{run}:{host}:{serial}:{match[1]}",
                    "run_id": run, "split": role, "timestamp": timestamp, "available_at": timestamp,
                    "host": host, "fragments": [], "raw_seen": set()})
                raw = raw.rstrip("\r\n")
                if raw in event["raw_seen"]:
                    duplicate += 1
                    continue
                event["raw_seen"].add(raw)
                part = fragment(raw, run, host, timestamp)
                part["source_member"] = member["name"]
                part["source_line"] = number
                event["fragments"].append(part)
                channels[part["channel"]] += 1
    ordered = sorted(events.values(), key=lambda event: (event["timestamp"], event["event_id"]))
    bins = set()
    query_roster = []
    # This loop must not look at annotations. The bin anchor is absolute UTC,
    # never a step onset, target identity, or simulation-relative offset.
    for event in ordered:
        bucket = math.floor(event["timestamp"] / BIN_SECONDS)
        event["query_roster"] = bucket not in bins
        bins.add(bucket)
        if event["query_roster"]:
            query_roster.append(event["event_id"])
    counts, step_counts = Counter(), Counter()
    for event in ordered:
        del event["raw_seen"]
        event["labels"], event["source_step_ids"] = interval_labels(event["timestamp"], intervals)
        event["target_eligible"] = bool(event["query_roster"] and event["labels"])
        event["label_status"] = "author_step_interval_proxy" if event["labels"] else "unlabeled_unknown"
        event["entity_keys"] = sorted({key for part in event["fragments"] for key in part["entity_keys"]})
        if event["target_eligible"]:
            counts["eligible"] += 1
            counts["overlapping_window_queries"] += len(event["source_step_ids"]) > 1
            step_counts.update(event["source_step_ids"])
            for target in TARGETS:
                if any(label.split(".")[0] == target for label in event["labels"]):
                    counts[target] += 1
    stats = {"host": host, "source_lines": line_count, "malformed_lines": malformed,
             "outside_replay_envelope_lines": outside, "duplicate_fragments": duplicate,
             "events": len(ordered), "fragments": sum(channels.values()), "channels": dict(channels),
             "label_blind_queries": len(query_roster), "eligible_targets": counts["eligible"],
             "overlapping_window_queries": counts["overlapping_window_queries"],
             "positive_targets": {target: counts[target] for target in TARGETS},
             "represented_source_steps": dict(step_counts),
             "query_roster_sha256": hashlib.sha256("\n".join(query_roster).encode()).hexdigest()}
    return ordered, stats


def prepare(root, output):
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError("Refusing to overwrite prepared evidence")
    intervals = load_intervals(root)
    source_labels = json.loads((root / "labels.json").read_text(encoding="utf-8"))
    splits = family_splits()
    runs = sorted(run for run in intervals if run.split("_")[0] in splits)
    source_receipts = {}
    for run in runs:
        path = root / f"scenario_{run}.acquisition.json"
        if not path.exists():
            raise ValueError("Complete defender audit acquisition is required for every eligible run")
        source_receipts[run] = {"path": path, "value": json.loads(path.read_text(encoding="utf-8")),
                                "sha256": digest(path)}
    output.mkdir(parents=True)
    selection = {"frozen_before_label_join_counts": True, "family_splits": splits,
                 "reserved_zero_T1105_families": ["5", "7"], "runs": runs,
                 "split_rule": "SHA256(camlds-robustness-v2:family), first2 fit, next development/calibration/test",
                 "query_rule": "First event by (timestamp,event_id) per host per fixed10-second UTC bin; choose before annotation lookup",
                 "target_semantics": "Author-designated technique manifestation-window membership at query timestamp; not literal active-step time or individual-event maliciousness",
                 "annotated_interval_join": "Author start <= source timestamp < end endpoints; union overlaps is a local convention, not author-extractor equivalence",
                 "source_window_construction": "Command timestamp minus2 seconds to output completion plus4 seconds, with manual start/end shifts and sleep-based end extensions in pinned author extraction script",
                 "author_source_commit": COMMIT, "labels_sha256": digest(root / "labels.json"),
                 "attack_times_sha256": digest(root / "attack_times.csv"),
                 "adapter_sha256": digest(Path(__file__)),
                 "shared_fragment_adapter_sha256": digest(Path(__file__).parents[1] / "robustness" / "casino_events.py")}
    (output / "SELECTION.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    summaries = []
    events_path = output / "EVENTS.jsonl"
    with events_path.with_suffix(".part").open("w", encoding="utf-8", newline="\n") as handle:
        for run in runs:
            family = run.split("_")[0]
            role = splits[family]
            anchor_stats = verify_source_anchors(root, run, source_receipts[run]["value"]["members"], source_labels)
            hosts = defaultdict(list)
            for member in source_receipts[run]["value"]["members"]:
                parts = member["name"].split("/")
                if parts[1] != "attacker" and "/logs/" in member["name"] and "/audit/audit.log" in member["name"]:
                    hosts[parts[1]].append(member)
            if not hosts:
                raise ValueError("No defender audit sources")
            run_events, host_stats = [], []
            for host, members in sorted(hosts.items()):
                events, stats = build_host(root, run, host, members, intervals[run], role)
                run_events.extend(events)
                host_stats.append(stats)
            run_events.sort(key=lambda event: (event["timestamp"], event["event_id"]))
            for event in run_events:
                handle.write(json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            summary = {"run_id": run, "family": family, "split": role, "hosts": host_stats,
                       "events": len(run_events), "eligible_targets": sum(s["eligible_targets"] for s in host_stats),
                       "positive_targets": {target: sum(s["positive_targets"][target] for s in host_stats) for target in TARGETS},
                       "source_acquisition_sha256": source_receipts[run]["sha256"]}
            summary["source_anchor_validation"] = anchor_stats
            positive_intervals = {item["step_id"] for item in intervals[run]
                                  if any(label.split(".")[0] == "T1105" for label in item["labels"])}
            represented = {step for stats in host_stats for step in stats["represented_source_steps"]}
            summary["T1105_source_intervals"] = len(positive_intervals)
            summary["T1105_intervals_represented"] = sorted(positive_intervals.intersection(represented))
            summaries.append(summary)
            print(json.dumps({key: summary[key] for key in ("run_id", "events", "eligible_targets", "positive_targets")}), flush=True)
    events_path.with_suffix(".part").replace(events_path)
    support = {}
    for target in TARGETS:
        support[target] = {}
        for role in ROLES:
            cohort = [s for s in summaries if s["split"] == role]
            total = sum(s["eligible_targets"] for s in cohort)
            positive = sum(s["positive_targets"][target] for s in cohort)
            support[target][role] = {"n": total, "positive": positive, "negative": total - positive,
                                    "runs": len(cohort), "families": sorted({s["family"] for s in cohort}),
                                    "positive_bearing_runs": sum(s["positive_targets"][target] > 0 for s in cohort)}
    manifest = {"status": "QUALIFIED_MANIFESTATION_WINDOW_PROXY_NOT_MALICIOUS_EVENT_GOLD", "dataset": "camlds",
                "events_sha256": digest(events_path), "events": sum(s["events"] for s in summaries),
                "eligible_targets": sum(s["eligible_targets"] for s in summaries),
                "selection": selection, "selection_sha256": digest(output / "SELECTION.json"),
                "source_record": "https://zenodo.org/records/18861762", "license": "CC-BY-4.0",
                "paper": "https://doi.org/10.1007/s10207-026-01318-x", "support": support, "runs": summaries,
                "family_qualified_target": "T1105", "unqualified_targets": ["T1068", "T1548"],
                "limits": ["Only one calibration and one test scenario family; variants are correlated repetitions",
                           "Scenario manifestation windows apply across all defender hosts; unrelated or idle host activity can inherit window membership",
                           "Author windows are padded and manually shifted, with sleep extensions; window membership is not a literal active-step or early-warning label",
                           "No ordinary benign-user workload; other technique intervals are not benign ground truth",
                           "Interval labels can include idle activity and delayed manifestations across boundaries",
                           "Event time substitutes for native record availability; injected delays are synthetic",
                           "Fixed-bin source-event roster is retained under missingness; hidden targets remain misses",
                           "Only audit records are used; this is not whole18-source sensor evaluation",
                           "No attacker execution logs, interval boundaries, scenario names, labels or step IDs enter feature text"]}
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"complete": True, "events": manifest["events"], "eligible_targets": manifest["eligible_targets"],
                      "support": support}), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.output)


if __name__ == "__main__":
    main()
