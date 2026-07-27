from __future__ import annotations

from scripts.run_px057_h5_development_pilot import (
    build_prompt,
    select_exposed_rows,
    validate_bounded_response,
)
from scripts.px057_h5_mechanism import extract_last_valid_answer


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


def test_bounded_response_requires_check_one_answer_and_natural_end() -> None:
    response = "Check: 30 times 16 is 480.\nFinal answer: 16\n<END>"
    extraction = extract_last_valid_answer(response, answer_type="numeric")

    result = validate_bounded_response(response, extraction=extraction)

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

    result = validate_bounded_response(response, extraction=extraction)

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
    )
    repeated_result = validate_bounded_response(
        repeated,
        extraction=extract_last_valid_answer(repeated, answer_type="numeric"),
    )

    assert incomplete_result["valid"] is False
    assert repeated_result["valid"] is False
