#!/usr/bin/env python
"""Score sealed model outputs for the PX-062 skill-name hallucination gate."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    return None if text in {"", "none", "null", "n/a"} else text


def score(tasks: list[dict], outputs: list[dict], registry: set[str]) -> dict:
    task_map = {row["task_id"]: row for row in tasks}
    groups = defaultdict(list)
    seen = set()
    for output in outputs:
        key = (output["model_id"], output["condition"], output["task_id"])
        if key in seen:
            raise ValueError(f"duplicate output: {key}")
        seen.add(key)
        task = task_map[output["task_id"]]
        recommendation = normalize(output.get("recommended_skill"))
        expected = normalize(task["expected_skill"])
        exists = recommendation is None or recommendation in registry
        groups[(output["model_id"], output["condition"])].append(
            {
                "correct": recommendation == expected,
                "nonexistent": recommendation is not None and not exists,
                "attempted_nonexistent": bool(output.get("attempted_load"))
                and recommendation is not None
                and not exists,
            }
        )
    summaries = {}
    for (model, condition), rows in groups.items():
        n = len(rows)
        summaries[f"{model}::{condition}"] = {
            "n": n,
            "accuracy": sum(row["correct"] for row in rows) / n,
            "nonexistent_name_rate": sum(row["nonexistent"] for row in rows) / n,
            "nonexistent_attempt_rate": sum(
                row["attempted_nonexistent"] for row in rows
            )
            / n,
        }
    return {"groups": summaries, "unique_outputs": len(seen)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry_payload = json.loads(args.registry.read_text(encoding="utf-8"))
    result = score(
        read_jsonl(args.tasks),
        read_jsonl(args.outputs),
        {normalize(name) for name in registry_payload["names"]},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
