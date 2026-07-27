#!/usr/bin/env python
"""Collect the outcome-exposed PX-057 H5 development prompt pilot.

This runner is deliberately separate from the future H5 confirmatory stack.  It
uses only H4 calibration questions, which must be excluded from every H5 split.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.px057_h5_mechanism import extract_last_valid_answer
from scripts.px057_h5_development_contract import (
    require_c1,
    validate_frozen_development_config,
)
from scripts.run_px057_h4_trace_collection import load_backend, runtime_metadata


DEFAULT_CONFIG = ROOT / "configs/px057_h5_development_pilot_20260727.json"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(canonical_bytes(row).decode("utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value))


def hash_rank(question_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode("utf-8")).hexdigest()


def generate_chat_one(
    torch: Any,
    tokenizer: Any,
    model: Any,
    prompt: str,
    max_new_tokens: int,
) -> tuple[str, float, int, int, str]:
    """Greedy generation through the model's pinned native chat template."""

    if not tokenizer.chat_template:
        raise ValueError("native chat serialization requires a tokenizer chat_template")
    input_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    )
    attention_mask = torch.ones_like(input_ids)
    if hasattr(model, "device"):
        input_ids = input_ids.to(model.device)
        attention_mask = attention_mask.to(model.device)
    from transformers import StoppingCriteria, StoppingCriteriaList

    stop_ids = tokenizer.encode("<END>", add_special_tokens=False)
    if not stop_ids:
        raise ValueError("tokenizer produced no IDs for the <END> terminator")

    class StopOnEnd(StoppingCriteria):
        def __call__(self, candidate_ids: Any, scores: Any, **kwargs: Any) -> bool:
            del scores, kwargs
            if candidate_ids.shape[1] < len(stop_ids):
                return False
            suffix = candidate_ids[0, -len(stop_ids) :].tolist()
            return suffix == stop_ids

    terminators = [tokenizer.eos_token_id]
    if "<|eot_id|>" in tokenizer.get_vocab():
        eot_id = tokenizer.convert_tokens_to_ids("<|eot_id|>")
        if isinstance(eot_id, int) and eot_id >= 0 and eot_id not in terminators:
            terminators.append(eot_id)
    terminators = [token_id for token_id in terminators if token_id is not None]
    if not terminators:
        raise ValueError("tokenizer supplies no EOS/EOT terminator")

    with torch.inference_mode():
        output = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            return_dict_in_generate=True,
            output_scores=True,
            stopping_criteria=StoppingCriteriaList([StopOnEnd()]),
            eos_token_id=terminators,
        )
    generated = output.sequences[0, input_ids.shape[1] :]
    response = tokenizer.decode(generated, skip_special_tokens=True)
    transition = model.compute_transition_scores(
        output.sequences, output.scores, normalize_logits=True
    )[0]
    finite = transition[torch.isfinite(transition)]
    mean_logprob = float(finite.mean().item()) if len(finite) else -100.0
    confidence = float(math.exp(max(-20.0, min(0.0, mean_logprob))))
    generated_tokens = int(len(generated))
    ended_with_literal_end = bool(
        generated_tokens >= len(stop_ids)
        and generated[-len(stop_ids) :].tolist() == stop_ids
    )
    last_generated_id = None if generated_tokens == 0 else int(generated[-1])
    if ended_with_literal_end and generated_tokens < max_new_tokens:
        termination_reason = "literal_end_marker"
    elif ended_with_literal_end:
        termination_reason = "literal_end_marker_at_token_cap"
    elif last_generated_id in terminators:
        termination_reason = "native_eos_or_eot"
    elif generated_tokens >= max_new_tokens:
        termination_reason = "token_cap"
    else:
        termination_reason = "unexpected_no_registered_terminator"
    return (
        response,
        confidence,
        generated_tokens,
        int(input_ids.shape[1]),
        termination_reason,
    )


