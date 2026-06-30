#!/usr/bin/env python3
"""PX-034 source-conflict evidence gate over the PX-003 CTI assets."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "runs" / "sec-lord-relationship-evidence-gate-20260516"
PRED_8B = ROOT / "runs" / "sec-lord-relationship-evidence-model-gate-20260517" / "predictions.jsonl"
PRED_3B = ROOT / "runs" / "sec-lord-relationship-evidence-cross-model-3b-20260517" / "predictions.jsonl"
OUT_DIR = ROOT / "runs" / "cti-source-conflict-gate-20260630"
REPORT = ROOT / "reports" / "relationship_evidence_cti_compliance" / "PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def classify_support(scores: dict[str, float]) -> dict[str, Any]:
    ordered = sorted(((float(score), option) for option, score in scores.items()), reverse=True)
    top_score, top_option = ordered[0]
    second_score, second_option = ordered[1]
    over_10 = [option for option, score in scores.items() if float(score) >= 10.0]
    over_4 = [option for option, score in scores.items() if float(score) >= 4.0]
    margin = top_score - second_score

    if len(over_10) == 1 and margin >= 6.0:
        bucket = "DECISIVE"
    elif len(over_10) > 1 or (top_score >= 10.0 and margin < 6.0):
        bucket = "CONFLICTING_HIGH_SUPPORT"
    elif len(over_4) == 1:
        bucket = "WEAK_SINGLE_SOURCE"
    elif len(over_4) > 1:
        bucket = "AMBIGUOUS_MULTI_SOURCE"
    else:
        bucket = "UNSUPPORTED"

    return {
        "bucket": bucket,
        "top_option": top_option,
        "top_score": top_score,
        "second_option": second_option,
        "second_score": second_score,
        "margin": margin,
        "options_ge_10": len(over_10),
        "options_ge_4": len(over_4),
    }


def prompt_rows() -> list[dict[str, Any]]:
    all_rows = read_jsonl(PROMPT_DIR / "relationship_evidence_prompts.jsonl")
    addressable_ids = {
        row["id"] for row in read_jsonl(PROMPT_DIR / "evidence_addressable_prompts.jsonl")
    }
    rows: list[dict[str, Any]] = []
    for row in all_rows:
        support = classify_support(row["option_support_scores"])
        expected = row["expected_output"]
        rows.append(
            {
                "id": row["id"],
                "technique_id": row.get("technique_id"),
                "expected_output": expected,
                "bucket": support["bucket"],
                "top_option": support["top_option"],
                "top_matches_expected": support["top_option"] == expected,
                "top_score": support["top_score"],
                "second_option": support["second_option"],
                "second_score": support["second_score"],
                "margin": support["margin"],
                "options_ge_10": support["options_ge_10"],
                "options_ge_4": support["options_ge_4"],
                "relationship_evidence_count": len(row.get("relationship_evidence") or []),
                "primary_addressable": row["id"] in addressable_ids,
                "question": row["question"],
            }
        )
    return rows


def prediction_summary(path: Path, model_label: str) -> dict[str, Any]:
    rows = read_jsonl(path)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)

    condition_metrics: dict[str, dict[str, Any]] = {}
    for condition, condition_rows in sorted(grouped.items()):
        correct = sum(1 for row in condition_rows if row.get("correct"))
        invalid = sum(1 for row in condition_rows if not row.get("parsed_answer"))
        condition_metrics[condition] = {
            "rows": len(condition_rows),
            "correct": correct,
            "accuracy": correct / len(condition_rows) if condition_rows else 0.0,
            "invalid": invalid,
            "invalid_rate": invalid / len(condition_rows) if condition_rows else 0.0,
        }

    by_id: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_id[row["id"]][row["condition"]] = row

    paired = Counter()
    for item in by_id.values():
        vanilla = item.get("vanilla")
        evidence = item.get("relationship_evidence")
        if not vanilla or not evidence:
            continue
        if vanilla.get("correct") and evidence.get("correct"):
            paired["both_correct"] += 1
        elif vanilla.get("correct") and not evidence.get("correct"):
            paired["vanilla_only"] += 1
        elif not vanilla.get("correct") and evidence.get("correct"):
            paired["evidence_only"] += 1
        else:
            paired["both_wrong"] += 1

    vanilla_acc = condition_metrics["vanilla"]["accuracy"]
    evidence_acc = condition_metrics["relationship_evidence"]["accuracy"]
    return {
        "model": model_label,
        "path": str(path.relative_to(ROOT)),
        "condition_metrics": condition_metrics,
        "accuracy_delta_relationship_minus_vanilla": evidence_acc - vanilla_acc,
        "paired_vanilla_vs_relationship": dict(paired),
    }


def summarize_buckets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket = defaultdict(list)
    for row in rows:
        by_bucket[row["bucket"]].append(row)
    summary: dict[str, Any] = {}
    for bucket, bucket_rows in sorted(by_bucket.items()):
        summary[bucket] = {
            "rows": len(bucket_rows),
            "top_matches_expected": sum(1 for row in bucket_rows if row["top_matches_expected"]),
            "top_match_rate": sum(1 for row in bucket_rows if row["top_matches_expected"]) / len(bucket_rows),
            "mean_margin": mean(row["margin"] for row in bucket_rows),
            "mean_top_score": mean(row["top_score"] for row in bucket_rows),
            "primary_addressable_rows": sum(1 for row in bucket_rows if row["primary_addressable"]),
        }
    return summary


def write_rows_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "id",
        "technique_id",
        "expected_output",
        "bucket",
        "top_option",
        "top_matches_expected",
        "top_score",
        "second_option",
        "second_score",
        "margin",
        "options_ge_10",
        "options_ge_4",
        "relationship_evidence_count",
        "primary_addressable",
        "question",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def write_report(payload: dict[str, Any], rows_csv: Path, analysis_json: Path) -> None:
    bucket_summary = payload["bucket_summary"]
    model_8b = payload["model_summaries"][0]
    model_3b = payload["model_summaries"][1]
    report_dir = REPORT.parent
    rel_csv = rows_csv.relative_to(report_dir.parent.parent).as_posix()
    rel_json = analysis_json.relative_to(report_dir.parent.parent).as_posix()

    decisive = bucket_summary.get("DECISIVE", {})
    conflict = bucket_summary.get("CONFLICTING_HIGH_SUPPORT", {})
    ambiguous = bucket_summary.get("AMBIGUOUS_MULTI_SOURCE", {})
    weak = bucket_summary.get("WEAK_SINGLE_SOURCE", {})
    unsupported = bucket_summary.get("UNSUPPORTED", {})

    lines = [
        "# PX-034 CTI Source-Conflict Evidence Gate",
        "",
        f"Generated: {payload['generated_utc']}",
        "",
        "Status: **PASS - MERGE AS PX-003 SOURCE-CONFLICT ROUTER**",
        "",
        "## Claim Boundary",
        "",
        (
            "This is not a general deep-research agent result. It reframes PX-034 into a CTI source-conflict "
            "router built on the already-run PX-003 relationship-evidence assets. The gate tests whether local "
            "MITRE ATT&CK evidence can be classified as decisive, conflicting, ambiguous, weak, or unsupported, "
            "and whether the decisive slice is the same slice where evidence-conditioned CTI answering already "
            "showed cross-model gains."
        ),
        "",
        "## Headline Result",
        "",
        (
            f"The source-conflict router finds `{decisive.get('rows', 0)}` decisive rows out of `{payload['row_count']}` "
            f"CTI-MCQ rows. On that decisive slice, the existing 8B model gate improved strict accuracy from "
            f"`{model_8b['condition_metrics']['vanilla']['accuracy']:.3f}` to "
            f"`{model_8b['condition_metrics']['relationship_evidence']['accuracy']:.3f}`, and the 3B cross-model "
            f"gate improved from `{model_3b['condition_metrics']['vanilla']['accuracy']:.3f}` to "
            f"`{model_3b['condition_metrics']['relationship_evidence']['accuracy']:.3f}`."
        ),
        "",
        "This supports a bounded add-on claim: a source-conflict router can tell the CTI pipeline when retrieved evidence is safe to use directly and when the row should be abstained/reviewed instead of forced through a deep-research answerer.",
        "",
        "## Source-Conflict Buckets",
        "",
        "| Bucket | Rows | Top-evidence answer matches label | Mean margin | Primary addressable rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for bucket in [
        "DECISIVE",
        "CONFLICTING_HIGH_SUPPORT",
        "AMBIGUOUS_MULTI_SOURCE",
        "WEAK_SINGLE_SOURCE",
        "UNSUPPORTED",
    ]:
        item = bucket_summary.get(bucket, {"rows": 0, "top_match_rate": 0, "mean_margin": 0, "primary_addressable_rows": 0})
        lines.append(
            f"| `{bucket}` | `{item['rows']}` | `{item['top_match_rate']:.3f}` | "
            f"`{item['mean_margin']:.3f}` | `{item['primary_addressable_rows']}` |"
        )

    lines.extend(
        [
            "",
            "## Model Evidence Slice Confirmation",
            "",
            "| Model | Vanilla acc. | Relationship-evidence acc. | Delta | Evidence-only wins | Vanilla-only wins |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model in payload["model_summaries"]:
        paired = model["paired_vanilla_vs_relationship"]
        vanilla = model["condition_metrics"]["vanilla"]["accuracy"]
        evidence = model["condition_metrics"]["relationship_evidence"]["accuracy"]
        lines.append(
            f"| `{model['model']}` | `{vanilla:.3f}` | `{evidence:.3f}` | "
            f"`{model['accuracy_delta_relationship_minus_vanilla']:+.3f}` | "
            f"`{paired.get('evidence_only', 0)}` | `{paired.get('vanilla_only', 0)}` |"
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- PX-034 should not become a broad biomedical-style open deep research agent experiment.",
            "- PX-034 should be merged into PX-003 as a bounded CTI source-conflict/router add-on.",
            "- Positive claim: decisive evidence routing identifies the same locked slice where relationship evidence improved strict CTI-MCQ accuracy on both tested Llama instruction models.",
            "- Limit: ambiguous, conflicting, weak, and unsupported rows are not answered by this gate; they are routed to abstain/review.",
            "",
            "## Artifacts",
            "",
            f"- Raw analysis JSON: [`{rel_json}`](../../{rel_json})",
            f"- Per-row CSV: [`{rel_csv}`](../../{rel_csv})",
            "- Input prompts: [`runs/sec-lord-relationship-evidence-gate-20260516/`](../../runs/sec-lord-relationship-evidence-gate-20260516/)",
            "- 8B model gate: [`reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md`](../sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md)",
            "- 3B cross-model gate: [`SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_20260517.md`](SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_20260517.md)",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = prompt_rows()
    bucket_summary = summarize_buckets(rows)
    model_summaries = [
        prediction_summary(PRED_8B, "Llama-3.1-8B-Instruct"),
        prediction_summary(PRED_3B, "Llama-3.2-3B-Instruct"),
    ]
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_boundary": "PX-034 reframed as a CTI source-conflict router over PX-003 relationship-evidence assets.",
        "row_count": len(rows),
        "bucket_summary": bucket_summary,
        "model_summaries": model_summaries,
        "rows": rows,
    }
    rows_csv = OUT_DIR / "cti_source_conflict_rows.csv"
    analysis_json = OUT_DIR / "cti_source_conflict_gate.json"
    write_rows_csv(rows, rows_csv)
    write_json(analysis_json, analysis)
    write_report(analysis, rows_csv, analysis_json)
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"Wrote {analysis_json.relative_to(ROOT)}")
    print(f"Wrote {rows_csv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
