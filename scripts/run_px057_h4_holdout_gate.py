#!/usr/bin/env python
"""Apply one committed PX-057 H4 policy once to its held-out split."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import (
    Policy,
    calibrate_cell,
    committed_file_info,
    evaluate_policy,
    heldout_gate,
    load_scored_traces,
    normalize_choice_answer,
    normalize_numeric_answer,
    policy_from_dict,
    read_json,
    read_jsonl,
    select_audit_question_ids,
    sha256_file,
    stable_collection_evidence,
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


def verify_all_locks(
    config: dict[str, Any], config_path: Path | None = None
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    if config_path is None:
        config_path = repo_path(
            config.get(
                "_config_path",
                "configs/px057_h4_ltt_transfer_20260725.json",
            )
        )
    if config["experiment_id"] != read_json(config_path)["experiment_id"]:
        raise ValueError("lock verifier received a noncanonical config")
    config_commit = committed_file_info(ROOT, config_path)
    phase_a_evidence = verify_phase_a_freeze(
        ROOT, config_path, config, require_current_runtime=False
    )
    for cell in config["cells"]:
        lock_path = repo_path(cell["ltt_lock_manifest"])
        lock_commit = committed_file_info(ROOT, lock_path)
        lock = read_json(lock_path)
        if lock["cell_id"] != cell["cell_id"]:
            raise ValueError(f"{lock_path}: cell mismatch")
        determination_path = repo_path(lock["determination_path"])
        expected_determination_path = repo_path(cell["ltt_determination"])
        if determination_path.resolve() != expected_determination_path.resolve():
            raise ValueError(f"{lock_path}: noncanonical determination path")
        determination_commit = committed_file_info(ROOT, determination_path)
        if sha256_file(determination_path) != lock["determination_sha256"]:
            raise ValueError(f"{lock_path}: determination hash mismatch")
        determination = read_json(determination_path)
        if determination["input_artifacts"]["config"]["sha256"] != sha256_file(
            config_path
        ):
            raise ValueError(f"{lock_path}: determination config hash mismatch")
        if (
            determination["experiment_id"] != config["experiment_id"]
            or determination["cell_id"] != cell["cell_id"]
            or determination["model"] != config["models"][cell["model_key"]]
            or determination["dataset_key"] != cell["dataset_key"]
            or determination["prompt_template_id"]
            != config["generation"]["prompt_template_id"]
        ):
            raise ValueError(f"{lock_path}: determination identity mismatch")
        if (
            bool(determination["calibration"]["h4a_certified_set_nonempty"])
            != bool(lock["h4a_certified_set_nonempty"])
        ):
            raise ValueError(f"{lock_path}: H4a outcome mismatch")
        if determination["calibration"]["selected_policy"] != lock["selected_policy"]:
            raise ValueError(f"{lock_path}: selected policy mismatch")
        expected_protected_paths = {
            config_path.relative_to(ROOT).as_posix(),
            str(config["generation"]["prompt_template_path"]),
            str(config["phase_a"]["requirements_path"]),
            str(config["phase_a"]["runtime_manifest"]),
            str(config["phase_a"]["freeze_determination"]),
            str(config["split_design"]["freeze_manifest"]),
            str(cell["calibration_manifest"]),
            str(cell["ltt_determination"]),
            *[
                str(metadata["path"])
                for metadata in determination["input_artifacts"][
                    "collection_bundle"
                ]["files"].values()
            ],
            *[
                str(metadata["path"])
                for metadata in determination["code_evidence"].values()
            ],
        }
        observed_protected_paths = {
            str(metadata["path"])
            for metadata in lock["protected_artifacts"].values()
        }
        if observed_protected_paths != expected_protected_paths:
            raise ValueError(f"{lock_path}: protected artifact set mismatch")
        for name, metadata in lock["protected_artifacts"].items():
            protected_path = repo_path(metadata["path"])
            protected_commit = committed_file_info(ROOT, protected_path)
            if protected_commit["sha256"] != metadata["sha256"]:
                raise ValueError(
                    f"{lock_path}: protected artifact changed: {name}"
                )
            if (
                protected_commit["last_change_commit"]
                != metadata["last_change_commit"]
            ):
                raise ValueError(
                    f"{lock_path}: protected artifact commit changed: {name}"
                )
        trace_path = repo_path(
            determination["input_artifacts"]["traces"]["path"]
        )
        split_path = repo_path(
            determination["input_artifacts"]["split"]["path"]
        )
        traces, _ = load_scored_traces(
            trace_path,
            split_path,
            expected_rounds=int(config["generation"]["rounds"]),
        )
        risk = config["risk_control"]
        recomputed = calibrate_cell(
            traces,
            population_size=int(cell["eligible_population_size"]),
            grid=risk["policy_grid"],
            order_spec=risk["fixed_sequence_order"],
            alpha=float(risk["alpha"]),
            cell_delta=float(risk["family_delta"]) / len(config["cells"]),
        )
        if recomputed != determination["calibration"]:
            raise ValueError(f"{lock_path}: determination recomputation mismatch")
        lock_remote_refs = [
            value.strip()
            for value in subprocess.check_output(
                [
                    "git",
                    "branch",
                    "-r",
                    "--contains",
                    lock_commit["last_change_commit"],
                ],
                cwd=ROOT,
                text=True,
            ).splitlines()
            if value.strip()
        ]
        if not lock_remote_refs:
            raise ValueError(f"{lock_path}: lock commit has not been pushed")
        evidence[cell["cell_id"]] = {
            "lock_path": lock_path.relative_to(ROOT).as_posix(),
            "lock_sha256": sha256_file(lock_path),
            "lock_commit": lock_commit,
            "determination_commit": determination_commit,
            "determination_sha256": lock["determination_sha256"],
            "config_commit": config_commit,
            "phase_a_evidence": phase_a_evidence,
            "lock_remote_refs": lock_remote_refs,
        }
    return evidence


def audit_status(
    path: Path | None,
    *,
    cell_id: str,
    traces: list[Any],
    blinded_path: Path | None = None,
    source_evidence: dict[str, Any] | None = None,
    split_rows: list[dict[str, Any]] | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "status": "PENDING",
            "valid": False,
            "reason": "The blinded 50-trace / 400-round extraction audit is missing.",
            "expected_path": None if path is None else str(path),
        }
    payload = read_json(path)
    required = {
        "cell_id": cell_id,
        "trace_units": 50,
        "round_units": 400,
        "seed": 5703,
        "auditor_blinded_to_automated_answer": True,
        "auditor_blinded_to_policy_and_gate": True,
    }
    checks = {key: payload.get(key) == value for key, value in required.items()}
    expected_ids = select_audit_question_ids(traces, seed=5703, sample_size=50)
    checks["audit_question_ids_match"] = payload.get("question_ids") == expected_ids
    trace_answers = {
        (trace.question_id, step.step): step.answer
        for trace in traces
        if trace.question_id in set(expected_ids)
        for step in trace.steps
    }
    judgments = payload.get("judgments", [])
    observed_keys = [
        (str(row.get("question_id")), int(row.get("round", -1)))
        for row in judgments
    ]
    checks["judgment_units_complete"] = (
        len(judgments) == 400
        and len(set(observed_keys)) == 400
        and set(observed_keys) == set(trace_answers)
    )
    checks["automated_answers_match_trace"] = all(
        str(row.get("automated_answer", "")) == trace_answers.get(key)
        for row, key in zip(judgments, observed_keys)
    )
    normalized_manual_answers: list[str] = []
    if split_rows is not None:
        split_by_id = {str(row["question_id"]): row for row in split_rows}
        for judgment, key in zip(judgments, observed_keys):
            manual_raw = str(
                judgment.get(
                    "auditor_answer_raw",
                    judgment.get("auditor_answer", ""),
                )
            )
            split_row = split_by_id[key[0]]
            normalized_manual_answers.append(
                normalize_numeric_answer(manual_raw)
                if split_row["answer_type"] == "numeric"
                else normalize_choice_answer(
                    manual_raw, split_row["choice_labels"]
                )
            )
        checks["joined_normalized_answers_match"] = all(
            normalized == str(judgment.get("auditor_answer", ""))
            for normalized, judgment in zip(
                normalized_manual_answers, judgments
            )
        )
    else:
        normalized_manual_answers = [
            str(row.get("auditor_answer", "")).strip().upper()
            for row in judgments
        ]
    computed_disagreements = sum(
        str(row.get("automated_answer", "")).strip().upper()
        != normalized.strip().upper()
        for row, normalized in zip(judgments, normalized_manual_answers)
    )
    disagreements = int(payload["round_disagreements"])
    checks["disagreement_count_matches"] = disagreements == computed_disagreements
    checks["round_disagreements_at_most_8"] = disagreements <= 8
    blinded_evidence: dict[str, Any] | None = None
    if blinded_path is not None:
        checks["auditor_blinded_to_gold"] = (
            payload.get("auditor_blinded_to_gold") is True
        )
        blinded_commit = committed_file_info(ROOT, blinded_path)
        blinded_sha256 = sha256_file(blinded_path)
        recorded_commit = payload.get("blinded_judgments_commit", {})
        checks["blinded_path_matches"] = (
            payload.get("blinded_judgments_path")
            == blinded_path.relative_to(ROOT).as_posix()
        )
        checks["blinded_sha256_matches"] = (
            payload.get("blinded_judgments_sha256") == blinded_sha256
        )
        checks["blinded_commit_matches"] = (
            recorded_commit.get("last_change_commit")
            == blinded_commit["last_change_commit"]
        )
        blinded = read_json(blinded_path)
        if source_evidence is not None:
            checks["source_evidence_matches_current_bundle"] = (
                payload.get("source_evidence") == source_evidence
                and blinded.get("source_evidence") == source_evidence
            )
            blinded_change_commit = blinded_commit["last_change_commit"]
            source_commits = list(
                source_evidence["collection_last_change_commits"].values()
            ) + [source_evidence["split"]["last_change_commit"]]
            checks["source_commits_precede_blinded_judgments"] = all(
                subprocess.run(
                    [
                        "git",
                        "merge-base",
                        "--is-ancestor",
                        source_commit,
                        blinded_change_commit,
                    ],
                    cwd=ROOT,
                    check=False,
                ).returncode
                == 0
                for source_commit in source_commits
            )
        blinded_items = list(blinded.get("items", []))
        blinded_keys = [
            (str(row.get("question_id")), int(row.get("round", -1)))
            for row in blinded_items
        ]
        checks["blinded_units_match"] = blinded_keys == observed_keys
        forbidden = {
            "automated_answer",
            "gold_answer",
            "correct",
            "selected_policy",
            "gate_result",
        }
        checks["blinded_packet_has_no_forbidden_fields"] = all(
            forbidden.isdisjoint(row) for row in blinded_items
        )
        if split_rows is not None and raw_rows is not None:
            split_by_id = {
                str(row["question_id"]): row for row in split_rows
            }
            raw_by_key = {
                (str(row["question_id"]), int(row["round"])): row
                for row in raw_rows
            }
            content_matches = len(blinded_items) == len(blinded_keys)
            for row, key in zip(blinded_items, blinded_keys):
                split_row = split_by_id.get(key[0])
                raw_row = raw_by_key.get(key)
                content_matches &= (
                    split_row is not None
                    and raw_row is not None
                    and row.get("question") == split_row["question"]
                    and row.get("choices") == split_row.get("choices")
                    and row.get("raw_response") == raw_row["response"]
                )
            checks["blinded_content_matches_current_bundle"] = content_matches
        derived_answers = []
        for row in blinded_items:
            primary_entry = str(row.get("primary_answer", "")).strip()
            primary = "" if primary_entry == "<NO_ANSWER>" else primary_entry
            ambiguous = bool(row.get("primary_ambiguous", False))
            second_entry = str(
                row.get("second_adjudicator_answer") or ""
            ).strip()
            second = "" if second_entry == "<NO_ANSWER>" else second_entry
            derived_answers.append(second if ambiguous else primary)
        checks["joined_answers_match_blinded_source"] = (
            derived_answers
            == [
                str(
                    row.get(
                        "auditor_answer_raw",
                        row.get("auditor_answer", ""),
                    )
                )
                for row in judgments
            ]
        )
        blinded_evidence = {
            "path": blinded_path.relative_to(ROOT).as_posix(),
            "sha256": blinded_sha256,
            "last_change_commit": blinded_commit["last_change_commit"],
        }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL_INVALID_CELL",
        "valid": all(checks.values()),
        "checks": checks,
        "round_disagreements": disagreements,
        "path": path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else str(path),
        "sha256": sha256_file(path),
        "blinded_evidence": blinded_evidence,
    }


def run_holdout(
    config_path: Path,
    *,
    cell_id: str,
    trace_path: Path | None = None,
    output_path: Path | None = None,
    manual_audit_path: Path | None = None,
) -> dict[str, Any]:
    config = read_json(config_path)
    config_commit = committed_file_info(ROOT, config_path)
    phase_a_evidence = verify_phase_a_freeze(
        ROOT, config_path, config, require_current_runtime=False
    )
    code_evidence = {
        "holdout_gate": committed_file_info(ROOT, Path(__file__)),
        "common": committed_file_info(ROOT, ROOT / "scripts/px057_h4_common.py"),
        "gate_backend": committed_file_info(
            ROOT, ROOT / "scripts/run_px057_adaptive_stopping_gate.py"
        ),
    }
    cell = get_cell(config, cell_id)
    all_lock_evidence = verify_all_locks(config, config_path)
    lock = read_json(repo_path(cell["ltt_lock_manifest"]))
    if lock["selected_policy"] is None:
        raise ValueError(
            f"{cell_id}: H4a produced no policy; no holdout gate may be run"
        )
    policy = policy_from_dict(lock["selected_policy"])

    split_path = repo_path(cell["holdout_manifest"])
    split_freeze_evidence = verify_frozen_split(
        ROOT,
        repo_path(config["split_design"]["freeze_manifest"]),
        split_path,
    )
    expected_trace_path = (
        repo_path(cell["output_dirs"]["holdout"]) / "reasoning_traces.jsonl"
    )
    if trace_path is None:
        trace_path = expected_trace_path
    if trace_path.resolve() != expected_trace_path.resolve():
        raise ValueError("holdout trace path differs from the frozen config")
    if trace_path.name != "reasoning_traces.jsonl":
        raise ValueError("holdout trace must belong to a complete collection bundle")
    expected_output_path = repo_path(cell["holdout_determination"])
    if output_path is None:
        output_path = expected_output_path
    if output_path.resolve() != expected_output_path.resolve():
        raise ValueError("holdout determination path differs from the frozen config")
    if output_path.exists():
        raise FileExistsError(
            f"{output_path} already exists; held-out determinations are immutable"
        )
    collection_bundle = verify_collection_bundle(
        trace_path.parent,
        split_path,
        repo_root=ROOT,
        expected_cell_id=cell_id,
        expected_split="holdout",
        expected_n=int(config["split_design"]["holdout_n"]),
        expected_rounds=int(config["generation"]["rounds"]),
        expected_model=config["models"][cell["model_key"]],
        expected_prompt_id=config["generation"]["prompt_template_id"],
        expected_prompt_sha256=config["generation"]["prompt_template_sha256"],
    )
    traces, split_rows = load_scored_traces(
        trace_path,
        split_path,
        expected_rounds=int(config["generation"]["rounds"]),
    )
    expected_n = int(config["split_design"]["holdout_n"])
    if len(traces) != expected_n:
        raise ValueError(f"expected {expected_n} held-out traces")
    trace_commit = committed_file_info(ROOT, trace_path)
    bundle_commits = {
        name: committed_file_info(ROOT, repo_path(metadata["path"]))
        for name, metadata in collection_bundle["files"].items()
    }
    source_evidence = stable_collection_evidence(
        ROOT, collection_bundle, split_path
    )

    expected_audit_path = repo_path(cell["manual_audit"])
    if manual_audit_path is None:
        manual_audit_path = expected_audit_path
    if manual_audit_path.resolve() != expected_audit_path.resolve():
        raise ValueError("manual audit path differs from the frozen config")
    if not manual_audit_path.exists():
        raise ValueError(
            "the blinded manual-audit join must be committed before gate calculation"
        )
    audit_commit = committed_file_info(ROOT, manual_audit_path)
    manual_audit = audit_status(
        manual_audit_path,
        cell_id=cell_id,
        traces=traces,
        blinded_path=repo_path(cell["manual_audit_blinded"]),
        source_evidence=source_evidence,
        split_rows=split_rows,
        raw_rows=read_jsonl(
            trace_path.parent / "raw_generations.jsonl"
        ),
    )
    if not manual_audit["valid"]:
        raise ValueError(
            "manual extraction audit failed; scientific point gates are not computed"
        )

    gates = config["heldout_gates"]
    gate_result = heldout_gate(
        traces,
        policy,
        harm_rate_max=float(gates["harm_rate_max"]),
        accuracy_delta_min=float(gates["accuracy_delta_min"]),
        mean_compute_saving_min=float(gates["mean_compute_saving_min"]),
    )
    confidence_ablation: dict[str, Any] | None = None
    if policy.confidence_threshold > 0.0:
        no_confidence = Policy(policy.min_step, policy.patience, 0.0)
        ablation_metrics = evaluate_policy(traces, no_confidence)
        confidence_ablation = {
            "matched_policy": no_confidence.to_dict(),
            "metrics": {
                key: value
                for key, value in ablation_metrics.items()
                if key != "rows"
            },
            "interpretation": (
                "Descriptive matched ablation only. H4e is an operational retention "
                "rule, not a causal test of confidence."
            ),
        }
    result = {
        "experiment_id": config["experiment_id"],
        "px_id": "PX-057",
        "stage": "H4_heldout_gate",
        "cell_id": cell_id,
        "model": config["models"][cell["model_key"]],
        "dataset_key": cell["dataset_key"],
        "gate_result": gate_result,
        "confidence_ablation": confidence_ablation,
        "manual_audit": manual_audit,
        "cell_valid": True,
        "cell_pass": bool(gate_result["heldout_gate_pass"]),
        "lock_evidence": all_lock_evidence,
        "input_artifacts": {
            "config_sha256": sha256_file(config_path),
            "config_commit": config_commit,
            "split_sha256": sha256_file(split_path),
            "split_freeze_evidence": split_freeze_evidence,
            "trace_sha256": sha256_file(trace_path),
            "trace_commit": trace_commit,
            "collection_bundle": collection_bundle,
            "collection_bundle_commits": bundle_commits,
            "manual_audit_commit": audit_commit,
            "split_rows": len(split_rows),
        },
        "code_evidence": code_evidence,
        "phase_a_evidence": phase_a_evidence,
        "claim_boundary": (
            "The calibration certificate concerns the finite frozen benchmark "
            "population. H4b-H4d are held-out point gates. A failed H4b is an "
            "empirical inconsistency, not a logical certificate violation or proof "
            "of distribution shift."
        ),
    }
    write_json(output_path, result)
    return result


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
    parser.add_argument("--manual-audit", type=Path)
    args = parser.parse_args()
    result = run_holdout(
        repo_path(args.config),
        cell_id=args.cell,
        trace_path=None if args.trace_path is None else repo_path(args.trace_path),
        output_path=None if args.output_path is None else repo_path(args.output_path),
        manual_audit_path=(
            None if args.manual_audit is None else repo_path(args.manual_audit)
        ),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
