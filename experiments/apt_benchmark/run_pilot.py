"""Run the frozen, CPU-only AIT source-log development pilot."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import time
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from .ait_adapter import load_ait
from .contracts import write_json, sha256_file
from .metrics import binary_metrics, stage_metrics
from .models import MODEL_SPECS, build_binary_model, score_binary, calibration_threshold, resolve_threshold


def step_detection(rows, y, scores, threshold):
    """Which labeled behaviors does the binary detector catch? Not a stage classifier."""
    output = {}
    for stage in sorted({s for row in rows for s in row["stages"]}):
        belongs = np.array([stage in row["stages"] for row in rows])
        select = belongs | (y == 0)
        output[stage] = {"attack_step_rows": int(belongs.sum()),
                         "detected_rows": int((belongs & (scores > threshold)).sum()),
                         "stage_vs_normal": binary_metrics(y[select], scores[select], threshold)}
    return {"interpretation": "Binary detection of each author-labeled attack step versus all normal rows. Other attack steps excluded from each diagnostic; these overlapping metrics are not stage-name identification or additive.",
            "steps": output}


def run(data: Path, output: Path, protocol_path: Path):
    repo = Path(__file__).resolve().parents[2]
    if output.resolve() == repo or repo in output.resolve().parents:
        raise ValueError("Private models and per-record predictions must be outside the Git repository")
    if (output / "results.json").exists():
        raise ValueError("Refusing to overwrite a completed run; choose a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(protocol_path.read_text())
    acquisition = json.loads((data / "ACQUISITION.json").read_text(encoding="utf-8"))
    acquired_runs = {entry["scenario"]: entry for entry in acquisition["scenarios"]}
    required_runs = {name for names in protocol["splits"].values() for name in names}
    if set(acquired_runs) != required_runs or acquisition["record"] != 19483937:
        raise ValueError("Acquisition receipt does not match frozen dataset/run contract")
    for scenario, receipt in acquired_runs.items():
        for member in receipt["members"]:
            path = data / scenario / member["local_relative_path"]
            if not member["crc32_verified"] or sha256_file(path) != member["sha256"]:
                raise ValueError("Source changed after acquisition verification")
    write_json(output / "frozen_protocol.json", protocol)
    code_hashes = {p.name: sha256_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    code_receipt = {"python_sources_sha256": code_hashes,
                    "protocol_sha256": sha256_file(protocol_path),
                    "git_base_commit": subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                    "frozen_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "pre_fit_code_receipt.json", code_receipt)
    started = time.monotonic()
    X, y, rows, qualification = load_ait(data, protocol)
    preparation_seconds = time.monotonic() - started
    masks = {role: np.array([row["split"] == role for row in rows]) for role in protocol["splits"]}
    support = {}
    for role, mask in masks.items():
        if len(np.unique(y[mask])) != 2:
            raise ValueError(f"Unqualified split {role}: both classes required")
        support[role] = {"rows": int(mask.sum()), "attack": int(y[mask].sum()),
                         "benign": int((y[mask] == 0).sum()),
                         "runs": protocol["splits"][role]}
    qualification["split_support"] = support
    # A repeated observation is not automatically a leak: measure and disclose
    # the lexical shortcut opportunity without deleting legitimate repetition.
    train_fingerprints = {X[i].tobytes() for i in np.flatnonzero(masks["fit"])}
    qualification["test_feature_vectors_seen_in_fit"] = sum(
        X[i].tobytes() in train_fingerprints for i in np.flatnonzero(masks["test"]))
    qualification["test_feature_overlap_interpretation"] = "Exact representation overlap, including legitimate recurring normal logs and hash collisions; descriptive shortcut diagnostic, not proof of duplicate raw attack episodes."
    write_json(output / "qualification.json", qualification)
    print(json.dumps({"qualification": support, "feature_dimensions": X.shape[1]}), flush=True)
    report = {
        "status": "DEVELOPMENT_PILOT", "started_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256_file(protocol_path), "source_file_count": len(qualification["files"]),
        "acquisition_receipt_sha256": sha256_file(data / "ACQUISITION.json"),
        "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                        "numpy": np.__version__, "device": "CPU", "thread_limit": 2},
        "preparation_seconds": preparation_seconds, "support": support, "models": {},
        "not_claimed": ["Novel method", "APT actor attribution", "Independent campaign generalization",
                        "Operational false alarms per host-hour", "Detection before verified impact",
                        "A universally best model", "A positive praxis contribution"],
    }
    test_rows = [row for row in rows if row["split"] == "test"]
    test_groups = [row["scenario"] for row in test_rows]
    for name in protocol["models"]:
        model = build_binary_model(name, protocol["seed"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            start = time.monotonic()
            model.fit(X[masks["fit"]], y[masks["fit"]])
            fit_seconds = time.monotonic() - start
        start = time.monotonic()
        scores = {role: score_binary(model, X[mask]) for role, mask in masks.items() if role != "fit"}
        batch_score_seconds = time.monotonic() - start
        calibration = calibration_threshold(y[masks["calibration"]], scores["calibration"],
                                           protocol["calibration"]["target_event_false_positive_rate"])
        threshold = resolve_threshold(calibration)
        test_y = y[masks["test"]]
        result = {"specification": MODEL_SPECS[name], "fit_seconds": fit_seconds,
                  "batch_scoring_seconds_dev_cal_test": batch_score_seconds,
                  "warnings": [str(w.message) for w in caught],
                  "calibration": calibration,
                  "development_fixed_0_5": binary_metrics(y[masks["development"]], scores["development"]),
                  "test_fixed_0_5": binary_metrics(test_y, scores["test"], groups=test_groups),
                  "test_calibrated": binary_metrics(test_y, scores["test"], threshold, groups=test_groups),
                  "attack_step_detection": step_detection(test_rows, test_y, scores["test"], threshold)}
        report["models"][name] = result
        joblib.dump(model, output / (name + ".joblib"))
        np.savez_compressed(output / (name + "_private_predictions.npz"),
                            test_y=test_y, test_scores=scores["test"],
                            record_ids=np.array([r["id"] for r in test_rows]),
                            calibration_y=y[masks["calibration"]],
                            calibration_scores=scores["calibration"],
                            calibration_record_ids=np.array([r["id"] for r in rows if r["split"] == "calibration"]),
                            development_y=y[masks["development"]],
                            development_scores=scores["development"])
        write_json(output / "results.partial.json", report)
        print(json.dumps({"model": name, "fit_seconds": fit_seconds,
                          "test_calibrated": {k: result["test_calibrated"][k]
                          for k in ["f1", "roc_auc", "average_precision", "recall", "false_positive_rate"]}}), flush=True)

    # Secondary, explicitly different target: predict source step names using a
    # multilabel linear classifier, including overlap rather than inventing order.
    fit_rows = [r for r in rows if r["split"] == "fit"]
    names = sorted({s for r in fit_rows for s in r["stages"]})
    stage_y = np.array([[int(s in row["stages"]) for s in names] for row in rows])
    eligible = np.array([len(np.unique(stage_y[masks["fit"], i])) == 2 for i in range(len(names))])
    names = [name for name, use in zip(names, eligible) if use]
    if not names:
        report["stage_identification"] = {"status": "UNSUPPORTED_NO_TRAINABLE_STAGES"}
        report["elapsed_seconds"] = time.monotonic() - started
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "results.json", report)
        return
    stage_y = stage_y[:, eligible]
    stage_model = make_pipeline(StandardScaler(), OneVsRestClassifier(
        LogisticRegression(class_weight="balanced", max_iter=1000, random_state=protocol["seed"]), n_jobs=1))
    start = time.monotonic()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        stage_model.fit(X[masks["fit"]], stage_y[masks["fit"]])
    stage_score = stage_model.predict_proba(X[masks["test"]])
    if len(names) == 1:
        stage_score = stage_score[:, [-1]]
    report["stage_identification"] = {
        "model": "One-vs-rest logistic regression", "threshold": 0.5,
        "source": "Author exact line-level step annotations; hierarchical/overlapping, not a universal kill-chain order",
        "seconds_fit_and_test_score": time.monotonic() - start,
        "warnings": [str(w.message) for w in caught],
        "test_stages_not_seen_in_fit": sorted({s for r in test_rows for s in r["stages"]} - set(names)),
        "metrics": stage_metrics(stage_y[masks["test"]], stage_score, stage_names=names,
                                 stage_source="AIT-LDS v2.1 exact original-line labels", mode="multilabel"),
        "interpretation": "Secondary fixed-threshold source-step identification, not part of the binary leaderboard. All test rows retained as negatives for absent known steps; no per-stage threshold tuning.",
    }
    joblib.dump(stage_model, output / "stage_logistic_regression.joblib")
    np.savez_compressed(output / "stage_private_predictions.npz",
                        test_y=stage_y[masks["test"]], test_scores=stage_score,
                        stage_names=np.array(names), record_ids=np.array([r["id"] for r in test_rows]))
    report["elapsed_seconds"] = time.monotonic() - started
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "results.json", report)
    print(json.dumps({"status": "COMPLETE_DEVELOPMENT_PILOT", "output": str(output),
                      "seconds": report["elapsed_seconds"], "stage_targets": len(names)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.data, args.output, args.protocol)
