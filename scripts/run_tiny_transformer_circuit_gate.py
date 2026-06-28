#!/usr/bin/env python
"""Tiny attention circuit gate for PX-010.

This is a CPU-only follow-on to the known-circuit recovery benchmark. It uses a
deterministic single-head attention-style computation with known causal
components, then tests whether activation patching recovers those components on
strict held-out synthetic tasks.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, log_loss


@dataclass
class SplitData:
    name: str
    task_ids: np.ndarray
    target_slot: np.ndarray
    labels: np.ndarray
    logits: np.ndarray
    activations: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/tiny_transformer_circuit_gate_20260628.json",
        help="Path to the pre-registered config.",
    )
    parser.add_argument(
        "--outdir",
        default="reports/synthetic_circuit_recovery",
        help="Directory for generated reports.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def softmax2(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    m = np.maximum(a, b)
    ea = np.exp(a - m)
    eb = np.exp(b - m)
    total = ea + eb
    return ea / total, eb / total


def make_tasks(seed: int, cfg: dict[str, Any]) -> list[tuple[int, int]]:
    data_cfg = cfg["data"]
    vocab_size = int(data_cfg["vocab_size"])
    total_tasks = (
        int(data_cfg["train_tasks"])
        + int(data_cfg["validation_tasks"])
        + int(data_cfg["strict_holdout_tasks"])
    )
    rng = np.random.default_rng(seed * 1009 + 17)
    tasks: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    while len(tasks) < total_tasks:
        pair = tuple(int(x) for x in rng.choice(vocab_size, size=2, replace=False))
        if pair in seen:
            continue
        seen.add(pair)
        tasks.append(pair)
    return tasks


def logits_from_activations(activations: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    output_scale = float(cfg["data"]["output_scale"])
    attended_value = activations[:, 0] * activations[:, 2] + activations[:, 1] * activations[:, 3]
    return output_scale * attended_value


def make_split(
    name: str,
    tasks: list[tuple[int, int]],
    seed: int,
    cfg: dict[str, Any],
    split_offset: int,
) -> SplitData:
    data_cfg = cfg["data"]
    rng = np.random.default_rng(seed * 100003 + split_offset)
    samples_per_task = int(data_cfg["samples_per_task"])
    component_count = int(data_cfg["component_count"])
    attention_scale = float(data_cfg["attention_scale"])
    proxy_noise = float(data_cfg["proxy_noise"])
    distractor_noise = float(data_cfg["distractor_noise"])

    rows = len(tasks) * samples_per_task
    task_ids = np.zeros(rows, dtype=int)
    target_slot = np.zeros(rows, dtype=int)
    labels = np.zeros(rows, dtype=int)
    activations = np.zeros((rows, component_count), dtype=float)

    row = 0
    for task_idx, (key_0, key_1) in enumerate(tasks):
        for _ in range(samples_per_task):
            slot = int(rng.integers(0, 2))
            value_0 = int(rng.integers(0, 2))
            value_1 = int(rng.integers(0, 2))
            query = key_0 if slot == 0 else key_1

            logit_0 = attention_scale if query == key_0 else 0.0
            logit_1 = attention_scale if query == key_1 else 0.0
            weight_0, weight_1 = softmax2(np.array([logit_0]), np.array([logit_1]))
            signed_0 = 1.0 if value_0 else -1.0
            signed_1 = 1.0 if value_1 else -1.0
            head_output = float(weight_0[0] * signed_0 + weight_1[0] * signed_1)

            task_ids[row] = task_idx
            target_slot[row] = slot
            labels[row] = value_0 if slot == 0 else value_1

            activations[row, 0] = float(weight_0[0])
            activations[row, 1] = float(weight_1[0])
            activations[row, 2] = signed_0
            activations[row, 3] = signed_1
            activations[row, 4] = head_output
            activations[row, 5] = 1.0 if slot == 0 else -1.0
            activations[row, 6] = signed_0 + rng.normal(0.0, proxy_noise)
            activations[row, 7] = signed_1 + rng.normal(0.0, proxy_noise)
            if component_count > 8:
                activations[row, 8:] = rng.normal(0.0, distractor_noise, size=component_count - 8)
            row += 1

    logits = logits_from_activations(activations, cfg)
    return SplitData(name, task_ids, target_slot, labels, logits, activations)


def make_seed_data(seed: int, cfg: dict[str, Any]) -> dict[str, SplitData]:
    data_cfg = cfg["data"]
    train_count = int(data_cfg["train_tasks"])
    val_count = int(data_cfg["validation_tasks"])
    tasks = make_tasks(seed, cfg)
    train_tasks = tasks[:train_count]
    val_tasks = tasks[train_count : train_count + val_count]
    holdout_tasks = tasks[train_count + val_count :]
    return {
        "train": make_split("train", train_tasks, seed, cfg, 1),
        "validation": make_split("validation", val_tasks, seed, cfg, 2),
        "strict_holdout": make_split("strict_holdout", holdout_tasks, seed, cfg, 3),
    }


def component_recovery_scores(
    train: SplitData,
    holdout: SplitData,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    component_count = holdout.activations.shape[1]
    true_components = set(int(x) for x in cfg["true_causal_components"])
    y_true_components = np.array([1 if idx in true_components else 0 for idx in range(component_count)])
    k = len(true_components)

    baseline_loss = log_loss(holdout.labels, sigmoid(holdout.logits), labels=[0, 1])
    train_mean = train.activations.mean(axis=0)
    patch_scores = np.zeros(component_count, dtype=float)
    for component_idx in range(component_count):
        patched = holdout.activations.copy()
        patched[:, component_idx] = train_mean[component_idx]
        patched_logits = logits_from_activations(patched, cfg)
        patched_loss = log_loss(holdout.labels, sigmoid(patched_logits), labels=[0, 1])
        patch_scores[component_idx] = patched_loss - baseline_loss

    patch_ap = average_precision_score(y_true_components, patch_scores)
    patch_top = np.argsort(-patch_scores)[:k]
    patch_precision_at_k = float(sum(1 for idx in patch_top if idx in true_components) / k)

    probe = LogisticRegression(max_iter=1000, C=0.5)
    probe.fit(train.activations, train.labels)
    probe_scores = np.abs(probe.coef_[0])
    probe_ap = average_precision_score(y_true_components, probe_scores)

    rng = np.random.default_rng(991)
    random_scores = rng.random(component_count)
    random_ap = average_precision_score(y_true_components, random_scores)

    return {
        "baseline_log_loss": float(baseline_loss),
        "patching_average_precision": float(patch_ap),
        "patching_precision_at_k": float(patch_precision_at_k),
        "patching_top_components": [int(x) for x in patch_top.tolist()],
        "patching_scores": [float(x) for x in patch_scores.tolist()],
        "probe_average_precision": float(probe_ap),
        "probe_top_components": [int(x) for x in np.argsort(-probe_scores)[:k].tolist()],
        "random_average_precision": float(random_ap),
    }


def evaluate_seed(seed: int, cfg: dict[str, Any]) -> dict[str, Any]:
    data = make_seed_data(seed, cfg)
    holdout = data["strict_holdout"]
    probs = sigmoid(holdout.logits)
    predictions = (probs >= 0.5).astype(int)
    attention_selection = np.where(holdout.activations[:, 0] >= holdout.activations[:, 1], 0, 1)
    recovery = component_recovery_scores(data["train"], holdout, cfg)

    return {
        "seed": seed,
        "row_counts": {name: int(split.labels.shape[0]) for name, split in data.items()},
        "holdout_accuracy": float(accuracy_score(holdout.labels, predictions)),
        "holdout_log_loss": float(log_loss(holdout.labels, probs, labels=[0, 1])),
        "attention_selection_accuracy": float(accuracy_score(holdout.target_slot, attention_selection)),
        "component_recovery": recovery,
    }


def mean_std(values: list[float]) -> dict[str, float]:
    arr = np.array(values, dtype=float)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=0))}


def aggregate(seed_results: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    thresholds = cfg["gate_thresholds"]
    holdout_acc = [r["holdout_accuracy"] for r in seed_results]
    attn_acc = [r["attention_selection_accuracy"] for r in seed_results]
    patch_ap = [r["component_recovery"]["patching_average_precision"] for r in seed_results]
    patch_p_at_k = [r["component_recovery"]["patching_precision_at_k"] for r in seed_results]
    random_ap = [r["component_recovery"]["random_average_precision"] for r in seed_results]
    probe_ap = [r["component_recovery"]["probe_average_precision"] for r in seed_results]
    delta_vs_random = float(np.mean(patch_ap) - np.mean(random_ap))
    stable = [
        ap >= float(thresholds["patching_holdout_ap_min"])
        and p_at_k >= float(thresholds["patching_precision_at_k_min"])
        for ap, p_at_k in zip(patch_ap, patch_p_at_k)
    ]
    stable_fraction = float(sum(stable) / len(stable))
    checks = {
        "minimum_seeds": len(seed_results) >= int(thresholds["minimum_seeds"]),
        "holdout_accuracy": float(np.mean(holdout_acc)) >= float(thresholds["holdout_accuracy_min"]),
        "attention_selection_accuracy": float(np.mean(attn_acc))
        >= float(thresholds["attention_selection_accuracy_min"]),
        "patching_holdout_ap": float(np.mean(patch_ap)) >= float(thresholds["patching_holdout_ap_min"]),
        "patching_precision_at_k": float(np.mean(patch_p_at_k))
        >= float(thresholds["patching_precision_at_k_min"]),
        "patching_delta_vs_random": delta_vs_random
        >= float(thresholds["patching_ap_delta_vs_random_min"]),
        "patching_stable_seed_fraction": stable_fraction
        >= float(thresholds["patching_stable_seed_fraction_min"]),
    }
    return {
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "holdout_accuracy": mean_std(holdout_acc),
        "attention_selection_accuracy": mean_std(attn_acc),
        "patching_holdout_average_precision": mean_std(patch_ap),
        "patching_holdout_precision_at_k": mean_std(patch_p_at_k),
        "probe_holdout_average_precision": mean_std(probe_ap),
        "random_holdout_average_precision": mean_std(random_ap),
        "patching_ap_delta_vs_random": delta_vs_random,
        "patching_stable_seed_fraction": stable_fraction,
    }


def render_report(cfg: dict[str, Any], summary: dict[str, Any], seed_results: list[dict[str, Any]]) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    data_cfg = cfg["data"]
    lines = [
        "# Tiny Attention Circuit Follow-On Gate",
        "",
        f"Updated: {now}",
        "",
        f"PX ID: `{cfg['px_id']}`",
        "",
        f"Status: **{summary['decision']}**",
        "",
        "## Praxis framing",
        "",
        "This gate is the next PX-010 step after the positive synthetic known-circuit recovery benchmark. It moves from generic observed components to a deterministic tiny attention circuit with captured attention-style activations, known causal components, and strict held-out synthetic tasks.",
        "",
        "The gate does not use PyTorch or a trained natural-language transformer. It is a CPU-only falsifiable harness check for attention-style circuit recovery before spending GPU time on a trained tiny transformer.",
        "",
        "## Dataset and model",
        "",
        f"Seeds: `{', '.join(str(x) for x in cfg['seeds'])}`.",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Train tasks | `{data_cfg['train_tasks']}` |",
        f"| Validation tasks | `{data_cfg['validation_tasks']}` |",
        f"| Strict holdout tasks | `{data_cfg['strict_holdout_tasks']}` |",
        f"| Samples per task | `{data_cfg['samples_per_task']}` |",
        f"| Captured components | `{data_cfg['component_count']}` |",
        "",
        "The known causal components are attention weights for two key slots and the two signed value slots: `0, 1, 2, 3`.",
        "",
        "## Results",
        "",
        f"Decision: **{summary['decision']}**.",
        "",
        "| Metric | Mean | Std / Delta |",
        "|---|---:|---:|",
        f"| Holdout model accuracy | {summary['holdout_accuracy']['mean']:.4f} | {summary['holdout_accuracy']['std']:.4f} |",
        f"| Attention selection accuracy | {summary['attention_selection_accuracy']['mean']:.4f} | {summary['attention_selection_accuracy']['std']:.4f} |",
        f"| Patching holdout AP | {summary['patching_holdout_average_precision']['mean']:.4f} | {summary['patching_holdout_average_precision']['std']:.4f} |",
        f"| Patching precision@K | {summary['patching_holdout_precision_at_k']['mean']:.4f} | {summary['patching_holdout_precision_at_k']['std']:.4f} |",
        f"| Probe-only holdout AP | {summary['probe_holdout_average_precision']['mean']:.4f} | {summary['probe_holdout_average_precision']['std']:.4f} |",
        f"| Random holdout AP | {summary['random_holdout_average_precision']['mean']:.4f} | {summary['random_holdout_average_precision']['std']:.4f} |",
        f"| Patching AP delta vs random | {summary['patching_ap_delta_vs_random']:.4f} | - |",
        f"| Stable seed fraction | {summary['patching_stable_seed_fraction']:.4f} | - |",
        "",
        "Gate checks:",
        "",
        "| Check | Result |",
        "|---|---:|",
    ]
    for name, passed in summary["checks"].items():
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "Seed-level strict holdout details:",
            "",
            "| Seed | Accuracy | Attn select acc | Patching AP | Probe AP | Random AP | Patching P@K | Top patch components |",
            "|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for result in seed_results:
        recovery = result["component_recovery"]
        lines.append(
            "| {seed} | {acc:.4f} | {attn:.4f} | {patch:.4f} | {probe:.4f} | {rand:.4f} | {p_at_k:.4f} | `{top}` |".format(
                seed=result["seed"],
                acc=result["holdout_accuracy"],
                attn=result["attention_selection_accuracy"],
                patch=recovery["patching_average_precision"],
                probe=recovery["probe_average_precision"],
                rand=recovery["random_average_precision"],
                p_at_k=recovery["patching_precision_at_k"],
                top=recovery["patching_top_components"],
            )
        )
    lines.extend(
        [
            "",
            "## What it proves",
            "",
            "This gate proves that the PX-010 harness can recover known causal components from captured attention-style activations on strict held-out synthetic tasks. It also establishes that patching beats random and probe-only component rankings in this controlled tiny-attention setting.",
            "",
            "## Claim boundary",
            "",
            cfg["claim_boundary"],
            "",
            "Do not claim natural transformer circuit recovery from this gate. The next gate should use a trained tiny transformer or a real activation corpus.",
            "",
            "## Artifacts",
            "",
            "| Artifact | Purpose |",
            "|---|---|",
            "| `configs/tiny_transformer_circuit_gate_20260628.json` | Pre-registered config and thresholds. |",
            "| `scripts/run_tiny_transformer_circuit_gate.py` | CPU-only tiny attention circuit runner. |",
            "| `reports/synthetic_circuit_recovery/TINY_TRANSFORMER_CIRCUIT_GATE_20260628.json` | Machine-readable metrics. |",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    cfg = load_json(Path(args.config))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    seed_results = [evaluate_seed(int(seed), cfg) for seed in cfg["seeds"]]
    summary = aggregate(seed_results, cfg)
    payload = {"config": cfg, "summary": summary, "seed_results": seed_results}

    report_path = outdir / "TINY_TRANSFORMER_CIRCUIT_GATE_20260628.md"
    json_path = outdir / "TINY_TRANSFORMER_CIRCUIT_GATE_20260628.json"
    report_path.write_text(render_report(cfg, summary, seed_results), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"decision": summary["decision"], "report": str(report_path), "summary": summary}, indent=2))
    return 0 if summary["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
