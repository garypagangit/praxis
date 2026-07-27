#!/usr/bin/env python
"""Single machine-readable contract for the PX-057 H5 C1 development r2 pilot."""

from __future__ import annotations

from typing import Any, Mapping


EXPERIMENT_ID = "px057-h5-development-pilot-bounded-chat-r2-20260727"
PROTOCOL_ID = "px057-h5-c1-development-native-chat-v1"
FROZEN_CELL_ID = "C1-H4DEV-NATIVECHAT-V1"
POLICY_ID = "m4-k2-valid-v1"
CELL_ID = "cell1_llama31_gsm8k"
ATTEMPT_ID = "r2"
JOB_NAME = "px057-h5-dev-c1-ccchat-n500-r2-20260727"
SOURCE_MANIFEST = "manifests/px057_h4_20260725/gsm8k_calibration.jsonl"
SOURCE_MANIFEST_SHA256 = (
    "a48ef2c73edc6eec80428358feee3f38e1c5182dac441ca39c339fb9b54f00ef"
)


EXPECTED_CONFIG: dict[str, Any] = {
    "experiment_id": EXPERIMENT_ID,
    "px_id": "PX-057",
    "attempt_id": ATTEMPT_ID,
    "protocol_revision": "2-exact-schema-c1-only-provenance",
    "protocol_id": PROTOCOL_ID,
    "frozen_cell_id": FROZEN_CELL_ID,
    "status": "DEVELOPMENT_ONLY_NOT_CONFIRMATORY",
    "claim_boundary": (
        "All questions were generated in H4 and are outcome-exposed. Results may "
        "select and fix an H5 mechanism, but may not be counted as H5 calibration, "
        "holdout, certification, or confirmatory evidence."
    ),
    "repository": {
        "url": "https://github.com/garypagangit/praxis.git",
        "branch": "agent/px057-h5-certified-transfer",
    },
    "aws": {
        "profile": "praxis-build",
        "region": "us-east-1",
        "role_arn": (
            "arn:aws:iam::272615233626:role/service-role/"
            "AmazonSageMaker-ExecutionRole-20260416T191047"
        ),
        "bucket": "praxis-garypagan-272615233626-us-east-1",
        "s3_prefix": (
            "experiments/px057-adaptive-stopping/"
            "h5-development-pilot-r2-20260727"
        ),
        "instance_type": "ml.g5.2xlarge",
        "volume_size_gb": 200,
        "max_runtime_seconds": 43200,
        "container_image": (
            "763104351884.dkr.ecr.us-east-1.amazonaws.com/"
            "pytorch-training@sha256:"
            "01d8dfbde8f6e47a20e5b1e4033e105976663f2641084921b8769ee6998ef807"
        ),
        "huggingface_secret_id": "praxis/huggingface/token",
    },
    "generation": {
        "rounds": 8,
        "max_new_tokens": 96,
        "seed": 5757,
        "pilot_n": 500,
        "sample_seed": 5758,
        "decoding": "greedy",
        "native_chat_template": True,
        "terminators": ["native_eos", "native_eot_if_present", "<END>"],
        "response_protocol": "bounded_check_then_answer_then_end",
        "previous_context": (
            "preceding_round_strict_valid_answer_else_NO_VALID_PRIOR_ANSWER"
        ),
    },
    "strict_response_schema": {
        "physical_lines_after_outer_whitespace_trim": 3,
        "line_1_prefix": "Check: ",
        "line_1_whitespace_delimited_words_min": 1,
        "line_1_whitespace_delimited_words_max": 40,
        "line_2_prefix": "Final answer: ",
        "line_2_numeric_full_match_required": True,
        "case_sensitive_literals": True,
        "exact_final_answer_marker_count": 1,
        "line_3_exact": "<END>",
        "completion_before_token_cap_required": True,
        "invalid_round_resets_context": True,
    },
    "primary_development_policy": {
        "policy_id": POLICY_ID,
        "min_step": 4,
        "patience": 2,
        "confidence_threshold": None,
        "fixed_long_answer": "strictly_valid_round_8_only_no_fallback",
    },
    "one_look_mechanism_selection_gate": {
        "early_stop_harms_max": 4,
        "mean_compute_saving_min": 0.25,
        "adaptive_minus_fixed_correct_min": -5,
        "strict_valid_round_rate_min": 0.95,
        "fixed_long_correct_min": 141,
        "all_mechanism_sentinels_selected_and_fixed_correct": True,
        "rule": (
            "Evaluate once after all 4,000 generations. No threshold or policy "
            "tuning from this pilot. Failure makes this mechanism H5 NO-GO; another "
            "repair requires a new development-pilot revision."
        ),
    },
    "mechanism_sentinels": [
        {"question_id": "gsm8k-test-1129", "gold_answer": "8"},
        {"question_id": "gsm8k-test-504", "gold_answer": "2"},
        {"question_id": "gsm8k-test-323", "gold_answer": "75"},
        {"question_id": "gsm8k-test-591", "gold_answer": "220"},
        {"question_id": "gsm8k-test-458", "gold_answer": "35"},
        {"question_id": "gsm8k-test-361", "gold_answer": "20"},
        {"question_id": "gsm8k-test-1249", "gold_answer": "56"},
    ],
    "repair_hypothesis": (
        "H4 called an instruction-tuned causal model with unframed bare text. Native "
        "chat serialization plus a bounded check/answer/end contract should prevent "
        "continuation loops, preserve short task-relevant reasoning, distinguish "
        "natural completion from truncation, and move the C1 safety/utility frontier."
    ),
    "prompts": {
        "numeric_instruction": (
            "Check: <one or two concise arithmetic sentences, at most 40 words>\n"
            "Final answer: <number>\n<END>"
        ),
        "choice_instruction": (
            "Check: <one or two concise sentences, at most 40 words>\n"
            "Final answer: <one listed label>\n<END>"
        ),
        "choice_line_template": "{label}. {text}",
        "initial_template": (
            "Solve the problem from scratch. Return exactly these lines and nothing "
            "else:\n{answer_instruction}\nDo not write \"Final answer\" anywhere "
            "else.\n\nProblem:\n{problem}"
        ),
        "reconsideration_template": (
            "Re-solve the problem from scratch. The prior answer below may be wrong; "
            "do not use it as a premise. Return exactly these lines and nothing "
            "else:\n{answer_instruction}\nDo not write \"Final answer\" anywhere "
            "else.\n\nProblem:\n{problem}\n\nUntrusted prior answer: "
            "{previous_answer}\nAudit round: {round_index}"
        ),
    },
    "models": {
        "llama31": {
            "model_id": "meta-llama/Llama-3.1-8B-Instruct",
            "revision": "0e9e39f249a16976918f6564b8830bc894c89659",
            "device_map": "auto",
            "local_files_only": False,
        }
    },
    "cells": [
        {
            "cell_id": CELL_ID,
            "frozen_cell_id": FROZEN_CELL_ID,
            "job_code": "c1",
            "model_key": "llama31",
            "source_manifest": SOURCE_MANIFEST,
            "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "output_dir": (
                "reports/adaptive_stopping_overthinking/"
                "h5_development_pilot_20260727/cell1_llama31_gsm8k"
            ),
        }
    ],
}


