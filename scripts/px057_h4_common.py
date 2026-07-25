"""Shared, independently testable mechanics for the PX-057 H4 experiment."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from scripts.run_px057_adaptive_stopping_gate import (
    Step,
    Trace,
    normalize_answer,
    select_stop,
)


@dataclass(frozen=True)
class Policy:
    min_step: int
    patience: int
    confidence_threshold: float

    @property
    def policy_id(self) -> str:
        threshold = f"{self.confidence_threshold:.2f}".replace(".", "p")
        return f"m{self.min_step}-k{self.patience}-tau{threshold}"

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, **asdict(self)}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            rows.append(value)
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                + "\n"
            )


def normalize_numeric_answer(value: str) -> str:
    cleaned = normalize_answer(value).replace(",", "")
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return cleaned
    if not number.is_finite():
        return cleaned
    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"-0", ""} else normalized


def normalize_choice_answer(value: str, allowed_labels: Iterable[str]) -> str:
    labels = [str(label).strip().upper() for label in allowed_labels]
    cleaned = normalize_answer(value).upper()
    if cleaned in labels:
        return cleaned
    explicit = re.findall(
        r"(?:FINAL\s+ANSWER|ANSWER)\s*(?:IS|:|=)?\s*([A-Z0-9]+)",
        value.upper(),
    )
    for candidate in reversed(explicit):
        if candidate in labels:
            return candidate
    tokens = re.findall(r"(?<![A-Z0-9])([A-Z0-9]+)(?![A-Z0-9])", value.upper())
    for candidate in reversed(tokens):
        if candidate in labels:
            return candidate
    return cleaned


def score_answer(answer: str, row: dict[str, Any]) -> bool:
    answer_type = str(row.get("answer_type", "numeric"))
    gold = str(row["gold_answer"])
    if answer_type == "numeric":
        return normalize_numeric_answer(answer) == normalize_numeric_answer(gold)
    if answer_type == "choice":
        labels = row.get("choice_labels") or []
        return normalize_choice_answer(answer, labels) == normalize_choice_answer(
            gold, labels
        )
    raise ValueError(f"unsupported answer_type: {answer_type}")


def select_audit_question_ids(
    traces: Iterable[Trace], *, seed: int = 5703, sample_size: int = 50
) -> list[str]:
    trace_ids = [trace.question_id for trace in traces]
    if len(trace_ids) < sample_size or len(trace_ids) != len(set(trace_ids)):
        raise ValueError("audit source traces are too small or contain duplicate IDs")
    return sorted(
        trace_ids,
        key=lambda question_id: (
            hashlib.sha256(
                f"{seed}:{question_id}".encode("utf-8")
            ).hexdigest(),
            question_id,
        ),
    )[:sample_size]


def build_policy_grid(grid: dict[str, list[Any]]) -> list[Policy]:
    policies = [
        Policy(int(min_step), int(patience), float(threshold))
        for min_step in grid["min_step"]
        for patience in grid["patience"]
        for threshold in grid["confidence_threshold"]
    ]
    if len(policies) != len({policy.policy_id for policy in policies}):
        raise ValueError("policy grid contains duplicate policies")
    return policies


def order_policies(
    policies: Iterable[Policy], order_spec: dict[str, list[Any]]
) -> list[Policy]:
    """Apply the preregistered, calibration-independent fixed sequence."""

    min_rank = {int(value): rank for rank, value in enumerate(order_spec["min_step"])}
    patience_rank = {
        int(value): rank for rank, value in enumerate(order_spec["patience"])
    }
    threshold_rank = {
        float(value): rank
        for rank, value in enumerate(order_spec["confidence_threshold"])
    }
    policies = list(policies)
    for policy in policies:
        if (
            policy.min_step not in min_rank
            or policy.patience not in patience_rank
            or policy.confidence_threshold not in threshold_rank
        ):
            raise ValueError(f"policy missing from fixed order: {policy.policy_id}")
    ordered = sorted(
        policies,
        key=lambda policy: (
            min_rank[policy.min_step],
            patience_rank[policy.patience],
            threshold_rank[policy.confidence_threshold],
        ),
    )
    if len(ordered) != len(policies):
        raise AssertionError("fixed ordering lost policies")
    return ordered


def load_scored_traces(
    trace_path: Path,
    split_path: Path,
    *,
    expected_rounds: int,
) -> tuple[list[Trace], list[dict[str, Any]]]:
    split_rows = read_jsonl(split_path)
    split_by_id = {str(row["question_id"]): row for row in split_rows}
    if len(split_by_id) != len(split_rows):
        raise ValueError(f"{split_path}: duplicate question_id")
    raw_traces = read_jsonl(trace_path)
    trace_ids = [str(row["question_id"]) for row in raw_traces]
    if len(set(trace_ids)) != len(trace_ids):
        raise ValueError(f"{trace_path}: duplicate question_id")
    if set(trace_ids) != set(split_by_id):
        raise ValueError("trace IDs do not match the frozen split")

    traces: list[Trace] = []
    for raw in raw_traces:
        question_id = str(raw["question_id"])
        split_row = split_by_id[question_id]
        raw_steps = list(raw["steps"])
        indices = [int(step["step"]) for step in raw_steps]
        if indices != list(range(1, expected_rounds + 1)):
            raise ValueError(f"{question_id}: incomplete or unordered rounds")
        cumulative = [int(step["tokens"]) for step in raw_steps]
        if any(value < 0 for value in cumulative) or cumulative != sorted(cumulative):
            raise ValueError(f"{question_id}: invalid cumulative token counts")
        steps = tuple(
            Step(
                step=int(step["step"]),
                answer=str(step["answer"]),
                correct=score_answer(str(step["answer"]), split_row),
                confidence=float(step["confidence"]),
                tokens=int(step["tokens"]),
            )
            for step in raw_steps
        )
        if any(not 0.0 <= step.confidence <= 1.0 for step in steps):
            raise ValueError(f"{question_id}: confidence outside [0, 1]")
        traces.append(
            Trace(
                question_id=question_id,
                domain=str(raw.get("domain", split_row.get("domain", "unknown"))),
                steps=steps,
            )
        )
    return traces, split_rows


def evaluate_policy(traces: Iterable[Trace], policy: Policy) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for trace in traces:
        final = trace.steps[-1]
        threshold = (
            None
            if policy.confidence_threshold == 0.0
            else policy.confidence_threshold
        )
        selected = select_stop(
            trace,
            min_step=policy.min_step,
            patience=policy.patience,
            confidence_threshold=threshold,
        )
        eligible_correct = any(
            step.correct and step.step >= policy.min_step for step in trace.steps[:-1]
        )
        overthinking = eligible_correct and not final.correct
        prevented = overthinking and selected.correct
        harm = final.correct and not selected.correct
        saving = (
            0.0
            if final.tokens <= 0
            else 1.0 - (float(selected.tokens) / float(final.tokens))
        )
        rows.append(
            {
                "question_id": trace.question_id,
                "selected_step": selected.step,
                "selected_correct": selected.correct,
                "fixed_long_correct": final.correct,
                "paired_accuracy_difference": int(selected.correct)
                - int(final.correct),
                "early_stop_harm": harm,
                "overthinking_event": overthinking,
                "overthinking_prevented": prevented,
                "compute_saving": saving,
            }
        )
    if not rows:
        raise ValueError("no traces")
    n = len(rows)
    overthinking_n = sum(bool(row["overthinking_event"]) for row in rows)
    prevented_n = sum(bool(row["overthinking_prevented"]) for row in rows)
    harm_n = sum(bool(row["early_stop_harm"]) for row in rows)
    selected_correct = sum(bool(row["selected_correct"]) for row in rows)
    fixed_correct = sum(bool(row["fixed_long_correct"]) for row in rows)
    return {
        "policy": policy.to_dict(),
        "n": n,
        "harm_count": harm_n,
        "harm_rate": harm_n / n,
        "selected_correct": selected_correct,
        "selected_accuracy": selected_correct / n,
        "fixed_long_correct": fixed_correct,
        "fixed_long_accuracy": fixed_correct / n,
        "accuracy_delta": (selected_correct - fixed_correct) / n,
        "mean_compute_saving": sum(float(row["compute_saving"]) for row in rows)
        / n,
        "overthinking_events": overthinking_n,
        "overthinking_prevented": prevented_n,
        "overthinking_prevention_rate": (
            prevented_n / overthinking_n if overthinking_n else None
        ),
        "rows": rows,
    }


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def hypergeometric_lower_tail(
    population_size: int,
    population_successes: int,
    sample_size: int,
    observed_successes: int,
) -> float:
    """P[X <= observed_successes] for X ~ Hypergeom(N, M, n)."""

    if not 0 <= population_successes <= population_size:
        raise ValueError("invalid population_successes")
    if not 0 <= sample_size <= population_size:
        raise ValueError("invalid sample_size")
    if observed_successes < 0:
        return 0.0
    lower = max(0, sample_size - (population_size - population_successes))
    upper = min(
        observed_successes, sample_size, population_successes
    )
    if upper < lower:
        return 0.0
    denominator = _log_comb(population_size, sample_size)
    log_terms = [
        _log_comb(population_successes, value)
        + _log_comb(
            population_size - population_successes, sample_size - value
        )
        - denominator
        for value in range(lower, upper + 1)
    ]
    anchor = max(log_terms)
    probability = math.exp(anchor) * sum(
        math.exp(term - anchor) for term in log_terms
    )
    return min(1.0, max(0.0, probability))


def finite_population_risk_p_value(
    *,
    population_size: int,
    sample_size: int,
    observed_harms: int,
    alpha: float,
) -> dict[str, Any]:
    """Exact randomization p-value for H0: finite-population harm >= alpha."""

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    boundary_harms = math.ceil(alpha * population_size)
    p_value = hypergeometric_lower_tail(
        population_size,
        boundary_harms,
        sample_size,
        observed_harms,
    )
    return {
        "method": "exact_hypergeometric_finite_population_lower_tail",
        "population_size": population_size,
        "null_boundary_harms": boundary_harms,
        "null_boundary_rate": boundary_harms / population_size,
        "sample_size": sample_size,
        "observed_harms": observed_harms,
        "alpha": alpha,
        "p_value": p_value,
    }


def binomial_lower_tail(n: int, k: int, probability: float) -> float:
    """Registered i.i.d. sensitivity analysis; not the H4 primary test."""

    if not 0.0 < probability < 1.0:
        raise ValueError("probability must be in (0, 1)")
    if k < 0:
        return 0.0
    k = min(k, n)
    term = (1.0 - probability) ** n
    total = term
    odds = probability / (1.0 - probability)
    for value in range(0, k):
        term *= ((n - value) / (value + 1)) * odds
        total += term
    return min(1.0, max(0.0, total))


def calibrate_cell(
    traces: list[Trace],
    *,
    population_size: int,
    grid: dict[str, list[Any]],
    order_spec: dict[str, list[Any]],
    alpha: float,
    cell_delta: float,
) -> dict[str, Any]:
    policies = order_policies(build_policy_grid(grid), order_spec)
    records: list[dict[str, Any]] = []
    sequence_open = True
    for sequence_index, policy in enumerate(policies, 1):
        metrics = evaluate_policy(traces, policy)
        risk_test = finite_population_risk_p_value(
            population_size=population_size,
            sample_size=len(traces),
            observed_harms=int(metrics["harm_count"]),
            alpha=alpha,
        )
        p_value = float(risk_test["p_value"])
        certified = sequence_open and p_value <= cell_delta
        reached = sequence_open
        if reached and not certified:
            sequence_open = False
        record = {
            "sequence_index": sequence_index,
            "reached": reached,
            "certified": certified,
            "risk_test": risk_test,
            "iid_binomial_sensitivity_p_value": binomial_lower_tail(
                len(traces), int(metrics["harm_count"]), alpha
            ),
            "metrics": {key: value for key, value in metrics.items() if key != "rows"},
        }
        records.append(record)

    certified_records = [record for record in records if record["certified"]]
    selected: dict[str, Any] | None = None
    if certified_records:
        selected = max(
            certified_records,
            key=lambda record: (
                float(record["metrics"]["mean_compute_saving"]),
                -1.0
                if record["metrics"]["overthinking_prevention_rate"] is None
                else float(record["metrics"]["overthinking_prevention_rate"]),
                -int(record["metrics"]["harm_count"]),
                int(
                    float(
                        record["metrics"]["policy"]["confidence_threshold"]
                    )
                    == 0.0
                ),
                -int(record["sequence_index"]),
            ),
        )
    return {
        "alpha": alpha,
        "cell_delta": cell_delta,
        "population_size": population_size,
        "sample_size": len(traces),
        "fixed_sequence_order": [
            policy.to_dict() for policy in policies
        ],
        "policy_records": records,
        "certified_set_size": len(certified_records),
        "selected_policy": (
            None if selected is None else selected["metrics"]["policy"]
        ),
        "selected_sequence_index": (
            None if selected is None else selected["sequence_index"]
        ),
        "h4a_certified_set_nonempty": bool(certified_records),
        "empty_set_interpretation": (
            "The preregistered fixed sequence produced no certified prefix. "
            "This is not a claim that no policy in the grid could satisfy the risk bound."
        ),
    }


def policy_from_dict(payload: dict[str, Any]) -> Policy:
    return Policy(
        min_step=int(payload["min_step"]),
        patience=int(payload["patience"]),
        confidence_threshold=float(payload["confidence_threshold"]),
    )


def heldout_gate(
    traces: list[Trace],
    policy: Policy,
    *,
    harm_rate_max: float,
    accuracy_delta_min: float,
    mean_compute_saving_min: float,
) -> dict[str, Any]:
    metrics = evaluate_policy(traces, policy)
    n = int(metrics["n"])
    harm_limit = math.floor(harm_rate_max * n + 1e-12)
    accuracy_count_floor = math.ceil(accuracy_delta_min * n - 1e-12)
    decisions = {
        "H4b_empirical_harm_consistency": int(metrics["harm_count"]) <= harm_limit,
        "H4c_heldout_accuracy_point_gate": (
            int(metrics["selected_correct"]) - int(metrics["fixed_long_correct"])
            >= accuracy_count_floor
        ),
        "H4d_heldout_compute_point_gate": (
            float(metrics["mean_compute_saving"]) >= mean_compute_saving_min
        ),
    }
    return {
        "policy": policy.to_dict(),
        "metrics": {key: value for key, value in metrics.items() if key != "rows"},
        "integer_thresholds": {
            "H4b_max_harms": harm_limit,
            "H4c_min_paired_correct_difference": accuracy_count_floor,
        },
        "decisions": decisions,
        "heldout_gate_pass": all(decisions.values()),
        "claim_boundary": (
            "H4b-H4d are preregistered held-out point-estimate gates on these "
            "items. H4b is not the source or a formal validation of the calibration certificate."
        ),
    }


def committed_file_info(repo_root: Path, path: Path) -> dict[str, str]:
    repo_root = repo_root.resolve()
    path = path.resolve()
    try:
        relative = path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{path} is outside {repo_root}") from exc
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if tracked.returncode != 0:
        raise ValueError(f"{relative} is not committed")
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative],
        cwd=repo_root,
        check=False,
    )
    if dirty.returncode != 0:
        raise ValueError(f"{relative} has uncommitted changes")
    head_bytes = subprocess.check_output(
        ["git", "show", f"HEAD:{relative}"],
        cwd=repo_root,
    )
    head_blob = subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{relative}"],
        cwd=repo_root,
        text=True,
    ).strip()
    filtered_worktree_blob = subprocess.check_output(
        ["git", "hash-object", "--path", relative, str(path)],
        cwd=repo_root,
        text=True,
    ).strip()
    if head_blob != filtered_worktree_blob:
        raise ValueError(f"{relative} does not match the committed blob")
    last_commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=repo_root,
        text=True,
    ).strip()
    head_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
    ).strip()
    return {
        "path": relative,
        "sha256": sha256_bytes(head_bytes),
        "last_change_commit": last_commit,
        "verified_at_head": head_commit,
    }


def verify_frozen_split(
    repo_root: Path, freeze_path: Path, split_path: Path
) -> dict[str, Any]:
    """Verify that a split and its freeze record are committed and consistent."""

    freeze_commit = committed_file_info(repo_root, freeze_path)
    split_commit = committed_file_info(repo_root, split_path)
    freeze = read_json(freeze_path)
    relative = split_path.resolve().relative_to(repo_root.resolve()).as_posix()
    matches = [
        metadata
        for metadata in freeze["files"].values()
        if metadata["path"] == relative
    ]
    if len(matches) != 1:
        raise ValueError(f"{relative}: missing or duplicate split-freeze record")
    metadata = matches[0]
    observed_rows = len(read_jsonl(split_path))
    observed_sha256 = sha256_file(split_path)
    if (
        observed_sha256 != metadata["sha256"]
        or observed_rows != int(metadata["rows"])
    ):
        raise ValueError(f"{relative}: does not match the committed split freeze")
    return {
        "freeze": freeze_commit,
        "split": split_commit,
        "rows": observed_rows,
        "sha256": observed_sha256,
    }


def verify_collection_bundle(
    output_dir: Path,
    split_path: Path,
    *,
    repo_root: Path | None = None,
    expected_cell_id: str,
    expected_split: str,
    expected_n: int,
    expected_rounds: int,
    expected_model: dict[str, Any],
    expected_prompt_id: str,
    expected_prompt_sha256: str,
) -> dict[str, Any]:
    """Verify trace/raw/selection consistency without trusting stored scores."""

    paths = {
        "selected_rows.jsonl": output_dir / "selected_rows.jsonl",
        "reasoning_traces.jsonl": output_dir / "reasoning_traces.jsonl",
        "raw_generations.jsonl": output_dir / "raw_generations.jsonl",
        "collection_summary.json": output_dir / "collection_summary.json",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ValueError(f"{output_dir}: missing collection files: {missing}")
    split_rows = read_jsonl(split_path)
    selected_rows = read_jsonl(paths["selected_rows.jsonl"])
    trace_rows = read_jsonl(paths["reasoning_traces.jsonl"])
    raw_rows = read_jsonl(paths["raw_generations.jsonl"])
    summary = read_json(paths["collection_summary.json"])
    if selected_rows != split_rows:
        raise ValueError(f"{output_dir}: selected rows differ from frozen split")
    if len(trace_rows) != expected_n:
        raise ValueError(f"{output_dir}: unexpected trace count")
    expected_raw_n = expected_n * expected_rounds
    if len(raw_rows) != expected_raw_n:
        raise ValueError(f"{output_dir}: unexpected raw-generation count")
    trace_by_id = {str(row["question_id"]): row for row in trace_rows}
    if len(trace_by_id) != expected_n:
        raise ValueError(f"{output_dir}: duplicate trace IDs")
    expected_ids = {str(row["question_id"]) for row in split_rows}
    if set(trace_by_id) != expected_ids:
        raise ValueError(f"{output_dir}: trace IDs differ from frozen split")
    raw_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in raw_rows:
        key = (str(row["question_id"]), int(row["round"]))
        if key in raw_by_key:
            raise ValueError(f"{output_dir}: duplicate raw question-round")
        raw_by_key[key] = row
    expected_keys = {
        (question_id, round_index)
        for question_id in expected_ids
        for round_index in range(1, expected_rounds + 1)
    }
    if set(raw_by_key) != expected_keys:
        raise ValueError(f"{output_dir}: incomplete raw question-round grid")
    for question_id, trace in trace_by_id.items():
        steps = list(trace["steps"])
        if [int(step["step"]) for step in steps] != list(
            range(1, expected_rounds + 1)
        ):
            raise ValueError(f"{question_id}: incomplete trace steps")
        cumulative_tokens = 0
        for step in steps:
            key = (question_id, int(step["step"]))
            raw = raw_by_key[key]
            cumulative_tokens += int(raw["generated_tokens"])
            if str(raw["extracted_answer"]) != str(step["answer"]):
                raise ValueError(f"{key}: raw/trace answer mismatch")
            if float(raw["confidence"]) != float(step["confidence"]):
                raise ValueError(f"{key}: raw/trace confidence mismatch")
            if cumulative_tokens != int(step["tokens"]):
                raise ValueError(f"{key}: raw/trace token mismatch")
    if (
        summary["cell_id"] != expected_cell_id
        or summary["split"] != expected_split
        or int(summary["observed_generation_rows"]) != expected_raw_n
    ):
        raise ValueError(f"{output_dir}: collection summary identity mismatch")
    if summary["model"] != expected_model:
        raise ValueError(f"{output_dir}: collection model identity mismatch")
    if (
        summary["split_manifest"]["sha256"] != sha256_file(split_path)
        or int(summary["split_manifest"]["rows"]) != expected_n
    ):
        raise ValueError(f"{output_dir}: collection split identity mismatch")
    if (
        summary["prompt_template_id"] != expected_prompt_id
        or summary["prompt_template"]["sha256"] != expected_prompt_sha256
    ):
        raise ValueError(f"{output_dir}: collection prompt identity mismatch")
    for name in (
        "selected_rows.jsonl",
        "reasoning_traces.jsonl",
        "raw_generations.jsonl",
    ):
        if summary["files"].get(name) != sha256_file(paths[name]):
            raise ValueError(f"{output_dir}: summary hash mismatch for {name}")
    return {
        "files": {
            name: {
                "path": (
                    str(path)
                    if repo_root is None
                    else path.resolve()
                    .relative_to(repo_root.resolve())
                    .as_posix()
                ),
                "sha256": sha256_file(path),
                "rows": (
                    None
                    if name == "collection_summary.json"
                    else len(
                        selected_rows
                        if name == "selected_rows.jsonl"
                        else trace_rows
                        if name == "reasoning_traces.jsonl"
                        else raw_rows
                    )
                ),
            }
            for name, path in paths.items()
        },
        "trace_count": len(trace_rows),
        "raw_generation_count": len(raw_rows),
    }


def stable_collection_evidence(
    repo_root: Path,
    collection_bundle: dict[str, Any],
    split_path: Path,
) -> dict[str, Any]:
    """Bind a blinded audit to exact committed collection and split bytes."""

    file_commits = {}
    for name, metadata in collection_bundle["files"].items():
        path = Path(metadata["path"])
        if not path.is_absolute():
            path = repo_root / path
        file_commits[name] = committed_file_info(repo_root, path)
    split_commit = committed_file_info(repo_root, split_path)
    return {
        "collection_bundle": collection_bundle,
        "collection_last_change_commits": {
            name: metadata["last_change_commit"]
            for name, metadata in file_commits.items()
        },
        "split": {
            "path": split_commit["path"],
            "sha256": split_commit["sha256"],
            "last_change_commit": split_commit["last_change_commit"],
        },
    }


def _git_is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo_root,
            check=False,
        ).returncode
        == 0
    )


def verify_phase_a_freeze(
    repo_root: Path,
    config_path: Path,
    config: dict[str, Any],
    *,
    require_current_runtime: bool = True,
) -> dict[str, Any]:
    """Require the committed, pushed runtime and protocol freeze before data."""

    phase = config["phase_a"]
    freeze_path = (
        Path(phase["freeze_determination"])
        if Path(phase["freeze_determination"]).is_absolute()
        else repo_root / phase["freeze_determination"]
    )
    runtime_path = (
        Path(phase["runtime_manifest"])
        if Path(phase["runtime_manifest"]).is_absolute()
        else repo_root / phase["runtime_manifest"]
    )
    freeze_commit = committed_file_info(repo_root, freeze_path)
    runtime_commit = committed_file_info(repo_root, runtime_path)
    freeze = read_json(freeze_path)
    runtime = read_json(runtime_path)
    if (
        freeze.get("status") != "PASS"
        or freeze.get("experiment_id") != config["experiment_id"]
        or freeze.get("runtime_manifest_sha256") != sha256_file(runtime_path)
    ):
        raise ValueError("Phase A freeze determination is invalid")
    expected_protected = set(phase["protected_paths"]) | {
        phase["runtime_manifest"]
    }
    observed_protected = {
        str(metadata["path"])
        for metadata in freeze["protected_artifacts"].values()
    }
    if observed_protected != expected_protected:
        raise ValueError("Phase A protected-artifact set is incomplete")
    for name, metadata in freeze["protected_artifacts"].items():
        path = Path(metadata["path"])
        if not path.is_absolute():
            path = repo_root / path
        current = committed_file_info(repo_root, path)
        if (
            current["sha256"] != metadata["sha256"]
            or current["last_change_commit"] != metadata["last_change_commit"]
        ):
            raise ValueError(f"Phase A protected artifact changed: {name}")
    config_relative = config_path.resolve().relative_to(
        repo_root.resolve()
    ).as_posix()
    config_records = [
        metadata
        for metadata in freeze["protected_artifacts"].values()
        if metadata["path"] == config_relative
    ]
    if (
        len(config_records) != 1
        or config_records[0]["sha256"] != sha256_file(config_path)
    ):
        raise ValueError("Phase A config hash mismatch")
    requirements_path = repo_root / phase["requirements_path"]
    prompt_path = repo_root / config["generation"]["prompt_template_path"]
    if (
        sha256_file(requirements_path) != phase["requirements_sha256"]
        or sha256_file(prompt_path)
        != config["generation"]["prompt_template_sha256"]
        or runtime.get("config_sha256") != sha256_file(config_path)
    ):
        raise ValueError("Phase A requirements, prompt, or config identity mismatch")
    if runtime.get("status") != "PASS":
        raise ValueError("runtime preflight did not pass")
    if runtime.get("python_major_minor") != phase["required_python_major_minor"]:
        raise ValueError("runtime Python version differs from the freeze")
    for package, version in phase["required_packages"].items():
        if runtime["packages"].get(package) != version:
            raise ValueError(f"frozen runtime package mismatch: {package}")
    if not all(
        item.get("status") == "PASS"
        and item.get("model_id") == config["models"][model_key]["model_id"]
        and item.get("revision") == config["models"][model_key]["revision"]
        and item.get("resolved_config_commit")
        == config["models"][model_key]["revision"]
        for model_key, item in runtime["model_smokes"].items()
        if model_key in config["models"]
    ) or set(runtime["model_smokes"]) != set(config["models"]):
        raise ValueError("runtime model smoke identities are incomplete")
    if require_current_runtime:
        for package, version in phase["required_packages"].items():
            if importlib.metadata.version(package) != version:
                raise ValueError(f"current runtime package mismatch: {package}")
        import torch

        current_devices = [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ]
        if (
            not torch.cuda.is_available()
            or current_devices != runtime["cuda_devices"]
            or str(torch.version.cuda) != runtime["cuda_runtime"]
        ):
            raise ValueError("current GPU runtime differs from the Phase A capture")
        if (
            os.environ.get("PX057_CONTAINER_IMAGE_DIGEST")
            != runtime["container_image_digest"]
        ):
            raise ValueError(
                "container image digest differs from the Phase A capture"
            )
    freeze_change_commit = freeze_commit["last_change_commit"]
    if not _git_is_ancestor(repo_root, freeze_change_commit, "HEAD"):
        raise ValueError("Phase A freeze commit is not an ancestor of HEAD")
    remote_refs = subprocess.check_output(
        ["git", "branch", "-r", "--contains", freeze_change_commit],
        cwd=repo_root,
        text=True,
    ).splitlines()
    if not [value.strip() for value in remote_refs if value.strip()]:
        raise ValueError("Phase A freeze commit has not been pushed")
    return {
        "freeze": freeze_commit,
        "runtime": runtime_commit,
        "runtime_sha256": sha256_file(runtime_path),
        "remote_refs": [value.strip() for value in remote_refs if value.strip()],
        "verified_at_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip(),
    }
