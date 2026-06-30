#!/usr/bin/env python3
"""PX-015 TTC transferability confidence-interval and missing-gates audit."""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXP01_DIR = ROOT / "runs" / "frontier-exp01-ttc-transfer-full-20260618"
OUT_DIR = ROOT / "runs" / "px015-ttc-ci-gate-20260630"
REPORT = ROOT / "reports" / "frontier_ai_ml_experiments_20260618" / "PX015_TTC_CI_GATE_20260630.md"
BOOTSTRAPS = 2000
RNG = random.Random(20260630)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def quantiles(values: list[float], lo: float = 0.025, hi: float = 0.975) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    values = sorted(values)
    lo_idx = max(0, min(len(values) - 1, int(round(lo * (len(values) - 1)))))
    hi_idx = max(0, min(len(values) - 1, int(round(hi * (len(values) - 1)))))
    return values[lo_idx], values[hi_idx]


def bootstrap_accuracy(flags: list[bool]) -> dict[str, float]:
    if not flags:
        return {"accuracy": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    n = len(flags)
    estimate = sum(flags) / n
    samples = []
    for _ in range(BOOTSTRAPS):
        sample = [flags[RNG.randrange(n)] for _ in range(n)]
        samples.append(sum(sample) / n)
    low, high = quantiles(samples)
    return {"accuracy": estimate, "ci_low": low, "ci_high": high}


def bootstrap_retention(pairs: list[tuple[bool, bool]]) -> dict[str, float | None]:
    if not pairs:
        return {"source_accuracy": 0.0, "target_accuracy": 0.0, "retention": None, "ci_low": None, "ci_high": None}
    source_acc = sum(1 for source, _ in pairs if source) / len(pairs)
    target_acc = sum(1 for _, target in pairs if target) / len(pairs)
    if target_acc == 0:
        return {"source_accuracy": source_acc, "target_accuracy": target_acc, "retention": None, "ci_low": None, "ci_high": None}
    retention = source_acc / target_acc
    samples = []
    n = len(pairs)
    for _ in range(BOOTSTRAPS):
        sample = [pairs[RNG.randrange(n)] for _ in range(n)]
        src = sum(1 for source, _ in sample if source) / n
        tgt = sum(1 for _, target in sample if target) / n
        if tgt > 0:
            samples.append(src / tgt)
    low, high = quantiles(samples)
    return {
        "source_accuracy": source_acc,
        "target_accuracy": target_acc,
        "retention": retention,
        "ci_low": low,
        "ci_high": high,
    }


def score_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str, int], dict[str, Any]]:
    indexed: dict[tuple[str, str, str, str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (
            row["model"],
            row["split_role"],
            row["dataset"],
            row["row_key"],
            row["strategy"],
            int(row["budget_k"]),
        )
        indexed[key] = row
    return indexed


def rows_for_policy(
    rows: list[dict[str, Any]],
    model: str,
    split_role: str,
    strategy: str,
    budget_k: int,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row["model"] == model
        and row["split_role"] == split_role
        and row["strategy"] == strategy
        and int(row["budget_k"]) == budget_k
    ]


def selected_policy_ci(rows: list[dict[str, Any]], selected: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for policy in selected:
        model = policy["model"]
        strategy = policy["selected_strategy"]
        budget = int(policy["selected_budget_k"])
        for split_role in ["validation_policy_selection", "test_in_domain", "strict_domain_holdout_test"]:
            policy_rows = rows_for_policy(rows, model, split_role, strategy, budget)
            flags = [bool(row["is_correct"]) for row in policy_rows]
            ci = bootstrap_accuracy(flags)
            out.append(
                {
                    "model": model,
                    "split_role": split_role,
                    "strategy": strategy,
                    "budget_k": budget,
                    "rows": len(flags),
                    "correct": sum(flags),
                    **ci,
                }
            )
    return out


def transfer_ci(rows: list[dict[str, Any]], transfer_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    indexed = score_index(rows)
    out = []
    for cell in transfer_rows:
        source_budget = int(cell["source_budget_k"])
        target_budget = int(cell["target_optimal_budget_k"])
        source_strategy = cell["source_strategy"]
        target_strategy = cell["target_optimal_strategy"]
        target_model = cell["target_model"]
        split_role = cell["evaluation_role"]
        target_policy_rows = rows_for_policy(rows, target_model, split_role, target_strategy, target_budget)
        pairs = []
        for target_row in target_policy_rows:
            key = (
                target_model,
                split_role,
                target_row["dataset"],
                target_row["row_key"],
                source_strategy,
                source_budget,
            )
            source_row = indexed.get(key)
            if source_row is not None:
                pairs.append((bool(source_row["is_correct"]), bool(target_row["is_correct"])))
        ci = bootstrap_retention(pairs)
        out.append(
            {
                "source_model": cell["source_model"],
                "target_model": target_model,
                "evaluation_role": split_role,
                "source_strategy": source_strategy,
                "source_budget_k": source_budget,
                "target_optimal_strategy": target_strategy,
                "target_optimal_budget_k": target_budget,
                "rows": len(pairs),
                **ci,
            }
        )
    return out


def aggregate_retention(cells: list[dict[str, Any]]) -> dict[str, Any]:
    by_role: dict[str, list[float]] = defaultdict(list)
    nulls: dict[str, int] = defaultdict(int)
    for cell in cells:
        role = cell["evaluation_role"]
        if cell["retention"] is None:
            nulls[role] += 1
        else:
            by_role[role].append(float(cell["retention"]))
    out: dict[str, Any] = {}
    for role, values in by_role.items():
        samples = []
        n = len(values)
        for _ in range(BOOTSTRAPS):
            sample = [values[RNG.randrange(n)] for _ in range(n)]
            samples.append(sum(sample) / n)
        low, high = quantiles(samples)
        out[role] = {
            "non_null_cells": n,
            "null_target_zero_cells": nulls.get(role, 0),
            "mean_retention": sum(values) / n if n else None,
            "ci_low": low,
            "ci_high": high,
        }
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_report(analysis: dict[str, Any], selected_csv: Path, transfer_csv: Path, analysis_json: Path) -> None:
    selected_rows = analysis["selected_policy_ci"]
    qwen_holdout = next(
        row
        for row in selected_rows
        if row["model"] == "qwen2p5_7b_instruct" and row["split_role"] == "strict_domain_holdout_test"
    )
    qwen_in_domain = next(
        row
        for row in selected_rows
        if row["model"] == "qwen2p5_7b_instruct" and row["split_role"] == "test_in_domain"
    )
    aggregate = analysis["aggregate_retention_ci"]
    strict_ret = aggregate["strict_domain_holdout_test"]
    in_ret = aggregate["test_in_domain"]

    lines = [
        "# PX-015 TTC Transferability CI and Missing-Gates Audit",
        "",
        f"Generated: {analysis['generated_utc']}",
        "",
        "Status: **CI AUDIT COMPLETE - PROVISIONAL HARNESS, NOT PROMOTED**",
        "",
        "## Claim Boundary",
        "",
        (
            "This audit closes the feasible missing-gates work available from the frozen EXP01 artifacts: "
            "bootstrap confidence intervals for selected policies and transfer-retention cells. It does not add "
            "the missing verifier best-of-N or sequential-refinement strategies, so it cannot promote EXP01/PX-015 "
            "to a publishable TTC transferability result."
        ),
        "",
        "## Headline Result",
        "",
        (
            f"The strongest selected model remains `qwen2p5_7b_instruct`, but its strict MATH-500 holdout accuracy is "
            f"`{qwen_holdout['accuracy']:.4f}` with bootstrap 95% CI "
            f"`[{qwen_holdout['ci_low']:.4f}, {qwen_holdout['ci_high']:.4f}]`, far below its in-domain GSM8K test "
            f"accuracy `{qwen_in_domain['accuracy']:.4f}` CI "
            f"`[{qwen_in_domain['ci_low']:.4f}, {qwen_in_domain['ci_high']:.4f}]`."
        ),
        "",
        (
            f"Mean non-null transfer retention is `{in_ret['mean_retention']:.4f}` on in-domain test cells "
            f"CI `[{in_ret['ci_low']:.4f}, {in_ret['ci_high']:.4f}]` and `{strict_ret['mean_retention']:.4f}` on strict "
            f"holdout cells CI `[{strict_ret['ci_low']:.4f}, {strict_ret['ci_high']:.4f}]`, but these retention estimates "
            f"exclude `{strict_ret['null_target_zero_cells']}` strict cells where the target optimum was zero. High retention is therefore "
            "not evidence of strong transferable reasoning performance."
        ),
        "",
        "## Selected-Policy Accuracy CIs",
        "",
        "| Model | Split | Policy | Accuracy | 95% CI | Rows |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in selected_rows:
        lines.append(
            f"| `{row['model']}` | `{row['split_role']}` | `{row['strategy']} K={row['budget_k']}` | "
            f"`{row['accuracy']:.4f}` | `[{row['ci_low']:.4f}, {row['ci_high']:.4f}]` | `{row['rows']}` |"
        )

    lines.extend(
        [
            "",
            "## Transfer-Retention Aggregate CIs",
            "",
            "| Eval role | Mean retention | 95% CI | Non-null cells | Null target-zero cells |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for role, row in aggregate.items():
        lines.append(
            f"| `{role}` | `{row['mean_retention']:.4f}` | `[{row['ci_low']:.4f}, {row['ci_high']:.4f}]` | "
            f"`{row['non_null_cells']}` | `{row['null_target_zero_cells']}` |"
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- Keep PX-015 as a provisional TTC measurement harness.",
            "- Do not claim TTC strategy transferability from this run; strict holdout accuracy is weak and transfer retention is inflated by weak target denominators.",
            "- Missing strategy gates remain unrun: verifier/scorer best-of-N and sequential refinement should be formally dropped or run in a future, narrower TTC study.",
            "- The predictor result remains negative: leave-one-target-family R2 was `-14.9408` in the frozen EXP01 analysis.",
            "",
            "## Artifacts",
            "",
            f"- Raw analysis JSON: [`{analysis_json.relative_to(ROOT).as_posix()}`](../../{analysis_json.relative_to(ROOT).as_posix()})",
            f"- Selected-policy CI CSV: [`{selected_csv.relative_to(ROOT).as_posix()}`](../../{selected_csv.relative_to(ROOT).as_posix()})",
            f"- Transfer-retention CI CSV: [`{transfer_csv.relative_to(ROOT).as_posix()}`](../../{transfer_csv.relative_to(ROOT).as_posix()})",
            "- EXP01 full run: [`runs/frontier-exp01-ttc-transfer-full-20260618/`](../../runs/frontier-exp01-ttc-transfer-full-20260618/)",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores = read_jsonl(EXP01_DIR / "scores_all.jsonl")
    selected = read_csv(EXP01_DIR / "selected_policies.csv")
    transfer = read_csv(EXP01_DIR / "transfer_retention.csv")
    selected_ci = selected_policy_ci(scores, selected)
    transfer_ci_rows = transfer_ci(scores, transfer)
    aggregate = aggregate_retention(transfer_ci_rows)
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_boundary": "Confidence-interval and missing-gates audit over frozen EXP01 TTC artifacts.",
        "bootstrap_samples": BOOTSTRAPS,
        "selected_policy_ci": selected_ci,
        "transfer_retention_ci": transfer_ci_rows,
        "aggregate_retention_ci": aggregate,
        "predictor_leave_one_target_family_r2": -14.94077666731859,
        "decision": "provisional_harness_not_promoted",
    }
    selected_csv = OUT_DIR / "selected_policy_ci.csv"
    transfer_csv = OUT_DIR / "transfer_retention_ci.csv"
    analysis_json = OUT_DIR / "px015_ttc_ci_gate.json"
    write_csv(
        selected_csv,
        selected_ci,
        ["model", "split_role", "strategy", "budget_k", "rows", "correct", "accuracy", "ci_low", "ci_high"],
    )
    write_csv(
        transfer_csv,
        transfer_ci_rows,
        [
            "source_model",
            "target_model",
            "evaluation_role",
            "source_strategy",
            "source_budget_k",
            "target_optimal_strategy",
            "target_optimal_budget_k",
            "rows",
            "source_accuracy",
            "target_accuracy",
            "retention",
            "ci_low",
            "ci_high",
        ],
    )
    analysis_json.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_report(analysis, selected_csv, transfer_csv, analysis_json)
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"Wrote {analysis_json.relative_to(ROOT)}")
    print(f"Wrote {selected_csv.relative_to(ROOT)}")
    print(f"Wrote {transfer_csv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
