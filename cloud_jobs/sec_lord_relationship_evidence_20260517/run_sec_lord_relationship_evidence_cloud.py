from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CONDITIONS = [
    ("vanilla_strict_prompt", "vanilla"),
    ("technique_only_evidence_prompt", "technique_only_evidence"),
    ("relationship_evidence_prompt", "relationship_evidence"),
    ("broad_seed_negative_control_prompt", "broad_seed"),
]


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strict_parse(text: str) -> str:
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


def render_prompt(tokenizer: Any, prompt_text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful cyber threat intelligence analyst. "
                "Return exactly one line in this format: Answer: <A|B|C|D>."
            ),
        },
        {"role": "user", "content": prompt_text},
    ]
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        return messages[0]["content"] + "\n\n" + messages[1]["content"]


def dtype_from_arg(torch: Any, value: str) -> Any:
    value = value.lower()
    if value == "auto":
        return "auto"
    if value == "bfloat16":
        return torch.bfloat16
    if value == "float16":
        return torch.float16
    if value == "float32":
        return torch.float32
    raise ValueError(f"Unsupported dtype: {value}")


def load_model(model_id: str, dtype: str, device_map: str) -> tuple[Any, Any, str]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    token_kwargs = {"token": token} if token else {}
    tokenizer = AutoTokenizer.from_pretrained(model_id, **token_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    use_cuda = bool(torch.cuda.is_available())
    resolved_dtype = dtype_from_arg(torch, dtype)
    model_kwargs: dict[str, Any] = {"torch_dtype": resolved_dtype, **token_kwargs}
    if use_cuda:
        model_kwargs["device_map"] = device_map
    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    if not use_cuda:
        model.to("cpu")
    model.eval()
    return model, tokenizer, "cuda" if use_cuda else "cpu"


def generate_batch(
    model: Any,
    tokenizer: Any,
    prompts: list[str],
    max_input_tokens: int,
    max_new_tokens: int,
) -> list[str]:
    import torch

    encoded = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_input_tokens,
    )
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    input_width = encoded["input_ids"].shape[1]
    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    outputs = []
    for output_ids in generated:
        continuation = output_ids[input_width:]
        outputs.append(tokenizer.decode(continuation, skip_special_tokens=True).strip())
    return outputs