def _first_difference(expected: Any, observed: Any, path: str = "config") -> str | None:
    if type(expected) is not type(observed):
        return f"{path}: expected {type(expected).__name__}, found {type(observed).__name__}"
    if isinstance(expected, dict):
        expected_keys = set(expected)
        observed_keys = set(observed)
        if expected_keys != observed_keys:
            missing = sorted(expected_keys - observed_keys)
            extra = sorted(observed_keys - expected_keys)
            return f"{path}: key mismatch missing={missing} extra={extra}"
        for key in expected:
            difference = _first_difference(
                expected[key], observed[key], f"{path}.{key}"
            )
            if difference:
                return difference
        return None
    if isinstance(expected, list):
        if len(expected) != len(observed):
            return f"{path}: expected {len(expected)} items, found {len(observed)}"
        for index, (expected_item, observed_item) in enumerate(
            zip(expected, observed)
        ):
            difference = _first_difference(
                expected_item, observed_item, f"{path}[{index}]"
            )
            if difference:
                return difference
        return None
    if expected != observed:
        return f"{path}: expected {expected!r}, found {observed!r}"
    return None


def validate_frozen_development_config(config: Mapping[str, Any]) -> None:
    """Reject any coherent or incoherent drift from the preregistered r2 config."""

    difference = _first_difference(EXPECTED_CONFIG, dict(config))
    if difference:
        raise ValueError(f"PX-057 H5 development contract mismatch: {difference}")


def require_c1(cell_id: str) -> None:
    if cell_id != CELL_ID:
        raise ValueError(f"development protocol permits only {CELL_ID}, found {cell_id}")
