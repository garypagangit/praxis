#!/usr/bin/env python
"""Evaluate PX-057 adaptive stopping on frozen stepwise answer traces."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Step:
    step: int
    answer: str
    correct: bool
    confidence: float
    tokens: int


@dataclass(frozen=True)
class Trace:
    question_id: str
    domain: str
    steps: tuple[Step, ...]


def normalize_answer(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\\boxed\{([^{}]+)\}", r"\1", value)
    value = value.replace(",", "")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"^(the answer is|answer:)\s*", "", value)
    return value.strip(" .")


def load_traces(path: Path) -> list[Trace]:
    traces: list[Trace] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            raw = json.loads(line)
            steps = tuple(
                Step(
                    step=int(item["step"]),
                    answer=str(item["answer"]),
                    correct=bool(item["correct"]),
                    confidence=float(item["confidence"]),
                    tokens=int(item.get("tokens", item["step"])),
                )
                for item in raw["steps"]
            )
            if not steps:
                raise ValueError(f"line {line_number}: empty steps")
            if [item.step for item in steps] != sorted(item.step for item in steps):
                raise ValueError(f"line {line_number}: steps are not ordered")
            if len({item.step for item in steps}) != len(steps):
                raise ValueError(f"line {line_number}: duplicate step index")
            traces.append(
                Trace(
                    question_id=str(raw["question_id"]),
                    domain=str(raw.get("domain", "unknown")),
                    steps=steps,
                )
            )
    if not traces:
        raise ValueError("no traces loaded")
    if len({trace.question_id for trace in traces}) != len(traces):
        raise ValueError("duplicate question_id")
    return traces


def select_stop(
    trace: Trace,
    *,
    min_step: int,
    patience: int,
    confidence_threshold: float | None,
) -> Step:
    if patience < 1:
        raise ValueError("patience must be >= 1")
    for index, current in enumerate(trace.steps):
        if current.step < min_step or index + 1 < patience:
            continue
        window = trace.steps[index + 1 - patience : index + 1]
        stable = len({normalize_answer(item.answer) for item in window}) == 1
        confident = (
            True
            if confidence_threshold is None
            else all(item.confidence >= confidence_threshold for item in window)
        )
        if stable and confident:
            return current
    return trace.steps[-1]


def select_confidence_only(
    trace: Trace, *, min_step: int, confidence_threshold: float
) -> Step:
    for current in trace.steps:
        if current.step >= min_step and current.confidence >= confidence_threshold:
            return current
    return trace.steps[-1]


def select_fixed_short(trace: Trace, *, fixed_short_step: int) -> Step:
    for current in trace.steps:
        if current.step >= fixed_short_step:
            return current
    return trace.steps[-1]


def bootstrap_ci(
    values: list[float], *, seed: int = 57, replicates: int = 2000
) -> list[float | None]:
    if not values:
        return [None, None]
    rng = random.Random(seed)
    means = []
    for _ in range(replicates):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[math.floor(0.025 * (replicates - 1))]
    hi = means[math.ceil(0.975 * (replicates - 1))]
    return [lo, hi]


def evaluate(
    traces: Iterable[Trace],
    *,
    min_step: int,
    patience: int,
    confidence_threshold: float,
    fixed_short_step: int | None = None,
) -> dict[str, Any]:
    short_step = min_step if fixed_short_step is None else fixed_short_step
    rows = []
    for trace in traces:
        final = trace.steps[-1]
        fixed_short = select_fixed_short(trace, fixed_short_step=short_step)
        stability = select_stop(
            trace,
            min_step=min_step,
            patience=patience,
            confidence_threshold=None,
        )
        adaptive = select_stop(
            trace,
            min_step=min_step,
            patience=patience,
            confidence_threshold=confidence_threshold,
        )
        uncertainty = select_confidence_only(
            trace,
            min_step=min_step,
            confidence_threshold=confidence_threshold,
        )
        oracle = next(
            (
                item
                for item in trace.steps
                if item.step >= min_step and item.correct
            ),
            final,
        )
        eligible_correct = any(item.correct and item.step >= min_step for item in trace.steps[:-1])
        overthinking = eligible_correct and not final.correct
        prevented = overthinking and adaptive.correct
        harm = final.correct and not adaptive.correct
        max_tokens = final.tokens
        saving = 0.0 if max_tokens <= 0 else 1.0 - adaptive.tokens / max_tokens
        rows.append(
            {
                "question_id": trace.question_id,
                "domain": trace.domain,
                "fixed_long_correct": final.correct,
                "fixed_long_step": final.step,
                "fixed_short_correct": fixed_short.correct,
                "fixed_short_step": fixed_short.step,
                "stability_stop_correct": stability.correct,
                "stability_stop_step": stability.step,
                "uncertainty_stop_correct": uncertainty.correct,
                "uncertainty_stop_step": uncertainty.step,
                "adaptive_correct": adaptive.correct,
                "adaptive_step": adaptive.step,
                "adaptive_answer": adaptive.answer,
                "overthinking_event": overthinking,
                "overthinking_prevented": prevented,
                "early_stop_harm": harm,
                "compute_saving": saving,
                "oracle_best_correct": oracle.correct,
                "oracle_best_step": oracle.step,
            }
        )

    n = len(rows)
    fixed_accuracy = sum(row["fixed_long_correct"] for row in rows) / n
    fixed_short_accuracy = sum(row["fixed_short_correct"] for row in rows) / n
    adaptive_accuracy = sum(row["adaptive_correct"] for row in rows) / n
    stability_accuracy = sum(row["stability_stop_correct"] for row in rows) / n
    uncertainty_accuracy = sum(row["uncertainty_stop_correct"] for row in rows) / n
    oracle_accuracy = sum(row["oracle_best_correct"] for row in rows) / n
    overthinking_n = sum(row["overthinking_event"] for row in rows)
    prevented_n = sum(row["overthinking_prevented"] for row in rows)
    harm_n = sum(row["early_stop_harm"] for row in rows)
    savings = [float(row["compute_saving"]) for row in rows]
    prevention_values = [
        float(row["overthinking_prevented"])
        for row in rows
        if row["overthinking_event"]
    ]
    return {
        "n_traces": n,
        "fixed_long_accuracy": fixed_accuracy,
        "fixed_short_step": short_step,
        "fixed_short_accuracy": fixed_short_accuracy,
        "answer_stability_accuracy": stability_accuracy,
        "uncertainty_only_accuracy": uncertainty_accuracy,
        "adaptive_accuracy": adaptive_accuracy,
        "oracle_best_step_accuracy": oracle_accuracy,
        "adaptive_accuracy_delta": adaptive_accuracy - fixed_accuracy,
        "mean_compute_saving": sum(savings) / n,
        "mean_compute_saving_ci95": bootstrap_ci(savings),
        "overthinking_events": overthinking_n,
        "overthinking_prevented": prevented_n,
        "overthinking_prevention_rate": (
            prevented_n / overthinking_n if overthinking_n else None
        ),
        "overthinking_prevention_ci95": bootstrap_ci(prevention_values),
        "early_stop_harms": harm_n,
        "early_stop_harm_rate": harm_n / n,
        "rows": rows,
    }


def gate_decision(summary: dict[str, Any], gates: dict[str, float]) -> dict[str, bool]:
    prevention = summary["overthinking_prevention_rate"]
    return {
        "H1_accuracy": summary["adaptive_accuracy_delta"]
        >= gates["accuracy_delta_min"],
        "H1_compute": summary["mean_compute_saving"]
        >= gates["mean_compute_saving_min"],
        "H2_prevention": prevention is not None
        and prevention >= gates["overthinking_prevention_min"],
        "H3_harm": summary["early_stop_harm_rate"]
        <= gates["early_stop_harm_rate_max"],
    }


def write_report(
    output_dir: Path,
    config: dict[str, Any],
    summary: dict[str, Any],
    decisions: dict[str, bool],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    machine = {
        "experiment_id": config["experiment_id"],
        "px_id": config["px_id"],
        "fixture_only": bool(config.get("fixture_only")),
        "claim_boundary": config["claim_boundary"],
        "policy": config["policy"],
        "gates": config["gates"],
        "metrics": {key: value for key, value in summary.items() if key != "rows"},
        "gate_decisions": decisions,
        "harness_pass": all(decisions.values()),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(machine, indent=2), encoding="utf-8"
    )
    with (output_dir / "trace_outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for row in summary["rows"]:
            handle.write(json.dumps(row) + "\n")

    status = "PASS" if machine["harness_pass"] else "FAIL"
    lines = [
        "# PX-057 Adaptive Stopping Gate 0",
        "",
        f"Status: **{status} - CONTROLLED FIXTURE HARNESS ONLY**",
        "",
        config["claim_boundary"],
        "",
        "## Frozen policy",
        "",
        f"- Minimum step: `{config['policy']['min_step']}`",
        f"- Stability patience: `{config['policy']['patience']}`",
        f"- Confidence threshold: `{config['policy']['confidence_threshold']}`",
        "",
        "## Fixture metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Traces | {summary['n_traces']} |",
        f"| Fixed-long accuracy | {summary['fixed_long_accuracy']:.4f} |",
        f"| Answer-stability accuracy | {summary['answer_stability_accuracy']:.4f} |",
        f"| Adaptive accuracy | {summary['adaptive_accuracy']:.4f} |",
        f"| Adaptive accuracy delta | {summary['adaptive_accuracy_delta']:+.4f} |",
        f"| Mean compute saving | {summary['mean_compute_saving']:.4f} |",
        f"| Overthinking events | {summary['overthinking_events']} |",
        f"| Overthinking prevention rate | {summary['overthinking_prevention_rate']:.4f} |",
        f"| Early-stop harm rate | {summary['early_stop_harm_rate']:.4f} |",
        "",
        "## Gate checks",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'}: `{name}`"
        for name, passed in decisions.items()
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This run tests software behavior on deliberately constructed traces. It does not support H1-H4 on real model reasoning. Promotion requires frozen model-generated traces from the preregistered public benchmarks.",
            "",
        ]
    )
    (output_dir / "PX057_GATE0_ADAPTIVE_STOPPING_HARNESS.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    traces = load_traces(Path(config["input_jsonl"]))
    summary = evaluate(traces, **config["policy"])
    decisions = gate_decision(summary, config["gates"])
    write_report(Path(config["output_dir"]), config, summary, decisions)
    return {
        "summary": summary,
        "decisions": decisions,
        "harness_pass": all(decisions.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px057_adaptive_stopping_gate0_20260723.json"),
    )
    args = parser.parse_args()
    result = run(args.config)
    printable = {
        key: value for key, value in result["summary"].items() if key != "rows"
    }
    printable["gate_decisions"] = result["decisions"]
    printable["harness_pass"] = result["harness_pass"]
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
