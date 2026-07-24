#!/usr/bin/env python
"""Collect iterative answer traces for PX-057 and score them for stopping replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_px057_adaptive_stopping_gate import Trace, evaluate, gate_decision, load_traces


NUMBER_RE = re.compile(r"[-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def normalize_numeric(value: str) -> str:
    value = value.replace(",", "").strip()
    try:
        number = float(value)
    except ValueError:
        return value.lower()
    if number.is_integer():
        return str(int(number))
    return f"{number:.10g}"


def extract_numeric_answer(text: str) -> str:
    boxed = re.findall(r"\\boxed\{([^{}]+)\}", text)
    if boxed:
        candidates = NUMBER_RE.findall(boxed[-1])
        if candidates:
            return normalize_numeric(candidates[-1])
    explicit = re.findall(
        r"(?:final answer|answer)\s*(?:is|:|=)\s*([-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)",
        text,
        flags=re.I,
    )
    if explicit:
        return normalize_numeric(explicit[-1])
    candidates = NUMBER_RE.findall(text)
    return normalize_numeric(candidates[-1]) if candidates else ""


def parse_gsm8k_gold(answer: str) -> str:
    marker = answer.rsplit("####", 1)
    if len(marker) != 2:
        raise ValueError("GSM8K answer lacks #### marker")
    return normalize_numeric(marker[1])


def download_dataset(url: str, output_dir: Path) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "gsm8k_test_source.jsonl"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    content = response.content
    digest = hashlib.sha256(content).hexdigest()
    target.write_bytes(content)
    return target, digest


def select_rows(path: Path, sample_size: int, seed: int) -> list[dict[str, str]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    rng = random.Random(seed)
    indices = sorted(rng.sample(range(len(rows)), sample_size))
    return [
        {
            "question_id": f"gsm8k-test-{index}",
            "question": rows[index]["question"],
            "gold_answer": parse_gsm8k_gold(rows[index]["answer"]),
            "source_index": index,
        }
        for index in indices
    ]


def build_prompt(question: str, previous: str | None, round_index: int) -> str:
    if previous is None:
        return (
            "Solve the arithmetic word problem carefully. End with exactly "
            "'Final answer: <number>'.\n\nProblem: "
            + question
        )
    return (
        "Reconsider the problem independently. Check the previous proposed solution "
        "for arithmetic or reasoning mistakes. You may keep or change the answer. "
        "End with exactly 'Final answer: <number>'.\n\nProblem: "
        + question
        + "\n\nPrevious proposed solution:\n"
        + previous
        + f"\n\nReconsideration round: {round_index}"
    )


def load_backend(
    model_id: str,
    local_files_only: bool,
    model_type: str,
    device_map: str | None,
) -> tuple[Any, Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_id, local_files_only=local_files_only
    )
    model_class = (
        AutoModelForCausalLM if model_type == "causal" else AutoModelForSeq2SeqLM
    )
    kwargs: dict[str, Any] = {"local_files_only": local_files_only}
    if device_map:
        kwargs["device_map"] = device_map
        kwargs["torch_dtype"] = "auto"
    model = model_class.from_pretrained(model_id, **kwargs)
    model.eval()
    return torch, tokenizer, model


def generate_one(
    torch: Any,
    tokenizer: Any,
    model: Any,
    prompt: str,
    max_new_tokens: int,
    model_type: str,
) -> tuple[str, float, int]:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    if hasattr(model, "device"):
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            return_dict_in_generate=True,
            output_scores=True,
        )
    sequence = output.sequences[0]
    prompt_tokens = int(inputs["input_ids"].shape[1]) if model_type == "causal" else 0
    generated = sequence[prompt_tokens:]
    text = tokenizer.decode(generated, skip_special_tokens=True)
    transition = model.compute_transition_scores(
        output.sequences, output.scores, normalize_logits=True
    )[0]
    finite = transition[torch.isfinite(transition)]
    mean_logprob = float(finite.mean().item()) if len(finite) else -100.0
    confidence = float(math.exp(max(-20.0, min(0.0, mean_logprob))))
    generated_tokens = int(len(generated))
    return text, confidence, generated_tokens


def collect(config: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(config["output_dir"])
    source_path, digest = download_dataset(config["dataset_url"], output_dir)
    expected = config.get("dataset_sha256")
    if expected and digest != expected:
        raise ValueError(f"dataset SHA-256 mismatch: {digest} != {expected}")
    selected = select_rows(source_path, config["sample_size"], config["sample_seed"])
    (output_dir / "selected_rows.json").write_text(
        json.dumps(selected, indent=2), encoding="utf-8"
    )
    torch, tokenizer, model = load_backend(
        config["model_id"],
        bool(config.get("local_files_only")),
        str(config.get("model_type", "seq2seq")),
        config.get("device_map"),
    )
    trace_path = Path(config["trace_jsonl"])
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    raw_rows = []
    with trace_path.open("w", encoding="utf-8") as trace_handle:
        for row in selected:
            steps = []
            previous = None
            cumulative_tokens = 0
            for round_index in range(1, int(config["rounds"]) + 1):
                prompt = build_prompt(row["question"], previous, round_index)
                response, confidence, tokens = generate_one(
                    torch,
                    tokenizer,
                    model,
                    prompt,
                    int(config["max_new_tokens"]),
                    str(config.get("model_type", "seq2seq")),
                )
                answer = extract_numeric_answer(response)
                cumulative_tokens += tokens
                steps.append(
                    {
                        "step": round_index,
                        "answer": answer,
                        "correct": answer == row["gold_answer"],
                        "confidence": confidence,
                        "tokens": cumulative_tokens,
                    }
                )
                raw_rows.append(
                    {
                        "question_id": row["question_id"],
                        "round": round_index,
                        "prompt": prompt,
                        "response": response,
                        "extracted_answer": answer,
                        "gold_answer": row["gold_answer"],
                        "correct": answer == row["gold_answer"],
                        "confidence": confidence,
                        "generated_tokens": tokens,
                    }
                )
                previous = response
            trace_handle.write(
                json.dumps(
                    {
                        "question_id": row["question_id"],
                        "domain": "gsm8k",
                        "steps": steps,
                    }
                )
                + "\n"
            )
    with (output_dir / "raw_generations.jsonl").open("w", encoding="utf-8") as handle:
        for row in raw_rows:
            handle.write(json.dumps(row) + "\n")

    traces = load_traces(trace_path)
    summary = evaluate(traces, **config["evaluation_config"])
    decisions = (
        gate_decision(summary, config["gates"])
        if "gates" in config
        else None
    )
    result = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "model_id": config["model_id"],
        "dataset_sha256": digest,
        "sample_size": config["sample_size"],
        "rounds": config["rounds"],
        "claim_boundary": config["claim_boundary"],
        "metrics": {key: value for key, value in summary.items() if key != "rows"},
        "gate_decisions": decisions,
        "gate_pass": None if decisions is None else all(decisions.values()),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px057_adaptive_stopping_gate1_local_pilot_20260723.json"),
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(collect(config), indent=2))


if __name__ == "__main__":
    main()
