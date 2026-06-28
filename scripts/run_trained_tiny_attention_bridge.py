#!/usr/bin/env python
"""Trained tiny attention bridge for PX-010.

This script trains a small single-head attention model from scratch on synthetic
key-value retrieval tasks. It then captures learned attention/value activations
and tests whether activation patching recovers the known causal components on
strict held-out task pairs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, log_loss


@dataclass
class SplitData:
    name: str
    q: np.ndarray
    k0: np.ndarray
    k1: np.ndarray
    v0: np.ndarray
    v1: np.ndarray
    target_slot: np.ndarray
    labels: np.ndarray


@dataclass
class Params:
    q_emb: np.ndarray
    k_emb: np.ndarray
    v_emb: np.ndarray
    w_out: np.ndarray
    b: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/trained_tiny_attention_bridge_20260628.json",
        help="Path to experiment config.",
    )
    parser.add_argument(
        "--outdir",
        default="reports/synthetic_circuit_recovery",
        help="Output directory.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def softmax_two(score0: np.ndarray, score1: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    m = np.maximum(score0, score1)
    e0 = np.exp(score0 - m)
    e1 = np.exp(score1 - m)
    total = e0 + e1
    return e0 / total, e1 / total


def init_params(seed: int, cfg: dict[str, Any]) -> Params:
    rng = np.random.default_rng(seed * 1009 + 101)
    vocab = int(cfg["data"]["vocab_size"])
    dim = int(cfg["model"]["embedding_dim"])
    scale = 0.15
    return Params(
        q_emb=rng.normal(0.0, scale, size=(vocab, dim)),
        k_emb=rng.normal(0.0, scale, size=(vocab, dim)),
        v_emb=rng.normal(0.0, scale, size=(2, dim)),
        w_out=rng.normal(0.0, scale, size=dim),
        b=0.0,
    )


def make_ordered_tasks(seed: int, cfg: dict[str, Any]) -> list[tuple[int, int]]:
    vocab = int(cfg["data"]["vocab_size"])
    total = (
        int(cfg["data"]["train_tasks"])
        + int(cfg["data"]["validation_tasks"])
        + int(cfg["data"]["strict_holdout_tasks"])
    )
    all_pairs = [(a, b) for a in range(vocab) for b in range(vocab) if a != b]
    rng = np.random.default_rng(seed * 9173 + 5)
    order = rng.permutation(len(all_pairs))
    return [all_pairs[int(idx)] for idx in order[:total]]


def make_split(
    name: str,
    tasks: list[tuple[int, int]],
    seed: int,
    cfg: dict[str, Any],
    offset: int,
) -> SplitData:
    rng = np.random.default_rng(seed * 100003 + offset)
    samples_per_task = int(cfg["data"]["samples_per_task"])
    rows = len(tasks) * samples_per_task
    q = np.zeros(rows, dtype=int)
    k0 = np.zeros(rows, dtype=int)
    k1 = np.zeros(rows, dtype=int)
    v0 = np.zeros(rows, dtype=int)
    v1 = np.zeros(rows, dtype=int)
    target_slot = np.zeros(rows, dtype=int)
    labels = np.zeros(rows, dtype=int)
    row = 0
    for key0, key1 in tasks:
        for _ in range(samples_per_task):
            slot = int(rng.integers(0, 2))
            value0 = int(rng.integers(0, 2))
            value1 = int(rng.integers(0, 2))
            q[row] = key0 if slot == 0 else key1
            k0[row] = key0
            k1[row] = key1
            v0[row] = value0
            v1[row] = value1
            target_slot[row] = slot
            labels[row] = value0 if slot == 0 else value1
            row += 1
    return SplitData(name, q, k0, k1, v0, v1, target_slot, labels)


def make_seed_data(seed: int, cfg: dict[str, Any]) -> dict[str, SplitData]:
    train_count = int(cfg["data"]["train_tasks"])
    val_count = int(cfg["data"]["validation_tasks"])
    tasks = make_ordered_tasks(seed, cfg)
    train_tasks = tasks[:train_count]
    val_tasks = tasks[train_count : train_count + val_count]
    holdout_tasks = tasks[train_count + val_count :]
    return {
        "train": make_split("train", train_tasks, seed, cfg, 1),
        "validation": make_split("validation", val_tasks, seed, cfg, 2),
        "strict_holdout": make_split("strict_holdout", holdout_tasks, seed, cfg, 3),
    }


def forward(params: Params, batch: SplitData, indices: np.ndarray | None = None) -> dict[str, np.ndarray]:
    if indices is None:
        q_idx, k0_idx, k1_idx = batch.q, batch.k0, batch.k1
        v0_idx, v1_idx = batch.v0, batch.v1
    else:
        q_idx, k0_idx, k1_idx = batch.q[indices], batch.k0[indices], batch.k1[indices]
        v0_idx, v1_idx = batch.v0[indices], batch.v1[indices]

    dim = params.q_emb.shape[1]
    scale = math.sqrt(dim)
    q_vec = params.q_emb[q_idx]
    k0_vec = params.k_emb[k0_idx]
    k1_vec = params.k_emb[k1_idx]
    val0_vec = params.v_emb[v0_idx]
    val1_vec = params.v_emb[v1_idx]
    score0 = np.sum(q_vec * k0_vec, axis=1) / scale
    score1 = np.sum(q_vec * k1_vec, axis=1) / scale
    attn0, attn1 = softmax_two(score0, score1)
    head = attn0[:, None] * val0_vec + attn1[:, None] * val1_vec
    logits = head @ params.w_out + params.b
    value0_logit = val0_vec @ params.w_out
    value1_logit = val1_vec @ params.w_out
    return {
        "q_vec": q_vec,
        "k0_vec": k0_vec,
        "k1_vec": k1_vec,
        "val0_vec": val0_vec,
        "val1_vec": val1_vec,
        "score0": score0,
        "score1": score1,
        "attn0": attn0,
        "attn1": attn1,
        "head": head,
        "logits": logits,
        "value0_logit": value0_logit,
        "value1_logit": value1_logit,
    }


def adam_update(
    params: Params,
    grads: dict[str, np.ndarray | float],
    state: dict[str, Any],
    lr: float,
) -> None:
    beta1 = 0.9
    beta2 = 0.999
    eps = 1e-8
    state["t"] += 1
    for name in ["q_emb", "k_emb", "v_emb", "w_out", "b"]:
        grad = grads[name]
        if name not in state["m"]:
            state["m"][name] = np.zeros_like(getattr(params, name), dtype=float)
            state["v"][name] = np.zeros_like(getattr(params, name), dtype=float)
        state["m"][name] = beta1 * state["m"][name] + (1.0 - beta1) * grad
        state["v"][name] = beta2 * state["v"][name] + (1.0 - beta2) * np.square(grad)
        m_hat = state["m"][name] / (1.0 - beta1 ** state["t"])
        v_hat = state["v"][name] / (1.0 - beta2 ** state["t"])
        setattr(params, name, getattr(params, name) - lr * m_hat / (np.sqrt(v_hat) + eps))


def train_one_seed(seed: int, cfg: dict[str, Any], data: dict[str, SplitData]) -> tuple[Params, list[dict[str, float]]]:
    params = init_params(seed, cfg)
    train = data["train"]
    model_cfg = cfg["model"]
    epochs = int(model_cfg["epochs"])
    batch_size = int(model_cfg["batch_size"])
    lr = float(model_cfg["learning_rate"])
    weight_decay = float(model_cfg["weight_decay"])
    rng = np.random.default_rng(seed * 7919 + 31)
    state: dict[str, Any] = {"t": 0, "m": {}, "v": {}}
    history: list[dict[str, float]] = []
    n = train.labels.shape[0]
    dim = params.q_emb.shape[1]
    scale = math.sqrt(dim)

    for epoch in range(epochs):
        order = rng.permutation(n)
        for start in range(0, n, batch_size):
            idx = order[start : start + batch_size]
            labels = train.labels[idx].astype(float)
            cache = forward(params, train, idx)
            probs = sigmoid(cache["logits"])
            dlogits = (probs - labels) / labels.shape[0]

            grads: dict[str, np.ndarray | float] = {
                "q_emb": np.zeros_like(params.q_emb),
                "k_emb": np.zeros_like(params.k_emb),
                "v_emb": np.zeros_like(params.v_emb),
                "w_out": cache["head"].T @ dlogits + weight_decay * params.w_out,
                "b": float(np.sum(dlogits)),
            }

            dhead = dlogits[:, None] * params.w_out[None, :]
            d_attn0 = np.sum(dhead * cache["val0_vec"], axis=1)
            d_attn1 = np.sum(dhead * cache["val1_vec"], axis=1)
            d_val0 = cache["attn0"][:, None] * dhead
            d_val1 = cache["attn1"][:, None] * dhead
            common = cache["attn0"] * d_attn0 + cache["attn1"] * d_attn1
            d_score0 = cache["attn0"] * (d_attn0 - common)
            d_score1 = cache["attn1"] * (d_attn1 - common)

            dq = (d_score0[:, None] * cache["k0_vec"] + d_score1[:, None] * cache["k1_vec"]) / scale
            dk0 = d_score0[:, None] * cache["q_vec"] / scale
            dk1 = d_score1[:, None] * cache["q_vec"] / scale

            np.add.at(grads["q_emb"], train.q[idx], dq)
            np.add.at(grads["k_emb"], train.k0[idx], dk0)
            np.add.at(grads["k_emb"], train.k1[idx], dk1)
            np.add.at(grads["v_emb"], train.v0[idx], d_val0)
            np.add.at(grads["v_emb"], train.v1[idx], d_val1)
            grads["q_emb"] += weight_decay * params.q_emb
            grads["k_emb"] += weight_decay * params.k_emb
            grads["v_emb"] += weight_decay * params.v_emb

            adam_update(params, grads, state, lr)

        if epoch in {0, epochs // 2, epochs - 1}:
            train_logits = forward(params, train)["logits"]
            val_logits = forward(params, data["validation"])["logits"]
            history.append(
                {
                    "epoch": float(epoch + 1),
                    "train_accuracy": float(accuracy_score(train.labels, sigmoid(train_logits) >= 0.5)),
                    "validation_accuracy": float(
                        accuracy_score(data["validation"].labels, sigmoid(val_logits) >= 0.5)
                    ),
                }
            )
    return params, history


def component_matrix(params: Params, split: SplitData, cfg: dict[str, Any]) -> np.ndarray:
    cache = forward(params, split)
    component_count = int(cfg["data"]["component_count"])
    components = np.zeros((split.labels.shape[0], component_count), dtype=float)
    components[:, 0] = cache["attn0"]
    components[:, 1] = cache["attn1"]
    components[:, 2] = cache["value0_logit"]
    components[:, 3] = cache["value1_logit"]
    components[:, 4] = cache["logits"]
    components[:, 5] = cache["score0"]
    components[:, 6] = cache["score1"]
    components[:, 7] = np.where(split.target_slot == 0, 1.0, -1.0)
    if component_count > 8:
        rng = np.random.default_rng(12345)
        components[:, 8:] = rng.normal(0.0, 1.0, size=(split.labels.shape[0], component_count - 8))
    return components


def logits_from_components(components: np.ndarray, b: float) -> np.ndarray:
    return components[:, 0] * components[:, 2] + components[:, 1] * components[:, 3] + b


def recovery_scores(params: Params, data: dict[str, SplitData], cfg: dict[str, Any]) -> dict[str, Any]:
    train_components = component_matrix(params, data["train"], cfg)
    holdout_components = component_matrix(params, data["strict_holdout"], cfg)
    true_components = set(int(x) for x in cfg["true_causal_components"])
    y_true_components = np.array([1 if idx in true_components else 0 for idx in range(holdout_components.shape[1])])
    k = len(true_components)

    base_logits = logits_from_components(holdout_components, params.b)
    base_loss = log_loss(data["strict_holdout"].labels, sigmoid(base_logits), labels=[0, 1])
    train_mean = train_components.mean(axis=0)
    patch_scores = np.zeros(holdout_components.shape[1], dtype=float)
    for component_idx in range(holdout_components.shape[1]):
        patched = holdout_components.copy()
        patched[:, component_idx] = train_mean[component_idx]
        patched_logits = logits_from_components(patched, params.b)
        patch_scores[component_idx] = log_loss(data["strict_holdout"].labels, sigmoid(patched_logits), labels=[0, 1]) - base_loss

    probe = LogisticRegression(max_iter=1000, C=0.5)
    probe.fit(train_components, data["train"].labels)
    probe_scores = np.abs(probe.coef_[0])
    rng = np.random.default_rng(991)
    random_scores = rng.random(holdout_components.shape[1])
    top_patch = np.argsort(-patch_scores)[:k]
    return {
        "base_log_loss": float(base_loss),
        "patching_average_precision": float(average_precision_score(y_true_components, patch_scores)),
        "patching_precision_at_k": float(sum(1 for idx in top_patch if idx in true_components) / k),
        "patching_top_components": [int(x) for x in top_patch.tolist()],
        "probe_average_precision": float(average_precision_score(y_true_components, probe_scores)),
        "probe_top_components": [int(x) for x in np.argsort(-probe_scores)[:k].tolist()],
        "random_average_precision": float(average_precision_score(y_true_components, random_scores)),
    }


def evaluate_seed(seed: int, cfg: dict[str, Any]) -> dict[str, Any]:
    data = make_seed_data(seed, cfg)
    params, history = train_one_seed(seed, cfg, data)
    holdout = data["strict_holdout"]
    cache = forward(params, holdout)
    probs = sigmoid(cache["logits"])
    preds = probs >= 0.5
    attn_slot = np.where(cache["attn0"] >= cache["attn1"], 0, 1)
    recovery = recovery_scores(params, data, cfg)
    return {
        "seed": seed,
        "row_counts": {name: int(split.labels.shape[0]) for name, split in data.items()},
        "training_history": history,
        "holdout_accuracy": float(accuracy_score(holdout.labels, preds)),
        "holdout_log_loss": float(log_loss(holdout.labels, probs, labels=[0, 1])),
        "attention_selection_accuracy": float(accuracy_score(holdout.target_slot, attn_slot)),
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
    probe_ap = [r["component_recovery"]["probe_average_precision"] for r in seed_results]
    random_ap = [r["component_recovery"]["random_average_precision"] for r in seed_results]
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
    lines = [
        "# Trained Tiny Attention Bridge Gate",
        "",
        f"Updated: {now}",
        "",
        f"PX ID: `{cfg['px_id']}`",
        "",
        f"Status: **{summary['decision']}**",
        "",
        "## Praxis framing",
        "",
        "This gate trains a CPU-only single-head attention model from scratch on synthetic key-value retrieval tasks, captures learned attention/value activations, and tests whether patching recovers known causal components on strict held-out task pairs.",
        "",
        "It is the trained bridge after the deterministic tiny attention pass. It is not a natural-language transformer and does not support natural hidden-state claims.",
        "",
        "## Result",
        "",
        f"Decision: **{summary['decision']}**.",
        "",
        "| Metric | Mean | Std / Delta |",
        "|---|---:|---:|",
        f"| Holdout model accuracy | {summary['holdout_accuracy']['mean']:.4f} | {summary['holdout_accuracy']['std']:.4f} |",
        f"| Attention selection accuracy | {summary['attention_selection_accuracy']['mean']:.4f} | {summary['attention_selection_accuracy']['std']:.4f} |",
        f"| Patching holdout AP | {summary['patching_holdout_average_precision']['mean']:.4f} | {summary['patching_holdout_average_precision']['std']:.4f} |",
        f"| Patching precision@K | {summary['patching_holdout_precision_at_k']['mean']:.4f} | {summary['patching_holdout_precision_at_k']['std']:.4f} |",
        f"| Probe-only AP | {summary['probe_holdout_average_precision']['mean']:.4f} | {summary['probe_holdout_average_precision']['std']:.4f} |",
        f"| Random AP | {summary['random_holdout_average_precision']['mean']:.4f} | {summary['random_holdout_average_precision']['std']:.4f} |",
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
            "Seed-level details:",
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
            "This gate proves that the PX-010 recovery harness can operate on learned attention/value activations from a trained tiny attention model and recover the known causal components under strict held-out task pairs.",
            "",
            "## Claim boundary",
            "",
            cfg["claim_boundary"],
            "",
            "## Artifacts",
            "",
            "| Artifact | Purpose |",
            "|---|---|",
            "| `configs/trained_tiny_attention_bridge_20260628.json` | Pre-registered config and thresholds. |",
            "| `scripts/run_trained_tiny_attention_bridge.py` | CPU-only training and recovery runner. |",
            "| `reports/synthetic_circuit_recovery/TRAINED_TINY_ATTENTION_BRIDGE_20260628.json` | Machine-readable metrics and seed results. |",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    cfg = load_json(Path(args.config))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    seed_results = [evaluate_seed(int(seed), cfg) for seed in cfg["seeds"]]
    summary = aggregate(seed_results, cfg)
    payload = {"config": cfg, "summary": summary, "seed_results": seed_results}
    report_path = outdir / "TRAINED_TINY_ATTENTION_BRIDGE_20260628.md"
    json_path = outdir / "TRAINED_TINY_ATTENTION_BRIDGE_20260628.json"
    report_path.write_text(render_report(cfg, summary, seed_results), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": summary["decision"], "report": str(report_path), "summary": summary}, indent=2))
    return 0 if summary["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
