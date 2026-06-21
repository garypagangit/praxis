from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "by",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "its",
    "this",
    "that",
    "those",
    "these",
    "he",
    "she",
    "they",
    "we",
    "you",
    "i",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "not",
    "no",
    "yes",
    "can",
    "could",
    "would",
    "should",
    "will",
    "just",
    "sure",
    "actually",
    "also",
    "about",
    "into",
    "like",
    "love",
    "know",
    "heard",
    "think",
    "one",
    "movie",
    "book",
    "film",
    "good",
    "great",
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


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", str(text).lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def capital_phrases(text: str) -> set[str]:
    return {
        phrase.strip()
        for phrase in re.findall(r"\b(?:[A-Z][A-Za-z0-9'\-]+(?:\s+|$)){1,5}", str(text))
        if phrase.strip()
    }


def numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b\d{2,4}\b", str(text)))


def negation_count(text: str) -> int:
    return len(re.findall(r"\b(no|not|never|wasn't|weren't|isn't|aren't|didn't|don't|doesn't)\b", str(text).lower()))


def engineered_features(knowledge: str, dialogue: str, response: str) -> list[float]:
    evidence_text = f"{knowledge} {dialogue}".strip()
    evidence_tokens = set(tokenize(evidence_text))
    response_tokens = tokenize(response)
    response_set = set(response_tokens)
    overlap = len(evidence_tokens & response_set) / max(len(response_set), 1)

    response_caps = capital_phrases(response)
    evidence_caps = capital_phrases(evidence_text)
    response_nums = numeric_tokens(response)
    evidence_nums = numeric_tokens(evidence_text)
    response_neg = negation_count(response)
    evidence_neg = negation_count(evidence_text)

    return [
        float(len(str(response))),
        float(len(response_tokens)),
        float(len(response_set)),
        overlap,
        1.0 - overlap,
        len(response_set - evidence_tokens) / max(len(response_set), 1),
        float(len(response_caps)),
        float(len(response_caps - evidence_caps)),
        float(len(response_caps & evidence_caps)),
        len(response_caps - evidence_caps) / max(len(response_caps), 1),
        float(len(response_nums)),
        float(len(response_nums - evidence_nums)),
        float(len(response_nums & evidence_nums)),
        len(response_nums - evidence_nums) / max(len(response_nums), 1),
        float(response_neg),
        float(max(0, response_neg - evidence_neg)),
        float("actually" in str(response).lower()),
        float("i think" in str(response).lower()),
        float("not" in str(response).lower()),
        len(str(response)) / max(len(evidence_text), 1),
    ]


def read_dialogue_examples(config: dict[str, Any]) -> list[dict[str, Any]]:
    df = pd.read_parquet(config["dataset"]["parquet_url"])
    examples: list[dict[str, Any]] = []
    for idx, row in df.reset_index(drop=True).iterrows():
        for variant, field, label in [
            ("right", "right_response", 0),
            ("hallucinated", "hallucinated_response", 1),
        ]:
            examples.append(
                {
                    "dialogue_idx": int(idx),
                    "variant": variant,
                    "label": label,
                    "knowledge": str(row["knowledge"]),
                    "dialogue": str(row["dialogue_history"]),
                    "response": str(row[field]),
                }
            )
    return examples


def split_role(example: dict[str, Any]) -> str:
    hashed = int(hashlib.sha256(f"dialogue:{example['dialogue_idx']}".encode("utf-8")).hexdigest()[:8], 16) % 100
    if hashed < 60:
        return "train"
    if hashed < 75:
        return "validation"
    if hashed < 90:
        return "test"
    return "strict_holdout"