def validate_bounded_response(
    response: str,
    *,
    extraction: Any,
    answer_type: str,
    allowed_labels: tuple[str, ...] | list[str] = (),
    termination_reason: str,
) -> dict[str, Any]:
    """Validate the exact, case-sensitive three-line response contract."""

    stripped = response.strip(" \t\r\n")
    schema_lines = stripped.splitlines()
    exact_line_count = len(schema_lines) == 3
    check_line = schema_lines[0] if exact_line_count else ""
    answer_line = schema_lines[1] if exact_line_count else ""
    end_line = schema_lines[2] if exact_line_count else ""
    check_prefix = check_line.startswith("Check: ")
    check_body = check_line[len("Check: ") :] if check_prefix else ""
    check_word_count = len(check_body.split())
    bounded_check = bool(check_body) and 1 <= check_word_count <= 40

    if answer_type == "numeric":
        answer_match = re.fullmatch(
            r"Final answer: ([-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)",
            answer_line,
        )
        exact_answer_line = answer_match is not None
    elif answer_type == "choice":
        answer_match = re.fullmatch(r"Final answer: ([A-Za-z0-9]+)", answer_line)
        allowed = {str(label).strip().upper() for label in allowed_labels}
        exact_answer_line = bool(
            answer_match and answer_match.group(1).upper() in allowed
        )
    else:
        raise ValueError(f"unsupported answer_type: {answer_type}")

    exact_end_line = end_line == "<END>"
    exact_three_lines = bool(
        exact_line_count
        and check_prefix
        and bounded_check
        and exact_answer_line
        and exact_end_line
    )
    end_matches = list(re.finditer(re.escape("<END>"), response))
    marker_count = extraction.marker_count
    end_after_answer = bool(
        extraction.selected_marker_ordinal is not None
        and end_matches
        and end_matches[-1].start()
        > extraction.candidates[extraction.selected_marker_ordinal - 1].marker_end
    )
    nothing_after_end = bool(
        end_matches and not response[end_matches[-1].end() :].strip()
    )
    valid = bool(
        extraction.valid
        and not extraction.token_cap_reached
        and termination_reason == "literal_end_marker"
        and check_prefix
        and bounded_check
        and exact_three_lines
        and marker_count == 1
        and len(end_matches) == 1
        and end_after_answer
        and nothing_after_end
        and stripped
    )
    return {
        "valid": valid,
        "check_prefix": check_prefix,
        "completed_before_token_cap": not extraction.token_cap_reached,
        "termination_reason": termination_reason,
        "terminated_by_exact_end_marker": termination_reason == "literal_end_marker",
        "exact_line_count": exact_line_count,
        "exact_three_lines": exact_three_lines,
        "exact_answer_line": exact_answer_line,
        "exact_end_line": exact_end_line,
        "check_word_count": check_word_count,
        "bounded_check": bounded_check,
        "final_answer_marker_count": marker_count,
        "end_marker_count": len(end_matches),
        "end_after_answer": end_after_answer,
        "nothing_after_end": nothing_after_end,
    }


def select_exposed_rows(
    rows: list[dict[str, Any]], *, pilot_n: int, seed: int
) -> list[dict[str, Any]]:
    if pilot_n <= 0 or pilot_n > len(rows):
        raise ValueError("pilot_n must be within the outcome-exposed source manifest")
    ranked = sorted(
        rows,
        key=lambda row: (
            hash_rank(str(row["question_id"]), seed),
            str(row["question_id"]),
        ),
    )
    selected = ranked[:pilot_n]
    if len({str(row["question_id"]) for row in selected}) != pilot_n:
        raise ValueError("selected development rows contain duplicate question IDs")
    return selected


def problem_text(row: dict[str, Any], prompts: dict[str, str]) -> tuple[str, str]:
    if row["answer_type"] == "numeric":
        return str(row["question"]), str(prompts["numeric_instruction"])
    if row["answer_type"] == "choice":
        choices = "\n".join(
            prompts["choice_line_template"].format(
                label=choice["label"], text=choice["text"]
            )
            for choice in row["choices"]
        )
        return (
            f"{row['question']}\n\nChoices:\n{choices}",
            str(prompts["choice_instruction"]),
        )
    raise ValueError(f"unsupported answer_type: {row['answer_type']}")


def build_prompt(
    row: dict[str, Any],
    *,
    previous_answer: str,
    round_index: int,
    prompts: dict[str, str],
) -> str:
    problem, instruction = problem_text(row, prompts)
    if round_index == 1:
        return prompts["initial_template"].format(
            answer_instruction=instruction,
            problem=problem,
        )
    return prompts["reconsideration_template"].format(
        answer_instruction=instruction,
        problem=problem,
        previous_answer=previous_answer or "NO VALID PRIOR ANSWER",
        round_index=round_index,
    )


