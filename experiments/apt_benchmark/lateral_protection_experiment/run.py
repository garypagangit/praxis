"""Immutable, two-phase fitting and policy evaluation for source development."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import warnings
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from ..tabular_batch.run_e1 import (sha256_file, canonical_hash, write_json, utc_now,
                                  package_versions, load_data, probability_metrics)
from ..tabular_followup.run_strong_baselines import select_support
from .backend import fit_model
from .selection import select_policies, alert_metrics, point_gate
from .specification import design

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ["experiments/apt_benchmark/lateral_protection_experiment/" + p for p in
           ["run.py", "backend.py", "selection.py", "specification.py", "__init__.py"]] + [
           "experiments/apt_benchmark/tabular_batch/run_e1.py",
           "experiments/apt_benchmark/tabular_batch/model_backend.py",
           "experiments/apt_benchmark/tabular_followup/run_strong_baselines.py"]

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def immutable_json(path, value):
    if path.exists():
        if read(path) != value:
            raise ValueError(f"Refusing to replace immutable receipt {path}")
    else:
        write_json(path, value)

def partitions(data, protocol):
    selected, verification = [], []
    for k in range(len(data["classes"])):
        pool = np.flatnonzero((data["split"] == 1) & (data["y"] == k)).tolist()
        pool.sort(key=lambda i: hashlib.sha256(f"{protocol['partition_tag']}|{data['group_sha256'][i]}".encode("ascii")).digest())
        middle = len(pool) // 2
        selected.extend(pool[:middle]); verification.extend(pool[middle:])
    return {"selection": np.asarray(selected), "verification": np.asarray(verification),
            "test": np.flatnonzero(data["split"] == 2)}

def support(data, budget, seed):
    indices = select_support(data, seed, "abundant_benign_1024")
    return indices[:192 + budget - 32]

def roster(data, indices):
    return {"indices": indices.tolist(), "fingerprints": data["group_sha256"][indices].tolist(),
            "class_counts": np.bincount(data["y"][indices], minlength=len(data["classes"])).tolist()}

def prepare(data, protocol, protocol_path, out):
    fixed = {"schema_version": 1, "protocol_sha256": sha256_file(protocol_path),
             "data_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
             "source_hashes": {p: sha256_file(ROOT / p) for p in SOURCES}, "versions": package_versions(),
             "classes": data["classes"].tolist(), "feature_names": data["feature_names"].tolist(),
             "partitions": {k: roster(data, v) for k, v in partitions(data, protocol).items()},
             "groups": [{**g, **roster(data, support(data, g["budget"], g["seed"]))} for g in protocol["groups"]]}
    binding = canonical_hash(fixed)
    path = out / "PREFIT_RECEIPT.json"
    if path.exists():
        receipt = read(path)
        if receipt["fixed"] != fixed or receipt["execution_binding"] != binding:
            raise ValueError("Input, code, environment, or fitting roster changed since prefit freeze")
    else:
        receipt = {"created_utc": utc_now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "execution_binding": binding, "fixed": fixed}
        immutable_json(path, receipt)
    return receipt

def verify_files(folder, records):
    for name, digest in records.items():
        if not (folder / name).is_file() or sha256_file(folder / name) != digest:
            raise ValueError(f"Artifact hash mismatch: {folder / name}")

def predict(classifier, imputer, X, classes, threads):
    if not np.array_equal(classifier.classes_, np.arange(len(classes))):
        raise ValueError("Probability class order differs")
    with threadpool_limits(limits=threads):
        p = np.concatenate([np.asarray(classifier.predict_proba(imputer.transform(X[i:i+1024])), dtype=np.float64)
                            for i in range(0, len(X), 1024)])
    if p.shape != (len(X), len(classes)) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(1), 1, atol=1e-5, rtol=0):
        raise ValueError("Invalid probability matrix")
    return p

def arrays(data, indices, probabilities, prefix=""):
    return {prefix + "probabilities": probabilities, prefix + "y": data["y"][indices],
            prefix + "indices": indices, prefix + "fingerprints": data["group_sha256"][indices]}

def run_group(data, protocol, receipt, out, group):
    budget, seed = group["budget"], group["seed"]
    group_dir = out / "groups" / str(budget) / str(seed)
    group_dir.mkdir(parents=True, exist_ok=True)
    binding = receipt["execution_binding"]
    classes = data["classes"].tolist(); normal = classes.index("NormalTraffic"); lateral = classes.index("LateralMovement")
    fitting = support(data, budget, seed); parts = partitions(data, protocol)
    cells = []
    for model in protocol["models"]:
        for scheme in protocol["schemes"]:
            cell_id = model + "/" + scheme
            folder = out / "cells" / str(budget) / str(seed) / model / scheme
            folder.mkdir(parents=True, exist_ok=True)
            fit_complete = folder / "FIT_COMPLETE.json"
            if fit_complete.exists():
                completed = read(fit_complete)
                if completed["execution_binding"] != binding:
                    raise ValueError("Stale fit completion")
                verify_files(folder, completed["files"])
            else:
                if (folder / "STARTED.json").exists():
                    raise ValueError(f"Incomplete fit requires a new output root, not silent overwrite: {folder}")
                immutable_json(folder / "STARTED.json", {"created_utc": utc_now(), "execution_binding": binding,
                    "budget": budget, "seed": seed, "cell_id": cell_id})
                classifier, imputer, cv, timing = fit_model(model, data["X"][fitting], data["y"][fitting], seed,
                    protocol["model_grids"][model], scheme, normal, lateral, len(classes), protocol["cpu_threads"])
                joblib.dump({"classifier": classifier, "imputer": imputer}, folder / "MODEL.joblib", compress=3)
                selection_p = predict(classifier, imputer, data["X"][parts["selection"]], classes, protocol["cpu_threads"])
                np.savez_compressed(folder / "SELECTION.npz", **arrays(data, parts["selection"], selection_p), classes=data["classes"])
                fitted = {"created_utc": utc_now(), "execution_binding": binding, "cell_id": cell_id, "budget": budget,
                    "seed": seed, "cv_metadata": cv, "timing_seconds": timing, "support_sha256": canonical_hash(fitting.tolist()),
                    "imputer_statistics": imputer.statistics_.tolist(), "model_sha256": sha256_file(folder / "MODEL.joblib"),
                    "selection_sha256": sha256_file(folder / "SELECTION.npz")}
                immutable_json(folder / "FITTED.json", fitted)
                immutable_json(fit_complete, {"created_utc": utc_now(), "execution_binding": binding,
                    "files": {p: sha256_file(folder / p) for p in ["STARTED.json", "MODEL.joblib", "SELECTION.npz", "FITTED.json"]}})
                print(json.dumps({"event": "FIT_COMPLETE", "budget": budget, "seed": seed, "cell_id": cell_id, "utc": utc_now()}), flush=True)
            with np.load(folder / "SELECTION.npz", allow_pickle=False) as a:
                scores = 1 - a["probabilities"][:, normal]
            cells.append({"cell_id": cell_id, "folder": folder, "scores": scores, "fit": read(folder / "FITTED.json")})
    lock_path = group_dir / "SELECTION_LOCK.json"
    choice = select_policies(cells, data["y"][parts["selection"]], normal, lateral)
    natural = [c for c in cells if c["cell_id"].endswith("/natural")]
    cvbest = max(natural, key=lambda c: c["fit"]["cv_metadata"]["selected_mean_macro_f1"])
    normal_scores = cvbest["scores"][data["y"][parts["selection"]] == normal]
    thresholds, counts = np.unique(normal_scores, return_counts=True)
    fp = len(normal_scores) - np.cumsum(counts)
    threshold = float(thresholds[np.flatnonzero(fp * 100 <= len(normal_scores))[0]])
    controls = {"cv_natural_argmax": {"cell_id": cvbest["cell_id"], "rule": "argmax"},
                "cv_natural_benign_threshold": {"cell_id": cvbest["cell_id"], "rule": "threshold", "threshold": threshold}}
    lock_core = {"execution_binding": binding, "budget": budget, "seed": seed, **choice, "controls": controls,
                 "fit_complete_sha256": {c["cell_id"]: sha256_file(c["folder"] / "FIT_COMPLETE.json") for c in cells}}
    if lock_path.exists():
        lock = read(lock_path)
        if {k: v for k, v in lock.items() if k != "created_utc"} != lock_core:
            raise ValueError("Locked policy differs from selection-only reconstruction")
    else:
        lock = {"created_utc": utc_now(), **lock_core}
        immutable_json(lock_path, lock)
    lock_sha = sha256_file(lock_path)
    cell_results = {}
    for cell in cells:
        folder = cell["folder"]
        complete_path = folder / "COMPLETE.json"
        if complete_path.exists():
            completed = read(complete_path)
            if completed["execution_binding"] != binding or completed["selection_lock_sha256"] != lock_sha:
                raise ValueError("Evaluation binding differs")
            verify_files(folder, completed["files"])
            result = read(folder / "CELL.json")
        else:
            if (folder / "EVALUATION_STARTED.json").exists():
                raise ValueError("Partial evaluation cannot be silently overwritten")
            immutable_json(folder / "EVALUATION_STARTED.json", {"created_utc": utc_now(), "selection_lock_sha256": lock_sha, "execution_binding": binding})
            fitted = joblib.load(folder / "MODEL.joblib")
            saved = {"classes": data["classes"]}; metrics = {}
            for part in ["verification", "test"]:
                indices = parts[part]
                p = predict(fitted["classifier"], fitted["imputer"], data["X"][indices], classes, protocol["cpu_threads"])
                saved.update(arrays(data, indices, p, part + "_"))
                metrics[part] = {"classification": probability_metrics(data["y"][indices], p, classes),
                    "argmax_alert": alert_metrics(data["y"][indices], 1-p[:, normal], p.argmax(1) != normal, classes, normal)}
            np.savez_compressed(folder / "EVALUATION.npz", **saved)
            result = {"created_utc": utc_now(), "execution_binding": binding, "selection_lock_sha256": lock_sha,
                      "cell_id": cell["cell_id"], "budget": budget, "seed": seed, "metrics": metrics}
            immutable_json(folder / "CELL.json", result)
            immutable_json(complete_path, {"created_utc": utc_now(), "execution_binding": binding, "selection_lock_sha256": lock_sha,
                "files": {p: sha256_file(folder / p) for p in ["CELL.json", "EVALUATION.npz", "EVALUATION_STARTED.json", "FIT_COMPLETE.json"]}})
        cell_results[cell["cell_id"]] = result
    policy_metrics = {p: {} for p in ["verification", "test"]}
    for name, policy in {**lock["choices"], **controls}.items():
        folder = next(c["folder"] for c in cells if c["cell_id"] == policy["cell_id"])
        with np.load(folder / "EVALUATION.npz", allow_pickle=False) as a:
            for part in policy_metrics:
                p, y = a[part + "_probabilities"], a[part + "_y"]
                scores = 1-p[:, normal]
                flags = p.argmax(1) != normal if policy.get("rule") == "argmax" else scores > policy["threshold"]
                policy_metrics[part][name] = alert_metrics(y, scores, flags, classes, normal)
    result = {"execution_binding": binding, "budget": budget, "seed": seed, "selection_status": lock["status"],
              "selection_lock_sha256": lock_sha, "selection": choice, "controls": controls, "partitions": policy_metrics,
              "cell_complete_sha256": {c["cell_id"]: sha256_file(c["folder"] / "COMPLETE.json") for c in cells}}
    immutable_json(group_dir / "RESULT.json", result)
    print(json.dumps({"event": "GROUP_COMPLETE", "budget": budget, "seed": seed, "status": lock["status"], "utc": utc_now()}), flush=True)

def summarize(protocol, receipt, out):
    rows = []
    for g in protocol["groups"]:
        path = out / "groups" / str(g["budget"]) / str(g["seed"]) / "RESULT.json"
        if path.exists():
            result = read(path)
            if result["execution_binding"] != receipt["execution_binding"]:
                raise ValueError("Mixed execution bindings")
            rows.append(result)
    primary = [r for r in rows if r["budget"] == 1024]
    value = {"created_utc": utc_now(), "execution_binding": receipt["execution_binding"],
        "completed_groups": len(rows), "required_groups": len(protocol["groups"]),
        "completed_cells": 8 * len(rows), "required_cells": 8 * len(protocol["groups"]),
        "status": "COMPLETE" if len(rows) == len(protocol["groups"]) else "INCOMPLETE",
        "primary_gate": point_gate(primary, 10), "secondary_gates": {str(b): point_gate([r for r in rows if r["budget"] == b], 3) for b in [32, 128, 512]},
        "groups": rows}
    write_json(out / "SUMMARY.json", value)
    return value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path); parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--prepare-only", action="store_true"); parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--group-indices", nargs="*", type=int)
    args = parser.parse_args(); protocol = read(args.protocol)
    if protocol != design():
        raise ValueError("Protocol differs from the frozen specification")
    data, _ = load_data(args.data, protocol)
    if sha256_file(ROOT / "experiments/apt_benchmark/tabular_batch/protocol.json") != protocol["e1_protocol_sha256"]:
        raise ValueError("Original protocol changed")
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = prepare(data, protocol, args.protocol, args.out)
    warnings.filterwarnings("ignore", message="X does not have valid feature names")
    if args.prepare_only:
        print(json.dumps({"status": "PREPARED", "binding": receipt["execution_binding"]})); return
    if not args.summarize_only:
        indices = list(range(len(protocol["groups"]))) if args.group_indices is None else args.group_indices
        if len(set(indices)) != len(indices) or any(i < 0 or i >= len(protocol["groups"]) for i in indices):
            raise ValueError("Invalid or duplicate group indices")
        for i in indices:
            run_group(data, protocol, receipt, args.out, protocol["groups"][i])
    # Parallel workers never write the shared summary. The coordinator does.
    if args.group_indices is None or args.summarize_only:
        result = summarize(protocol, receipt, args.out)
        print(json.dumps({"status": result["status"], "primary_gate": result["primary_gate"]}))

if __name__ == "__main__":
    main()