def split_examples(examples: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": [], "strict_holdout": []}
    for example in examples:
        role = split_role(example)
        row = dict(example)
        row["split_role"] = role
        splits[role].append(row)
    return splits


def text_inputs(examples: list[dict[str, Any]], mode: str) -> list[str]:
    if mode == "response":
        return [row["response"] for row in examples]
    return [
        f"{row['knowledge']} [DIALOGUE] {row['dialogue']} [RESPONSE] {row['response']}"
        for row in examples
    ]


def numeric_matrix(examples: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray(
        [engineered_features(row["knowledge"], row["dialogue"], row["response"]) for row in examples],
        dtype=float,
    )


def labels(examples: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([int(row["label"]) for row in examples], dtype=int)


def build_matrices(
    splits: dict[str, list[dict[str, Any]]],
    mode: str,
    max_features: int,
) -> tuple[Any, Any, Any, Any]:
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    holdout = splits["strict_holdout"]
    if mode == "numeric":
        scaler = StandardScaler()
        return (
            csr_matrix(scaler.fit_transform(numeric_matrix(train))),
            csr_matrix(scaler.transform(numeric_matrix(validation))),
            csr_matrix(scaler.transform(numeric_matrix(test))),
            csr_matrix(scaler.transform(numeric_matrix(holdout))),
        )
    if mode in {"response", "evidence"}:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_features=max_features,
            strip_accents="unicode",
        )
        return (
            vectorizer.fit_transform(text_inputs(train, mode)),
            vectorizer.transform(text_inputs(validation, mode)),
            vectorizer.transform(text_inputs(test, mode)),
            vectorizer.transform(text_inputs(holdout, mode)),
        )
    if mode == "evidence_numeric":
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_features=max_features,
            strip_accents="unicode",
        )
        scaler = StandardScaler()
        return (
            hstack(
                [
                    vectorizer.fit_transform(text_inputs(train, "evidence")),
                    csr_matrix(scaler.fit_transform(numeric_matrix(train))),
                ]
            ),
            hstack(
                [
                    vectorizer.transform(text_inputs(validation, "evidence")),
                    csr_matrix(scaler.transform(numeric_matrix(validation))),
                ]
            ),
            hstack(
                [
                    vectorizer.transform(text_inputs(test, "evidence")),
                    csr_matrix(scaler.transform(numeric_matrix(test))),
                ]
            ),
            hstack(
                [
                    vectorizer.transform(text_inputs(holdout, "evidence")),
                    csr_matrix(scaler.transform(numeric_matrix(holdout))),
                ]
            ),
        )
    raise ValueError(f"Unknown mode: {mode}")


def binary_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    preds = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, preds, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision_score(y_true, preds, zero_division=0)),
        "recall": float(recall_score(y_true, preds, zero_division=0)),
        "f1": float(f1_score(y_true, preds, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, preds)),
        "false_alarm_rate": float(fp / max(fp + tn, 1)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "average_precision": float(average_precision_score(y_true, scores)),
    }


def threshold_grid(config: dict[str, Any]) -> list[float]:
    search = config["model_search"]
    start = float(search["threshold_grid_start"])
    stop = float(search["threshold_grid_stop"])
    step = float(search["threshold_grid_step"])
    count = int(math.floor((stop - start) / step)) + 1
    return [round(start + step * idx, 10) for idx in range(count + 1) if start + step * idx <= stop + 1e-9]


def pick_threshold(y_true: np.ndarray, scores: np.ndarray, grid: list[float]) -> dict[str, Any]:
    metrics = [binary_metrics(y_true, scores, threshold) for threshold in grid]
    metrics.sort(key=lambda row: (row["f1"], row["accuracy"], -row["false_alarm_rate"]), reverse=True)
    return metrics[0]


