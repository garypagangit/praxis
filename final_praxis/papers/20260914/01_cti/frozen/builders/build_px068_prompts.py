from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_px003_query_only_prompts import (
        build_candidate_search_index,
        flatten_candidates,
        indexed_candidate_ids,
    )
    from scripts.build_sec_lord_relationship_evidence_gate import (
        build_candidate_index,
        clean_text,
        kind_bonus,
        normalized,
        tokens,
    )
except ModuleNotFoundError:
    from build_px003_query_only_prompts import (  # type: ignore[no-redef]
        build_candidate_search_index,
        flatten_candidates,
        indexed_candidate_ids,
    )
    from build_sec_lord_relationship_evidence_gate import (  # type: ignore[no-redef]
        build_candidate_index,
        clean_text,
        kind_bonus,
        normalized,
        tokens,
    )


LETTERS = ("A", "B", "C", "D", "E")
QUERY_KEYS = {"id", "question", "options"}
SYNTHETIC_ANSWER_FIELDS = (
    "answer",
    "correct_answer",
    "updated_answer",
    "expected_output",
    "explanation",
    "url",
    "source_type",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def sanitize_query(row: dict[str, Any]) -> dict[str, Any]:
    options = row.get("options")
    if not isinstance(options, dict) or tuple(options) != LETTERS:
        raise ValueError(f"Query {row.get('id')} must contain ordered A-E options")
    return {
        "id": str(row["id"]),
        "question": str(row["question"]),
        "options": {letter: str(options[letter]) for letter in LETTERS},
    }


def validate_query_file(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        if set(row) != QUERY_KEYS:
            raise ValueError(
                f"Query {row.get('id')} violates exact query allowlist: {sorted(row)}"
            )
        sanitize_query(row)
    ids = [str(row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Query IDs are not unique")


def options_text(row: dict[str, Any]) -> str:
    return "\n".join(
        f"{letter}. {row['options'][letter]}" for letter in LETTERS
    )


def vanilla_prompt(row: dict[str, Any]) -> str:
    return (
        "Answer the cyber threat intelligence multiple-choice question.\n"
        "Return exactly one line in this format: Answer: <A|B|C|D|E>\n\n"
        f"Question: {row['question']}\n"
        f"Options:\n{options_text(row)}\n\n"
        "Answer:"
    )


def relationship_prompt(
    row: dict[str, Any], evidence: list[dict[str, Any]], attack_version: str
) -> str:
    block = (
        "\n".join(f"- [{item['kind']}] {item['text']}" for item in evidence)
        if evidence
        else "- No retrieved relationship evidence."
    )
    return (
        "Answer the CTI multiple-choice question using the provided MITRE ATT&CK evidence when it directly supports an option.\n"
        f"Evidence source: {attack_version}.\n"
        "Do not explain. Return exactly one line in this format: Answer: <A|B|C|D|E>\n\n"
        f"Evidence:\n{block}\n\n"
        f"Question: {row['question']}\n"
        f"Options:\n{options_text(row)}\n\n"
        "Answer:"
    )


def rank_five_option_evidence(
    raw_row: dict[str, Any],
    candidates: list[dict[str, Any]],
    search_index: dict[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    row = sanitize_query(raw_row)
    query_text = " ".join(
        [row["question"], *[row["options"][letter] for letter in LETTERS]]
    )
    query_tokens = tokens(query_text)
    option_phrases = [normalized(row["options"][letter]) for letter in LETTERS]
    candidate_ids = indexed_candidate_ids(
        query_text,
        query_tokens,
        option_phrases,
        candidates,
        search_index,
    )
    scored: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for index in candidate_ids:
        candidate = candidates[index]
        text = clean_text(candidate["text"])
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        candidate_tokens = candidate.get("_tokens") or tokens(text)
        overlap = len(query_tokens & candidate_tokens)
        score = float(overlap) + kind_bonus(str(candidate["kind"]), query_text)
        normalized_text = str(candidate.get("_normalized") or normalized(text))
        for phrase in option_phrases:
            if phrase and phrase in normalized_text:
                score += 7.5
        if overlap == 0 and score < 1.0:
            continue
        scored.append(
            {
                "technique_id": str(candidate["technique_id"]),
                "kind": str(candidate["kind"]),
                "text": text,
                "score": round(score, 3),
            }
        )
    sort_key = lambda item: (
        -item["score"],
        item["technique_id"],
        item["kind"],
        item["text"],
    )
    return heapq.nsmallest(top_k, scored, key=sort_key)


def build_prompt_record(
    raw_row: dict[str, Any],
    candidates: list[dict[str, Any]],
    search_index: dict[str, Any],
    top_k: int,
    attack_version: str,
) -> dict[str, Any]:
    row = sanitize_query(raw_row)
    ranked = rank_five_option_evidence(row, candidates, search_index, top_k)
    prompt_evidence = [
        {"kind": item["kind"], "text": item["text"], "score": item["score"]}
        for item in ranked
    ]
    return {
        "id": row["id"],
        "vanilla_prompt": vanilla_prompt(row),
        "relationship_evidence_prompt": relationship_prompt(
            row, prompt_evidence, attack_version
        ),
        "retrieval_mode": "query_only_global_lexical_five_option",
        "retrieved_technique_ids": [item["technique_id"] for item in ranked],
        "relationship_evidence": prompt_evidence,
    }


def build_prompts(
    query_path: Path,
    attack_path: Path,
    output_path: Path,
    audit_path: Path,
    top_k: int,
) -> dict[str, Any]:
    rows = read_jsonl(query_path)
    validate_query_file(rows)
    candidate_index = build_candidate_index(attack_path)
    candidates = flatten_candidates(candidate_index)
    search_index = build_candidate_search_index(candidates)
    attack_version = attack_path.stem
    output = [
        build_prompt_record(row, candidates, search_index, top_k, attack_version)
        for row in rows
    ]

    # Exhaustive five-label permutation check. The synthetic answer/provenance
    # fields are cycled through A-E and deliberately ignored by sanitize_query.
    label_invariance_failures = 0
    for index, (row, baseline) in enumerate(zip(rows, output, strict=True)):
        mutated = dict(row)
        label = LETTERS[(index + 1) % len(LETTERS)]
        for field in SYNTHETIC_ANSWER_FIELDS:
            mutated[field] = label if "answer" in field or field == "expected_output" else f"synthetic-{label}"
        rebuilt = build_prompt_record(
            mutated, candidates, search_index, top_k, attack_version
        )
        label_invariance_failures += int(sha256_json(rebuilt) != sha256_json(baseline))
    if label_invariance_failures:
        raise ValueError(
            f"Five-option answer/provenance permutation changed {label_invariance_failures} prompt records"
        )

    write_jsonl(output_path, output)
    audit: dict[str, Any] = {
        "status": "five_option_query_only_prompts_frozen_without_truth",
        "rows": len(rows),
        "query_path": str(query_path),
        "query_sha256": sha256_file(query_path),
        "attack_path": str(attack_path),
        "attack_sha256": sha256_file(attack_path),
        "attack_version": attack_version,
        "candidate_facts": len(candidates),
        "unique_candidate_facts": len(search_index["unique_ids"]),
        "top_k": top_k,
        "option_letters": list(LETTERS),
        "retrieval_reads_question_and_all_five_options_only": True,
        "target_truth_read": False,
        "synthetic_permuted_fields": list(SYNTHETIC_ANSWER_FIELDS),
        "label_permutation_rows_checked": len(rows),
        "label_invariance_failures": label_invariance_failures,
        "output_path": str(output_path),
        "output_sha256": sha256_file(output_path),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-jsonl", type=Path, required=True)
    parser.add_argument("--attack-json", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()
    audit = build_prompts(
        query_path=args.query_jsonl,
        attack_path=args.attack_json,
        output_path=args.output_jsonl,
        audit_path=args.audit_json,
        top_k=args.top_k,
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "rows": audit["rows"],
                "label_invariance_failures": audit["label_invariance_failures"],
                "output_sha256": audit["output_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
