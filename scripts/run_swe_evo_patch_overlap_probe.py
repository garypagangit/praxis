#!/usr/bin/env python
"""PX-033 SWE-EVO released-prediction patch-overlap probe.

This is a no-cost usefulness proxy. It compares released SWE-agent model
patches with SWE-EVO gold patches to test whether file-level repo planning is
both measurable and unsolved. It is not an execution-based correctness result.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "configs/swe_evo_patch_overlap_probe_20260628.json"
USER_AGENT = "praxis-px033-swe-evo-overlap-probe/20260628"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_json(url: str, timeout: int = 90) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def hf_resolve(dataset: str, path: str) -> str:
    return f"https://huggingface.co/datasets/{dataset}/resolve/main/{urllib.parse.quote(path, safe='/')}"


def hf_tree(dataset: str, path: str) -> Any:
    encoded = urllib.parse.quote(dataset, safe="/")
    encoded_path = urllib.parse.quote(path, safe="/")
    return fetch_json(f"https://huggingface.co/api/datasets/{encoded}/tree/main/{encoded_path}?recursive=false")


def fetch_dataset_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    encoded = urllib.parse.quote(config["hf_dataset"], safe="")
    url = (
        "https://datasets-server.huggingface.co/rows?"
        f"dataset={encoded}&config={urllib.parse.quote(config['hf_config'])}"
        f"&split={urllib.parse.quote(config['hf_split'])}&offset=0&length={int(config['expected_rows'])}"
    )
    payload = fetch_json(url)
    return [row["row"] for row in payload["rows"]]


def list_prediction_models(config: dict[str, Any]) -> list[str]:
    rows = hf_tree(config["hf_dataset"], config["prediction_root"])
    return sorted(item["path"].split("/")[-1] for item in rows if item.get("type") == "directory")


def fetch_preds(config: dict[str, Any], model: str) -> dict[str, Any]:
    path = f"{config['prediction_root']}/{model}/preds.json"
    return fetch_json(hf_resolve(config["hf_dataset"], path))


def parse_patch(patch: str) -> dict[str, Any]:
    files: set[str] = set()
    added: set[tuple[str, str]] = set()
    deleted: set[tuple[str, str]] = set()
    current_file = ""
    for line in patch.splitlines():
        match = re.match(r"diff --git a/(.+?) b/(.+)$", line)
        if match:
            current_file = match.group(2)
            files.add(current_file)
            continue
        if not current_file:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            text = line[1:].strip()
            if text:
                added.add((current_file, text))
        elif line.startswith("-"):
            text = line[1:].strip()
            if text:
                deleted.add((current_file, text))
    return {"files": files, "added": added, "deleted": deleted}


def f1(precision: float, recall: float) -> float:
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def jaccard(a: set[Any], b: set[Any]) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def build_attempt_rows(dataset_rows: list[dict[str, Any]], model_preds: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gold_by_id = {row["instance_id"]: row for row in dataset_rows}
    gold_parsed = {instance_id: parse_patch(row.get("patch", "")) for instance_id, row in gold_by_id.items()}
    attempts: list[dict[str, Any]] = []
    for model, preds in model_preds.items():
        for instance_id, gold in gold_by_id.items():
            pred = preds.get(instance_id)
            if not pred:
                continue
            parsed_pred = parse_patch(pred.get("model_patch", ""))
            parsed_gold = gold_parsed[instance_id]
            gold_files = parsed_gold["files"]
            pred_files = parsed_pred["files"]
            file_overlap = len(gold_files & pred_files)
            file_precision = file_overlap / len(pred_files) if pred_files else 0.0
            file_recall = file_overlap / len(gold_files) if gold_files else 0.0
            attempts.append(
                {
                    "model": model,
                    "instance_id": instance_id,
                    "repo": gold.get("repo", ""),
                    "gold_patch_files": len(gold_files),
                    "pred_patch_files": len(pred_files),
                    "file_overlap": file_overlap,
                    "file_precision": file_precision,
                    "file_recall": file_recall,
                    "file_f1": f1(file_precision, file_recall),
                    "exact_file_set": pred_files == gold_files and bool(gold_files),
                    "zero_file_overlap": file_overlap == 0,
                    "added_line_jaccard": jaccard(parsed_pred["added"], parsed_gold["added"]),
                    "deleted_line_jaccard": jaccard(parsed_pred["deleted"], parsed_gold["deleted"]),
                    "gold_fail_to_pass": len(gold.get("FAIL_TO_PASS") or []),
                    "gold_pass_to_pass": len(gold.get("PASS_TO_PASS") or []),
                    "problem_chars": len(gold.get("problem_statement", "")),
                }
            )
    return attempts


def mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows]
    return statistics.fmean(values) if values else 0.0


def summarize(config: dict[str, Any], dataset_rows: list[dict[str, Any]], models: list[str], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, list[dict[str, Any]]] = {model: [] for model in models}
    by_task: dict[str, list[dict[str, Any]]] = {row["instance_id"]: [] for row in dataset_rows}
    for row in attempts:
        by_model[row["model"]].append(row)
        by_task[row["instance_id"]].append(row)

    model_summary = []
    for model, rows in by_model.items():
        model_summary.append(
            {
                "model": model,
                "attempts": len(rows),
                "mean_file_precision": mean(rows, "file_precision"),
                "mean_file_recall": mean(rows, "file_recall"),
                "mean_file_f1": mean(rows, "file_f1"),
                "exact_file_set_rate": mean(rows, "exact_file_set"),
                "zero_file_overlap_rate": mean(rows, "zero_file_overlap"),
                "mean_added_line_jaccard": mean(rows, "added_line_jaccard"),
            }
        )
    model_summary.sort(key=lambda row: row["mean_file_f1"], reverse=True)

    task_summary = []
    for instance_id, rows in by_task.items():
        gold = next(row for row in dataset_rows if row["instance_id"] == instance_id)
        best_file_f1 = max((float(row["file_f1"]) for row in rows), default=0.0)
        task_summary.append(
            {
                "instance_id": instance_id,
                "repo": gold.get("repo", ""),
                "gold_patch_files": len(parse_patch(gold.get("patch", ""))["files"]),
                "attempts": len(rows),
                "best_file_f1": best_file_f1,
                "any_file_overlap": any(row["file_overlap"] > 0 for row in rows),
                "any_exact_file_set": any(row["exact_file_set"] for row in rows),
                "fail_to_pass": len(gold.get("FAIL_TO_PASS") or []),
                "pass_to_pass": len(gold.get("PASS_TO_PASS") or []),
                "problem_chars": len(gold.get("problem_statement", "")),
            }
        )
    task_summary.sort(key=lambda row: (row["best_file_f1"], -row["gold_patch_files"]))

    unique_tasks = len({row["instance_id"] for row in attempts})
    tasks_with_any_overlap = sum(1 for row in task_summary if row["any_file_overlap"])
    exact_file_set_rate = mean(attempts, "exact_file_set")
    mean_file_f1 = mean(attempts, "file_f1")
    best_task_f1 = [float(row["best_file_f1"]) for row in task_summary]
    patch_complexity = [float(row["gold_patch_files"]) for row in task_summary]
    publish_checks = {
        "released_predictions_available": len(models) >= int(config["min_models"]) and len(attempts) >= int(config["min_attempts"]),
        "unique_task_coverage": unique_tasks >= int(config["min_unique_tasks"]),
        "nontrivial_file_overlap_signal": mean_file_f1 >= float(config["min_mean_file_f1_for_signal"]),
        "most_tasks_have_some_overlap": tasks_with_any_overlap / max(len(task_summary), 1) >= float(config["min_tasks_with_any_overlap_ratio"]),
        "opportunity_not_saturated": exact_file_set_rate <= float(config["max_exact_file_set_rate_for_opportunity"]),
    }
    status = "PROXY GATE PASS - REAL EVAL REQUIRED" if all(publish_checks.values()) else "PROXY GATE MIXED - REAL EVAL REQUIRED"
    return {
        "generated_utc": utc_now(),
        "experiment_id": "PX-033",
        "status": status,
        "claim_boundary": "Released-prediction patch-overlap proxy only. No tests were executed and no model correctness or fix-rate claim is made.",
        "models": models,
        "attempts": len(attempts),
        "unique_tasks": unique_tasks,
        "dataset_rows": len(dataset_rows),
        "mean_file_precision": mean(attempts, "file_precision"),
        "mean_file_recall": mean(attempts, "file_recall"),
        "mean_file_f1": mean_file_f1,
        "median_file_f1": statistics.median([row["file_f1"] for row in attempts]) if attempts else 0.0,
        "exact_file_set_rate": exact_file_set_rate,
        "zero_file_overlap_rate": mean(attempts, "zero_file_overlap"),
        "mean_added_line_jaccard": mean(attempts, "added_line_jaccard"),
        "mean_deleted_line_jaccard": mean(attempts, "deleted_line_jaccard"),
        "tasks_with_any_overlap": tasks_with_any_overlap,
        "tasks_with_any_overlap_ratio": tasks_with_any_overlap / max(len(task_summary), 1),
        "tasks_with_any_exact_file_set": sum(1 for row in task_summary if row["any_exact_file_set"]),
        "best_task_file_f1_mean": statistics.fmean(best_task_f1) if best_task_f1 else 0.0,
        "patch_complexity_vs_best_file_f1_pearson": pearson(patch_complexity, best_task_f1),
        "model_summary": model_summary,
        "hardest_tasks": task_summary[:10],
        "publish_checks": publish_checks,
        "next_gate": "Execute or obtain true SWE-EVO evaluation results for one small model/instance slice, then test whether repo-state summaries improve fix-rate prediction beyond metadata-only baselines.",
    }


def write_attempt_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model",
        "instance_id",
        "repo",
        "gold_patch_files",
        "pred_patch_files",
        "file_overlap",
        "file_precision",
        "file_recall",
        "file_f1",
        "exact_file_set",
        "zero_file_overlap",
        "added_line_jaccard",
        "deleted_line_jaccard",
        "gold_fail_to_pass",
        "gold_pass_to_pass",
        "problem_chars",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_report(report_path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PX-033 SWE-EVO Patch-Overlap Probe",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Released SWE-agent models | `{len(summary['models'])}` |",
        f"| Prediction attempts parsed | `{summary['attempts']}` |",
        f"| Unique tasks covered | `{summary['unique_tasks']}` / `{summary['dataset_rows']}` |",
        f"| Mean file precision | `{summary['mean_file_precision']:.4f}` |",
        f"| Mean file recall | `{summary['mean_file_recall']:.4f}` |",
        f"| Mean file F1 | `{summary['mean_file_f1']:.4f}` |",
        f"| Median file F1 | `{summary['median_file_f1']:.4f}` |",
        f"| Exact file-set rate | `{summary['exact_file_set_rate']:.4f}` |",
        f"| Zero file-overlap rate | `{summary['zero_file_overlap_rate']:.4f}` |",
        f"| Tasks with any file overlap | `{summary['tasks_with_any_overlap']}` / `{summary['dataset_rows']}` |",
        f"| Tasks with any exact file set | `{summary['tasks_with_any_exact_file_set']}` / `{summary['dataset_rows']}` |",
        f"| Best-task file F1 mean | `{summary['best_task_file_f1_mean']:.4f}` |",
    ]
    corr = summary["patch_complexity_vs_best_file_f1_pearson"]
    lines.append(f"| Patch complexity vs best file F1 Pearson | `{corr:.4f}` |" if corr is not None else "| Patch complexity vs best file F1 Pearson | `n/a` |")
    lines.extend(["", "## Publish Checks", "", "| Check | Pass |", "|---|---:|"])
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Model Summary", "", "| Model | Attempts | File P | File R | File F1 | Exact set | Zero overlap | Added-line J |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for row in summary["model_summary"]:
        lines.append(
            f"| `{row['model']}` | `{row['attempts']}` | `{row['mean_file_precision']:.4f}` | "
            f"`{row['mean_file_recall']:.4f}` | `{row['mean_file_f1']:.4f}` | "
            f"`{row['exact_file_set_rate']:.4f}` | `{row['zero_file_overlap_rate']:.4f}` | "
            f"`{row['mean_added_line_jaccard']:.4f}` |"
        )
    lines.extend(["", "## Hardest Tasks By Best File F1", "", "| Instance | Repo | Gold files | Attempts | Best file F1 | Any overlap | Any exact set |", "|---|---|---:|---:|---:|---:|---:|"])
    for row in summary["hardest_tasks"]:
        lines.append(
            f"| `{row['instance_id']}` | `{row['repo']}` | `{row['gold_patch_files']}` | `{row['attempts']}` | "
            f"`{row['best_file_f1']:.4f}` | `{row['any_file_overlap']}` | `{row['any_exact_file_set']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The released prediction patches provide a usable no-cost proxy for repo-state planning: enough models and attempts are available, most tasks have at least some file-level overlap, and exact file-set matches are rare. That combination is useful because the signal is not empty, but the file-planning problem is clearly not saturated.",
            "",
            "This still does not prove the PX-033 world-model idea works. It proves that the next paid or containerized evaluation should be small and targeted: one true SWE-EVO evaluation slice plus a metadata-only baseline and a repo-state-summary baseline.",
            "",
            "## Next Gate",
            "",
            summary["next_gate"],
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = read_json(Path(args.config))
    dataset_rows = fetch_dataset_rows(config)
    models = list_prediction_models(config)
    model_preds = {}
    for model in models:
        try:
            model_preds[model] = fetch_preds(config, model)
        except Exception:
            continue
    attempts = build_attempt_rows(dataset_rows, model_preds)
    summary = summarize(config, dataset_rows, sorted(model_preds.keys()), attempts)

    output_dir = Path(config["output_dir"])
    write_json(output_dir / "summary.json", summary)
    write_attempt_csv(output_dir / "attempt_overlap.csv", attempts)
    render_report(Path(config["report_path"]), summary)
    print(json.dumps({"status": summary["status"], "attempts": summary["attempts"], "report_path": config["report_path"]}, indent=2))


if __name__ == "__main__":
    main()