def fit_candidate(
    splits: dict[str, list[dict[str, Any]]],
    mode: str,
    c_value: float,
    max_features: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    x_train, x_validation, x_test, x_holdout = build_matrices(splits, mode, max_features)
    y_train = labels(splits["train"])
    y_validation = labels(splits["validation"])
    y_test = labels(splits["test"])
    y_holdout = labels(splits["strict_holdout"])
    clf = LogisticRegression(
        C=float(c_value),
        class_weight="balanced",
        max_iter=1000,
        solver="liblinear",
        random_state=int(config["split_seed"]),
    )
    clf.fit(x_train, y_train)
    validation_scores = clf.predict_proba(x_validation)[:, 1]
    threshold_metrics = pick_threshold(y_validation, validation_scores, threshold_grid(config))
    threshold = float(threshold_metrics["threshold"])
    return {
        "mode": mode,
        "c_value": float(c_value),
        "max_features": int(max_features),
        "validation": threshold_metrics,
        "test": binary_metrics(y_test, clf.predict_proba(x_test)[:, 1], threshold),
        "strict_holdout": binary_metrics(y_holdout, clf.predict_proba(x_holdout)[:, 1], threshold),
        "strict_holdout_scores": clf.predict_proba(x_holdout)[:, 1],
        "threshold": threshold,
    }


def bootstrap_metric(labels_: np.ndarray, scores: np.ndarray, threshold: float, samples: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(labels_)
    f1s: list[float] = []
    accs: list[float] = []
    for _ in range(samples):
        idxs = [rng.randrange(n) for _ in range(n)]
        metric = binary_metrics(labels_[idxs], scores[idxs], threshold)
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


def redacted_prediction_rows(
    examples: list[dict[str, Any]],
    scores: np.ndarray,
    threshold: float,
    model_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row, score in zip(examples, scores):
        rows.append(
            {
                "row_id": f"pminervini/HaluEval:dialogue:data:{row['dialogue_idx']}:{row['variant']}",
                "dialogue_idx": row["dialogue_idx"],
                "variant": row["variant"],
                "split_role": row["split_role"],
                "label": int(row["label"]),
                "hallucination_probability": float(score),
                "threshold": float(threshold),
                "prediction": int(score >= threshold),
                "knowledge_sha256": sha256_text(row["knowledge"]),
                "dialogue_sha256": sha256_text(row["dialogue"]),
                "response_sha256": sha256_text(row["response"]),
                "knowledge_length": len(row["knowledge"]),
                "dialogue_length": len(row["dialogue"]),
                "response_length": len(row["response"]),
                "model": model_name,
            }
        )
    return rows


def best_by_mode(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in candidates:
        current = best.get(row["mode"])
        key = (row["validation"]["f1"], row["validation"]["accuracy"])
        if current is None or key > (current["validation"]["f1"], current["validation"]["accuracy"]):
            best[row["mode"]] = row
    return best


def render_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    best = summary["best_models"]
    evidence = best["evidence_numeric"]
    response = best["response"]
    numeric = best["numeric"]
    lines = [
        "# EXP04 Dialogue Feature Gate Result",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Scope",
        "",
        "- Dataset: HaluEval `dialogue` parquet from `pminervini/HaluEval`.",
        "- Split discipline: paired right/hallucinated responses stay together by dialogue row.",
        "- Train/validation/test/strict holdout split: 60/15/15/10 by deterministic row hash.",
        "- Hyperparameters and thresholds are selected on validation only.",
        "- Committed prediction rows are redacted hashes, lengths, labels, scores, and metrics only.",
        "",
        "## Praxis Frame",
        "",
        "**Hypothesis.** Evidence-conditioned features should identify hallucinated dialogue responses better than response-only artifacts and numeric novelty alone.",
        "",
        "**GMR.** Goal: find a defensible verifier signal for multi-turn hallucination. Method: train row-disjoint logistic baselines over response text, evidence text, and engineered novelty/entity/negation features. Rationale: a publishable KG/evidence claim must beat response-style shortcuts on a sealed holdout.",
        "",
        "## Split Counts",
        "",
        "| Split | Examples | Right | Hallucinated |",
        "|---|---:|---:|---:|",
    ]
    for split, counts in summary["split_counts"].items():
        lines.append(
            f"| {split} | `{counts['examples']}` | `{counts['labels'].get('0', 0)}` | `{counts['labels'].get('1', 0)}` |"
        )
    lines.extend(
        [
            "",
            "## Primary Metrics",
            "",
            "| Model | Validation F1 | Test F1 | Strict holdout F1 | Strict holdout accuracy | Strict holdout FAR |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for mode in ["numeric", "response", "evidence", "evidence_numeric"]:
        row = best[mode]
        lines.append(
            f"| `{mode}` | `{row['validation']['f1']:.4f}` | `{row['test']['f1']:.4f}` | "
            f"`{row['strict_holdout']['f1']:.4f}` | `{row['strict_holdout']['accuracy']:.4f}` | "
            f"`{row['strict_holdout']['false_alarm_rate']:.4f}` |"
        )
    lines.extend(
        [
            "",
            "## Promotion Checks",
            "",
            "| Check | Pass |",
            "|---|---:|",
        ]
    )
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"The evidence-plus-numeric verifier reached strict holdout F1 `{evidence['strict_holdout']['f1']:.4f}`, but the response-only artifact baseline reached `{response['strict_holdout']['f1']:.4f}`. The evidence model therefore does not support the EXP04 thesis yet. Treat this as a failed promotion gate and move to the next experiment rather than claiming a KG/evidence result.",
            "",
            "## Claim Boundary",
            "",
            "This gate does not prove evidence-grounded hallucination verification. It shows that, on this HaluEval dialogue setup, response-style artifacts remain a stronger signal than the current evidence features.",
        ]
    )
    (output_dir / "EXP04_DIALOGUE_FEATURE_GATE_RESULT_20260620.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    challenge = [
        "# EXP04 Dialogue Feature Gate Internal Defensibility Challenge",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Verdict: **{summary['status']}**",
        "",
        "| Defense question | Answer |",
        "|---|---|",
        "| Are train, validation, test, and strict holdout separated? | Yes. Split is deterministic by underlying dialogue row, and paired responses stay in the same split. |",
        "| Did threshold or hyperparameter selection touch strict holdout? | No. Model selection used validation metrics only. |",
        f"| Does the evidence model clear the F1 target? | Evidence-plus-numeric strict holdout F1 is `{evidence['strict_holdout']['f1']:.4f}`. |",
        f"| Does the evidence model beat response-only artifacts? | No. Evidence-plus-numeric F1 delta over response-only is `{summary['evidence_delta_over_response_only']:.4f}`. |",
        f"| Does it beat numeric novelty alone? | Yes. Evidence-plus-numeric F1 delta over numeric-only is `{summary['evidence_delta_over_numeric']:.4f}`. |",
        "| Are raw HaluEval rows committed? | No. Output predictions contain hashes, lengths, labels, scores, and metrics only. |",
        "| Publishability decision | Not as a positive EXP04 result. A committee can fairly argue that the current signal is an artifact detector. |",
    ]
    (output_dir / "EXP04_DIALOGUE_FEATURE_DEFENSIBILITY_CHALLENGE_20260620.md").write_text(
        "\n".join(challenge) + "\n", encoding="utf-8"
    )


def summarize_counts(splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for split, rows in splits.items():
        labels_ = Counter(str(int(row["label"])) for row in rows)
        summary[split] = {
            "examples": len(rows),
            "dialogue_rows": len({int(row["dialogue_idx"]) for row in rows}),
            "labels": dict(labels_),
        }
    return summary


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", config)

    examples = read_dialogue_examples(config)
    splits = split_examples(examples)
    candidates: list[dict[str, Any]] = []
    for mode in config["model_search"]["modes"]:
        max_features_values = [0] if mode == "numeric" else config["model_search"]["max_feature_values"]
        for c_value in config["model_search"]["c_values"]:
            for max_features in max_features_values:
                candidates.append(fit_candidate(splits, mode, float(c_value), int(max_features), config))

    best = best_by_mode(candidates)
    holdout_labels = labels(splits["strict_holdout"])
    for row in best.values():
        row["strict_holdout_bootstrap_ci"] = bootstrap_metric(
            holdout_labels,
            np.asarray(row["strict_holdout_scores"], dtype=float),
            float(row["threshold"]),
            int(config["metrics"]["bootstrap_samples"]),
            int(config["split_seed"]),
        )

    evidence = best["evidence_numeric"]
    response = best["response"]
    numeric = best["numeric"]
    evidence_delta_over_response = (
        evidence["strict_holdout"]["f1"] - response["strict_holdout"]["f1"]
    )
    evidence_delta_over_numeric = evidence["strict_holdout"]["f1"] - numeric["strict_holdout"]["f1"]
    publish_checks = {
        "strict_holdout_rows": len(splits["strict_holdout"]) >= int(config["metrics"]["target_strict_holdout_examples"]),
        "evidence_holdout_f1": evidence["strict_holdout"]["f1"] >= float(config["metrics"]["target_strict_holdout_f1"]),
        "evidence_beats_response_only": evidence_delta_over_response
        >= float(config["metrics"]["target_evidence_delta_over_response_only"]),
        "evidence_beats_numeric": evidence_delta_over_numeric
        >= float(config["metrics"]["target_evidence_delta_over_numeric"]),
        "no_model_generation": not bool(config["content_policy"].get("model_generation_allowed")),
        "redacted_predictions": not bool(config["content_policy"].get("commit_raw_dataset_text")),
    }
    status = "PASS - EVIDENCE VERIFIER SIGNAL" if all(publish_checks.values()) else "MIXED - RESPONSE ARTIFACT BASELINE WINS"

    compact_best: dict[str, Any] = {}
    for mode, row in best.items():
        compact_best[mode] = {
            "mode": row["mode"],
            "c_value": row["c_value"],
            "max_features": row["max_features"],
            "threshold": row["threshold"],
            "validation": row["validation"],
            "test": row["test"],
            "strict_holdout": row["strict_holdout"],
            "strict_holdout_bootstrap_ci": row["strict_holdout_bootstrap_ci"],
        }
    compact_candidates = [
        {
            "mode": row["mode"],
            "c_value": row["c_value"],
            "max_features": row["max_features"],
            "threshold": row["threshold"],
            "validation": row["validation"],
            "test": row["test"],
            "strict_holdout": row["strict_holdout"],
        }
        for row in candidates
    ]
    compact_candidates.sort(key=lambda row: (row["mode"], row["c_value"], row["max_features"]))

    summary = {
        "generated_utc": utc_now(),
        "status": status,
        "dataset": config["dataset"],
        "split_counts": summarize_counts(splits),
        "candidate_results": compact_candidates,
        "best_models": compact_best,
        "evidence_delta_over_response_only": evidence_delta_over_response,
        "evidence_delta_over_numeric": evidence_delta_over_numeric,
        "publish_checks": publish_checks,
    }
    write_json(output_dir / "EXP04_DIALOGUE_FEATURE_SUMMARY_20260620.json", summary)
    write_jsonl(
        output_dir / "evidence_numeric_strict_holdout_predictions_redacted.jsonl",
        redacted_prediction_rows(
            splits["strict_holdout"],
            np.asarray(best["evidence_numeric"]["strict_holdout_scores"], dtype=float),
            float(best["evidence_numeric"]["threshold"]),
            "evidence_numeric",
        ),
    )
    write_jsonl(
        output_dir / "response_only_strict_holdout_predictions_redacted.jsonl",
        redacted_prediction_rows(
            splits["strict_holdout"],
            np.asarray(best["response"]["strict_holdout_scores"], dtype=float),
            float(best["response"]["threshold"]),
            "response",
        ),
    )
    render_reports(output_dir, summary)
    print(status, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp04_dialogue_feature_gate_20260620.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
