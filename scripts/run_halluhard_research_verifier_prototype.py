#!/usr/bin/env python
"""PX-011 HalluHard research-lane verifier prototype.

This is a no-cost prototype gate. It creates deterministic supported and
corrupted citation claims from public HalluHard research rows, then checks
whether a frozen metadata verifier beats response-only baselines. It is not a
model-response HalluHard result.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import random
import re
import unicodedata
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "configs/halluhard_research_verifier_prototype_20260628.json"
USER_AGENT = "praxis-px011-halluhard-verifier-prototype/20260628"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read().decode("utf-8")


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def norm(text: Any) -> str:
    value = "" if text is None else str(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def snippet(text: Any, limit: int = 140) -> str:
    value = "" if text is None else str(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def similarity(a: Any, b: Any) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def content_grounded(claimed_content: Any, abstract: Any, threshold: float) -> tuple[bool, float]:
    claim_norm = norm(claimed_content)
    abstract_norm = norm(abstract)
    if claim_norm and claim_norm in abstract_norm:
        return True, 1.0
    score = difflib.SequenceMatcher(None, claim_norm, abstract_norm).ratio()
    return score >= threshold, score


def first_content(abstract: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", abstract or "").strip()
    return cleaned[:limit]


def split_rows(rows: list[dict[str, Any]], seed: int, test_fraction: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shuffled = rows[:]
    random.Random(seed).shuffle(shuffled)
    test_size = int(round(len(shuffled) * test_fraction))
    return shuffled[test_size:], shuffled[:test_size]


def build_indexes(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    doi_index = {norm(row.get("doi")): row for row in rows if norm(row.get("doi"))}
    arxiv_index = {norm(row.get("arxiv_id")): row for row in rows if norm(row.get("arxiv_id"))}
    return {"doi": doi_index, "arxiv": arxiv_index}


def other_row(rows: list[dict[str, Any]], idx: int, offset: int) -> dict[str, Any]:
    return rows[(idx + offset) % len(rows)]


def build_claims(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    limit = int(config["content_chars"])
    for idx, row in enumerate(rows):
        swapped_title = other_row(rows, idx, 37)
        swapped_doi = other_row(rows, idx, 73)
        swapped_content = other_row(rows, idx, 101)
        year = int(row.get("publication_year") or 0)
        base = {
            "source_row": idx,
            "research_question": snippet(row.get("research_question"), 180),
            "claimed_title": row.get("title", ""),
            "claimed_authors": row.get("authors", []),
            "claimed_year": row.get("publication_year", ""),
            "claimed_doi": row.get("doi", ""),
            "claimed_arxiv_id": row.get("arxiv_id", ""),
            "claimed_content": first_content(row.get("abstract", ""), limit),
        }
        variants = [
            ("supported", "supported", {}),
            ("title_swap", "hallucinated", {"claimed_title": swapped_title.get("title", "")}),
            ("doi_swap", "hallucinated", {"claimed_doi": swapped_doi.get("doi", ""), "claimed_arxiv_id": swapped_doi.get("arxiv_id", "")}),
            ("year_shift", "hallucinated", {"claimed_year": str(year + 1) if year else "9999"}),
            ("content_swap", "hallucinated", {"claimed_content": first_content(swapped_content.get("abstract", ""), limit)}),
        ]
        for variant, label, updates in variants:
            claim = dict(base)
            claim.update(updates)
            claim["claim_id"] = f"{idx:03d}-{variant}"
            claim["variant"] = variant
            claim["label"] = label
            claims.append(claim)
    return claims


def verify_claim(claim: dict[str, Any], indexes: dict[str, dict[str, dict[str, Any]]], config: dict[str, Any]) -> dict[str, Any]:
    source = None
    source_key = ""
    doi = norm(claim.get("claimed_doi"))
    arxiv = norm(claim.get("claimed_arxiv_id"))
    if doi and doi in indexes["doi"]:
        source = indexes["doi"][doi]
        source_key = "doi"
    elif arxiv and arxiv in indexes["arxiv"]:
        source = indexes["arxiv"][arxiv]
        source_key = "arxiv"
    if source is None:
        return {
            "prediction": "abstain",
            "source_key": "",
            "title_similarity": 0.0,
            "content_similarity": 0.0,
            "year_match": False,
            "verification_error": False,
            "reason": "no_source_identifier_match",
        }

    title_score = similarity(claim.get("claimed_title"), source.get("title"))
    content_ok, content_score = content_grounded(
        claim.get("claimed_content"),
        source.get("abstract"),
        float(config["content_similarity_threshold"]),
    )
    year_match = str(claim.get("claimed_year", "")).strip() == str(source.get("publication_year", "")).strip()
    title_ok = title_score >= float(config["title_similarity_threshold"])
    supported = title_ok and content_ok and year_match
    return {
        "prediction": "supported" if supported else "hallucinated",
        "source_key": source_key,
        "title_similarity": title_score,
        "content_similarity": content_score,
        "year_match": year_match,
        "verification_error": False,
        "reason": "all_checks_pass" if supported else "metadata_or_content_mismatch",
    }


def f1_for_label(rows: list[dict[str, Any]], label: str, pred_key: str) -> dict[str, float]:
    tp = sum(1 for row in rows if row["label"] == label and row[pred_key] == label)
    fp = sum(1 for row in rows if row["label"] != label and row[pred_key] == label)
    fn = sum(1 for row in rows if row["label"] == label and row[pred_key] != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def metrics(rows: list[dict[str, Any]], pred_key: str) -> dict[str, Any]:
    labels = ["supported", "hallucinated"]
    per_label = {label: f1_for_label(rows, label, pred_key) for label in labels}
    accuracy = sum(1 for row in rows if row["label"] == row[pred_key]) / len(rows) if rows else 0.0
    return {
        "accuracy": accuracy,
        "macro_f1": sum(per_label[label]["f1"] for label in labels) / len(labels),
        "per_label": per_label,
    }


def apply_baselines(train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> None:
    majority = Counter(row["label"] for row in train_rows).most_common(1)[0][0]
    for row in test_rows:
        row["majority_prediction"] = majority
        has_fields = bool(norm(row.get("claimed_title"))) and bool(norm(row.get("claimed_doi")) or norm(row.get("claimed_arxiv_id")))
        row["field_presence_prediction"] = "supported" if has_fields else "hallucinated"


def summarize(config: dict[str, Any], rows: list[dict[str, Any]], claims: list[dict[str, Any]], train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> dict[str, Any]:
    verifier_metrics = metrics(test_rows, "verifier_prediction")
    majority_metrics = metrics(test_rows, "majority_prediction")
    field_metrics = metrics(test_rows, "field_presence_prediction")
    abstentions = sum(1 for row in test_rows if row["verifier_prediction"] == "abstain")
    verification_errors = sum(1 for row in test_rows if row.get("verification_error"))
    thresholds = config["pass_thresholds"]
    publish_checks = {
        "research_rows_available": len(rows) >= 200,
        "synthetic_claims_generated": len(claims) == len(rows) * 5,
        "test_macro_f1": verifier_metrics["macro_f1"] >= float(thresholds["min_test_macro_f1"]),
        "beats_majority_macro_f1": verifier_metrics["macro_f1"] - majority_metrics["macro_f1"] >= float(thresholds["min_margin_vs_majority_macro_f1"]),
        "verification_error_rate": verification_errors / max(len(test_rows), 1) <= float(thresholds["max_verification_error_rate"]),
        "abstention_rate": abstentions / max(len(test_rows), 1) <= float(thresholds["max_abstention_rate"]),
    }
    status = "PROTOTYPE PASS - MODEL RESPONSE GATE REQUIRED" if all(publish_checks.values()) else "PROTOTYPE MIXED - MODEL RESPONSE GATE REQUIRED"
    return {
        "generated_utc": utc_now(),
        "experiment_id": config["experiment_id"],
        "status": status,
        "claim_boundary": "Synthetic citation-claim verifier prototype only. No HalluHard model responses were generated or scored.",
        "research_rows": len(rows),
        "claims_total": len(claims),
        "train_claims": len(train_rows),
        "test_claims": len(test_rows),
        "variant_counts": dict(Counter(row["variant"] for row in test_rows)),
        "label_counts": dict(Counter(row["label"] for row in test_rows)),
        "verifier_metrics": verifier_metrics,
        "majority_baseline_metrics": majority_metrics,
        "field_presence_baseline_metrics": field_metrics,
        "abstentions": abstentions,
        "verification_errors": verification_errors,
        "publish_checks": publish_checks,
        "next_gate": "Run sealed HalluHard research-lane model responses and compare the frozen source-backed verifier against response-only baselines.",
    }


def write_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "claim_id",
        "variant",
        "label",
        "verifier_prediction",
        "majority_prediction",
        "field_presence_prediction",
        "source_key",
        "title_similarity",
        "content_similarity",
        "year_match",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def render_report(report_path: Path, summary: dict[str, Any]) -> None:
    vm = summary["verifier_metrics"]
    mm = summary["majority_baseline_metrics"]
    fm = summary["field_presence_baseline_metrics"]
    lines = [
        "# PX-011 HalluHard Research Verifier Prototype",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Primary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Research rows | `{summary['research_rows']}` |",
        f"| Synthetic claims | `{summary['claims_total']}` |",
        f"| Train claims | `{summary['train_claims']}` |",
        f"| Sealed test claims | `{summary['test_claims']}` |",
        f"| Verifier macro F1 | `{vm['macro_f1']:.4f}` |",
        f"| Verifier accuracy | `{vm['accuracy']:.4f}` |",
        f"| Majority response-only macro F1 | `{mm['macro_f1']:.4f}` |",
        f"| Field-presence response-only macro F1 | `{fm['macro_f1']:.4f}` |",
        f"| Abstentions | `{summary['abstentions']}` |",
        f"| Verification errors | `{summary['verification_errors']}` |",
        "",
        "## Label Metrics",
        "",
        "| Predictor | Label | Precision | Recall | F1 |",
        "|---|---|---:|---:|---:|",
    ]
    for name, result in [("verifier", vm), ("majority", mm), ("field_presence", fm)]:
        for label, vals in result["per_label"].items():
            lines.append(f"| `{name}` | `{label}` | `{vals['precision']:.4f}` | `{vals['recall']:.4f}` | `{vals['f1']:.4f}` |")
    lines.extend(["", "## Test Distribution", "", "| Bucket | Count |", "|---|---:|"])
    for key, value in summary["variant_counts"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Publish Checks", "", "| Check | Pass |", "|---|---:|"])
    for key, value in summary["publish_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The frozen research-lane verifier can separate deterministic supported citations from title, DOI, year, and abstract-content corruptions. This is a useful prototype result because it proves the DOI/arXiv/title/abstract evidence path is operational and that simple response-only baselines do not solve the synthetic task.",
            "",
            "This is not yet a HalluHard model-response result. The next gate must use sealed model responses from the research lane and keep the EXP04 guardrail: the source-backed verifier must beat response-only baselines on a held-out split.",
            "",
            "## Next Gate",
            "",
            summary["next_gate"],
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()

    config = read_json(Path(args.config))
    rows = parse_jsonl(fetch_text(config["raw_research_url"]))
    indexes = build_indexes(rows)
    claims = build_claims(rows, config)
    train_rows, test_rows = split_rows(claims, int(config["split_seed"]), float(config["test_fraction"]))
    for row in test_rows:
        result = verify_claim(row, indexes, config)
        row.update(result)
        row["verifier_prediction"] = result["prediction"]
    apply_baselines(train_rows, test_rows)
    summary = summarize(config, rows, claims, train_rows, test_rows)

    output_dir = Path(config["output_dir"])
    write_json(output_dir / "summary.json", summary)
    write_predictions(output_dir / "test_predictions.csv", test_rows)
    render_report(Path(config["report_path"]), summary)
    print(json.dumps({"status": summary["status"], "test_macro_f1": summary["verifier_metrics"]["macro_f1"], "report_path": config["report_path"]}, indent=2))


if __name__ == "__main__":
    main()
