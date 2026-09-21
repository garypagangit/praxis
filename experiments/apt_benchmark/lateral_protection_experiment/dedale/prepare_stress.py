"""Prepare the frozen day17 external stress sample; never fit or score a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(values):
    values = np.array(values, dtype="<f8", order="C", copy=True)
    values[~np.isfinite(values)] = np.nan
    values[values == 0] = 0.0
    return values


def fingerprints(values):
    return [hashlib.sha256(row.tobytes(order="C")).hexdigest() for row in values]


def prepare(protocol_path, source_data, source_csv, output):
    protocol = json.loads(protocol_path.read_text())
    for path, key in [(Path(__file__), "preparation_code_sha256"),
                      (source_data, "source_scvic_npz_sha256"),
                      (source_csv, "target_day17_csv_sha256")]:
        if sha(path) != protocol[key]:
            raise ValueError(f"Frozen input mismatch: {key}")
    if protocol["status"] != "FROZEN_BEFORE_EXTRACTION" or protocol["seed"] != 20260921:
        raise ValueError("Unsupported protocol")
    if output.exists():
        raise FileExistsError("Fresh output required; do not overwrite preparation receipts")
    with np.load(source_data, allow_pickle=False) as source:
        names = source["feature_names"].tolist()
        source_canonical = canonical(source["X"])
        computed_source_groups = fingerprints(source_canonical)
        if computed_source_groups != source["group_sha256"].tolist():
            raise ValueError("Recomputed canonical source fingerprints differ from source receipt")
        source_groups = set(computed_source_groups)
    if names != protocol["feature_names"]:
        raise ValueError("Source feature order mismatch")
    mapping = protocol["feature_mapping_scvic_to_dedale"]
    target_names = [mapping[n] for n in names]
    metadata_cols = ["label", "attack_step", "tactic", "technique"]
    groups, raw_counts = {}, Counter()
    offset = 0
    nonfinite_rows = 0
    for frame in pd.read_csv(source_csv, usecols=target_names + metadata_cols,
                             chunksize=100_000, low_memory=False):
        raw_labels = pd.to_numeric(frame["label"], errors="raise").to_numpy(dtype=np.float64)
        if not np.isfinite(raw_labels).all() or not np.isin(raw_labels, [0, 1, 2]).all():
            raise ValueError("Unknown/fractional author label")
        labels = raw_labels.astype(np.int8)
        values = frame[target_names].apply(pd.to_numeric, errors="raise").to_numpy(dtype="<f8")
        nonfinite_rows += int((~np.isfinite(values)).any(axis=1).sum())
        values = canonical(values)
        hashes = fingerprints(values)
        tactics = frame["tactic"].fillna("").astype(str).tolist()
        techniques = frame["technique"].fillna("").astype(str).tolist()
        stages = frame["attack_step"].fillna("").astype(str).tolist()
        for i, fp in enumerate(hashes):
            label = int(labels[i])
            category = "normal" if label == 0 else "lateral" if label == 1 and tactics[i] == "TA0008" else "other"
            raw_counts[category] += 1
            signature = (label, stages[i], tactics[i], techniques[i])
            if fp in groups:
                item = groups[fp]
                item[1] += 1
                item[3] |= item[2] != signature
            else:
                groups[fp] = [offset + i, 1, signature, False, category]
        offset += len(frame)
    source_overlap = {fp for fp in groups if fp in source_groups}
    conflicts = {fp for fp, item in groups.items() if item[3]}
    excluded = source_overlap | conflicts
    retained = {fp: item for fp, item in groups.items() if fp not in excluded}
    normal = [fp for fp, item in retained.items() if item[4] == "normal"]
    lateral = [fp for fp, item in retained.items() if item[4] == "lateral"]
    normal.sort(key=lambda fp: (hashlib.sha256(fp.encode("ascii")).hexdigest(), fp))
    normal = normal[:protocol["maximum_normal_unique_groups"]]
    selected = sorted(normal + lateral)
    if not normal or not lateral:
        raise ValueError("Preparation cannot produce both declared classes")
    indices = np.asarray([retained[fp][0] for fp in selected], dtype=np.int64)
    x = np.empty((len(selected), len(names)), dtype="<f8")
    filled = np.zeros(len(selected), dtype=bool)
    offset = 0
    for frame in pd.read_csv(source_csv, usecols=target_names, chunksize=100_000, low_memory=False):
        positions = np.flatnonzero((indices >= offset) & (indices < offset + len(frame)))
        if len(positions):
            values = frame.iloc[indices[positions] - offset][target_names].apply(pd.to_numeric, errors="raise")
            x[positions] = canonical(values.to_numpy(dtype="<f8"))
            filled[positions] = True
        offset += len(frame)
    if not filled.all() or fingerprints(x) != selected:
        raise ValueError("Second-pass extraction does not match frozen feature groups")
    y = np.asarray([1 if retained[fp][4] == "lateral" else 0 for fp in selected], dtype=np.int8)
    multiplicity = np.asarray([retained[fp][1] for fp in selected], dtype=np.int64)
    output.mkdir(parents=True)
    np.savez_compressed(output / "DATA.npz", X=x, y_binary=y,
                        feature_names=np.asarray(names, dtype=str),
                        group_sha256=np.asarray(selected, dtype="U64"),
                        source_row_indices=indices, multiplicity=multiplicity)
    manifest = {
        "schema_version": 1, "experiment": "DEDALE_DAY17_SOURCE_LOCKED_LATERAL_STRESS",
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "preparation_protocol_sha256": sha(protocol_path),
        "preparation_code_sha256": sha(Path(__file__)),
        "source_scvic_npz_sha256": sha(source_data), "target_day17_csv_sha256": sha(source_csv),
        "data_npz_sha256": sha(output / "DATA.npz"), "feature_names": names,
        "feature_mapping_scvic_to_dedale": mapping, "feature_count": len(names),
        "X_dtype": str(x.dtype), "rows": len(x),
        "class_counts": {"0_normal": int((y == 0).sum()), "1_author_lateral": int((y == 1).sum())},
        "raw_rows": offset, "raw_scope_counts": dict(raw_counts),
        "raw_unique_feature_groups": len(groups),
        "source_overlap_groups": len(source_overlap),
        "source_overlap_rows": sum(groups[fp][1] for fp in source_overlap),
        "conflicting_author_label_groups": len(conflicts),
        "conflicting_author_label_rows": sum(groups[fp][1] for fp in conflicts),
        "overlap_or_conflict_excluded_groups": len(source_overlap | conflicts),
        "overlap_or_conflict_excluded_rows": sum(groups[fp][1] for fp in source_overlap | conflicts),
        "retained_scope_group_counts": dict(Counter(item[4] for item in retained.values())),
        "retained_duplicate_excess_rows": sum(item[1] - 1 for item in retained.values()),
        "selected_raw_multiplicity_by_class": {"normal": int(multiplicity[y == 0].sum()), "lateral": int(multiplicity[y == 1].sum())},
        "rows_with_nonfinite_predictors_before_canonicalization": nonfinite_rows,
        "source_fingerprints_recomputed_and_matched": True,
        "exact_equality_rule": "SHA256 of source-ordered little-endian float64 rows; nonfinite->canonicalNaN and signedzero->positivezero. Byte equality only, no approximate tolerance or semantic-equivalence proof.",
        "scientific_fits": 0, "target_calibration": False, "model_outcomes_inspected": False,
        "independent_campaigns": 1, "documented_lateral_executions": 1,
        "seed": protocol["seed"],
        "interpretation": "One-event external stress evidence only. Stratified unique-feature sample, all lateral plus at most100000normal; precision/F1 are not deployment-prevalence estimates. Other attack stages excluded by frozen scope. No target fitting/calibration/threshold selection.",
    }
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    complete = {"status": "COMPLETE", "file_sha256": {n: sha(output / n) for n in ["DATA.npz", "MANIFEST.json"]},
                "protocol_sha256": sha(protocol_path)}
    (output / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["rows", "class_counts", "source_overlap_rows", "conflicting_author_label_rows", "raw_unique_feature_groups", "data_npz_sha256"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--source-data", type=Path, required=True)
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    prepare(a.protocol, a.source_data, a.source_csv, a.output)
