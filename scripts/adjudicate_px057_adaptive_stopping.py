from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    artifact = args.artifact_dir
    summary = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    selected = json.loads(
        (artifact / "selected_rows.json").read_text(encoding="utf-8")
    )
    traces = read_jsonl(artifact / "reasoning_traces.jsonl")
    generations = read_jsonl(artifact / "raw_generations.jsonl")
    reported_decisions = summary.get("gate_decisions") or {}

    expected_samples = int(config["sample_size"])
    expected_rounds = int(config["rounds"])
    selected_ids = [str(row["question_id"]) for row in selected]
    trace_ids = [str(row["question_id"]) for row in traces]
    generation_ids = [str(row["question_id"]) for row in generations]
    generation_pairs = [
        (str(row["question_id"]), int(row["round"])) for row in generations
    ]
    expected_pairs = {
        (question_id, step)
        for question_id in selected_ids
        for step in range(1, expected_rounds + 1)
    }

    checks = {
        "experiment_id_matches": summary["experiment_id"] == config["experiment_id"],
        "model_id_matches": summary["model_id"] == config["model_id"],
        "dataset_sha256_matches_config": (
            summary["dataset_sha256"] == config["dataset_sha256"]
        ),
        "summary_sample_size_matches": (
            int(summary["sample_size"]) == expected_samples
        ),
        "summary_rounds_matches": int(summary["rounds"]) == expected_rounds,
        "selected_row_count": len(selected) == expected_samples,
        "selected_ids_unique": len(set(selected_ids)) == expected_samples,
        "trace_count": len(traces) == expected_samples,
        "trace_ids_match_selected": set(trace_ids) == set(selected_ids),
        "trace_steps_complete": all(
            len(row["steps"]) == expected_rounds for row in traces
        ),
        "raw_generation_count": (
            len(generations) == expected_samples * expected_rounds
        ),
        "raw_generation_pairs_unique": (
            len(set(generation_pairs)) == expected_samples * expected_rounds
        ),
        "raw_generation_pairs_complete": set(generation_pairs) == expected_pairs,
        "self_reported_gate_checks_complete": (
            set(reported_decisions) == {
                "H1_accuracy",
                "H1_compute",
                "H2_prevention",
                "H3_harm",
            }
        ),
    }
    valid = all(checks.values())
    gate_checks = {key: bool(value) for key, value in reported_decisions.items()}
    gate_pass = valid and all(gate_checks.values())
    file_hashes = {}
    for name in (
        "summary.json",
        "selected_rows.json",
        "reasoning_traces.jsonl",
        "raw_generations.jsonl",
    ):
        file_hashes[name] = hashlib.sha256((artifact / name).read_bytes()).hexdigest()

    result = {
        "experiment_id": "PX-057",
        "stage": "gate2_full",
        "status": (
            "PASS" if gate_pass else "FAIL" if valid else "INVALID_INCOMPLETE"
        ),
        "valid": valid,
        "gate_pass": gate_pass,
        "completeness_checks": checks,
        "gate_checks": gate_checks,
        "metrics": summary["metrics"],
        "file_sha256": file_hashes,
        "claim_boundary": (
            config["claim_boundary"]
            + " Passing supports this frozen GSM8K/Qwen setting only; H4 "
            "cross-model and cross-domain transfer remains untested."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
