#!/usr/bin/env python
"""Verify the canonical PX-062 Gate 2.2 audits against an answer key.

The production CLI has no path overrides: it reads the two stable audit slots
in fixed order.  Programmatic callers may pass staged task/answer files for the
post-regeneration verification, but predicted_skill is always JSON null or one
exact frozen catalog name.  The legacy string ``"NONE"`` is invalid.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_20260728"
)
FROZEN_DIR = GATE_DIR / "frozen_inputs"
CANONICAL_TASKS = FROZEN_DIR / "tasks.jsonl"
CANONICAL_ANSWER = FROZEN_DIR / "answer_key.jsonl"
CANONICAL_CATALOG = FROZEN_DIR / "registry_catalog.json"
CANONICAL_AUDITS = (
    GATE_DIR / "label_audit_1_predictions.jsonl",
    GATE_DIR / "label_audit_2_predictions.jsonl",
)
AUDIT_FIELDS = {"task_id", "predicted_skill", "confidence", "note"}
CONFIDENCE_LEVELS = ("high", "medium", "low")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_loads(raw: str, label: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {label}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read UTF-8 JSONL: {path}") from exc
    if text.startswith("\ufeff") or "\r" in text:
        raise ValueError(f"JSONL must be BOM-free with LF endings: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            raise ValueError(f"blank JSONL line {line_number}: {path}")
        row = strict_json_loads(line, f"{path}:{line_number}")
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row is not an object: {path}:{line_number}")
        rows.append(row)
    return rows


def load_catalog(path: Path) -> set[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read registry catalog: {path}") from exc
    value = strict_json_loads(raw, str(path))
    if not isinstance(value, dict):
        raise ValueError("registry catalog must be an object")
    names = value.get("names")
    entries = value.get("entries")
    if (
        not isinstance(names, list)
        or len(names) != 43
        or not all(isinstance(name, str) and name for name in names)
        or len(set(names)) != 43
        or not isinstance(entries, list)
        or len(entries) != 43
        or not all(isinstance(entry, dict) for entry in entries)
        or [entry.get("name") for entry in entries] != names
    ):
        raise ValueError("registry catalog names are invalid")
    return set(names)


def validate_audit_row(
    row: dict[str, Any],
    *,
    catalog_names: set[str],
    path: Path,
    row_number: int,
) -> None:
    if set(row) != AUDIT_FIELDS:
        raise ValueError(f"audit schema drift: {path}:{row_number}")
    predicted = row["predicted_skill"]
    if predicted is not None and (
        not isinstance(predicted, str) or predicted not in catalog_names
    ):
        raise ValueError(
            f"audit predicted_skill must be JSON null or an exact catalog name: "
            f"{path}:{row_number}"
        )
    if row["confidence"] not in CONFIDENCE_LEVELS:
        raise ValueError(f"audit confidence is invalid: {path}:{row_number}")
    note = row["note"]
    if (
        not isinstance(note, str)
        or not 1 <= len(note) <= 160
        or "\r" in note
        or "\n" in note
    ):
        raise ValueError(f"audit note is invalid: {path}:{row_number}")


def verify(
    tasks_path: Path,
    answer_path: Path,
    audit_paths: list[Path],
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    if len(audit_paths) != 2 or audit_paths[0].resolve() == audit_paths[1].resolve():
        raise ValueError("exactly two distinct audit files are required")
    catalog_names = load_catalog(catalog_path or tasks_path.parent / "registry_catalog.json")
    tasks = read_jsonl(tasks_path)
    answers = read_jsonl(answer_path)
    task_ids = [row.get("task_id") for row in tasks]
    if len(task_ids) != 1032 or len(set(task_ids)) != 1032:
        raise ValueError("frozen task IDs are not exactly 1,032 unique rows")
    if [row.get("task_id") for row in answers] != task_ids:
        raise ValueError("answer key is not in exact task order")
    if any(
        row.get("expected_skill") is not None
        and (
            not isinstance(row.get("expected_skill"), str)
            or row.get("expected_skill") not in catalog_names
        )
        for row in answers
    ):
        raise ValueError("answer key contains a label outside the frozen catalog")
    truth = {row["task_id"]: row.get("expected_skill") for row in answers}
    audit_summaries: list[dict[str, Any]] = []
    prediction_maps: list[dict[str, str | None]] = []
    for path in audit_paths:
        rows = read_jsonl(path)
        if [row.get("task_id") for row in rows] != task_ids:
            raise ValueError(f"audit task order mismatch: {path}")
        for row_number, row in enumerate(rows, 1):
            validate_audit_row(
                row,
                catalog_names=catalog_names,
                path=path,
                row_number=row_number,
            )
        predictions = {row["task_id"]: row["predicted_skill"] for row in rows}
        disagreements = [
            task_id for task_id in task_ids if predictions[task_id] != truth[task_id]
        ]
        prediction_maps.append(predictions)
        audit_summaries.append(
            {
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "rows": len(rows),
                "agreement_with_answer_key": len(rows) - len(disagreements),
                "disagreement_task_ids": disagreements,
                "confidence_counts": {
                    level: sum(row["confidence"] == level for row in rows)
                    for level in CONFIDENCE_LEVELS
                },
            }
        )
    cross_disagreements = [
        task_id
        for task_id in task_ids
        if prediction_maps[0][task_id] != prediction_maps[1][task_id]
    ]
    result = {
        "schema_version": "px062-gate2.2-label-audit-resolution-v1",
        "tasks": {
            "path": tasks_path.as_posix(),
            "sha256": sha256_file(tasks_path),
            "rows": len(tasks),
        },
        "answer_key": {
            "path": answer_path.as_posix(),
            "sha256": sha256_file(answer_path),
            "rows": len(answers),
        },
        "audits": audit_summaries,
        "cross_audit_disagreement_task_ids": cross_disagreements,
        "all_labels_independently_agreed": not cross_disagreements
        and all(not item["disagreement_task_ids"] for item in audit_summaries),
    }
    if not result["all_labels_independently_agreed"]:
        raise ValueError("label audits do not unanimously support the answer key")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify only the canonical fixed-slot PX-062 Gate 2.2 audit pair."
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
