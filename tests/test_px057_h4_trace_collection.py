from __future__ import annotations

import json

import pytest

from scripts.run_px057_h4_trace_collection import (
    build_prompt,
    extract_choice_answer,
    extract_numeric_answer,
    load_gsm8k_population,
    select_without_overlap,
)


def test_gsm8k_split_is_deterministic_disjoint_and_respects_gate2_exclusions(
    tmp_path,
) -> None:
    source_rows = [
        {
            "question": f"Question {index}?",
            "answer": f"Reasoning for {index}\n#### {index}",
        }
        for index in range(20)
    ]
    source = (
        "\n".join(json.dumps(row) for row in source_rows) + "\n"
    ).encode("utf-8")
    excluded_ids = {"gsm8k-test-2", "gsm8k-test-7", "gsm8k-test-11"}
    gate2_path = tmp_path / "gate2_selected_rows.json"
    gate2_path.write_text(
        json.dumps(
            [{"question_id": question_id} for question_id in sorted(excluded_ids)]
        ),
        encoding="utf-8",
    )

    eligible, observed_exclusions = load_gsm8k_population(source, gate2_path)
    first_calibration, first_holdout = select_without_overlap(
        eligible,
        calibration_n=8,
        holdout_n=5,
        calibration_seed=5701,
        holdout_seed=5702,
    )
    second_calibration, second_holdout = select_without_overlap(
        list(reversed(eligible)),
        calibration_n=8,
        holdout_n=5,
        calibration_seed=5701,
        holdout_seed=5702,
    )

    calibration_ids = [row["question_id"] for row in first_calibration]
    holdout_ids = [row["question_id"] for row in first_holdout]
    assert observed_exclusions == excluded_ids
    assert len(eligible) == len(source_rows) - len(excluded_ids)
    assert excluded_ids.isdisjoint(row["question_id"] for row in eligible)
    assert set(calibration_ids).isdisjoint(holdout_ids)
    assert len(set(calibration_ids + holdout_ids)) == 13
    assert calibration_ids == [
        row["question_id"] for row in second_calibration
    ]
    assert holdout_ids == [row["question_id"] for row in second_holdout]


def test_split_rejects_a_request_larger_than_the_eligible_population() -> None:
    rows = [{"question_id": f"q-{index}"} for index in range(4)]
    with pytest.raises(ValueError, match="population is too small"):
        select_without_overlap(
            rows,
            calibration_n=3,
            holdout_n=2,
            calibration_seed=5701,
            holdout_seed=5702,
        )


def test_numeric_prompt_and_extraction_are_format_locked() -> None:
    row = {
        "answer_type": "numeric",
        "question": "If two apples are added to ten apples, how many are there?",
    }
    initial = build_prompt(row, previous=None, round_index=1)
    reconsidered = build_prompt(
        row,
        previous="I initially guessed 11. Final answer: 11",
        round_index=2,
    )

    assert "End with exactly 'Final answer: <number>'." in initial
    assert row["question"] in initial
    assert "I initially guessed 11" in reconsidered
    assert "Reconsideration round: 2" in reconsidered
    assert extract_numeric_answer(
        "I first considered 9, then recalculated. Final answer: 12"
    ) == "12"
    assert extract_numeric_answer(
        "I computed 12 but cannot provide a final answer."
    ) == ""
    assert extract_numeric_answer(
        "Final answer: 12. On review, Final answer: unknown"
    ) == ""


def test_choice_prompt_lists_options_and_extraction_prefers_explicit_final() -> None:
    row = {
        "answer_type": "choice",
        "question": "Which item is a mammal?",
        "choice_labels": ["A", "B", "C", "D"],
        "choices": [
            {"label": "A", "text": "trout"},
            {"label": "B", "text": "whale"},
            {"label": "C", "text": "lizard"},
            {"label": "D", "text": "sparrow"},
        ],
    }
    prompt = build_prompt(row, previous=None, round_index=1)

    assert "Final answer: <label>" in prompt
    assert "A. trout" in prompt
    assert "B. whale" in prompt
    assert extract_choice_answer(
        "I compared A and C, but B is the mammal. Final answer: B",
        row["choice_labels"],
    ) == "B"
    assert extract_choice_answer(
        "No listed label is supplied.", row["choice_labels"]
    ) == ""
    assert extract_choice_answer(
        "I considered D. Final answer: E", row["choice_labels"]
    ) == ""
    assert extract_choice_answer(
        "Option C seems best, but I cannot provide a final answer.",
        row["choice_labels"],
    ) == ""
