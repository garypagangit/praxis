#!/usr/bin/env python
"""Export a blinded PX-057 H4 audit packet and join committed judgments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NO_ANSWER_SENTINEL = "<NO_ANSWER>"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import (
    committed_file_info,
    load_scored_traces,
    normalize_choice_answer,
    normalize_numeric_answer,
    read_json,
    read_jsonl,
    select_audit_question_ids,
    sha256_file,
    stable_collection_evidence,
    verify_collection_bundle,
    write_json,
)
from scripts.run_px057_h4_holdout_gate import get_cell, verify_all_locks


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def audit_keys(
    traces: list[Any],
) -> tuple[list[str], list[tuple[str, int]]]:
    question_ids = select_audit_question_ids(
        traces, seed=5703, sample_size=50
    )
    keys = [
        (question_id, round_index)
        for question_id in question_ids
        for round_index in range(1, 9)
    ]
    return question_ids, keys


def export_packet(
    config_path: Path, *, cell_id: str, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"{output_path} already exists")
    config = read_json(config_path)
    cell = get_cell(config, cell_id)
    expected_output = repo_path(cell["manual_audit_blinded"])
    if output_path.resolve() != expected_output.resolve():
        raise ValueError("blinded packet path differs from the frozen config")
    verify_all_locks(config, config_path)
    split_path = repo_path(cell["holdout_manifest"])
    trace_path = (
        repo_path(cell["output_dirs"]["holdout"]) / "reasoning_traces.jsonl"
    )
    raw_path = repo_path(cell["output_dirs"]["holdout"]) / "raw_generations.jsonl"
    committed_file_info(ROOT, split_path)
    bundle = verify_collection_bundle(
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
    for metadata in bundle["files"].values():
        committed_file_info(ROOT, repo_path(metadata["path"]))
    source_evidence = stable_collection_evidence(ROOT, bundle, split_path)
    traces, split_rows = load_scored_traces(
        trace_path,
        split_path,
        expected_rounds=int(config["generation"]["rounds"]),
    )
    question_ids, keys = audit_keys(traces)
    split_by_id = {str(row["question_id"]): row for row in split_rows}
    raw_by_key = {
        (str(row["question_id"]), int(row["round"])): row
        for row in read_jsonl(raw_path)
    }
    items = []
    for question_id, round_index in keys:
        split_row = split_by_id[question_id]
        raw = raw_by_key[(question_id, round_index)]
        items.append(
            {
                "question_id": question_id,
                "round": round_index,
                "question": split_row["question"],
                "choices": split_row.get("choices"),
                "raw_response": raw["response"],
                "primary_answer": "",
                "primary_ambiguous": False,
                "second_adjudicator_answer": None,
            }
        )
    packet = {
        "experiment_id": config["experiment_id"],
        "stage": "H4_blinded_manual_extraction_packet",
        "cell_id": cell_id,
        "seed": 5703,
        "trace_units": 50,
        "round_units": 400,
        "question_ids": question_ids,
        "auditor_blinded_to_gold": True,
        "auditor_blinded_to_automated_answer": True,
        "auditor_blinded_to_policy_and_gate": True,
        "source_evidence": source_evidence,
        "instructions": (
            "Fill primary_answer for every row. Mark primary_ambiguous only "
            "when needed; a second blinded adjudicator must then fill "
            "second_adjudicator_answer. Use <NO_ANSWER> when the response "
            "expresses no extractable final answer. Ordinary equivalent numeric "
            "formats are accepted and normalized only during the later join. "
            "Do not add gold, automated extraction, policy, certificate, or "
            "gate information."
        ),
        "items": items,
    }
    write_json(output_path, packet)
    return packet


def join_judgments(
    config_path: Path, *, cell_id: str, blinded_path: Path
) -> dict[str, Any]:
    config = read_json(config_path)
    cell = get_cell(config, cell_id)
    expected_blinded = repo_path(cell["manual_audit_blinded"])
    if blinded_path.resolve() != expected_blinded.resolve():
        raise ValueError("blinded judgment path differs from the frozen config")
    blinded_commit = committed_file_info(ROOT, blinded_path)
    output_path = repo_path(cell["manual_audit"])
    if output_path.exists():
        raise FileExistsError(f"{output_path} already exists")
    payload = read_json(blinded_path)
    required_metadata = {
        "cell_id": cell_id,
        "seed": 5703,
        "trace_units": 50,
        "round_units": 400,
        "auditor_blinded_to_gold": True,
        "auditor_blinded_to_automated_answer": True,
        "auditor_blinded_to_policy_and_gate": True,
    }
    if any(payload.get(key) != value for key, value in required_metadata.items()):
        raise ValueError("blinded judgment metadata mismatch")
    split_path = repo_path(cell["holdout_manifest"])
    trace_path = (
        repo_path(cell["output_dirs"]["holdout"]) / "reasoning_traces.jsonl"
    )
    raw_path = repo_path(cell["output_dirs"]["holdout"]) / "raw_generations.jsonl"
    bundle = verify_collection_bundle(
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
    source_evidence = stable_collection_evidence(ROOT, bundle, split_path)
    if payload.get("source_evidence") != source_evidence:
        raise ValueError("blinded judgments are not bound to the current holdout bundle")
    traces, split_rows = load_scored_traces(
        trace_path,
        split_path,
        expected_rounds=int(config["generation"]["rounds"]),
    )
    question_ids, expected_keys = audit_keys(traces)
    items = list(payload.get("items", []))
    observed_keys = [
        (str(item.get("question_id")), int(item.get("round", -1)))
        for item in items
    ]
    if (
        payload.get("question_ids") != question_ids
        or len(items) != 400
        or observed_keys != expected_keys
    ):
        raise ValueError("blinded judgment units differ from the frozen audit sample")
    trace_answers = {
        (trace.question_id, step.step): step.answer
        for trace in traces
        if trace.question_id in set(question_ids)
        for step in trace.steps
    }
    split_by_id = {str(row["question_id"]): row for row in split_rows}
    raw_by_key = {
        (str(row["question_id"]), int(row["round"])): row
        for row in read_jsonl(raw_path)
    }
    for item, key in zip(items, expected_keys):
        split_row = split_by_id[key[0]]
        raw = raw_by_key[key]
        if (
            item.get("question") != split_row["question"]
            or item.get("choices") != split_row.get("choices")
            or item.get("raw_response") != raw["response"]
        ):
            raise ValueError(f"{key}: blinded packet differs from holdout source")
    judgments = []
    disagreements = 0
    for item, key in zip(items, expected_keys):
        primary_entry = str(item.get("primary_answer", "")).strip()
        if not primary_entry:
            raise ValueError(f"{key}: primary_answer is missing")
        primary = (
            ""
            if primary_entry == NO_ANSWER_SENTINEL
            else primary_entry
        )
        ambiguous = bool(item.get("primary_ambiguous", False))
        second_entry = item.get("second_adjudicator_answer")
        if ambiguous and not str(second_entry or "").strip():
            raise ValueError(f"{key}: ambiguous answer lacks second adjudication")
        if not ambiguous and second_entry not in {None, ""}:
            raise ValueError(f"{key}: unexpected second adjudication")
        second = (
            ""
            if str(second_entry or "").strip() == NO_ANSWER_SENTINEL
            else str(second_entry or "").strip()
        )
        auditor_answer_raw = second if ambiguous else primary
        auditor_answer_entry = (
            str(second_entry).strip() if ambiguous else primary_entry
        )
        split_row = split_by_id[key[0]]
        if split_row["answer_type"] == "numeric":
            auditor_answer = normalize_numeric_answer(auditor_answer_raw)
        else:
            auditor_answer = normalize_choice_answer(
                auditor_answer_raw, split_row["choice_labels"]
            )
        automated_answer = str(trace_answers[key])
        disagreement = (
            automated_answer.strip().upper() != auditor_answer.strip().upper()
        )
        disagreements += int(disagreement)
        judgments.append(
            {
                "question_id": key[0],
                "round": key[1],
                "primary_answer": primary_entry,
                "primary_ambiguous": ambiguous,
                "second_adjudicator_answer": second_entry,
                "auditor_answer_entry": auditor_answer_entry,
                "auditor_answer_raw": auditor_answer_raw,
                "auditor_answer": auditor_answer,
                "automated_answer": automated_answer,
                "disagreement": disagreement,
            }
        )
    result = {
        "experiment_id": config["experiment_id"],
        "stage": "H4_manual_extraction_audit_join",
        "cell_id": cell_id,
        "trace_units": 50,
        "round_units": 400,
        "seed": 5703,
        "auditor_blinded_to_gold": True,
        "auditor_blinded_to_automated_answer": True,
        "auditor_blinded_to_policy_and_gate": True,
        "question_ids": question_ids,
        "round_disagreements": disagreements,
        "blinded_judgments_path": blinded_path.relative_to(ROOT).as_posix(),
        "blinded_judgments_sha256": sha256_file(blinded_path),
        "blinded_judgments_commit": blinded_commit,
        "source_evidence": source_evidence,
        "judgments": judgments,
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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--export-packet", type=Path)
    mode.add_argument("--join", type=Path)
    args = parser.parse_args()
    config_path = repo_path(args.config)
    if args.export_packet is not None:
        result = export_packet(
            config_path,
            cell_id=args.cell,
            output_path=repo_path(args.export_packet),
        )
    else:
        result = join_judgments(
            config_path,
            cell_id=args.cell,
            blinded_path=repo_path(args.join),
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
