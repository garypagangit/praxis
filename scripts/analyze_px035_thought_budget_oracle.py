#!/usr/bin/env python3
"""PX-035 thought-budget oracle probe over EXP01 TTC artifacts."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXP01_DIR = ROOT / "runs" / "frontier-exp01-ttc-transfer-full-20260618"
CTI_ABLATION = ROOT / "runs" / "sec-lord-relationship-evidence-ablation-8b-20260517" / "summary.json"
OUT_DIR = ROOT / "runs" / "px035-thought-budget-oracle-20260630"
REPORT = ROOT / "reports" / "frontier_ai_ml_experiments_20260618" / "PX035_THOUGHT_BUDGET_ORACLE_20260630.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def group_scores(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (row["model"], row["split_role"], row["dataset"], row["row_key"])
        policy = f"{row['strategy']}_k{row['budget_k']}"
        grouped[key][policy] = row
    return grouped


def eval_policy(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"rows": 0, "correct": 0, "accuracy": 0.0, "mean_tokens": 0.0, "total_tokens": 0}
    correct = sum(1 for item in items if item["is_correct"])
    total_tokens = sum(float(item["tokens_used"]) for item in items)
    return {
        "rows": len(items),
        "correct": correct,
        "accuracy": correct / len(items),
        "mean_tokens": total_tokens / len(items),
        "total_tokens": total_tokens,
    }


def threshold_choice(policies: dict[str, dict[str, Any]], threshold: float) -> dict[str, Any]:
    k2 = policies["majority_vote_k2"]
    k8 = policies["majority_vote_k8"]
    if float(k2["self_consistency_margin"]) < threshold:
        chosen = dict(k8)
        chosen["router_decision"] = "ESCALATE_TO_K8"
    else:
        chosen = dict(k2)
        chosen["router_decision"] = "STOP_AT_K2"
    chosen["router_threshold"] = threshold
    return chosen


def oracle_choice(policies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        policies[key]
        for key in ["single_sample_k1", "majority_vote_k2", "majority_vote_k4", "majority_vote_k8"]
        if key in policies
    ]
    correct = [item for item in candidates if item["is_correct"]]
    pool = correct if correct else candidates
    chosen = min(pool, key=lambda item: float(item["tokens_used"]))
    chosen = dict(chosen)
    chosen["router_decision"] = "HINDSIGHT_MIN_TOKEN_CORRECT" if correct else "HINDSIGHT_MIN_TOKEN_WRONG"
    return chosen


def split_items(
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, Any]]],
    model: str,
    split_role: str,
) -> list[tuple[tuple[str, str, str, str], dict[str, dict[str, Any]]]]:
    return [
        (key, policies)
        for key, policies in grouped.items()
        if key[0] == model
        and key[1] == split_role
        and "majority_vote_k2" in policies
        and "majority_vote_k8" in policies
    ]


def choose_threshold_for_model(
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, Any]]],
    model: str,
) -> dict[str, Any]:
    validation = split_items(grouped, model, "validation_policy_selection")
    k8_eval = eval_policy([policies["majority_vote_k8"] for _, policies in validation])
    thresholds = [round(i / 40, 3) for i in range(0, 41)] + [1.001]
    candidates: list[dict[str, Any]] = []
    for threshold in thresholds:
        chosen = [threshold_choice(policies, threshold) for _, policies in validation]
        metrics = eval_policy(chosen)
        metrics["threshold"] = threshold
        metrics["escalation_rate"] = sum(1 for item in chosen if item["router_decision"] == "ESCALATE_TO_K8") / len(chosen)
        metrics["retention_vs_k8"] = metrics["accuracy"] / k8_eval["accuracy"] if k8_eval["accuracy"] else 1.0
        candidates.append(metrics)

    eligible = [item for item in candidates if item["accuracy"] >= 0.95 * k8_eval["accuracy"]]
    if not eligible:
        selected = max(candidates, key=lambda item: (item["accuracy"], -item["mean_tokens"]))
        reason = "no_threshold_retained_95pct_k8"
    else:
        selected = min(eligible, key=lambda item: (item["mean_tokens"], -item["accuracy"], item["threshold"]))
        reason = "min_tokens_retaining_95pct_validation_k8"
    return {
        "model": model,
        "selected_threshold": selected["threshold"],
        "selection_reason": reason,
        "validation_k8": k8_eval,
        "validation_selected_router": selected,
        "threshold_candidates": candidates,
    }


def evaluate_selected(
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, Any]]],
    thresholds: dict[str, dict[str, Any]],
    split_role: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    k2: list[dict[str, Any]] = []
    k8: list[dict[str, Any]] = []
    oracle: list[dict[str, Any]] = []
    by_model: dict[str, dict[str, Any]] = {}
    for model, config in thresholds.items():
        items = split_items(grouped, model, split_role)
        threshold = float(config["selected_threshold"])
        selected_rows = []
        for key, policies in items:
            chosen = threshold_choice(policies, threshold)
            hindsight = oracle_choice(policies)
            row = {
                "model": model,
                "split_role": split_role,
                "dataset": key[2],
                "row_key": key[3],
                "threshold": threshold,
                "k2_correct": policies["majority_vote_k2"]["is_correct"],
                "k8_correct": policies["majority_vote_k8"]["is_correct"],
                "k2_margin": policies["majority_vote_k2"]["self_consistency_margin"],
                "router_decision": chosen["router_decision"],
                "router_correct": chosen["is_correct"],
                "router_tokens": chosen["tokens_used"],
                "k2_tokens": policies["majority_vote_k2"]["tokens_used"],
                "k8_tokens": policies["majority_vote_k8"]["tokens_used"],
                "oracle_correct": hindsight["is_correct"],
                "oracle_tokens": hindsight["tokens_used"],
            }
            rows.append(row)
            selected_rows.append(chosen)
            k2.append(policies["majority_vote_k2"])
            k8.append(policies["majority_vote_k8"])
            oracle.append(hindsight)
        by_model[model] = {
            "router": eval_policy(selected_rows),
            "k2": eval_policy([policies["majority_vote_k2"] for _, policies in items]),
            "k8": eval_policy([policies["majority_vote_k8"] for _, policies in items]),
            "oracle": eval_policy([oracle_choice(policies) for _, policies in items]),
            "escalation_rate": sum(1 for item in selected_rows if item["router_decision"] == "ESCALATE_TO_K8") / len(selected_rows)
            if selected_rows
            else 0.0,
        }
    return {
        "split_role": split_role,
        "rows": rows,
        "aggregate": {
            "router": eval_policy(
                [
                    {
                        "is_correct": row["router_correct"],
                        "tokens_used": row["router_tokens"],
                    }
                    for row in rows
                ]
            ),
            "k2": eval_policy(k2),
            "k8": eval_policy(k8),
            "oracle": eval_policy(oracle),
            "escalation_rate": sum(1 for row in rows if row["router_decision"] == "ESCALATE_TO_K8") / len(rows)
            if rows
            else 0.0,
        },
        "by_model": by_model,
    }


def cti_budget_frontier() -> dict[str, Any]:
    summary = load_json(CTI_ABLATION)
    by_condition = {row["condition"]: row for row in summary["condition_summaries"]}
    frontier_conditions = ["vanilla", "technique_only_evidence", "relationship_evidence"]
    frontier = {
        condition: {
            "accuracy": by_condition[condition]["accuracy"],
            "mean_prompt_tokens": by_condition[condition]["mean_prompt_tokens"],
            "mean_evidence_block_tokens": by_condition[condition]["mean_evidence_block_tokens"],
        }
        for condition in frontier_conditions
    }
    return {
        "frontier": frontier,
        "relationship_minus_technique_accuracy": frontier["relationship_evidence"]["accuracy"]
        - frontier["technique_only_evidence"]["accuracy"],
        "relationship_minus_technique_prompt_tokens": frontier["relationship_evidence"]["mean_prompt_tokens"]
        - frontier["technique_only_evidence"]["mean_prompt_tokens"],
    }


def write_rows_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "model",
        "split_role",
        "dataset",
        "row_key",
        "threshold",
        "k2_correct",
        "k8_correct",
        "k2_margin",
        "router_decision",
        "router_correct",
        "router_tokens",
        "k2_tokens",
        "k8_tokens",
        "oracle_correct",
        "oracle_tokens",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def write_report(analysis: dict[str, Any], rows_csv: Path, analysis_json: Path) -> None:
    strict = analysis["evaluations"]["strict_domain_holdout_test"]["aggregate"]
    in_domain = analysis["evaluations"]["test_in_domain"]["aggregate"]
    val = analysis["evaluations"]["validation_policy_selection"]["aggregate"]
    cti = analysis["cti_budget_frontier"]

    def pct_saved(candidate: dict[str, Any], baseline: dict[str, Any]) -> float:
        return 1.0 - (candidate["mean_tokens"] / baseline["mean_tokens"] if baseline["mean_tokens"] else 0.0)

    def retention(candidate: dict[str, Any], baseline: dict[str, Any]) -> float:
        return candidate["accuracy"] / baseline["accuracy"] if baseline["accuracy"] else 1.0

    report_dir = REPORT.parent
    rel_json = analysis_json.relative_to(ROOT).as_posix()
    rel_csv = rows_csv.relative_to(ROOT).as_posix()
    lines = [
        "# PX-035 Thought-Budget Oracle Probe",
        "",
        f"Generated: {analysis['generated_utc']}",
        "",
        "Status: **MIXED - ORACLE UPPER BOUND EXISTS; CHEAP ROUTER NOT PROMOTED**",
        "",
        "## Claim Boundary",
        "",
        (
            "This is a budget-control probe over the existing EXP01 test-time-compute run, not Long-CoT "
            "data collection or RLVR training. The deployable probe uses a cheap K=2 majority-vote "
            "self-consistency margin, selected on the validation-policy split, to decide whether to spend "
            "the full K=8 budget."
        ),
        "",
        "## Headline Result",
        "",
        (
            "A hindsight thought-budget oracle exists, but the cheap validation-selected margin router is not "
            "strong enough to promote PX-035 as a new positive research lane. On the strict MATH-500 holdout, "
            f"the K=8 baseline accuracy is `{strict['k8']['accuracy']:.4f}` with mean tokens `{strict['k8']['mean_tokens']:.1f}`. "
            f"The deployable K=2->K=8 router reaches accuracy `{strict['router']['accuracy']:.4f}` with mean tokens "
            f"`{strict['router']['mean_tokens']:.1f}`; retention is `{retention(strict['router'], strict['k8']):.4f}` "
            f"and token savings are `{pct_saved(strict['router'], strict['k8']):.4f}`."
        ),
        "",
        (
            f"The hindsight oracle upper bound reaches accuracy `{strict['oracle']['accuracy']:.4f}` with mean tokens "
            f"`{strict['oracle']['mean_tokens']:.1f}`, showing there is budget structure in the frozen generations. "
            "The missing piece is a reliable cheap predictor of which rows deserve the long budget."
        ),
        "",
        "## EXP01 Budget-Router Scorecard",
        "",
        "| Split | Policy | Accuracy | Mean tokens | Retention vs K8 | Token savings vs K8 | Escalation rate |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for label, payload in [
        ("Validation policy", val),
        ("In-domain test", in_domain),
        ("Strict holdout", strict),
    ]:
        for policy in ["k2", "router", "k8", "oracle"]:
            item = payload[policy]
            escalation = payload.get("escalation_rate", 0.0) if policy == "router" else (1.0 if policy == "k8" else 0.0)
            lines.append(
                f"| {label} | `{policy}` | `{item['accuracy']:.4f}` | `{item['mean_tokens']:.1f}` | "
                f"`{retention(item, payload['k8']):.4f}` | `{pct_saved(item, payload['k8']):.4f}` | `{escalation:.4f}` |"
            )

    lines.extend(
        [
            "",
            "## Selected Router Thresholds",
            "",
            "| Model | Threshold | Validation K8 acc. | Validation router acc. | Validation router mean tokens | Reason |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for model, config in sorted(analysis["selected_thresholds"].items()):
        lines.append(
            f"| `{model}` | `{config['selected_threshold']}` | "
            f"`{config['validation_k8']['accuracy']:.4f}` | "
            f"`{config['validation_selected_router']['accuracy']:.4f}` | "
            f"`{config['validation_selected_router']['mean_tokens']:.1f}` | {config['selection_reason']} |"
        )

    lines.extend(
        [
            "",
            "## CTI Evidence-Budget Cross-Check",
            "",
            (
                "The PX-003 CTI ablation shows a separate budget frontier: vanilla prompt accuracy "
                f"`{cti['frontier']['vanilla']['accuracy']:.3f}` at mean prompt tokens "
                f"`{cti['frontier']['vanilla']['mean_prompt_tokens']:.1f}`, technique-only evidence accuracy "
                f"`{cti['frontier']['technique_only_evidence']['accuracy']:.3f}` at "
                f"`{cti['frontier']['technique_only_evidence']['mean_prompt_tokens']:.1f}` tokens, and relationship "
                f"evidence accuracy `{cti['frontier']['relationship_evidence']['accuracy']:.3f}` at "
                f"`{cti['frontier']['relationship_evidence']['mean_prompt_tokens']:.1f}` tokens."
            ),
            "",
            (
                "That cross-check agrees with the EXP01 result: budget tiers matter, but the current evidence is "
                "not a standalone Long-CoT/RLVR result. It is a practical budget-control diagnostic that should "
                "be merged into EXP01/PX-003 style protocols."
            ),
            "",
            "## Decision",
            "",
            "- Do not start Long-CoT collection or RLVR training for PX-035.",
            "- Keep PX-035 as a mixed budget-control add-on: useful diagnostics and an oracle upper bound, but no deployable positive yet.",
            "- A future positive would require a cheap predictor that retains at least 95% of K8 strict-holdout accuracy while saving at least 25% tokens across more model families.",
            "",
            "## Artifacts",
            "",
            f"- Raw analysis JSON: [`{rel_json}`](../../{rel_json})",
            f"- Per-row router CSV: [`{rel_csv}`](../../{rel_csv})",
            "- EXP01 full run: [`runs/frontier-exp01-ttc-transfer-full-20260618/`](../../runs/frontier-exp01-ttc-transfer-full-20260618/)",
            "- CTI ablation cross-check: [`SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md`](../relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md)",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(EXP01_DIR / "scores_all.jsonl")
    grouped = group_scores(rows)
    models = sorted({key[0] for key in grouped})
    selected_thresholds = {model: choose_threshold_for_model(grouped, model) for model in models}
    evaluations = {
        split: evaluate_selected(grouped, selected_thresholds, split)
        for split in [
            "validation_policy_selection",
            "test_in_domain",
            "strict_domain_holdout_test",
        ]
    }
    router_rows = []
    for split_payload in evaluations.values():
        router_rows.extend(split_payload["rows"])
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_boundary": "Budget-control probe over frozen EXP01 TTC generations; no Long-CoT training or RLVR.",
        "selected_thresholds": selected_thresholds,
        "evaluations": evaluations,
        "cti_budget_frontier": cti_budget_frontier(),
    }
    rows_csv = OUT_DIR / "px035_budget_router_rows.csv"
    analysis_json = OUT_DIR / "px035_thought_budget_oracle.json"
    write_rows_csv(router_rows, rows_csv)
    analysis_json.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_report(analysis, rows_csv, analysis_json)
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"Wrote {analysis_json.relative_to(ROOT)}")
    print(f"Wrote {rows_csv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
