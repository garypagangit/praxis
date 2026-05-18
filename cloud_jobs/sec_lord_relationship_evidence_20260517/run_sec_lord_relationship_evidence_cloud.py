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
    ("relationship_evidence_prompt", "relationship_evidence"),
    ("technique_only_evidence_prompt", "technique_only_evidence"),
    ("random_facts_evidence_prompt", "random_facts"),
    ("empty_evidence_prompt", "empty_evidence"),
    ("broad_seed_negative_control_prompt", "broad_seed"),
]

ORIGINAL_8B_LIFT = 0.2735849056603774


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


def token_count(tokenizer: Any, text: str) -> int:
    if not text:
        return 0
    try:
        return len(tokenizer.encode(text, add_special_tokens=False))
    except Exception:
        return len(re.findall(r"\S+", text))


def evidence_block_text(prompt_text: str) -> str:
    match = re.search(r"Evidence:\n(.*?)\n\nQuestion:", prompt_text, flags=re.S)
    return match.group(1).strip() if match else ""


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
    output_token_counts: list[int] = []
    prompt_token_counts: list[int] = []
    evidence_token_counts: list[int] = []
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
            output_token_counts.append(token_count(tokenizer, output))
            prompt_text = str(row[condition_key])
            prompt_token_counts.append(token_count(tokenizer, prompt_text))
            evidence_token_counts.append(token_count(tokenizer, evidence_block_text(prompt_text)))
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
            "mean_output_tokens": sum(output_token_counts) / max(len(output_token_counts), 1),
            "mean_prompt_tokens": sum(prompt_token_counts) / max(len(prompt_token_counts), 1),
            "mean_evidence_block_tokens": sum(evidence_token_counts)
            / max(len(evidence_token_counts), 1),
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


