from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_SCAFFOLD = Path("runs/sec-lord-cti-scaffold-20260509")
DEFAULT_ATTACK_JSON = Path(
    "external/datasets/mitre-attack/enterprise-attack/enterprise-attack-12.0.json"
)
DEFAULT_OUT_DIR = Path("runs/sec-lord-relationship-evidence-gate-20260516")
DEFAULT_REPORT = Path(
    "reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_GATE_20260516.md"
)
DEFAULT_PREVIOUS_PREDICTIONS = {
    "Llama-3.2-3B-Instruct": Path("runs/sec-lord-llama-cti-20260510/predictions.jsonl"),
    "Llama-3.1-8B-Instruct": Path("runs/sec-lord-llama-cti-20260510-8b/predictions.jsonl"),
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "may",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "under",
    "use",
    "used",
    "via",
    "what",
    "which",
    "with",
}


def clean_text(value: Any, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    text = (
        text.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
    )
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\(Citation:[^)]+\)", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit is not None and len(text) > limit:
        return text[:limit].rsplit(" ", 1)[0].rstrip() + "."
    return text


def compact_sentence(text: str, limit: int = 360) -> str:
    clean = clean_text(text)
    if not clean:
        return ""
    match = re.search(r"(?<=[.!?])\s+", clean)
    sentence = clean[: match.start()] if match else clean
    return clean_text(sentence, limit=limit)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def active(obj: dict[str, Any]) -> bool:
    return not obj.get("revoked", False) and not obj.get("x_mitre_deprecated", False)


def external_id(obj: dict[str, Any]) -> str:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return str(ref.get("external_id") or "")
    return ""


def technique_from_url(url: str) -> str:
    match = re.search(r"/techniques/(T\d+)(?:/(\d+))?", url or "")
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}" if match.group(2) else match.group(1)


def display_name(obj: dict[str, Any]) -> str:
    ext_id = external_id(obj)
    name = clean_text(obj.get("name", ""))
    if ext_id and name:
        return f"{ext_id} {name}"
    return ext_id or name or clean_text(obj.get("id", ""))


def tokens(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9]+", clean_text(text).lower())
        if tok not in STOPWORDS and len(tok) > 1
    }


def normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", clean_text(text).lower()))


def tactic_label(phase_name: str) -> str:
    return phase_name.replace("-", " ").title()


def add_candidate(
    bucket: dict[str, list[dict[str, str]]],
    technique_id: str,
    kind: str,
    text: str,
) -> None:
    text = clean_text(text)
    if not technique_id or not text:
        return
    bucket[technique_id].append({"kind": kind, "text": text})


