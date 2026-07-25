#!/usr/bin/env python
"""Independently adjudicate the complete PX-057 H4 evidence package."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import (
    committed_file_info,
    read_json,
    read_jsonl,
    sha256_file,
    stable_collection_evidence,
    verify_collection_bundle,
    verify_phase_a_freeze,
    write_json,
)
from scripts.run_px057_h4_holdout_gate import audit_status, verify_all_locks


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def independent_normalize_answer(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\\boxed\{([^{}]+)\}", r"\1", value)
    value = value.replace(",", "")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"^(the answer is|answer:)\s*", "", value)
    return value.strip(" .")


def independent_numeric(value: str) -> str:
    cleaned = independent_normalize_answer(value)
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return cleaned
    if not number.is_finite():
        return cleaned
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"", "-0"} else normalized


def independent_score(answer: str, gold_row: dict[str, Any]) -> bool:
    if gold_row["answer_type"] == "numeric":
        return independent_numeric(answer) == independent_numeric(
            str(gold_row["gold_answer"])
        )
    allowed = {
        str(value).strip().upper() for value in gold_row["choice_labels"]
    }

    def choice(value: str) -> str:
        cleaned = independent_normalize_answer(value).upper()
        if cleaned in allowed:
            return cleaned
        tokens = re.findall(
            r"(?<![A-Z0-9])([A-Z0-9]+)(?![A-Z0-9])", value.upper()
        )
        return next(
            (candidate for candidate in reversed(tokens) if candidate in allowed),
            cleaned,
        )

    return choice(answer) == choice(str(gold_row["gold_answer"]))


def independent_load_traces(
    trace_path: Path, split_path: Path, expected_rounds: int
) -> list[dict[str, Any]]:
    split_rows = read_jsonl(split_path)
    split_by_id = {str(row["question_id"]): row for row in split_rows}
    raw_traces = read_jsonl(trace_path)
    if (
        len(split_by_id) != len(split_rows)
        or len({str(row["question_id"]) for row in raw_traces})
        != len(raw_traces)
        or {str(row["question_id"]) for row in raw_traces}
        != set(split_by_id)
    ):
        raise ValueError("independent scorer found split/trace ID drift")
    traces = []
    for raw in raw_traces:
        question_id = str(raw["question_id"])
        steps = list(raw["steps"])
        if [int(step["step"]) for step in steps] != list(
            range(1, expected_rounds + 1)
        ):
            raise ValueError(f"{question_id}: independent round check failed")
        cumulative = [int(step["tokens"]) for step in steps]
        if cumulative != sorted(cumulative) or any(value < 0 for value in cumulative):
            raise ValueError(f"{question_id}: independent token check failed")
        scored_steps = [
            {
                "step": int(step["step"]),
                "answer": str(step["answer"]),
                "correct": independent_score(
                    str(step["answer"]), split_by_id[question_id]
                ),
                "confidence": float(step["confidence"]),
                "tokens": int(step["tokens"]),
            }
            for step in steps
        ]
        if any(
            not 0.0 <= step["confidence"] <= 1.0 for step in scored_steps
        ):
            raise ValueError(f"{question_id}: independent confidence check failed")
        traces.append(
            {
                "question_id": question_id,
                "domain": raw.get("domain", "unknown"),
                "steps": scored_steps,
            }
        )
    return traces


def independent_policies(risk: dict[str, Any]) -> list[dict[str, Any]]:
    grid = risk["policy_grid"]
    order = risk["fixed_sequence_order"]
    grid_tuples = {
        (int(min_step), int(patience), float(threshold))
        for min_step in grid["min_step"]
        for patience in grid["patience"]
        for threshold in grid["confidence_threshold"]
    }
    ordered_tuples = [
        (int(min_step), int(patience), float(threshold))
        for min_step in order["min_step"]
        for patience in order["patience"]
        for threshold in order["confidence_threshold"]
    ]
    if len(ordered_tuples) != 30 or set(ordered_tuples) != grid_tuples:
        raise ValueError("independent policy-order check failed")
    return [
        {
            "policy_id": (
                f"m{min_step}-k{patience}-tau"
                f"{threshold:.2f}".replace(".", "p")
            ),
            "min_step": min_step,
            "patience": patience,
            "confidence_threshold": threshold,
        }
        for min_step, patience, threshold in ordered_tuples
    ]


def independent_evaluate(
    traces: list[dict[str, Any]], policy: dict[str, Any]
) -> dict[str, Any]:
    rows = []
    for trace in traces:
        steps = trace["steps"]
        selected = steps[-1]
        for index, current in enumerate(steps):
            patience = int(policy["patience"])
            if (
                current["step"] < int(policy["min_step"])
                or index + 1 < patience
            ):
                continue
            window = steps[index + 1 - patience : index + 1]
            stable = len(
                {independent_normalize_answer(item["answer"]) for item in window}
            ) == 1
            threshold = float(policy["confidence_threshold"])
            confident = threshold == 0.0 or all(
                item["confidence"] >= threshold for item in window
            )
            if stable and confident:
                selected = current
                break
        final = steps[-1]
        eligible_correct = any(
            step["correct"]
            and step["step"] >= int(policy["min_step"])
            for step in steps[:-1]
        )
        overthinking = eligible_correct and not final["correct"]
        harm = final["correct"] and not selected["correct"]
        saving = (
            0.0
            if final["tokens"] <= 0
            else 1.0 - selected["tokens"] / final["tokens"]
        )
        rows.append(
            {
                "harm": harm,
                "selected_correct": selected["correct"],
                "fixed_correct": final["correct"],
                "saving": saving,
                "overthinking": overthinking,
                "prevented": overthinking and selected["correct"],
            }
        )
    n = len(rows)
    harm_count = sum(row["harm"] for row in rows)
    selected_correct = sum(row["selected_correct"] for row in rows)
    fixed_correct = sum(row["fixed_correct"] for row in rows)
    overthinking = sum(row["overthinking"] for row in rows)
    prevented = sum(row["prevented"] for row in rows)
    return {
        "policy": policy,
        "n": n,
        "harm_count": harm_count,
        "harm_rate": harm_count / n,
        "selected_correct": selected_correct,
        "selected_accuracy": selected_correct / n,
        "fixed_long_correct": fixed_correct,
        "fixed_long_accuracy": fixed_correct / n,
        "accuracy_delta": (selected_correct - fixed_correct) / n,
        "mean_compute_saving": sum(row["saving"] for row in rows) / n,
        "overthinking_events": overthinking,
        "overthinking_prevented": prevented,
        "overthinking_prevention_rate": (
            prevented / overthinking if overthinking else None
        ),
    }


def h4e_decision(
    *,
    selected_policy_cells: int,
    positive_tau_cells: int,
    total_cells: int,
) -> str:
    if selected_policy_cells < total_cells:
        return "INCONCLUSIVE"
    if positive_tau_cells >= 2:
        return "RETAIN_FOR_FUTURE_PX057_CANDIDATE"
    return "RETIRE_FROM_FUTURE_PX057_CANDIDATE"


def independent_collection_provenance_checks(
    config: dict[str, Any],
    cell: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, bool]:
    phase = config["phase_a"]
    freeze_path = repo_path(phase["freeze_determination"])
    runtime_path = repo_path(phase["runtime_manifest"])
    freeze = read_json(freeze_path)
    frozen_runtime = read_json(runtime_path)
    generation_base = summary["config_commit"]["verified_at_head"]

    def recorded_file_matches(
        recorded: dict[str, Any], current: dict[str, Any]
    ) -> bool:
        return (
            recorded.get("path") == current["path"]
            and recorded.get("sha256") == current["sha256"]
            and recorded.get("last_change_commit")
            == current["last_change_commit"]
            and recorded.get("verified_at_head") == generation_base
        )

    protected_by_path = {
        str(metadata["path"]): metadata
        for metadata in freeze["protected_artifacts"].values()
    }
    config_path = repo_path("configs/px057_h4_ltt_transfer_20260725.json")
    expected_code_paths = {
        "collector": "scripts/run_px057_h4_trace_collection.py",
        "common": "scripts/px057_h4_common.py",
        "generation_backend": "scripts/run_px057_trace_collection.py",
    }
    code_checks = []
    for name, relative in expected_code_paths.items():
        current = committed_file_info(ROOT, repo_path(relative))
        recorded = summary["code_evidence"].get(name, {})
        frozen = protected_by_path.get(relative, {})
        code_checks.append(
            recorded_file_matches(recorded, current)
            and frozen.get("sha256") == current["sha256"]
            and frozen.get("last_change_commit")
            == current["last_change_commit"]
        )
    model_smoke = frozen_runtime["model_smokes"][cell["model_key"]]
    summary_runtime = summary["runtime"]
    runtime_fields_match = all(
        summary_runtime.get(key) == frozen_runtime.get(key)
        for key in (
            "python",
            "platform",
            "torch",
            "transformers",
            "cuda_runtime",
            "cudnn",
            "cuda_devices",
        )
    ) and all(
        summary_runtime.get(summary_key) == model_smoke.get(smoke_key)
        for summary_key, smoke_key in (
            ("model_config_commit", "resolved_config_commit"),
            ("model_dtype", "model_dtype"),
            ("chat_template_sha256", "chat_template_sha256"),
            ("model_class", "model_class"),
            ("tokenizer_class", "tokenizer_class"),
        )
    ) and summary_runtime.get("cuda_available") is True
    phase_summary = summary["phase_a_evidence"]
    phase_commit = committed_file_info(ROOT, freeze_path)
    runtime_commit = committed_file_info(ROOT, runtime_path)
    config_commit = committed_file_info(ROOT, config_path)
    prompt_path = repo_path(config["generation"]["prompt_template_path"])
    prompt_commit = committed_file_info(ROOT, prompt_path)
    split_name = str(summary["split"])
    split_path = repo_path(cell[f"{split_name}_manifest"])
    split_commit = committed_file_info(ROOT, split_path)
    split_freeze_path = repo_path(config["split_design"]["freeze_manifest"])
    split_freeze_commit = committed_file_info(ROOT, split_freeze_path)
    prompt_summary = summary["prompt_template"]
    split_summary = summary["split_manifest"]
    split_freeze_summary = summary["split_freeze_evidence"]
    return {
        "collection_identity_matches": (
            summary["experiment_id"] == config["experiment_id"]
            and summary["cell_id"] == cell["cell_id"]
            and split_name in {"calibration", "holdout"}
        ),
        "config_identity_matches": (
            recorded_file_matches(summary["config_commit"], config_commit)
        ),
        "phase_freeze_identity_matches": (
            recorded_file_matches(phase_summary["freeze"], phase_commit)
            and recorded_file_matches(phase_summary["runtime"], runtime_commit)
            and phase_summary["runtime_sha256"] == sha256_file(runtime_path)
            and phase_summary["verified_at_head"] == generation_base
        ),
        "phase_freeze_precedes_generation": (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    phase_commit["last_change_commit"],
                    generation_base,
                ],
                cwd=ROOT,
                check=False,
            ).returncode
            == 0
        ),
        "code_identity_matches": all(code_checks),
        "runtime_identity_matches": runtime_fields_match,
        "model_identity_matches": (
            summary["model"] == config["models"][cell["model_key"]]
        ),
        "prompt_identity_matches": (
            summary["prompt_template_id"]
            == config["generation"]["prompt_template_id"]
            and prompt_summary["path"]
            == config["generation"]["prompt_template_path"]
            and prompt_summary["sha256"]
            == config["generation"]["prompt_template_sha256"]
            and prompt_summary["sha256"] == sha256_file(prompt_path)
            and recorded_file_matches(prompt_summary["commit"], prompt_commit)
        ),
        "split_identity_matches": (
            split_summary["path"] == split_commit["path"]
            and split_summary["sha256"] == sha256_file(split_path)
            and int(split_summary["rows"])
            == int(config["split_design"][f"{split_name}_n"])
            and recorded_file_matches(
                split_freeze_summary["freeze"], split_freeze_commit
            )
            and recorded_file_matches(
                split_freeze_summary["split"], split_commit
            )
            and split_freeze_summary["sha256"] == sha256_file(split_path)
            and int(split_freeze_summary["rows"])
            == int(config["split_design"][f"{split_name}_n"])
        ),
    }


def exact_hypergeom_tail_integer(
    population_size: int,
    population_successes: int,
    sample_size: int,
    observed_successes: int,
) -> float:
    """Second implementation using exact integer combinations."""

    lower = max(0, sample_size - (population_size - population_successes))
    upper = min(observed_successes, sample_size, population_successes)
    if upper < lower:
        return 0.0
    numerator = sum(
        math.comb(population_successes, value)
        * math.comb(
            population_size - population_successes, sample_size - value
        )
        for value in range(lower, upper + 1)
    )
    denominator = math.comb(population_size, sample_size)
    return numerator / denominator


def check_splits(config: dict[str, Any]) -> dict[str, bool]:
    freeze_path = repo_path(config["split_design"]["freeze_manifest"])
    committed_file_info(ROOT, freeze_path)
    freeze = read_json(freeze_path)
    checks: dict[str, bool] = {
        "freeze_manifest_hashes_self_consistent": True,
        "gsm_calibration_holdout_disjoint": True,
        "arc_calibration_holdout_disjoint": True,
        "gsm_excludes_gate2_ids": True,
        "arc_manifests_reused_across_model_cells": True,
    }
    loaded: dict[str, list[dict[str, Any]]] = {}
    for name, metadata in freeze["files"].items():
        path = repo_path(metadata["path"])
        committed_file_info(ROOT, path)
        loaded[name] = read_jsonl(path)
        checks["freeze_manifest_hashes_self_consistent"] &= (
            sha256_file(path) == metadata["sha256"]
            and len(loaded[name]) == int(metadata["rows"])
        )
    gsm_cal = {str(row["question_id"]) for row in loaded["gsm8k_calibration"]}
    gsm_hold = {str(row["question_id"]) for row in loaded["gsm8k_holdout"]}
    arc_cal = {
        str(row["question_id"]) for row in loaded["arc_challenge_calibration"]
    }
    arc_hold = {
        str(row["question_id"]) for row in loaded["arc_challenge_holdout"]
    }
    checks["gsm_calibration_holdout_disjoint"] = not bool(gsm_cal & gsm_hold)
    checks["arc_calibration_holdout_disjoint"] = not bool(arc_cal & arc_hold)
    gate2_rows = read_jsonl_or_array(
        repo_path(config["datasets"]["gsm8k"]["gate2_selected_rows"])
    )
    gate2_ids = {str(row["question_id"]) for row in gate2_rows}
    checks["gsm_excludes_gate2_ids"] = not bool((gsm_cal | gsm_hold) & gate2_ids)
    arc_cells = [
        cell for cell in config["cells"] if cell["dataset_key"] == "arc_challenge"
    ]
    checks["arc_manifests_reused_across_model_cells"] = (
        len({cell["calibration_manifest"] for cell in arc_cells}) == 1
        and len({cell["holdout_manifest"] for cell in arc_cells}) == 1
    )
    checks.update(independent_source_checks(config, loaded))
    return checks


def read_jsonl_or_array(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".json":
        value = read_json(path)
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected array")
        return value
    return read_jsonl(path)


def independent_source_checks(
    config: dict[str, Any],
    loaded: dict[str, list[dict[str, Any]]],
) -> dict[str, bool]:
    checks = {
        "gsm_source_hash_and_rows_match": False,
        "arc_source_hash_and_rows_match": False,
        "gsm_split_rederived_from_source": False,
        "arc_split_rederived_from_source": False,
        "frozen_gold_and_prompts_match_sources": False,
    }
    gsm_config = config["datasets"]["gsm8k"]
    gsm_response = requests.get(gsm_config["source_url"], timeout=120)
    gsm_response.raise_for_status()
    gsm_content = gsm_response.content
    gsm_source = [
        json.loads(line)
        for line in gsm_content.decode("utf-8").splitlines()
        if line.strip()
    ]
    checks["gsm_source_hash_and_rows_match"] = (
        hashlib.sha256(gsm_content).hexdigest() == gsm_config["source_sha256"]
        and len(gsm_source) == int(gsm_config["source_population_size"])
    )
    gate2 = read_jsonl_or_array(
        repo_path(gsm_config["gate2_selected_rows"])
    )
    excluded = {str(row["question_id"]) for row in gate2}
    gsm_by_id = {
        f"gsm8k-test-{index}": {
            "question": str(row["question"]),
            "gold_answer": independent_numeric(
                str(row["answer"]).rsplit("####", 1)[-1]
            ),
        }
        for index, row in enumerate(gsm_source)
        if f"gsm8k-test-{index}" not in excluded
    }

    arc_config = config["datasets"]["arc_challenge"]
    arc_response = requests.get(arc_config["source_url"], timeout=120)
    arc_response.raise_for_status()
    arc_content = arc_response.content
    import pandas as pd

    arc_frame = pd.read_parquet(io.BytesIO(arc_content))
    checks["arc_source_hash_and_rows_match"] = (
        hashlib.sha256(arc_content).hexdigest() == arc_config["source_sha256"]
        and len(arc_frame) == int(arc_config["source_population_size"])
    )
    arc_by_id = {}
    for _, record in arc_frame.iterrows():
        choices = record["choices"]
        labels = [str(value) for value in list(choices["label"])]
        texts = [str(value) for value in list(choices["text"])]
        arc_by_id[f"arc-challenge-test-{record['id']}"] = {
            "question": str(record["question"]),
            "gold_answer": str(record["answerKey"]),
            "choice_labels": labels,
            "choices": [
                {"label": label, "text": text}
                for label, text in zip(labels, texts)
            ],
        }

    def derive_ids(
        population_ids: list[str],
    ) -> tuple[list[str], list[str]]:
        split = config["split_design"]
        calibration = sorted(
            population_ids,
            key=lambda question_id: (
                hashlib.sha256(
                    f"{split['calibration_seed']}:{question_id}".encode("utf-8")
                ).hexdigest(),
                question_id,
            ),
        )[: int(split["calibration_n"])]
        calibration_set = set(calibration)
        holdout = sorted(
            [
                question_id
                for question_id in population_ids
                if question_id not in calibration_set
            ],
            key=lambda question_id: (
                hashlib.sha256(
                    f"{split['holdout_seed']}:{question_id}".encode("utf-8")
                ).hexdigest(),
                question_id,
            ),
        )[: int(split["holdout_n"])]
        return calibration, holdout

    gsm_cal_ids, gsm_hold_ids = derive_ids(list(gsm_by_id))
    arc_cal_ids, arc_hold_ids = derive_ids(list(arc_by_id))
    checks["gsm_split_rederived_from_source"] = (
        [row["question_id"] for row in loaded["gsm8k_calibration"]]
        == gsm_cal_ids
        and [row["question_id"] for row in loaded["gsm8k_holdout"]]
        == gsm_hold_ids
    )
    checks["arc_split_rederived_from_source"] = (
        [
            row["question_id"]
            for row in loaded["arc_challenge_calibration"]
        ]
        == arc_cal_ids
        and [row["question_id"] for row in loaded["arc_challenge_holdout"]]
        == arc_hold_ids
    )
    source_fields_match = True
    for name in ("gsm8k_calibration", "gsm8k_holdout"):
        for row in loaded[name]:
            source = gsm_by_id[str(row["question_id"])]
            source_fields_match &= (
                row["question"] == source["question"]
                and independent_numeric(str(row["gold_answer"]))
                == source["gold_answer"]
            )
    for name in ("arc_challenge_calibration", "arc_challenge_holdout"):
        for row in loaded[name]:
            source = arc_by_id[str(row["question_id"])]
            source_fields_match &= all(
                row[key] == source[key]
                for key in (
                    "question",
                    "gold_answer",
                    "choice_labels",
                    "choices",
                )
            )
    checks["frozen_gold_and_prompts_match_sources"] = source_fields_match
    return checks


def recompute_calibration(
    config: dict[str, Any],
    cell: dict[str, Any],
    determination: dict[str, Any],
) -> dict[str, Any]:
    trace_path = (
        repo_path(cell["output_dirs"]["calibration"]) / "reasoning_traces.jsonl"
    )
    split_path = repo_path(cell["calibration_manifest"])
    committed_file_info(ROOT, trace_path)
    collection_bundle = verify_collection_bundle(
        trace_path.parent,
        split_path,
        repo_root=ROOT,
        expected_cell_id=cell["cell_id"],
        expected_split="calibration",
        expected_n=int(config["split_design"]["calibration_n"]),
        expected_rounds=int(config["generation"]["rounds"]),
        expected_model=config["models"][cell["model_key"]],
        expected_prompt_id=config["generation"]["prompt_template_id"],
        expected_prompt_sha256=config["generation"]["prompt_template_sha256"],
    )
    collection_summary = read_json(
        trace_path.parent / "collection_summary.json"
    )
    provenance_checks = independent_collection_provenance_checks(
        config, cell, collection_summary
    )
    for metadata in collection_bundle["files"].values():
        committed_file_info(ROOT, repo_path(metadata["path"]))
    traces = independent_load_traces(
        trace_path,
        split_path,
        int(config["generation"]["rounds"]),
    )
    risk = config["risk_control"]
    ordered = independent_policies(risk)
    cell_delta = float(risk["cell_delta"])
    records = []
    sequence_open = True
    for index, policy in enumerate(ordered, 1):
        metrics = independent_evaluate(traces, policy)
        boundary = math.ceil(
            float(risk["alpha"]) * int(cell["eligible_population_size"])
        )
        p_value = exact_hypergeom_tail_integer(
            int(cell["eligible_population_size"]),
            boundary,
            len(traces),
            int(metrics["harm_count"]),
        )
        reached = sequence_open
        certified = reached and p_value <= cell_delta
        if reached and not certified:
            sequence_open = False
        records.append(
            {
                "sequence_index": index,
                "policy": policy,
                "metrics": metrics,
                "p_value": p_value,
                "reached": reached,
                "certified": certified,
            }
        )
    certified = [record for record in records if record["certified"]]
    selected = (
        None
        if not certified
        else max(
            certified,
            key=lambda record: (
                float(record["metrics"]["mean_compute_saving"]),
                -1.0
                if record["metrics"]["overthinking_prevention_rate"] is None
                else float(record["metrics"]["overthinking_prevention_rate"]),
                -int(record["metrics"]["harm_count"]),
                int(record["policy"]["confidence_threshold"] == 0.0),
                -int(record["sequence_index"]),
            ),
        )
    )
    reported_records = determination["calibration"]["policy_records"]
    record_checks = []
    for observed, reported in zip(records, reported_records):
        record_checks.append(
            observed["sequence_index"] == reported["sequence_index"]
            and observed["policy"] == reported["metrics"]["policy"]
            and observed["reached"] == reported["reached"]
            and observed["certified"] == reported["certified"]
            and abs(observed["p_value"] - reported["risk_test"]["p_value"]) <= 1e-12
            and observed["metrics"]["harm_count"]
            == reported["metrics"]["harm_count"]
            and abs(
                observed["metrics"]["mean_compute_saving"]
                - reported["metrics"]["mean_compute_saving"]
            )
            <= 1e-12
        )
    selected_policy = None if selected is None else selected["policy"]
    return {
        **{
            f"collection_provenance_{name}": passed
            for name, passed in provenance_checks.items()
        },
        "trace_hash_matches": (
            sha256_file(trace_path)
            == determination["input_artifacts"]["traces"]["sha256"]
        ),
        "split_hash_matches": (
            sha256_file(split_path)
            == determination["input_artifacts"]["split"]["sha256"]
        ),
        "collection_bundle_matches": (
            collection_bundle
            == determination["input_artifacts"]["collection_bundle"]
        ),
        "policy_record_count_matches": len(records) == len(reported_records),
        "policy_records_match": len(record_checks) == len(records)
        and all(record_checks),
        "selected_policy_matches": (
            selected_policy == determination["calibration"]["selected_policy"]
        ),
        "h4a_matches": bool(certified)
        == bool(determination["calibration"]["h4a_certified_set_nonempty"]),
        "selected_policy": selected_policy,
    }


def recompute_holdout(
    config: dict[str, Any],
    cell: dict[str, Any],
    determination: dict[str, Any],
    selected_policy: dict[str, Any],
    lock_evidence: dict[str, dict[str, Any]],
) -> tuple[dict[str, bool], bool]:
    trace_path = repo_path(cell["output_dirs"]["holdout"]) / "reasoning_traces.jsonl"
    committed_file_info(ROOT, trace_path)
    collection_bundle = verify_collection_bundle(
        trace_path.parent,
        repo_path(cell["holdout_manifest"]),
        repo_root=ROOT,
        expected_cell_id=cell["cell_id"],
        expected_split="holdout",
        expected_n=int(config["split_design"]["holdout_n"]),
        expected_rounds=int(config["generation"]["rounds"]),
        expected_model=config["models"][cell["model_key"]],
        expected_prompt_id=config["generation"]["prompt_template_id"],
        expected_prompt_sha256=config["generation"]["prompt_template_sha256"],
    )
    for metadata in collection_bundle["files"].values():
        committed_file_info(ROOT, repo_path(metadata["path"]))
    summary = read_json(
        trace_path.parent / "collection_summary.json"
    )
    provenance_checks = independent_collection_provenance_checks(
        config, cell, summary
    )
    generation_base_commit = summary["config_commit"]["verified_at_head"]
    chronology_checks = {
        "generation_base_is_ancestor_of_adjudication": (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    generation_base_commit,
                    "HEAD",
                ],
                cwd=ROOT,
                check=False,
            ).returncode
            == 0
        ),
        "all_locks_precede_holdout_generation": True,
        "summary_lock_hashes_match": True,
    }
    summary_locks = {
        item["lock"]["cell_id"]: item
        for item in summary["holdout_lock_evidence"]
    }
    for locked_cell_id, evidence in lock_evidence.items():
        lock_commit = evidence["lock_commit"]["last_change_commit"]
        chronology_checks["all_locks_precede_holdout_generation"] &= (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    lock_commit,
                    generation_base_commit,
                ],
                cwd=ROOT,
                check=False,
            ).returncode
            == 0
        )
        recorded = summary_locks.get(locked_cell_id, {}).get(
            "verification", {}
        )
        chronology_checks["summary_lock_hashes_match"] &= (
            recorded.get("lock_sha256") == evidence["lock_sha256"]
            and recorded.get("determination_sha256")
            == evidence["determination_sha256"]
            and recorded.get("lock_commit", {}).get("last_change_commit")
            == lock_commit
        )
    traces = independent_load_traces(
        trace_path,
        repo_path(cell["holdout_manifest"]),
        int(config["generation"]["rounds"]),
    )
    gates = config["heldout_gates"]
    metrics = independent_evaluate(traces, selected_policy)
    n = int(metrics["n"])
    harm_limit = math.floor(float(gates["harm_rate_max"]) * n + 1e-12)
    accuracy_floor = math.ceil(
        float(gates["accuracy_delta_min"]) * n - 1e-12
    )
    decisions = {
        "H4b_empirical_harm_consistency": (
            int(metrics["harm_count"]) <= harm_limit
        ),
        "H4c_heldout_accuracy_point_gate": (
            int(metrics["selected_correct"])
            - int(metrics["fixed_long_correct"])
            >= accuracy_floor
        ),
        "H4d_heldout_compute_point_gate": (
            float(metrics["mean_compute_saving"])
            >= float(gates["mean_compute_saving_min"])
        ),
    }
    recomputed = {
        "policy": selected_policy,
        "metrics": metrics,
        "integer_thresholds": {
            "H4b_max_harms": harm_limit,
            "H4c_min_paired_correct_difference": accuracy_floor,
        },
        "decisions": decisions,
        "heldout_gate_pass": all(decisions.values()),
    }
    reported = determination["gate_result"]
    audit_path = repo_path(cell["manual_audit"])
    committed_file_info(ROOT, audit_path)
    recomputed_audit = audit_status(
        audit_path,
        cell_id=cell["cell_id"],
        traces=traces,
        blinded_path=repo_path(cell["manual_audit_blinded"]),
        source_evidence=stable_collection_evidence(
            ROOT,
            collection_bundle,
            repo_path(cell["holdout_manifest"]),
        ),
        split_rows=read_jsonl(repo_path(cell["holdout_manifest"])),
        raw_rows=read_jsonl(
            trace_path.parent / "raw_generations.jsonl"
        ),
    )
    checks = {
        **{
            f"collection_provenance_{name}": passed
            for name, passed in provenance_checks.items()
        },
        "trace_hash_matches": (
            sha256_file(trace_path)
            == determination["input_artifacts"]["trace_sha256"]
        ),
        "collection_bundle_matches": (
            collection_bundle
            == determination["input_artifacts"]["collection_bundle"]
        ),
        "holdout_chronology_valid": all(chronology_checks.values()),
        "policy_matches": recomputed["policy"] == reported["policy"],
        "integer_thresholds_match": (
            recomputed["integer_thresholds"] == reported["integer_thresholds"]
        ),
        "decisions_match": recomputed["decisions"] == reported["decisions"],
        "heldout_gate_pass_matches": (
            recomputed["heldout_gate_pass"]
            == reported["heldout_gate_pass"]
        ),
        "metrics_match": recomputed["metrics"] == reported["metrics"],
        "manual_audit_matches": recomputed_audit == determination["manual_audit"],
        "manual_audit_valid": bool(recomputed_audit["valid"]),
    }
    return checks, bool(recomputed["heldout_gate_pass"])


def adjudicate(config_path: Path) -> dict[str, Any]:
    committed_file_info(ROOT, config_path)
    code_evidence = {
        "adjudicator": committed_file_info(ROOT, Path(__file__)),
        "common": committed_file_info(ROOT, ROOT / "scripts/px057_h4_common.py"),
        "holdout_gate": committed_file_info(
            ROOT, ROOT / "scripts/run_px057_h4_holdout_gate.py"
        ),
    }
    config = read_json(config_path)
    phase_a_evidence = verify_phase_a_freeze(
        ROOT, config_path, config, require_current_runtime=False
    )
    split_checks = check_splits(config)
    lock_evidence = verify_all_locks(config, config_path)
    model2_cells = [
        cell for cell in config["cells"] if cell["model_key"] == "second_model"
    ]
    shared_model_revision = (
        len({config["models"][cell["model_key"]]["revision"] for cell in model2_cells})
        == 1
    )

    cells: dict[str, Any] = {}
    tau_positive = 0
    selected_policy_cells = 0
    all_h4a_to_d = True
    all_valid = all(split_checks.values()) and shared_model_revision
    for cell in config["cells"]:
        calibration_path = repo_path(cell["ltt_determination"])
        holdout_path = repo_path(cell["holdout_determination"])
        calibration = read_json(calibration_path)
        calibration_checks = recompute_calibration(config, cell, calibration)
        selected = calibration_checks["selected_policy"]
        if selected is None:
            holdout_dir = repo_path(cell["output_dirs"]["holdout"])
            unexpected_holdout_files = (
                []
                if not holdout_dir.exists()
                else [path for path in holdout_dir.rglob("*") if path.is_file()]
            )
            holdout_checks = {
                "not_run_without_certified_policy": (
                    not holdout_path.exists() and not unexpected_holdout_files
                )
            }
            h4a_to_d = False
        else:
            selected_policy_cells += 1
            tau_positive += int(float(selected["confidence_threshold"]) > 0.0)
            if not holdout_path.exists():
                trace_path = (
                    repo_path(cell["output_dirs"]["holdout"])
                    / "reasoning_traces.jsonl"
                )
                audit_path = repo_path(cell["manual_audit"])
                if trace_path.exists() and audit_path.exists():
                    committed_file_info(ROOT, trace_path)
                    committed_file_info(ROOT, audit_path)
                    audit_traces = independent_load_traces(
                        trace_path,
                        repo_path(cell["holdout_manifest"]),
                        int(config["generation"]["rounds"]),
                    )
                    audit_objects = [
                        SimpleNamespace(
                            question_id=trace["question_id"],
                            steps=[
                                SimpleNamespace(**step)
                                for step in trace["steps"]
                            ],
                        )
                        for trace in audit_traces
                    ]
                    failed_audit = audit_status(
                        audit_path,
                        cell_id=cell["cell_id"],
                        traces=audit_objects,
                        blinded_path=repo_path(cell["manual_audit_blinded"]),
                        source_evidence=stable_collection_evidence(
                            ROOT,
                            verify_collection_bundle(
                                trace_path.parent,
                                repo_path(cell["holdout_manifest"]),
                                repo_root=ROOT,
                                expected_cell_id=cell["cell_id"],
                                expected_split="holdout",
                                expected_n=int(
                                    config["split_design"]["holdout_n"]
                                ),
                                expected_rounds=int(
                                    config["generation"]["rounds"]
                                ),
                                expected_model=config["models"][
                                    cell["model_key"]
                                ],
                                expected_prompt_id=config["generation"][
                                    "prompt_template_id"
                                ],
                                expected_prompt_sha256=config["generation"][
                                    "prompt_template_sha256"
                                ],
                            ),
                            repo_path(cell["holdout_manifest"]),
                        ),
                        split_rows=read_jsonl(
                            repo_path(cell["holdout_manifest"])
                        ),
                        raw_rows=read_jsonl(
                            trace_path.parent / "raw_generations.jsonl"
                        ),
                    )
                    holdout_checks = {
                        "trace_available_for_invalid_audit": bool(audit_traces),
                        "holdout_determination_absent": True,
                        "manual_audit_valid": bool(failed_audit["valid"]),
                    }
                else:
                    holdout_checks = {
                        "required_holdout_determination_present": False
                    }
                h4a_to_d = False
            else:
                committed_file_info(ROOT, holdout_path)
                holdout = read_json(holdout_path)
                holdout_checks, recomputed_holdout_pass = recompute_holdout(
                    config, cell, holdout, selected, lock_evidence
                )
                h4a_to_d = bool(
                    calibration["calibration"]["h4a_certified_set_nonempty"]
                    and holdout["cell_valid"]
                    and recomputed_holdout_pass
                )
        calibration_valid = all(
            value
            for key, value in calibration_checks.items()
            if key != "selected_policy"
        )
        cell_valid = calibration_valid and all(holdout_checks.values())
        all_valid &= cell_valid
        all_h4a_to_d &= h4a_to_d
        cells[cell["cell_id"]] = {
            "calibration_checks": calibration_checks,
            "holdout_checks": holdout_checks,
            "h4a_to_d_pass": h4a_to_d,
            "valid": cell_valid,
        }

    h4e = {
        "type": "operational_component_retention_rule",
        "cells_selecting_positive_tau": tau_positive,
        "cells_with_selected_policy": selected_policy_cells,
        "decision": h4e_decision(
            selected_policy_cells=selected_policy_cells,
            positive_tau_cells=tau_positive,
            total_cells=len(config["cells"]),
        ),
        "claim_boundary": (
            "This 2-of-3 vote does not establish a causal or statistically independent "
            "incremental benefit from confidence."
        ),
    }
    status = (
        "INVALID"
        if not all_valid
        else "PASS" if all_h4a_to_d else "VALID_NEGATIVE"
    )
    result = {
        "experiment_id": config["experiment_id"],
        "px_id": "PX-057",
        "stage": "H4_independent_adjudication",
        "status": status,
        "valid": all_valid,
        "all_cells_h4a_to_d_pass": all_h4a_to_d,
        "split_checks": split_checks,
        "shared_second_model_revision": shared_model_revision,
        "lock_evidence": lock_evidence,
        "cells": cells,
        "h4e": h4e,
        "phase_a_evidence": phase_a_evidence,
        "code_evidence": code_evidence,
        "claim_boundary": (
            "A PASS supports finite-benchmark, per-cell calibrated adaptation with "
            "a familywise 95% risk-control statement across the three frozen cells. "
            "It is not a universal deployment, cross-distribution, or zero-shot "
            "policy-transfer claim."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px057_h4_ltt_transfer_20260725.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/adaptive_stopping_overthinking/h4_20260725/final_adjudication.json"
        ),
    )
    args = parser.parse_args()
    result = adjudicate(repo_path(args.config))
    output_path = repo_path(args.output)
    if output_path.exists():
        raise FileExistsError(
            f"{output_path} already exists; final adjudications are immutable"
        )
    write_json(output_path, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
