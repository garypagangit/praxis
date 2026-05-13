from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_cti_taa_rows(
    path: Path, limit: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    df = pd.read_parquet(path)
    rows: list[dict[str, Any]] = []
    for idx, row in df.head(limit).iterrows():
        rows.append(
            {
                "id": f"cti_taa_{idx}",
                "source_dataset": "ctibench/cti-taa",
                "task": "threat_actor_attribution",
                "url": clean_text(row.get("URL")),
                "prompt": clean_text(row.get("Prompt")),
                "input_text": clean_text(row.get("Text")),
                "expected_output": None,
                "seed_tags": ["threat_actor", "attribution", "cti_report"],
            }
        )
    meta = {
        "path": str(path),
        "rows_available": int(len(df)),
        "rows_emitted": len(rows),
        "columns": list(df.columns),
    }
    return rows, meta


def build_cti_mcq_rows(
    path: Path, limit: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    df = pd.read_parquet(path)
    rows: list[dict[str, Any]] = []
    for idx, row in df.head(limit).iterrows():
        options = {
            "A": clean_text(row.get("Option A")),
            "B": clean_text(row.get("Option B")),
            "C": clean_text(row.get("Option C")),
            "D": clean_text(row.get("Option D")),
        }
        rows.append(
            {
                "id": f"cti_mcq_{idx}",
                "source_dataset": "ctibench/cti-mcq",
                "task": "cti_multiple_choice",
                "url": clean_text(row.get("URL")),
                "question": clean_text(row.get("Question")),
                "options": options,
                "prompt": clean_text(row.get("Prompt")),
                "expected_output": clean_text(row.get("GT")),
                "seed_tags": ["mitre_attack", "technique_knowledge", "cti_reasoning"],
            }
        )
    meta = {
        "path": str(path),
        "rows_available": int(len(df)),
        "rows_emitted": len(rows),
        "columns": list(df.columns),
        "answer_distribution": {
            str(k): int(v) for k, v in Counter(df["GT"].dropna().astype(str)).items()
        },
    }
    return rows, meta


def build_annoctr_rows(
    path: Path, limit: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_rows = iter_jsonl(path)
    rows: list[dict[str, Any]] = []
    entity_type_counts: Counter[str] = Counter()
    group_names: set[str] = set()
    for idx, row in enumerate(source_rows[:limit]):
        entity_type = clean_text(row.get("entity_type"))
        entity_type_counts[entity_type] += 1
        label_title = clean_text(row.get("label_title"))
        if entity_type == "GROUP" and label_title:
            group_names.add(label_title)
        left = clean_text(row.get("context_left") or row.get("_context_left"))
        right = clean_text(row.get("context_right") or row.get("_context_right"))
        mention = clean_text(row.get("mention"))
        rows.append(
            {
                "id": f"annoctr_linking_{idx}",
                "source_dataset": "annoctr/linking",
                "task": "cti_entity_linking",
                "document": clean_text(row.get("document")),
                "mention": mention,
                "context": clean_text(f"{left} [MENTION: {mention}] {right}"),
                "entity_type": entity_type,
                "expected_output": {
                    "label_title": label_title,
                    "label_link": clean_text(row.get("label_link")),
                    "entity_class": clean_text(row.get("entity_class")),
                    "entity_type": entity_type,
                },
                "seed_tags": ["entity_linking", "cti_entities", entity_type.lower()],
            }
        )
    meta = {
        "path": str(path),
        "rows_available": len(source_rows),
        "rows_emitted": len(rows),
        "entity_type_counts_emitted": dict(sorted(entity_type_counts.items())),
        "group_names_emitted": sorted(group_names),
    }
    return rows, meta


def build_seed_bank(rows: list[dict[str, Any]]) -> dict[str, Any]:
    terms: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    for row in rows:
        for tag in row.get("seed_tags", []):
            tags[clean_text(tag)] += 1
        if row.get("source_dataset") == "ctibench/cti-mcq":
            url = clean_text(row.get("url"))
            if "attack.mitre.org" in url:
                match = re.search(r"/techniques/(T\d+)(?:/(\d+))?", url)
                if match:
                    technique = match.group(1)
                    subtechnique = match.group(2)
                    terms[
                        f"{technique}.{subtechnique}" if subtechnique else technique
                    ] += 1
            for option in row.get("options", {}).values():
                if option:
                    terms[option] += 1
        if row.get("source_dataset") == "annoctr/linking":
            expected = row.get("expected_output", {})
            title = clean_text(expected.get("label_title"))
            if title:
                terms[title] += 1
            mention = clean_text(row.get("mention"))
            if mention:
                terms[mention] += 1

    curated = [
        "APT",
        "MITRE ATT&CK",
        "threat actor attribution",
        "TTP",
        "campaign",
        "malware",
        "intrusion set",
        "indicator of compromise",
        "technique",
        "tactic",
        "entity linking",
        "vulnerability",
    ]
    for term in curated:
        terms[term] += 1

    return {
        "domain_seed_terms": [term for term, _ in terms.most_common(100)],
        "seed_tag_counts": dict(tags.most_common()),
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# SEC-LoRD / DS-LoRD CTI Adapter Scaffold",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        "Status: **UNBLOCKED FOR SCAFFOLD WORK**. The CTI inputs are readable and now have normalized JSONL query files for LoRD/DS-LoRD prompt construction. This does not yet run model extraction; it removes the data-adapter blocker.",
        "",
        "## Emitted Artifacts",
        "",
    ]
    for name, artifact in summary["artifacts"].items():
        lines.append(f"- `{name}`: `{artifact}`")
    lines.extend(
        [
            "",
            "## Input Summary",
            "",
            "| Source | Rows available | Rows emitted | Notes |",
            "|---|---:|---:|---|",
        ]
    )
    for source, meta in summary["inputs"].items():
        notes = []
        if "answer_distribution" in meta:
            notes.append(f"GT distribution {meta['answer_distribution']}")
        if "entity_type_counts_emitted" in meta:
            notes.append(f"entity types {meta['entity_type_counts_emitted']}")
        lines.append(
            f"| {source} | {meta['rows_available']} | {meta['rows_emitted']} | {'; '.join(notes) or 'schema readable'} |"
        )
    lines.extend(
        [
            "",
            "## DS-LoRD Seed Bank",
            "",
            f"- Seed terms emitted: `{summary['seed_bank_size']}`",
            f"- Top seed terms: `{', '.join(summary['top_seed_terms'])}`",
            "",
            "## Next Gate",
            "",
            "Build a tiny extraction harness that uses these files to compare vanilla prompts against domain-seeded prompts on CTI tasks. The first honest compute gate should use a small open model or verified Llama access, write every query/response to S3, and score CTI-MCQ exact match plus AnnoCTR entity-link accuracy before attempting full LoRD extraction.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("tmp") / "sec_lord")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "sec-lord-cti-scaffold-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "sec_lord_ds_lord"
        / "CTI_ADAPTER_SCAFFOLD_20260509.md",
    )
    parser.add_argument("--taa-limit", type=int, default=50)
    parser.add_argument("--mcq-limit", type=int, default=500)
    parser.add_argument("--annoctr-limit", type=int, default=500)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    inputs: dict[str, dict[str, Any]] = {}

    taa_rows, inputs["ctibench/cti-taa"] = build_cti_taa_rows(
        args.input_dir / "cti_taa_test.parquet", args.taa_limit
    )
    mcq_rows, inputs["ctibench/cti-mcq"] = build_cti_mcq_rows(
        args.input_dir / "cti_mcq_test.parquet", args.mcq_limit
    )
    annoctr_rows, inputs["annoctr/linking"] = build_annoctr_rows(
        args.input_dir / "annoctr_sample.json", args.annoctr_limit
    )

    all_rows = taa_rows + mcq_rows + annoctr_rows
    seed_bank = build_seed_bank(all_rows)

    artifacts = {
        "cti_taa_queries": args.out_dir / "cti_taa_queries.jsonl",
        "cti_mcq_queries": args.out_dir / "cti_mcq_queries.jsonl",
        "annoctr_linking_queries": args.out_dir / "annoctr_linking_queries.jsonl",
        "combined_queries": args.out_dir / "combined_queries.jsonl",
        "domain_seed_bank": args.out_dir / "domain_seed_bank.json",
        "summary": args.out_dir / "summary.json",
    }
    write_jsonl(artifacts["cti_taa_queries"], taa_rows)
    write_jsonl(artifacts["cti_mcq_queries"], mcq_rows)
    write_jsonl(artifacts["annoctr_linking_queries"], annoctr_rows)
    write_jsonl(artifacts["combined_queries"], all_rows)
    artifacts["domain_seed_bank"].write_text(
        json.dumps(seed_bank, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "status": "unblocked_for_scaffold_work",
        "inputs": inputs,
        "artifacts": {k: str(v) for k, v in artifacts.items()},
        "rows_emitted_total": len(all_rows),
        "seed_bank_size": len(seed_bank["domain_seed_terms"]),
        "top_seed_terms": seed_bank["domain_seed_terms"][:15],
    }
    artifacts["summary"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(args.report, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
