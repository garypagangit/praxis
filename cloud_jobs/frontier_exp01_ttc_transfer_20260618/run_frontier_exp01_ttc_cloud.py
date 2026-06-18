from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_SERVER = "https://datasets-server.huggingface.co"
DATASET_ADAPTERS: dict[str, dict[str, str]] = {
    "gsm8k": {
        "hf_dataset": "openai/gsm8k",
        "hf_config": "main",
        "hf_split": "test",
        "problem_field": "question",
        "answer_field": "answer",
    },
    "math500": {
        "hf_dataset": "HuggingFaceH4/MATH-500",
        "hf_config": "default",
        "hf_split": "test",
        "problem_field": "problem",
        "answer_field": "answer",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def request_json(path: str, params: dict[str, Any], retries: int = 5) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{DATASET_SERVER}/{path}?{query}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = int(retry_after)
                elif exc.code == 429:
                    delay = 20 * attempt
                else:
                    delay = 3 * attempt
                time.sleep(delay)
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt < retries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_error}")


def fetch_row_page(adapter: dict[str, str], offset: int, length: int = 100) -> dict[int, dict[str, Any]]:
    data = request_json(
        "rows",
        {
            "dataset": adapter["hf_dataset"],
            "config": adapter["hf_config"],
            "split": adapter["hf_split"],
            "offset": offset,
            "length": length,
        },
    )
    return {int(item["row_idx"]): item["row"] for item in data.get("rows", [])}


def get_total_rows(adapter: dict[str, str]) -> int:
    data = request_json(
        "rows",
        {
            "dataset": adapter["hf_dataset"],
            "config": adapter["hf_config"],
            "split": adapter["hf_split"],
            "offset": 0,
            "length": 1,
        },
    )
    total = data.get("num_rows_total")
    if not isinstance(total, int):
        raise RuntimeError(f"num_rows_total missing for {adapter['hf_dataset']}")
    return total


def sample_indices(total_rows: int, sample_size: int, seed: int, key: str) -> list[int]:
    rng = random.Random(f"{seed}:{key}")
    return sorted(rng.sample(range(total_rows), sample_size))


def fetch_selected_rows(adapter: dict[str, str], indices: list[int]) -> dict[int, dict[str, Any]]:
    selected = set(indices)
    rows: dict[int, dict[str, Any]] = {}
    page_starts = sorted({(idx // 100) * 100 for idx in indices})
    for page_start in page_starts:
        page = fetch_row_page(adapter, page_start, 100)
        for idx in selected:
            if idx in page:
                rows[idx] = page[idx]
    missing = sorted(selected - set(rows))
    if missing:
        raise RuntimeError(f"missing selected row indices for {adapter['hf_dataset']}: {missing}")
    return rows


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_answer(dataset_name: str, raw_answer: str) -> str:
    text = str(raw_answer).strip()
    if dataset_name == "gsm8k" and "####" in text:
        text = text.rsplit("####", 1)[-1].strip()
    text = re.sub(r"\\boxed\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", text)
    text = text.replace("$", "").replace("\\,", "")
    text = text.replace(",", "")
    text = text.strip().strip(".\u3002")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def extract_final_answer(text: str) -> str:
    cleaned = str(text).strip()
    patterns = [
        r"final\s+answer\s*[:\uFF1A]\s*([^\n]+)",
        r"answer\s*[:\uFF1A]\s*([^\n]+)",
        r"\\boxed\s*\{([^{}]+)\}",
        r"####\s*([^\n]+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, cleaned, flags=re.I)
        if matches:
            return str(matches[-1]).strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if lines:
        return lines[-1][:160].strip()
    return cleaned[:160].strip()


def assign_role(dataset_name: str, position: int, count: int) -> str:
    if dataset_name == "math500":
        return "strict_domain_holdout_test"
    split_at = count // 2
    return "validation_policy_selection" if position < split_at else "test_in_domain"


def build_rows(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    seed = int(config["splits"]["split_seed"])
    problem_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    for spec in config["datasets"]:
        dataset_name = spec["name"]
        adapter = DATASET_ADAPTERS[dataset_name]
        total_rows = get_total_rows(adapter)
        totals[dataset_name] = total_rows
        indices = sample_indices(total_rows, int(spec["sample_size"]), seed, dataset_name)
        fetched = fetch_selected_rows(adapter, indices)
        for position, row_idx in enumerate(indices):
            raw = fetched[row_idx]
            problem = str(raw[adapter["problem_field"]])
            answer = str(raw[adapter["answer_field"]])
            normalized = normalize_answer(dataset_name, answer)
            row_key = f"{dataset_name}:{adapter['hf_split']}:{row_idx}"
            split_role = assign_role(dataset_name, position, len(indices))
            problem_rows.append(
                {
                    "row_key": row_key,
                    "dataset": dataset_name,
                    "hf_dataset": adapter["hf_dataset"],
                    "hf_config": adapter["hf_config"],
                    "hf_split": adapter["hf_split"],
                    "row_idx": row_idx,
                    "split_role": split_role,
                    "problem": problem,
                    "problem_text_sha256": sha256_text(problem),
                    "gold_answer_sha256": sha256_text(normalized),
                    "problem_length_chars": len(problem),
                }
            )
            label_rows.append(
                {
                    "row_key": row_key,
                    "dataset": dataset_name,
                    "split_role": split_role,
                    "gold_answer_normalized": normalized,
                    "gold_answer_sha256": sha256_text(normalized),
                }
            )
    problem_rows.sort(key=lambda item: (item["split_role"], item["dataset"], item["row_idx"]))
    label_rows.sort(key=lambda item: item["row_key"])
    return problem_rows, label_rows, totals


def render_prompt(tokenizer: Any, problem: str, dataset: str) -> str:
    user_text = (
        "Solve the following problem. Keep the reasoning concise. "
        "Return the final answer on the last line exactly as: Final answer: <answer>.\n\n"
        f"Dataset: {dataset}\nProblem:\n{problem}"
    )
    messages = [
        {"role": "system", "content": "You are a careful mathematical reasoning assistant."},
        {"role": "user", "content": user_text},
    ]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        return messages[0]["content"] + "\n\n" + messages[1]["content"] + "\n\nAssistant:"


def load_model(model_id: str, dtype: str, device_map: str) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    token_kwargs = {"token": token} if token else {}
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, **token_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    dtype_map = {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
        "auto": "auto",
    }
    model_kwargs: dict[str, Any] = {
        "torch_dtype": dtype_map.get(dtype, torch.float16),
        "trust_remote_code": True,
        **token_kwargs,
    }
    if torch.cuda.is_available():
        model_kwargs["device_map"] = device_map
    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    if not torch.cuda.is_available():
        model.to("cpu")
    model.eval()
    return model, tokenizer


def token_count(tokenizer: Any, text: str) -> int:
    try:
        return len(tokenizer.encode(text, add_special_tokens=False))
    except Exception:
        return len(re.findall(r"\S+", text))


def generate_outputs(
    model: Any,
    tokenizer: Any,
    prompts: list[str],
    max_input_tokens: int,
    max_new_tokens: int,
    do_sample: bool,
    temperature: float,
    top_p: float,
    num_return_sequences: int = 1,
) -> list[list[str]]:
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
    generation_kwargs = {
        **encoded,
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "pad_token_id": tokenizer.eos_token_id,
        "num_return_sequences": num_return_sequences,
    }
    if do_sample:
        generation_kwargs["temperature"] = temperature
        generation_kwargs["top_p"] = top_p
    with torch.inference_mode():
        generated = model.generate(**generation_kwargs)
    decoded = []
    for output_ids in generated:
        continuation = output_ids[input_width:]
        decoded.append(tokenizer.decode(continuation, skip_special_tokens=True).strip())
    grouped: list[list[str]] = []
    if num_return_sequences == 1:
        grouped = [[text] for text in decoded]
    else:
        for idx in range(0, len(decoded), num_return_sequences):
            grouped.append(decoded[idx : idx + num_return_sequences])
    return grouped


def majority_vote(answers: list[str]) -> tuple[str, float, float, int]:
    nonempty = [answer for answer in answers if answer]
    if not nonempty:
        return "", 0.0, 0.0, 0
    counts = Counter(nonempty)
    selected, top_count = counts.most_common(1)[0]
    total = len(nonempty)
    probs = [count / total for count in counts.values()]
    entropy = -sum(prob * math.log(prob + 1e-12) for prob in probs)
    sorted_counts = counts.most_common()
    if len(sorted_counts) == 1:
        margin = 1.0
    else:
        margin = (sorted_counts[0][1] - sorted_counts[1][1]) / total
    return selected, entropy, margin, len(counts)


def evaluate_model(
    model_spec: dict[str, Any],
    config: dict[str, Any],
    problem_rows: list[dict[str, Any]],
    labels_by_key: dict[str, str],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    import torch

    generation_cfg = config["generation"]
    model_id = model_spec["hf_model_id"]
    model_name = model_spec["id"]
    print(f"Loading model {model_name}: {model_id}", flush=True)
    model, tokenizer = load_model(
        model_id=model_id,
        dtype=str(generation_cfg.get("dtype", "float16")),
        device_map=str(generation_cfg.get("device_map", "auto")),
    )
    prompts = [render_prompt(tokenizer, row["problem"], row["dataset"]) for row in problem_rows]
    prompt_tokens = [token_count(tokenizer, prompt) for prompt in prompts]
    max_input_tokens = int(generation_cfg["max_input_tokens"])
    max_new_tokens = int(generation_cfg["max_new_tokens"])
    batch_size = int(generation_cfg["batch_size"])
    sample_batch_size = int(generation_cfg.get("sample_batch_size", 1))
    max_k = int(config["sample_pool"]["max_k"])
    seed = int(generation_cfg["generation_seed"])
    temperature = float(generation_cfg["temperature"])
    top_p = float(generation_cfg["top_p"])

    raw_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []

    print(f"Generating greedy outputs for {model_name}", flush=True)
    greedy_outputs: list[list[str]] = []
    start_time = time.time()
    for start in range(0, len(prompts), batch_size):
        grouped = generate_outputs(
            model,
            tokenizer,
            prompts[start : start + batch_size],
            max_input_tokens,
            max_new_tokens,
            do_sample=False,
            temperature=temperature,
            top_p=top_p,
            num_return_sequences=1,
        )
        greedy_outputs.extend(grouped)
    greedy_elapsed = time.time() - start_time

    print(f"Generating sample pools for {model_name}", flush=True)
    sample_outputs: list[list[str]] = []
    start_time = time.time()
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    for start in range(0, len(prompts), sample_batch_size):
        grouped = generate_outputs(
            model,
            tokenizer,
            prompts[start : start + sample_batch_size],
            max_input_tokens,
            max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            num_return_sequences=max_k,
        )
        sample_outputs.extend(grouped)
    sample_elapsed = time.time() - start_time

    for idx, row in enumerate(problem_rows):
        row_key = row["row_key"]
        gold = labels_by_key[row_key]
        greedy_text = greedy_outputs[idx][0]
        greedy_raw = extract_final_answer(greedy_text)
        greedy_norm = normalize_answer(row["dataset"], greedy_raw)
        sample_texts = sample_outputs[idx]
        sample_raw_answers = [extract_final_answer(text) for text in sample_texts]
        sample_norm_answers = [normalize_answer(row["dataset"], answer) for answer in sample_raw_answers]
        sample_token_counts = [token_count(tokenizer, text) for text in sample_texts]
        raw_rows.append(
            {
                "row_key": row_key,
                "dataset": row["dataset"],
                "split_role": row["split_role"],
                "model": model_name,
                "hf_model_id": model_id,
                "prompt_tokens": prompt_tokens[idx],
                "greedy_output": greedy_text,
                "greedy_answer_raw": greedy_raw,
                "greedy_answer_normalized": greedy_norm,
                "sample_outputs": sample_texts,
                "sample_answer_raw": sample_raw_answers,
                "sample_answer_normalized": sample_norm_answers,
                "sample_output_tokens": sample_token_counts,
            }
        )
        score_rows.append(
            {
                "row_key": row_key,
                "dataset": row["dataset"],
                "split_role": row["split_role"],
                "model": model_name,
                "strategy": "single_sample",
                "budget_k": 1,
                "selected_answer_normalized": greedy_norm,
                "gold_answer_normalized": gold,
                "is_correct": greedy_norm == gold,
                "tokens_used": prompt_tokens[idx] + token_count(tokenizer, greedy_text),
                "wall_time_seconds": greedy_elapsed / max(len(problem_rows), 1),
                "answer_entropy": 0.0,
                "self_consistency_margin": 1.0,
                "unique_answer_rate": 1.0,
            }
        )
        for k in [2, 4, 8]:
            answers_k = sample_norm_answers[:k]
            selected, entropy, margin, unique_count = majority_vote(answers_k)
            score_rows.append(
                {
                    "row_key": row_key,
                    "dataset": row["dataset"],
                    "split_role": row["split_role"],
                    "model": model_name,
                    "strategy": "majority_vote",
                    "budget_k": k,
                    "selected_answer_normalized": selected,
                    "gold_answer_normalized": gold,
                    "is_correct": selected == gold,
                    "tokens_used": prompt_tokens[idx] * k + sum(sample_token_counts[:k]),
                    "wall_time_seconds": sample_elapsed * (k / max_k) / max(len(problem_rows), 1),
                    "answer_entropy": entropy,
                    "self_consistency_margin": margin,
                    "unique_answer_rate": unique_count / max(k, 1),
                }
            )
        diagnostic_rows.append(
            {
                "row_key": row_key,
                "dataset": row["dataset"],
                "split_role": row["split_role"],
                "model": model_name,
                "greedy_correct": greedy_norm == gold,
                "sample_pool_contains_correct": gold in sample_norm_answers,
                "sample_pool_unique_answers": len(set(answer for answer in sample_norm_answers if answer)),
                "sample_pool_entropy": majority_vote(sample_norm_answers)[1],
                "prompt_tokens": prompt_tokens[idx],
            }
        )

    del model
    del tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    write_jsonl(output_dir / f"raw_generations_{model_name}.jsonl", raw_rows)
    write_jsonl(output_dir / f"scores_{model_name}.jsonl", score_rows)
    write_jsonl(output_dir / f"diagnostics_{model_name}.jsonl", diagnostic_rows)
    return raw_rows, score_rows, diagnostic_rows


def summarize_scores(score_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        key = (row["model"], row["strategy"], int(row["budget_k"]), row["dataset"], row["split_role"])
        grouped[key].append(row)
    summary = []
    for (model, strategy, budget_k, dataset, split_role), rows in sorted(grouped.items()):
        correct = sum(1 for row in rows if row["is_correct"])
        summary.append(
            {
                "model": model,
                "strategy": strategy,
                "budget_k": budget_k,
                "dataset": dataset,
                "split_role": split_role,
                "rows": len(rows),
                "correct": correct,
                "accuracy": correct / max(len(rows), 1),
                "mean_tokens_used": statistics.fmean(float(row["tokens_used"]) for row in rows),
                "mean_answer_entropy": statistics.fmean(float(row["answer_entropy"]) for row in rows),
                "mean_self_consistency_margin": statistics.fmean(
                    float(row["self_consistency_margin"]) for row in rows
                ),
                "mean_unique_answer_rate": statistics.fmean(float(row["unique_answer_rate"]) for row in rows),
            }
        )
    return summary


def choose_policy(summary_rows: list[dict[str, Any]], model: str) -> dict[str, Any]:
    candidates = [
        row
        for row in summary_rows
        if row["model"] == model and row["split_role"] == "validation_policy_selection"
    ]
    if not candidates:
        raise RuntimeError(f"No validation candidates for model {model}")
    return max(candidates, key=lambda row: (row["accuracy"], -int(row["budget_k"]), row["strategy"]))


def summary_lookup(summary_rows: list[dict[str, Any]]) -> dict[tuple[str, str, int, str], dict[str, Any]]:
    lookup = {}
    for row in summary_rows:
        key = (row["model"], row["strategy"], int(row["budget_k"]), row["split_role"])
        lookup[key] = row
    return lookup


def compute_transfer(
    summary_rows: list[dict[str, Any]], models: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lookup = summary_lookup(summary_rows)
    model_ids = [model["id"] for model in models]
    policies = {model_id: choose_policy(summary_rows, model_id) for model_id in model_ids}
    policy_rows = [
        {
            "model": model,
            "selected_strategy": policy["strategy"],
            "selected_budget_k": policy["budget_k"],
            "validation_accuracy": policy["accuracy"],
        }
        for model, policy in policies.items()
    ]
    transfer_rows: list[dict[str, Any]] = []
    for source in model_ids:
        source_policy = policies[source]
        for target in model_ids:
            target_policy = policies[target]
            for role in ["test_in_domain", "strict_domain_holdout_test"]:
                source_on_target = lookup.get(
                    (target, source_policy["strategy"], int(source_policy["budget_k"]), role)
                )
                target_optimal = lookup.get(
                    (target, target_policy["strategy"], int(target_policy["budget_k"]), role)
                )
                if not source_on_target or not target_optimal:
                    continue
                denom = float(target_optimal["accuracy"])
                retention = float(source_on_target["accuracy"]) / denom if denom > 0 else None
                transfer_rows.append(
                    {
                        "source_model": source,
                        "target_model": target,
                        "evaluation_role": role,
                        "source_strategy": source_policy["strategy"],
                        "source_budget_k": source_policy["budget_k"],
                        "target_optimal_strategy": target_policy["strategy"],
                        "target_optimal_budget_k": target_policy["budget_k"],
                        "source_policy_accuracy_on_target": source_on_target["accuracy"],
                        "target_optimal_accuracy": target_optimal["accuracy"],
                        "retention": retention,
                        "target_rows": source_on_target["rows"],
                    }
                )
    return policy_rows, transfer_rows


def bootstrap_ci(values: list[bool], samples: int = 1000, seed: int = 13) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    means = []
    n = len(values)
    for _ in range(samples):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(draw) / n)
    means.sort()
    mean = sum(values) / n
    return mean, means[int(0.025 * samples)], means[int(0.975 * samples) - 1]


def run_predictor_analysis(
    summary_rows: list[dict[str, Any]],
    transfer_rows: list[dict[str, Any]],
    models: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    model_meta = {model["id"]: model for model in models}
    val_base = {
        row["model"]: row["accuracy"]
        for row in summary_rows
        if row["split_role"] == "validation_policy_selection"
        and row["strategy"] == "single_sample"
        and int(row["budget_k"]) == 1
    }
    feature_rows = []
    for row in transfer_rows:
        if row["retention"] is None:
            continue
        source_meta = model_meta[row["source_model"]]
        target_meta = model_meta[row["target_model"]]
        feature_rows.append(
            {
                **row,
                "source_family": source_meta["family"],
                "target_family": target_meta["family"],
                "source_scale_b": float(source_meta["scale_b"]),
                "target_scale_b": float(target_meta["scale_b"]),
                "source_base_validation_accuracy": val_base.get(row["source_model"], 0.0),
                "target_base_validation_accuracy": val_base.get(row["target_model"], 0.0),
                "base_accuracy_gap": abs(
                    val_base.get(row["source_model"], 0.0) - val_base.get(row["target_model"], 0.0)
                ),
            }
        )
    write_csv(output_dir / "predictor_feature_table.csv", feature_rows)
    if len(feature_rows) < 8:
        result = {"status": "SKIPPED_TOO_FEW_ROWS", "rows": len(feature_rows)}
        write_json(output_dir / "predictor_analysis.json", result)
        return result
    try:
        import optuna
        import pandas as pd
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import LeaveOneGroupOut, cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler

        numeric_features = [
            "source_scale_b",
            "target_scale_b",
            "source_base_validation_accuracy",
            "target_base_validation_accuracy",
            "base_accuracy_gap",
            "source_budget_k",
        ]
        categorical_features = [
            "source_family",
            "target_family",
            "source_strategy",
            "evaluation_role",
        ]
        X = pd.DataFrame(
            [{feature: row.get(feature, 0) for feature in numeric_features + categorical_features} for row in feature_rows]
        )
        y = [float(row["retention"]) for row in feature_rows]
        groups = [row["target_family"] for row in feature_rows]
        if len(set(groups)) < 2:
            result = {"status": "SKIPPED_TOO_FEW_GROUPS", "rows": len(feature_rows), "target_family_groups": sorted(set(groups))}
            write_json(output_dir / "predictor_analysis.json", result)
            return result

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_features),
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ]
        )
        logo = LeaveOneGroupOut()

        def objective(trial: Any) -> float:
            model = RandomForestRegressor(
                n_estimators=trial.suggest_int("n_estimators", 50, 200),
                max_depth=trial.suggest_int("max_depth", 2, 8),
                min_samples_leaf=trial.suggest_int("min_samples_leaf", 1, 4),
                random_state=20260618,
            )
            pipe = Pipeline([("pre", preprocessor), ("model", model)])
            scores = cross_val_score(pipe, X, y, cv=logo.split(X, y, groups), scoring="r2")
            finite = [score for score in scores if not math.isnan(score) and math.isfinite(score)]
            if not finite:
                return -999.0
            return float(statistics.fmean(finite))

        study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=20260618))
        study.optimize(objective, n_trials=25, show_progress_bar=False)
        result = {
            "status": "COMPLETE",
            "rows": len(feature_rows),
            "best_value_leave_one_target_family_r2": study.best_value,
            "best_params": study.best_params,
            "note": "Small-cell exploratory predictor; not a formal RQ3 pass unless enough model-family diversity and stable CIs are present.",
        }
    except Exception as exc:
        result = {"status": "FAILED", "rows": len(feature_rows), "error": repr(exc)}
    write_json(output_dir / "predictor_analysis.json", result)
    return result


def render_report(
    output_dir: Path,
    config: dict[str, Any],
    dataset_totals: dict[str, int],
    summary_rows: list[dict[str, Any]],
    policy_rows: list[dict[str, Any]],
    transfer_rows: list[dict[str, Any]],
    predictor_result: dict[str, Any],
) -> None:
    lines = [
        "# EXP01 Full AWS Result",
        "",
        f"Generated: {utc_now()}",
        "",
        "Status: **RESULTS PRESENT - INTERNAL DEFENSIBILITY REVIEW REQUIRED BEFORE CLAIM PROMOTION**",
        "",
        "## Run Scope",
        "",
        f"- Models: `{len(config['models'])}` open models",
        f"- GSM8K rows sampled: `{config['datasets'][0]['sample_size']}`",
        f"- MATH-500 strict holdout rows sampled: `{config['datasets'][1]['sample_size']}`",
        f"- Budgets evaluated: `K=1,2,4,8`",
        "- Strategies evaluated: `single_sample`, `majority_vote`",
        "- Policy selection: GSM8K validation-policy rows only",
        "- Strict holdout: MATH-500 rows were not used for policy selection",
        "",
        "## Dataset Access",
        "",
        "| Dataset | Visible rows | Sampled rows | Role |",
        "|---|---:|---:|---|",
    ]
    for spec in config["datasets"]:
        lines.append(
            f"| `{spec['name']}` | {dataset_totals.get(spec['name'], 0)} | {spec['sample_size']} | {spec['role']} |"
        )
    lines.extend(["", "## Selected Validation Policies", "", "| Model | Strategy | K | Validation accuracy |", "|---|---|---:|---:|"])
    for row in policy_rows:
        lines.append(
            f"| `{row['model']}` | `{row['selected_strategy']}` | {row['selected_budget_k']} | {row['validation_accuracy']:.4f} |"
        )
    lines.extend(["", "## Model / Strategy Accuracy Summary", ""])
    lines.extend(["| Model | Strategy | K | Split role | Rows | Accuracy | Mean entropy | Mean margin |", "|---|---|---:|---|---:|---:|---:|---:|"])
    for row in summary_rows:
        if row["split_role"] in {"validation_policy_selection", "test_in_domain", "strict_domain_holdout_test"}:
            lines.append(
                f"| `{row['model']}` | `{row['strategy']}` | {row['budget_k']} | `{row['split_role']}` | "
                f"{row['rows']} | {row['accuracy']:.4f} | {row['mean_answer_entropy']:.4f} | {row['mean_self_consistency_margin']:.4f} |"
            )
    lines.extend(["", "## Transfer Retention Matrix Rows", ""])
    lines.extend(
        [
            "| Source | Target | Eval role | Source policy | Target optimum | Source-on-target acc | Target-opt acc | Retention |",
            "|---|---|---|---|---|---:|---:|---:|",
        ]
    )
    for row in transfer_rows:
        retention = row["retention"]
        retention_text = "" if retention is None else f"{retention:.4f}"
        lines.append(
            f"| `{row['source_model']}` | `{row['target_model']}` | `{row['evaluation_role']}` | "
            f"`{row['source_strategy']} K={row['source_budget_k']}` | "
            f"`{row['target_optimal_strategy']} K={row['target_optimal_budget_k']}` | "
            f"{row['source_policy_accuracy_on_target']:.4f} | {row['target_optimal_accuracy']:.4f} | {retention_text} |"
        )
    lines.extend(["", "## Predictor / Feature Engineering", "", f"Predictor status: `{predictor_result.get('status')}`."])
    if predictor_result.get("status") == "COMPLETE":
        r2_value = float(predictor_result.get("best_value_leave_one_target_family_r2", float("nan")))
        lines.extend(
            [
                "",
                f"Best leave-one-target-family R2: `{r2_value:.4f}`.",
                f"Best Optuna parameters: `{predictor_result.get('best_params')}`.",
            ]
        )
        if r2_value < 0:
            lines.append(
                "Interpretation: the feature-engineered transfer predictor did not generalize across held-out target model families."
            )
    elif predictor_result.get("error"):
        lines.extend(["", f"Predictor error: `{predictor_result.get('error')}`."])
    lines.extend(
        [
            "",
            "Feature engineering used model-family metadata, source/target base validation accuracy, base-accuracy gap, strategy id, budget, and evaluation role. Optuna was limited to transfer-predictor hyperparameters and did not tune prompts, budgets, or final holdout behavior.",
            "",
            "## Claim Boundary",
            "",
            "This run can support a first-pass transferability analysis only. It does not yet support claims about verifier-based best-of-N or sequential refinement because those strategy classes were intentionally deferred until exact-answer scoring and majority-vote logging were stable.",
            "",
        ]
    )
    (output_dir / "EXP01_FULL_AWS_RESULT_20260618.md").write_text("\n".join(lines), encoding="utf-8")


def render_defense_challenge(
    output_dir: Path,
    config: dict[str, Any],
    transfer_rows: list[dict[str, Any]],
    predictor_result: dict[str, Any],
) -> None:
    complete_matrix = len(transfer_rows) >= len(config["models"]) * len(config["models"]) * 2
    has_holdout = any(row["evaluation_role"] == "strict_domain_holdout_test" for row in transfer_rows)
    diagonal = [row for row in transfer_rows if row["source_model"] == row["target_model"]]
    offdiag = [row for row in transfer_rows if row["source_model"] != row["target_model"]]
    offdiag_ret = [float(row["retention"]) for row in offdiag if row["retention"] is not None]
    mean_offdiag = statistics.fmean(offdiag_ret) if offdiag_ret else 0.0
    predictor_status = predictor_result.get("status")
    predictor_r2 = predictor_result.get("best_value_leave_one_target_family_r2")
    if predictor_r2 is None:
        predictor_phrase = f"Predictor status `{predictor_status}`"
    else:
        predictor_phrase = f"Predictor status `{predictor_status}`, leave-one-target-family R2 `{float(predictor_r2):.4f}`"
    lines = [
        "# EXP01 Internal Defensibility Challenge",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Defense Verdict",
        "",
        "Verdict: **PROVISIONAL / DO NOT OVERCLAIM**",
        "",
        "The experiment now has results and proper split discipline. It is defensible as a first-pass open-model TTC transfer matrix if the report keeps the exact limitations visible. It is not yet a complete Praxis-level paper claim because verifier-based best-of-N, sequential refinement, and multi-seed decoding were deferred.",
        "",
        "## Challenge Questions",
        "",
        "| Challenge | Answer |",
        "|---|---|",
        f"| Is the transfer matrix complete for the configured model set? | `{complete_matrix}` ({len(transfer_rows)} rows). |",
        f"| Is there a strict holdout not used for policy selection? | `{has_holdout}`. |",
        f"| Are off-diagonal transfer rows present? | `{bool(offdiag)}`; mean off-diagonal retention `{mean_offdiag:.4f}`. |",
        f"| Are diagonal target-optimal controls present? | `{bool(diagonal)}`. |",
        "| Were final test/holdout rows used for policy selection? | No; policy selection is defined on GSM8K validation-policy rows. |",
        "| Did the run test H1 fully? | No. H1 requires verifier/scorer best-of-N; this first run tests majority-vote transfer only. |",
        "| Did the run test H3 fully? | No. Sequential refinement was deferred. |",
        f"| Did Optuna tune only the predictor? | {predictor_phrase}; no prompt/budget rescue path is implemented. |",
        "| Is answer scoring fully semantic? | No. It is strict normalized exact-answer scoring. This is conservative but may undercount equivalent math expressions. |",
        "| Is the result ready for a defense slide? | Yes, as preliminary full-run evidence with limitations. Not yet as final dissertation claim. |",
        "",
        "## Required Before Praxis Promotion",
        "",
        "1. Add a verifier/scorer-based best-of-N condition.",
        "2. Add sequential self-refinement or explicitly drop H3.",
        "3. Add at least one more decoding seed or justify bootstrap-over-problems only.",
        "4. Manually audit exact-answer scoring on a random sample and report agreement.",
        "5. Expand or replace strict math scoring with a symbolic/math verifier if exact matching undercounts too heavily.",
        "",
    ]
    (output_dir / "EXP01_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def run_analysis_only(config: dict[str, Any], output_dir: Path) -> None:
    scores_path = output_dir / "scores_all.jsonl"
    if not scores_path.exists():
        raise FileNotFoundError(f"analysis-only mode requires {scores_path}")
    split_summary_path = output_dir / "split_summary.json"
    if split_summary_path.exists():
        split_summary = read_json(split_summary_path)
        dataset_totals = split_summary.get("dataset_totals", {})
        row_count = int(split_summary.get("rows", 0))
    else:
        dataset_totals = {spec["name"]: 0 for spec in config["datasets"]}
        row_count = len({row["row_key"] for row in read_jsonl(scores_path)})

    all_scores = read_jsonl(scores_path)
    summary_rows = summarize_scores(all_scores)
    write_csv(output_dir / "accuracy_summary.csv", summary_rows)
    policy_rows, transfer_rows = compute_transfer(summary_rows, config["models"])
    write_csv(output_dir / "selected_policies.csv", policy_rows)
    write_csv(output_dir / "transfer_retention.csv", transfer_rows)
    predictor_result = run_predictor_analysis(summary_rows, transfer_rows, config["models"], output_dir)
    render_report(output_dir, config, dataset_totals, summary_rows, policy_rows, transfer_rows, predictor_result)
    render_defense_challenge(output_dir, config, transfer_rows, predictor_result)
    write_json(
        output_dir / "run_summary.json",
        {
            "generated_utc": utc_now(),
            "status": "COMPLETE",
            "models": [model["id"] for model in config["models"]],
            "rows": row_count,
            "score_rows": len(all_scores),
            "transfer_rows": len(transfer_rows),
            "predictor_status": predictor_result.get("status"),
            "result_report": "EXP01_FULL_AWS_RESULT_20260618.md",
            "defense_challenge": "EXP01_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md",
            "analysis_only": True,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-label", default="frontier-exp01-ttc-transfer-20260618")
    parser.add_argument("--analysis-only", action="store_true")
    args = parser.parse_args()

    config = read_json(args.config)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)

    if args.analysis_only:
        run_analysis_only(config, output_dir)
        print("COMPLETE", output_dir)
        return

    problem_rows, label_rows, dataset_totals = build_rows(config)
    labels_by_key = {row["row_key"]: row["gold_answer_normalized"] for row in label_rows}
    write_jsonl(
        output_dir / "problem_manifest_private_with_prompts.jsonl",
        [
            {
                key: value
                for key, value in row.items()
                if key not in {"problem"}
            }
            for row in problem_rows
        ],
    )
    write_jsonl(output_dir / "gold_labels.jsonl", label_rows)
    write_json(
        output_dir / "split_summary.json",
        {
            "generated_utc": utc_now(),
            "dataset_totals": dataset_totals,
            "rows": len(problem_rows),
            "split_role_counts": dict(Counter(row["split_role"] for row in problem_rows)),
            "dataset_counts": dict(Counter(row["dataset"] for row in problem_rows)),
            "run_label": args.run_label,
        },
    )

    all_scores: list[dict[str, Any]] = []
    all_diagnostics: list[dict[str, Any]] = []
    for model_spec in config["models"]:
        _, score_rows, diagnostic_rows = evaluate_model(
            model_spec=model_spec,
            config=config,
            problem_rows=problem_rows,
            labels_by_key=labels_by_key,
            output_dir=output_dir,
        )
        all_scores.extend(score_rows)
        all_diagnostics.extend(diagnostic_rows)
        write_jsonl(output_dir / "scores_all_partial.jsonl", all_scores)

    write_jsonl(output_dir / "scores_all.jsonl", all_scores)
    write_jsonl(output_dir / "diagnostics_all.jsonl", all_diagnostics)
    summary_rows = summarize_scores(all_scores)
    write_csv(output_dir / "accuracy_summary.csv", summary_rows)
    policy_rows, transfer_rows = compute_transfer(summary_rows, config["models"])
    write_csv(output_dir / "selected_policies.csv", policy_rows)
    write_csv(output_dir / "transfer_retention.csv", transfer_rows)
    predictor_result = run_predictor_analysis(summary_rows, transfer_rows, config["models"], output_dir)
    render_report(output_dir, config, dataset_totals, summary_rows, policy_rows, transfer_rows, predictor_result)
    render_defense_challenge(output_dir, config, transfer_rows, predictor_result)
    write_json(
        output_dir / "run_summary.json",
        {
            "generated_utc": utc_now(),
            "status": "COMPLETE",
            "models": [model["id"] for model in config["models"]],
            "rows": len(problem_rows),
            "score_rows": len(all_scores),
            "transfer_rows": len(transfer_rows),
            "predictor_status": predictor_result.get("status"),
            "result_report": "EXP01_FULL_AWS_RESULT_20260618.md",
            "defense_challenge": "EXP01_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md",
        },
    )
    print("COMPLETE", output_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
