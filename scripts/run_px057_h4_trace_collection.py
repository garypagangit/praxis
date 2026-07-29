#!/usr/bin/env python
"""Prepare frozen H4 splits and collect one PX-057 H4 trace cell."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h4_common import (
    committed_file_info,
    read_json,
    read_jsonl,
    sha256_bytes,
    sha256_file,
    verify_frozen_split,
    verify_phase_a_freeze,
    write_json,
    write_jsonl,
)
from scripts.run_px057_trace_collection import (
    generate_one,
    normalize_numeric,
    parse_gsm8k_gold,
)


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def download_verified(url: str, expected_sha256: str) -> bytes:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    content = response.content
    observed = sha256_bytes(content)
    if observed != expected_sha256:
        raise ValueError(f"source SHA-256 mismatch: {observed} != {expected_sha256}")
    return content


def hash_rank(question_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def select_without_overlap(
    rows: list[dict[str, Any]],
    *,
    calibration_n: int,
    holdout_n: int,
    calibration_seed: int,
    holdout_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if calibration_n + holdout_n > len(rows):
        raise ValueError("population is too small for the frozen split sizes")
    calibration_order = sorted(
        rows,
        key=lambda row: (
            hash_rank(str(row["question_id"]), calibration_seed),
            str(row["question_id"]),
        ),
    )
    calibration = calibration_order[:calibration_n]
    calibration_ids = {str(row["question_id"]) for row in calibration}
    remaining = [
        row for row in rows if str(row["question_id"]) not in calibration_ids
    ]
    holdout_order = sorted(
        remaining,
        key=lambda row: (
            hash_rank(str(row["question_id"]), holdout_seed),
            str(row["question_id"]),
        ),
    )
    holdout = holdout_order[:holdout_n]
    if calibration_ids & {str(row["question_id"]) for row in holdout}:
        raise AssertionError("calibration and holdout overlap")
    return calibration, holdout


def load_gsm8k_population(
    content: bytes, gate2_selected_path: Path
) -> tuple[list[dict[str, Any]], set[str]]:
    rows = [
        json.loads(line)
        for line in content.decode("utf-8").splitlines()
        if line.strip()
    ]
    gate2_rows = read_json(gate2_selected_path)
    gate2_ids = {str(row["question_id"]) for row in gate2_rows}
    population: list[dict[str, Any]] = []
    for source_index, row in enumerate(rows):
        question_id = f"gsm8k-test-{source_index}"
        if question_id in gate2_ids:
            continue
        population.append(
            {
                "question_id": question_id,
                "domain": "gsm8k",
                "answer_type": "numeric",
                "question": str(row["question"]),
                "gold_answer": parse_gsm8k_gold(str(row["answer"])),
                "source_index": source_index,
            }
        )
    return population, gate2_ids


def load_arc_population(content: bytes) -> list[dict[str, Any]]:
    import pandas as pd

    frame = pd.read_parquet(io.BytesIO(content))
    rows: list[dict[str, Any]] = []
    for source_index, record in frame.iterrows():
        choices = record["choices"]
        labels = [str(value) for value in list(choices["label"])]
        texts = [str(value) for value in list(choices["text"])]
        rows.append(
            {
                "question_id": f"arc-challenge-test-{record['id']}",
                "domain": "arc_challenge",
                "answer_type": "choice",
                "question": str(record["question"]),
                "choice_labels": labels,
                "choices": [
                    {"label": label, "text": text}
                    for label, text in zip(labels, texts)
                ],
                "gold_answer": str(record["answerKey"]),
                "source_index": int(source_index),
                "source_id": str(record["id"]),
            }
        )
    return rows


def prepare_splits(config: dict[str, Any], *, overwrite: bool = False) -> dict[str, Any]:
    split_config = config["split_design"]
    output_dir = repo_path(split_config["manifest_dir"])
    freeze_path = output_dir / "split_freeze.json"
    if freeze_path.exists() and not overwrite:
        raise FileExistsError(
            f"{freeze_path} already exists; pass --overwrite only before data collection"
        )
    if overwrite:
        evidence_paths = [
            repo_path(value)
            for cell in config["cells"]
            for value in (
                *cell["output_dirs"].values(),
                cell["ltt_determination"],
                cell["ltt_lock_manifest"],
                cell["holdout_determination"],
            )
        ]
        evidence_paths.extend(
            [
                repo_path(config["phase_a"]["runtime_manifest"]),
                repo_path(config["phase_a"]["freeze_determination"]),
            ]
        )
        populated = [
            path
            for path in evidence_paths
            if path.is_file() or (path.is_dir() and any(path.iterdir()))
        ]
        if populated:
            raise ValueError(
                "split overwrite is forbidden after H4 evidence exists: "
                + ", ".join(str(path) for path in populated)
            )
    output_dir.mkdir(parents=True, exist_ok=True)

    gsm_config = config["datasets"]["gsm8k"]
    gsm_content = download_verified(
        gsm_config["source_url"], gsm_config["source_sha256"]
    )
    gsm_population, gate2_ids = load_gsm8k_population(
        gsm_content, repo_path(gsm_config["gate2_selected_rows"])
    )
    if len(gsm_population) != int(gsm_config["eligible_population_size"]):
        raise ValueError("unexpected eligible GSM8K population size")

    arc_config = config["datasets"]["arc_challenge"]
    arc_content = download_verified(
        arc_config["source_url"], arc_config["source_sha256"]
    )
    arc_population = load_arc_population(arc_content)
    if len(arc_population) != int(arc_config["eligible_population_size"]):
        raise ValueError("unexpected ARC-Challenge population size")

    kwargs = {
        "calibration_n": int(split_config["calibration_n"]),
        "holdout_n": int(split_config["holdout_n"]),
        "calibration_seed": int(split_config["calibration_seed"]),
        "holdout_seed": int(split_config["holdout_seed"]),
    }
    gsm_calibration, gsm_holdout = select_without_overlap(gsm_population, **kwargs)
    arc_calibration, arc_holdout = select_without_overlap(arc_population, **kwargs)

    files = {
        "gsm8k_calibration": output_dir / "gsm8k_calibration.jsonl",
        "gsm8k_holdout": output_dir / "gsm8k_holdout.jsonl",
        "arc_challenge_calibration": output_dir / "arc_challenge_calibration.jsonl",
        "arc_challenge_holdout": output_dir / "arc_challenge_holdout.jsonl",
    }
    rows_by_name = {
        "gsm8k_calibration": gsm_calibration,
        "gsm8k_holdout": gsm_holdout,
        "arc_challenge_calibration": arc_calibration,
        "arc_challenge_holdout": arc_holdout,
    }
    for name, path in files.items():
        write_jsonl(path, rows_by_name[name])

    freeze = {
        "px_id": "PX-057",
        "stage": "H4_predata_split_freeze",
        "selection_algorithm": (
            "SHA256('<seed>:<question_id>') ascending; calibration selected first; "
            "holdout selected from the remaining population"
        ),
        "calibration_seed": int(split_config["calibration_seed"]),
        "holdout_seed": int(split_config["holdout_seed"]),
        "calibration_n": int(split_config["calibration_n"]),
        "holdout_n": int(split_config["holdout_n"]),
        "gsm8k": {
            "source_url": gsm_config["source_url"],
            "repository_revision": gsm_config["repository_revision"],
            "source_sha256": sha256_bytes(gsm_content),
            "source_rows": len(gsm_population) + len(gate2_ids),
            "excluded_gate2_ids": len(gate2_ids),
            "gate2_selected_rows": {
                "path": repo_path(gsm_config["gate2_selected_rows"])
                .relative_to(ROOT)
                .as_posix(),
                "sha256": committed_file_info(
                    ROOT, repo_path(gsm_config["gate2_selected_rows"])
                )["sha256"],
            },
            "eligible_population_size": len(gsm_population),
        },
        "arc_challenge": {
            "source_url": arc_config["source_url"],
            "dataset_revision": arc_config["dataset_revision"],
            "source_sha256": sha256_bytes(arc_content),
            "eligible_population_size": len(arc_population),
            "reuse_rule": (
                "The same frozen ARC calibration and holdout IDs are used in cells 2 "
                "and 3 to support a paired cross-model comparison."
            ),
        },
        "files": {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "rows": len(rows_by_name[name]),
                "sha256": sha256_file(path),
            }
            for name, path in files.items()
        },
    }
    write_json(freeze_path, freeze)
    freeze["split_freeze_path"] = freeze_path.relative_to(ROOT).as_posix()
    freeze["split_freeze_sha256"] = sha256_file(freeze_path)
    return freeze


def load_prompt_templates(
    config: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    path = repo_path(config["generation"]["prompt_template_path"])
    committed = committed_file_info(ROOT, path)
    observed_sha256 = sha256_file(path)
    expected_sha256 = str(config["generation"]["prompt_template_sha256"])
    if observed_sha256 != expected_sha256:
        raise ValueError(
            f"prompt template SHA-256 mismatch: {observed_sha256} != "
            f"{expected_sha256}"
        )
    templates = read_json(path)
    if (
        templates["prompt_template_id"]
        != config["generation"]["prompt_template_id"]
    ):
        raise ValueError("prompt template ID mismatch")
    return templates, committed


def build_prompt(
    row: dict[str, Any],
    previous: str | None,
    round_index: int,
    templates: dict[str, str] | None = None,
) -> str:
    if templates is None:
        templates = read_json(
            ROOT / "configs/px057_h4_prompt_templates_20260725.json"
        )
    if row["answer_type"] == "numeric":
        answer_instruction = templates["numeric_answer_instruction"]
        problem = str(row["question"])
    elif row["answer_type"] == "choice":
        answer_instruction = templates["choice_answer_instruction"]
        options = "\n".join(
            templates["choice_line_template"].format(
                label=choice["label"], text=choice["text"]
            )
            for choice in row["choices"]
        )
        problem = f"{row['question']}\n\nChoices:\n{options}"
    else:
        raise ValueError(f"unsupported answer_type: {row['answer_type']}")
    if previous is None:
        return templates["initial_template"].format(
            answer_instruction=answer_instruction,
            problem=problem,
        )
    return templates["reconsideration_template"].format(
        answer_instruction=answer_instruction,
        problem=problem,
        previous=previous,
        round_index=round_index,
    )


def extract_choice_answer(text: str, allowed_labels: list[str]) -> str:
    import re

    labels = [str(label).strip().upper() for label in allowed_labels]
    markers = list(
        re.finditer(r"final\s+answer\s*(?:is|:|=)?", text, flags=re.I)
    )
    if not markers:
        return ""
    suffix = text[markers[-1].end() :]
    match = re.match(r"\s*\(?([A-Za-z0-9]+)\)?", suffix)
    if not match:
        return ""
    candidate = match.group(1).upper()
    return candidate if candidate in labels else ""


def extract_numeric_answer(text: str) -> str:
    import re

    markers = list(
        re.finditer(r"final\s+answer\s*(?:is|:|=)?", text, flags=re.I)
    )
    if not markers:
        return ""
    suffix = text[markers[-1].end() :]
    match = re.match(
        r"\s*([-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)",
        suffix,
    )
    return "" if not match else normalize_numeric(match.group(1))


def load_backend(model_config: dict[str, Any]) -> tuple[Any, Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_id = str(model_config["model_id"])
    revision = str(model_config["revision"])
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        revision=revision,
        local_files_only=bool(model_config.get("local_files_only", False)),
        trust_remote_code=False,
    )
    kwargs: dict[str, Any] = {
        "revision": revision,
        "local_files_only": bool(model_config.get("local_files_only", False)),
        "trust_remote_code": False,
    }
    if model_config.get("device_map"):
        kwargs["device_map"] = model_config["device_map"]
        kwargs["torch_dtype"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    model.eval()
    return torch, tokenizer, model


def runtime_metadata(torch: Any, tokenizer: Any, model: Any) -> dict[str, Any]:
    import transformers

    cuda_available = bool(torch.cuda.is_available())
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": str(torch.__version__),
        "transformers": str(transformers.__version__),
        "cuda_available": cuda_available,
        "cuda_runtime": str(torch.version.cuda),
        "cudnn": (
            None
            if not cuda_available
            else str(torch.backends.cudnn.version())
        ),
        "cuda_devices": (
            []
            if not cuda_available
            else [
                torch.cuda.get_device_name(index)
                for index in range(torch.cuda.device_count())
            ]
        ),
        "tokenizer_class": tokenizer.__class__.__name__,
        "model_class": model.__class__.__name__,
        "model_config_commit": getattr(model.config, "_commit_hash", None),
        "model_dtype": str(next(model.parameters()).dtype),
        "chat_template_sha256": hashlib.sha256(
            (tokenizer.chat_template or "").encode("utf-8")
        ).hexdigest(),
    }


def verify_holdout_locks(config: dict[str, Any]) -> list[dict[str, Any]]:
    from scripts.run_px057_h4_holdout_gate import verify_all_locks

    lock_evidence = verify_all_locks(config)
    verified = []
    for cell in config["cells"]:
        path = repo_path(cell["ltt_lock_manifest"])
        verified.append(
            {
                "lock": read_json(path),
                "verification": lock_evidence[cell["cell_id"]],
            }
        )
    return verified


def collect_cell(
    config: dict[str, Any],
    *,
    cell_id: str,
    split_name: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    if config["protocol_status"] != "PRE_DATA_FROZEN":
        raise ValueError("scientific collection requires protocol_status=PRE_DATA_FROZEN")
    if split_name not in {"calibration", "holdout"}:
        raise ValueError("split must be calibration or holdout")
    cell = next((item for item in config["cells"] if item["cell_id"] == cell_id), None)
    if cell is None:
        raise ValueError(f"unknown cell_id: {cell_id}")

    config_commit = committed_file_info(ROOT, repo_path(config["_config_path"]))
    phase_a_evidence = verify_phase_a_freeze(
        ROOT, repo_path(config["_config_path"]), config
    )
    code_evidence = {
        "collector": committed_file_info(ROOT, Path(__file__)),
        "common": committed_file_info(ROOT, ROOT / "scripts/px057_h4_common.py"),
        "generation_backend": committed_file_info(
            ROOT, ROOT / "scripts/run_px057_trace_collection.py"
        ),
    }
    split_path = repo_path(cell[f"{split_name}_manifest"])
    split_evidence = verify_frozen_split(
        ROOT,
        repo_path(config["split_design"]["freeze_manifest"]),
        split_path,
    )
    lock_evidence = verify_holdout_locks(config) if split_name == "holdout" else []
    if split_name == "holdout":
        target_lock = next(
            item["lock"]
            for item in lock_evidence
            if item["lock"]["cell_id"] == cell_id
        )
        if target_lock["selected_policy"] is None:
            raise ValueError(
                f"{cell_id}: H4a produced no policy; holdout generation is forbidden"
            )

    rows = read_jsonl(split_path)
    expected_n = int(config["split_design"][f"{split_name}_n"])
    if len(rows) != expected_n:
        raise ValueError(f"{split_path}: expected {expected_n} rows")
    output_dir = repo_path(cell["output_dirs"][split_name])
    if overwrite:
        raise ValueError(
            "H4 trace outputs are immutable; use a new experiment ID for a rerun"
        )
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"{output_dir} is not empty")
    output_dir.mkdir(parents=True, exist_ok=True)

    model_config = config["models"][cell["model_key"]]
    prompt_templates, prompt_commit = load_prompt_templates(config)
    torch, tokenizer, model = load_backend(model_config)
    runtime = runtime_metadata(torch, tokenizer, model)
    frozen_runtime = read_json(repo_path(config["phase_a"]["runtime_manifest"]))
    frozen_model = frozen_runtime["model_smokes"][cell["model_key"]]
    runtime_identity = {
        "python": frozen_runtime["python"],
        "platform": frozen_runtime["platform"],
        "torch": frozen_runtime["torch"],
        "transformers": frozen_runtime["transformers"],
        "cuda_runtime": frozen_runtime["cuda_runtime"],
        "cudnn": frozen_runtime["cudnn"],
        "cuda_devices": frozen_runtime["cuda_devices"],
        "model_config_commit": frozen_model["resolved_config_commit"],
        "model_dtype": frozen_model["model_dtype"],
        "chat_template_sha256": frozen_model["chat_template_sha256"],
        "model_class": frozen_model["model_class"],
        "tokenizer_class": frozen_model["tokenizer_class"],
    }
    if any(runtime[key] != value for key, value in runtime_identity.items()):
        raise ValueError("loaded model/tokenizer differs from the Phase A capture")
    seed = int(config["generation"]["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    rounds = int(config["generation"]["rounds"])
    max_new_tokens = int(config["generation"]["max_new_tokens"])
    trace_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    for row in rows:
        steps: list[dict[str, Any]] = []
        previous: str | None = None
        cumulative_tokens = 0
        for round_index in range(1, rounds + 1):
            prompt = build_prompt(
                row, previous, round_index, templates=prompt_templates
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            started = time.perf_counter()
            response, confidence, generated_tokens = generate_one(
                torch,
                tokenizer,
                model,
                prompt,
                max_new_tokens,
                "causal",
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            if row["answer_type"] == "numeric":
                answer = extract_numeric_answer(response)
            else:
                answer = extract_choice_answer(response, row["choice_labels"])
            cumulative_tokens += generated_tokens
            steps.append(
                {
                    "step": round_index,
                    "answer": answer,
                    "confidence": confidence,
                    "tokens": cumulative_tokens,
                    "wall_seconds": elapsed,
                    "gpu_seconds": elapsed if torch.cuda.is_available() else None,
                }
            )
            raw_rows.append(
                {
                    "question_id": row["question_id"],
                    "round": round_index,
                    "prompt": prompt,
                    "response": response,
                    "extracted_answer": answer,
                    "confidence": confidence,
                    "generated_tokens": generated_tokens,
                    "wall_seconds": elapsed,
                    "gpu_seconds": elapsed if torch.cuda.is_available() else None,
                }
            )
            previous = response
        trace_rows.append(
            {
                "question_id": row["question_id"],
                "domain": row["domain"],
                "steps": steps,
            }
        )

    selected_path = output_dir / "selected_rows.jsonl"
    trace_path = output_dir / "reasoning_traces.jsonl"
    raw_path = output_dir / "raw_generations.jsonl"
    write_jsonl(selected_path, rows)
    write_jsonl(trace_path, trace_rows)
    write_jsonl(raw_path, raw_rows)
    summary = {
        "experiment_id": config["experiment_id"],
        "px_id": "PX-057",
        "stage": "H4_trace_collection",
        "cell_id": cell_id,
        "split": split_name,
        "model": model_config,
        "runtime": runtime,
        "config_commit": config_commit,
        "phase_a_evidence": phase_a_evidence,
        "code_evidence": code_evidence,
        "dataset_key": cell["dataset_key"],
        "prompt_template_id": config["generation"]["prompt_template_id"],
        "prompt_template": {
            "path": config["generation"]["prompt_template_path"],
            "sha256": config["generation"]["prompt_template_sha256"],
            "commit": prompt_commit,
        },
        "split_manifest": {
            "path": split_path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(split_path),
            "rows": len(rows),
        },
        "split_freeze_evidence": split_evidence,
        "rounds": rounds,
        "expected_generation_rows": len(rows) * rounds,
        "observed_generation_rows": len(raw_rows),
        "confidence_definition": (
            "exp(mean normalized transition log probability) over generated tokens, "
            "clipped to exp([-20,0])"
        ),
        "holdout_lock_evidence": lock_evidence,
        "files": {
            path.name: sha256_file(path)
            for path in (selected_path, trace_path, raw_path)
        },
    }
    write_json(output_dir / "collection_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px057_h4_ltt_transfer_20260725.json"),
    )
    parser.add_argument("--prepare-splits", action="store_true")
    parser.add_argument("--cell")
    parser.add_argument("--split", choices=("calibration", "holdout"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config_path = repo_path(args.config)
    config = read_json(config_path)
    config["_config_path"] = config_path.relative_to(ROOT).as_posix()
    if args.prepare_splits:
        result = prepare_splits(config, overwrite=args.overwrite)
    else:
        if not args.cell or not args.split:
            parser.error("--cell and --split are required for trace collection")
        result = collect_cell(
            config,
            cell_id=args.cell,
            split_name=args.split,
            overwrite=args.overwrite,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
