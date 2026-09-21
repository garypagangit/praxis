"""Aggregate-only qualification of fixed CAM-LDS retrospective windows.

No feature matrix or model is built. Raw text is never written or printed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

from ..camlds.events import load_intervals


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def is_target(item):
    return any(label.split(".")[0] == "T1105" for label in item["labels"])


def union_seconds(intervals, low, high):
    total = 0.0
    end = low
    for item in sorted(intervals, key=lambda x: x["start"]):
        left, right = max(low, item["start"]), min(high, item["end"])
        if left < right:
            total += max(0.0, right - max(end, left))
            end = max(end, right)
    return total


def qualify(source, prepared):
    source, prepared = Path(source), Path(prepared)
    manifest = json.loads((prepared / "MANIFEST.json").read_text(encoding="utf-8"))
    intervals = load_intervals(source)
    roles = manifest["selection"]["family_splits"]
    bins = {}
    run_meta = {}
    roster = hashlib.sha256()
    for run in manifest["selection"]["runs"]:
        items = intervals[run]
        low, high = min(i["start"] for i in items) - 120.0, max(i["end"] for i in items)
        first, stop = math.ceil(low / 10), math.floor(high / 10)
        known_coverage, target_coverage = set(), set()
        for bucket in range(first, stop):
            # The available replay envelope uses author annotations. Inside it,
            # fixed absolute UTC bins are constructed independently of labels.
            start, end = bucket * 10, (bucket + 1) * 10
            hits = [i for i in items if i["start"] < end and i["end"] > start]
            positive = [i for i in hits if is_target(i)]
            other = [i for i in hits if not is_target(i)]
            y = 1 if positive else 0 if hits else -1
            known_coverage.update(i["step_id"] for i in hits)
            target_coverage.update(i["step_id"] for i in positive)
            bins[run, bucket] = {
                "y": y, "events": 0, "fragments": 0,
                "retained_events": 0, "retained_fragments": 0,
                "hosts": set(), "retained_hosts": set(),
                "positive_and_other": bool(positive and other),
                "multiple_source_intervals": len(hits) > 1,
                "positive_overlap_seconds": union_seconds(positive, start, end),
                "known_overlap_seconds": union_seconds(hits, start, end),
                "positive_source_steps": {i["step_id"] for i in positive},
            }
            roster.update((run + ":" + str(bucket) + "\n").encode())
        raw_overlaps = []
        for index, item in enumerate(items):
            for later in items[index + 1:]:
                overlap = min(item["end"], later["end"]) - max(item["start"], later["start"])
                if overlap > 0:
                    raw_overlaps.append({"seconds": overlap,
                                         "target_vs_other": is_target(item) != is_target(later)})
        positive_steps = {i["step_id"] for i in items if is_target(i)}
        run_meta[run] = {
            "run_id": run, "family": run.split("_")[0], "split": roles[run.split("_")[0]],
            "complete_bins": stop - first,
            "excluded_partial_boundary_bins": int(first * 10 > low) + int(stop * 10 < high),
            "excluded_boundary_seconds": first * 10 - low + high - stop * 10,
            "source_intervals": len(items), "source_target_intervals": len(positive_steps),
            "source_intervals_overlapping_complete_bins": len(known_coverage),
            "source_target_intervals_overlapping_complete_bins": len(target_coverage),
            "source_target_intervals_without_complete_bin": len(positive_steps - target_coverage),
            "source_target_intervals_with_additional_techniques": sum(is_target(i) and len(i["labels"]) > 1 for i in items),
            "overlapping_source_interval_pairs": len(raw_overlaps),
            "overlapping_source_interval_seconds": sum(i["seconds"] for i in raw_overlaps),
            "overlapping_source_target_other_pairs": sum(i["target_vs_other"] for i in raw_overlaps),
        }
    source_events = outside_events = attacker_members = timestamp_mismatch = 0
    source_fragments = outside_fragments = 0
    channel_counts, text_markers = Counter(), Counter()
    exact_target_evidence = defaultdict(set)
    exact_target_retained_evidence = defaultdict(set)
    with (prepared / "EVENTS.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            source_events += 1
            source_fragments += len(event["fragments"])
            run, timestamp = event["run_id"], event["timestamp"]
            key = run, math.floor(timestamp / 10)
            retained = [p for p in event["fragments"] if p["channel"] not in {"EXECVE", "PROCTITLE"}]
            attacker_members += sum("/attacker/" in p["source_member"] for p in event["fragments"])
            timestamp_mismatch += int(timestamp != event["available_at"])
            if key not in bins:
                outside_events += 1
                outside_fragments += len(event["fragments"])
                continue
            row = bins[key]
            row["events"] += 1
            row["fragments"] += len(event["fragments"])
            row["retained_events"] += bool(retained)
            row["retained_fragments"] += len(retained)
            row["hosts"].add(event["host"])
            if retained:
                row["retained_hosts"].add(event["host"])
            channel_counts.update(p["channel"] for p in event["fragments"])
            for part in event["fragments"]:
                for marker in ("TECHNIQUE_MARKER", "SCENARIO_MARKER", "CHALLENGE_MARKER"):
                    text_markers[marker] += marker in part["text"]
            for item in intervals[run]:
                if is_target(item) and item["start"] <= timestamp < item["end"]:
                    exact_target_evidence[run].add(item["step_id"])
                    if retained:
                        exact_target_retained_evidence[run].add(item["step_id"])

    def summarize(rows):
        values = list(rows)
        pos = [r for r in values if r["y"] == 1]
        known = [r for r in values if r["y"] >= 0]
        return {
            "windows": len(values), "positive": len(pos),
            "negative_other_annotation": sum(r["y"] == 0 for r in values),
            "unknown_unscored": sum(r["y"] == -1 for r in values),
            "scored": len(known),
            "empty_windows": sum(r["events"] == 0 for r in values),
            "empty_scored_windows": sum(r["events"] == 0 for r in known),
            "empty_positive_windows": sum(r["events"] == 0 for r in pos),
            "command_loss_empty_windows": sum(r["retained_events"] == 0 for r in values),
            "command_loss_empty_positive_windows": sum(r["retained_events"] == 0 for r in pos),
            "positive_with_other_annotation": sum(r["positive_and_other"] for r in pos),
            "multiple_source_interval_windows": sum(r["multiple_source_intervals"] for r in values),
            "positive_bins_less_than_one_second_target_overlap": sum(r["positive_overlap_seconds"] < 1 for r in pos),
            "positive_bins_less_than_half_target_overlap": sum(r["positive_overlap_seconds"] < 5 for r in pos),
            "positive_bins_fully_target_covered": sum(r["positive_overlap_seconds"] >= 10 - 1e-7 for r in pos),
            "positive_total_target_overlap_seconds": sum(r["positive_overlap_seconds"] for r in pos),
            "scored_total_known_overlap_seconds": sum(r["known_overlap_seconds"] for r in known),
            "events": sum(r["events"] for r in values), "fragments": sum(r["fragments"] for r in values),
            "command_loss_retained_events": sum(r["retained_events"] for r in values),
            "command_loss_retained_fragments": sum(r["retained_fragments"] for r in values),
            "positive_windows_with_multiple_observed_hosts": sum(len(r["hosts"]) > 1 for r in pos),
        }
    per_run = []
    for run, meta in run_meta.items():
        rows = [value for (name, _), value in bins.items() if name == run]
        active_steps = {step for row in rows if row["events"] for step in row["positive_source_steps"]}
        retained_steps = {step for row in rows if row["retained_events"] for step in row["positive_source_steps"]}
        per_run.append({**meta, **summarize(rows),
            "target_intervals_with_any_evidence_in_overlapping_bin": len(active_steps),
            "target_intervals_with_retained_evidence_in_overlapping_bin": len(retained_steps),
            "target_intervals_with_evidence_inside_actual_author_interval": len(exact_target_evidence[run]),
            "target_intervals_with_retained_evidence_inside_actual_author_interval": len(exact_target_retained_evidence[run]),
        })
    support = {}
    for role in ("fit", "development", "calibration", "test"):
        runs = [r for r in per_run if r["split"] == role]
        selected = {r["run_id"] for r in runs}
        support[role] = {**summarize(v for (name, _), v in bins.items() if name in selected),
            "runs": len(runs), "families": sorted({r["family"] for r in runs}),
            "positive_bearing_runs": sum(r["positive"] > 0 for r in runs),
            "source_target_intervals": sum(r["source_target_intervals"] for r in runs),
            "source_target_intervals_overlapping_complete_bins": sum(r["source_target_intervals_overlapping_complete_bins"] for r in runs),
        }
    per_family = {}
    for family in sorted(roles):
        per_family[family] = summarize(v for (name, _), v in bins.items() if name.split("_")[0] == family)
    computed_hash = digest(prepared / "EVENTS.jsonl")
    if computed_hash != manifest["events_sha256"]:
        raise ValueError("Prepared source hash differs from pinned manifest")
    return {
        "status": "QUALIFIED_EXPLORATORY_RETROSPECTIVE_WINDOW_DIAGNOSTIC_ONLY",
        "dataset": "CAM-LDS", "target": "T1105", "window_seconds": 10,
        "source_events_sha256": computed_hash,
        "source_manifest_sha256": digest(prepared / "MANIFEST.json"),
        "source_intervals_sha256": digest(source / "attack_times.csv"),
        "qualifier_sha256": digest(Path(__file__)),
        "label_blind_fixed_bin_roster_sha256": roster.hexdigest(),
        "roster_hash_definition": "SHA256 of UTF-8 run_id:floor(UTC_seconds/10) followed by newline, sorted source run order then increasing bins",
        "label_rule": "Half-open fixed window overlaps any T1105 author interval => positive; other author interval only => negative; no annotation => unknown/unscored. Target membership wins mixed bins; report mixed-bin support separately.",
        "roster_rule": "For each already acquired run, create every 10-second absolute-UTC bin entirely inside [min(author_start)-120,max(author_end)); retain empty bins; exclude both partial boundary bins. Do not use annotation boundaries as features.",
        "source_slice_limitation": "Existing prepared replay envelope was selected from author interval extrema. Bin boundaries are label-independent inside this slice; acquisition coverage is not label-blind or a whole-day deployment cohort.",
        "inference_time": "At window close; uses only events inside that window; retrospective window classification, not early warning or individual-event maliciousness.",
        "source_events": source_events, "source_fragments": source_fragments,
        "excluded_partial_boundary_events": outside_events,
        "excluded_partial_boundary_fragments": outside_fragments,
        "attacker_feature_members": attacker_members,
        "event_availability_timestamp_mismatches": timestamp_mismatch,
        "overall": summarize(bins.values()), "support": support,
        "families": per_family, "runs": per_run,
        "source_channels_inside_complete_bins": dict(sorted(channel_counts.items())),
        "generic_source_marker_fragment_counts": dict(text_markers),
        "limits": [
            "Author manifestation windows include padding, manual shifts, and sleep extensions; window membership is still weak supervision, not exact malicious activity.",
            "Negatives are other annotated technique periods, not independently verified benign periods; unknown windows are excluded from scoring.",
            "Any-overlap labeling can mix target and other stages and dilute short target evidence across a whole ten-second bin.",
            "All defender audit hosts are pooled, matching the scope of global source labels but still including unrelated/idle activity; no ground truth of the affected host is inferred.",
            "Only audit records are present; deleting EXECVE and PROCTITLE does not remove all command/program evidence from SYSCALL, PATH, and other surviving fields.",
            "Lexical paths, program names, channel counts, volume, and coarse identity classes may encode simulation-family artifacts despite fixed host/run/technique masking.",
            "Some generic TECHNIQUE_MARKER/SCENARIO_MARKER/CHALLENGE_MARKER tokens may encode testbed artifacts; exclude these literal markers from model text.",
            "One test family and one calibration family with correlated variants cannot establish general APT detection or reliable population uncertainty.",
            "Prior outcomes on this cohort are exposed: every new result is development evidence and needs fresh external confirmation.",
            "No fits, tuning, labels created by a model, or human audit were performed by this qualification.",
        ],
    }


def render(value):
    text = ["# Fixed-window data qualification", "", "Status: exploratory retrospective T1105 manifestation-window diagnostic.", "",
        "Every complete 10-second UTC bin is pooled across all acquired defender audit hosts. Empty bins remain. Positive means any overlap with an author T1105 window; other annotated periods are negatives; unannotated bins are unknown and unscored. Mixed bins remain positive and are counted separately.", "",
        "**The existing replay slice is annotation-derived.** Fixed bin boundaries are label-independent within `[first author start - 120 seconds, last author end)`, but this is not a whole-day or annotation-independent acquisition cohort. Partial boundary bins are excluded. Predictions are made at window close; this is not an early-warning test.", "",
        "| Split | All bins | Positive | Other-label negative | Unknown | Empty positive | Mixed positive | Source target windows covered |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for role, row in value["support"].items():
        text.append(f"| {role} | {row['windows']} | {row['positive']} | {row['negative_other_annotation']} | {row['unknown_unscored']} | {row['empty_positive_windows']} | {row['positive_with_other_annotation']} | {row['source_target_intervals_overlapping_complete_bins']}/{row['source_target_intervals']} |")
    text += ["", "## Interpretation limits", ""]
    text.extend("- " + line for line in value["limits"])
    text += ["", "Detailed aggregate counts by family and run, source hashes, boundary exclusions, source coverage, and command-removal support are recorded in [DATA_QUALIFICATION.json](DATA_QUALIFICATION.json). No raw attacker command logs or event text are included.", ""]
    return "\n".join(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = qualify(args.source, args.prepared)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "DATA_QUALIFICATION.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    (args.output / "DATA_QUALIFICATION.md").write_text(render(value), encoding="utf-8")
    print(json.dumps({"overall": value["overall"], "support": value["support"], "attacker_feature_members": value["attacker_feature_members"], "source_events_sha256": value["source_events_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
