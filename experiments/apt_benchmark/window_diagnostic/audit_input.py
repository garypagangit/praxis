"""Independent aggregate input audit; no model fits or feature mutations.

Reconstructs labels directly from the author CSV and re-counts source events.
Does not call feature construction or its roster/label helper functions.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import sparse


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(source, features, qualification):
    manifest_path = features / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qualified = json.loads(qualification.read_text(encoding="utf-8"))
    prepared = source / "prepared_masked_v2"
    source_manifest = json.loads((prepared / "MANIFEST.json").read_text(encoding="utf-8"))
    checks = []

    def check(name, condition, **detail):
        checks.append({"check": name, "pass": bool(condition), **detail})

    check("pinned_source_manifest_hash", digest(prepared / "MANIFEST.json") == manifest["source_manifest_sha256"] == qualified["source_manifest_sha256"])
    check("source_interval_hash", digest(source / "attack_times.csv") == manifest["attack_times_sha256"] == qualified["source_intervals_sha256"])
    check("source_label_hash", digest(source / "labels.json") == manifest["labels_sha256"])
    check("qualifier_code_hash", digest(qualification.parent / "qualify_data.py") == qualified["qualifier_sha256"])
    for filename, expected in manifest["artifacts"].items():
        path = features / filename
        check("feature_artifact_hash:" + filename, path.stat().st_size == expected["bytes"] and digest(path) == expected["sha256"])
    for filename, expected in manifest["code_sha256"].items():
        path = Path(__file__).parent / filename if "/" not in filename else Path(__file__).parents[1] / filename
        check("feature_source_code_hash:" + filename, digest(path) == expected)

    intervals = defaultdict(list)
    occurrences = Counter()
    with (source / "attack_times.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            source_id = row["scenario"] + "-" + row["event_id"]
            occurrences[source_id] += 1
            intervals[row["scenario"]].append({
                "start": float(row["start"]), "end": float(row["end"]),
                "target": any(t.split(".")[0] == "T1105" for t in row["techniques"].split("_")),
                "step": source_id + ":occurrence" + str(occurrences[source_id]),
            })
    expected = []
    roster_hash = hashlib.sha256()
    for run in sorted(source_manifest["selection"]["runs"]):
        items = intervals[run]
        first = math.ceil((min(item["start"] for item in items) - 120.0) / 10)
        stop = math.floor(max(item["end"] for item in items) / 10)
        for bucket in range(first, stop):
            start, end = bucket * 10, (bucket + 1) * 10
            hits = [item for item in items if max(start, item["start"]) < min(end, item["end"])]
            positive_steps = sorted(item["step"] for item in hits if item["target"])
            expected.append({"run_id": run, "family": run.split("_")[0], "start": start, "end": end,
                "window_id": f"camlds-window:{run}:{bucket}",
                "split": source_manifest["selection"]["family_splits"][run.split("_")[0]],
                "label": 1 if positive_steps else 0 if hits else -1,
                "positive_source_step_ids": positive_steps})
            roster_hash.update((run + ":" + str(bucket) + "\n").encode())
    metadata = json.loads((features / "metadata.json").read_text(encoding="utf-8"))
    check("exact_5480_bin_roster", len(metadata) == len(expected) == manifest["windows"] == 5480)
    check("independent_roster_hash", roster_hash.hexdigest() == qualified["label_blind_fixed_bin_roster_sha256"])
    mismatches = 0
    for actual, intended in zip(metadata, expected):
        mismatches += any(actual.get(key) != value for key, value in intended.items())
    check("every_metadata_label_boundary_role_and_source_step_set", mismatches == 0 and len(metadata) == len(expected), mismatched_rows=mismatches)

    by_key = {(row["run_id"], row["start"] // 10): i for i, row in enumerate(expected)}
    source_counts = np.zeros(len(expected), dtype=np.int64)
    source_digest = hashlib.sha256()
    source_event_total = excluded = 0
    with (prepared / "EVENTS.jsonl").open("rb") as handle:
        for line in handle:
            source_digest.update(line)
            event = json.loads(line)
            source_event_total += 1
            index = by_key.get((event["run_id"], math.floor(event["timestamp"] / 10)))
            if index is None:
                excluded += 1
            else:
                source_counts[index] += 1
    check("pinned_source_event_hash", source_digest.hexdigest() == manifest["source_events_sha256"] == qualified["source_events_sha256"])
    check("source_event_accounting", source_event_total == qualified["source_events"] == 691563 and excluded == qualified["excluded_partial_boundary_events"] == 2724 and int(source_counts.sum()) == qualified["overall"]["events"] == 688839)
    observed_counts = np.asarray([row["clean_event_count"] for row in metadata])
    check("independent_every_bin_event_count", np.array_equal(observed_counts, source_counts))
    labels = np.asarray([row["label"] for row in metadata])
    label_counts = {"positive": int(np.sum(labels == 1)), "negative": int(np.sum(labels == 0)), "unknown": int(np.sum(labels == -1))}
    check("label_counts", label_counts == {"positive": 264, "negative": 4319, "unknown": 897}, **label_counts)
    empty_positive = int(np.sum((source_counts == 0) & (labels == 1)))
    check("empty_positive_bins_kept", empty_positive == 13, empty_positive=empty_positive)
    family_counts = {}
    for family in sorted(qualified["families"]):
        use = np.asarray([row["family"] == family for row in metadata])
        counts = {"windows": int(use.sum()), "positive": int(np.sum(use & (labels == 1))),
                  "negative_other_annotation": int(np.sum(use & (labels == 0))),
                  "unknown_unscored": int(np.sum(use & (labels == -1))),
                  "empty_positive_windows": int(np.sum(use & (labels == 1) & (source_counts == 0))),
                  "events": int(source_counts[use].sum())}
        family_counts[family] = counts
        check("family_counts:" + family, all(qualified["families"][family][key] == value for key, value in counts.items()))
    run_counts_valid = True
    target_steps = set()
    for run_summary in qualified["runs"]:
        run = run_summary["run_id"]
        use = np.asarray([row["run_id"] == run for row in metadata])
        steps = {s for row in metadata if row["run_id"] == run for s in row["positive_source_step_ids"]}
        target_steps.update(steps)
        run_counts_valid &= int(use.sum()) == run_summary["windows"]
        run_counts_valid &= int(source_counts[use].sum()) == run_summary["events"]
        run_counts_valid &= int(np.sum(use & (labels == 1))) == run_summary["positive"]
        run_counts_valid &= len(steps) == run_summary["source_target_intervals_overlapping_complete_bins"]
    check("run_counts_and_source_window_coverage", run_counts_valid and len(target_steps) == 83, target_source_intervals=len(target_steps))

    matrices = {name: sparse.load_npz(features / (name + ".npz")).tocsr() for name in manifest["matrices"]}
    matrix_summary = {}
    for name, matrix in matrices.items():
        check("matrix_shape_and_nonzero_count:" + name, list(matrix.shape) == manifest["matrices"][name]["shape"] == [5480, 8200] and matrix.nnz == manifest["matrices"][name]["nnz"])
        check("finite_nonnegative_values:" + name, np.isfinite(matrix.data).all() and (matrix.data >= 0).all())
        text = matrix[:, :8192].tocsr()
        row_nnz = np.diff(text.indptr)
        expected_text = np.repeat(np.divide(1.0, np.sqrt(row_nnz), out=np.zeros(len(row_nnz), dtype=np.float64), where=row_nnz != 0), row_nnz)
        check("binary_presence_l2_scaling_only:" + name, np.allclose(text.data, expected_text, rtol=2e-6, atol=1e-7))
        empty = source_counts == 0
        check("empty_bin_zero_features:" + name, matrix[empty].nnz == 0)
        count_columns = np.expm1(matrix[:, 8192:].toarray().astype(np.float64))
        check("observed_counts_near_integers:" + name, np.allclose(count_columns, np.round(count_columns), rtol=0, atol=0.1))
        matrix_summary[name] = {"shape": list(matrix.shape), "nnz": matrix.nnz, "empty_rows": int(np.sum(np.diff(matrix.indptr) == 0)), "max_observed_events": int(np.round(count_columns[:, 0].max()))}
        if name.endswith("command_absent"):
            check("removed_channel_columns_zero:" + name, matrix[:, [8196, 8197]].nnz == 0)
    for condition in ("clean", "command_absent"):
        first = matrices["first_" + condition]
        pooled = matrices["pooled_" + condition]
        first_presence = first[:, :8192].copy()
        first_presence.data[:] = 1
        pooled_presence = pooled[:, :8192].copy()
        pooled_presence.data[:] = 1
        outside = first_presence - first_presence.multiply(pooled_presence)
        outside.eliminate_zeros()
        check("first_text_presence_subset_of_pool:" + condition, outside.nnz == 0)
        check("first_observed_counts_no_greater_than_pool:" + condition, np.all(first[:, 8192:].toarray() <= pooled[:, 8192:].toarray() + 1e-7))
        first_events = first[:, 8192].toarray().ravel()
        check("first_event_count_at_most_one:" + condition, np.all(first_events <= np.log(2) + 1e-7))
    for pooling in ("first", "pooled"):
        clean = matrices[pooling + "_clean"][:, 8192:].toarray()
        absent = matrices[pooling + "_command_absent"][:, 8192:].toarray()
        check("ablation_observed_counts_never_increase:" + pooling, np.all(absent <= clean + 1e-7))
        check("ablation_surviving_channels_unchanged:" + pooling, np.array_equal(absent[:, [3, 6, 7]], clean[:, [3, 6, 7]]))
    clean_event_feature = matrices["pooled_clean"][:, 8192].toarray().ravel()
    check("clean_event_count_column_8192", np.array_equal(clean_event_feature, np.log1p(observed_counts.astype(np.float32))))
    clean_rule = np.load(features / "rules_clean.npy", allow_pickle=False)
    absent_rule = np.load(features / "rules_command_absent.npy", allow_pickle=False)
    check("rule_scores_finite_bounded_integers", all(v.shape == (5480,) and np.isfinite(v).all() and (v >= 0).all() and (v <= 6).all() and np.equal(v, np.floor(v)).all() for v in (clean_rule, absent_rule)))
    check("rule_score_cannot_increase_after_removal", np.all(absent_rule <= clean_rule))
    failures = [item["check"] for item in checks if not item["pass"]]
    return {"status": "PASS" if not failures else "FAIL", "audit_type": "Independent software/input audit; not a human label audit",
        "features_manifest_sha256": digest(manifest_path), "qualification_sha256": digest(qualification),
        "auditor_sha256": digest(Path(__file__)), "checks": checks, "failed_checks": failures,
        "check_count": len(checks), "windows": len(metadata), "label_counts": label_counts,
        "empty_positive_bins": empty_positive, "target_source_intervals": len(target_steps),
        "family_counts": family_counts, "matrices": matrix_summary,
        "scope": "Direct CSV overlap and roster reconstruction; fresh complete source pass for per-bin event counts and hash; source coverage, aggregate support, all saved artifact hashes, and sparse-matrix invariants. Does not refit, score, mutate features, or certify semantic label correctness.",
        "limits": ["Does not independently reconstruct every lexical hash from raw fragments; tests invariant relations and provenance/code hashes.",
            "Ablation may create new cross-fragment bigrams, so text-column subset of clean is not asserted. First-event text must be a subset of pooled text within the same condition.",
            "The author-derived slice, padded window labels, unknown-period handling, and exposed development-family limitations remain."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source, args.features, args.output / "DATA_QUALIFICATION.json")
    (args.output / "INPUT_AUDIT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Independent input audit", "", f"Status: **{result['status']}**; {result['check_count']} checks.", "", result["audit_type"] + ".", "", result["scope"], "",
        f"Confirmed {result['windows']:,} bins: {result['label_counts']['positive']} positive, {result['label_counts']['negative']:,} other-annotation negative, {result['label_counts']['unknown']} unknown. Retained {result['empty_positive_bins']} empty positive bins and all {result['target_source_intervals']} target source intervals.", "", "## Limits", ""]
    lines.extend("- " + item for item in result["limits"])
    if result["failed_checks"]:
        lines += ["", "## Failed checks", ""] + ["- " + item for item in result["failed_checks"]]
    lines += ["", "Detailed aggregate checks: [INPUT_AUDIT.json](INPUT_AUDIT.json).", ""]
    (args.output / "INPUT_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "check_count", "failed_checks", "windows", "label_counts", "empty_positive_bins", "target_source_intervals")}, indent=2))
    if result["failed_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
