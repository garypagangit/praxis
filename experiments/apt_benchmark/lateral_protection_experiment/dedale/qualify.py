"""Read author-labeled flow tables and report counts/compatibility; no models.

All outputs are aggregate. IDs/addresses/times and author label fields are not
predictors. Feature fingerprints use the existing SCVIC byte convention.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads((args.root / "ACQUISITION_PLAN.json").read_text())
    with np.load(args.source_data, allow_pickle=False) as z:
        names = z["feature_names"].tolist()
        source_fingerprints = set(z["group_sha256"].tolist())
    mapping = {n: {"Protocol": "proto", "Flow Duration": "duration"}.get(n, n) for n in names}
    if len(names) != 73 or len(set(mapping.values())) != 73:
        raise ValueError("Unexpected source feature contract")
    total_label, total_tactic, total_step = Counter(), Counter(), Counter()
    attack_fingerprints = Counter()
    lateral_fingerprints = Counter()
    day_results, all_nonfinite, all_overlap = [], np.zeros(73, dtype=np.int64), 0
    canonical_columns = None
    for member in plan["members"]:
        filename = "717871_" + re.sub(r"[^A-Za-z0-9_.-]", "_", member)
        path = args.root / "members" / filename
        receipt = json.loads(path.with_suffix(path.suffix + ".receipt.json").read_text())
        if sha(path) != receipt["sha256"]:
            raise ValueError("Acquired table failed its checksum")
        with path.open(newline="", encoding="utf-8") as stream:
            columns = next(csv.reader(stream))
        if canonical_columns is None:
            canonical_columns = columns
        if columns != canonical_columns or not set(mapping.values()).issubset(columns):
            raise ValueError("Inconsistent/unmapped feature schema")
        extra = ["label", "step", "attack_step", "tactic", "technique", "ts"]
        usecols = list(mapping.values()) + extra
        counts, tactics, steps, descriptions = Counter(), Counter(), Counter(), Counter()
        protocols = Counter()
        n, missing, overlap, bad_lateral_labels = 0, 0, 0, 0
        label_time_ranges = {}
        for frame in pd.read_csv(path, usecols=usecols, chunksize=100_000, low_memory=False):
            labels = pd.to_numeric(frame["label"], errors="raise").to_numpy(dtype=np.int64)
            if not set(np.unique(labels)).issubset({0, 1, 2}):
                raise ValueError("Unknown author label; refuse invented mapping")
            x = frame[list(mapping.values())].apply(pd.to_numeric, errors="raise").to_numpy(dtype="<f8", copy=True)
            nonfinite = ~np.isfinite(x)
            all_nonfinite += nonfinite.sum(axis=0)
            missing += int(nonfinite.any(axis=1).sum())
            x[nonfinite] = np.nan
            x[x == 0] = 0.0
            tactic = frame["tactic"].fillna("").astype(str).to_numpy()
            fingerprints = [hashlib.sha256(row.tobytes()).hexdigest() for row in x]
            overlap += sum(f in source_fingerprints for f in fingerprints)
            n += len(frame)
            counts.update(str(int(label)) for label in labels)
            protocols.update(str(int(v)) for v in frame["proto"].unique())
            bad_lateral_labels += int(((tactic == "TA0008") & (labels != 1)).sum())
            for i in np.flatnonzero(labels != 0):
                attack_fingerprints[fingerprints[i]] += 1
                key = f"{labels[i]}|{tactic[i]}"
                tactics[key] += 1
                step = f"{labels[i]}|{int(frame['step'].iloc[i])}|{frame['attack_step'].iloc[i]}|{frame['technique'].iloc[i]}"
                steps[step] += 1
                if tactic[i] == "TA0008":
                    lateral_fingerprints[fingerprints[i]] += 1
            for label in np.unique(labels):
                times = pd.to_numeric(frame.loc[labels == label, "ts"], errors="raise")
                old = label_time_ranges.setdefault(str(int(label)), [float("inf"), float("-inf")])
                old[0], old[1] = min(old[0], float(times.min())), max(old[1], float(times.max()))
        total_label.update(counts)
        total_tactic.update(tactics)
        total_step.update(steps)
        all_overlap += overlap
        result = {"member": member, "sha256": receipt["sha256"], "day": int(re.search(r"/D(\d+)_", member)[1]),
                  "rows": n, "author_label_counts": dict(counts), "nonbenign_label_tactic_counts": dict(tactics),
                  "nonbenign_execution_step_counts": dict(steps), "rows_with_nonfinite_predictors": missing,
                  "exact_scvic_feature_overlap_rows": overlap, "lateral_rows_not_label1": bad_lateral_labels,
                  "label_time_ranges_utc": {k: [datetime.fromtimestamp(v, timezone.utc).isoformat() for v in pair]
                                            for k, pair in label_time_ranges.items()},
                  "protocol_codes_present": sorted(protocols)}
        day_results.append(result)
        print(json.dumps({"day": result["day"], "rows": n, "labels": dict(counts),
                          "tactics": dict(tactics), "scvic_overlap_rows": overlap}), flush=True)
    summary = {
        "schema_version": 1, "dataset": "DEDALE2.0 internal-network precomputed labeled CICFlowMeter subset",
        "qualified_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_fits": 0, "model_outcomes_inspected": False,
        "dataset_doi": "10.57745/Y5JLDG", "license": "CC-BY-4.0 per released dataset metadata",
        "source_metadata_sha256": plan["source_metadata_sha256"],
        "acquisition_plan_sha256": sha(args.root / "ACQUISITION_PLAN.json"),
        "qualifier_sha256": sha(Path(__file__)), "source_scvic_npz_sha256": sha(args.source_data),
        "days": day_results, "rows": sum(d["rows"] for d in day_results),
        "author_label_counts": dict(total_label), "nonbenign_label_tactic_counts": dict(total_tactic),
        "nonbenign_execution_step_counts": dict(total_step),
        "nonbenign_unique_feature_groups": len(attack_fingerprints),
        "lateral_unique_feature_groups": len(lateral_fingerprints),
        "lateral_raw_rows": sum(lateral_fingerprints.values()),
        "exact_scvic_feature_overlap_rows": all_overlap,
        "feature_mapping_scvic_to_dedale": mapping,
        "feature_nonfinite_cell_counts": dict(zip(names, map(int, all_nonfinite))),
        "feature_count": len(names), "all_author_columns": canonical_columns,
        "feature_schema_status": "ALL73_MAPPED_TWO_AUTHOR_DOCUMENTED_RENAMES",
        "feature_semantics_limit": "DEDALE extractor revision pinned; SCVIC exact extractor revision/settings not verified. Common names and numeric layout do not establish bitwise extractor equivalence.",
        "grouping_limit": "One campaign and one documented PrintNightmare lateral execution, two labeled substeps. Flows and fitting seeds are not independent executions.",
        "deduplication_limit": "Counts are raw except explicitly unique nonbenign/lateral feature counts. Full target deduplication and cross-label conflicts, including normal versus attack, require preparation before model evaluation.",
        "label_semantics": {"0": "author benign", "1": "author attack", "2": "author attack-related, not inherently malicious; separate evaluation stratum"},
        "calibration_days": [1, 8], "external_evaluation_days": list(range(15, 29)),
        "supervised_target_training_limit": "Acquired pre-attack days contain no attack supervision; independent within-target lateral training and evaluation are unsupported by one execution.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError("Refusing to overwrite an existing qualification")
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
