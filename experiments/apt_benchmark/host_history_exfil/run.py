"""Fixed single-sensor chronological UNRAVELED host-context pilot."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from threadpoolctl import threadpool_limits

from .context import history_features, role, role_features, ROLE_NAMES, STATE_NAMES, WINDOWS_MS

INPUT_SHA = "1b6da619c1ed830f0f131bfb7778589d781c3826e7fd3dc50f21bd7829ead002"
SEEDS = [20260922, 20260923, 20260924]
CLASSES = ["Benign", "OtherAttackStage", "LateralMovement", "DataExfiltration"]
STAGES = {"Benign": 0, "Reconnaissance": 1, "Establish Foothold": 1, "Cover up": 1, "Lateral Movement": 2, "Data Exfiltration": 3}
ARMS = ["current", "current_roles", "current_history", "current_roles_history", "current_roles_wrong_host_history", "roles_only"]
PARAMS = {"n_estimators": 300, "num_leaves": 15, "learning_rate": .05, "min_child_samples": 10, "reg_lambda": 1.}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def utc():
    return datetime.now(timezone.utc).isoformat()


def protocol():
    return {"version": 1, "status": "FROZEN_BEFORE_FEATURE_PREPARATION_AND_FITS", "input_manifest_sha256": INPUT_SHA,
            "study": "Do coarse host roles and earlier completed activity distinguish author movement and exfiltration stages?",
            "source": "UNRAVELED author net1013x sensor; eleven complete capture files as assigned in input manifest",
            "classes": CLASSES, "stage_mapping": STAGES, "seeds": SEEDS, "arms": ARMS, "model": "LightGBM", "parameters": PARAMS,
            "fit_caps_by_class": [20000, 5000, 5000, 5000], "fit_sampling": "SHA256 HOST_HISTORY_V1|seed|observable-event-hash within original fit captures",
            "current_features": "Numeric stable prefix except identifiers, endpoint identities/ports, first/last absolute timestamps, VLAN/tunnel IDs; add three destination-service categories equally to every current-feature arm",
            "roles": ROLE_NAMES, "role_source": "Author static topology:10.1.1/2/3 department;10.1.4 public services;10.1.5 private services;other address unknown, not automatically Internet",
            "history_windows_ms": list(WINDOWS_MS), "history_state_names": STATE_NAMES,
            "history_availability": "Strict end_of_prior_flow < start_of_current_flow; compute all qualified flows before fitting-row subsampling; no labels or predictions used in history",
            "history_control": "Current roles plus earlier state of a deterministic different host selected from only the hosts observed by query time",
            "thresholds": "Calibration-only exfil F1 maximum (higher threshold on ties), plus empirical all-nonexfil tails 0.1/0.5/1/2 percent",
            "evaluation": "All later test rows; four-class macroF1, per-stage AP/ROC/F1/P/R, Exfil-vs-Lateral AP, exfil false labels by true class and role strata",
            "important_stratum": "Department source to private-services destination contains both target labels in test; training/calibration have no exfil examples in this stratum",
            "calibration_limitation": "No lateral movement calibration rows; no movement threshold tuning, calibration claim or recall protection guarantee",
            "primary_comparisons": ["roles minus current", "history minus current", "roles+history minus roles", "roles+history minus history", "roles+history minus wrong-host control"],
            "interpretation": "Previously exposed alternative dataset; one APT campaign with later-period evaluation. Author Stage is progress annotation, not independently verified stolen-data content. No independent-campaign, early-warning, or algorithm-novelty claim",
            "success_rule": "Report paired directions and measured costs, no arbitrary pass/fail magnitude; disclose sparse lateral support and role shift"}


def prepare(inputs_path, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Fresh preparation directory required")
    if sha(inputs_path) != INPUT_SHA:
        raise ValueError("Input qualification changed")
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    root = Path(inputs["private_raw_root"])
    header, records, source_rows = None, [], []
    exclude = {"id", "expiration_id", "src_ip", "dst_ip", "src_mac", "dst_mac", "src_oui", "dst_oui", "src_port", "dst_port", "vlan_id", "tunnel_id"}
    source_receipts = []
    for file_index, item in enumerate(inputs["files"]):
        path = root / item["source_file"]
        if sha(path) != item["sha256"]:
            raise ValueError("Raw source changed: " + str(path))
        print("READ " + item["source_file"], flush=True)
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            names = next(reader)
            if header is None:
                header = names
                positions = {n: i for i, n in enumerate(header)}
                feature_names = [n for n in header[:77] if n not in exclude and "first_seen" not in n and "last_seen" not in n]
                numeric_positions = [positions[n] for n in feature_names]
            if names != header:
                raise ValueError("Source schema changed")
            count, counts = 0, Counter()
            for row_number, row in enumerate(reader, 2):
                if len(row) < 89 or row[-3] not in STAGES:
                    raise ValueError("Unresolved right-anchored annotation")
                stage, signature = row[-3], row[-1]
                if (stage == "Benign" and signature != "None") or (stage != "Benign" and signature not in {"APT", "AA", "SH"}):
                    raise ValueError("Unexpected stage/signature combination")
                nums = [float(row[i]) for i in numeric_positions]
                if not np.isfinite(nums).all():
                    raise ValueError("Nonfinite predictor")
                start, end = float(row[positions["bidirectional_first_seen_ms"]]), float(row[positions["bidirectional_last_seen_ms"]])
                if not (0 < start <= end):
                    raise ValueError("Invalid chronology")
                src, dst = row[positions["src_ip"]], row[positions["dst_ip"]]
                sport, dport = int(row[positions["src_port"]]), int(row[positions["dst_port"]])
                admin = float(dport in {22, 135, 139, 445, 3389, 5985, 5986})
                nums.extend([admin, float(dport in {80, 443, 8080, 8443}), float(dport == 53)])
                # Identity binds observables only, not labels, capture name or local row.
                observable = [src, dst, sport, dport, start, end, *nums]
                key = hashlib.sha256(json.dumps(observable, separators=(",", ":")).encode()).hexdigest()
                records.append((nums, STAGES[stage], {"fit": 0, "calibration": 1, "test": 2}.get(item["split"], {"cal": 1}.get(item["split"])), start, end, src, dst,
                                float(row[positions["src2dst_bytes"]]), float(row[positions["dst2src_bytes"]]), admin, key, file_index))
                source_rows.append(row_number)
                count += 1; counts[stage] += 1
            if count != item["rows"] or dict(counts) != item["right_anchored_stage_counts"]:
                raise ValueError("Qualified source row counts changed")
        source_receipts.append({"source_file": item["source_file"], "sha256": item["sha256"], "rows": count, "right_anchored_stage_counts": dict(counts)})
    # Remove every repeated observable identity across the selected files. Exact
    # repeats are not independent events; conflicting labels are quarantined.
    groups = {}
    for i, row in enumerate(records):
        groups.setdefault(row[10], []).append(i)
    duplicate_rows, conflicts, kept = 0, 0, []
    for indexes in groups.values():
        if len({records[i][1] for i in indexes}) > 1:
            conflicts += len(indexes)
        else:
            duplicate_rows += len(indexes) - 1
            kept.append(indexes[0])
    records = [records[i] for i in kept]
    source_rows = np.asarray(source_rows)[kept]
    X = np.asarray([r[0] for r in records], dtype=float)
    y, split, start, end = (np.asarray([r[k] for r in records]) for k in (1, 2, 3, 4))
    if set(np.unique(split)) != {0, 1, 2}:
        raise ValueError("Invalid split")
    split = split.astype(np.int8)
    if not (end[split == 0].max() < start[split == 1].min() and end[split == 1].max() < start[split == 2].min()):
        raise ValueError("Training/calibration/test acquisition periods overlap")
    src, dst = (np.asarray([r[k] for r in records]) for k in (5, 6))
    roles = role_features(src, dst)
    forward, reverse, admin = (np.asarray([r[k] for r in records]) for k in (7, 8, 9))
    history, wrong, latest, latest_wrong = history_features(start, end, src, dst, forward, reverse, admin)
    names = feature_names + ["dst_remote_admin_service", "dst_web_service", "dst_dns_service"]
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / "DATA.npz", current=X, roles=roles, history=history, wrong_history=wrong, y=y, split=split,
                        start=start, end=end, latest_history_end=latest, latest_wrong_history_end=latest_wrong,
                        src_role=np.asarray([role(v) for v in src]), dst_role=np.asarray([role(v) for v in dst]),
                        group_sha256=np.asarray([r[10] for r in records]), capture=np.asarray([r[11] for r in records]), source_row=source_rows,
                        feature_names=np.asarray(names), src=src, dst=dst)
    receipt = {"prepared_utc": utc(), "input_manifest_sha256": sha(inputs_path), "data_sha256": sha(output / "DATA.npz"),
               "runner_sha256": sha(__file__), "context_sha256": sha(Path(__file__).with_name("context.py")),
               "rows": len(y), "duplicate_rows_removed": duplicate_rows, "conflicting_rows_quarantined": conflicts,
               "current_features": names, "role_features": 8, "history_features": history.shape[1],
               "split_counts": {name: dict(zip(CLASSES, np.bincount(y[split == k], minlength=4).tolist())) for k, name in enumerate(["fit", "calibration", "test"])},
               "source_files": source_receipts,
               "availability_checks": {"all_history_ends_strictly_before_current_start": bool(np.all(latest < start)), "all_wrong_host_ends_strictly_before_current_start": bool(np.all(latest_wrong < start))}}
    write(output / "PREPARATION.json", receipt)
    print(json.dumps({"prepared_rows": len(y), "counts": receipt["split_counts"]}), flush=True)


def f1_threshold(y, score):
    order = np.argsort(score, kind="stable"); s, t = score[order], y[order]
    ends = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]
    tp = np.r_[t.sum(), t.sum() - np.cumsum(t)[ends]]
    fp = np.r_[(~t).sum(), (~t).sum() - np.cumsum(~t)[ends]]
    den = t.sum() + tp + fp
    f = np.divide(2 * tp, den, out=np.zeros(len(den)), where=den > 0)
    return float(np.r_[-1., s[ends]][np.flatnonzero(f == f.max())[-1]])


def alert_metrics(y, flags):
    truth = y == 3
    tp, fp, fn = int(np.sum(truth & flags)), int(np.sum(~truth & flags)), int(np.sum(truth & ~flags))
    return {"tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp + fp) if tp + fp else 0., "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
            "false_exfil_by_true_class": {c: int(np.sum((y == k) & flags)) for k, c in enumerate(CLASSES) if k != 3}}


def metrics(y, p):
    predicted = p.argmax(axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(y, predicted, labels=np.arange(4), zero_division=0)
    out = {"rows": len(y), "macro_f1_all_four": float(f1.mean()), "confusion": confusion_matrix(y, predicted, labels=np.arange(4)).tolist(),
           "per_class": {c: {"support": int(support[k]), "precision": float(precision[k]), "recall": float(recall[k]), "f1": float(f1[k]),
                             "ap": float(average_precision_score(y == k, p[:, k])) if np.any(y == k) else None,
                             "roc_auc": float(roc_auc_score(y == k, p[:, k])) if np.any(y == k) and np.any(y != k) else None} for k, c in enumerate(CLASSES)}}
    pair = np.isin(y, [2, 3])
    score = p[:, 3] / np.maximum(p[:, 2] + p[:, 3], 1e-12)
    out["exfil_vs_lateral_ap"] = float(average_precision_score(y[pair] == 3, score[pair])) if np.any(y == 2) and np.any(y == 3) else None
    out["exfil_vs_lateral_exfil_prevalence"] = float(np.mean(y[pair] == 3)) if pair.any() else None
    out["lateral_any_attack_recall"] = float(np.mean(predicted[y == 2] != 0)) if np.any(y == 2) else None
    out["benign_false_attack_count"] = int(np.sum((y == 0) & (predicted != 0)))
    return out


def fit(prepared, protocol_path, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Fresh run output required")
    spec = json.loads(protocol_path.read_text(encoding="utf-8"))
    if spec != protocol():
        raise ValueError("Protocol changed")
    receipt = json.loads((prepared / "PREPARATION.json").read_text(encoding="utf-8"))
    if receipt["data_sha256"] != sha(prepared / "DATA.npz") or receipt["runner_sha256"] != sha(__file__) or receipt["context_sha256"] != sha(Path(__file__).with_name("context.py")):
        raise ValueError("Preparation binding mismatch")
    with np.load(prepared / "DATA.npz", allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    y, split = d["y"], d["split"]
    views = {"current": d["current"], "current_roles": np.column_stack([d["current"], d["roles"]]),
             "current_history": np.column_stack([d["current"], d["history"]]),
             "current_roles_history": np.column_stack([d["current"], d["roles"], d["history"]]),
             "current_roles_wrong_host_history": np.column_stack([d["current"], d["roles"], d["wrong_history"]]), "roles_only": d["roles"]}
    cal, test = np.flatnonzero(split == 1), np.flatnonzero(split == 2)
    output.mkdir(parents=True, exist_ok=True)
    binding = {"started_utc": utc(), "protocol_sha256": sha(protocol_path), "runner_sha256": sha(__file__), "context_sha256": sha(Path(__file__).with_name("context.py")),
               "prepared_sha256": sha(prepared / "DATA.npz"), "preparation_receipt_sha256": sha(prepared / "PREPARATION.json"),
               "versions": {k: importlib.metadata.version(k) for k in ["numpy", "lightgbm", "scikit-learn"]}, "cloud_compute_started": False}
    write(output / "STARTED.json", binding)
    results = []; start_clock = time.perf_counter()
    for seed in SEEDS:
        directory = output / str(seed); directory.mkdir()
        rows = []
        for k, cap in enumerate(spec["fit_caps_by_class"]):
            pool = np.flatnonzero((split == 0) & (y == k))
            ordered = sorted(pool, key=lambda i: hashlib.sha256(f"HOST_HISTORY_V1|{seed}|{d['group_sha256'][i]}".encode()).digest())
            rows.extend(ordered[:cap])
        rows = np.asarray(rows, dtype=np.int64)
        saved = {"fit_indices": rows, "cal_indices": cal, "test_indices": test, "cal_y": y[cal], "test_y": y[test]}
        arms = {}
        for name, X in views.items():
            print(f"FIT {seed} {name} n={len(rows)}", flush=True)
            model = LGBMClassifier(**PARAMS, random_state=seed, n_jobs=4, deterministic=True, force_col_wise=True, verbosity=-1)
            model.fit(X[rows], y[rows])
            pc, pt = model.predict_proba(X[cal]), model.predict_proba(X[test])
            if not np.array_equal(model.classes_, np.arange(4)):
                raise ValueError("Missing fitting class")
            threshold = f1_threshold(y[cal] == 3, pc[:, 3])
            arms[name] = {"test": metrics(y[test], pt), "exfil_f1_threshold": {"threshold": threshold, **alert_metrics(y[test], pt[:, 3] > threshold)},
                          "role_strata": {}, "by_test_capture": {}, "non_exfil_budget_thresholds": {}}
            for a in range(4):
                for b in range(4):
                    keep = (d["src_role"][test] == a) & (d["dst_role"][test] == b)
                    if keep.any():
                        arms[name]["role_strata"][f"{ROLE_NAMES[a]}->{ROLE_NAMES[b]}"] = metrics(y[test][keep], pt[keep])
            for cap in np.unique(d["capture"][test]):
                keep = d["capture"][test] == cap
                arms[name]["by_test_capture"][str(cap)] = metrics(y[test][keep], pt[keep])
            negatives = np.sort(pc[y[cal] != 3, 3])
            for budget in [.001, .005, .01, .02]:
                allowed = int(np.floor(budget * len(negatives))); cut = float(negatives[len(negatives) - allowed - 1])
                arms[name]["non_exfil_budget_thresholds"][str(budget)] = {"threshold": cut, "calibration_non_exfil_fpr": float(np.mean(negatives > cut)), **alert_metrics(y[test], pt[:, 3] > cut)}
            saved[f"{name}__cal"] = pc; saved[f"{name}__test"] = pt
            joblib.dump(model, directory / f"{name}.joblib", compress=3)
        result = {"seed": seed, "fit_counts": dict(zip(CLASSES, np.bincount(y[rows], minlength=4).tolist())), "arms": arms}
        np.savez_compressed(directory / "PREDICTIONS.npz", **saved)
        write(directory / "METRICS.json", result)
        write(directory / "COMPLETE.json", {"files": {p.name: sha(p) for p in directory.iterdir() if p.is_file()}})
        results.append(result)
    binding.update({"completed_utc": utc(), "elapsed_seconds": time.perf_counter() - start_clock, "models_fitted": len(ARMS) * len(SEEDS)})
    write(output / "SUMMARY.json", {"receipt": binding, "preparation": receipt, "seeds": results})
    write(output / "COMPLETE.json", {"summary_sha256": sha(output / "SUMMARY.json"), "started_sha256": sha(output / "STARTED.json")})
    print("COMPLETE " + str(binding["elapsed_seconds"]), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=["freeze", "prepare", "fit"])
    parser.add_argument("--inputs", type=Path); parser.add_argument("--protocol", type=Path); parser.add_argument("--prepared", type=Path); parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=4):
        if args.mode == "freeze":
            if args.protocol.exists(): raise ValueError("Existing protocol")
            write(args.protocol, protocol())
        elif args.mode == "prepare": prepare(args.inputs, args.output)
        else: fit(args.prepared, args.protocol, args.output)


if __name__ == "__main__": main()
