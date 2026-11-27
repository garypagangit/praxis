#!/usr/bin/env python
"""Collect frozen PX-062 skill-name recommendations from open models."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_name(text: str, names: list[str]) -> str | None:
    """Parse only an exact registry name or an explicit abstention.

    Any other first-line response remains a normalized candidate so the
    deterministic existence verifier can reject it. Substring matching is
    intentionally forbidden: a response such as ``pdf-pro`` must never be
    silently converted to the registered name ``pdf``.
    """

    first_line = next(
        (line.strip() for line in text.splitlines() if line.strip()), ""
    )
    stripped = first_line.strip(" `\"'.:")
    normalized = stripped.casefold()
    if normalized in {"", "none", "null", "n/a", "no skill"}:
        return None
    exact = {name.casefold(): name for name in names}
    return exact.get(normalized, normalized)


def validate_source(config: dict, tasks_path: Path, registry_path: Path) -> None:
    expected = config["source_integrity"]
    observed = {
        "tasks_sha256": sha256_file(tasks_path),
        "registry_sha256": sha256_file(registry_path),
    }
    for key, value in observed.items():
        if value != expected[key]:
            raise ValueError(
                f"source integrity failure for {key}: {value} != {expected[key]}"
            )


def runtime_environment(torch) -> dict:
    torch_build = str(torch.__version__)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch_build.split("+", 1)[0],
        "torch_build": torch_build,
        "transformers": __import__("transformers").__version__,
        "accelerate": importlib.metadata.version("accelerate"),
        "safetensors": importlib.metadata.version("safetensors"),
        "sentencepiece": importlib.metadata.version("sentencepiece"),
        "cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "gpu_names": [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ],
    }


def validate_environment(config: dict, environment: dict) -> None:
    for package, expected_version in config["dependency_versions"].items():
        if environment.get(package) != expected_version:
            raise ValueError(
                f"dependency version mismatch for {package}: "
                f"{environment.get(package)} != {expected_version}"
            )


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
    tasks_path = benchmark / "tasks.jsonl"
    registry_path = benchmark / "registry_names.json"
    validate_source(config, tasks_path, registry_path)
    tasks = read_jsonl(tasks_path)
    registry_payload = json.loads(
        registry_path.read_text(encoding="utf-8")
    )
    names = registry_payload["names"]
    if len(tasks) != int(config["expected_tasks"]):
        raise ValueError(f"expected {config['expected_tasks']} tasks, found {len(tasks)}")
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise ValueError("duplicate task_id in frozen benchmark")
    observed_types = {
        task_type: sum(task["task_type"] == task_type for task in tasks)
        for task_type in config["expected_task_type_counts"]
    }
    if observed_types != config["expected_task_type_counts"]:
        raise ValueError(
            "task-type count mismatch: "
            f"{observed_types} != {config['expected_task_type_counts']}"
        )
    environment = runtime_environment(torch)
    validate_environment(config, environment)
    registry_text = ", ".join(names)
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    output_path = out / "model_outputs.jsonl"
    total = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for model_id in config["models"]:
            revision = config["model_revisions"][model_id]
            tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                revision=revision,
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
                        correction = config["correction_prompt_template"].format(
                            candidate=first_name,
                            registry=registry_text,
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
                        "model_revision": revision,
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
        "protocol_version": config["protocol_version"],
        "models": config["models"],
        "model_revisions": config["model_revisions"],
        "conditions": config["conditions"],
        "tasks": len(tasks),
        "outputs": total,
        "expected_outputs": int(config["expected_outputs"]),
        "source_integrity": {
            "config_sha256": sha256_file(config_path),
            "tasks_sha256": sha256_file(tasks_path),
            "registry_sha256": sha256_file(registry_path),
        },
        "environment": environment,
    }
    if total != int(config["expected_outputs"]):
        raise ValueError(
            f"expected {config['expected_outputs']} outputs, collected {total}"
        )
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
