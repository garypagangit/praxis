"""Audit locked-source external predictions without inference or model loading."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from . import audit


POLICIES = ["reference", "candidate", "threshold_only", "cv_natural_argmax", "cv_natural_benign_threshold"]
EXTERNAL_SOURCE = "experiments/apt_benchmark/lateral_protection_experiment/run_external.py"


def canonical_fingerprints(X):
    rows = np.array(X, dtype="<f8", order="C", copy=True)
    rows[~np.isfinite(rows)] = np.nan
    rows[rows == 0] = 0.0
    return [hashlib.sha256(row.tobytes(order="C")).hexdigest() for row in rows]


def check_target(data_path, protocol, source_data, source_fixed):
    data_path = Path(data_path)
    manifest_path = data_path.with_name("MANIFEST.json")
    audit.require(audit.file_hash(data_path) == protocol["data_sha256"], "External input hash differs")
    audit.require(audit.file_hash(manifest_path) == protocol["manifest_sha256"], "External manifest hash differs")
    manifest = audit.read_json(manifest_path)
    audit.require(manifest["data_npz_sha256"] == protocol["data_sha256"], "Manifest target binding differs")
    audit.require(manifest["source_scvic_npz_sha256"] == source_fixed["data_sha256"], "Manifest source binding differs")
    with np.load(data_path, allow_pickle=False) as archive:
        data = {k: archive[k] for k in archive.files}
    audit.require({"X", "y_binary", "feature_names", "group_sha256", "source_row_indices", "multiplicity"} == set(data), "Target array roster differs")
    X, y = data["X"], data["y_binary"]
    audit.require(X.ndim == 2 and X.shape[1] == len(source_fixed["feature_names"]) and not np.isinf(X).any(), "Invalid target feature matrix")
    audit.require(all(data[k].shape == (len(X),) for k in ["y_binary", "group_sha256", "source_row_indices", "multiplicity"]), "Target row metadata differs")
    audit.require(y.dtype.kind in "iu" and np.array_equal(np.unique(y), [0, 1]), "Target binary labels differ")
    audit.require(data["feature_names"].tolist() == source_fixed["feature_names"] == manifest["feature_names"], "Target/source feature order differs")
    audit.require(data["group_sha256"].tolist() == canonical_fingerprints(X), "Target fingerprints do not match features")
    audit.require(len(set(data["group_sha256"].tolist())) == len(X), "Target contains repeated feature groups")
    audit.require(not set(data["group_sha256"].tolist()) & set(source_data["group_sha256"].tolist()), "Target contains source feature overlap")
    audit.require(data["source_row_indices"].dtype.kind in "iu" and len(np.unique(data["source_row_indices"])) == len(X)
                  and np.all(data["source_row_indices"] >= 0), "Invalid target source row IDs")
    audit.require(data["multiplicity"].dtype.kind in "iu" and np.all(data["multiplicity"] >= 1), "Invalid target multiplicities")
    normal, lateral = int(np.count_nonzero(y == 0)), int(np.count_nonzero(y == 1))
    audit.require(0 < normal <= 100000 and 0 < lateral <= 4, "Target exceeds frozen stress scope")
    audit.require(manifest["rows"] == len(X) and manifest["class_counts"] == {"0_normal": normal, "1_author_lateral": lateral}, "Manifest target counts differ")
    audit.require(manifest["independent_campaigns"] == 1 and manifest["documented_lateral_executions"] == 1, "Target independence scope changed")
    audit.require(manifest["scientific_fits"] == 0 and manifest["target_calibration"] is False, "Unexpected target fitting/calibration")
    return data, manifest


def audit_external(data_path, source_data_path, source_protocol_path, source_run, protocol_path, run):
    source_run, protocol_path, run = Path(source_run), Path(protocol_path), Path(run)
    protocol = audit.read_json(protocol_path)
    source_protocol = audit.read_json(source_protocol_path)
    audit.check_protocol(source_protocol)
    source_data = audit.load_bound_input(source_data_path, source_protocol)
    source_receipt_path = source_run / "PREFIT_RECEIPT.json"
    source = audit.read_json(source_receipt_path)
    fixed, binding = source["fixed"], source["execution_binding"]
    audit.require(binding == audit.value_hash(fixed), "Source prefit digest differs")
    audit.require(fixed["protocol_sha256"] == audit.file_hash(source_protocol_path), "Source protocol hash differs")
    audit.require(fixed["data_sha256"] == source_protocol["data_npz_sha256"] and fixed["manifest_sha256"] == source_protocol["manifest_sha256"], "Source input bindings differ")
    audit.require(audit.file_hash(audit.REPO / "experiments/apt_benchmark/tabular_batch/protocol.json") == source_protocol["e1_protocol_sha256"], "Original E1 protocol differs")
    audit.compare(source_data["classes"].tolist(), fixed["classes"], "Source classes")
    audit.compare(source_data["feature_names"].tolist(), fixed["feature_names"], "Source features")
    audit.verify_files(audit.REPO, fixed["source_hashes"], audit.SOURCE_FILES)
    expected_constants = {"schema_version": 1, "experiment": "DEDALE_LOCKED_SOURCE_STRESS_V1",
        "status": "FROZEN_BEFORE_EXTERNAL_PREDICTIONS", "source_budget": 1024, "source_seed": 20260921,
        "source_execution_binding": binding, "source_prefit_sha256": audit.file_hash(source_receipt_path),
        "policy_names": POLICIES, "cpu_threads": 4, "normal_binary_label": 0, "lateral_binary_label": 1}
    for key, value in expected_constants.items():
        audit.compare(value, protocol.get(key), f"External protocol.{key}")
    audit.verify_files(audit.REPO, protocol["source_hashes"], audit.SOURCE_FILES + [EXTERNAL_SOURCE])
    audit.require(all(protocol["source_hashes"][name] == fixed["source_hashes"][name] for name in audit.SOURCE_FILES), "Source code differs from external freeze")
    parts = audit.reconstruct_partitions(source_data, source_protocol["partition_tag"])
    audit.compare({k: audit.roster(source_data, v) for k, v in parts.items()}, fixed["partitions"], "Source partitions")
    audit.compare([{**g, **audit.roster(source_data, audit.reconstruct_support(source_data, g["budget"], g["seed"]))}
                   for g in source_protocol["groups"]], fixed["groups"], "Source supports")
    # Recheck only the one frozen source group; no fit or inference is called.
    group = {"budget": 1024, "seed": 20260921}
    source_result = audit.check_group(source_data, source_protocol, source, source_run, group, parts)
    target, manifest = check_target(data_path, protocol, source_data, fixed)
    lock_path = source_run / "groups/1024/20260921/SELECTION_LOCK.json"
    lock = audit.read_json(lock_path)
    policies = {**lock["choices"], **lock["controls"]}
    expected_policy_names = set(POLICIES if lock["status"] == "SELECTED" else POLICIES[-2:])
    audit.require(lock["status"] in {"SELECTED", "INFEASIBLE"} and set(policies) == expected_policy_names, "Source policy roster differs")
    preflight_path, result_path, predictions_path = [run / name for name in ["PREFLIGHT.json", "RESULT.json", "PREDICTIONS.npz"]]
    preflight, result = audit.read_json(preflight_path), audit.read_json(result_path)
    audit.require(audit.stamp(lock) <= audit.stamp(preflight) <= audit.stamp(result), "External prediction receipt order differs")
    audit.require(preflight["protocol_hash"] == audit.value_hash(protocol) and preflight["source_lock_sha256"] == audit.file_hash(lock_path), "External preflight policy/protocol binding differs")
    audit.require(preflight["data_sha256"] == protocol["data_sha256"], "External preflight data binding differs")
    audit.compare(fixed["versions"], preflight["versions"], "Source/external runtime versions")
    model_ids = sorted({v["cell_id"] for v in policies.values()})
    model_hashes = {}
    for cell_id in model_ids:
        folder = source_run / "cells/1024/20260921" / cell_id
        audit.require(audit.file_hash(folder / "FIT_COMPLETE.json") == lock["fit_complete_sha256"][cell_id], "Selected source fit receipt differs")
        fit_complete = audit.read_json(folder / "FIT_COMPLETE.json")
        audit.verify_files(folder, fit_complete["files"], ["STARTED.json", "MODEL.joblib", "SELECTION.npz", "FITTED.json"])
        model_hashes[cell_id] = audit.file_hash(folder / "MODEL.joblib")
    audit.compare(model_hashes, preflight["model_hashes"], "External model provenance")
    audit.require(result["preflight_sha256"] == audit.file_hash(preflight_path) and result["predictions_sha256"] == audit.file_hash(predictions_path), "External result artifact hash mismatch")
    classes = fixed["classes"]
    normal, lateral = classes.index("NormalTraffic"), classes.index("LateralMovement")
    y = np.where(target["y_binary"] == 0, normal, lateral)
    predictions = {}
    with np.load(predictions_path, allow_pickle=False) as archive:
        audit.require(set(archive.files) == {"y_binary", "group_sha256", "classes"} | {k.replace("/", "__") for k in model_ids}, "External prediction roster differs")
        audit.require(archive["classes"].tolist() == classes, "External probability class order differs")
        audit.require(np.array_equal(archive["y_binary"], target["y_binary"]), "External prediction labels differ")
        audit.require(np.array_equal(archive["group_sha256"], target["group_sha256"]), "External prediction row fingerprints differ")
        for model_id in model_ids:
            predictions[model_id] = audit.check_probabilities(archive[model_id.replace("/", "__")], y, len(classes))
    expected_metrics = {}
    for name in POLICIES:
        if name in policies:
            policy = policies[name]
            p = predictions[policy["cell_id"]]
            scores = 1 - p[:, normal]
            flags = p.argmax(axis=1) != normal if policy.get("rule") == "argmax" else scores > policy["threshold"]
            expected_metrics[name] = audit.metrics(y, scores, flags, classes, normal)
    expected_result = {"status": "COMPLETE_LIMITED_EXTERNAL_STRESS", "source_selection_status": lock["status"],
        "source_budget": 1024, "source_seed": 20260921, "rows": len(y), "benign_n": int(np.count_nonzero(target["y_binary"] == 0)),
        "lateral_n": int(np.count_nonzero(target["y_binary"] == 1)), "source_policies": policies,
        "missing_policies": [p for p in POLICIES if p not in policies], "metrics": expected_metrics, "protocol": protocol,
        "preflight_sha256": audit.file_hash(preflight_path), "predictions_sha256": audit.file_hash(predictions_path),
        "interpretation": protocol["interpretation"]}
    audit.compare(expected_result, {k: v for k, v in result.items() if k != "created_utc"}, "External result")
    return {"audit_status": "PASS", "run_status": "COMPLETE_LIMITED_EXTERNAL_STRESS", "rows": len(y),
        "benign_n": expected_result["benign_n"], "lateral_n": expected_result["lateral_n"],
        "source_selection_status": lock["status"], "source_budget": 1024, "source_seed": 20260921,
        "missing_policies": expected_result["missing_policies"], "metrics": expected_metrics,
        "artifact_hashes": {p.name: audit.file_hash(p) for p in [result_path, preflight_path, predictions_path]},
        "external_protocol_sha256": audit.file_hash(protocol_path), "target_data_sha256": protocol["data_sha256"],
        "target_manifest_sha256": protocol["manifest_sha256"], "source_prefit_sha256": audit.file_hash(source_receipt_path),
        "source_selection_lock_sha256": audit.file_hash(lock_path),
        "source_group_result_sha256": audit.file_hash(source_run / "groups/1024/20260921/RESULT.json"),
        "audit_source_sha256": audit.file_hash(__file__), "common_auditor_sha256": audit.file_hash(audit.__file__),
        "checks": ["Frozen source, target, code, protocol and model provenance", "Independent source-group selection reconstruction",
            "Target row fingerprints recomputed and source overlap excluded", "Saved prediction labels/classes/rows",
            "Every locked-policy binary and stage count, FPR, precision, recall, F1, ROC-AUC and average precision"],
        "limitations": ["No model loading, fitting or inference was repeated. Raw CSV extraction/author labels were not independently rebuilt in this audit.",
            "One documented execution with at most four lateral feature groups cannot confirm a three-point protection margin.",
            "The selected target prevalence is not a deployment prevalence; no independent-incident or population guarantee is established."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--source-data", required=True, type=Path)
    parser.add_argument("--source-protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "AUDIT.json"
    audit.require(not path.exists(), "Use a fresh external audit directory")
    try:
        result = audit_external(args.data, args.source_data, args.source_protocol, args.source_run, args.protocol, args.run)
    except Exception as exc:
        result = {"audit_status": "FAIL", "run_status": "NOT_VERIFIED", "error_type": type(exc).__name__, "error": str(exc)}
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    result["audited_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["audit_status", "run_status", "benign_n", "lateral_n", "missing_policies"]}))


if __name__ == "__main__":
    main()