def build_candidate_index(attack_json: Path) -> dict[str, list[dict[str, str]]]:
    bundle = json.loads(attack_json.read_text(encoding="utf-8"))
    objects = [obj for obj in bundle["objects"] if active(obj)]
    by_stix_id = {obj["id"]: obj for obj in objects if "id" in obj}
    technique_by_stix: dict[str, str] = {}
    candidates: dict[str, list[dict[str, str]]] = defaultdict(list)

    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue
        technique_id = external_id(obj)
        if not technique_id:
            continue
        technique_by_stix[obj["id"]] = technique_id
        name = display_name(obj)
        description = compact_sentence(obj.get("description", ""), limit=320)
        add_candidate(candidates, technique_id, "technique", f"Technique {name}: {description}")
        phases = [
            tactic_label(phase.get("phase_name", ""))
            for phase in obj.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]
        if phases:
            add_candidate(
                candidates,
                technique_id,
                "tactic",
                f"Tactics for {name}: {', '.join(phases)}.",
            )
        platforms = obj.get("x_mitre_platforms", []) or []
        if platforms:
            add_candidate(
                candidates,
                technique_id,
                "platform",
                f"Platforms for {name}: {', '.join(platforms[:10])}.",
            )
        data_sources = obj.get("x_mitre_data_sources", []) or []
        if data_sources:
            add_candidate(
                candidates,
                technique_id,
                "data_source",
                f"Data sources for {name}: {', '.join(data_sources[:12])}.",
            )
        detection = compact_sentence(obj.get("x_mitre_detection", ""), limit=360)
        if detection:
            add_candidate(candidates, technique_id, "detection", f"Detection for {name}: {detection}")

    for rel in objects:
        if rel.get("type") != "relationship":
            continue
        relationship_type = rel.get("relationship_type", "")
        source = by_stix_id.get(rel.get("source_ref", ""), {})
        target = by_stix_id.get(rel.get("target_ref", ""), {})
        target_technique = technique_by_stix.get(rel.get("target_ref", ""))
        source_technique = technique_by_stix.get(rel.get("source_ref", ""))
        rel_desc = compact_sentence(rel.get("description", ""), limit=520)

        if relationship_type == "mitigates" and target_technique:
            source_desc = compact_sentence(source.get("description", ""), limit=420)
            body = rel_desc or source_desc
            add_candidate(
                candidates,
                target_technique,
                "mitigation",
                f"Mitigation {display_name(source)} for {display_name(target)}: {body}",
            )
        elif relationship_type == "detects" and target_technique:
            source_desc = compact_sentence(source.get("description", ""), limit=420)
            body = rel_desc or source_desc
            add_candidate(
                candidates,
                target_technique,
                "detection",
                f"Detection or data component {display_name(source)} for {display_name(target)}: {body}",
            )
        elif relationship_type == "uses" and target_technique:
            add_candidate(
                candidates,
                target_technique,
                "procedure",
                f"Procedure example for {display_name(target)}: {display_name(source)} - {rel_desc}",
            )
        elif relationship_type == "subtechnique-of" and target_technique and source_technique:
            add_candidate(
                candidates,
                target_technique,
                "subtechnique",
                f"Subtechnique of {display_name(target)}: {display_name(source)}.",
            )

    # A row may point to a parent technique while the answer-bearing fact is on a subtechnique.
    # Copy a small amount of parent evidence down and subtechnique names up via explicit links.
    for rel in objects:
        if rel.get("type") != "relationship" or rel.get("relationship_type") != "subtechnique-of":
            continue
        child = technique_by_stix.get(rel.get("source_ref", ""))
        parent = technique_by_stix.get(rel.get("target_ref", ""))
        if child and parent:
            for item in candidates.get(parent, [])[:6]:
                add_candidate(candidates, child, f"parent_{item['kind']}", item["text"])

    return dict(candidates)


def options_text(row: dict[str, Any]) -> str:
    return "\n".join(
        f"{letter}. {row['options'].get(letter, '')}" for letter in ["A", "B", "C", "D"]
    )


def strict_vanilla_prompt(row: dict[str, Any]) -> str:
    return (
        "Answer the cyber threat intelligence multiple-choice question.\n"
        "Return exactly one line in this format: Answer: <A|B|C|D>\n\n"
        f"Question: {row['question']}\n"
        f"Options:\n{options_text(row)}\n\n"
        "Answer:"
    )


def broad_seed_prompt(row: dict[str, Any], seed_terms: list[str]) -> str:
    seeds = ", ".join(seed_terms[:40])
    return (
        "You are a CTI expert. Use the following broad domain vocabulary if relevant.\n"
        f"Domain vocabulary: {seeds}\n\n"
        "Return exactly one line in this format: Answer: <A|B|C|D>\n\n"
        f"Question: {row['question']}\n"
        f"Options:\n{options_text(row)}\n\n"
        "Answer:"
    )


def kind_bonus(kind: str, query_text: str) -> float:
    query = query_text.lower()
    bonus = 0.0
    if "mitigation" in query or re.search(r"\bm\d{4}\b", query):
        if "mitigation" in kind:
            bonus += 5.0
    if any(term in query for term in ["data source", "detect", "monitor", "indicator"]):
        if "detection" in kind or "data" in kind:
            bonus += 5.0
    if any(term in query for term in ["group", "malware", "tool", "campaign", "used", "command", "certificate"]):
        if "procedure" in kind:
            bonus += 4.0
    if "tactic" in query or "categorized under" in query:
        if "tactic" in kind:
            bonus += 6.0
    return bonus


