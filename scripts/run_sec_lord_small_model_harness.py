from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


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


def parse_answer(text: str) -> str:
    match = re.search(r"\b([ABCD])\b", text.upper())
    if match:
        return match.group(1)
    match = re.search(r"[ABCD]", text.upper())
    return match.group(0) if match else ""


def build_prompt(row: dict[str, Any], seed_terms: list[str] | None = None) -> str:
    seed_prefix = ""
    if seed_terms:
        seed_prefix = (
            "Use cyber threat intelligence concepts when helpful. "
            f"Relevant domain terms: {', '.join(seed_terms[:25])}.\n\n"
        )
    options = row["options"]
    return (
        seed_prefix
        + "Answer the CTI multiple-choice question. Return only A, B, C, or D.\n\n"
        + f"Question: {row['question']}\n"
        + f"A. {options['A']}\n"
        + f"B. {options['B']}\n"
        + f"C. {options['C']}\n"
        + f"D. {options['D']}\n"
        + "Answer:"
    )


def generate_answers(
    model: AutoModelForSeq2SeqLM,
    tokenizer: AutoTokenizer,
    prompts: list[str],
    batch_size: int,
) -> list[str]:
    outputs: list[str] = []
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        encoded = tokenizer(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=1024
        )
        with torch.no_grad():
            generated = model.generate(
                **encoded,
                max_new_tokens=4,
                do_sample=False,
            )
        outputs.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    return outputs


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# SEC-LoRD Small-Model CTI Harness",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        f"Model: `{summary['model']}`",
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
    lines.extend(["", "## Recommendation", "", summary["recommendation"]])
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
        default=Path("runs") / "sec-lord-small-model-harness-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "sec_lord_ds_lord"
        / "SMALL_MODEL_CTI_HARNESS_20260509.md",
    )
    parser.add_argument("--model", default="google/flan-t5-small")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    rows = read_jsonl(args.scaffold_dir / "cti_mcq_queries.jsonl", args.limit)
    seed_bank = json.loads(
        (args.scaffold_dir / "domain_seed_bank.json").read_text(encoding="utf-8")
    )
    seed_terms = seed_bank["domain_seed_terms"]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    model.eval()

    vanilla_prompts = [build_prompt(row) for row in rows]
    seeded_prompts = [build_prompt(row, seed_terms) for row in rows]
    vanilla_outputs = generate_answers(
        model, tokenizer, vanilla_prompts, args.batch_size
    )
    seeded_outputs = generate_answers(model, tokenizer, seeded_prompts, args.batch_size)

    pred_rows = []
    for row, vanilla, seeded in zip(rows, vanilla_outputs, seeded_outputs):
        gt = parse_answer(str(row["expected_output"]))
        vanilla_pred = parse_answer(vanilla)
        seeded_pred = parse_answer(seeded)
        pred_rows.append(
            {
                "id": row["id"],
                "gt": gt,
                "vanilla_output": vanilla,
                "vanilla_prediction": vanilla_pred,
                "seeded_output": seeded,
                "seeded_prediction": seeded_pred,
                "vanilla_correct": vanilla_pred == gt,
                "seeded_correct": seeded_pred == gt,
                "question": row["question"],
            }
        )
    frame = pd.DataFrame(pred_rows)
    vanilla_acc = float(frame["vanilla_correct"].mean())
    seeded_acc = float(frame["seeded_correct"].mean())
    decision = (
        "PROCEED - DOMAIN SEEDING IMPROVES SMALL MODEL"
        if seeded_acc >= vanilla_acc + 0.03
        else "NO SMALL-MODEL SEEDING SIGNAL"
    )
    summary = {
        "decision": decision,
        "model": args.model,
        "conditions": [
            {
                "condition": "vanilla_prompt",
                "accuracy": vanilla_acc,
                "rows": int(len(frame)),
            },
            {
                "condition": "domain_seeded_prompt",
                "accuracy": seeded_acc,
                "rows": int(len(frame)),
            },
        ],
        "delta_seeded_vs_vanilla": seeded_acc - vanilla_acc,
        "recommendation": (
            "Run the approved Llama model next and compare against this small-model baseline."
            if seeded_acc >= vanilla_acc + 0.03
            else "Do not claim DS-LoRD benefit from prompting alone; move to approved Llama or true extraction protocol."
        ),
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
