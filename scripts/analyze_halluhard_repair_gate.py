#!/usr/bin/env python3
"""PX-011 HalluHard malformed-JSON repair gate over frozen model outputs."""

from __future__ import annotations

import csv
import difflib
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "runs" / "praxis-paid-viability-20260628-rerun" / "halluhard_model_responses.csv"
INPUT_SUMMARY = ROOT / "runs" / "praxis-paid-viability-20260628-rerun" / "halluhard_model_response_summary.json"
HALLUHARD_URL = "https://raw.githubusercontent.com/epfml/halluhard/main/research_questions/data/research_questions_all.jsonl"
OUT_DIR = ROOT / "runs" / "halluhard-repair-gate-20260630"
REPORT = ROOT / "reports" / "halluhard_source_verifier" / "HALLUHARD_REPAIR_GATE_20260630.md"
USER_AGENT = "praxis-px011-halluhard-repair-gate/20260630"


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read().decode("utf-8")


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(text: Any) -> str:
    value = "" if text is None else str(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def ratio(a: Any, b: Any) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def content_grounded(claimed_content: Any, abstract: Any, threshold: float = 0.80) -> tuple[bool, float]:
    claim_norm = norm(claimed_content)
    abstract_norm = norm(abstract)
    if claim_norm and claim_norm in abstract_norm:
        return True, 1.0
    score = ratio(claimed_content, abstract)
    return score >= threshold, score


def parse_json_object(text: str) -> tuple[dict[str, Any], str | None]:
    stripped = text.strip()
    try:
        obj = json.loads(stripped)
        return obj if isinstance(obj, dict) else {}, None
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(stripped[start : end + 1])
            return obj if isinstance(obj, dict) else {}, None
        except json.JSONDecodeError as exc:
            return {}, str(exc)
    return {}, "no_json_object"


def clean_value(value: str) -> str:
    value = value.strip()
    value = value.strip(",")
    value = value.strip()
    value = value.strip('"')
    value = value.replace('\\"', '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value


def regex_between(text: str, key: str, next_keys: list[str]) -> str:
    next_pattern = "|".join(re.escape(f'"{item}"') for item in next_keys)
    pattern = rf'"{re.escape(key)}"\s*:\s*(?P<value>.*?)(?:,\s*(?:{next_pattern})\s*:|$)'
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return ""
    return clean_value(match.group("value"))


def repair_claim(raw_output: str) -> tuple[dict[str, Any], str]:
    strict, error = parse_json_object(raw_output)
    if strict:
        return strict, "strict_json"

    start = raw_output.find("{")
    text = raw_output[start:] if start >= 0 else raw_output
    keys = ["claimed_title", "claimed_year", "claimed_doi", "claimed_arxiv_id", "claimed_content"]
    claim: dict[str, Any] = {}
    for idx, key in enumerate(keys):
        claim[key] = regex_between(text, key, keys[idx + 1 :])

    year_match = re.search(r'"claimed_year"\s*:\s*"?(\d{4})"?', text)
    if year_match:
        claim["claimed_year"] = year_match.group(1)

    useful_fields = [
        bool(norm(claim.get("claimed_title"))),
        bool(norm(claim.get("claimed_year"))),
        bool(norm(claim.get("claimed_doi")) or norm(claim.get("claimed_arxiv_id"))),
        bool(norm(claim.get("claimed_content"))),
    ]
    if sum(useful_fields) >= 3:
        return claim, "regex_repair"
    return {}, f"unrepairable:{error or 'insufficient_fields'}"


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


def metrics(rows: list[dict[str, Any]], pred_key: str) -> dict[str, Any]:
    labels = ["supported", "hallucinated"]
    per_label = {label: f1(rows, label, pred_key) for label in labels}
    return {
        "accuracy": sum(1 for row in rows if row["label"] == row[pred_key]) / len(rows),
        "macro_f1": sum(per_label[label]["f1"] for label in labels) / len(labels),
        "per_label": per_label,
    }


def read_model_rows() -> list[dict[str, Any]]:
    with INPUT_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze() -> dict[str, Any]:
    research_rows = parse_jsonl(fetch_text(HALLUHARD_URL))
    original_summary = load_json(INPUT_SUMMARY)
    repaired_rows: list[dict[str, Any]] = []

    for row in read_model_rows():
        idx = int(row["idx"])
        source_idx = idx if row["case_type"] == "source_conditioned_supported" else (idx + 1) % len(research_rows)
        source = research_rows[source_idx]
        claim, repair_status = repair_claim(row["raw_output"])
        verification = verify_claim(source, claim)
        field_presence = bool(
            norm(claim.get("claimed_title")) and (norm(claim.get("claimed_doi")) or norm(claim.get("claimed_arxiv_id")))
        )
        repaired_rows.append(
            {
                "idx": idx,
                "case_type": row["case_type"],
                "label": row["label"],
                "original_json_valid": row["json_valid"] == "True",
                "repair_status": repair_status,
                "repair_valid": bool(claim),
                "claimed_title": claim.get("claimed_title", ""),
                "claimed_year": claim.get("claimed_year", ""),
                "claimed_doi": claim.get("claimed_doi", ""),
                "claimed_arxiv_id": claim.get("claimed_arxiv_id", ""),
                "claimed_content": claim.get("claimed_content", ""),
                "gold_title": source.get("title", ""),
                "research_question": source.get("research_question", ""),
                "always_supported_prediction": "supported",
                "field_presence_prediction": "supported" if field_presence else "hallucinated",
                **verification,
            }
        )

    supported_cases = [row for row in repaired_rows if row["label"] == "supported"]
    repair_valid_supported = sum(1 for row in supported_cases if row["repair_valid"])
    supported_claims = sum(1 for row in supported_cases if row["verifier_prediction"] == "supported")
    verifier_metrics = metrics(repaired_rows, "verifier_prediction")
    always_metrics = metrics(repaired_rows, "always_supported_prediction")
    field_metrics = metrics(repaired_rows, "field_presence_prediction")
    repair_counts = Counter(row["repair_status"] for row in repaired_rows)
    status = (
        "REPAIR GATE PASS - PARSER WAS PRIMARY BLOCKER"
        if repair_valid_supported >= 200
        and supported_claims >= 100
        and verifier_metrics["macro_f1"] >= max(always_metrics["macro_f1"], field_metrics["macro_f1"]) + 0.10
        else "REPAIR GATE MIXED"
    )
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "claim_boundary": "Repair analysis over frozen HalluHard source-conditioned model outputs; no new generations.",
        "input_csv": str(INPUT_CSV.relative_to(ROOT)),
        "original_summary": original_summary,
        "evaluation_pairs": len(repaired_rows),
        "generations": len(supported_cases),
        "original_parse_valid_supported": original_summary["parse_valid"],
        "original_parse_valid_rate": original_summary["parse_valid_rate"],
        "repair_valid_supported": repair_valid_supported,
        "repair_valid_supported_rate": repair_valid_supported / len(supported_cases),
        "repair_valid_pairs": sum(1 for row in repaired_rows if row["repair_valid"]),
        "repair_valid_pair_rate": sum(1 for row in repaired_rows if row["repair_valid"]) / len(repaired_rows),
        "supported_claims": supported_claims,
        "supported_rate": supported_claims / len(supported_cases),
        "repair_counts": dict(repair_counts),
        "verifier_metrics": verifier_metrics,
        "always_supported_baseline": always_metrics,
        "field_presence_baseline": field_metrics,
        "rows": repaired_rows,
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "idx",
        "case_type",
        "label",
        "original_json_valid",
        "repair_status",
        "repair_valid",
        "verifier_prediction",
        "source_id_match",
        "title_similarity",
        "content_similarity",
        "year_match",
        "content_grounded",
        "claimed_title",
        "claimed_year",
        "claimed_doi",
        "claimed_arxiv_id",
        "gold_title",
        "research_question",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def write_report(analysis: dict[str, Any], analysis_json: Path, rows_csv: Path) -> None:
    original = analysis["original_summary"]
    lines = [
        "# PX-011 HalluHard Repair Gate",
        "",
        f"Generated: {analysis['generated_utc']}",
        "",
        f"Status: **{analysis['status']}**",
        "",
        "## Claim Boundary",
        "",
        (
            "This is a local repair analysis over frozen source-conditioned HalluHard model outputs. "
            "It does not generate new model responses and does not broaden the claim beyond the research_questions lane."
        ),
        "",
        "## Headline Result",
        "",
        (
            f"The original strict parser marked only `{analysis['original_parse_valid_supported']}`/`{analysis['generations']}` "
            f"supported generations parse-valid (`{analysis['original_parse_valid_rate']:.4f}`). A repair parser recovered "
            f"`{analysis['repair_valid_supported']}`/`{analysis['generations']}` supported generations "
            f"(`{analysis['repair_valid_supported_rate']:.4f}`). After recomputing the same DOI/arXiv/title/year/content "
            f"verifier against matched supported and shifted-source negative pairs, verifier macro F1 is "
            f"`{analysis['verifier_metrics']['macro_f1']:.4f}` versus field-presence macro F1 "
            f"`{analysis['field_presence_baseline']['macro_f1']:.4f}`."
        ),
        "",
        "This means PX-011 is not a broad HalluHard positive, but the live-model failure was largely an output-format/parser problem rather than a total absence of source-grounded citation content.",
        "",
        "## Metrics",
        "",
        "| Metric | Original strict gate | Repair gate |",
        "|---|---:|---:|",
        f"| Supported generations recovered | `{original['parse_valid']}` | `{analysis['repair_valid_supported']}` |",
        f"| Supported recovery rate | `{original['parse_valid_rate']:.4f}` | `{analysis['repair_valid_supported_rate']:.4f}` |",
        f"| Supported claims passing verifier | `{original['supported_claims']}` | `{analysis['supported_claims']}` |",
        f"| Supported rate | `{original['supported_rate']:.4f}` | `{analysis['supported_rate']:.4f}` |",
        f"| Verifier macro F1 | `{original['verifier_metrics']['macro_f1']:.4f}` | `{analysis['verifier_metrics']['macro_f1']:.4f}` |",
        f"| Always-supported macro F1 | `{original['always_supported_baseline']['macro_f1']:.4f}` | `{analysis['always_supported_baseline']['macro_f1']:.4f}` |",
        f"| Field-presence macro F1 | `{original['field_presence_baseline']['macro_f1']:.4f}` | `{analysis['field_presence_baseline']['macro_f1']:.4f}` |",
        "",
        "## Repair Status Counts",
        "",
        "| Repair status | Rows |",
        "|---|---:|",
    ]
    for key, count in sorted(analysis["repair_counts"].items()):
        lines.append(f"| `{key}` | `{count}` |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- Promote PX-011 only as a bounded repair/parser gate over frozen model outputs.",
            "- The next live run should use constrained JSON/schema decoding or a shorter field-by-field prompt before claiming HalluHard utility.",
            "- Do not claim a general HalluHard benchmark solution; this result is research-lane only and depends on deterministic source metadata.",
            "",
            "## Artifacts",
            "",
            f"- Raw analysis JSON: [`{analysis_json.relative_to(ROOT).as_posix()}`](../../{analysis_json.relative_to(ROOT).as_posix()})",
            f"- Repaired rows CSV: [`{rows_csv.relative_to(ROOT).as_posix()}`](../../{rows_csv.relative_to(ROOT).as_posix()})",
            "- Original source-conditioned gate: [`HALLUHARD_SOURCE_CONDITIONED_RESPONSE_GATE_20260628.md`](HALLUHARD_SOURCE_CONDITIONED_RESPONSE_GATE_20260628.md)",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    analysis = analyze()
    rows = analysis.pop("rows")
    analysis_json = OUT_DIR / "halluhard_repair_gate.json"
    rows_csv = OUT_DIR / "halluhard_repair_rows.csv"
    write_csv(rows, rows_csv)
    analysis["row_count"] = len(rows)
    analysis_json.write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_report(analysis, analysis_json, rows_csv)
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print(f"Wrote {analysis_json.relative_to(ROOT)}")
    print(f"Wrote {rows_csv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
