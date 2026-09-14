from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.build_sec_lord_relationship_evidence_gate import (
        build_candidate_index,
        clean_text,
        kind_bonus,
        normalized,
        relationship_evidence_prompt,
        tokens,
    )
except ModuleNotFoundError:  # Direct execution adds scripts/, not the repository root.
    from build_sec_lord_relationship_evidence_gate import (  # type: ignore[no-redef]
        build_candidate_index,
        clean_text,
        kind_bonus,
        normalized,
        relationship_evidence_prompt,
        tokens,
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flatten_candidates(
    candidate_index: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for technique_id, candidates in sorted(candidate_index.items()):
        for candidate in candidates:
            text = clean_text(candidate["text"])
            flattened.append(
                {
                    "technique_id": technique_id,
                    "kind": str(candidate["kind"]),
                    "text": text,
                    "_tokens": tokens(text),
                    "_normalized": normalized(text),
                }
            )
    return flattened


def build_candidate_search_index(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an exact candidate prefilter for the lexical scoring rule.

    The original implementation scored every fact for every row. A fact can
    survive that scorer only through query-token overlap, a kind bonus, or an
    exact option-phrase match. This index returns the union of precisely those
    candidate sets while retaining the original first-text deduplication rule.
    """

    token_to_ids: dict[str, set[int]] = defaultdict(set)
    word_to_ids: dict[str, set[int]] = defaultdict(set)
    bonus_groups: dict[str, set[int]] = defaultdict(set)
    unique_ids: list[int] = []
    seen_text: set[str] = set()
    for index, candidate in enumerate(candidates):
        text = str(candidate["text"])
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        unique_ids.append(index)
        for token in candidate.get("_tokens") or tokens(text):
            token_to_ids[token].add(index)
        normalized_text = str(candidate.get("_normalized") or normalized(text))
        for word in re.findall(r"[a-z0-9]+", normalized_text):
            word_to_ids[word].add(index)
        kind = str(candidate["kind"])
        if "mitigation" in kind:
            bonus_groups["mitigation"].add(index)
        if "detection" in kind or "data" in kind:
            bonus_groups["detection"].add(index)
        if "procedure" in kind:
            bonus_groups["procedure"].add(index)
        if "tactic" in kind:
            bonus_groups["tactic"].add(index)
    return {
        "token_to_ids": dict(token_to_ids),
        "word_to_ids": dict(word_to_ids),
        "bonus_groups": dict(bonus_groups),
        "unique_ids": unique_ids,
    }


def indexed_candidate_ids(
    query_text: str,
    query_tokens: set[str],
    option_phrases: list[str],
    candidates: list[dict[str, Any]],
    search_index: dict[str, Any],
) -> set[int]:
    candidate_ids: set[int] = set()
    token_to_ids = search_index["token_to_ids"]
    for token in query_tokens:
        candidate_ids.update(token_to_ids.get(token, ()))

    query = query_text.lower()
    bonus_groups = search_index["bonus_groups"]
    if "mitigation" in query or re.search(r"\bm\d{4}\b", query):
        candidate_ids.update(bonus_groups.get("mitigation", ()))
    if any(term in query for term in ["data source", "detect", "monitor", "indicator"]):
        candidate_ids.update(bonus_groups.get("detection", ()))
    if any(
        term in query
        for term in ["group", "malware", "tool", "campaign", "used", "command", "certificate"]
    ):
        candidate_ids.update(bonus_groups.get("procedure", ()))
    if "tactic" in query or "categorized under" in query:
        candidate_ids.update(bonus_groups.get("tactic", ()))

    word_to_ids = search_index["word_to_ids"]
    for phrase in option_phrases:
        phrase_words = phrase.split()
        if not phrase_words:
            continue
        for index in word_to_ids.get(phrase_words[0], ()):
            candidate_normalized = str(
                candidates[index].get("_normalized")
                or normalized(str(candidates[index].get("text", "")))
            )
            if phrase in candidate_normalized:
                candidate_ids.add(index)
    return candidate_ids


def rank_query_only_evidence(
    row: dict[str, Any],
    candidates: list[dict[str, Any]],
    top_k: int,
    search_index: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Rank globally without reading source URL, source technique, or answer label."""

    query_text = " ".join(
        [
            str(row.get("question", "")),
            *[
                str(row.get("options", {}).get(letter, ""))
                for letter in ("A", "B", "C", "D")
            ],
        ]
    )
    query_tokens = tokens(query_text)
    option_phrases = [
        normalized(row.get("options", {}).get(letter, ""))
        for letter in ("A", "B", "C", "D")
    ]
    scored: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    if search_index is None:
        candidate_stream = candidates
    else:
        candidate_stream = [
            candidates[index]
            for index in indexed_candidate_ids(
                query_text,
                query_tokens,
                option_phrases,
                candidates,
                search_index,
            )
        ]
    for candidate in candidate_stream:
        text = candidate["text"]
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        candidate_tokens = candidate.get("_tokens") or tokens(text)
        overlap = len(query_tokens & candidate_tokens)
        score = float(overlap) + kind_bonus(candidate["kind"], query_text)
        norm_text = candidate.get("_normalized") or normalized(text)
        for phrase in option_phrases:
            if phrase and phrase in norm_text:
                score += 7.5
        if overlap == 0 and score < 1.0:
            continue
        scored.append(
            {
                "technique_id": candidate["technique_id"],
                "kind": candidate["kind"],
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


def build_query_only_rows(
    rows: list[dict[str, Any]],
    candidate_index: dict[str, list[dict[str, str]]],
    attack_version: str,
    top_k: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = flatten_candidates(candidate_index)
    search_index = build_candidate_search_index(candidates)
    output: list[dict[str, Any]] = []
    source_technique_top1 = 0
    source_technique_topk = 0
    answer_phrase_present = 0
    for row in rows:
        ranked = rank_query_only_evidence(
            row,
            candidates,
            top_k=top_k,
            search_index=search_index,
        )
        prompt_evidence = [
            {"kind": item["kind"], "text": item["text"], "score": item["score"]}
            for item in ranked
        ]
        enriched = copy.deepcopy(row)
        enriched["source_pointer_relationship_evidence"] = enriched.get(
            "relationship_evidence", []
        )
        enriched["source_pointer_relationship_evidence_prompt"] = enriched.get(
            "relationship_evidence_prompt", ""
        )
        enriched["relationship_evidence"] = prompt_evidence
        enriched["relationship_evidence_prompt"] = relationship_evidence_prompt(
            row, prompt_evidence, attack_version
        )
        enriched["retrieval_mode"] = "query_only_global_lexical"
        enriched["query_only_retrieved_technique_ids"] = [
            item["technique_id"] for item in ranked
        ]
        source_technique = str(row.get("technique_id", ""))
        if ranked and ranked[0]["technique_id"] == source_technique:
            source_technique_top1 += 1
        if source_technique and source_technique in enriched["query_only_retrieved_technique_ids"]:
            source_technique_topk += 1
        expected = str(row.get("expected_output", "")).upper()
        expected_text = normalized(row.get("options", {}).get(expected, ""))
        evidence_text = normalized(" ".join(item["text"] for item in ranked))
        answer_phrase_present += int(bool(expected_text and expected_text in evidence_text))
        output.append(enriched)

    # A label permutation must not affect retrieval or prompt construction. This is
    # an executable leakage check, not an assumption.
    label_invariance_failures = 0
    for original, built in zip(rows, output):
        permuted = copy.deepcopy(original)
        original_label = str(permuted.get("expected_output", "A")).upper()
        alphabet = ("A", "B", "C", "D")
        permuted["expected_output"] = alphabet[(alphabet.index(original_label) + 1) % 4]
        reranked_prompt = relationship_evidence_prompt(
            permuted,
            [
                {"kind": item["kind"], "text": item["text"], "score": item["score"]}
                for item in built["relationship_evidence"]
            ],
            attack_version,
        )
        label_invariance_failures += int(
            sha256_text(reranked_prompt)
            != sha256_text(str(built["relationship_evidence_prompt"]))
        )

    count = len(output)
    return output, {
        "rows": count,
        "attack_version": attack_version,
        "candidate_facts": len(candidates),
        "unique_candidate_facts": len(search_index["unique_ids"]),
        "candidate_prefilter": "exact_token_kind_phrase_union_v1",
        "top_k": top_k,
        "retrieval_mode": "query_only_global_lexical",
        "source_url_or_technique_used_for_retrieval": False,
        "expected_output_used_for_retrieval": False,
        "label_invariance_failures": label_invariance_failures,
        "source_technique_top1": source_technique_top1,
        "source_technique_top1_rate": source_technique_top1 / count if count else 0.0,
        "source_technique_topk": source_technique_topk,
        "source_technique_topk_rate": source_technique_topk / count if count else 0.0,
        "answer_option_phrase_present": answer_phrase_present,
        "answer_option_phrase_present_rate": answer_phrase_present / count if count else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--attack-json", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()
    rows = read_jsonl(args.input_jsonl)
    candidate_index = build_candidate_index(args.attack_json)
    output, audit = build_query_only_rows(
        rows,
        candidate_index=candidate_index,
        attack_version=args.attack_json.stem,
        top_k=args.top_k,
    )
    write_jsonl(args.output_jsonl, output)
    audit.update(
        {
            "source_input": str(args.input_jsonl),
            "source_input_sha256": sha256_file(args.input_jsonl),
            "attack_json": str(args.attack_json),
            "attack_json_sha256": sha256_file(args.attack_json),
            "output_jsonl": str(args.output_jsonl),
            "output_sha256": sha256_file(args.output_jsonl),
        }
    )
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
