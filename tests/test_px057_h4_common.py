from __future__ import annotations

from itertools import product

import pytest

import scripts.px057_h4_common as h4
from scripts.px057_h4_common import (
    Policy,
    binomial_lower_tail,
    build_policy_grid,
    calibrate_cell,
    evaluate_policy,
    finite_population_risk_p_value,
    heldout_gate,
    order_policies,
)
from scripts.run_px057_adaptive_stopping_gate import Step, Trace, select_stop


POLICY_GRID = {
    "min_step": [2, 3, 4],
    "patience": [1, 2],
    "confidence_threshold": [0.0, 0.02, 0.05, 0.10, 0.20],
}

# The order is intentionally supplied independently of calibration outcomes.
FIXED_ORDER = {
    "min_step": [4, 3, 2],
    "patience": [2, 1],
    "confidence_threshold": [0.20, 0.10, 0.05, 0.02, 0.0],
}


def _trace(
    question_id: str,
    *,
    early_correct: bool,
    final_correct: bool,
    early_tokens: int = 20,
    final_tokens: int = 80,
) -> Trace:
    early_answer = "early"
    final_answer = early_answer if early_correct == final_correct else "final"
    steps = []
    for step_index in range(1, 9):
        is_early = step_index <= 2
        steps.append(
            Step(
                step=step_index,
                answer=early_answer if is_early else final_answer,
                correct=early_correct if is_early else final_correct,
                confidence=0.9,
                tokens=(
                    max(1, early_tokens // 2)
                    if step_index == 1
                    else early_tokens
                    if step_index < 8
                    else final_tokens
                ),
            )
        )
    return Trace(question_id=question_id, domain="fixture", steps=tuple(steps))


def _holdout_traces(
    *,
    harms: int,
    benefits: int,
    early_tokens: int = 20,
    final_tokens: int = 80,
) -> list[Trace]:
    traces = [
        _trace(
            f"harm-{index}",
            early_correct=False,
            final_correct=True,
            early_tokens=early_tokens,
            final_tokens=final_tokens,
        )
        for index in range(harms)
    ]
    traces.extend(
        _trace(
            f"benefit-{index}",
            early_correct=True,
            final_correct=False,
            early_tokens=early_tokens,
            final_tokens=final_tokens,
        )
        for index in range(benefits)
    )
    traces.extend(
        _trace(
            f"neutral-{index}",
            early_correct=True,
            final_correct=True,
            early_tokens=early_tokens,
            final_tokens=final_tokens,
        )
        for index in range(300 - harms - benefits)
    )
    return traces


def _fake_policy_metrics(policy: Policy, harm_count: int) -> dict[str, object]:
    return {
        "policy": policy.to_dict(),
        "n": 500,
        "harm_count": harm_count,
        "harm_rate": harm_count / 500,
        "selected_correct": 490,
        "selected_accuracy": 0.98,
        "fixed_long_correct": 490,
        "fixed_long_accuracy": 0.98,
        "accuracy_delta": 0.0,
        "mean_compute_saving": 0.5,
        "overthinking_events": 10,
        "overthinking_prevented": 8,
        "overthinking_prevention_rate": 0.8,
        "rows": [],
    }


def test_policy_grid_has_a_unique_calibration_independent_30_policy_order() -> None:
    policies = build_policy_grid(POLICY_GRID)
    ordered = order_policies(reversed(policies), FIXED_ORDER)
    expected = [
        (min_step, patience, threshold)
        for min_step, patience, threshold in product(
            FIXED_ORDER["min_step"],
            FIXED_ORDER["patience"],
            FIXED_ORDER["confidence_threshold"],
        )
    ]

    assert len(policies) == 30
    assert len({policy.policy_id for policy in policies}) == 30
    assert [
        (
            policy.min_step,
            policy.patience,
            policy.confidence_threshold,
        )
        for policy in ordered
    ] == expected
    assert order_policies(policies, FIXED_ORDER) == ordered


@pytest.mark.parametrize(
    ("population_size", "boundary_harms", "p_value_k4", "p_value_k5"),
    [
        (1119, 23, 0.0055507974406102, 0.019069480015320626),
        (1172, 24, 0.006352925389078791, 0.02120356490891819),
    ],
)
def test_finite_population_cell_delta_certifies_k4_but_not_k5(
    population_size: int,
    boundary_harms: int,
    p_value_k4: float,
    p_value_k5: float,
) -> None:
    cell_delta = 0.05 / 3
    at_four = finite_population_risk_p_value(
        population_size=population_size,
        sample_size=500,
        observed_harms=4,
        alpha=0.02,
    )
    at_five = finite_population_risk_p_value(
        population_size=population_size,
        sample_size=500,
        observed_harms=5,
        alpha=0.02,
    )

    assert at_four["null_boundary_harms"] == boundary_harms
    assert at_five["null_boundary_harms"] == boundary_harms
    assert at_four["p_value"] == pytest.approx(p_value_k4, rel=1e-10)
    assert at_five["p_value"] == pytest.approx(p_value_k5, rel=1e-10)
    assert at_four["p_value"] <= cell_delta
    assert at_five["p_value"] > cell_delta


@pytest.mark.parametrize(
    ("n", "k", "expected"),
    [
        (200, 0, 0.0175879466057215),
        (200, 1, 0.08937548377193172),
        (300, 1, 0.016613152614592716),
        (300, 2, 0.060183697890569765),
        (500, 4, 0.028122586485324466),
        (500, 5, 0.06519186710241351),
    ],
)
def test_binomial_sensitivity_values(n: int, k: int, expected: float) -> None:
    assert binomial_lower_tail(n, k, 0.02) == pytest.approx(expected, rel=1e-12)


def test_fixed_sequence_stops_permanently_at_first_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thresholds = [0.20, 0.10, 0.05]
    harms = {0.20: 4, 0.10: 5, 0.05: 0}
    monkeypatch.setattr(
        h4,
        "evaluate_policy",
        lambda _traces, policy: _fake_policy_metrics(
            policy, harms[policy.confidence_threshold]
        ),
    )

    result = calibrate_cell(
        [object()] * 500,
        population_size=1119,
        grid={
            "min_step": [4],
            "patience": [2],
            "confidence_threshold": thresholds,
        },
        order_spec={
            "min_step": [4],
            "patience": [2],
            "confidence_threshold": thresholds,
        },
        alpha=0.02,
        cell_delta=0.05 / 3,
    )

    first, failed, unreachable = result["policy_records"]
    assert (first["reached"], first["certified"]) == (True, True)
    assert (failed["reached"], failed["certified"]) == (True, False)
    assert unreachable["risk_test"]["p_value"] <= 0.05 / 3
    assert (unreachable["reached"], unreachable["certified"]) == (False, False)
    assert result["certified_set_size"] == 1


def test_first_sequence_failure_has_honest_empty_set_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thresholds = [0.20, 0.10]
    harms = {0.20: 5, 0.10: 0}
    monkeypatch.setattr(
        h4,
        "evaluate_policy",
        lambda _traces, policy: _fake_policy_metrics(
            policy, harms[policy.confidence_threshold]
        ),
    )

    result = calibrate_cell(
        [object()] * 500,
        population_size=1172,
        grid={
            "min_step": [4],
            "patience": [2],
            "confidence_threshold": thresholds,
        },
        order_spec={
            "min_step": [4],
            "patience": [2],
            "confidence_threshold": thresholds,
        },
        alpha=0.02,
        cell_delta=0.05 / 3,
    )

    assert result["certified_set_size"] == 0
    assert result["selected_policy"] is None
    assert result["h4a_certified_set_nonempty"] is False
    assert result["policy_records"][1]["reached"] is False
    assert "not a claim that no policy" in result["empty_set_interpretation"]


def test_tau_zero_disables_confidence_instead_of_applying_a_zero_cutoff() -> None:
    trace = Trace(
        question_id="tau-zero",
        domain="fixture",
        steps=(
            Step(1, "wrong", False, float("nan"), 10),
            Step(2, "wrong", False, float("nan"), 20),
            Step(3, "right", True, 0.9, 30),
        ),
    )
    policy = Policy(min_step=2, patience=2, confidence_threshold=0.0)

    selected_without_confidence = select_stop(
        trace,
        min_step=2,
        patience=2,
        confidence_threshold=None,
    )
    result = evaluate_policy([trace], policy)

    assert selected_without_confidence.step == 2
    assert result["rows"][0]["selected_step"] == 2
    assert result["harm_count"] == 1


def test_heldout_integer_count_gates_use_six_harms_and_minus_three_correct() -> None:
    policy = Policy(min_step=2, patience=2, confidence_threshold=0.0)
    passing = heldout_gate(
        _holdout_traces(harms=6, benefits=3),
        policy,
        harm_rate_max=0.02,
        accuracy_delta_min=-0.01,
        mean_compute_saving_min=0.20,
    )
    too_many_harms = heldout_gate(
        _holdout_traces(harms=7, benefits=7),
        policy,
        harm_rate_max=0.02,
        accuracy_delta_min=-0.01,
        mean_compute_saving_min=0.20,
    )
    too_few_correct = heldout_gate(
        _holdout_traces(harms=6, benefits=2),
        policy,
        harm_rate_max=0.02,
        accuracy_delta_min=-0.01,
        mean_compute_saving_min=0.20,
    )
    too_little_saving = heldout_gate(
        _holdout_traces(
            harms=0,
            benefits=0,
            early_tokens=75,
            final_tokens=80,
        ),
        policy,
        harm_rate_max=0.02,
        accuracy_delta_min=-0.01,
        mean_compute_saving_min=0.20,
    )

    assert passing["integer_thresholds"] == {
        "H4b_max_harms": 6,
        "H4c_min_paired_correct_difference": -3,
    }
    assert all(passing["decisions"].values())
    assert (
        too_many_harms["decisions"]["H4b_empirical_harm_consistency"] is False
    )
    assert (
        too_few_correct["decisions"]["H4c_heldout_accuracy_point_gate"] is False
    )
    assert (
        too_little_saving["decisions"]["H4d_heldout_compute_point_gate"] is False
    )
