from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_SCAFFOLD = Path("runs/sec-lord-cti-scaffold-20260509")
DEFAULT_ATTACK_JSON = Path(
    "external/datasets/mitre-attack/enterprise-attack/enterprise-attack.json"
)
DEFAULT_OUT_DIR = Path("runs/sec-lord-retrieved-evidence-gate-20260514")
DEFAULT_REPORT = Path(
    "reports/sec_lord_ds_lord/SEC_LORD_RETRIEVED_EVIDENCE_GATE_READY_20260514.md"
)


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
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def active(obj: dict[str, Any]) -> bool:
    return not obj.get("revoked", False) and not obj.get("x_mitre_deprecated", False)


def external_id(obj: dict[str, Any]) -> str:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return str(ref.get("external_id") or "")
    return ""


def first_sentence(text: str, limit: int = 260) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return ""
    match = re.search(r"(?<=[.!?])\s+", clean)
    sentence = clean[: match.start()] if match else clean
    return sentence[:limit].rstrip()


def load_attack_facts(path: Path) -> dict[str, dict[str, Any]]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    facts: dict[str, dict[str, Any]] = {}
    for obj in bundle["objects"]:
        if not active(obj) or obj.get("type") != "attack-pattern":
            continue
        ext_id = external_id(obj)
        if not ext_id:
            continue
        tactics = [
            phase.get("phase_name", "").replace("-", " ")
            for phase in obj.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]
        data_sources = obj.get("x_mitre_data_sources", []) or []
        platforms = obj.get("x_mitre_platforms", []) or []
        facts[ext_id] = {
            "id": ext_id,
            "name": obj.get("name", ""),
            "description": first_sentence(obj.get("description", "")),
            "tactics": tactics[:6],
            "data_sources": data_sources[:8],
            "platforms": platforms[:8],
            "detection": first_sentence(obj.get("x_mitre_detection", ""), limit=280),
        }
    return facts


def technique_from_url(url: str) -> str:
    match = re.search(r"/techniques/(T\d+)(?:/(\d+))?", url or "")
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}" if match.group(2) else match.group(1)


def evidence_lines(fact: dict[str, Any] | None) -> list[str]:
    if not fact:
        return []
    lines = [
        f"{fact['id']} {fact['name']}: {fact['description']}",
    ]
    if fact.get("tactics"):
        lines.append(f"Tactics: {', '.join(fact['tactics'])}.")
    if fact.get("data_sources"):
        lines.append(f"Data sources: {', '.join(fact['data_sources'])}.")
    elif fact.get("detection"):
        lines.append(f"Detection: {fact['detection']}")
    if fact.get("platforms"):
        lines.append(f"Platforms: {', '.join(fact['platforms'])}.")
    return [line for line in lines if line.strip()][:3]


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


def retrieved_evidence_prompt(row: dict[str, Any], evidence: list[str]) -> str:
    evidence_block = "\n".join(f"- {item}" for item in evidence) or "- No retrieved evidence."
    return (
        "Use only the evidence that is relevant to the question. If the evidence is not useful, answer from the question and options.\n"
        "Return exactly one line in this format: Answer: <A|B|C|D>\n\n"
        f"Evidence:\n{evidence_block}\n\n"
        f"Question: {row['question']}\n"
        f"Options:\n{options_text(row)}\n\n"
        "Answer:"
    )


