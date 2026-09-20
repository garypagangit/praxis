"""Publish only aggregate receipts/reports from a completed private pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import write_json


def percent(value):
    return "undefined" if value is None else f"{100*value:.3f}%"


def number(value):
    return "undefined" if value is None else f"{value:.6f}"


def package(private, destination, capture_qualification=None):
    result = json.loads((private / "results.json").read_text())
    qualification = json.loads((private / "qualification.json").read_text())
    if not result.get("completed_at"):
        raise ValueError("Only a completed pilot can be packaged")
    destination.mkdir(parents=True, exist_ok=True)
    # Explicit whitelist; never recurse/copy private predictions, models or data.
    for name in ["results.json", "qualification.json", "frozen_protocol.json", "pre_fit_code_receipt.json"]:
        write_json(destination / name, json.loads((private / name).read_text()))
    if capture_qualification:
        write_json(destination / "capture_qualification.json", json.loads(capture_qualification.read_text()))
    test = result["support"]["test"]
    lines = ["# First model comparison: AIT source-log development pilot", "",
             "**Completed development baseline; no new-method improvement or production APT claim.**", "",
             f"The same 128-feature view was used for every binary model. Fit: {result['support']['fit']['rows']:,} lines across four runs; calibration: one separate run; test: {test['rows']:,} lines across two February runs. Thresholds were selected before test scoring for at most 1% observed calibration event false positives.", "",
             "## Binary detection on the two held-out runs", "",
             "| Model | F1 | ROC-AUC | Average precision | Test false-positive rate | Fit seconds |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, entry in result["models"].items():
        m = entry["test_calibrated"]
        lines.append(f"| {name.replace('_', ' ')} | {percent(m['f1'])} | {number(m['roc_auc'])} | {number(m['average_precision'])} | {percent(m['false_positive_rate'])} | {entry['fit_seconds']:.2f} |")
    lines.extend(["", "ROC-AUC and average precision use continuous scores. Constant predictions have undefined precision/MCC where appropriate; the no-skill reference emits no alarms at its calibrated threshold. Fixed-0.5 results and confusion counts are retained in results.json.", "",
                  "**Interpretation:** evaluate actual test false positives alongside F1. A model that misses the calibration budget after transfer has not met a 1% test operating requirement, regardless of its near-perfect F1.", "",
                  "## Detection by attack step", "",
                  "Each cell is correctly detected malicious source lines / labeled source lines at the frozen binary threshold. This table measures detection within a step, not prediction of its name.", "",
                  "| Author-labeled step | Logistic regression | Random forest | Gradient boosting |",
                  "|---|---:|---:|---:|"])
    for stage in ["service_scan", "dirb", "wpscan", "webshell_upload", "webshell_cmd", "escalate"]:
        values = []
        for name in ["logistic_regression", "random_forest", "hist_gradient_boosting"]:
            step = result["models"][name]["attack_step_detection"]["steps"].get(stage)
            values.append("unsupported" if not step else f"{step['detected_rows']:,}/{step['attack_step_rows']:,}")
        lines.append("| " + stage + " | " + " | ".join(values) + " |")
    stage = result["stage_identification"]
    lines.extend(["", "## Separate stage-name classifier", "",
                  "A fixed-threshold, one-vs-rest logistic model predicts the overlapping source-defined step labels. Per-label precision, recall, F1, ROC-AUC and support are in `results.json > stage_identification`. These labels include hierarchy and are not independent kill-chain stages.", ""])
    if "metrics" in stage:
        lines.extend(["| Source step being named | Positive test lines | Precision | Recall | F1 |",
                      "|---|---:|---:|---:|---:|"])
        for name in ["service_scan", "dirb", "wpscan", "webshell_upload", "webshell_cmd", "escalate"]:
            m = stage["metrics"]["per_stage"].get(name)
            if m:
                lines.append(f"| {name} | {m['n_attack']:,} | {percent(m['precision'])} | {percent(m['recall'])} | {percent(m['f1'])} |")
        lines.append("")
    lines.extend(["## Limits that govern the result", "",
                  f"- Test prevalence is {percent(test['attack']/test['rows'])} attack-labeled. This selected annotated-source view is dominated by repeated directory scans, not normal enterprise traffic.",
                  f"- {qualification['test_feature_vectors_seen_in_fit']:,}/{test['rows']:,} test feature vectors appear in fit data ({percent(qualification['test_feature_vectors_seen_in_fit']/test['rows'])}). Repeated legitimate logs, attack templates and hash collisions can contribute; this is not itself proof of raw-row leakage.",
                  "- Authors supply rule-based source labels. They are not an independent human audit, and missing rule manifestations are possible.",
                  "- The source slice covers scanning, webshell activity and escalation. It contains no labeled exfiltration, collection or lateral movement; those stage scores are unsupported.",
                  "- Only two test executions, shared scenario templates and one selected host type. No unseen-family, actor-attribution or population confidence claim.",
                  "- Before-impact detection, actual end-to-end alert latency and benign-host-hour rates remain unmeasured. Timestamp/impact/coverage qualification must precede those experiments.",
                  "- The 1% operating target is empirical calibration. It is not certified risk control under distribution shift.", "",
                  "## Research decision", "",
                  "Use the pilot to qualify the environment and reveal tradeoffs. Pooled F1 is already near its ceiling, so an absolute multi-percentage-point F1 gain would be mathematically impossible here. The useful next question concerns rare harmful steps, false-alert transfer, causal context and incomplete telemetry, followed by confirmation on an independent source. Model comparison alone establishes no methodological novelty.", "",
                  "The already inspected extra AIT background files are a separately qualified coverage expansion; any subsequent run must name its changed denominator and remain development evidence. Do not revise this pilot's frozen results.", ""])
    (destination / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--capture-qualification", type=Path)
    args = parser.parse_args()
    package(args.private, args.destination, args.capture_qualification)
