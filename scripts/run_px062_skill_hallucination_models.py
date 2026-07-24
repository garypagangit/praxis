#!/usr/bin/env python
"""Collect frozen PX-062 skill-name recommendations from open models."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def extract_name(text: str, names: list[str]) -> str | None:
    stripped = text.strip().splitlines()[0].strip(" `\"'.:") if text.strip() else ""
    if stripped.lower() in {"none", "null", "n/a", "no skill"}:
        return None
    lower = text.lower()
    matches = [name for name in names if name.lower() in lower]
    if len(matches) == 1:
        return matches[0]
    return stripped.lower() or None


def generate(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    import torch

    messages = [
        {
            "role": "system",
            "content": (
                "You select agent skills. Follow the requested output format. "
                "Never fabricate registry evidence."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0, inputs["input_ids"].shape[1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def run(config_path: Path) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    config = json.loads(config_path.read_text(encoding="utf-8"))
    benchmark = Path(config["benchmark_dir"])
    tasks = read_jsonl(benchmark / "tasks.jsonl")
    registry_payload = json.loads(
        (benchmark / "registry_names.json").read_text(encoding="utf-8")
    )
    names = registry_payload["names"]
    registry_text = ", ".join(names)
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    output_path = out / "model_outputs.jsonl"
    total = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for model_id in config["models"]:
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16,
                device_map="auto",
            )
            model.eval()
            for condition in config["conditions"]:
                for task in tasks:
                    prompt = task["prompt"]
                    if condition == "registry_constrained":
                        prompt += (
                            "\nThe complete frozen registry is: "
                            + registry_text
                            + "\nChoose only from this list or return NONE."
                        )
                    first = generate(
                        tokenizer, model, prompt, int(config["max_new_tokens"])
                    )
                    first_name = extract_name(first, names)
                    final = first
                    final_name = first_name
                    verifier_rejected = bool(
                        first_name is not None and first_name not in names
                    )
                    if condition == "post_generation_verification" and verifier_rejected:
                        correction = (
                            f"Your proposed skill '{first_name}' does not exist in the "
                            "frozen registry. Choose an exact name from this complete "
                            f"registry or return NONE: {registry_text}"
                        )
                        final = generate(
                            tokenizer,
                            model,
                            correction,
                            int(config["max_new_tokens"]),
                        )
                        final_name = extract_name(final, names)
                    row = {
                        "task_id": task["task_id"],
                        "model_id": model_id,
                        "condition": condition,
                        "raw_response": final,
                        "initial_response": first,
                        "initial_recommended_skill": first_name,
                        "verifier_rejected_initial": verifier_rejected,
                        "recommended_skill": final_name,
                        "attempted_load": final_name is not None,
                    }
                    handle.write(json.dumps(row) + "\n")
                    handle.flush()
                    total += 1
            del model
            del tokenizer
            gc.collect()
            torch.cuda.empty_cache()
    summary = {
        "experiment_id": config["experiment_id"],
        "models": config["models"],
        "conditions": config["conditions"],
        "tasks": len(tasks),
        "outputs": total,
    }
    (out / "collection_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
