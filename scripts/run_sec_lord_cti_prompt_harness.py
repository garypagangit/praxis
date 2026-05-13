from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def clean_answer(value: str) -> str:
    match = re.search(r"[ABCD]", str(value).upper())
    return match.group(0) if match else ""


def overlap_score(question: str, option: str, seed_terms: set[str]) -> float:
    text = f"{question} {option}".lower()
    tokens = set(re.findall(r"[a-z0-9_.-]+", text))
    seed_hits = sum(1 for term in seed_terms if term.lower() in text)
    return float(len(tokens.intersection(seed_terms)) + 2.0 * seed_hits)


def heuristic_answer(
    row: dict[str, Any], seed_terms: list[str], domain_seeded: bool
) -> str:
    question = row["question"]
    options = row["options"]
    if not domain_seeded:
        lengths = {letter: len(str(text)) for letter, text in options.items()}
        return max(lengths.items(), key=lambda item: item[1])[0]

    seed_set = set(re.findall(r"[a-z0-9_.-]+", " ".join(seed_terms).lower()))
    scores = {
        letter: overlap_score(question, str(text), seed_set)
        for letter, text in options.items()
    }
    best_score = max(scores.values())
    if best_score <= 0:
        return heuristic_answer(row, seed_terms, domain_seeded=False)
    return max(scores.items(), key=lambda item: (item[1], len(str(options[item[0]]))))[
        0
    ]


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# SEC-LoRD CTI Prompt Harness",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## Result",
        "",
        "| Condition | Accuracy | Rows |",
        "|---|---:|---:|",
    ]
    for row in summary["conditions"]:
        lines.append(
            f"| `{row['condition']}` | `{row['accuracy']:.4f}` | `{row['rows']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "## Recommendation",
            "",
            summary["recommendation"],
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scaffold-dir",
        type=Path,
        default=Path("runs") / "sec-lord-cti-scaffold-20260509",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "sec-lord-cti-prompt-harness-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports") / "sec_lord_ds_lord" / "CTI_PROMPT_HARNESS_20260509.md",
    )
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    rows = read_jsonl(args.scaffold_dir / "cti_mcq_queries.jsonl", args.limit)
    seed_bank = json.loads(
        (args.scaffold_dir / "domain_seed_bank.json").read_text(encoding="utf-8")
    )
    seed_terms = seed_bank["domain_seed_terms"]

    output_rows: list[dict[str, Any]] = []
    for row in rows:
        gt = clean_answer(row["expected_output"])
        vanilla = heuristic_answer(row, seed_terms, domain_seeded=False)
        seeded = heuristic_answer(row, seed_terms, domain_seeded=True)
        output_rows.append(
            {
                "id": row["id"],
                "gt": gt,
                "vanilla_prediction": vanilla,
                "seeded_prediction": seeded,
                "vanilla_correct": vanilla == gt,
                "seeded_correct": seeded == gt,
                "question": row["question"],
            }
        )

    frame = pd.DataFrame(output_rows)
    vanilla_acc = float(frame["vanilla_correct"].mean())
    seeded_acc = float(frame["seeded_correct"].mean())
    decision = (
        "NEEDS REAL MODEL - HEURISTIC SEEDING NOT SUFFICIENT"
        if seeded_acc <= vanilla_acc + 0.02
        else "PROCEED - SEEDING HEURISTIC SHOWS SIGNAL"
    )
    summary = {
        "decision": decision,
        "conditions": [
            {
                "condition": "vanilla_length_heuristic",
                "accuracy": vanilla_acc,
                "rows": int(len(frame)),
            },
            {
                "condition": "domain_seed_overlap_heuristic",
                "accuracy": seeded_acc,
                "rows": int(len(frame)),
            },
        ],
        "delta_seeded_vs_vanilla": seeded_acc - vanilla_acc,
        "interpretation": (
            "This harness validates the CTI-MCQ scoring path, but the heuristic prompt substitute is not enough to establish DS-LoRD value."
            if seeded_acc <= vanilla_acc + 0.02
            else "The domain seed bank changes answer selection enough to justify a real model run."
        ),
        "recommendation": "Run the same harness with an actual small instruct model, then with approved Llama, before attempting extraction.",
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out_dir / "predictions.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
