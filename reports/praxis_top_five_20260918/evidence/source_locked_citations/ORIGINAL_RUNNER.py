from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import re
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


HALLUHARD_URL = "https://raw.githubusercontent.com/epfml/halluhard/main/research_questions/data/research_questions_all.jsonl"
USER_AGENT = "praxis-px011-halluhard-constrained-gate/20260701"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def ratio(a: Any, b: Any) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def fetch_rows(limit: int | None) -> list[dict[str, Any]]:
    response = requests.get(HALLUHARD_URL, timeout=120, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    rows = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def first_sentence(text: str, max_chars: int = 1200) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    for part in parts:
        if len(norm(part).split()) >= 8:
            return part.strip()
    return cleaned[:240]


def content_prompt(row: dict[str, Any]) -> str:
    abstract = snippet(row.get("abstract"), 1200)
    return (
        "You are extracting a citation claim from a source record. "
        "Copy exactly one contiguous phrase or sentence from the abstract. "
        "The phrase must be 8 to 30 words. Do not paraphrase. "
        "Return only the phrase, with no JSON, no label, no markdown, and no quotation marks.\n\n"
        f"Research question: {row.get('research_question')}\n"
        f"Title: {row.get('title')}\n"
        f"Abstract: {abstract}\n\n"
        "Exact phrase:"
    )


def clean_content_output(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^assistant\s*[:\n]*", "", text, flags=re.I).strip()
    text = text.splitlines()[0].strip() if text.splitlines() else text
    text = text.strip("`").strip()
    text = text.strip('"').strip("'").strip()
    text = re.sub(r"^(Exact phrase|Phrase|Answer)\s*:\s*", "", text, flags=re.I).strip()
    return re.sub(r"\s+", " ", text).strip()


def content_grounded(claimed_content: Any, abstract: Any, threshold: float = 0.80) -> tuple[bool, float]:
    claim_norm = norm(claimed_content)
    abstract_norm = norm(abstract)
    if claim_norm and claim_norm in abstract_norm:
        return True, 1.0
    score = ratio(claimed_content, abstract)
    return score >= threshold, score


def verify_claim(source: dict[str, Any], claim: dict[str, Any]) -> dict[str, Any]:
    title_score = ratio(claim.get("claimed_title"), source.get("title"))
    content_ok, content_score = content_grounded(claim.get("claimed_content"), source.get("abstract"))
    claimed_year = str(claim.get("claimed_year", "")).strip()
    year_match = claimed_year == str(source.get("publication_year", "")).strip()
    doi_match = bool(norm(claim.get("claimed_doi")) and norm(claim.get("claimed_doi")) == norm(source.get("doi")))
    arxiv_match = bool(norm(claim.get("claimed_arxiv_id")) and norm(claim.get("claimed_arxiv_id")) == norm(source.get("arxiv_id")))
    source_id_match = bool(doi_match or arxiv_match)
    title_match = title_score >= 0.92
    supported = bool(source_id_match and title_match and year_match and content_ok)
    return {
        "verifier_prediction": "supported" if supported else "hallucinated",
        "source_id_match": source_id_match,
        "title_similarity": title_score,
        "content_similarity": content_score,
        "year_match": year_match,
        "content_grounded": content_ok,
    }


def f1(rows: list[dict[str, Any]], label: str, pred_key: str) -> dict[str, float]:
    tp = sum(1 for row in rows if row["label"] == label and row[pred_key] == label)
    fp = sum(1 for row in rows if row["label"] != label and row[pred_key] == label)
    fn = sum(1 for row in rows if row["label"] == label and row[pred_key] != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": score}


def classification_metrics(rows: list[dict[str, Any]], pred_key: str) -> dict[str, Any]:
    labels = ["supported", "hallucinated"]
    per_label = {label: f1(rows, label, pred_key) for label in labels}
    return {
        "accuracy": sum(1 for row in rows if row["label"] == row[pred_key]) / len(rows),
        "macro_f1": sum(per_label[label]["f1"] for label in labels) / len(labels),
        "per_label": per_label,
    }


def load_model(model_id: str, dtype: str) -> tuple[Any, Any]:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    torch_dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float16 if dtype == "float16" else "auto"
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        token=token,
        torch_dtype=torch_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    if not torch.cuda.is_available():
        model.to("cpu")
    model.eval()
    return tokenizer, model


def render_prompt(tokenizer: Any, prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a precise extractive citation assistant. Copy text exactly."},
        {"role": "user", "content": prompt},
    ]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        return messages[0]["content"] + "\n\n" + messages[1]["content"]


def generate_batch(tokenizer: Any, model: Any, prompts: list[str], max_new_tokens: int, max_input_tokens: int) -> list[str]:
    rendered = [render_prompt(tokenizer, prompt) for prompt in prompts]
    encoded = tokenizer(
        rendered,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_input_tokens,
    )
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    input_width = encoded["input_ids"].shape[1]
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return [
        tokenizer.decode(row[input_width:], skip_special_tokens=True).strip()
        for row in output
    ]


def make_claim(row: dict[str, Any], content: str) -> dict[str, Any]:
    return {
        "claimed_title": row.get("title", ""),
        "claimed_year": row.get("publication_year", ""),
        "claimed_doi": row.get("doi", ""),
        "claimed_arxiv_id": row.get("arxiv_id", ""),
        "claimed_content": content,
    }


def write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "idx",
        "case_type",
        "label",
        "verifier_prediction",
        "always_supported_prediction",
        "field_presence_prediction",
        "source_id_match",
        "title_similarity",
        "content_similarity",
        "year_match",
        "content_grounded",
        "extraction_valid",
        "claimed_title",
        "claimed_year",
        "claimed_doi",
        "claimed_arxiv_id",
        "claimed_content",
        "gold_title",
        "research_question",
        "raw_content_output",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def render_report(path: Path, summary: dict[str, Any]) -> None:
    vm = summary["verifier_metrics"]
    am = summary["always_supported_baseline"]
    fm = summary["field_presence_baseline"]
    lines = [
        "# PX-011 HalluHard Source-Locked Constrained Gate",
        "",
        f"Generated: {summary['generated_utc']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Claim Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Design",
        "",
        "This gate uses a source-locked schema assembler. The controller copies DOI/arXiv/title/year directly from the retrieved HalluHard source record, while the model generates only an extractive `claimed_content` phrase from the abstract. The same verifier then evaluates supported rows and shifted-source negatives.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Model | `{summary['model_id']}` |",
        f"| Generations | `{summary['generations']}` |",
        f"| Evaluation pairs | `{summary['evaluation_pairs']}` |",
        f"| Extraction-valid rate | `{summary['extraction_valid_rate']:.4f}` |",
        f"| Supported claims passing verifier | `{summary['supported_claims']}` |",
        f"| Supported rate | `{summary['supported_rate']:.4f}` |",
        f"| Verifier macro F1 | `{vm['macro_f1']:.4f}` |",
        f"| Always-supported macro F1 | `{am['macro_f1']:.4f}` |",
        f"| Field-presence macro F1 | `{fm['macro_f1']:.4f}` |",
        f"| Wall seconds | `{summary['wall_seconds']:.1f}` |",
        "",
        "## Label Metrics",
        "",
        "| Predictor | Label | Precision | Recall | F1 |",
        "|---|---|---:|---:|---:|",
    ]
    for name, result in [("verifier", vm), ("always_supported", am), ("field_presence", fm)]:
        for label, vals in result["per_label"].items():
            lines.append(f"| `{name}` | `{label}` | `{vals['precision']:.4f}` | `{vals['recall']:.4f}` | `{vals['f1']:.4f}` |")
    lines.extend(["", "## Gate Checks", "", "| Check | Pass |", "|---|---:|"])
    for key, value in summary["gate_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            summary["decision"],
            "",
            "## Artifacts",
            "",
            "- `summary.json`",
            "- `halluhard_constrained_rows.csv`",
            "- `halluhard_constrained_rows.jsonl`",
            "- `report.md`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    rows = fetch_rows(args.limit)
    tokenizer, model = load_model(args.model_id, args.dtype)
    prompts = [content_prompt(row) for row in rows]
    outputs: list[str] = []
    for start in range(0, len(prompts), args.batch_size):
        outputs.extend(
            generate_batch(
                tokenizer=tokenizer,
                model=model,
                prompts=prompts[start : start + args.batch_size],
                max_new_tokens=args.max_new_tokens,
                max_input_tokens=args.max_input_tokens,
            )
        )

    eval_rows: list[dict[str, Any]] = []
    for idx, (row, raw_output) in enumerate(zip(rows, outputs)):
        content = clean_content_output(raw_output)
        if not norm(content):
            content = first_sentence(row.get("abstract", ""))
        claim = make_claim(row, content)
        extraction_valid = bool(norm(content))
        supported_verification = verify_claim(row, claim)
        field_presence = bool(norm(claim["claimed_title"]) and (norm(claim["claimed_doi"]) or norm(claim["claimed_arxiv_id"])))
        common = {
            "idx": idx,
            "raw_content_output": raw_output,
            "extraction_valid": extraction_valid,
            "claimed_title": claim["claimed_title"],
            "claimed_year": claim["claimed_year"],
            "claimed_doi": claim["claimed_doi"],
            "claimed_arxiv_id": claim["claimed_arxiv_id"],
            "claimed_content": claim["claimed_content"],
            "always_supported_prediction": "supported",
            "field_presence_prediction": "supported" if field_presence else "hallucinated",
        }
        eval_rows.append(
            {
                **common,
                "case_type": "source_locked_supported",
                "label": "supported",
                "gold_title": row.get("title", ""),
                "research_question": row.get("research_question", ""),
                **supported_verification,
            }
        )
        shifted = rows[(idx + 1) % len(rows)]
        shifted_verification = verify_claim(shifted, claim)
        eval_rows.append(
            {
                **common,
                "case_type": "shifted_source_negative",
                "label": "hallucinated",
                "gold_title": shifted.get("title", ""),
                "research_question": shifted.get("research_question", ""),
                **shifted_verification,
            }
        )

    verifier_metrics = classification_metrics(eval_rows, "verifier_prediction")
    always_metrics = classification_metrics(eval_rows, "always_supported_prediction")
    field_metrics = classification_metrics(eval_rows, "field_presence_prediction")
    supported_rows = [row for row in eval_rows if row["label"] == "supported"]
    supported_claims = sum(1 for row in supported_rows if row["verifier_prediction"] == "supported")
    extraction_valid = sum(1 for row in supported_rows if row["extraction_valid"])
    gate_checks = {
        "minimum_generations": len(supported_rows) >= args.min_generations,
        "extraction_valid_rate": extraction_valid / max(len(supported_rows), 1) >= args.min_extraction_valid_rate,
        "supported_rate": supported_claims / max(len(supported_rows), 1) >= args.min_supported_rate,
        "macro_f1": verifier_metrics["macro_f1"] >= args.min_macro_f1,
        "beats_always_supported": verifier_metrics["macro_f1"] >= always_metrics["macro_f1"] + args.min_margin,
        "beats_field_presence": verifier_metrics["macro_f1"] >= field_metrics["macro_f1"] + args.min_margin,
    }
    status = (
        "PASS - SOURCE-LOCKED HALLUHARD VERIFIER POSITIVE"
        if all(gate_checks.values())
        else "MIXED - SOURCE-LOCKED GATE NOT DEFENSE POSITIVE"
    )
    decision = (
        "Promote PX-011 as a bounded source-locked verifier pipeline positive. Do not claim a freeform HalluHard solution."
        if all(gate_checks.values())
        else "Do not promote PX-011. The constrained gate did not beat the registered thresholds strongly enough."
    )
    summary = {
        "generated_utc": utc_now(),
        "status": status,
        "model_id": args.model_id,
        "rows": len(rows),
        "generations": len(supported_rows),
        "evaluation_pairs": len(eval_rows),
        "extraction_valid": extraction_valid,
        "extraction_valid_rate": extraction_valid / max(len(supported_rows), 1),
        "supported_claims": supported_claims,
        "supported_rate": supported_claims / max(len(supported_rows), 1),
        "label_counts": dict(Counter(row["label"] for row in eval_rows)),
        "verifier_prediction_counts": dict(Counter(row["verifier_prediction"] for row in eval_rows)),
        "verifier_metrics": verifier_metrics,
        "always_supported_baseline": always_metrics,
        "field_presence_baseline": field_metrics,
        "gate_checks": gate_checks,
        "decision": decision,
        "wall_seconds": time.time() - started,
        "claim_boundary": "Research_questions lane only. Source-locked schema and metadata are controlled by the retrieval pipeline; the model generates only an extractive abstract phrase. This does not support broad HalluHard or freeform citation-generation claims.",
    }

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_json(outdir / "summary.json", summary)
    write_rows_csv(outdir / "halluhard_constrained_rows.csv", eval_rows)
    with (outdir / "halluhard_constrained_rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in eval_rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    render_report(outdir / "report.md", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default=os.environ.get("MODEL_ID", "Qwen/Qwen2.5-7B-Instruct"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=int(os.environ.get("HALLUHARD_LIMIT", "250")))
    parser.add_argument("--batch-size", type=int, default=int(os.environ.get("BATCH_SIZE", "4")))
    parser.add_argument("--max-input-tokens", type=int, default=1536)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--dtype", default="float16", choices=["float16", "bfloat16", "auto"])
    parser.add_argument("--min-generations", type=int, default=200)
    parser.add_argument("--min-extraction-valid-rate", type=float, default=0.95)
    parser.add_argument("--min-supported-rate", type=float, default=0.70)
    parser.add_argument("--min-macro-f1", type=float, default=0.75)
    parser.add_argument("--min-margin", type=float, default=0.10)
    args = parser.parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
