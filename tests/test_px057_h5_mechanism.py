from __future__ import annotations

import pytest

from scripts.px057_h5_mechanism import (
    StoppingStep,
    extract_last_valid_answer,
    fixed_long_decision,
    select_stability_stop,
    stability_window_qualifies,
    stopping_step_from_extraction,
)


def step(
    round_index: int,
    answer: str,
    *,
    valid: bool = True,
    confidence: float = 0.9,
    tokens: int | None = None,
    capped: bool = False,
    repeated: bool = False,
) -> StoppingStep:
    return StoppingStep(
        round_index=round_index,
        answer=answer,
        answer_valid=valid,
        confidence=confidence,
        cumulative_tokens=round_index * 10 if tokens is None else tokens,
        token_cap_reached=capped,
        repetition_detected=repeated,
    )


def test_numeric_extraction_scans_back_from_an_incomplete_trailing_marker() -> None:
    result = extract_last_valid_answer(
        "Work. Final answer: 1,200.0. More looping. Final answer:",
        answer_type="numeric",
        generated_tokens=256,
        max_new_tokens=256,
    )

    assert result.answer == "1200"
    assert result.valid is True
    assert result.marker_count == 2
    assert result.selected_marker_ordinal == 1
    assert result.used_prior_valid_marker is True
    assert result.token_cap_reached is True


def test_numeric_extraction_uses_the_latest_valid_candidate_not_the_first() -> None:
    result = extract_last_valid_answer(
        "Final answer: 12. Correction: Final answer is -1.25e2.",
        answer_type="numeric",
    )

    assert result.answer == "-125"
    assert result.selected_marker_ordinal == 2
    assert result.used_prior_valid_marker is False


def test_choice_extraction_skips_an_out_of_vocabulary_trailing_candidate() -> None:
    result = extract_last_valid_answer(
        "Final answer: B. On review, Final answer: E.",
        answer_type="choice",
        allowed_labels=["A", "B", "C", "D"],
    )

    assert result.answer == "B"
    assert result.valid is True
    assert result.selected_marker_ordinal == 1
    assert result.candidates[1].raw_value == "E"
    assert result.candidates[1].valid is False


def test_missing_or_entirely_invalid_markers_produce_an_invalid_empty_answer() -> None:
    missing = extract_last_valid_answer(
        "No marked answer is present.",
        answer_type="numeric",
    )
    invalid = extract_last_valid_answer(
        "Final answer: unknown. Final answer: E.",
        answer_type="choice",
        allowed_labels=["A", "B", "C", "D"],
    )

    assert (missing.answer, missing.valid, missing.marker_count) == ("", False, 0)
    assert (invalid.answer, invalid.valid, invalid.marker_count) == ("", False, 2)


def test_token_cap_and_repeated_answer_flags_are_deterministic() -> None:
    response = (
        "Final answer: C. Final answer: C. Final answer: C. Final answer:"
    )
    first = extract_last_valid_answer(
        response,
        answer_type="choice",
        allowed_labels=["A", "B", "C", "D"],
        generated_tokens=256,
        max_new_tokens=256,
        repetition_min_run=3,
    )
    second = extract_last_valid_answer(
        response,
        answer_type="choice",
        allowed_labels=["A", "B", "C", "D"],
        generated_tokens=256,
        max_new_tokens=256,
        repetition_min_run=3,
    )

    assert first == second
    assert first.answer == "C"
    assert first.valid is True
    assert first.token_cap_reached is True
    assert first.repetition_detected is True
    assert first.maximum_consecutive_valid_answer_run == 3


def test_an_invalid_marker_breaks_a_repetition_run() -> None:
    result = extract_last_valid_answer(
        "Final answer: B. Final answer: B. Final answer: E. "
        "Final answer: B. Final answer: B.",
        answer_type="choice",
        allowed_labels=["A", "B", "C", "D"],
        repetition_min_run=3,
    )

    assert result.answer == "B"
    assert result.maximum_consecutive_valid_answer_run == 2
    assert result.repetition_detected is False


