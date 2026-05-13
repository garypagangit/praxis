from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit_run(model_name: str, predictions_path: Path) -> dict[str, Any]:
    rows = read_jsonl(predictions_path)
    ids_by_condition: dict[str, set[str]] = defaultdict(set)
    expected_by_id: dict[str, str] = {}
    for row in rows:
        ids_by_condition[row["condition"]].add(row["id"])
        expected_by_id.setdefault(row["id"], row["expected_output"])

    conditions = {}
    for condition in sorted(ids_by_condition):
        subset = [row for row in rows if row["condition"] == condition]
        strict_answers = [strict_parse(row.get("raw_output") or "") for row in subset]
        strict_correct = [
            answer == row["expected_output"]
            for answer, row in zip(strict_answers, subset)
        ]
        invalid_rows = [
            row
            for answer, row in zip(strict_answers, subset)
            if answer not in {"A", "B", "C", "D"}
        ]
        by_expected = {}
        for letter in "ABCD":
            letter_rows = [
                (answer, row)
                for answer, row in zip(strict_answers, subset)
                if row["expected_output"] == letter
            ]
            by_expected[letter] = (
                sum(answer == row["expected_output"] for answer, row in letter_rows)
                / max(len(letter_rows), 1)
            )

        conditions[condition] = {
            "rows": len(subset),
            "old_correct": sum(bool(row.get("correct")) for row in subset),
            "old_accuracy": sum(bool(row.get("correct")) for row in subset)
            / max(len(subset), 1),
            "strict_correct": sum(strict_correct),
            "strict_accuracy": sum(strict_correct) / max(len(subset), 1),
            "strict_invalid": len(invalid_rows),
            "expected_distribution": dict(
                Counter(row["expected_output"] for row in subset)
            ),
            "strict_prediction_distribution": dict(Counter(strict_answers)),
            "strict_accuracy_by_expected": by_expected,
            "invalid_output_examples": Counter(
                (row.get("raw_output") or "").strip() for row in invalid_rows
            ).most_common(8),
        }

    paired: Counter[str] = Counter()
    by_id_condition: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        enriched = dict(row)
        enriched["strict_answer"] = strict_parse(row.get("raw_output") or "")
        enriched["strict_correct"] = (
            enriched["strict_answer"] == enriched["expected_output"]
        )
        by_id_condition[row["id"]][row["condition"]] = enriched
    for row_by_condition in by_id_condition.values():
        if set(row_by_condition) != {"vanilla_prompt", "domain_seeded_prompt"}:
            continue
        vanilla = row_by_condition["vanilla_prompt"]["strict_correct"]
        seeded = row_by_condition["domain_seeded_prompt"]["strict_correct"]
        if vanilla and seeded:
            paired["both_correct"] += 1
        elif vanilla and not seeded:
            paired["vanilla_only"] += 1
        elif not vanilla and seeded:
            paired["seeded_only"] += 1
        else:
            paired["both_wrong"] += 1

    vanilla_acc = conditions["vanilla_prompt"]["strict_accuracy"]
    seeded_acc = conditions["domain_seeded_prompt"]["strict_accuracy"]
    return {
        "model": model_name,
        "prediction_file": str(predictions_path),
        "rows": len(rows),
        "unique_questions": len(expected_by_id),
        "same_question_set": len(set.intersection(*ids_by_condition.values())),
        "expected_distribution": dict(Counter(expected_by_id.values())),
        "strict_delta_seeded_minus_vanilla": seeded_acc - vanilla_acc,
        "conditions": conditions,
        "paired_outcomes": dict(paired),
    }


def render_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# SEC-LoRD Llama Failure Audit",
        "",
        "Generated: 2026-05-11",
        "",
        "## Decision",
        "",
        "Gate result: `CONFIRMED NEGATIVE - CURRENT DOMAIN SEEDING SHOULD STOP`",
        "",
        "The original cloud reports were directionally correct but too generous: the parser treated fallback letters inside non-answer text, including the `a` in `assistant`, as answer `A`. A strict parser lowers absolute accuracy and confirms the same scientific decision: domain-seeded prompting makes both Llama models worse on this CTI-MCQ gate.",
        "",
        "## Strict Reparse Summary",
        "",
        "| Model | Vanilla strict acc | Seeded strict acc | Delta | Vanilla invalid | Seeded invalid |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for run in payload["runs"]:
        vanilla = run["conditions"]["vanilla_prompt"]
        seeded = run["conditions"]["domain_seeded_prompt"]
        lines.append(
            f"| {run['model']} | {vanilla['strict_accuracy']:.3f} | "
            f"{seeded['strict_accuracy']:.3f} | "
            f"{run['strict_delta_seeded_minus_vanilla']:.3f} | "
            f"{vanilla['strict_invalid']} | {seeded['strict_invalid']} |"
        )

    lines.extend(
        [
            "",
            "## Parser Artifact",
            "",
            "The old parser used a fallback that searched for any `A/B/C/D` anywhere in the generated text. That means malformed outputs such as `assistant\\n\\nI'm ready` became `A`. The harness has now been patched to accept only an explicit answer letter or answer-prefixed letter near the beginning of the generated answer.",
            "",
            "## Paired Outcomes",
            "",
            "| Model | Both correct | Vanilla only | Seeded only | Both wrong |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for run in payload["runs"]:
        paired = run["paired_outcomes"]
        lines.append(
            f"| {run['model']} | {paired.get('both_correct', 0)} | "
            f"{paired.get('vanilla_only', 0)} | {paired.get('seeded_only', 0)} | "
            f"{paired.get('both_wrong', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is not a defensible SEC-LoRD positive result.",
            "- The best current Llama signal is plain 8B prompting, not domain seeding.",
            "- The domain-seed prefix appears to increase non-answer/meta responses and answer-position bias.",
            "- The honest next step is not extraction. It is redesigning seed injection and re-gating on answer-format compliance before any LoRD-style attack.",
            "",
            "## Alternatives Worth Testing",
            "",
            "1. Replace long seed lists with 1-3 retrieved ATT&CK facts tied to the specific question.",
            "2. Put seed context in separate evidence snippets, then force `Answer: <letter>` with constrained decoding or post-hoc invalid rejection.",
            "3. Move from CTI-MCQ to a domain where seeding should plausibly help extraction, such as AnnoCTR TTP linking with exact-match labels.",
            "4. Treat vanilla 8B as a victim baseline and test extraction separately only if the attack objective no longer depends on prompt seeding improving accuracy.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/sec_lord_ds_lord/SEC_LORD_FAILURE_AUDIT_20260511.md"),
    )
    args = parser.parse_args()

    payload = {
        "runs": [
            audit_run(
                "Llama-3.2-3B-Instruct",
                Path("runs/sec-lord-llama-cti-20260510/predictions.jsonl"),
            ),
            audit_run(
                "Llama-3.1-8B-Instruct",
                Path("runs/sec-lord-llama-cti-20260510-8b/predictions.jsonl"),
            ),
        ]
    }
    render_report(args.out, payload)
    json_path = args.out.with_suffix(".json")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.out), "json": str(json_path)}, indent=2))


if __name__ == "__main__":
    main()