def evaluate_condition(
    condition_key: str,
    condition_name: str,
    rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    batch_size: int,
    max_input_tokens: int,
    max_new_tokens: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    predictions: list[dict[str, Any]] = []
    correct = 0
    invalid = 0
    parsed_counter: Counter[str] = Counter()
    start_time = time.time()

    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        prompts = [render_prompt(tokenizer, str(row[condition_key])) for row in batch]
        outputs = generate_batch(
            model=model,
            tokenizer=tokenizer,
            prompts=prompts,
            max_input_tokens=max_input_tokens,
            max_new_tokens=max_new_tokens,
        )
        for row, prompt, output in zip(batch, prompts, outputs):
            parsed = strict_parse(output)
            expected = str(row["expected_output"]).strip().upper()
            is_correct = parsed == expected
            correct += int(is_correct)
            invalid += int(parsed not in {"A", "B", "C", "D"})
            parsed_counter[parsed or "<invalid>"] += 1
            predictions.append(
                {
                    "condition": condition_name,
                    "condition_key": condition_key,
                    "id": row["id"],
                    "technique_id": row.get("technique_id", ""),
                    "question": row.get("question", ""),
                    "expected_output": expected,
                    "parsed_answer": parsed,
                    "correct": is_correct,
                    "raw_output": output,
                    "prompt": prompt,
                    "source_dataset": row.get("source_dataset", ""),
                    "evidence_pointer_option": row.get("evidence_pointer_option", ""),
                    "option_support_scores": row.get("option_support_scores", {}),
                }
            )

    elapsed = time.time() - start_time
    return (
        {
            "condition": condition_name,
            "condition_key": condition_key,
            "rows": len(rows),
            "correct": correct,
            "accuracy": correct / max(len(rows), 1),
            "invalid": invalid,
            "invalid_rate": invalid / max(len(rows), 1),
            "parsed_distribution": dict(parsed_counter),
            "elapsed_seconds": elapsed,
            "seconds_per_row": elapsed / max(len(rows), 1),
        },
        predictions,
    )


def paired_summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in predictions:
        by_id[row["id"]][row["condition"]] = row

    paired: Counter[str] = Counter()
    usable = 0
    for row_by_condition in by_id.values():
        if not {"vanilla", "relationship_evidence"}.issubset(row_by_condition):
            continue
        usable += 1
        vanilla = bool(row_by_condition["vanilla"]["correct"])
        evidence = bool(row_by_condition["relationship_evidence"]["correct"])
        if vanilla and evidence:
            paired["both_correct"] += 1
        elif vanilla and not evidence:
            paired["vanilla_only"] += 1
        elif evidence and not vanilla:
            paired["evidence_only"] += 1
        else:
            paired["both_wrong"] += 1

    return {
        "rows": usable,
        "both_correct": paired["both_correct"],
        "vanilla_only": paired["vanilla_only"],
        "evidence_only": paired["evidence_only"],
        "both_wrong": paired["both_wrong"],
    }


def decide(summary_by_condition: dict[str, dict[str, Any]], paired: dict[str, Any]) -> dict[str, Any]:
    vanilla = summary_by_condition["vanilla"]
    technique_only = summary_by_condition["technique_only_evidence"]
    evidence = summary_by_condition["relationship_evidence"]
    broad = summary_by_condition["broad_seed"]
    delta = evidence["accuracy"] - vanilla["accuracy"]
    technique_delta = evidence["accuracy"] - technique_only["accuracy"]
    invalid_ok = evidence["invalid_rate"] <= vanilla["invalid_rate"]
    paired_ok = paired["evidence_only"] > paired["vanilla_only"]
    accuracy_ok = delta >= 0.03
    technique_ok = technique_delta >= 0.03
    passed = accuracy_ok and technique_ok and invalid_ok and paired_ok
    if passed:
        status = "PASS - RELATIONSHIP EVIDENCE ABLATION GATE"
        next_step = "Promote as relationship-evidence CTI task compliance after one replication slice or model; keep extraction separate."
    else:
        status = "STOP - RELATIONSHIP EVIDENCE ABLATION GATE FAILED"
        next_step = "Reframe around the winning retrieval condition; do not claim relationship-specific evidence or extraction."
    return {
        "status": status,
        "passed": passed,
        "accuracy_delta_relationship_minus_vanilla": delta,
        "accuracy_delta_relationship_minus_technique_only": technique_delta,
        "accuracy_ok": accuracy_ok,
        "technique_ok": technique_ok,
        "invalid_ok": invalid_ok,
        "paired_ok": paired_ok,
        "technique_only_accuracy": technique_only["accuracy"],
        "broad_seed_accuracy": broad["accuracy"],
        "next_step": next_step,
    }


def render_report(path: Path, payload: dict[str, Any]) -> None:
    decision = payload["decision"]
    lines = [
        "# SEC-LoRD Relationship-Evidence Model Gate",
        "",
        "Generated: 2026-05-17",
        "",
        f"Status: **{decision['status']}**",
        "",
        "## Model",
        "",
        f"- Model: `{payload['model_id']}`",
        f"- Device: `{payload['device']}`",
        f"- Rows: `{payload['rows']}`",
        "",
        "## Strict Scorecard",
        "",
        "| Condition | Accuracy | Correct | Rows | Invalid | Invalid rate | Seconds / row |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["condition_summaries"]:
        lines.append(
            f"| `{row['condition']}` | `{row['accuracy']:.3f}` | `{row['correct']}` | "
            f"`{row['rows']}` | `{row['invalid']}` | `{row['invalid_rate']:.3f}` | "
            f"`{row['seconds_per_row']:.3f}` |"
        )
    paired = payload["paired_summary"]
    lines.extend(
        [
            "",
            "## Paired Vanilla Vs Relationship Evidence",
            "",
            "| Both correct | Vanilla only | Evidence only | Both wrong |",
            "|---:|---:|---:|---:|",
            f"| `{paired['both_correct']}` | `{paired['vanilla_only']}` | `{paired['evidence_only']}` | `{paired['both_wrong']}` |",
            "",
            "## Pass Criteria",
            "",
            f"- Accuracy delta relationship minus vanilla: `{decision['accuracy_delta_relationship_minus_vanilla']:.3f}`; pass = `{decision['accuracy_ok']}`.",
            f"- Accuracy delta relationship minus technique-only: `{decision['accuracy_delta_relationship_minus_technique_only']:.3f}`; pass = `{decision['technique_ok']}`.",
            f"- Relationship invalid rate no worse than vanilla: pass = `{decision['invalid_ok']}`.",
            f"- Evidence-only paired wins exceed vanilla-only wins: pass = `{decision['paired_ok']}`.",
            "- Broad-seed negative control is reported above and cannot be hidden.",
            "",
            "## Decision",
            "",
            decision["next_step"],
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-input-tokens", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--dtype", default="float16", choices=["auto", "bfloat16", "float16", "float32"])
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.input_jsonl, args.limit)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    missing_keys = [
        key
        for key, _ in CONDITIONS
        if any(key not in row or not row[key] for row in rows)
    ]
    if missing_keys:
        raise ValueError(f"Input rows are missing prompt fields: {sorted(set(missing_keys))}")

    if args.dry_run:
        payload = {
            "status": "dry_run_ok",
            "model_id": args.model_id,
            "rows": len(rows),
            "conditions": [name for _, name in CONDITIONS],
            "input_jsonl": str(args.input_jsonl),
        }
        write_json(args.output_dir / "dry_run_summary.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    model, tokenizer, device = load_model(args.model_id, args.dtype, args.device_map)
    condition_summaries: list[dict[str, Any]] = []
    all_predictions: list[dict[str, Any]] = []
    for condition_key, condition_name in CONDITIONS:
        summary, predictions = evaluate_condition(
            condition_key=condition_key,
            condition_name=condition_name,
            rows=rows,
            model=model,
            tokenizer=tokenizer,
            batch_size=args.batch_size,
            max_input_tokens=args.max_input_tokens,
            max_new_tokens=args.max_new_tokens,
        )
        condition_summaries.append(summary)
        all_predictions.extend(predictions)
        with (args.output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
            for pred in all_predictions:
                handle.write(json.dumps(pred, ensure_ascii=True, sort_keys=True) + "\n")

    summary_by_condition = {row["condition"]: row for row in condition_summaries}
    paired = paired_summary(all_predictions)
    decision = decide(summary_by_condition, paired)
    payload = {
        "model_id": args.model_id,
        "device": device,
        "rows": len(rows),
        "input_jsonl": str(args.input_jsonl),
        "condition_summaries": condition_summaries,
        "paired_summary": paired,
        "decision": decision,
    }
    write_json(args.output_dir / "summary.json", payload)
    render_report(args.output_dir / "report.md", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
