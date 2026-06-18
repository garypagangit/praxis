from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_SERVER = "https://datasets-server.huggingface.co"


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


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def request_json(path: str, params: dict[str, Any], retries: int = 5) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{DATASET_SERVER}/{path}?{query}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if attempt < retries and exc.code in {429, 500, 502, 503, 504}:
                time.sleep(8 * attempt)
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(4 * attempt)
                continue
            raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_error}") from exc
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_error}")


def fetch_page(dataset: str, config: str, split: str, offset: int, length: int = 100) -> tuple[int, list[dict[str, Any]]]:
    payload = request_json(
        "rows",
        {
            "dataset": dataset,
            "config": config,
            "split": split,
            "offset": offset,
            "length": length,
        },
    )
    total = int(payload.get("num_rows_total") or 0)
    rows = [{"row_idx": int(item["row_idx"]), **item["row"]} for item in payload.get("rows", [])]
    return total, rows


def fetch_dataset_rows(dataset: str, config: str, split: str, max_rows: int | None = None) -> list[dict[str, Any]]:
    total, _ = fetch_page(dataset, config, split, 0, 1)
    limit = total if max_rows is None else min(total, max_rows)
    rows: list[dict[str, Any]] = []
    for offset in range(0, limit, 100):
        _, page = fetch_page(dataset, config, split, offset, min(100, limit - offset))
        rows.extend(page)
    return rows[:limit]


def canonical_label(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"1", "true", "harmful", "unsafe", "adversarial", "jailbreak", "refusal"}:
        return "unsafe_request"
    if text in {"0", "false", "benign", "safe"}:
        return "benign_control"
    if any(marker in text for marker in ["harmful", "unsafe", "jailbreak"]):
        return "unsafe_request"
    if any(marker in text for marker in ["benign", "safe"]):
        return "benign_control"
    return text or "unlabeled"


def normalize_response_label(value: Any) -> int:
    # JailbreakBench judge labels use 1 for successful harmful/non-refusal completions
    # and 0 for safe refusal/non-harmful completions.
    return 1 if int(value) == 1 else 0


def join_fields(row: dict[str, Any], fields: list[str]) -> str:
    return "\n".join(str(row.get(field, "") or "") for field in fields)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", str(text).strip())
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned or [str(text).strip()]


def bootstrap_ci(values: list[float], samples: int = 1000, seed: int = 20260618) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    means = []
    n = len(values)
    for _ in range(samples):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(draw))
    means.sort()
    mean = statistics.fmean(values)
    return mean, means[int(0.025 * samples)], means[int(0.975 * samples) - 1]


def binary_metrics(y_true: list[int], y_prob: list[float], threshold: float) -> dict[str, float]:
    y_pred = [1 if prob >= threshold else 0 for prob in y_prob]
    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    tn = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 0)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    false_positive_rate = fp / max(fp + tn, 1)
    accuracy = (tp + tn) / max(len(y_true), 1)
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
        "accuracy": accuracy,
    }


def pick_threshold(
    y_true: list[int],
    y_prob: list[float],
    grid: list[float],
    false_positive_cap: float,
) -> tuple[float, dict[str, float]]:
    scored = [binary_metrics(y_true, y_prob, threshold) for threshold in grid]
    feasible = [row for row in scored if row["false_positive_rate"] <= false_positive_cap]
    if not feasible:
        feasible = scored
    feasible.sort(key=lambda row: (row["recall"], row["f1"], -row["false_positive_rate"]), reverse=True)
    best = feasible[0]
    return float(best["threshold"]), best


def train_text_classifier(texts: list[str], labels: list[int], seed: int) -> Any:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    word = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
        max_features=50000,
        strip_accents="unicode",
        lowercase=True,
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_features=50000,
        lowercase=True,
    )
    model = LogisticRegression(
        C=2.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=seed,
    )
    pipe = Pipeline([("features", FeatureUnion([("word", word), ("char", char)])), ("model", model)])
    pipe.fit(texts, labels)
    return pipe


def probability(model: Any, texts: list[str]) -> list[float]:
    return [float(value) for value in model.predict_proba(texts)[:, 1]]


def stratified_split(indices: list[int], labels: list[int], test_fraction: float, seed: int) -> tuple[list[int], list[int]]:
    rng = random.Random(seed)
    by_label: dict[int, list[int]] = {0: [], 1: []}
    for idx in indices:
        by_label[int(labels[idx])].append(idx)
    train: list[int] = []
    test: list[int] = []
    for label_indices in by_label.values():
        rng.shuffle(label_indices)
        cut = max(1, int(round(len(label_indices) * test_fraction)))
        test.extend(label_indices[:cut])
        train.extend(label_indices[cut:])
    train.sort()
    test.sort()
    return train, test


