from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_bucket_rows(path: Path) -> dict[str, dict[str, str]]:
    """Read PX-034 source-conflict bucket assignments keyed by CTI row id."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def read_predictions(path: Path) -> list[dict[str, Any]]:
    """Read model predictions written by the SEC-LoRD relationship-evidence runner."""

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize_by_bucket(
    buckets_by_id: dict[str, dict[str, str]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Join model predictions to source-conflict buckets and aggregate accuracy."""

    grouped: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    missing_bucket = 0
    for pred in predictions:
        row_id = str(pred["id"])
        bucket_row = buckets_by_id.get(row_id)
        if bucket_row is None:
            missing_bucket += 1
            continue
        condition = str(pred["condition"])
        bucket = bucket_row["bucket"]
        counter = grouped[condition][bucket]
        counter["rows"] += 1
        counter["correct"] += int(bool(pred.get("correct")))
        parsed = str(pred.get("parsed_answer", "") or "")
        counter["invalid"] += int(parsed not in {"A", "B", "C", "D"})

    condition_summaries: dict[str, Any] = {}
    for condition, bucket_map in sorted(grouped.items()):
        rows = []
        totals = Counter()
        for bucket, counter in sorted(bucket_map.items()):
            total_rows = counter["rows"]
            correct = counter["correct"]
            invalid = counter["invalid"]
            totals.update(counter)
            rows.append(
                {
                    "bucket": bucket,
                    "rows": total_rows,
                    "correct": correct,
                    "accuracy": correct / max(total_rows, 1),
                    "invalid": invalid,
                    "invalid_rate": invalid / max(total_rows, 1),
                }
            )
        condition_summaries[condition] = {
            "rows": totals["rows"],
            "correct": totals["correct"],
            "accuracy": totals["correct"] / max(totals["rows"], 1),
            "invalid": totals["invalid"],
            "invalid_rate": totals["invalid"] / max(totals["rows"], 1),
            "buckets": rows,
        }

    return {
        "missing_bucket_predictions": missing_bucket,
        "conditions": condition_summaries,
    }


def condition_delta(
    summary: dict[str, Any],
    left: str,
    right: str,
    bucket: str | None = None,
) -> float | None:
    """Return accuracy(left) - accuracy(right), optionally inside one bucket."""

    if left not in summary["conditions"] or right not in summary["conditions"]:
        return None
    if bucket is None:
        return summary["conditions"][left]["accuracy"] - summary["conditions"][right]["accuracy"]

    def find_bucket(condition: str) -> dict[str, Any] | None:
        for row in summary["conditions"][condition]["buckets"]:
            if row["bucket"] == bucket:
                return row
        return None

    left_bucket = find_bucket(left)
    right_bucket = find_bucket(right)
    if not left_bucket or not right_bucket:
        return None
    return float(left_bucket["accuracy"]) - float(right_bucket["accuracy"])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["condition", "bucket", "rows", "correct", "accuracy", "invalid", "invalid_rate"],
        )
        writer.writeheader()
        for condition, condition_summary in sorted(summary["conditions"].items()):
            for row in condition_summary["buckets"]:
                writer.writerow({"condition": condition, **row})


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    """Write a defense-readable PX-003/PX-034 bucket accuracy report."""

    rel_vanilla_delta = condition_delta(summary, "relationship_evidence", "vanilla")
    decisive_delta = condition_delta(summary, "relationship_evidence", "vanilla", "DECISIVE")
    lines = [
        "# PX-003/PX-034 Full-Bucket Downstream Accuracy Audit",
        "",
        "Status: **ANALYSIS COMPLETE**",
        "",
        "## Purpose",
        "",
        "This audit implements the reviewer recommendation to test whether the PX-034 source-conflict buckets predict downstream CTI answerability when a model is forced to answer. It joins model predictions to the 500-row source-conflict router table and reports accuracy by bucket.",
        "",
        "## Headline",
        "",
        f"- Relationship-evidence minus vanilla delta, all evaluated rows: `{rel_vanilla_delta:.4f}`." if rel_vanilla_delta is not None else "- Relationship-evidence vs vanilla delta was not available in this prediction set.",
        f"- Relationship-evidence minus vanilla delta on DECISIVE rows: `{decisive_delta:.4f}`." if decisive_delta is not None else "- DECISIVE-bucket relationship-vs-vanilla delta was not available.",
        f"- Predictions without a bucket join: `{summary['missing_bucket_predictions']}`.",
        "",
        "## Per-Condition Bucket Accuracy",
        "",
    ]
    for condition, condition_summary in sorted(summary["conditions"].items()):
        lines.extend(
            [
                f"### `{condition}`",
                "",
                f"Overall accuracy: `{condition_summary['accuracy']:.4f}` over `{condition_summary['rows']}` rows; invalid rate `{condition_summary['invalid_rate']:.4f}`.",
                "",
                "| Bucket | Rows | Accuracy | Correct | Invalid rate |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in condition_summary["buckets"]:
            lines.append(
                f"| `{row['bucket']}` | `{row['rows']}` | `{row['accuracy']:.4f}` | "
                f"`{row['correct']}` | `{row['invalid_rate']:.4f}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "Use this report to decide whether PX-034 is merely a source-support classifier or a real answerability router. A strong router result should show the best direct-answer performance in `DECISIVE` rows and weaker or unstable direct-answer performance in conflicting, ambiguous, weak, or unsupported rows.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket-csv", type=Path, required=True)
    parser.add_argument("--predictions-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    buckets_by_id = read_bucket_rows(args.bucket_csv)
    predictions = read_predictions(args.predictions_jsonl)
    summary = summarize_by_bucket(buckets_by_id, predictions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "cti_bucket_downstream_accuracy.json", summary)
    write_csv(args.output_dir / "cti_bucket_downstream_accuracy.csv", summary)
    write_markdown(args.output_dir / "PX003_PX034_FULL_BUCKET_DOWNSTREAM_ACCURACY_AUDIT.md", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
