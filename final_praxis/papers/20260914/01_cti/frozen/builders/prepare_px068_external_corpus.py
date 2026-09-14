from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


ATHENA_COMMIT = "39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf"
ATHENA_FILENAME = "benchmark/athena-cti-ckt-3k.jsonl"
ATHENA_RAW_URL = (
    "https://raw.githubusercontent.com/Athena-Software-Group/athenabench/"
    f"{ATHENA_COMMIT}/{ATHENA_FILENAME}"
)
ATHENA_SHA256 = "7893643dd98973fff5b2c3230a4f8f08227d7b6b312ba1a73309f97bb56a7542"
ATHENA_BYTES = 5_994_938
PROSPECTIVELY_CONTAMINATED_SOURCE_IDS = {
    "1": "pre_router_schema_record_exposure",
    "480": "pre_router_label_normalization_error_exposure",
    "1384": "pre_router_malformed_canonical_answer_error_exposure",
}
LETTERS = ("A", "B", "C", "D", "E")
QUERY_KEYS = {"id", "question", "options"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    return re.sub(r"\s+", " ", text).strip().lower()


def canonical_query(question: str, options: dict[str, str]) -> str:
    return normalized("\n".join([question, *[options[letter] for letter in options]]))


def canonical_question(question: str) -> str:
    return normalized(question)


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def source_id(row: dict[str, Any]) -> str:
    value = row.get("id")
    if value is None or str(value).strip() == "":
        raise ValueError("AthenaBench row is missing id")
    return str(value).strip()


def experiment_id(raw_id: str) -> str:
    return f"athena_ckt_{int(raw_id):04d}"


def target_query(row: dict[str, Any]) -> dict[str, Any]:
    options = {
        letter: str(row[f"option_{letter.lower()}"]).strip() for letter in LETTERS
    }
    if not str(row.get("question", "")).strip() or not all(options.values()):
        raise ValueError(f"Incomplete question/options for AthenaBench id={row.get('id')}")
    return {
        "id": experiment_id(source_id(row)),
        "question": str(row["question"]).strip(),
        "options": options,
    }


def attack_path_type(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return "other"
    if parsed.hostname != "attack.mitre.org":
        return "non_attack"
    parts = [part.lower() for part in parsed.path.split("/") if part]
    return parts[0] if parts else "other"


def is_eligible(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    parts = [part.lower() for part in parsed.path.split("/") if part]
    return parsed.hostname == "attack.mitre.org" and bool(parts) and parts[0] == "techniques"


def target_truth(row: dict[str, Any], row_id: str) -> dict[str, Any]:
    # AthenaBench's pinned run.py and evaluate.py score the released `answer`
    # field. `updated_answer` is retained for provenance but is not the scoring
    # target and must not silently override the evaluator's canonical field.
    answer = unicodedata.normalize("NFKC", str(row.get("answer") or "")).strip().upper()
    url = str(row.get("url", "")).strip()
    return {
        "id": row_id,
        "source_record_id": source_id(row),
        "url": url,
        "source_type": str(row.get("source_type", "")),
        "processed_path": str(row.get("processed_path", "")),
        "raw_path": str(row.get("raw_path", "")),
        "correct_answer": str(row.get("correct_answer", "")),
        "answer": answer,
        "answer_label_valid": answer in LETTERS,
        "updated_answer": str(row.get("updated_answer", "")),
        "explanation": str(row.get("explanation", "")),
        "prompt_hash": str(row.get("prompt_hash", "")),
        "eligible": is_eligible(url),
        "attack_path_type": attack_path_type(url),
    }


def ctibench_fingerprints(path: Path) -> tuple[set[str], set[str], set[str]]:
    frame = pd.read_parquet(
        path,
        columns=["URL", "Question", "Option A", "Option B", "Option C", "Option D"],
    )
    full_hashes: set[str] = set()
    question_hashes: set[str] = set()
    urls: set[str] = set()
    for record in frame.to_dict(orient="records"):
        options = {letter: str(record[f"Option {letter}"]) for letter in LETTERS[:4]}
        question = str(record["Question"])
        full_hashes.add(text_hash(canonical_query(question, options)))
        question_hashes.add(text_hash(canonical_question(question)))
        urls.add(str(record["URL"]).strip())
    if len(frame) != 2_500 or len(full_hashes) != 2_500:
        raise ValueError("CTIBench training artifact failed the 2,500-row uniqueness check")
    return full_hashes, question_hashes, urls


def fetch_athena() -> bytes:
    request = urllib.request.Request(ATHENA_RAW_URL, headers={"User-Agent": "PX068/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    if len(payload) != ATHENA_BYTES or sha256_bytes(payload) != ATHENA_SHA256:
        raise ValueError("Pinned AthenaBench artifact failed byte/hash verification")
    return payload


def parse_jsonl_bytes(payload: bytes) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line]
    if len(rows) != 3_000:
        raise ValueError(f"Expected 3,000 AthenaBench rows, found {len(rows)}")
    ids = [source_id(row) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("AthenaBench source IDs are not unique")
    return rows


def prepare(
    ctibench_parquet: Path,
    output_dir: Path,
) -> dict[str, Any]:
    payload = fetch_athena()
    raw_path = output_dir / "sealed" / "athena-cti-ckt-3k.pinned.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    rows = parse_jsonl_bytes(payload)
    train_hashes, train_question_hashes, train_urls = ctibench_fingerprints(
        ctibench_parquet
    )

    primary_queries: list[dict[str, Any]] = []
    primary_truth: list[dict[str, Any]] = []
    overlap_queries: list[dict[str, Any]] = []
    overlap_truth: list[dict[str, Any]] = []
    contaminated_queries: list[dict[str, Any]] = []
    contaminated_truth: list[dict[str, Any]] = []
    overlap_records: list[dict[str, Any]] = []
    exact_question_only_matches = 0
    source_url_overlaps = 0

    for raw in rows:
        query = target_query(raw)
        truth = target_truth(raw, query["id"])
        full_hash = text_hash(canonical_query(query["question"], query["options"]))
        question_hash = text_hash(canonical_question(query["question"]))
        exact_overlap = full_hash in train_hashes
        question_overlap = question_hash in train_question_hashes
        source_overlap = truth["url"] in train_urls
        exact_question_only_matches += int(question_overlap)
        source_url_overlaps += int(source_overlap)

        if truth["source_record_id"] in PROSPECTIVELY_CONTAMINATED_SOURCE_IDS:
            contaminated_queries.append(query)
            contaminated_truth.append(truth)
            overlap_records.append(
                {
                    "id": query["id"],
                    "source_record_id": truth["source_record_id"],
                    "reason": PROSPECTIVELY_CONTAMINATED_SOURCE_IDS[
                        truth["source_record_id"]
                    ],
                    "canonical_query_sha256": full_hash,
                    "canonical_question_sha256": question_hash,
                }
            )
        elif not truth["answer_label_valid"]:
            contaminated_queries.append(query)
            contaminated_truth.append(truth)
            overlap_records.append(
                {
                    "id": query["id"],
                    "source_record_id": truth["source_record_id"],
                    "reason": "invalid_canonical_answer_label",
                    "canonical_query_sha256": full_hash,
                    "canonical_question_sha256": question_hash,
                }
            )
        elif exact_overlap:
            overlap_queries.append(query)
            overlap_truth.append(truth)
            overlap_records.append(
                {
                    "id": query["id"],
                    "source_record_id": truth["source_record_id"],
                    "reason": "exact_ctibench_query_overlap",
                    "canonical_query_sha256": full_hash,
                    "canonical_question_sha256": question_hash,
                }
            )
        else:
            primary_queries.append(query)
            primary_truth.append(truth)

    primary_ids = {row["id"] for row in primary_queries}
    if primary_ids != {row["id"] for row in primary_truth}:
        raise ValueError("Primary query/truth IDs differ")
    eligible = sum(bool(row["eligible"]) for row in primary_truth)
    ineligible = len(primary_truth) - eligible
    if len(primary_truth) < 2_800 or eligible < 900 or ineligible < 1_800:
        raise ValueError(
            "Post-exclusion target failed minimum size gate: "
            f"n={len(primary_truth)}, eligible={eligible}, ineligible={ineligible}"
        )

    paths = {
        "target_queries": output_dir / "target_queries.primary.jsonl",
        "sealed_truth": output_dir / "sealed" / "sealed_truth.primary.jsonl",
        "contaminated_queries": output_dir / "target_queries.schema_sensitivity.jsonl",
        "contaminated_truth": output_dir / "sealed" / "sealed_truth.schema_sensitivity.jsonl",
        "overlap_queries": output_dir / "target_queries.overlap_sensitivity.jsonl",
        "overlap_truth": output_dir / "sealed" / "sealed_truth.overlap_sensitivity.jsonl",
        "exclusions": output_dir / "sealed" / "exclusion_ledger.jsonl",
    }
    write_jsonl(paths["target_queries"], primary_queries)
    write_jsonl(paths["sealed_truth"], primary_truth)
    write_jsonl(paths["contaminated_queries"], contaminated_queries)
    write_jsonl(paths["contaminated_truth"], contaminated_truth)
    write_jsonl(paths["overlap_queries"], overlap_queries)
    write_jsonl(paths["overlap_truth"], overlap_truth)
    write_jsonl(paths["exclusions"], overlap_records)

    source_counts = Counter(row["source_type"] for row in primary_truth)
    attack_counts = Counter(row["attack_path_type"] for row in primary_truth)
    audit: dict[str, Any] = {
        "status": "prepared_before_router_fit_or_target_metric_inspection",
        "athena_commit": ATHENA_COMMIT,
        "athena_raw_url": ATHENA_RAW_URL,
        "athena_raw_bytes": len(payload),
        "athena_raw_sha256": sha256_bytes(payload),
        "athena_total_rows": len(rows),
        "ctibench_parquet": str(ctibench_parquet),
        "ctibench_parquet_sha256": sha256_file(ctibench_parquet),
        "primary_rows": len(primary_queries),
        "primary_eligible": eligible,
        "primary_ineligible": ineligible,
        "primary_non_attack": len(primary_truth)
        - source_counts.get("mitre_attack", 0),
        "primary_source_counts": dict(sorted(source_counts.items())),
        "primary_attack_path_counts": dict(sorted(attack_counts.items())),
        "exact_query_overlap_exclusions": len(overlap_queries),
        "prospective_contamination_exclusions": len(contaminated_queries),
        "exact_question_only_matches_before_exclusion": exact_question_only_matches,
        "source_url_overlaps_before_exclusion": source_url_overlaps,
        "query_allowlist": sorted(QUERY_KEYS),
        "canonical_answer_field": "answer",
        "answer_label_normalization": "NFKC_strip_upper",
        "invalid_canonical_answer_rows_before_exclusion": sum(
            not row["answer_label_valid"]
            for row in primary_truth + overlap_truth + contaminated_truth
        ),
        "minimum_count_gate": {
            "rows_at_least_2800": len(primary_queries) >= 2_800,
            "eligible_at_least_900": eligible >= 900,
            "ineligible_at_least_1800": ineligible >= 1_800,
        },
        "artifacts": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
    }
    audit_path = output_dir / "corpus_preparation_audit.json"
    write_json(audit_path, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ctibench-parquet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    audit = prepare(args.ctibench_parquet, args.output_dir)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "primary_rows": audit["primary_rows"],
                "exact_query_overlap_exclusions": audit[
                    "exact_query_overlap_exclusions"
                ],
                "prospective_contamination_exclusions": audit[
                    "prospective_contamination_exclusions"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