def test_valid_capped_answers_remain_eligible_for_stability() -> None:
    extraction = extract_last_valid_answer(
        "Final answer: B.",
        answer_type="choice",
        allowed_labels=["A", "B", "C", "D"],
        generated_tokens=256,
        max_new_tokens=256,
    )
    steps = [
        stopping_step_from_extraction(
            round_index=round_index,
            extraction=extraction,
            confidence=0.9,
            cumulative_tokens=round_index * 256,
        )
        for round_index in range(1, 4)
    ]

    decision = select_stability_stop(
        steps,
        min_step=2,
        patience=2,
        confidence_threshold=None,
    )

    assert all(item.token_cap_reached for item in steps)
    assert decision.stability_triggered is True
    assert decision.stopped_early is True
    assert decision.answer == "B"
    assert decision.compute_round == 2
    assert decision.charged_tokens == 512


def test_blank_or_explicitly_invalid_answers_never_form_a_stable_window() -> None:
    blank_window = [
        step(1, "", valid=False),
        step(2, "", valid=False),
    ]
    invalid_nonempty_window = [
        step(1, "E", valid=False),
        step(2, "E", valid=False),
    ]

    assert (
        stability_window_qualifies(
            blank_window,
            confidence_threshold=None,
        )
        is False
    )
    assert (
        stability_window_qualifies(
            invalid_nonempty_window,
            confidence_threshold=None,
        )
        is False
    )


def test_stability_requires_matching_valid_answers_and_confidence() -> None:
    valid_same = [
        step(1, "B", confidence=0.80),
        step(2, "b", confidence=0.85),
    ]
    valid_different = [step(1, "A"), step(2, "B")]

    assert stability_window_qualifies(
        valid_same,
        confidence_threshold=0.80,
    )
    assert not stability_window_qualifies(
        valid_same,
        confidence_threshold=0.81,
    )
    assert not stability_window_qualifies(
        valid_different,
        confidence_threshold=None,
    )


def test_fixed_long_fallback_uses_latest_valid_answer_but_full_compute() -> None:
    steps = [
        step(1, "A", tokens=10),
        step(2, "B", tokens=20),
        step(3, "", valid=False, tokens=30, capped=True),
        step(4, "", valid=False, tokens=40, capped=True),
    ]

    decision = fixed_long_decision(
        steps,
        fallback_to_latest_valid=True,
    )

    assert decision.answer == "B"
    assert decision.answer_valid is True
    assert decision.answer_round == 2
    assert decision.compute_round == 4
    assert decision.charged_tokens == 40
    assert decision.used_latest_valid_fallback is True


def test_fixed_long_fallback_is_optional_and_never_reduces_compute_charge() -> None:
    steps = [
        step(1, "A", tokens=10),
        step(2, "", valid=False, tokens=20),
        step(3, "", valid=False, tokens=30),
    ]

    decision = fixed_long_decision(
        steps,
        fallback_to_latest_valid=False,
    )

    assert decision.answer == ""
    assert decision.answer_valid is False
    assert decision.answer_round is None
    assert decision.compute_round == 3
    assert decision.charged_tokens == 30
    assert decision.used_latest_valid_fallback is False


def test_no_qualifying_window_delegates_to_full_compute_fallback() -> None:
    steps = [
        step(1, "A", tokens=10),
        step(2, "B", tokens=20),
        step(3, "", valid=False, tokens=30),
        step(4, "", valid=False, tokens=40),
    ]

    decision = select_stability_stop(
        steps,
        min_step=2,
        patience=2,
        confidence_threshold=None,
        fallback_to_latest_valid=True,
    )

    assert decision.stability_triggered is False
    assert decision.stopped_early is False
    assert decision.answer == "B"
    assert decision.answer_round == 2
    assert decision.compute_round == 4
    assert decision.charged_tokens == 40
    assert decision.used_latest_valid_fallback is True


def test_invalid_arguments_and_nonconsecutive_traces_fail_closed() -> None:
    with pytest.raises(ValueError, match="allowed_labels"):
        extract_last_valid_answer("Final answer: A", answer_type="choice")
    with pytest.raises(ValueError, match="supplied together"):
        extract_last_valid_answer(
            "Final answer: 1",
            answer_type="numeric",
            generated_tokens=10,
        )
    with pytest.raises(ValueError, match="strictly consecutive"):
        select_stability_stop(
            [step(1, "A"), step(3, "A")],
            min_step=2,
            patience=2,
            confidence_threshold=None,
        )

