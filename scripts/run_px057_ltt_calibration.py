#!/usr/bin/env python
"""Run or lock one PX-057 H4 Learn-then-Test calibration cell."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import (
    calibrate_cell,
    committed_file_info,
    load_scored_traces,
    read_json,
    sha256_file,
    verify_collection_bundle,
    verify_frozen_split,
    verify_phase_a_freeze,
    write_json,
)


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def get_cell(config: dict[str, Any], cell_id: str) -> dict[str, Any]:
    cell = next((row for row in config["cells"] if row["cell_id"] == cell_id), None)
    if cell is None:
        raise ValueError(f"unknown cell: {cell_id}")
    return cell


def run_calibration(
    config_path: Path,
    *,
    cell_id: str,
    trace_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    config = read_json(config_path)
    config_commit = committed_file_info(ROOT, config_path)
    phase_a_evidence = verify_phase_a_freeze(
        ROOT, config_path, config, require_current_runtime=False
    )
    code_evidence = {
        "calibration": committed_file_info(ROOT, Path(__file__)),
        "common": committed_file_info(ROOT, ROOT / "scripts/px057_h4_common.py"),
        "gate_backend": committed_file_info(
            ROOT, ROOT / "scripts/run_px057_adaptive_stopping_gate.py"
        ),
    }
    cell = get_cell(config, cell_id)
    split_path = repo_path(cell["calibration_manifest"])
    split_freeze_evidence = verify_frozen_split(
        ROOT,
        repo_path(config["split_design"]["freeze_manifest"]),
        split_path,
    )
    expected_trace_path = (
        repo_path(cell["output_dirs"]["calibration"]) / "reasoning_traces.jsonl"
    )
    if trace_path is None:
        trace_path = expected_trace_path
    if trace_path.resolve() != expected_trace_path.resolve():
        raise ValueError("calibration trace path differs from the frozen config")
    if trace_path.name != "reasoning_traces.jsonl":
        raise ValueError("calibration trace must belong to a complete collection bundle")
    expected_output_path = repo_path(cell["ltt_determination"])
    if output_path is None:
        output_path = expected_output_path
    if output_path.resolve() != expected_output_path.resolve():
        raise ValueError("calibration determination path differs from the frozen config")
    if output_path.exists():
        raise FileExistsError(
            f"{output_path} already exists; calibration determinations are immutable"
        )
    rounds = int(config["generation"]["rounds"])
    collection_bundle = verify_collection_bundle(
        trace_path.parent,
        split_path,
        repo_root=ROOT,
        expected_cell_id=cell_id,
        expected_split="calibration",
        expected_n=int(config["split_design"]["calibration_n"]),
        expected_rounds=rounds,
        expected_model=config["models"][cell["model_key"]],
        expected_prompt_id=config["generation"]["prompt_template_id"],
        expected_prompt_sha256=config["generation"]["prompt_template_sha256"],
    )
    traces, split_rows = load_scored_traces(
        trace_path, split_path, expected_rounds=rounds
    )
    expected_n = int(config["split_design"]["calibration_n"])
    if len(traces) != expected_n:
        raise ValueError(f"expected {expected_n} calibration traces")

    risk = config["risk_control"]
    cell_delta = float(risk["family_delta"]) / len(config["cells"])
    if not math_is_close(cell_delta, float(risk["cell_delta"])):
        raise ValueError("cell_delta must equal family_delta / number of cells")
    calibration = calibrate_cell(
        traces,
        population_size=int(cell["eligible_population_size"]),
        grid=risk["policy_grid"],
        order_spec=risk["fixed_sequence_order"],
        alpha=float(risk["alpha"]),
        cell_delta=cell_delta,
    )
    result = {
        "experiment_id": config["experiment_id"],
        "px_id": "PX-057",
        "stage": "H4_LTT_calibration",
        "cell_id": cell_id,
        "model": config["models"][cell["model_key"]],
        "dataset_key": cell["dataset_key"],
        "prompt_template_id": config["generation"]["prompt_template_id"],
        "calibration": calibration,
        "input_artifacts": {
            "config": {
                "path": config_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(config_path),
                "commit": config_commit,
            },
            "split": {
                "path": split_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(split_path),
                "rows": len(split_rows),
                "freeze_evidence": split_freeze_evidence,
            },
            "traces": {
                "path": trace_path.relative_to(ROOT).as_posix()
                if trace_path.is_relative_to(ROOT)
                else str(trace_path),
                "sha256": sha256_file(trace_path),
                "rows": len(traces),
            },
            "collection_bundle": collection_bundle,
        },
        "code_evidence": code_evidence,
        "phase_a_evidence": phase_a_evidence,
        "claim_boundary": (
            "The primary p-values target finite benchmark-population harm under "
            "the preregistered without-replacement split. The family delta is "
            "allocated across all three cells. H4a certifies only the reached "
            "fixed-sequence prefix."
        ),
    }
    write_json(output_path, result)
    return result


def math_is_close(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-12


def write_lock(
    config_path: Path,
    *,
    cell_id: str,
    determination_path: Path | None = None,
    lock_path: Path | None = None,
) -> dict[str, Any]:
    config = read_json(config_path)
    committed_file_info(ROOT, config_path)
    phase_a_evidence = verify_phase_a_freeze(
        ROOT, config_path, config, require_current_runtime=False
    )
    cell = get_cell(config, cell_id)
    expected_determination_path = repo_path(cell["ltt_determination"])
    if determination_path is None:
        determination_path = expected_determination_path
    if determination_path.resolve() != expected_determination_path.resolve():
        raise ValueError("determination path differs from the frozen config")
    expected_lock_path = repo_path(cell["ltt_lock_manifest"])
    if lock_path is None:
        lock_path = expected_lock_path
    if lock_path.resolve() != expected_lock_path.resolve():
        raise ValueError("lock path differs from the frozen config")
    if lock_path.exists():
        raise FileExistsError(f"{lock_path} already exists; locks are immutable")
    determination = read_json(determination_path)
    if determination["cell_id"] != cell_id:
        raise ValueError("determination cell mismatch")
    if (
        determination["experiment_id"] != config["experiment_id"]
        or determination["model"] != config["models"][cell["model_key"]]
        or determination["dataset_key"] != cell["dataset_key"]
        or determination["prompt_template_id"]
        != config["generation"]["prompt_template_id"]
    ):
        raise ValueError("determination identity differs from the frozen config")
    committed = committed_file_info(ROOT, determination_path)
    artifacts = determination["input_artifacts"]
    if artifacts["config"]["sha256"] != sha256_file(config_path):
        raise ValueError("determination was produced from a different config")
    prompt_path = repo_path(config["generation"]["prompt_template_path"])
    if sha256_file(prompt_path) != config["generation"]["prompt_template_sha256"]:
        raise ValueError("prompt template hash differs from the frozen config")
    split_path = repo_path(artifacts["split"]["path"])
    if artifacts["split"]["sha256"] != sha256_file(split_path):
        raise ValueError("determination split hash mismatch")
    trace_path = repo_path(artifacts["traces"]["path"])
    if artifacts["traces"]["sha256"] != sha256_file(trace_path):
        raise ValueError("determination trace hash mismatch")
    verify_frozen_split(
        ROOT,
        repo_path(config["split_design"]["freeze_manifest"]),
        split_path,
    )
    committed_file_info(ROOT, trace_path)
    for metadata in artifacts["collection_bundle"]["files"].values():
        artifact_path = repo_path(metadata["path"])
        if metadata["sha256"] != sha256_file(artifact_path):
            raise ValueError(f"{artifact_path}: determination bundle hash mismatch")
        committed_file_info(ROOT, artifact_path)
    traces, _ = load_scored_traces(
        trace_path,
        split_path,
        expected_rounds=int(config["generation"]["rounds"]),
    )
    risk = config["risk_control"]
    recomputed_calibration = calibrate_cell(
        traces,
        population_size=int(cell["eligible_population_size"]),
        grid=risk["policy_grid"],
        order_spec=risk["fixed_sequence_order"],
        alpha=float(risk["alpha"]),
        cell_delta=float(risk["family_delta"]) / len(config["cells"]),
    )
    if recomputed_calibration != determination["calibration"]:
        raise ValueError("calibration determination does not recompute exactly")
    protected_paths = {
        "config": config_path,
        "prompt_template": prompt_path,
        "requirements": repo_path(config["phase_a"]["requirements_path"]),
        "runtime_manifest": repo_path(config["phase_a"]["runtime_manifest"]),
        "phase_a_freeze": repo_path(
            config["phase_a"]["freeze_determination"]
        ),
        "split_freeze": repo_path(
            config["split_design"]["freeze_manifest"]
        ),
        "calibration_split": split_path,
        "determination": determination_path,
        **{
            f"collection/{name}": repo_path(metadata["path"])
            for name, metadata in artifacts["collection_bundle"]["files"].items()
        },
        **{
            f"code/{name}": repo_path(metadata["path"])
            for name, metadata in determination["code_evidence"].items()
        },
    }
    protected_artifacts = {
        name: committed_file_info(ROOT, path)
        for name, path in protected_paths.items()
    }
    h4a_pass = bool(
        determination["calibration"]["h4a_certified_set_nonempty"]
    )
    lock = {
        "experiment_id": config["experiment_id"],
        "px_id": "PX-057",
        "stage": "H4_LTT_determination_lock",
        "cell_id": cell_id,
        "determination_path": determination_path.relative_to(ROOT).as_posix(),
        "determination_sha256": sha256_file(determination_path),
        "determination_last_change_commit": committed["last_change_commit"],
        "determination_verified_at_head": committed["verified_at_head"],
        "h4a_certified_set_nonempty": h4a_pass,
        "selected_policy": determination["calibration"]["selected_policy"],
        "phase_a_evidence": phase_a_evidence,
        "protected_artifacts": protected_artifacts,
        "rule": (
            "This terminal calibration lock must itself be committed before any H4 "
            "holdout trace is generated. A null selected_policy closes this cell "
            "without holdout generation."
        ),
    }
    write_json(lock_path, lock)
    return lock


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px057_h4_ltt_transfer_20260725.json"),
    )
    parser.add_argument("--cell", required=True)
    parser.add_argument("--trace-path", type=Path)
    parser.add_argument("--output-path", type=Path)
    parser.add_argument("--write-lock", action="store_true")
    parser.add_argument("--determination-path", type=Path)
    parser.add_argument("--lock-path", type=Path)
    args = parser.parse_args()

    config_path = repo_path(args.config)
    if args.write_lock:
        result = write_lock(
            config_path,
            cell_id=args.cell,
            determination_path=(
                None
                if args.determination_path is None
                else repo_path(args.determination_path)
            ),
            lock_path=None if args.lock_path is None else repo_path(args.lock_path),
        )
    else:
        result = run_calibration(
            config_path,
            cell_id=args.cell,
            trace_path=None if args.trace_path is None else repo_path(args.trace_path),
            output_path=(
                None if args.output_path is None else repo_path(args.output_path)
            ),
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
