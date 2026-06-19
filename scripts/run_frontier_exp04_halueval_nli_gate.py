from __future__ import annotations

import argparse
import hashlib
import json
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


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def request_json(path: str, params: dict[str, Any], retries: int = 5) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{DATASET_SERVER}/{path}?{query}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
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


def fetch_dataset_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    total, _ = fetch_page(source["hf_dataset"], source["hf_config"], source["hf_split"], 0, 1)
    limit = min(total, int(source.get("max_rows", total)))
    rows: list[dict[str, Any]] = []
    for offset in range(0, limit, 100):
        _, page = fetch_page(source["hf_dataset"], source["hf_config"], source["hf_split"], offset, min(100, limit - offset))
        rows.extend(page)
    return rows[:limit]


def build_examples(source: dict[str, Any], split_role: str) -> list[dict[str, Any]]:
    rows = fetch_dataset_rows(source)
    examples: list[dict[str, Any]] = []
    for row in rows:
        evidence = str(row.get(source["evidence_field"], "") or "")
        question = str(row.get(source.get("question_field", ""), "") or "")
        premise = f"Evidence:\n{evidence}\n\nContext:\n{question}".strip()
        for variant, label, field in [
            ("right", 0, source["right_field"]),
            ("hallucinated", 1, source["hallucinated_field"]),
        ]:
            answer = str(row.get(field, "") or "")
            examples.append(
                {
                    "row_id": f"{source['hf_dataset']}:{source['hf_config']}:{source['hf_split']}:{row['row_idx']}:{variant}",
                    "source_dataset": source["hf_dataset"],
                    "source_config": source["hf_config"],
                    "source_split": source["hf_split"],
                    "split_role": split_role,
                    "variant": variant,
                    "label": label,
                    "premise": premise,
                    "hypothesis": answer,
                }
            )
    return examples


def tokenize_words(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def lexical_overlap_scores(examples: list[dict[str, Any]]) -> list[float]:
    scores: list[float] = []
    for row in examples:
        premise_tokens = tokenize_words(row["premise"])
        hypothesis_tokens = tokenize_words(row["hypothesis"])
        overlap = len(premise_tokens & hypothesis_tokens) / max(len(hypothesis_tokens), 1)
        scores.append(1.0 - overlap)
    return scores


def load_nli_model(config: dict[str, Any]) -> tuple[Any, Any, int, int, int, str]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_id = config["nli_model"]["model_id"]
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and bool(config["nli_model"].get("use_fp16_on_cuda", True)):
        model = model.half()
    model.to(device)
    model.eval()
    label_map = {str(label).lower(): int(idx) for label, idx in model.config.label2id.items()}

    def find_label(names: list[str], fallback: int) -> int:
        for label, idx in label_map.items():
            if any(name in label for name in names):
                return idx
        return fallback

    contradiction_idx = find_label(["contradiction"], 0)
    neutral_idx = find_label(["neutral"], 1)
    entailment_idx = find_label(["entailment"], 2)
    return tokenizer, model, contradiction_idx, neutral_idx, entailment_idx, device


def nli_hallucination_scores(examples: list[dict[str, Any]], config: dict[str, Any]) -> list[float]:
    import torch

    tokenizer, model, contradiction_idx, neutral_idx, entailment_idx, device = load_nli_model(config)
    batch_size = int(config["nli_model"]["batch_size"])
    max_length = int(config["nli_model"]["max_length"])
    scores: list[float] = []
    for offset in range(0, len(examples), batch_size):
        batch = examples[offset : offset + batch_size]
        encoded = tokenizer(
            [row["premise"] for row in batch],
            [row["hypothesis"] for row in batch],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.inference_mode():
            logits = model(**encoded).logits.float()
        probs = torch.softmax(logits, dim=-1)
        entailment = probs[:, entailment_idx]
        contradiction = probs[:, contradiction_idx]
        neutral = probs[:, neutral_idx]
        hallucination = 1.0 - entailment + 0.25 * contradiction - 0.10 * neutral
        hallucination = torch.clamp(hallucination, min=0.0, max=1.0)
        scores.extend(float(value) for value in hallucination.detach().cpu().tolist())
    return scores


def binary_metrics(labels: list[int], scores: list[float], threshold: float) -> dict[str, Any]:
    preds = [1 if score >= threshold else 0 for score in scores]
    tp = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 1)
    tn = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 0)
    fn = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 0)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    accuracy = (tp + tn) / max(len(labels), 1)
    false_alarm = fp / max(fp + tn, 1)
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "false_alarm_rate": false_alarm,
    }


