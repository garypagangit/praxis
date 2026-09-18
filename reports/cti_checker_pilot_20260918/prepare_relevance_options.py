"""Create an explicit question-plus-options projection for parity scoring.

The original data and q-only scorer remain unchanged. No answer keys, labels,
source information, outcomes or prior scores enter the transformed text.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / "data.jsonl"
    target = ROOT / "data_relevance_options.jsonl"
    source_scorer = ROOT / "score_relevance.py"
    options_scorer = ROOT / "score_relevance_options.py"
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    original_rows = [json.loads(json.dumps(row)) for row in rows]
    for row in rows:
        row["question"] += "\n" + "\n".join(f'{k}. {row["options"][k]}' for k in sorted(row["options"]))
    for before, after in zip(original_rows, rows):
        assert {k: v for k, v in before.items() if k != "question"} == {k: v for k, v in after.items() if k != "question"}
    text = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows)
    target.write_text(text, encoding="utf-8", newline="\n")

    # Preserve original frozen scoring code. This variant changes only its
    # input-description and default paths, leaving all scoring operations equal.
    original_code = source_scorer.read_text(encoding="utf-8")
    replacements = {
        '"question text only; no answer options, labels, source identifiers or outcomes"':
            '"original question plus all displayed options sorted by letter; no answer keys, labels, source identifiers or outcomes"',
        'here / "data.jsonl"': 'here / "data_relevance_options.jsonl"',
        'here / "relevance_scores.jsonl"': 'here / "relevance_options_scores.jsonl"',
        'here / "relevance_metadata.json"': 'here / "relevance_options_metadata.json"',
    }
    variant = original_code
    for old, new in replacements.items():
        assert variant.count(old) == 1, old
        variant = variant.replace(old, new)
    options_scorer.write_text(variant, encoding="utf-8", newline="\n")
    receipt = {
        "purpose": "Pre-fitting input-access parity sensitivity for the published relevance comparator",
        "source_input": str(source), "source_input_sha256": sha(source),
        "transformed_input": str(target), "transformed_input_sha256": sha(target),
        "transform": "question + newline + newline.join(letter + '. ' + displayed_option for letter in sorted(options))",
        "questions": len(rows), "only_question_field_changed": True,
        "original_scorer_sha256": sha(source_scorer), "options_scorer_sha256": sha(options_scorer),
        "scorer_changes": replacements, "preparation_code_sha256": sha(Path(__file__)),
        "interpretation": "All displayed choices enter relevance scoring, never the correct-choice key. This is an explicit adaptation of the published question/passage input format.",
    }
    (ROOT / "relevance_options_projection.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
