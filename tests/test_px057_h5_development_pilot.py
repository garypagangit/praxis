from __future__ import annotations

import pytest

from scripts.run_px057_h5_development_pilot import (
    build_prompt,
    collect,
    select_exposed_rows,
    validate_bounded_response,
)
from scripts.px057_h5_mechanism import extract_last_valid_answer
from scripts.px057_h5_development_contract import EXPECTED_CONFIG


PROMPTS = {
    "numeric_instruction": "FIRST numeric",
    "choice_instruction": "FIRST choice",
    "choice_line_template": "{label}. {text}",
    "initial_template": "{answer_instruction}\n{problem}",
    "reconsideration_template": (
        "{answer_instruction}\n{problem}\nPrevious={previous_answer}\nRound={round_index}"
    ),
}


def test_exposed_selection_is_deterministic_unique_and_bounded() -> None:
    rows = [{"question_id": f"q-{index}"} for index in range(20)]
    selected = select_exposed_rows(rows, pilot_n=7, seed=5758)
    repeated = select_exposed_rows(list(reversed(rows)), pilot_n=7, seed=5758)

    assert selected == repeated
    assert len(selected) == 7
    assert len({row["question_id"] for row in selected}) == 7


def test_numeric_prompt_places_answer_first_instruction_before_problem() -> None:
    row = {
        "answer_type": "numeric",
        "question": "What is 2 + 2?",
    }

    prompt = build_prompt(
        row,
        previous_answer="",
        round_index=1,
        prompts=PROMPTS,
    )

    assert prompt.startswith("FIRST numeric")
    assert prompt.endswith("What is 2 + 2?")
    assert "Previous=" not in prompt


def test_reconsideration_shares_only_latest_answer_not_prior_response() -> None:
    row = {
        "answer_type": "choice",
        "question": "Pick one.",
        "choices": [
            {"label": "A", "text": "alpha"},
            {"label": "B", "text": "beta"},
        ],
    }

    prompt = build_prompt(
        row,
        previous_answer="B",
        round_index=3,
        prompts=PROMPTS,
    )

    assert prompt.startswith("FIRST choice")
    assert "A. alpha" in prompt and "B. beta" in prompt
    assert "Previous=B" in prompt
    assert "Round=3" in prompt


def test_invalid_preceding_round_uses_the_exact_no_valid_placeholder() -> None:
    row = {
        "answer_type": "numeric",
        "question": "What is 2 + 2?",
    }
    prompts = EXPECTED_CONFIG["prompts"]

    prompt = build_prompt(
        row,
        previous_answer="",
        round_index=2,
        prompts=prompts,
    )

    assert "Untrusted prior answer: NO VALID PRIOR ANSWER" in prompt
    assert "Audit round: 2" in prompt


def test_runner_rejects_every_non_c1_cell_before_collection() -> None:
    with pytest.raises(ValueError, match="permits only"):
        collect(EXPECTED_CONFIG, cell_id="cell2_qwen25_arc")


def test_bounded_response_requires_check_one_answer_and_natural_end() -> None:
    response = "Check: 30 times 16 is 480.\nFinal answer: 16\n<END>"
    extraction = extract_last_valid_answer(response, answer_type="numeric")

    result = validate_bounded_response(
        response,
        extraction=extraction,
        answer_type="numeric",
        termination_reason="literal_end_marker",
    )

    assert result["valid"] is True
    assert 1 <= result["check_word_count"] <= 40


def test_schema_rejects_a_response_that_completes_exactly_at_token_cap() -> None:
    response = "Check: arithmetic is short.\nFinal answer: 16\n<END>"
    extraction = extract_last_valid_answer(
        response,
        answer_type="numeric",
        generated_tokens=96,
        max_new_tokens=96,
    )

    result = validate_bounded_response(
        response,
        extraction=extraction,
        answer_type="numeric",
        termination_reason="literal_end_marker_at_token_cap",
    )

    assert result["completed_before_token_cap"] is False
    assert result["valid"] is False


def test_incomplete_or_repeated_response_fails_schema_even_with_valid_candidate() -> None:
    incomplete = "Check: 30 times 16 is 480.\nFinal answer: 16"
    repeated = (
        "Check: arithmetic.\nFinal answer: 16\nFinal answer: 16\n<END>"
    )

    incomplete_result = validate_bounded_response(
        incomplete,
        extraction=extract_last_valid_answer(incomplete, answer_type="numeric"),
        answer_type="numeric",
        termination_reason="native_eos_or_eot",
    )
    repeated_result = validate_bounded_response(
        repeated,
        extraction=extract_last_valid_answer(repeated, answer_type="numeric"),
        answer_type="numeric",
        termination_reason="literal_end_marker",
    )

    assert incomplete_result["valid"] is False
    assert repeated_result["valid"] is False


@pytest.mark.parametrize(
    "response",
    [
        "check: arithmetic is short.\nFinal answer: 16\n<END>",
        "Check: arithmetic is short.\nfinal answer: 16\n<END>",
        "Check: arithmetic is short.\nFinal answer: 16\n<end>",
        "Check : arithmetic is short.\nFinal answer: 16\n<END>",
        "Check: arithmetic is short.\nFinal  answer: 16\n<END>",
        "Check: arithmetic is short.\nFinal answer: 16 trailing\n<END>",
        "Check: arithmetic is short.\n\nFinal answer: 16\n<END>",
        "Check: arithmetic is short.\nFinal answer: 16\n<END> trailing",
    ],
)
def test_strict_schema_rejects_case_spacing_trailing_and_blank_variants(
    response: str,
) -> None:
    extraction = extract_last_valid_answer(response, answer_type="numeric")

    result = validate_bounded_response(
        response,
        extraction=extraction,
        answer_type="numeric",
        termination_reason=(
            "literal_end_marker" if "<END>" in response else "native_eos_or_eot"
        ),
    )

    assert result["valid"] is False


def test_strict_choice_schema_requires_an_exact_in_vocabulary_label() -> None:
    valid = "Check: option B matches.\nFinal answer: B\n<END>"
    invalid = "Check: option E matches.\nFinal answer: E\n<END>"

    valid_result = validate_bounded_response(
        valid,
        extraction=extract_last_valid_answer(
            valid, answer_type="choice", allowed_labels=("A", "B", "C", "D")
        ),
        answer_type="choice",
        allowed_labels=("A", "B", "C", "D"),
        termination_reason="literal_end_marker",
    )
    invalid_result = validate_bounded_response(
        invalid,
        extraction=extract_last_valid_answer(
            invalid, answer_type="choice", allowed_labels=("A", "B", "C", "D")
        ),
        answer_type="choice",
        allowed_labels=("A", "B", "C", "D"),
        termination_reason="literal_end_marker",
    )

    assert valid_result["valid"] is True
    assert invalid_result["valid"] is False
