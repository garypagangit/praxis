#!/usr/bin/env python
"""Evaluate the outcome-exposed PX-057 H5 development prompt pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h5_mechanism import (
    StoppingStep,
    fixed_long_decision,
    select_stability_stop,
)


DEFAULT_CONFIG = ROOT / "configs/px057_h5_development_pilot_20260727.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trace_steps(trace: dict[str, Any]) -> list[StoppingStep]:
    return [
        StoppingStep(
            round_index=int(step["step"]),
            answer=str(step["answer"]),
            answer_valid=bool(step["answer"]),
            confidence=float(step["confidence"]),
            cumulative_tokens=int(step["tokens"]),
            token_cap_reached=bool(step.get("token_cap_reached", False)),
            repetition_detected=bool(step.get("repetition_detected", False)),
        )
        for step in trace["steps"]
    ]


def evaluate_policy(
    traces: list[dict[str, Any]], *, min_step: int, patience: int
) -> dict[str, Any]:
    item_rows: list[dict[str, Any]] = []
    for trace in traces:
        steps = trace_steps(trace)
        gold = str(trace["gold_answer"])
        fixed = fixed_long_decision(steps, fallback_to_latest_valid=False)
        adaptive = select_stability_stop(
            steps,
            min_step=min_step,
            patience=patience,
            confidence_threshold=None,
            fallback_to_latest_valid=False,
        )
        fixed_correct = fixed.answer_valid and fixed.answer == gold
        adaptive_correct = adaptive.answer_valid and adaptive.answer == gold
        max_tokens = fixed.charged_tokens
        saving = (
            0.0
            if max_tokens <= 0
            else 1.0 - adaptive.charged_tokens / max_tokens
        )
        earlier_correct = any(
            step.answer_valid and step.answer == gold for step in steps[:-1]
        )
        overthinking = earlier_correct and not fixed_correct
        item_rows.append(
            {
                "question_id": trace["question_id"],
                "fixed_long_answer": fixed.answer,
                "fixed_long_answer_valid": fixed.answer_valid,
                "fixed_long_answer_round": fixed.answer_round,
                "fixed_long_correct": fixed_correct,
                "fixed_long_fallback": fixed.used_latest_valid_fallback,
                "adaptive_answer": adaptive.answer,
                "adaptive_answer_valid": adaptive.answer_valid,
                "adaptive_step": adaptive.compute_round,
                "adaptive_correct": adaptive_correct,
                "stability_triggered": adaptive.stability_triggered,
                "early_stop_harm": fixed_correct and not adaptive_correct,
                "overthinking_event": overthinking,
                "overthinking_prevented": overthinking and adaptive_correct,
                "compute_saving": saving,
            }
        )
    n = len(item_rows)
    if not n:
        raise ValueError("development evaluation requires at least one trace")
    harms = sum(bool(row["early_stop_harm"]) for row in item_rows)
    fixed_correct_n = sum(bool(row["fixed_long_correct"]) for row in item_rows)
    adaptive_correct_n = sum(bool(row["adaptive_correct"]) for row in item_rows)
    overthinking_n = sum(bool(row["overthinking_event"]) for row in item_rows)
    prevented_n = sum(bool(row["overthinking_prevented"]) for row in item_rows)
    return {
        "policy": {
            "min_step": min_step,
            "patience": patience,
            "confidence_threshold": None,
            "validity_gate": "bounded_check_answer_end_schema",
        },
        "n": n,
        "fixed_long_correct": fixed_correct_n,
        "fixed_long_accuracy": fixed_correct_n / n,
        "adaptive_correct": adaptive_correct_n,
        "adaptive_accuracy": adaptive_correct_n / n,
        "adaptive_accuracy_delta": (adaptive_correct_n - fixed_correct_n) / n,
        "early_stop_harms": harms,
        "early_stop_harm_rate": harms / n,
        "mean_compute_saving": sum(row["compute_saving"] for row in item_rows) / n,
        "stability_stops": sum(bool(row["stability_triggered"]) for row in item_rows),
        "overthinking_events": overthinking_n,
        "overthinking_prevented": prevented_n,
        "overthinking_prevention_rate": (
            None if overthinking_n == 0 else prevented_n / overthinking_n
        ),
        "development_target": {
            "harm_at_most_4_of_500": harms <= 4 and n == 500,
            "accuracy_loss_at_most_5_items": (
                adaptive_correct_n - fixed_correct_n
            )
            >= -5,
            "mean_compute_saving_at_least_25_percent": (
                sum(row["compute_saving"] for row in item_rows) / n >= 0.25
            ),
        },
        "rows": item_rows,
    }


def evaluate_cell(config: dict[str, Any], *, cell_id: str) -> dict[str, Any]:
    matches = [cell for cell in config["cells"] if cell["cell_id"] == cell_id]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate cell: {cell_id}")
    output_dir = ROOT / matches[0]["output_dir"]
    trace_path = output_dir / "reasoning_traces.jsonl"
    raw_path = output_dir / "raw_generations.jsonl"
    traces = read_jsonl(trace_path)
    raw = read_jsonl(raw_path)
    expected_n = int(config["generation"]["pilot_n"])
    expected_rounds = int(config["generation"]["rounds"])
    if len(traces) != expected_n or len(raw) != expected_n * expected_rounds:
        raise ValueError("development collection cardinality mismatch")
    primary_spec = config["primary_development_policy"]
    primary = evaluate_policy(
        traces,
        min_step=int(primary_spec["min_step"]),
        patience=int(primary_spec["patience"]),
    )
    valid_rounds = sum(bool(row.get("response_schema", {}).get("valid")) for row in raw)
    capped_rounds = sum(
        int(row["generated_tokens"]) >= int(config["generation"]["max_new_tokens"])
        for row in raw
    )
    malformed_rounds = len(raw) - valid_rounds
    repeated_marker_rounds = sum(
        int(row.get("response_schema", {}).get("final_answer_marker_count", 0)) > 1
        for row in raw
    )
    prompt_tokens = sum(int(row.get("prompt_tokens", 0)) for row in raw)
    completion_tokens = sum(int(row.get("generated_tokens", 0)) for row in raw)
    wall_seconds = sum(float(row.get("wall_seconds", 0.0)) for row in raw)
    gpu_seconds = sum(float(row.get("gpu_seconds") or 0.0) for row in raw)
    primary_by_id = {row["question_id"]: row for row in primary["rows"]}
    trace_gold_by_id = {
        str(trace["question_id"]): str(trace["gold_answer"]) for trace in traces
    }
    sentinels = []
    for sentinel in config["mechanism_sentinels"]:
        row = primary_by_id.get(sentinel["question_id"])
        if row is None:
            raise ValueError(f"mechanism sentinel missing: {sentinel['question_id']}")
        if trace_gold_by_id.get(sentinel["question_id"]) != str(
            sentinel["gold_answer"]
        ):
            raise ValueError(
                f"mechanism sentinel gold mismatch: {sentinel['question_id']}"
            )
        sentinels.append(
            {
                "question_id": sentinel["question_id"],
                "gold_answer": sentinel["gold_answer"],
                "fixed_long_answer": row["fixed_long_answer"],
                "fixed_long_valid": row["fixed_long_answer_valid"],
                "fixed_long_correct": row["fixed_long_correct"],
                "adaptive_answer": row["adaptive_answer"],
                "adaptive_valid": row["adaptive_answer_valid"],
                "adaptive_correct": row["adaptive_correct"],
            }
        )
    gate_config = config["one_look_mechanism_selection_gate"]
    valid_rate = valid_rounds / len(raw)
    gate_checks = {
        "early_stop_harms": primary["early_stop_harms"]
        <= int(gate_config["early_stop_harms_max"]),
        "mean_compute_saving": primary["mean_compute_saving"]
        >= float(gate_config["mean_compute_saving_min"]),
        "adaptive_minus_fixed_correct": (
            primary["adaptive_correct"] - primary["fixed_long_correct"]
        )
        >= int(gate_config["adaptive_minus_fixed_correct_min"]),
        "strict_valid_round_rate": valid_rate
        >= float(gate_config["strict_valid_round_rate_min"]),
        "fixed_long_correct": primary["fixed_long_correct"]
        >= int(gate_config["fixed_long_correct_min"]),
        "mechanism_sentinels": all(
            row["fixed_long_valid"]
            and row["fixed_long_correct"]
            and row["adaptive_valid"]
            and row["adaptive_correct"]
            for row in sentinels
        ),
    }
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "H5_DEVELOPMENT_PILOT_EVALUATION",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell_id,
        "input": {
            "reasoning_traces_sha256": sha256_file(trace_path),
            "raw_generations_sha256": sha256_file(raw_path),
            "traces": len(traces),
            "generations": len(raw),
        },
        "protocol_diagnostics": {
            "valid_schema_rounds": valid_rounds,
            "valid_schema_rate": valid_rate,
            "token_capped_rounds": capped_rounds,
            "token_cap_rate": capped_rounds / len(raw),
            "malformed_rounds": malformed_rounds,
            "malformed_rate": malformed_rounds / len(raw),
            "repeated_marker_rounds": repeated_marker_rounds,
            "repeated_marker_rate": repeated_marker_rounds / len(raw),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "wall_seconds": wall_seconds,
            "gpu_seconds": gpu_seconds,
        },
        "one_look_primary_policy": {
            key: value for key, value in primary.items() if key != "rows"
        },
        "mechanism_sentinels": sentinels,
        "mechanism_selection_gate": {
            "status": "PASS" if all(gate_checks.values()) else "FAIL",
            "checks": gate_checks,
            "thresholds": gate_config,
        },
        "evaluated_candidate_count": 1,
        "primary_policy_rows": primary["rows"],
    }
    output_path = output_dir / "development_evaluation.json"
    if output_path.exists():
        raise FileExistsError(f"development evaluation is immutable: {output_path}")
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cell", required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    print(json.dumps(evaluate_cell(config, cell_id=args.cell), indent=2))


if __name__ == "__main__":
    main()