def redacted_prediction_row(
    row_id: str,
    split_role: str,
    label: int,
    probability_value: float,
    threshold: float,
    text: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "row_id": row_id,
        "split_role": split_role,
        "label": label,
        "probability": probability_value,
        "threshold": threshold,
        "prediction": int(probability_value >= threshold),
        "text_sha256": sha256_text(text),
        "text_length": len(text),
    }
    if extra:
        payload.update(extra)
    return payload


def prompt_detector_experiment(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    from sklearn.metrics import average_precision_score, roc_auc_score

    seed = int(config["split_seed"])
    prompt_cfg = config["prompt_detector"]
    train_source = prompt_cfg["train_source"]
    wild_rows = fetch_dataset_rows(
        train_source["hf_dataset"],
        train_source["hf_config"],
        train_source["hf_split"],
        int(train_source.get("max_rows", 2210)),
    )
    texts = [str(row.get(train_source["text_field"], "")) for row in wild_rows]
    labels = [1 if canonical_label(row.get(train_source["label_field"])) == "unsafe_request" else 0 for row in wild_rows]
    train_idx, dev_idx = stratified_split(list(range(len(texts))), labels, float(prompt_cfg["dev_fraction"]), seed)
    model = train_text_classifier([texts[idx] for idx in train_idx], [labels[idx] for idx in train_idx], seed)
    dev_prob = probability(model, [texts[idx] for idx in dev_idx])
    dev_labels = [labels[idx] for idx in dev_idx]
    threshold, dev_metrics = pick_threshold(
        dev_labels,
        dev_prob,
        [float(value) for value in prompt_cfg["threshold_grid"]],
        float(prompt_cfg["false_refusal_cap"]),
    )

    harmful_cfg = prompt_cfg["strict_harmful_holdout"]
    benign_cfg = prompt_cfg["benign_control_holdout"]
    harmful_rows = fetch_dataset_rows(harmful_cfg["hf_dataset"], harmful_cfg["hf_config"], harmful_cfg["hf_split"])
    benign_rows = fetch_dataset_rows(benign_cfg["hf_dataset"], benign_cfg["hf_config"], benign_cfg["hf_split"])
    harmful_texts = [join_fields(row, harmful_cfg["text_fields"]) for row in harmful_rows]
    benign_texts = [join_fields(row, benign_cfg["text_fields"]) for row in benign_rows]
    holdout_texts = harmful_texts + benign_texts
    holdout_labels = [1] * len(harmful_texts) + [0] * len(benign_texts)
    holdout_probs = probability(model, holdout_texts)
    holdout_metrics = binary_metrics(holdout_labels, holdout_probs, threshold)
    harmful_recall_values = [
        1.0 if prob >= threshold else 0.0 for prob in holdout_probs[: len(harmful_texts)]
    ]
    benign_false_refusal_values = [
        1.0 if prob >= threshold else 0.0 for prob in holdout_probs[len(harmful_texts) :]
    ]
    harmful_mean, harmful_lo, harmful_hi = bootstrap_ci(harmful_recall_values, config["metrics"]["bootstrap_samples"], seed)
    fpr_mean, fpr_lo, fpr_hi = bootstrap_ci(benign_false_refusal_values, config["metrics"]["bootstrap_samples"], seed + 1)

    try:
        dev_roc_auc = float(roc_auc_score(dev_labels, dev_prob))
        dev_pr_auc = float(average_precision_score(dev_labels, dev_prob))
        holdout_roc_auc = float(roc_auc_score(holdout_labels, holdout_probs))
        holdout_pr_auc = float(average_precision_score(holdout_labels, holdout_probs))
    except Exception:
        dev_roc_auc = dev_pr_auc = holdout_roc_auc = holdout_pr_auc = float("nan")

    redacted_rows: list[dict[str, Any]] = []
    for idx in dev_idx:
        redacted_rows.append(
            redacted_prediction_row(
                f"WildJailbreak:train:{wild_rows[idx]['row_idx']}",
                "prompt_detector_dev",
                labels[idx],
                probability(model, [texts[idx]])[0],
                threshold,
                texts[idx],
            )
        )
    for local_idx, text in enumerate(harmful_texts):
        redacted_rows.append(
            redacted_prediction_row(
                f"JBB-Behaviors:harmful:{harmful_rows[local_idx]['row_idx']}",
                "strict_behavior_holdout_test",
                1,
                holdout_probs[local_idx],
                threshold,
                text,
            )
        )
    offset = len(harmful_texts)
    for local_idx, text in enumerate(benign_texts):
        redacted_rows.append(
            redacted_prediction_row(
                f"JBB-Behaviors:benign:{benign_rows[local_idx]['row_idx']}",
                "benign_control_test",
                0,
                holdout_probs[offset + local_idx],
                threshold,
                text,
            )
        )
    write_jsonl(output_dir / "prompt_detector_predictions_redacted.jsonl", redacted_rows)

    return {
        "status": "COMPLETE",
        "train_rows": len(train_idx),
        "dev_rows": len(dev_idx),
        "wildjailbreak_label_counts": dict(Counter(labels)),
        "threshold": threshold,
        "dev_metrics": {**dev_metrics, "roc_auc": dev_roc_auc, "pr_auc": dev_pr_auc},
        "holdout_metrics": {**holdout_metrics, "roc_auc": holdout_roc_auc, "pr_auc": holdout_pr_auc},
        "strict_harmful_recall_ci": {
            "mean": harmful_mean,
            "lo": harmful_lo,
            "hi": harmful_hi,
            "rows": len(harmful_recall_values),
        },
        "benign_false_refusal_ci": {
            "mean": fpr_mean,
            "lo": fpr_lo,
            "hi": fpr_hi,
            "rows": len(benign_false_refusal_values),
        },
    }


def response_step_experiment(config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    from sklearn.metrics import average_precision_score, roc_auc_score

    seed = int(config["split_seed"])
    step_cfg = config["response_step_detector"]
    source = step_cfg["source"]
    rows = fetch_dataset_rows(source["hf_dataset"], source["hf_config"], source["hf_split"])
    texts = [str(row.get(source["response_field"], "")) for row in rows]
    prompts = [str(row.get(source["prompt_field"], "")) for row in rows]
    labels = [normalize_response_label(row.get(source["label_field"], 0)) for row in rows]
    train_idx, test_idx = stratified_split(list(range(len(texts))), labels, float(step_cfg["test_fraction"]), seed + 7)
    model = train_text_classifier([texts[idx] for idx in train_idx], [labels[idx] for idx in train_idx], seed + 7)
    train_prob = probability(model, [texts[idx] for idx in train_idx])
    train_labels = [labels[idx] for idx in train_idx]
    threshold, train_metrics = pick_threshold(
        train_labels,
        train_prob,
        [float(value) for value in step_cfg["threshold_grid"]],
        float(step_cfg["safe_block_cap"]),
    )

    test_response_probs = probability(model, [texts[idx] for idx in test_idx])
    test_labels = [labels[idx] for idx in test_idx]
    response_metrics = binary_metrics(test_labels, test_response_probs, threshold)
    try:
        response_roc_auc = float(roc_auc_score(test_labels, test_response_probs))
        response_pr_auc = float(average_precision_score(test_labels, test_response_probs))
    except Exception:
        response_roc_auc = response_pr_auc = float("nan")

    redacted_rows: list[dict[str, Any]] = []
    unsafe_recall_values: list[float] = []
    safe_block_values: list[float] = []
    step_exposure_fractions: list[float] = []
    caught_unsafe = 0
    unsafe_total = 0
    safe_total = 0
    safe_blocked = 0
    for idx in test_idx:
        sentences = split_sentences(texts[idx])
        sentence_probs = probability(model, sentences)
        first_flag = next((pos for pos, prob in enumerate(sentence_probs) if prob >= threshold), None)
        max_sentence_prob = max(sentence_probs) if sentence_probs else 0.0
        pred = int(max_sentence_prob >= threshold)
        label = labels[idx]
        exposure_fraction = 1.0
        if first_flag is not None:
            exposure_fraction = (first_flag + 1) / max(len(sentences), 1)
        if label == 1:
            unsafe_total += 1
            unsafe_recall_values.append(float(pred))
            if pred:
                caught_unsafe += 1
                step_exposure_fractions.append(exposure_fraction)
        else:
            safe_total += 1
            safe_block_values.append(float(pred))
            if pred:
                safe_blocked += 1
        redacted_rows.append(
            redacted_prediction_row(
                f"JBB-judge-comparison:test:{rows[idx]['row_idx']}",
                "response_step_holdout_test",
                label,
                max_sentence_prob,
                threshold,
                texts[idx],
                {
                    "prompt_sha256": sha256_text(prompts[idx]),
                    "prompt_length": len(prompts[idx]),
                    "sentence_count": len(sentences),
                    "first_flag_step": first_flag,
                    "step_exposure_fraction": exposure_fraction if pred else 1.0,
                    "full_response_probability": test_response_probs[test_idx.index(idx)],
                },
            )
        )
    write_jsonl(output_dir / "response_step_predictions_redacted.jsonl", redacted_rows)

    recall_mean, recall_lo, recall_hi = bootstrap_ci(unsafe_recall_values, config["metrics"]["bootstrap_samples"], seed + 2)
    safe_mean, safe_lo, safe_hi = bootstrap_ci(safe_block_values, config["metrics"]["bootstrap_samples"], seed + 3)
    exposure_mean, exposure_lo, exposure_hi = bootstrap_ci(
        step_exposure_fractions or [1.0], config["metrics"]["bootstrap_samples"], seed + 4
    )
    exposure_reduction = 1.0 - exposure_mean
    return {
        "status": "COMPLETE",
        "train_rows": len(train_idx),
        "test_rows": len(test_idx),
        "response_label_counts": dict(Counter(labels)),
        "threshold": threshold,
        "train_metrics": train_metrics,
        "response_level_holdout_metrics": {
            **response_metrics,
            "roc_auc": response_roc_auc,
            "pr_auc": response_pr_auc,
        },
        "step_level_holdout": {
            "unsafe_total": unsafe_total,
            "unsafe_caught": caught_unsafe,
            "safe_total": safe_total,
            "safe_blocked": safe_blocked,
            "unsafe_recall_ci": {"mean": recall_mean, "lo": recall_lo, "hi": recall_hi},
            "safe_block_rate_ci": {"mean": safe_mean, "lo": safe_lo, "hi": safe_hi},
            "caught_unsafe_exposure_fraction_ci": {
                "mean": exposure_mean,
                "lo": exposure_lo,
                "hi": exposure_hi,
            },
            "exposure_reduction_vs_output_only": exposure_reduction,
        },
    }


def render_report(
    output_dir: Path,
    config: dict[str, Any],
    prompt_result: dict[str, Any],
    response_result: dict[str, Any],
) -> dict[str, Any]:
    p_holdout = prompt_result["holdout_metrics"]
    p_harm = prompt_result["strict_harmful_recall_ci"]
    p_benign = prompt_result["benign_false_refusal_ci"]
    s_holdout = response_result["step_level_holdout"]
    s_response = response_result["response_level_holdout_metrics"]
    thresholds = config["metrics"]
    publish_checks = {
        "prompt_harmful_recall": p_harm["mean"] >= float(thresholds["target_prompt_detector_harmful_recall"]),
        "prompt_benign_false_refusal": p_benign["mean"] <= float(thresholds["target_benign_false_refusal_max"]),
        "response_step_unsafe_recall": s_holdout["unsafe_recall_ci"]["mean"] >= float(thresholds["target_response_step_recall"]),
        "safe_response_block_rate": s_holdout["safe_block_rate_ci"]["mean"] <= float(thresholds["target_safe_response_block_max"]),
        "no_model_generation": not bool(config["content_policy"].get("model_generation_allowed")),
    }
    verdict = "PUBLISHABLE PILOT POSITIVE" if all(publish_checks.values()) else "MIXED / NEEDS NEXT GATE"
    summary = {
        "generated_utc": utc_now(),
        "status": verdict,
        "publish_checks": publish_checks,
        "prompt_detector": prompt_result,
        "response_step_detector": response_result,
    }
    write_json(output_dir / "EXP02_FULL_GUARDRAIL_SUMMARY_20260618.json", summary)
    lines = [
        "# EXP02 Full Guardrail Experiment Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{verdict}**",
        "",
        "## Run Scope",
        "",
        "- No model generations were run.",
        "- Raw prompts and responses were used only in memory.",
        "- Committed artifacts contain hashes, lengths, labels, predictions, and metrics only.",
        "- Prompt detector trained on WildJailbreak and evaluated on JailbreakBench harmful/benign behavior holdouts.",
        "- Response-step detector trained/evaluated on JailbreakBench human-labeled comparison responses.",
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value | 95% bootstrap CI |",
        "|---|---:|---:|",
        f"| Prompt detector harmful-request recall on strict holdout | `{p_harm['mean']:.4f}` | `[{p_harm['lo']:.4f}, {p_harm['hi']:.4f}]` |",
        f"| Prompt detector benign false-refusal rate | `{p_benign['mean']:.4f}` | `[{p_benign['lo']:.4f}, {p_benign['hi']:.4f}]` |",
        f"| Response-step unsafe recall | `{s_holdout['unsafe_recall_ci']['mean']:.4f}` | `[{s_holdout['unsafe_recall_ci']['lo']:.4f}, {s_holdout['unsafe_recall_ci']['hi']:.4f}]` |",
        f"| Safe-response block rate | `{s_holdout['safe_block_rate_ci']['mean']:.4f}` | `[{s_holdout['safe_block_rate_ci']['lo']:.4f}, {s_holdout['safe_block_rate_ci']['hi']:.4f}]` |",
        f"| Caught-unsafe exposure fraction before step intervention | `{s_holdout['caught_unsafe_exposure_fraction_ci']['mean']:.4f}` | `[{s_holdout['caught_unsafe_exposure_fraction_ci']['lo']:.4f}, {s_holdout['caught_unsafe_exposure_fraction_ci']['hi']:.4f}]` |",
        f"| Exposure reduction vs output-only intervention | `{s_holdout['exposure_reduction_vs_output_only']:.4f}` |  |",
        "",
        "## Detector Details",
        "",
        "| Component | Threshold | ROC-AUC | PR-AUC | F1 | Recall | False positive / safe block rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Prompt holdout detector | `{prompt_result['threshold']:.2f}` | `{p_holdout['roc_auc']:.4f}` | `{p_holdout['pr_auc']:.4f}` | `{p_holdout['f1']:.4f}` | `{p_holdout['recall']:.4f}` | `{p_holdout['false_positive_rate']:.4f}` |",
        f"| Response-step holdout detector | `{response_result['threshold']:.2f}` | `{s_response['roc_auc']:.4f}` | `{s_response['pr_auc']:.4f}` | `{s_response['f1']:.4f}` | `{s_response['recall']:.4f}` | `{s_response['false_positive_rate']:.4f}` |",
        "",
        "## Publish Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for key, value in publish_checks.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## RQ/H Readout",
            "",
            "- RQ1/H1: supported if response-step unsafe recall clears the target while safe-response block rate stays low.",
            "- RQ2/H2: supported as a training-free intervention proxy if prompt blocking plus step interruption reduces unsafe exposure without benign-control over-refusal.",
            "- RQ3/H3: partially supported if step-level monitoring catches unsafe responses earlier than output-only blocking at comparable safety recall.",
            "",
            "## Claim Boundary",
            "",
            "This is a publishable pilot only if described as a redacted, dataset-based guardrail experiment. It does not claim that a live reasoning model was made safe, because no new model generations were run. The next external-validity gate should run the same guardrail online against one open model with private raw-output storage.",
        ]
    )
    (output_dir / "EXP02_FULL_GUARDRAIL_RESULT_20260618.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    challenge_lines = [
        "# EXP02 Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{verdict}**",
        "",
        "| Challenge | Answer |",
        "|---|---|",
        f"| Did the run use strict holdouts? | Yes. JailbreakBench harmful and benign behavior splits were held out from WildJailbreak prompt-detector training. |",
        f"| Was raw harmful text committed? | No. Prediction artifacts contain hashes, lengths, labels, probabilities, and metrics only. |",
        f"| Did the prompt detector preserve benign controls? | Benign false-refusal mean `{p_benign['mean']:.4f}`. |",
        f"| Did the response-step detector catch unsafe responses? | Unsafe recall mean `{s_holdout['unsafe_recall_ci']['mean']:.4f}`. |",
        f"| Does step-level beat output-only? | It provides earlier interruption: caught-unsafe exposure fraction `{s_holdout['caught_unsafe_exposure_fraction_ci']['mean']:.4f}` vs output-only `1.0000`. |",
        "| Is this a final live-model safety claim? | No. It is a dataset-based publishable pilot; live open-model validation is still required. |",
        "| Main weakness | Response-step labels are response-level human labels applied to sentence scans; future work should add manually labeled boundary steps. |",
        "| Main strength | Strong redaction discipline, strict benign controls, and measurable intervention utility without unsafe generation. |",
    ]
    (output_dir / "EXP02_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md").write_text(
        "\n".join(challenge_lines) + "\n", encoding="utf-8"
    )
    return summary


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)
    prompt_result = prompt_detector_experiment(config, output_dir)
    write_json(output_dir / "prompt_detector_metrics.json", prompt_result)
    response_result = response_step_experiment(config, output_dir)
    write_json(output_dir / "response_step_detector_metrics.json", response_result)
    summary = render_report(output_dir, config, prompt_result, response_result)
    print(summary["status"], output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp02_self_jailbreak_full_20260618.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
