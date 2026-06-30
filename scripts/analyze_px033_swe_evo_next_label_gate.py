#!/usr/bin/env python3
"""PX-033 SWE-EVO cross-model next-label gate."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OVERLAP_CSV = ROOT / "runs" / "swe-evo-patch-overlap-probe-20260628" / "attempt_overlap.csv"
LABEL_CSV = ROOT / "runs" / "swe-evo-failure-predictor-probe-20260630" / "swe_evo_failure_taxonomy_and_predictor_probe.csv"
OUT_DIR = ROOT / "runs" / "px033-swe-evo-next-label-gate-20260630"
REPORT = ROOT / "reports" / "swe_evo_repo_state_world_model" / "SWE_EVO_NEXT_LABEL_CROSS_MODEL_GATE_20260630.md"

METADATA_BASELINE_ACC = 0.8
METADATA_BASELINE_F1 = 0.8
PRIMARY_QUEUE_MODEL = "gpt-4o-2024-11-20"
CONFIRM_QUEUE_MODEL = "deepseek-r1-0528"
PROXY_THRESHOLD = 0.05


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def binary_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": (tp + tn) / max(len(y_true), 1),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def threshold_screen(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    y_true = [int(row["glm_label"]) for row in rows]
    y_pred = [1 if float(row["file_f1"]) >= threshold else 0 for row in rows]
    return {"threshold": threshold, "predicted_passes": sum(y_pred), **binary_metrics(y_true, y_pred)}


def best_threshold(rows: list[dict[str, Any]]) -> dict[str, Any]:
    thresholds = sorted({0.0, PROXY_THRESHOLD, 0.1, 0.25, 0.33, 0.5, 0.75, 1.0} | {float(row["file_f1"]) for row in rows})
    screens = [threshold_screen(rows, threshold) for threshold in thresholds]
    return max(screens, key=lambda row: (row["accuracy"], row["f1"], row["recall"], -row["threshold"]))


def load_valid_labels() -> dict[str, dict[str, Any]]:
    labels = {}
    for row in read_csv(LABEL_CSV):
        if row["valid_model_label"] == "True":
            labels[row["instance_id"]] = {
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "glm_status": row["status"],
                "glm_label": 1 if row["binary_label"] == "PASS" else 0,
                "glm_binary_label": row["binary_label"],
                "selected_test_count": int(row["selected_test_count"]),
                "first_eval_signal": row["first_eval_signal"],
            }
    return labels


def joined_attempts(labels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(OVERLAP_CSV):
        label = labels.get(row["instance_id"])
        if not label:
            continue
        rows.append(
            {
                **label,
                "model": row["model"],
                "file_f1": float(row["file_f1"]),
                "file_precision": float(row["file_precision"]),
                "file_recall": float(row["file_recall"]),
                "file_overlap": int(row["file_overlap"]),
                "pred_patch_files": int(row["pred_patch_files"]),
                "gold_patch_files": int(row["gold_patch_files"]),
                "zero_file_overlap": row["zero_file_overlap"] == "True",
            }
        )
    return rows


def proxy_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_model.setdefault(row["model"], []).append(row)

    scores = []
    for model, model_rows in sorted(by_model.items()):
        fixed = threshold_screen(model_rows, PROXY_THRESHOLD)
        best = best_threshold(model_rows)
        scores.append(
            {
                "model": model,
                "valid_rows": len(model_rows),
                "mean_file_f1_on_valid_tasks": sum(float(row["file_f1"]) for row in model_rows) / len(model_rows),
                "zero_overlap_rows": sum(1 for row in model_rows if row["zero_file_overlap"]),
                "threshold_0p05_accuracy": fixed["accuracy"],
                "threshold_0p05_f1": fixed["f1"],
                "threshold_0p05_predicted_passes": fixed["predicted_passes"],
                "best_threshold": best["threshold"],
                "best_accuracy": best["accuracy"],
                "best_precision": best["precision"],
                "best_recall": best["recall"],
                "best_f1": best["f1"],
                "posthoc_beats_metadata_baseline": best["accuracy"] > METADATA_BASELINE_ACC and best["f1"] > METADATA_BASELINE_F1,
            }
        )
    return sorted(scores, key=lambda row: (row["best_accuracy"], row["best_f1"], row["threshold_0p05_accuracy"]), reverse=True)


def metadata_baseline(labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ordered = [labels[key] for key in sorted(labels)]
    y_true = [int(row["glm_label"]) for row in ordered]
    y_pred = [1 if row["repo"] == "psf/requests" else 0 for row in ordered]
    return {"rule": "metadata_repo_is_requests", **binary_metrics(y_true, y_pred)}


def next_label_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {(row["model"], row["instance_id"]): row for row in rows}
    labels = sorted({row["instance_id"]: row for row in rows}.values(), key=lambda row: (row["repo"], row["instance_id"]))
    queue = []
    priority = 1
    for model, lane in [(PRIMARY_QUEUE_MODEL, "primary"), (CONFIRM_QUEUE_MODEL, "confirmation")]:
        for label_row in labels:
            row = by_key.get((model, label_row["instance_id"]))
            if row is None:
                continue
            proxy_expected = "PASS" if row["file_f1"] >= PROXY_THRESHOLD else "FAIL"
            queue.append(
                {
                    "priority": priority,
                    "lane": lane,
                    "model": model,
                    "instance_id": row["instance_id"],
                    "repo": row["repo"],
                    "glm_label": row["glm_binary_label"],
                    "proxy_expected_label": proxy_expected,
                    "file_f1": row["file_f1"],
                    "file_overlap": row["file_overlap"],
                    "pred_patch_files": row["pred_patch_files"],
                    "selected_test_count": row["selected_test_count"],
                    "purpose": "cross-model positive replication" if proxy_expected == "PASS" else "cross-model negative control",
                }
            )
            priority += 1
    return queue


def execution_availability() -> dict[str, Any]:
    docker_path = shutil.which("docker")
    aws_path = shutil.which("aws")
    aws_identity = None
    aws_error = None
    if aws_path:
        try:
            proc = subprocess.run(
                [aws_path, "sts", "get-caller-identity", "--region", "us-east-1", "--output", "json"],
                text=True,
                capture_output=True,
                timeout=30,
            )
            if proc.returncode == 0:
                aws_identity = json.loads(proc.stdout)
            else:
                aws_error = (proc.stderr or proc.stdout).strip()
        except Exception as exc:  # pragma: no cover - diagnostic capture only
            aws_error = str(exc)
    return {
        "docker_available": docker_path is not None,
        "docker_path": docker_path,
        "aws_cli_available": aws_path is not None,
        "aws_path": aws_path,
        "aws_credentials_available": aws_identity is not None,
        "aws_identity": aws_identity,
        "aws_error": aws_error,
    }


def fmt(value: Any, digits: int = 4) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_report(analysis: dict[str, Any], scores_csv: Path, queue_csv: Path, json_path: Path) -> None:
    scores = analysis["cross_model_proxy_scores"]
    top_scores = scores[:6]
    queue = analysis["next_label_queue"]
    env = analysis["execution_availability"]
    lines = [
        "# PX-033 SWE-EVO Next-Label Cross-Model Gate",
        "",
        f"Generated: {analysis['generated_utc']}",
        "",
        "Status: **NEXT-LABEL QUEUE READY - CROSS-MODEL EXECUTION NOT RUN IN THIS SHELL**",
        "",
        "## Claim Boundary",
        "",
        "This gate does not add executable SWE-EVO labels. It uses the existing 5 valid glm-4p5 execution labels plus released cross-model patch-overlap proxies to decide whether another paid/containerized cross-model slice is justified.",
        "",
        "Patch overlap is not correctness. Any apparent threshold result below is a screening signal only until the queued model patches are executed in the benchmark images.",
        "",
        "## Baseline",
        "",
        f"- Valid executable glm labels: `{analysis['valid_label_count']}` (`{analysis['valid_pass_count']}` PASS / `{analysis['valid_fail_count']}` FAIL).",
        f"- Metadata-only baseline `repo == psf/requests`: accuracy `{fmt(analysis['metadata_baseline']['accuracy'])}`, F1 `{fmt(analysis['metadata_baseline']['f1'])}`.",
        "",
        "## Cross-Model Proxy Screen",
        "",
        "| Model | Best threshold | Best acc | Best F1 | Acc @ F1>=0.05 | Mean file F1 | Note |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in top_scores:
        note = "post-hoc beats metadata" if row["posthoc_beats_metadata_baseline"] else "does not beat metadata"
        lines.append(
            f"| `{row['model']}` | `{fmt(row['best_threshold'])}` | `{fmt(row['best_accuracy'])}` | `{fmt(row['best_f1'])}` | `{fmt(row['threshold_0p05_accuracy'])}` | `{fmt(row['mean_file_f1_on_valid_tasks'])}` | {note} |"
        )

    lines.extend(
        [
            "",
            "Two released-prediction models (`gpt-4o-2024-11-20` and `deepseek-r1-0528`) separate the five glm labels perfectly at a tiny file-overlap threshold, but this is post-hoc on five examples. It justifies a small cross-model execution queue; it does not prove a repo-state world model.",
            "",
            "## Next Executable Label Queue",
            "",
            "| Priority | Lane | Model | Instance | Proxy expected | glm label | File F1 | Purpose |",
            "|---:|---|---|---|---|---|---:|---|",
        ]
    )
    for row in queue:
        lines.append(
            f"| {row['priority']} | {row['lane']} | `{row['model']}` | `{row['instance_id']}` | `{row['proxy_expected_label']}` | `{row['glm_label']}` | `{fmt(row['file_f1'])}` | {row['purpose']} |"
        )

    lines.extend(
        [
            "",
            "## Execution Availability",
            "",
            f"- Local Docker available: `{env['docker_available']}`.",
            f"- AWS credentials available in this shell: `{env['aws_credentials_available']}`.",
            f"- AWS diagnostic: `{env['aws_error'] or 'ok'}`.",
            "",
            "No cloud or Docker execution was started from this shell because the local Docker CLI is unavailable and AWS credentials are not loaded.",
            "",
            "## Decision",
            "",
            "Keep PX-033 as an active execution-and-prediction lane only. Run the 5-row primary `gpt-4o-2024-11-20` queue when AWS SSO is connected; add the 5-row DeepSeek confirmation queue only if the primary queue beats the metadata baseline. Do not start RWML/world-model training unless cross-model executable labels beat accuracy/F1 `0.8000` on a larger valid slice.",
            "",
            "## Artifacts",
            "",
            f"- Raw JSON: `{json_path.relative_to(ROOT).as_posix()}`",
            f"- Cross-model proxy scores: `{scores_csv.relative_to(ROOT).as_posix()}`",
            f"- Next-label queue: `{queue_csv.relative_to(ROOT).as_posix()}`",
            "- Prior executable labels: `runs/swe-evo-failure-predictor-probe-20260630/`",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    labels = load_valid_labels()
    attempts = joined_attempts(labels)
    scores = proxy_scores(attempts)
    queue = next_label_queue(attempts)
    metadata = metadata_baseline(labels)
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NEXT-LABEL QUEUE READY - CROSS-MODEL EXECUTION NOT RUN IN THIS SHELL",
        "valid_label_count": len(labels),
        "valid_pass_count": sum(1 for row in labels.values() if row["glm_label"] == 1),
        "valid_fail_count": sum(1 for row in labels.values() if row["glm_label"] == 0),
        "metadata_baseline": metadata,
        "proxy_threshold": PROXY_THRESHOLD,
        "cross_model_proxy_scores": scores,
        "next_label_queue": queue,
        "execution_availability": execution_availability(),
        "decision": "Run primary cross-model executable queue before any RWML/world-model training.",
    }
    json_path = OUT_DIR / "px033_swe_evo_next_label_gate.json"
    scores_csv = OUT_DIR / "cross_model_proxy_scores.csv"
    queue_csv = OUT_DIR / "next_label_queue.csv"
    write_csv(
        scores_csv,
        scores,
        [
            "model",
            "valid_rows",
            "mean_file_f1_on_valid_tasks",
            "zero_overlap_rows",
            "threshold_0p05_accuracy",
            "threshold_0p05_f1",
            "threshold_0p05_predicted_passes",
            "best_threshold",
            "best_accuracy",
            "best_precision",
            "best_recall",
            "best_f1",
            "posthoc_beats_metadata_baseline",
        ],
    )
    write_csv(
        queue_csv,
        queue,
        [
            "priority",
            "lane",
            "model",
            "instance_id",
            "repo",
            "glm_label",
            "proxy_expected_label",
            "file_f1",
            "file_overlap",
            "pred_patch_files",
            "selected_test_count",
            "purpose",
        ],
    )
    json_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    write_report(analysis, scores_csv, queue_csv, json_path)
    print(json.dumps({"status": analysis["status"], "queue_rows": len(queue)}, indent=2))


if __name__ == "__main__":
    main()
