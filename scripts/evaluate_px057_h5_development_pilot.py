#!/usr/bin/env python
"""Evaluate the outcome-exposed PX-057 H5 development prompt pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
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
from scripts.px057_h5_development_contract import (
    require_c1,
    validate_frozen_development_config,
)
from scripts.fetch_px057_h5_development_pilot import (
    FILES as CLOUD_FILES,
    download_verified_remote_bundle,
    validate_launch_manifest,
    verify_local_execution_tree,
)
from scripts.px057_h5_development_integrity import (
    read_jsonl_strict,
    strict_json_bytes,
)


DEFAULT_CONFIG = ROOT / "configs/px057_h5_development_pilot_20260727.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return read_jsonl_strict(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_evaluation_inputs(
    config: dict[str, Any],
    *,
    cell: dict[str, Any],
    output_dir: Path,
    profile: str,
) -> dict[str, Any]:
    """Re-fetch, verify, and parse the exact remote bytes used for metrics."""

    expected_files = {*CLOUD_FILES, "fetch_receipt.json"}
    if not output_dir.is_dir():
        raise ValueError("development output directory is missing")
    observed = {path.name for path in output_dir.iterdir()}
    if observed != expected_files or any(
        not (output_dir / name).is_file() for name in expected_files
    ):
        raise ValueError(
            "evaluation input directory differs from the six-file contract"
        )
    launch_path = (
        ROOT
        / "manifests/px057_h5_development_pilot_20260727/launches"
        / f"{cell['cell_id']}_r2.json"
    )
    launch_bytes = launch_path.read_bytes()
    launch = strict_json_bytes(launch_bytes, source=str(launch_path))
    validate_launch_manifest(config, cell=cell, launch=launch)
    local_execution_code = verify_local_execution_tree(launch)
    receipt_path = output_dir / "fetch_receipt.json"
    receipt_bytes = receipt_path.read_bytes()
    receipt = strict_json_bytes(receipt_bytes, source=str(receipt_path))
    with tempfile.TemporaryDirectory(
        prefix="px057-h5-evaluation-remote-"
    ) as temp:
        downloaded = download_verified_remote_bundle(
            config,
            cell=cell,
            launch=launch,
            destination=Path(temp) / "registered-artifact",
            profile=profile,
            region=config["aws"]["region"],
            receipt=receipt,
        )
        bundle = downloaded["bundle"]
        bundle_verification = downloaded["verification"]
        traces = read_jsonl_strict(bundle / "reasoning_traces.jsonl")
        raw = read_jsonl_strict(bundle / "raw_generations.jsonl")
        for name, record in bundle_verification["files"].items():
            path = bundle / name
            if (
                sha256_file(path) != record["sha256"]
                or path.stat().st_size != record["bytes"]
            ):
                raise ValueError("remote bundle changed between replay and parsing")
        local_records = {
            name: {
                "sha256": sha256_file(output_dir / name),
                "bytes": (output_dir / name).stat().st_size,
            }
            for name in CLOUD_FILES
        }
        if local_records != bundle_verification["files"]:
            raise ValueError("installed cloud files differ from registered artifact")
        receipt_verification = downloaded["receipt_verification"]
    return {
        "status": "PASS",
        "traces": traces,
        "raw": raw,
        "local_execution_code": local_execution_code,
        "launch_manifest": {
            "path": str(launch_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(launch_bytes).hexdigest(),
            "job_name": launch["job_name"],
            "git_commit": launch["git_commit"],
            "request_sha256": launch["request_sha256"],
        },
        "fetch_receipt": {
            "path": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            **receipt_verification,
        },
        "bundle": bundle_verification,
    }


def trace_steps(trace: dict[str, Any]) -> list[StoppingStep]:
    result: list[StoppingStep] = []
    for step in trace["steps"]:
        if not isinstance(step.get("response_schema_valid"), bool):
            raise ValueError("trace step lacks explicit response_schema_valid")
        result.append(
            StoppingStep(
                round_index=int(step["step"]),
                answer=str(step["answer"]),
                answer_valid=bool(step["response_schema_valid"]),
                confidence=float(step["confidence"]),
                cumulative_tokens=int(step["tokens"]),
                token_cap_reached=bool(step.get("token_cap_reached", False)),
                repetition_detected=bool(step.get("repetition_detected", False)),
            )
        )
    return result


def evaluate_policy(
    traces: list[dict[str, Any]], *, min_step: int, patience: int
) -> dict[str, Any]:
    item_rows: list[dict[str, Any]] = []
    for trace in traces:
        steps = trace_steps(trace)
        gold = str(trace["gold_answer"])
        fixed = fixed_long_decision(steps)
        adaptive = select_stability_stop(
            steps,
            min_step=min_step,
            patience=patience,
            confidence_threshold=None,
        )
        fixed_correct = fixed.answer_valid and fixed.answer == gold
        adaptive_correct = adaptive.answer_valid and adaptive.answer == gold
        max_tokens = fixed.charged_tokens
        saving = (
            0.0
            if max_tokens <= 0
            else 1.0 - adaptive.charged_tokens / max_tokens
        )
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
                "stopped_early": adaptive.stopped_early,
                "early_stop_harm": fixed_correct and not adaptive_correct,
                "compute_saving": saving,
            }
        )
    n = len(item_rows)
    if not n:
        raise ValueError("development evaluation requires at least one trace")
    harms = sum(bool(row["early_stop_harm"]) for row in item_rows)
    fixed_correct_n = sum(bool(row["fixed_long_correct"]) for row in item_rows)
    adaptive_correct_n = sum(bool(row["adaptive_correct"]) for row in item_rows)
    stop_round_distribution = {
        str(round_index): sum(
            int(row["adaptive_step"]) == round_index for row in item_rows
        )
        for round_index in range(1, 9)
    }
    early_stop_n = sum(bool(row["stopped_early"]) for row in item_rows)
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
        "accuracy_delta_count": adaptive_correct_n - fixed_correct_n,
        "adaptive_accuracy_delta": (adaptive_correct_n - fixed_correct_n) / n,
        "early_stop_harms": harms,
        "early_stop_harm_rate": harms / n,
        "mean_compute_saving": sum(row["compute_saving"] for row in item_rows) / n,
        "stability_stops": sum(bool(row["stability_triggered"]) for row in item_rows),
        "early_stop_count": early_stop_n,
        "early_stop_rate": early_stop_n / n,
        "stop_round_distribution": stop_round_distribution,
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


def evaluate_cell(
    config: dict[str, Any], *, cell_id: str, profile: str | None = None
) -> dict[str, Any]:
    validate_frozen_development_config(config)
    require_c1(cell_id)
    matches = [cell for cell in config["cells"] if cell["cell_id"] == cell_id]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate cell: {cell_id}")
    cell = matches[0]
    output_dir = ROOT / cell["output_dir"]
    input_verification = verify_evaluation_inputs(
        config,
        cell=cell,
        output_dir=output_dir,
        profile=profile or config["aws"]["profile"],
    )
    traces = input_verification.pop("traces")
    raw = input_verification.pop("raw")
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
    primary["policy"]["policy_id"] = str(primary_spec["policy_id"])
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
            primary["accuracy_delta_count"]
            >= int(gate_config["adaptive_minus_fixed_correct_min"])
        ),
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
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": primary_spec["policy_id"],
        "stage": "H5_DEVELOPMENT_PILOT_EVALUATION",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell_id,
        "input": {
            "integrity_status": input_verification["status"],
            "local_execution_code": input_verification[
                "local_execution_code"
            ],
            "launch_manifest": input_verification["launch_manifest"],
            "fetch_receipt": input_verification["fetch_receipt"],
            "bundle_verification": input_verification["bundle"],
            "reasoning_traces_sha256": input_verification["bundle"]["files"]
            ["reasoning_traces.jsonl"]["sha256"],
            "raw_generations_sha256": input_verification["bundle"]["files"]
            ["raw_generations.jsonl"]["sha256"],
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
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    if config_path.resolve() != DEFAULT_CONFIG.resolve():
        raise ValueError("evaluation requires the committed default development config")
    config = strict_json_bytes(config_path.read_bytes(), source=str(config_path))
    print(
        json.dumps(
            evaluate_cell(config, cell_id=args.cell, profile=args.profile), indent=2
        )
    )


if __name__ == "__main__":
    main()