def rank_evidence(row: dict[str, Any], candidates: list[dict[str, str]], top_k: int) -> list[dict[str, Any]]:
    query_text = " ".join(
        [row.get("question", ""), *[row.get("options", {}).get(letter, "") for letter in ["A", "B", "C", "D"]]]
    )
    query_tokens = tokens(query_text)
    option_phrases = [normalized(row.get("options", {}).get(letter, "")) for letter in ["A", "B", "C", "D"]]
    scored: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for candidate in candidates:
        text = clean_text(candidate["text"])
        if not text or text in seen_text:
            continue
        seen_text.add(text)
        candidate_tokens = tokens(text)
        overlap = len(query_tokens & candidate_tokens)
        score = float(overlap) + kind_bonus(candidate["kind"], query_text)
        norm_text = normalized(text)
        for phrase in option_phrases:
            if phrase and phrase in norm_text:
                score += 7.5
        if overlap == 0 and score < 1:
            continue
        scored.append(
            {
                "kind": candidate["kind"],
                "text": text,
                "score": round(score, 3),
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["kind"], item["text"]))
    return scored[:top_k]


def relationship_evidence_prompt(row: dict[str, Any], evidence: list[dict[str, Any]], attack_version: str) -> str:
    if evidence:
        evidence_block = "\n".join(
            f"- [{item['kind']}] {item['text']}" for item in evidence
        )
    else:
        evidence_block = "- No retrieved relationship evidence."
    return (
        "Answer the CTI multiple-choice question using the provided MITRE ATT&CK evidence when it directly supports an option.\n"
        f"Evidence source: {attack_version}.\n"
        "Do not explain. Return exactly one line in this format: Answer: <A|B|C|D>\n\n"
        f"Evidence:\n{evidence_block}\n\n"
        f"Question: {row['question']}\n"
        f"Options:\n{options_text(row)}\n\n"
        "Answer:"
    )


def option_support_scores(row: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, float]:
    evidence_norm = normalized(" ".join(item["text"] for item in evidence))
    evidence_tokens = tokens(" ".join(item["text"] for item in evidence))
    scores: dict[str, float] = {}
    for letter in ["A", "B", "C", "D"]:
        option = row.get("options", {}).get(letter, "")
        option_norm = normalized(option)
        option_tokens = tokens(option)
        score = 0.0
        if option_norm and option_norm in evidence_norm:
            score += 10.0
        if option_tokens:
            overlap = len(option_tokens & evidence_tokens)
            score += overlap / len(option_tokens)
            if overlap == len(option_tokens):
                score += 3.0
        scores[letter] = round(score, 4)
    return scores


def addressable_letter(row: dict[str, Any], threshold: float) -> str:
    strong = [
        letter
        for letter, score in row.get("option_support_scores", {}).items()
        if float(score) >= threshold
    ]
    return strong[0] if len(strong) == 1 else ""


def strict_parse(text: str) -> str:
    cleaned = re.sub(r"^assistant\s*[:\n]*", "", text.strip(), flags=re.I).strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return ""
    first_line = lines[0]
    match = re.match(
        r"^(?:answer\s*[:\-]?\s*)?([ABCD])(?:[\).:\s]|$)",
        first_line,
        flags=re.I,
    )
    if match:
        return match.group(1).upper()
    match = re.search(r"\b([ABCD])\b", first_line[:20].upper())
    return match.group(1) if match else ""


def prediction_subset_summary(
    prediction_paths: dict[str, Path],
    subset_ids: set[str],
) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for model_name, path in prediction_paths.items():
        if not path.exists():
            continue
        rows = read_jsonl(path)
        model_summary: dict[str, Any] = {}
        for condition in sorted({row.get("condition", "") for row in rows}):
            if not condition:
                continue
            subset = [
                row
                for row in rows
                if row.get("condition") == condition and row.get("id") in subset_ids
            ]
            if not subset:
                continue
            strict_answers = [strict_parse(row.get("raw_output") or "") for row in subset]
            correct = sum(
                answer == row.get("expected_output", "")
                for answer, row in zip(strict_answers, subset)
            )
            invalid = sum(answer not in {"A", "B", "C", "D"} for answer in strict_answers)
            model_summary[condition] = {
                "rows": len(subset),
                "strict_correct": correct,
                "strict_accuracy": correct / max(len(subset), 1),
                "strict_invalid": invalid,
            }
        summaries[model_name] = model_summary
    return summaries