def collect(config: dict[str, Any], *, cell_id: str) -> dict[str, Any]:
    validate_frozen_development_config(config)
    require_c1(cell_id)
    if config.get("status") != "DEVELOPMENT_ONLY_NOT_CONFIRMATORY":
        raise ValueError("development pilot status boundary is missing")
    cells = [cell for cell in config["cells"] if cell["cell_id"] == cell_id]
    if len(cells) != 1:
        raise ValueError(f"unknown or duplicate cell: {cell_id}")
    cell = cells[0]
    source_path = ROOT / cell["source_manifest"]
    all_rows = read_jsonl(source_path)
    generation = config["generation"]
    if generation.get("native_chat_template") is not True:
        raise ValueError("development repair requires native_chat_template=true")
    rows = select_exposed_rows(
        all_rows,
        pilot_n=int(generation["pilot_n"]),
        seed=int(generation["sample_seed"]),
    )
    output_dir = ROOT / cell["output_dir"]
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"development pilot output is immutable: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    model_config = config["models"][cell["model_key"]]
    torch, tokenizer, model = load_backend(model_config)
    runtime = runtime_metadata(torch, tokenizer, model)
    seed = int(generation["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    trace_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    rounds = int(generation["rounds"])
    max_new_tokens = int(generation["max_new_tokens"])
    for item_index, row in enumerate(rows, start=1):
        steps: list[dict[str, Any]] = []
        previous_answer = ""
        cumulative_tokens = 0
        for round_index in range(1, rounds + 1):
            prompt = build_prompt(
                row,
                previous_answer=previous_answer,
                round_index=round_index,
                prompts=config["prompts"],
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            started = time.perf_counter()
            (
                response,
                confidence,
                generated_tokens,
                prompt_tokens,
                termination_reason,
            ) = generate_chat_one(
                torch,
                tokenizer,
                model,
                prompt,
                max_new_tokens,
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            allowed = row.get("choice_labels") if row["answer_type"] == "choice" else ()
            extraction = extract_last_valid_answer(
                response,
                answer_type=str(row["answer_type"]),
                allowed_labels=allowed,
                generated_tokens=generated_tokens,
                max_new_tokens=max_new_tokens,
            )
            schema = validate_bounded_response(
                response,
                extraction=extraction,
                answer_type=str(row["answer_type"]),
                allowed_labels=allowed,
                termination_reason=termination_reason,
            )
            answer = extraction.answer if schema["valid"] else ""
            previous_answer = answer
            cumulative_tokens += generated_tokens
            step = {
                "step": round_index,
                "answer": answer,
                "confidence": confidence,
                "tokens": cumulative_tokens,
                "generated_tokens": generated_tokens,
                "prompt_tokens": prompt_tokens,
                "termination_reason": termination_reason,
                "token_cap_reached": generated_tokens >= max_new_tokens,
                "marker_count": extraction.marker_count,
                "used_prior_valid_marker": extraction.used_prior_valid_marker,
                "repetition_detected": extraction.repetition_detected,
                "response_schema_valid": schema["valid"],
                "wall_seconds": elapsed,
                "gpu_seconds": elapsed if torch.cuda.is_available() else None,
            }
            steps.append(step)
            raw_rows.append(
                {
                    "question_id": row["question_id"],
                    "round": round_index,
                    "prompt": prompt,
                    "response": response,
                    "extracted_answer": answer,
                    "parsed_candidate": extraction.answer,
                    "response_schema": schema,
                    **{key: value for key, value in step.items() if key != "answer"},
                }
            )
        trace_rows.append(
            {
                "question_id": row["question_id"],
                "domain": row["domain"],
                "gold_answer": row["gold_answer"],
                "answer_type": row["answer_type"],
                "steps": steps,
            }
        )
        if item_index % 10 == 0:
            print(f"PX057 H5 dev {cell_id}: {item_index}/{len(rows)}", flush=True)

    selected_path = output_dir / "selected_rows.jsonl"
    traces_path = output_dir / "reasoning_traces.jsonl"
    raw_path = output_dir / "raw_generations.jsonl"
    write_jsonl(selected_path, rows)
    write_jsonl(traces_path, trace_rows)
    write_jsonl(raw_path, raw_rows)
    summary = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "attempt_id": config["attempt_id"],
        "protocol_id": config["protocol_id"],
        "frozen_cell_id": config["frozen_cell_id"],
        "policy_id": config["primary_development_policy"]["policy_id"],
        "stage": "H5_DEVELOPMENT_PILOT_COLLECTION",
        "status": "PASS",
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "cell_id": cell_id,
        "source_manifest": {
            "path": cell["source_manifest"],
            "sha256": sha256_file(source_path),
            "available_rows": len(all_rows),
            "outcome_exposed": True,
        },
        "selection": {
            "algorithm": "SHA256('<sample_seed>:<question_id>') ascending",
            "sample_seed": int(generation["sample_seed"]),
            "rows": len(rows),
            "selected_id_sha256": hashlib.sha256(
                canonical_bytes([row["question_id"] for row in rows])
            ).hexdigest(),
        },
        "model": model_config,
        "runtime": runtime,
        "generation": generation,
        "response_protocol": config["prompts"],
        "observed_generation_rows": len(raw_rows),
        "files": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in (selected_path, traces_path, raw_path)
        },
    }
    write_json(output_dir / "collection_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cell", required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    print(json.dumps(collect(config, cell_id=args.cell), indent=2))


if __name__ == "__main__":
    main()
