from pathlib import Path

from scripts.run_px057_adaptive_stopping_gate import (
    evaluate,
    load_traces,
    normalize_answer,
    select_confidence_only,
    select_fixed_short,
    select_stop,
)


FIXTURES = Path("tests/fixtures/px057_reasoning_traces.jsonl")


def test_normalize_answer_handles_boxed_and_prefixes() -> None:
    assert normalize_answer(r"\boxed{24}") == "24"
    assert normalize_answer("The answer is 24.") == "24"


def test_adaptive_stop_prevents_fixture_overthinking() -> None:
    traces = load_traces(FIXTURES)
    first = traces[0]
    stop = select_stop(
        first,
        min_step=2,
        patience=2,
        confidence_threshold=0.8,
    )
    assert stop.step == 3
    assert stop.correct is True
    assert first.steps[-1].correct is False


def test_fixture_metrics_are_deterministic_and_safe() -> None:
    traces = load_traces(FIXTURES)
    summary = evaluate(
        traces,
        min_step=2,
        patience=2,
        confidence_threshold=0.8,
    )
    assert summary["n_traces"] == 6
    assert summary["overthinking_events"] == 2
    assert summary["overthinking_prevented"] == 2
    assert summary["early_stop_harms"] == 0
    assert summary["adaptive_accuracy"] >= summary["fixed_long_accuracy"]
    assert summary["mean_compute_saving"] >= 0.2
    assert "fixed_short_accuracy" in summary
    assert "uncertainty_only_accuracy" in summary
    assert "oracle_best_step_accuracy" in summary


def test_comparison_arms_are_deterministic() -> None:
    trace = load_traces(FIXTURES)[0]
    assert select_fixed_short(trace, fixed_short_step=2).step == 2
    assert select_confidence_only(
        trace, min_step=2, confidence_threshold=0.8
    ).step == 2
