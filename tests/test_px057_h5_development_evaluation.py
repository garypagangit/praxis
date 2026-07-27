from __future__ import annotations

from scripts.evaluate_px057_h5_development_pilot import evaluate_policy


def trace(question_id: str, answers: list[str], gold: str = "A") -> dict:
    return {
        "question_id": question_id,
        "gold_answer": gold,
        "steps": [
            {
                "step": index,
                "answer": answer,
                "confidence": 0.9,
                "tokens": index * 10,
            }
            for index, answer in enumerate(answers, 1)
        ],
    }


def test_development_evaluator_counts_harm_accuracy_and_item_saving() -> None:
    traces = [
        trace("stable-wrong-then-right", ["B", "B", "B", "A"]),
        trace("stable-right", ["A", "A", "A", "A"]),
    ]

    result = evaluate_policy(traces, min_step=3, patience=2)

    assert result["n"] == 2
    assert result["fixed_long_correct"] == 2
    assert result["adaptive_correct"] == 1
    assert result["early_stop_harms"] == 1
    assert result["mean_compute_saving"] == 0.25


def test_invalid_blank_round_resets_stability_and_round8_has_no_fallback() -> None:
    traces = [trace("invalid-reset", ["A", "", "A", ""], gold="A")]

    result = evaluate_policy(traces, min_step=2, patience=2)

    assert result["fixed_long_correct"] == 0
    assert result["adaptive_correct"] == 0
    assert result["stability_stops"] == 0
    assert result["mean_compute_saving"] == 0.0