def pairwise_win_matrix(predictions: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    by_id: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    conditions = sorted({row["condition"] for row in predictions})
    for row in predictions:
        by_id[row["id"]][row["condition"]] = row

    matrix: dict[str, dict[str, int]] = {
        left: {right: 0 for right in conditions} for left in conditions
    }
    for row_by_condition in by_id.values():
        for left in conditions:
            if left not in row_by_condition:
                continue
            left_correct = bool(row_by_condition[left]["correct"])
            for right in conditions:
                if right not in row_by_condition:
                    continue
                right_correct = bool(row_by_condition[right]["correct"])
                if left == right:
                    matrix[left][right] += int(left_correct)
                elif left_correct and not right_correct:
                    matrix[left][right] += 1
    return matrix


def hypothesis_verdict(
    vanilla: dict[str, Any],
    evidence: dict[str, Any],
    technique_only: dict[str, Any] | None,
    random_facts: dict[str, Any] | None,
    empty_evidence: dict[str, Any] | None,
) -> str:
    rel_lift = evidence["accuracy"] - vanilla["accuracy"]
    technique_lift = (
        technique_only["accuracy"] - vanilla["accuracy"] if technique_only else None
    )
    random_lift = random_facts["accuracy"] - vanilla["accuracy"] if random_facts else None
    empty_lift = empty_evidence["accuracy"] - vanilla["accuracy"] if empty_evidence else None

    if (
        technique_lift is not None
        and random_lift is not None
        and empty_lift is not None
        and rel_lift >= 0.20
        and abs(technique_lift) <= 0.05
        and random_lift <= 0.05
        and empty_lift <= 0.05
    ):
        return "H_relationship"
    if (
        technique_lift is not None
        and random_lift is not None
        and empty_lift is not None
        and rel_lift >= 0.15
        and technique_lift >= 0.15
        and abs(evidence["accuracy"] - technique_only["accuracy"]) <= 0.05
        and random_lift <= 0.05
        and empty_lift <= 0.05
    ):
        return "H_specificity"
    if (
        random_lift is not None
        and empty_lift is not None
        and random_lift >= 0.10
        and empty_lift >= 0.10
    ):
        return "H_format"
    return "unclear"


def decide(summary_by_condition: dict[str, dict[str, Any]], paired: dict[str, Any]) -> dict[str, Any]:
    if "vanilla" not in summary_by_condition:
        return {
            "status": "SUMMARY - VANILLA CONDITION NOT RUN",
            "passed": False,
            "next_step": "Run a condition set that includes vanilla before evaluating a gate.",
        }
    if "relationship_evidence" not in summary_by_condition:
        return {
            "status": "SUMMARY - PARTIAL CONDITION RUN",
            "passed": False,
            "next_step": "Partial run recorded. Use this only for the complement-slice vanilla audit or diagnostics.",
        }

    vanilla = summary_by_condition["vanilla"]
    technique_only = summary_by_condition.get("technique_only_evidence")
    random_facts = summary_by_condition.get("random_facts")
    empty_evidence = summary_by_condition.get("empty_evidence")
    evidence = summary_by_condition["relationship_evidence"]
    broad = summary_by_condition.get("broad_seed")
    delta = evidence["accuracy"] - vanilla["accuracy"]
    invalid_ok = evidence["invalid_rate"] <= vanilla["invalid_rate"]
    paired_ok = paired["evidence_only"] > paired["vanilla_only"]
    accuracy_ok = delta >= 0.03

    decision: dict[str, Any] = {
        "status": "SUMMARY - RELATIONSHIP EVIDENCE GATE NOT EVALUATED",
        "passed": False,
        "accuracy_delta_relationship_minus_vanilla": delta,
        "accuracy_ok": accuracy_ok,
        "invalid_ok": invalid_ok,
        "paired_ok": paired_ok,
        "next_step": "",
    }
    if broad:
        decision["broad_seed_accuracy"] = broad["accuracy"]

    if technique_only and random_facts and empty_evidence:
        technique_delta = evidence["accuracy"] - technique_only["accuracy"]
        relationship_lift_reproduced = abs(delta - ORIGINAL_8B_LIFT) <= 0.04
        random_ok = random_facts["accuracy"] <= vanilla["accuracy"] + 0.05
        empty_ok = empty_evidence["accuracy"] <= vanilla["accuracy"] + 0.05
        max_allowed_invalid = evidence["invalid_rate"] + 0.03
        all_invalid_ok = all(
            row["invalid_rate"] <= max_allowed_invalid
            for row in summary_by_condition.values()
        )
        technique_ok = technique_delta >= 0.03
        verdict = hypothesis_verdict(
            vanilla, evidence, technique_only, random_facts, empty_evidence
        )
        passed = (
            relationship_lift_reproduced
            and random_ok
            and empty_ok
            and all_invalid_ok
            and accuracy_ok
            and technique_ok
            and paired_ok
        )
        decision.update(
            {
                "status": (
                    "PASS - RELATIONSHIP EVIDENCE ABLATION GATE"
                    if passed
                    else "STOP - RELATIONSHIP EVIDENCE ABLATION GATE FAILED"
                ),
                "passed": passed,
                "accuracy_delta_relationship_minus_technique_only": technique_delta,
                "technique_only_accuracy": technique_only["accuracy"],
                "random_facts_accuracy": random_facts["accuracy"],
                "empty_evidence_accuracy": empty_evidence["accuracy"],
                "relationship_lift_reproduced": relationship_lift_reproduced,
                "random_ok": random_ok,
                "empty_ok": empty_ok,
                "all_invalid_ok": all_invalid_ok,
                "technique_ok": technique_ok,
                "hypothesis_verdict": verdict,
                "next_step": (
                    "Promote using the hypothesis verdict after the leakage audit and cross-model gate are complete."
                    if passed
                    else "Do not promote the mechanism claim; inspect AB gates and reframe around the winning condition."
                ),
            }
        )
        return decision

    if technique_only:
        technique_delta = evidence["accuracy"] - technique_only["accuracy"]
        technique_ok = technique_delta >= 0.03
        passed = accuracy_ok and technique_ok and invalid_ok and paired_ok
        decision.update(
            {
                "status": (
                    "PASS - RELATIONSHIP EVIDENCE MODEL GATE"
                    if passed
                    else "STOP - RELATIONSHIP EVIDENCE MODEL GATE FAILED"
                ),
                "passed": passed,
                "accuracy_delta_relationship_minus_technique_only": technique_delta,
                "technique_only_accuracy": technique_only["accuracy"],
                "technique_ok": technique_ok,
                "next_step": "Run random-facts and empty-evidence ablations before naming the Praxis mechanism.",
            }
        )
        return decision

    passed = accuracy_ok and invalid_ok and paired_ok
    decision.update(
        {
            "status": (
                "PASS - RELATIONSHIP EVIDENCE MODEL GATE"
                if passed
                else "STOP - RELATIONSHIP EVIDENCE MODEL GATE FAILED"
            ),
            "passed": passed,
            "next_step": "Run technique-only, random-facts, and empty-evidence ablations before naming the Praxis mechanism.",
        }
    )
    return decision


def render_pairwise_markdown(matrix: dict[str, dict[str, int]]) -> list[str]:
    if not matrix:
        return ["No pairwise matrix available."]
    conditions = sorted(matrix)
    lines = [
        "| Condition | " + " | ".join(f"`{condition}`" for condition in conditions) + " |",
        "|---" + "|---:" * len(conditions) + "|",
    ]
    for condition in conditions:
        values = " | ".join(f"`{matrix[condition].get(other, 0)}`" for other in conditions)
        lines.append(f"| `{condition}` | {values} |")
    return lines


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
            f"- Accuracy delta relationship minus vanilla: `{decision.get('accuracy_delta_relationship_minus_vanilla', 0.0):.3f}`; pass = `{decision.get('accuracy_ok', False)}`.",
            f"- Accuracy delta relationship minus technique-only: `{decision.get('accuracy_delta_relationship_minus_technique_only', 0.0):.3f}`; pass = `{decision.get('technique_ok', False)}`.",
            f"- Random-facts negative control pass: `{decision.get('random_ok', 'not_run')}`.",
            f"- Empty-evidence negative control pass: `{decision.get('empty_ok', 'not_run')}`.",
            f"- Relationship invalid rate no worse than vanilla: pass = `{decision.get('invalid_ok', 'not_run')}`.",
            f"- Evidence-only paired wins exceed vanilla-only wins: pass = `{decision.get('paired_ok', 'not_run')}`.",
            "- Broad-seed negative control is reported above and cannot be hidden.",
            f"- Hypothesis verdict: `{decision.get('hypothesis_verdict', 'not_available')}`.",
            "",
            "## Pairwise Win Matrix",
            "",
            "Each cell counts rows where the row condition is correct and the column condition is wrong; diagonal cells are correct counts.",
            "",
            *render_pairwise_markdown(payload.get("pairwise_win_matrix", {})),
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
    parser.add_argument(
        "--conditions",
        default="all",
        help="Comma-separated condition names to run, or 'all'. Valid names: "
        + ", ".join(name for _, name in CONDITIONS),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.input_jsonl, args.limit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    condition_lookup = {name: (key, name) for key, name in CONDITIONS}
    if args.conditions.lower() == "all":
        selected_conditions = CONDITIONS
    else:
        requested = [name.strip() for name in args.conditions.split(",") if name.strip()]
        unknown = [name for name in requested if name not in condition_lookup]
        if unknown:
            raise ValueError(f"Unknown conditions: {unknown}")
        selected_conditions = [condition_lookup[name] for name in requested]

    missing_keys = [
        key
        for key, _ in selected_conditions
        if any(key not in row or not row[key] for row in rows)
    ]
    if missing_keys:
        raise ValueError(f"Input rows are missing prompt fields: {sorted(set(missing_keys))}")

    if args.dry_run:
        payload = {
            "status": "dry_run_ok",
            "model_id": args.model_id,
            "rows": len(rows),
            "conditions": [name for _, name in selected_conditions],
            "input_jsonl": str(args.input_jsonl),
        }
        write_json(args.output_dir / "dry_run_summary.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    model, tokenizer, device = load_model(args.model_id, args.dtype, args.device_map)
    condition_summaries: list[dict[str, Any]] = []
    all_predictions: list[dict[str, Any]] = []
    for condition_key, condition_name in selected_conditions:
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
    pairwise = pairwise_win_matrix(all_predictions)
    payload = {
        "model_id": args.model_id,
        "device": device,
        "rows": len(rows),
        "input_jsonl": str(args.input_jsonl),
        "condition_summaries": condition_summaries,
        "paired_summary": paired,
        "pairwise_win_matrix": pairwise,
        "decision": decision,
    }
    write_json(args.output_dir / "summary.json", payload)
    render_report(args.output_dir / "report.md", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
