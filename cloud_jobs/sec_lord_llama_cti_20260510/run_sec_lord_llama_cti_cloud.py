from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


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
    cleaned = re.sub(r"^assistant\s*[:\n]*", "", text.strip(), flags=re.I).strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return ""
    first_line = lines[0]
    match = re.match(
        r"^(?:answer\s*[:\-]?\s*)?([ABCD])(?:[\).:\s]|$)",
        first_line,
        flags=re.I,
    )
    if match:
        return match.group(1).upper()
    match = re.search(r"\b([ABCD])\b", first_line[:20].upper())
    return match.group(1) if match else ""


def mcq_user_prompt(row: dict[str, Any], seed_terms: list[str] | None = None) -> str:
    seed_prefix = ""
    if seed_terms:
        seed_prefix = (
            "Use cyber threat intelligence and MITRE ATT&CK concepts when helpful. "
            f"Relevant domain terms: {', '.join(seed_terms[:30])}.\n\n"
        )
    options = row["options"]
    return (
        seed_prefix
        + "Choose the best answer. Return only one uppercase letter: A, B, C, or D.\n\n"
        + f"Question: {row['question']}\n"
        + f"A. {options['A']}\n"
        + f"B. {options['B']}\n"
        + f"C. {options['C']}\n"
        + f"D. {options['D']}\n"
        + "Answer:"
    )


def render_prompt(tokenizer: AutoTokenizer, row: dict[str, Any], seed_terms: list[str] | None) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful cyber threat intelligence analyst. "
                "For multiple-choice questions, answer with only A, B, C, or D."
            ),
        },
        {"role": "user", "content": mcq_user_prompt(row, seed_terms)},
    ]
    try:
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        return messages[0]["content"] + "\n\n" + messages[1]["content"]


def generate_batch(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompts: list[str],
    device: torch.device,
) -> list[str]:
    encoded = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1536,
    ).to(device)
    input_lengths = encoded["attention_mask"].sum(dim=1).tolist()
    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            max_new_tokens=8,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    outputs = []
    for row_idx, output_ids in enumerate(generated):
        continuation = output_ids[int(input_lengths[row_idx]) :]
        outputs.append(tokenizer.decode(continuation, skip_special_tokens=True))
    return outputs


def evaluate_condition(
    condition: str,
    rows: list[dict[str, Any]],
    seed_terms: list[str] | None,
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    batch_size: int,
    device: torch.device,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    predictions: list[dict[str, Any]] = []
    correct = 0
    start_time = time.time()
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        prompts = [render_prompt(tokenizer, row, seed_terms) for row in batch]
        outputs = generate_batch(model, tokenizer, prompts, device)
        for row, prompt, output in zip(batch, prompts, outputs):
            parsed = parse_answer(output)
            expected = str(row["expected_output"]).strip().upper()
            is_correct = parsed == expected
            correct += int(is_correct)
            predictions.append(
                {
                    "condition": condition,
                    "id": row["id"],
                    "question": row["question"],
                    "expected_output": expected,
                    "parsed_answer": parsed,
                    "correct": is_correct,
                    "raw_output": output,
                    "prompt": prompt,
                    "source_dataset": row.get("source_dataset"),
                    "url": row.get("url"),
                }
            )
    elapsed = time.time() - start_time
    summary = {
        "condition": condition,
        "rows": len(rows),
        "correct": correct,
        "accuracy": correct / max(len(rows), 1),
        "elapsed_seconds": elapsed,
        "seconds_per_row": elapsed / max(len(rows), 1),
    }
    return summary, predictions


def render_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# SEC-LoRD Llama CTI-MCQ Harness",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        f"Gate result: `{payload['decision']}`",
        "",
        payload["rationale"],
        "",
        "## Model",
        "",
        f"- Model: `{payload['model_id']}`",
        f"- Rows: `{payload['rows']}`",
        f"- Device: `{payload['device']}`",
        "",
        "## Results",
        "",
        "| Condition | Accuracy | Correct | Rows | Seconds / row |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["condition_summaries"]:
        lines.append(
            f"| {row['condition']} | {row['accuracy']:.4f} | {row['correct']} | "
            f"{row['rows']} | {row['seconds_per_row']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            payload["next_gate"],
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="meta-llama/Llama-3.2-3B-Instruct")
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--seed-bank", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(args.input_jsonl, args.limit)
    seed_terms = json.loads(args.seed_bank.read_text(encoding="utf-8"))[
        "domain_seed_terms"
    ]
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required for gated Llama access.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        token=token,
        torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
        device_map="auto" if device.type == "cuda" else None,
    )
    model.eval()

    condition_summaries = []
    all_predictions = []
    for condition, terms in [
        ("vanilla_prompt", None),
        ("domain_seeded_prompt", seed_terms),
    ]:
        summary, predictions = evaluate_condition(
            condition=condition,
            rows=rows,
            seed_terms=terms,
            model=model,
            tokenizer=tokenizer,
            batch_size=args.batch_size,
            device=device,
        )
        condition_summaries.append(summary)
        all_predictions.extend(predictions)

    by_condition = {row["condition"]: row for row in condition_summaries}
    vanilla = by_condition["vanilla_prompt"]["accuracy"]
    seeded = by_condition["domain_seeded_prompt"]["accuracy"]
    delta = seeded - vanilla
    if seeded >= vanilla + 0.03:
        decision = "PROCEED - LLAMA DOMAIN SEEDING POSITIVE"
        rationale = "Domain-seeded prompting improved Llama CTI-MCQ accuracy enough to justify the next extraction gate."
        next_gate = "Proceed to SEC-LoRD extraction protocol design using this model/task pair."
    elif seeded >= vanilla - 0.02:
        decision = "MIXED - LLAMA DOMAIN SEEDING NEUTRAL"
        rationale = "Llama did not show a meaningful domain-seeding gain, but performance did not collapse."
        next_gate = "Do not claim DS-LoRD benefit from prompting alone. Move to true extraction protocol only if the attack objective needs Llama as a victim model."
    else:
        decision = "STOP - LLAMA DOMAIN SEEDING NEGATIVE"
        rationale = "Domain-seeded prompting reduced Llama CTI-MCQ accuracy under this gate."
        next_gate = "Do not proceed to extraction with this prompt strategy. Redesign seeding or task selection first."

    payload = {
        "decision": decision,
        "rationale": rationale,
        "next_gate": next_gate,
        "model_id": args.model_id,
        "rows": len(rows),
        "device": str(device),
        "accuracy_delta_seeded_minus_vanilla": delta,
        "condition_summaries": condition_summaries,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    with (args.output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_predictions:
            handle.write(json.dumps(row) + "\n")
    render_report(args.output_dir / "report.md", payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