def build_gate(scaffold_dir: Path, attack_json: Path, limit: int | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(scaffold_dir / "cti_mcq_queries.jsonl", limit)
    seed_bank = json.loads((scaffold_dir / "domain_seed_bank.json").read_text(encoding="utf-8"))
    seed_terms = seed_bank["domain_seed_terms"]
    attack_facts = load_attack_facts(attack_json)

    prompt_rows: list[dict[str, Any]] = []
    with_evidence = 0
    exact_technique = 0
    for row in rows:
        technique_id = technique_from_url(row.get("url", ""))
        fact = attack_facts.get(technique_id)
        if fact:
            exact_technique += 1
        evidence = evidence_lines(fact)
        if evidence:
            with_evidence += 1
        prompt_rows.append(
            {
                "id": row["id"],
                "source_dataset": row["source_dataset"],
                "technique_id": technique_id,
                "expected_output": row["expected_output"],
                "question": row["question"],
                "options": row["options"],
                "evidence": evidence,
                "vanilla_strict_prompt": strict_vanilla_prompt(row),
                "broad_seed_negative_control_prompt": broad_seed_prompt(row, seed_terms),
                "retrieved_evidence_prompt": retrieved_evidence_prompt(row, evidence),
            }
        )

    summary = {
        "rows": len(prompt_rows),
        "rows_with_exact_technique_fact": exact_technique,
        "rows_with_evidence": with_evidence,
        "evidence_coverage": with_evidence / max(len(prompt_rows), 1),
        "strict_output_format": "Answer: <A|B|C|D>",
        "comparisons": [
            "vanilla_strict_prompt",
            "broad_seed_negative_control_prompt",
            "retrieved_evidence_prompt",
        ],
    }
    return prompt_rows, summary


def render_report(path: Path, summary: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# SEC-LoRD Retrieved-Evidence Gate Readiness",
        "",
        "Generated: 2026-05-14",
        "",
        "Status: **ready for cheap model gate; still no extraction claim**",
        "",
        "## Bottom Line",
        "",
        "The failed broad domain-seeding method is now converted into a concrete retrieved-evidence prompt gate. This closes the design ambiguity: the next SEC-LoRD step is a strict three-way prompt comparison, not LoRD-style extraction.",
        "",
        "## Generated Artifacts",
        "",
        f"- Prompt JSONL: `{out_dir / 'retrieved_evidence_prompts.jsonl'}`",
        f"- Summary JSON: `{out_dir / 'summary.json'}`",
        "",
        "## Gate Input Summary",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| CTI-MCQ rows | `{summary['rows']}` |",
        f"| Rows with exact ATT&CK technique fact | `{summary['rows_with_exact_technique_fact']}` |",
        f"| Rows with evidence snippets | `{summary['rows_with_evidence']}` |",
        f"| Evidence coverage | `{summary['evidence_coverage']:.3f}` |",
        "",
        "## Prompt Conditions",
        "",
        "| Condition | Purpose |",
        "|---|---|",
        "| `vanilla_strict_prompt` | Strong plain baseline with exact `Answer: <A|B|C|D>` output requirement. |",
        "| `broad_seed_negative_control_prompt` | Keeps the failed domain-stuffing strategy visible as a negative control. |",
        "| `retrieved_evidence_prompt` | Uses 1-3 question-specific ATT&CK facts in a separate Evidence block. |",
        "",
        "## Pass Gate",
        "",
        "- Retrieved-evidence strict accuracy must beat vanilla by at least `+0.030` absolute.",
        "- Retrieved-evidence invalid response rate must be no worse than vanilla.",
        "- Evidence-only paired wins must exceed vanilla-only paired wins.",
        "- Broad seed negative control remains reported and cannot be hidden.",
        "",
        "## Decision",
        "",
        "SEC-LoRD remains negative for the old method. It is now **gate-ready** for one cheap strict prompt evaluation. No extraction experiment should run until this gate passes.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scaffold-dir", type=Path, default=DEFAULT_SCAFFOLD)
    parser.add_argument("--attack-json", type=Path, default=DEFAULT_ATTACK_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    prompt_rows, summary = build_gate(args.scaffold_dir, args.attack_json, args.limit)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "retrieved_evidence_prompts.jsonl", prompt_rows)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    render_report(args.report, summary, args.out_dir)
    print(json.dumps({"report": str(args.report), **summary}, indent=2))


if __name__ == "__main__":
    main()
