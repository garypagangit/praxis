#!/usr/bin/env python3
"""Analyze the PX-033 SWE-EVO true-eval sweep failure modes.

This is a deliberately small-n analysis over the six executable tasks already
run in the SWE-EVO F2P sweep. It does not train a predictor; it records whether
simple metadata and patch/repo-state proxies are informative enough to justify
the next experimental gate.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SWEEP_DIR = ROOT / "runs" / "swe-evo-true-eval-sweep-20260629-safe-f2p"
OUT_DIR = ROOT / "runs" / "swe-evo-failure-predictor-probe-20260630"
REPORT = (
    ROOT
    / "reports"
    / "swe_evo_repo_state_world_model"
    / "SWE_EVO_FAILURE_TAXONOMY_AND_PREDICTOR_PROBE_20260630.md"
)


VALID_STATUSES = {"PASS", "MODEL_FAIL"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path, base: Path) -> str:
    return Path(os.path.relpath(path.resolve(), base.resolve())).as_posix()


def safe_float(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.4f}"


def binary_metrics(rows: list[dict[str, Any]], predictor: Callable[[dict[str, Any]], str]) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    predictions: list[str] = []
    for row in rows:
        actual = row["binary_label"]
        pred = predictor(row)
        predictions.append(pred)
        if pred == "PASS" and actual == "PASS":
            tp += 1
        elif pred == "PASS" and actual == "FAIL":
            fp += 1
        elif pred == "FAIL" and actual == "FAIL":
            tn += 1
        elif pred == "FAIL" and actual == "PASS":
            fn += 1
        else:
            raise ValueError(f"unexpected prediction {pred!r} or label {actual!r}")

    total = len(rows)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "n": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": (tp + tn) / total if total else None,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "predictions": predictions,
    }


def classify(row: dict[str, Any]) -> tuple[str, str]:
    status = row["status"]
    base_rc = row.get("base_returncode")
    model_rc = row.get("model_returncode")
    gold_rc = row.get("gold_returncode")

    if status == "PASS":
        return "PASS", "Model and gold patches both pass selected fail-to-pass tests."
    if status == "MODEL_FAIL" and base_rc != 0 and model_rc != 0 and gold_rc == 0:
        return (
            "MODEL_FIX_INCOMPLETE",
            "Model patch applies and executes, but selected fail-to-pass tests still fail while gold passes.",
        )
    if status == "GOLD_FAIL" or gold_rc != 0:
        return (
            "HARNESS_OR_TEST_NODE_INVALID",
            "Gold patch did not pass the selected test node, so this task is not a valid model-patch label.",
        )
    if not row.get("model_patch_applied", False) or not row.get("gold_patch_applied", False):
        return "PATCH_APPLY_OR_INFRA_FAIL", "Patch application failed before a semantic model result could be read."
    return "UNCLASSIFIED", "The return-code pattern did not match a known taxonomy bucket."


def first_relevant_eval_line(path: Path) -> str:
    if not path.exists():
        return "No eval log found."
    data = load_json(path)
    stdout = data.get("stdout", "") or ""
    stderr = data.get("stderr", "") or ""
    lines = [line.strip() for line in stdout.splitlines() + stderr.splitlines() if line.strip()]
    failed = [line for line in lines if line.startswith("FAILED ")]
    if failed:
        return failed[0]
    assertion = [line for line in lines if "AssertionError" in line or line.startswith("E ")]
    if assertion:
        return assertion[0]
    short_summary = [line for line in lines if "failed" in line.lower() or "error" in line.lower()]
    if short_summary:
        return short_summary[-1]
    return lines[-1] if lines else "Eval log had no stdout/stderr detail."


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def build_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in summary["results"]:
        instance_id = raw["instance_id"]
        per_instance = load_json(SWEEP_DIR / "per_instance" / f"{instance_id}.json")
        merged = {**raw, **per_instance}
        taxonomy, interpretation = classify(merged)

        model_files = set(merged.get("model_patch_files") or [])
        gold_files = set(merged.get("gold_patch_files") or [])
        test_files = set(merged.get("test_patch_files") or [])
        valid_model_label = (
            merged["status"] in VALID_STATUSES
            and merged.get("base_returncode") != 0
            and merged.get("gold_returncode") == 0
        )

        eval_name = "model_eval.json" if merged["status"] != "GOLD_FAIL" else "gold_eval.json"
        eval_path = SWEEP_DIR / "evals" / instance_id / eval_name

        rows.append(
            {
                "instance_id": instance_id,
                "repo": merged["repo"],
                "status": merged["status"],
                "valid_model_label": valid_model_label,
                "binary_label": "PASS" if merged["status"] == "PASS" else "FAIL",
                "taxonomy": taxonomy,
                "taxonomy_interpretation": interpretation,
                "base_returncode": merged.get("base_returncode"),
                "model_returncode": merged.get("model_returncode"),
                "gold_returncode": merged.get("gold_returncode"),
                "selected_test_count": merged.get("selected_test_count", 0),
                "fail_to_pass_count": merged.get("fail_to_pass_count", 0),
                "pass_to_pass_count": merged.get("pass_to_pass_count", 0),
                "file_overlap_count": merged.get("file_overlap_count", 0),
                "model_patch_file_count": len(model_files),
                "gold_patch_file_count": len(gold_files),
                "test_patch_file_count": len(test_files),
                "model_gold_jaccard": jaccard(model_files, gold_files),
                "model_test_jaccard": jaccard(model_files, test_files),
                "model_files_subset_gold": bool(model_files and model_files <= gold_files),
                "model_files_equal_gold": bool(model_files and model_files == gold_files),
                "first_eval_signal": first_relevant_eval_line(eval_path),
                "per_instance_path": SWEEP_DIR / "per_instance" / f"{instance_id}.json",
                "eval_path": eval_path,
            }
        )
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "instance_id",
        "repo",
        "status",
        "valid_model_label",
        "binary_label",
        "taxonomy",
        "base_returncode",
        "model_returncode",
        "gold_returncode",
        "selected_test_count",
        "fail_to_pass_count",
        "pass_to_pass_count",
        "file_overlap_count",
        "model_patch_file_count",
        "gold_patch_file_count",
        "test_patch_file_count",
        "model_gold_jaccard",
        "model_test_jaccard",
        "model_files_subset_gold",
        "model_files_equal_gold",
        "first_eval_signal",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def write_report(
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    valid_rows: list[dict[str, Any]],
    heuristic_results: list[dict[str, Any]],
    analysis_json: Path,
    analysis_csv: Path,
) -> None:
    total = len(rows)
    valid = len(valid_rows)
    valid_pass = sum(1 for row in valid_rows if row["binary_label"] == "PASS")
    taxonomy_counts = Counter(row["taxonomy"] for row in rows)
    status_counts = Counter(row["status"] for row in rows)

    best = max(
        heuristic_results,
        key=lambda item: (
            item["metrics"]["accuracy"] if item["metrics"]["accuracy"] is not None else -1,
            item["metrics"]["f1"] if item["metrics"]["f1"] is not None else -1,
        ),
    )

    report_dir = REPORT.parent
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines: list[str] = [
        "# PX-033 SWE-EVO Failure Taxonomy and Predictor Probe",
        "",
        f"Generated: {generated}",
        "",
        "Status: **PREDICTOR GATE MIXED**",
        "",
        "## Claim Boundary",
        "",
        (
            "This analyzes the six-task SWE-EVO released-prediction F2P sweep already run on AWS. "
            "It is not a trained world model and not a benchmark-scale result. The valid predictor "
            f"slice has only `{valid}` model-patch labels after excluding gold/harness-invalid tasks."
        ),
        "",
        "## Headline Result",
        "",
        (
            f"The executable lane remains useful, but the predictor claim is not proven yet: `{valid_pass}`/`{valid}` "
            "valid model-patch labels passed, all valid failures were semantic incomplete-fix failures, and the "
            f"strongest simple baseline in this tiny slice was `{best['name']}` with accuracy "
            f"`{safe_float(best['metrics']['accuracy'])}` and F1 `{safe_float(best['metrics']['f1'])}`."
        ),
        "",
        "What this proves now:",
        "",
        "- SWE-EVO can produce executable, inspectable labels for Praxis repo-state experiments.",
        "- The failing model patches are not merely patch-apply or Docker failures; gold passes the same selected F2P tests in the valid failures.",
        "- Patch/repo-state overlap alone is not enough evidence for a publishable repo-state world-model claim.",
        "",
        "What it does not prove yet:",
        "",
        "- It does not prove a trained repo-state predictor beats metadata-only baselines.",
        "- It does not justify RWML-style training until we add more labels or cross-model replications.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Sweep tasks | `{total}` |",
        f"| Valid model-patch labels | `{valid}` |",
        f"| Valid PASS | `{valid_pass}` |",
        f"| Valid MODEL_FAIL | `{valid - valid_pass}` |",
        f"| Valid pass rate | `{valid_pass / valid:.4f}` |",
        f"| Gold/harness-invalid tasks | `{taxonomy_counts['HARNESS_OR_TEST_NODE_INVALID']}` |",
        f"| Raw PASS | `{status_counts['PASS']}` |",
        f"| Raw MODEL_FAIL | `{status_counts['MODEL_FAIL']}` |",
        f"| Raw GOLD_FAIL | `{status_counts['GOLD_FAIL']}` |",
        f"| Model under test | `{summary.get('model')}` |",
        f"| Sweep source | [`{SWEEP_DIR.name}`]({rel(SWEEP_DIR, report_dir)}/) |",
        f"| Raw analysis JSON | [`{analysis_json.name}`]({rel(analysis_json, report_dir)}) |",
        f"| Raw analysis CSV | [`{analysis_csv.name}`]({rel(analysis_csv, report_dir)}) |",
        "",
        "## Failure Taxonomy",
        "",
        "| Instance | Repo | Status | Taxonomy | Evidence |",
        "|---|---|---:|---|---|",
    ]

    for row in rows:
        instance_link = rel(row["per_instance_path"], report_dir)
        eval_link = rel(row["eval_path"], report_dir)
        evidence = (
            f"base `{row['base_returncode']}`, model `{row['model_returncode']}`, gold `{row['gold_returncode']}`; "
            f"[instance JSON]({instance_link}); [eval log]({eval_link}); {row['first_eval_signal']}"
        )
        lines.append(
            f"| [`{row['instance_id']}`]({instance_link}) | `{row['repo']}` | `{row['status']}` | "
            f"`{row['taxonomy']}` | {evidence} |"
        )

    lines.extend(
        [
            "",
            "## Metadata vs Repo-State Proxy Probe",
            "",
            (
                "The table below treats the five valid model-patch tasks as PASS/FAIL labels. "
                "Metadata-only rules use task/repo metadata. Repo-state proxy rules use patch-file structure "
                "from the executed artifacts; rules that compare with gold patch files are diagnostic and "
                "not deployable before the answer is known."
            ),
            "",
            "| Rule | Feature class | Accuracy | Precision | Recall | F1 | Notes |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for item in heuristic_results:
        metrics = item["metrics"]
        lines.append(
            f"| `{item['name']}` | {item['feature_class']} | `{safe_float(metrics['accuracy'])}` | "
            f"`{safe_float(metrics['precision'])}` | `{safe_float(metrics['recall'])}` | "
            f"`{safe_float(metrics['f1'])}` | {item['notes']} |"
        )

    lines.extend(
        [
            "",
            "## Per-Task Feature Table",
            "",
            "| Instance | Label | Selected tests | F2P | Overlap | Model files | Gold files | Model/Gold Jaccard | First eval signal |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        label = row["binary_label"] if row["valid_model_label"] else "EXCLUDED"
        lines.append(
            f"| `{row['instance_id']}` | `{label}` | `{row['selected_test_count']}` | "
            f"`{row['fail_to_pass_count']}` | `{row['file_overlap_count']}` | "
            f"`{row['model_patch_file_count']}` | `{row['gold_patch_file_count']}` | "
            f"`{row['model_gold_jaccard']:.4f}` | {row['first_eval_signal']} |"
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "PX-033 should continue only as a measured execution-and-prediction lane. The useful next gate "
                "is either more executable F2P labels or a cross-model replication on the same valid tasks, followed "
                "by a comparison against the repo-family metadata baseline. Do not move to expensive world-model "
                "training until a repo-state predictor beats that simple baseline on a larger valid slice."
            ),
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    summary = load_json(SWEEP_DIR / "swe_evo_true_eval_sweep_summary.json")
    rows = build_rows(summary)
    valid_rows = [row for row in rows if row["valid_model_label"]]

    heuristics: list[dict[str, Any]] = [
        {
            "name": "metadata_repo_is_requests",
            "feature_class": "metadata-only",
            "predictor": lambda row: "PASS" if row["repo"] == "psf/requests" else "FAIL",
            "notes": "Predicts requests tasks pass and non-requests tasks fail.",
        },
        {
            "name": "metadata_selected_tests_ge_2",
            "feature_class": "metadata-only",
            "predictor": lambda row: "PASS" if row["selected_test_count"] >= 2 else "FAIL",
            "notes": "Uses selected fail-to-pass test count only.",
        },
        {
            "name": "repo_state_gold_overlap_ge_1",
            "feature_class": "repo-state proxy, post-hoc",
            "predictor": lambda row: "PASS" if row["file_overlap_count"] >= 1 else "FAIL",
            "notes": "All valid tasks overlap at least one gold file, so this is not discriminative.",
        },
        {
            "name": "repo_state_gold_overlap_ge_2",
            "feature_class": "repo-state proxy, post-hoc",
            "predictor": lambda row: "PASS" if row["file_overlap_count"] >= 2 else "FAIL",
            "notes": "High precision in this slice, but misses one passing requests task.",
        },
        {
            "name": "repo_state_model_subset_gold",
            "feature_class": "repo-state proxy, post-hoc",
            "predictor": lambda row: "PASS" if row["model_files_subset_gold"] else "FAIL",
            "notes": "Tests whether the model touched only files later touched by gold.",
        },
        {
            "name": "repo_state_model_gold_jaccard_ge_033",
            "feature_class": "repo-state proxy, post-hoc",
            "predictor": lambda row: "PASS" if row["model_gold_jaccard"] >= 0.33 else "FAIL",
            "notes": "Approximate file-level similarity threshold.",
        },
    ]

    heuristic_results: list[dict[str, Any]] = []
    for item in heuristics:
        metrics = binary_metrics(valid_rows, item["predictor"])
        heuristic_results.append(
            {
                "name": item["name"],
                "feature_class": item["feature_class"],
                "notes": item["notes"],
                "metrics": metrics,
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    analysis_csv = OUT_DIR / "swe_evo_failure_taxonomy_and_predictor_probe.csv"
    analysis_json = OUT_DIR / "swe_evo_failure_taxonomy_and_predictor_probe.json"
    write_csv(rows, analysis_csv)
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_boundary": "Small-n taxonomy and heuristic predictor probe over the PX-033 SWE-EVO six-task F2P sweep.",
        "sweep_dir": rel(SWEEP_DIR, ROOT),
        "valid_model_label_count": len(valid_rows),
        "raw_task_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "taxonomy_counts": dict(Counter(row["taxonomy"] for row in rows)),
        "heuristics": heuristic_results,
        "rows": [
            {
                key: value
                for key, value in row.items()
                if key not in {"per_instance_path", "eval_path"}
            }
            for row in rows
        ],
    }
    analysis_json.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_report(summary, rows, valid_rows, heuristic_results, analysis_json, analysis_csv)
    print(f"Wrote {rel(REPORT, ROOT)}")
    print(f"Wrote {rel(analysis_json, ROOT)}")
    print(f"Wrote {rel(analysis_csv, ROOT)}")


if __name__ == "__main__":
    main()