def pick_threshold(labels: list[int], scores: list[float], grid: list[float]) -> tuple[float, dict[str, Any]]:
    scored = [binary_metrics(labels, scores, float(threshold)) for threshold in grid]
    scored.sort(key=lambda row: (row["f1"], row["recall"], row["accuracy"]), reverse=True)
    best = scored[0]
    return float(best["threshold"]), best


def bootstrap_metric(labels: list[int], scores: list[float], threshold: float, samples: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(labels)
    f1s: list[float] = []
    accs: list[float] = []
    for _ in range(samples):
        idxs = [rng.randrange(n) for _ in range(n)]
        metric = binary_metrics([labels[idx] for idx in idxs], [scores[idx] for idx in idxs], threshold)
        f1s.append(float(metric["f1"]))
        accs.append(float(metric["accuracy"]))
    f1s.sort()
    accs.sort()
    return {
        "f1_mean": statistics.fmean(f1s),
        "f1_lo": f1s[int(0.025 * samples)],
        "f1_hi": f1s[int(0.975 * samples) - 1],
        "accuracy_mean": statistics.fmean(accs),
        "accuracy_lo": accs[int(0.025 * samples)],
        "accuracy_hi": accs[int(0.975 * samples) - 1],
    }


def redacted_rows(examples: list[dict[str, Any]], scores: list[float], threshold: float, model_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row, score in zip(examples, scores):
        rows.append(
            {
                "row_id": row["row_id"],
                "split_role": row["split_role"],
                "source_dataset": row["source_dataset"],
                "source_config": row["source_config"],
                "variant": row["variant"],
                "label": row["label"],
                "hallucination_probability": score,
                "threshold": threshold,
                "prediction": int(score >= threshold),
                "premise_sha256": sha256_text(row["premise"]),
                "hypothesis_sha256": sha256_text(row["hypothesis"]),
                "premise_length": len(row["premise"]),
                "hypothesis_length": len(row["hypothesis"]),
                "model": model_name,
            }
        )
    return rows


def render_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    holdout = summary["holdout_nli_metrics"]
    lexical = summary["holdout_lexical_metrics"]
    ci = summary["holdout_nli_bootstrap_ci"]
    lines = [
        "# EXP04 HaluEval NLI Gate Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Scope",
        "",
        "- Validation/tuning split: HaluEval QA.",
        "- Strict holdout split: HaluEval dialogue.",
        "- Open NLI model scored evidence-response support.",
        "- No model answer generation was run.",
        "- Committed predictions are redacted hashes/lengths/probabilities only.",
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Validation examples | `{summary['validation_examples']}` |",
        f"| Strict holdout examples | `{summary['strict_holdout_examples']}` |",
        f"| NLI threshold selected on validation | `{summary['nli_threshold']:.2f}` |",
        f"| Lexical threshold selected on validation | `{summary['lexical_threshold']:.2f}` |",
        f"| Holdout NLI precision | `{holdout['precision']:.4f}` |",
        f"| Holdout NLI recall | `{holdout['recall']:.4f}` |",
        f"| Holdout NLI F1 | `{holdout['f1']:.4f}` CI `[{ci['f1_lo']:.4f}, {ci['f1_hi']:.4f}]` |",
        f"| Holdout NLI accuracy | `{holdout['accuracy']:.4f}` CI `[{ci['accuracy_lo']:.4f}, {ci['accuracy_hi']:.4f}]` |",
        f"| Holdout lexical F1 | `{lexical['f1']:.4f}` |",
        f"| F1 delta over lexical | `{summary['f1_delta_over_lexical']:.4f}` |",
        "",
        "## Publish Checks",
        "",
        "| Check | Pass |",
        "|---|---:|",
    ]
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This gate is dataset-backed and uses a strict HaluEval dialogue holdout, but it is still verifier-only. It does not prove that live model hallucination is reduced in conversation; it tests whether evidence-conditioned scoring can detect hallucinated responses better than a lexical baseline.",
        ]
    )
    (output_dir / "EXP04_HALUEVAL_NLI_GATE_RESULT_20260619.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    challenge = [
        "# EXP04 HaluEval NLI Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{summary['status']}**",
        "",
        "| Challenge | Answer |",
        "|---|---|",
        f"| Were validation and strict holdout separated? | Yes. Validation used HaluEval QA; strict holdout used HaluEval dialogue. |",
        f"| Did threshold selection touch holdout? | No. NLI threshold `{summary['nli_threshold']:.2f}` was selected on validation only. |",
        f"| Did NLI beat lexical? | F1 delta `{summary['f1_delta_over_lexical']:.4f}`. |",
        f"| Did the holdout F1 clear target? | Holdout NLI F1 `{holdout['f1']:.4f}`. |",
        "| Are raw dataset responses committed? | No. Prediction rows use hashes, lengths, labels, probabilities, and metrics only. |",
        "| Main weakness | NLI is not KG reasoning and may reward lexical support rather than full factual entailment. |",
        "| Main strength | It adds a real external HaluEval dialogue holdout after the Wikidata smoke gate. |",
    ]
    (output_dir / "EXP04_HALUEVAL_NLI_DEFENSIBILITY_CHALLENGE_20260619.md").write_text(
        "\n".join(challenge) + "\n", encoding="utf-8"
    )


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)
    validation_examples = build_examples(config["validation_source"], "validation_qa")
    holdout_examples = build_examples(config["strict_holdout_source"], "strict_dialogue_holdout")
    validation_labels = [int(row["label"]) for row in validation_examples]
    holdout_labels = [int(row["label"]) for row in holdout_examples]

    validation_nli_scores = nli_hallucination_scores(validation_examples, config)
    nli_threshold, validation_nli_metrics = pick_threshold(validation_labels, validation_nli_scores, config["threshold_grid"])
    holdout_nli_scores = nli_hallucination_scores(holdout_examples, config)
    holdout_nli_metrics = binary_metrics(holdout_labels, holdout_nli_scores, nli_threshold)

    validation_lexical_scores = lexical_overlap_scores(validation_examples)
    lexical_threshold, validation_lexical_metrics = pick_threshold(validation_labels, validation_lexical_scores, config["threshold_grid"])
    holdout_lexical_scores = lexical_overlap_scores(holdout_examples)
    holdout_lexical_metrics = binary_metrics(holdout_labels, holdout_lexical_scores, lexical_threshold)

    ci = bootstrap_metric(
        holdout_labels,
        holdout_nli_scores,
        nli_threshold,
        int(config["metrics"]["bootstrap_samples"]),
        int(config["split_seed"]),
    )
    publish_checks = {
        "strict_holdout_rows": len(holdout_examples) >= int(config["metrics"]["target_holdout_rows"]),
        "holdout_nli_f1": holdout_nli_metrics["f1"] >= float(config["metrics"]["target_holdout_hallucination_f1"]),
        "beats_lexical": (holdout_nli_metrics["f1"] - holdout_lexical_metrics["f1"])
        >= float(config["metrics"]["target_f1_delta_over_lexical"]),
        "no_model_generation": not bool(config["content_policy"].get("model_generation_allowed")),
        "redacted_predictions": not bool(config["content_policy"].get("commit_raw_dataset_text")),
    }
    status = "PASS - DATASET VERIFIER SIGNAL" if all(publish_checks.values()) else "MIXED - NEEDS NEXT GATE"
    summary = {
        "generated_utc": utc_now(),
        "status": status,
        "nli_model": config["nli_model"]["model_id"],
        "validation_examples": len(validation_examples),
        "strict_holdout_examples": len(holdout_examples),
        "label_counts_validation": dict(Counter(validation_labels)),
        "label_counts_holdout": dict(Counter(holdout_labels)),
        "nli_threshold": nli_threshold,
        "lexical_threshold": lexical_threshold,
        "validation_nli_metrics": validation_nli_metrics,
        "holdout_nli_metrics": holdout_nli_metrics,
        "holdout_nli_bootstrap_ci": ci,
        "validation_lexical_metrics": validation_lexical_metrics,
        "holdout_lexical_metrics": holdout_lexical_metrics,
        "f1_delta_over_lexical": holdout_nli_metrics["f1"] - holdout_lexical_metrics["f1"],
        "publish_checks": publish_checks,
    }
    write_json(output_dir / "EXP04_HALUEVAL_NLI_SUMMARY_20260619.json", summary)
    write_jsonl(output_dir / "nli_predictions_redacted.jsonl", redacted_rows(holdout_examples, holdout_nli_scores, nli_threshold, "nli"))
    write_jsonl(
        output_dir / "lexical_predictions_redacted.jsonl",
        redacted_rows(holdout_examples, holdout_lexical_scores, lexical_threshold, "lexical"),
    )
    render_reports(output_dir, summary)
    print(summary["status"], output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp04_halueval_nli_full_20260619.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
