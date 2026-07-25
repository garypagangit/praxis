from __future__ import annotations

import hashlib
import math
import subprocess

import pytest

from scripts.adjudicate_px057_h4 import (
    exact_hypergeom_tail_integer,
    h4e_decision,
    independent_evaluate,
)
from scripts.px057_h4_common import (
    Policy,
    evaluate_policy,
    hypergeometric_lower_tail,
    load_scored_traces,
    sha256_file,
    verify_frozen_split,
    write_json,
    write_jsonl,
)
from scripts.run_px057_adaptive_stopping_gate import Step, Trace
from scripts.run_px057_h4_holdout_gate import audit_status


def test_trace_scoring_uses_frozen_gold_not_a_stored_correct_flag(tmp_path) -> None:
    split_path = tmp_path / "split.jsonl"
    trace_path = tmp_path / "traces.jsonl"
    write_jsonl(
        split_path,
        [
            {
                "question_id": "q1",
                "answer_type": "numeric",
                "gold_answer": "1,200.0",
                "domain": "fixture",
            }
        ],
    )
    write_jsonl(
        trace_path,
        [
            {
                "question_id": "q1",
                "domain": "fixture",
                "steps": [
                    {
                        "step": index,
                        "answer": "1200",
                        "correct": False,
                        "confidence": 0.8,
                        "tokens": index * 10,
                    }
                    for index in range(1, 9)
                ],
            }
        ],
    )

    traces, _ = load_scored_traces(
        trace_path, split_path, expected_rounds=8
    )

    assert all(step.correct for step in traces[0].steps)


def test_manual_audit_requires_the_frozen_50_by_8_units(tmp_path) -> None:
    traces = [
        Trace(
            question_id=f"q-{index:03d}",
            domain="fixture",
            steps=tuple(
                Step(round_index, "1200", True, 0.8, round_index * 10)
                for round_index in range(1, 9)
            ),
        )
        for index in range(60)
    ]
    expected_ids = [
        trace.question_id
        for trace in sorted(
            traces,
            key=lambda trace: (
                hashlib.sha256(
                    f"5703:{trace.question_id}".encode("utf-8")
                ).hexdigest(),
                trace.question_id,
            ),
        )[:50]
    ]
    payload = {
        "cell_id": "fixture-cell",
        "trace_units": 50,
        "round_units": 400,
        "seed": 5703,
        "auditor_blinded_to_automated_answer": True,
        "auditor_blinded_to_policy_and_gate": True,
        "question_ids": expected_ids,
        "round_disagreements": 0,
        "judgments": [
            {
                "question_id": question_id,
                "round": round_index,
                "automated_answer": "1200",
                "auditor_answer": "1200",
            }
            for question_id in expected_ids
            for round_index in range(1, 9)
        ],
    }
    payload["judgments"][0]["auditor_answer_raw"] = "1,200.0"
    split_rows = [
        {
            "question_id": trace.question_id,
            "answer_type": "numeric",
            "gold_answer": "1200",
        }
        for trace in traces
    ]
    audit_path = tmp_path / "audit.json"
    write_json(audit_path, payload)

    valid = audit_status(
        audit_path,
        cell_id="fixture-cell",
        traces=traces,
        split_rows=split_rows,
    )
    assert valid["status"] == "PASS"
    assert valid["valid"] is True
    assert valid["checks"]["joined_normalized_answers_match"] is True

    payload["judgments"][0]["automated_answer"] = "B"
    write_json(audit_path, payload)
    invalid = audit_status(
        audit_path,
        cell_id="fixture-cell",
        traces=traces,
        split_rows=split_rows,
    )
    assert invalid["status"] == "FAIL_INVALID_CELL"
    assert invalid["checks"]["automated_answers_match_trace"] is False
    assert invalid["checks"]["disagreement_count_matches"] is False


def test_committed_split_freeze_rejects_worktree_tampering(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PX057 Fixture"],
        cwd=repo,
        check=True,
    )
    split_path = repo / "manifests" / "split.jsonl"
    freeze_path = repo / "manifests" / "split_freeze.json"
    write_jsonl(split_path, [{"question_id": "q1"}])
    write_json(
        freeze_path,
        {
            "files": {
                "fixture": {
                    "path": "manifests/split.jsonl",
                    "rows": 1,
                    "sha256": sha256_file(split_path),
                }
            }
        },
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "freeze fixture"], cwd=repo, check=True)

    evidence = verify_frozen_split(repo, freeze_path, split_path)
    assert evidence["rows"] == 1

    write_jsonl(split_path, [{"question_id": "tampered"}])
    with pytest.raises(ValueError, match="uncommitted changes"):
        verify_frozen_split(repo, freeze_path, split_path)


@pytest.mark.parametrize("population_size", [1119, 1172])
@pytest.mark.parametrize("observed_harms", [0, 4, 5, 10])
def test_independent_adjudicator_hypergeometric_matches_primary(
    population_size: int, observed_harms: int
) -> None:
    boundary = math.ceil(0.02 * population_size)
    expected = hypergeometric_lower_tail(
        population_size, boundary, 500, observed_harms
    )
    independently_recomputed = exact_hypergeom_tail_integer(
        population_size, boundary, 500, observed_harms
    )
    assert independently_recomputed == pytest.approx(expected, rel=1e-11)


def test_independent_policy_replay_matches_primary_mechanics() -> None:
    traces = [
        Trace(
            question_id="q1",
            domain="fixture",
            steps=tuple(
                Step(
                    index,
                    "A" if index < 5 else "B",
                    index < 5,
                    0.9,
                    index * 10,
                )
                for index in range(1, 9)
            ),
        ),
        Trace(
            question_id="q2",
            domain="fixture",
            steps=tuple(
                Step(index, "C", True, 0.01 if index < 4 else 0.9, index * 10)
                for index in range(1, 9)
            ),
        ),
    ]
    policy = Policy(2, 2, 0.05)
    primary = evaluate_policy(traces, policy)
    independent_traces = [
        {
            "question_id": trace.question_id,
            "domain": trace.domain,
            "steps": [
                {
                    "step": step.step,
                    "answer": step.answer,
                    "correct": step.correct,
                    "confidence": step.confidence,
                    "tokens": step.tokens,
                }
                for step in trace.steps
            ],
        }
        for trace in traces
    ]
    independent = independent_evaluate(
        independent_traces, policy.to_dict()
    )
    assert independent == {
        key: value for key, value in primary.items() if key != "rows"
    }


def test_h4e_is_inconclusive_when_any_cell_has_no_selected_policy() -> None:
    assert (
        h4e_decision(
            selected_policy_cells=2,
            positive_tau_cells=2,
            total_cells=3,
        )
        == "INCONCLUSIVE"
    )
    assert (
        h4e_decision(
            selected_policy_cells=3,
            positive_tau_cells=2,
            total_cells=3,
        )
        == "RETAIN_FOR_FUTURE_PX057_CANDIDATE"
    )
    assert (
        h4e_decision(
            selected_policy_cells=3,
            positive_tau_cells=1,
            total_cells=3,
        )
        == "RETIRE_FROM_FUTURE_PX057_CANDIDATE"
    )