def addressable_subset_summary(
    prompt_rows: list[dict[str, Any]],
    threshold: float,
    prediction_paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    subset_rows: list[dict[str, Any]] = []
    heuristic_correct = 0
    for row in prompt_rows:
        selected = addressable_letter(row, threshold)
        if not selected:
            continue
        enriched = dict(row)
        enriched["evidence_addressable_threshold"] = threshold
        enriched["evidence_pointer_option"] = selected
        subset_rows.append(enriched)
        if selected == row.get("expected_output"):
            heuristic_correct += 1
    subset_ids = {row["id"] for row in subset_rows}
    summary = {
        "threshold": threshold,
        "rows": len(subset_rows),
        "heuristic_correct": heuristic_correct,
        "heuristic_accuracy": heuristic_correct / max(len(subset_rows), 1),
        "selection_rule": (
            "Include a row when exactly one option has lexical support score "
            f">= {threshold} from retrieved evidence. Labels are not used for selection."
        ),
        "previous_prediction_baselines": prediction_subset_summary(
            prediction_paths, subset_ids
        ),
    }
    return subset_rows, summary


def build_gate(
    scaffold_dir: Path,
    attack_json: Path,
    limit: int | None,
    top_k: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(scaffold_dir / "cti_mcq_queries.jsonl", limit)
    seed_bank = json.loads((scaffold_dir / "domain_seed_bank.json").read_text(encoding="utf-8"))
    seed_terms = seed_bank["domain_seed_terms"]
    candidate_index = build_candidate_index(attack_json)
    attack_version = attack_json.stem

    prompt_rows: list[dict[str, Any]] = []
    evidence_counts: Counter[int] = Counter()
    evidence_kind_counts: Counter[str] = Counter()
    expected_phrase_supported = 0
    expected_top_supported = 0
    rows_with_any_evidence = 0
    examples: list[dict[str, Any]] = []

    for row in rows:
        technique_id = technique_from_url(row.get("url", ""))
        evidence = rank_evidence(row, candidate_index.get(technique_id, []), top_k)
        if evidence:
            rows_with_any_evidence += 1
        evidence_counts[len(evidence)] += 1
        for item in evidence:
            evidence_kind_counts[item["kind"]] += 1

        support_scores = option_support_scores(row, evidence)
        expected = str(row.get("expected_output", "")).upper()
        expected_option = row.get("options", {}).get(expected, "")
        evidence_norm = normalized(" ".join(item["text"] for item in evidence))
        if normalized(expected_option) and normalized(expected_option) in evidence_norm:
            expected_phrase_supported += 1
        top_score = max(support_scores.values()) if support_scores else 0.0
        if expected and support_scores.get(expected, -1.0) == top_score and top_score > 0:
            tied = sum(1 for value in support_scores.values() if value == top_score)
            if tied == 1:
                expected_top_supported += 1

        if len(examples) < 8 and evidence:
            examples.append(
                {
                    "id": row["id"],
                    "technique_id": technique_id,
                    "expected": expected,
                    "expected_option": expected_option,
                    "support_scores": support_scores,
                    "evidence": evidence[:3],
                }
            )

        prompt_rows.append(
            {
                "id": row["id"],
                "source_dataset": row["source_dataset"],
                "technique_id": technique_id,
                "expected_output": expected,
                "question": row["question"],
                "options": row["options"],
                "relationship_evidence": evidence,
                "option_support_scores": support_scores,
                "vanilla_strict_prompt": strict_vanilla_prompt(row),
                "broad_seed_negative_control_prompt": broad_seed_prompt(row, seed_terms),
                "relationship_evidence_prompt": relationship_evidence_prompt(
                    row, evidence, attack_version
                ),
            }
        )

    row_count = len(prompt_rows)
    summary = {
        "rows": row_count,
        "attack_json": str(attack_json),
        "attack_version": attack_version,
        "top_k_evidence": top_k,
        "rows_with_any_evidence": rows_with_any_evidence,
        "evidence_coverage": rows_with_any_evidence / max(row_count, 1),
        "expected_option_phrase_in_evidence": expected_phrase_supported,
        "expected_option_phrase_coverage": expected_phrase_supported / max(row_count, 1),
        "expected_option_top_support": expected_top_supported,
        "expected_option_top_support_rate": expected_top_supported / max(row_count, 1),
        "evidence_count_distribution": {str(k): int(v) for k, v in sorted(evidence_counts.items())},
        "evidence_kind_counts": dict(evidence_kind_counts.most_common()),
        "strict_output_format": "Answer: <A|B|C|D>",
        "comparisons": [
            "vanilla_strict_prompt",
            "broad_seed_negative_control_prompt",
            "relationship_evidence_prompt",
        ],
        "examples": examples,
    }
    return prompt_rows, summary


def render_report(path: Path, summary: dict[str, Any], out_dir: Path) -> None:
    examples = summary.get("primary_addressable_examples") or summary["examples"][:3]
    primary_subset = summary.get("primary_addressable_subset", {})
    diagnostic_subset = summary.get("diagnostic_addressable_subset", {})
    lines = [
        "# SEC-LoRD Relationship-Evidence Gate",
        "",
        "Generated: 2026-05-16",
        "",
        "Status: **stronger retrieval gate ready; still no extraction claim**",
        "",
        "## Bottom Line",
        "",
        "The previous retrieved-evidence gate was too shallow because it only attached short technique facts. This gate retrieves from an ATT&CK snapshot closer to the CTI-MCQ source era and ranks relationship-level evidence: mitigations, detection/data components, procedure examples, tactics, and technique metadata.",
        "",
        "This is the best honest way to give SEC-LoRD a chance: improve evidence selection, keep vanilla and broad-seed controls, and require the same strict pass gate before any extraction work.",
        "",
        "## Generated Artifacts",
        "",
        f"- Prompt JSONL: `{out_dir / 'relationship_evidence_prompts.jsonl'}`",
        f"- Evidence-addressable prompt JSONL: `{out_dir / 'evidence_addressable_prompts.jsonl'}`",
        f"- Summary JSON: `{out_dir / 'summary.json'}`",
        "",
        "Regenerate command:",
        "",
        "```powershell",
        ".\\.venv-diag\\Scripts\\python.exe .\\scripts\\build_sec_lord_relationship_evidence_gate.py",
        "```",
        "",
        "## Input And Retrieval Summary",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| CTI-MCQ rows | `{summary['rows']}` |",
        f"| ATT&CK bundle | `{summary['attack_version']}` |",
        f"| Rows with evidence | `{summary['rows_with_any_evidence']}` |",
        f"| Evidence coverage | `{summary['evidence_coverage']:.3f}` |",
        f"| Expected option phrase appears in retrieved evidence | `{summary['expected_option_phrase_coverage']:.3f}` |",
        f"| Expected option is unique top lexical support | `{summary['expected_option_top_support_rate']:.3f}` |",
        f"| Primary evidence-addressable rows | `{primary_subset.get('rows', 0)}` |",
        f"| Primary evidence-pointer audit accuracy | `{primary_subset.get('heuristic_accuracy', 0.0):.3f}` |",
        f"| Diagnostic evidence-addressable rows | `{diagnostic_subset.get('rows', 0)}` |",
        f"| Diagnostic evidence-pointer audit accuracy | `{diagnostic_subset.get('heuristic_accuracy', 0.0):.3f}` |",
        "",
        "## Prompt Conditions",
        "",
        "| Condition | Purpose |",
        "|---|---|",
        "| `vanilla_strict_prompt` | Strong plain baseline with exact `Answer: <A|B|C|D>` output requirement. |",
        "| `broad_seed_negative_control_prompt` | Keeps the failed domain-stuffing strategy visible as a negative control. |",
        "| `relationship_evidence_prompt` | Uses question-ranked ATT&CK relationship evidence instead of broad seed stuffing. |",
        "",
        "## Pass Gate",
        "",
        "- Relationship-evidence strict accuracy must beat vanilla by at least `+0.030` absolute.",
        "- Relationship-evidence invalid response rate must be no worse than vanilla.",
        "- Evidence-only paired wins must exceed vanilla-only paired wins.",
        "- Broad seed negative control remains reported and cannot be hidden.",
        "",
        "## Audit Note",
        "",
        "The lexical support audit uses labels only after retrieval to estimate whether the retrieved evidence contains answer-bearing text. It is not a model result and it is not a pass claim.",
        "",
        "## Previous Llama Baselines On Primary Addressable Slice",
        "",
        "| Model | Vanilla strict acc | Broad-seed strict acc | Vanilla invalid | Broad-seed invalid |",
        "|---|---:|---:|---:|---:|",
    ]
    baselines = primary_subset.get("previous_prediction_baselines", {})
    for model_name, model_summary in baselines.items():
        vanilla = model_summary.get("vanilla_prompt", {})
        seeded = model_summary.get("domain_seeded_prompt", {})
        lines.append(
            f"| {model_name} | `{vanilla.get('strict_accuracy', 0.0):.3f}` | "
            f"`{seeded.get('strict_accuracy', 0.0):.3f}` | "
            f"`{vanilla.get('strict_invalid', 0)}` | "
            f"`{seeded.get('strict_invalid', 0)}` |"
        )
    if not baselines:
        lines.append("| n/a | `0.000` | `0.000` | `0` | `0` |")
    lines.extend(
        [
        "",
        "## Sample Retrieved Evidence",
        "",
        ]
    )
    for example in examples:
        lines.append(f"### {example['id']} / {example['technique_id']}")
        lines.append("")
        lines.append(f"- Expected: `{example['expected']}` / `{example['expected_option']}`")
        if example.get("evidence_pointer_option"):
            lines.append(f"- Evidence pointer: `{example['evidence_pointer_option']}`")
        lines.append(f"- Support scores: `{example['support_scores']}`")
        for item in example["evidence"]:
            lines.append(f"- `{item['kind']}`: {item['text']}")
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "SEC-LoRD remains negative for the old broad-seeding method. This relationship-evidence gate is the recommended next model run. No extraction experiment should run until it passes.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scaffold-dir", type=Path, default=DEFAULT_SCAFFOLD)
    parser.add_argument("--attack-json", type=Path, default=DEFAULT_ATTACK_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--addressable-threshold", type=float, default=10.0)
    parser.add_argument("--diagnostic-threshold", type=float, default=4.0)
    args = parser.parse_args()

    prompt_rows, summary = build_gate(
        scaffold_dir=args.scaffold_dir,
        attack_json=args.attack_json,
        limit=args.limit,
        top_k=args.top_k,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    primary_rows, primary_summary = addressable_subset_summary(
        prompt_rows, args.addressable_threshold, DEFAULT_PREVIOUS_PREDICTIONS
    )
    diagnostic_rows, diagnostic_summary = addressable_subset_summary(
        prompt_rows, args.diagnostic_threshold, DEFAULT_PREVIOUS_PREDICTIONS
    )
    summary["primary_addressable_subset"] = primary_summary
    summary["diagnostic_addressable_subset"] = diagnostic_summary
    summary["primary_addressable_examples"] = [
        {
            "id": row["id"],
            "technique_id": row["technique_id"],
            "expected": row["expected_output"],
            "expected_option": row["options"].get(row["expected_output"], ""),
            "evidence_pointer_option": row["evidence_pointer_option"],
            "support_scores": row["option_support_scores"],
            "evidence": row["relationship_evidence"][:3],
        }
        for row in primary_rows[:5]
    ]
    write_jsonl(args.out_dir / "relationship_evidence_prompts.jsonl", prompt_rows)
    write_jsonl(args.out_dir / "evidence_addressable_prompts.jsonl", primary_rows)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    render_report(args.report, summary, args.out_dir)
    print(json.dumps({"report": str(args.report), **summary}, indent=2))


if __name__ == "__main__":
    main()
