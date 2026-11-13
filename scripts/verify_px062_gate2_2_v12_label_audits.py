#!/usr/bin/env python
"""Verify the two canonical PX-062 Gate 2.2 v1.2 full label audits."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

try:
    from scripts import verify_px062_gate2_2_v11_label_audits as core
except ImportError:  # Direct ``python scripts/...`` execution.
    import verify_px062_gate2_2_v11_label_audits as core  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728"
)
FROZEN_DIR = GATE_DIR / "frozen_inputs"
CANONICAL_TASKS = FROZEN_DIR / "tasks.jsonl"
CANONICAL_ANSWER = FROZEN_DIR / "answer_key.jsonl"
CANONICAL_CATALOG = FROZEN_DIR / "registry_catalog.json"
CANONICAL_AUDITS = (
    GATE_DIR / "label_audit_1_predictions.jsonl",
    GATE_DIR / "label_audit_2_predictions.jsonl",
)
CORE_RELATIVE_PATH = Path("scripts/verify_px062_gate2_2_v11_label_audits.py")
RESOLUTION_SCHEMA = "px062-gate2.2-v1.2-label-audit-resolution-v1"

AUDIT_FIELDS = core.AUDIT_FIELDS
CONFIDENCE_LEVELS = core.CONFIDENCE_LEVELS
strict_json_loads = core.strict_json_loads
sha256_file = core.sha256_file
read_jsonl = core.read_jsonl
load_catalog = core.load_catalog
validate_audit_row = core.validate_audit_row


def verify(
    tasks_path: Path,
    answer_path: Path,
    audit_paths: list[Path],
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Require two distinct, ordered, unanimous 1,032-row audit files."""

    result = core.verify(tasks_path, answer_path, audit_paths, catalog_path)
    migrated = copy.deepcopy(result)
    migrated["schema_version"] = RESOLUTION_SCHEMA
    if (
        migrated.get("all_labels_independently_agreed") is not True
        or len(migrated.get("audits", [])) != 2
        or [row.get("rows") for row in migrated["audits"]] != [1032, 1032]
    ):
        raise ValueError("v1.2 requires two unanimous full 1,032-row audits")
    return migrated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify only the canonical fixed-slot PX-062 Gate 2.2 v1.2 pair."
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
