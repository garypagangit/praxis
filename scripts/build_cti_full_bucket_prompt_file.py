from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load one JSONL prompt file."""

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def cti_row_number(row: dict[str, Any]) -> int:
    """Sort `cti_mcq_N` rows by their numeric suffix."""

    match = re.match(r"^cti_mcq_(\d+)$", str(row.get("id", "")))
    if not match:
        raise ValueError(f"Unexpected row id: {row.get('id')}")
    return int(match.group(1))


def build_full_bucket_rows(decisive_path: Path, complement_path: Path) -> list[dict[str, Any]]:
    """
    Merge the decisive PX-003 slice with the PX-034 complement rows.

    The decisive file contains the 106 rows used in the final Qwen defense
    replication. The complement file contains the other 394 rows from the
    500-row CTI-MCQ source-conflict router table. Keeping them separate was
    useful during the original experiment; this builder recreates the full
    forced-answer audit input recommended by the later review.
    """

    rows = read_jsonl(decisive_path) + read_jsonl(complement_path)
    seen: set[str] = set()
    for row in rows:
        row_id = str(row["id"])
        if row_id in seen:
            raise ValueError(f"Duplicate CTI row id: {row_id}")
        seen.add(row_id)
    return sorted(rows, key=cti_row_number)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--decisive-jsonl",
        type=Path,
        default=Path("cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl"),
    )
    parser.add_argument(
        "--complement-jsonl",
        type=Path,
        default=Path("cloud_jobs/sec_lord_relationship_evidence_20260517/input/complement_vanilla_prompts.jsonl"),
    )
    parser.add_argument("--output-jsonl", type=Path, required=True)
    args = parser.parse_args()

    rows = build_full_bucket_rows(args.decisive_jsonl, args.complement_jsonl)
    if len(rows) != 500:
        raise ValueError(f"Expected 500 full-bucket rows, got {len(rows)}")
    write_jsonl(args.output_jsonl, rows)
    print(
        json.dumps(
            {
                "output_jsonl": str(args.output_jsonl),
                "rows": len(rows),
                "first_id": rows[0]["id"],
                "last_id": rows[-1]["id"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
