#!/usr/bin/env python
"""Verify the four canonical PX-062 Gate 2.2 v1.3 label-audit payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts import verify_px062_gate2_2_v11_label_audits as core
except ImportError:  # Direct ``python scripts/...`` execution.
    import verify_px062_gate2_2_v11_label_audits as core  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_3_20260728"
)
FROZEN_DIR = GATE_DIR / "frozen_inputs"
CANONICAL_TASKS = FROZEN_DIR / "tasks.jsonl"
CANONICAL_ANSWER = FROZEN_DIR / "answer_key.jsonl"
CANONICAL_CATALOG = FROZEN_DIR / "registry_catalog.json"
CANONICAL_AUDITS = tuple(
    GATE_DIR / f"label_audit_{slot}_predictions.jsonl" for slot in (1, 2, 3, 4)
)
SLOT_MODELS = {
    1: "gpt-5.6-sol",
    2: "gpt-5.6-terra",
    3: "gpt-5.6-sol",
    4: "gpt-5.6-terra",
}
SOL_SLOTS = {1, 3}
TERRA_SLOTS = {2, 4}
RESOLUTION_SCHEMA = "px062-gate2.2-v1.3-label-audit-resolution-v1"
AUDIT_FIELDS = core.AUDIT_FIELDS
CONFIDENCE_LEVELS = core.CONFIDENCE_LEVELS
strict_json_loads = core.strict_json_loads
read_jsonl = core.read_jsonl
load_catalog = core.load_catalog
validate_audit_row = core.validate_audit_row


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate(
    tasks_path: Path,
    answer_path: Path,
    audit_paths: list[Path],
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Return deterministic row-level balanced-consensus diagnostics."""

    if len(audit_paths) != 4 or len({path.resolve() for path in audit_paths}) != 4:
        raise ValueError("exactly four distinct audit files are required")
    tasks = read_jsonl(tasks_path)
    answers = read_jsonl(answer_path)
    if len(tasks) != 1032 or len(answers) != 1032:
        raise ValueError("v1.3 verification requires exactly 1,032 tasks and answers")
    task_ids = [row.get("task_id") for row in tasks]
    if len(set(task_ids)) != 1032 or [row.get("task_id") for row in answers] != task_ids:
        raise ValueError("task and answer order/identity drift")
    if any("expected_skill" not in row for row in answers):
        raise ValueError("answer-key schema lacks expected_skill")
    if catalog_path is None:
        raise ValueError("the frozen registry catalog is required")
    catalog_names = load_catalog(catalog_path)
    truth = {row["task_id"]: row["expected_skill"] for row in answers}
    if any(value is not None and value not in catalog_names for value in truth.values()):
        raise ValueError("answer key contains a label outside the frozen catalog")

    rows_by_slot: dict[int, list[dict[str, Any]]] = {}
    audit_summaries: list[dict[str, Any]] = []
    for slot, path in enumerate(audit_paths, 1):
        rows = read_jsonl(path)
        if len(rows) != 1032 or [row.get("task_id") for row in rows] != task_ids:
            raise ValueError(f"audit {slot} does not contain the complete ordered corpus")
        confidence = Counter()
        disagreement_ids: list[str] = []
        for row_number, row in enumerate(rows, 1):
            validate_audit_row(
                row,
                catalog_names=catalog_names,
                path=path,
                row_number=row_number,
            )
            confidence[row["confidence"]] += 1
            if row["predicted_skill"] != truth[row["task_id"]]:
                disagreement_ids.append(row["task_id"])
        rows_by_slot[slot] = rows
        audit_summaries.append(
            {
                "slot": slot,
                "model": SLOT_MODELS[slot],
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "rows": len(rows),
                "agreement_with_answer_key": len(rows) - len(disagreement_ids),
                "disagreement_task_ids": disagreement_ids,
                "confidence_counts": {
                    level: confidence[level] for level in ("high", "medium", "low")
                },
            }
        )

    rejected: list[dict[str, Any]] = []
    single_dissent: list[dict[str, Any]] = []
    unanimous = 0
    for index, task_id in enumerate(task_ids):
        expected = truth[task_id]
        predictions = {
            slot: rows_by_slot[slot][index]["predicted_skill"] for slot in (1, 2, 3, 4)
        }
        matching = {slot for slot, prediction in predictions.items() if prediction == expected}
        accepted = (
            len(matching) >= 3
            and bool(matching.intersection(SOL_SLOTS))
            and bool(matching.intersection(TERRA_SLOTS))
        )
        row = {
            "task_id": task_id,
            "expected_skill": expected,
            "predictions": {str(slot): predictions[slot] for slot in (1, 2, 3, 4)},
            "key_vote_count": len(matching),
            "key_support_from_sol": bool(matching.intersection(SOL_SLOTS)),
            "key_support_from_terra": bool(matching.intersection(TERRA_SLOTS)),
        }
        if not accepted:
            rejected.append(row)
        elif len(matching) == 3:
            single_dissent.append(row)
        else:
            unanimous += 1
    accepted_rows = 1032 - len(rejected)
    return {
        "schema_version": RESOLUTION_SCHEMA,
        "tasks": {"sha256": sha256_file(tasks_path), "rows": len(tasks)},
        "answer_key": {"sha256": sha256_file(answer_path), "rows": len(answers)},
        "catalog": {"sha256": sha256_file(catalog_path), "names": len(catalog_names)},
        "policy": {
            "audit_slots": 4,
            "sol_slots": [1, 3],
            "terra_slots": [2, 4],
            "minimum_key_votes": 3,
            "require_key_support_from_each_model_family": True,
            "single_dissent_tolerated": True,
            "semantic_retry_permitted": False,
            "disputed_only_rerun_permitted": False,
        },
        "audits": audit_summaries,
        "unanimous_key_rows": unanimous,
        "single_dissent_rows": len(single_dissent),
        "single_dissent_task_ids": [row["task_id"] for row in single_dissent],
        "single_dissent_details": single_dissent,
        "accepted_rows": accepted_rows,
        "rejected_rows": len(rejected),
        "rejected_task_ids": [row["task_id"] for row in rejected],
        "rejected_details": rejected,
        "all_labels_balanced_consensus_accepted": len(rejected) == 0,
    }


def verify(
    tasks_path: Path,
    answer_path: Path,
    audit_paths: list[Path],
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    result = evaluate(tasks_path, answer_path, audit_paths, catalog_path)
    if result["all_labels_balanced_consensus_accepted"] is not True:
        raise ValueError(
            "label audits do not satisfy balanced 3-of-4 consensus on all 1032 rows"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify only the canonical PX-062 Gate 2.2 v1.3 four-pass evidence."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify(
        root / CANONICAL_TASKS,
        root / CANONICAL_ANSWER,
        [root / path for path in CANONICAL_AUDITS],
        root / CANONICAL_CATALOG,
    )
    raw = (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if args.output:
        with args.output.open("xb") as handle:
            handle.write(raw)
    print(raw.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
