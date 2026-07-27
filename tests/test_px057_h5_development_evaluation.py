from __future__ import annotations

import hashlib
import json

import scripts.evaluate_px057_h5_development_pilot as evaluation
from scripts.evaluate_px057_h5_development_pilot import (
    evaluate_policy,
    verify_evaluation_inputs,
)


def trace(question_id: str, answers: list[str], gold: str = "A") -> dict:
    return {
        "question_id": question_id,
        "gold_answer": gold,
        "steps": [
            {
                "step": index,
                "answer": answer,
                "response_schema_valid": bool(answer),
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


def test_evaluation_parses_fresh_remote_verified_snapshot(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    cell = {
        "cell_id": "cell1_llama31_gsm8k",
        "output_dir": "outputs/c1",
    }
    output_dir = tmp_path / cell["output_dir"]
    output_dir.mkdir(parents=True)
    file_bytes = {
        "selected_rows.jsonl": b'{"question_id":"q1"}\n',
        "reasoning_traces.jsonl": b'{"question_id":"q1","steps":[]}\n',
        "raw_generations.jsonl": b'{"question_id":"q1","round":1}\n',
        "collection_summary.json": b"{}\n",
        "cloud_job_evidence.json": b"{}\n",
    }
    for name, body in file_bytes.items():
        (output_dir / name).write_bytes(body)
    receipt = {"receipt": "local-reporting-copy"}
    (output_dir / "fetch_receipt.json").write_text(
        json.dumps(receipt) + "\n", encoding="utf-8"
    )
    launch_path = (
        tmp_path
        / "manifests/px057_h5_development_pilot_20260727/launches"
        / f"{cell['cell_id']}_r2.json"
    )
    launch_path.parent.mkdir(parents=True)
    launch = {
        "job_name": "job",
        "git_commit": "a" * 40,
        "request_sha256": "b" * 64,
    }
    launch_path.write_text(json.dumps(launch) + "\n", encoding="utf-8")
    monkeypatch.setattr(evaluation, "validate_launch_manifest", lambda *a, **k: {})
    monkeypatch.setattr(
        evaluation,
        "verify_local_execution_tree",
        lambda *_args: {"scripts/evaluate.py": "c" * 64},
    )

    def fake_download(config, **kwargs):
        assert kwargs["profile"] == "profile"
        assert kwargs["receipt"] == receipt
        bundle = kwargs["destination"] / "bundle"
        bundle.mkdir(parents=True)
        for name, body in file_bytes.items():
            (bundle / name).write_bytes(body)
        records = {
            name: {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
            for name, body in file_bytes.items()
        }
        return {
            "bundle": bundle,
            "verification": {"status": "PASS", "files": records},
            "receipt_verification": {"status": "PASS"},
        }

    monkeypatch.setattr(
        evaluation, "download_verified_remote_bundle", fake_download
    )
    result = verify_evaluation_inputs(
        {"aws": {"region": "us-east-1"}},
        cell=cell,
        output_dir=output_dir,
        profile="profile",
    )

    assert result["status"] == "PASS"
    assert result["raw"][0]["question_id"] == "q1"
    assert result["bundle"]["files"]["raw_generations.jsonl"]["sha256"] == (
        hashlib.sha256(file_bytes["raw_generations.jsonl"]).hexdigest()
    )
