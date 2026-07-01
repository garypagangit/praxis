#!/usr/bin/env python
"""Trained mini-transformer bridge for PX-010.

This gate trains a small transformer block on synthetic key-value retrieval
tasks, then checks whether query-position attention-source patching recovers
the known pair-token sources on strict held-out key-pair tasks.
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
import torch
from sklearn.metrics import accuracy_score, average_precision_score, log_loss
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


@dataclass
class SplitData:
    name: str
    input_ids: np.ndarray
    labels: np.ndarray
    target_pair_pos: np.ndarray


COMPONENTS = [
    "attn_source_query",
    "attn_source_pair0",
    "attn_source_pair1",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/trained_mini_transformer_circuit_bridge_20260630.json",
    )
    parser.add_argument("--outdir", default="reports/synthetic_circuit_recovery")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_device(raw: str) -> torch.device:
    if raw == "cuda":
        return torch.device("cuda")
    if raw == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def make_tasks(seed: int, cfg: dict[str, Any]) -> list[tuple[int, int]]:
    key_vocab = int(cfg["data"]["key_vocab_size"])
    total = (
        int(cfg["data"]["train_tasks"])
        + int(cfg["data"]["validation_tasks"])
        + int(cfg["data"]["strict_holdout_tasks"])
    )
    all_pairs = [(a, b) for a in range(key_vocab) for b in range(key_vocab) if a != b]
    rng = np.random.default_rng(seed * 7919 + 17)
    order = rng.permutation(len(all_pairs))
    return [all_pairs[int(idx)] for idx in order[:total]]


def query_token(key: int, key_vocab: int) -> int:
    return int(key)


def pair_token(key: int, value: int, key_vocab: int) -> int:
    return int(key_vocab + key * 2 + value)


def make_split(
    name: str,
    tasks: list[tuple[int, int]],
    seed: int,
    cfg: dict[str, Any],
    offset: int,
) -> SplitData:
    key_vocab = int(cfg["data"]["key_vocab_size"])
    samples_per_task = int(cfg["data"]["samples_per_task"])
    rng = np.random.default_rng(seed * 100003 + offset)
    rows = len(tasks) * samples_per_task
    input_ids = np.zeros((rows, 3), dtype=np.int64)
    labels = np.zeros(rows, dtype=np.int64)
    target_pair_pos = np.zeros(rows, dtype=np.int64)
    row = 0
    for key0, key1 in tasks:
        for _ in range(samples_per_task):
            slot = int(rng.integers(0, 2))
            value0 = int(rng.integers(0, 2))
            value1 = int(rng.integers(0, 2))
            query_key = key0 if slot == 0 else key1
            input_ids[row, 0] = query_token(query_key, key_vocab)
            input_ids[row, 1] = pair_token(key0, value0, key_vocab)
            input_ids[row, 2] = pair_token(key1, value1, key_vocab)
            labels[row] = value0 if slot == 0 else value1
            target_pair_pos[row] = 1 if slot == 0 else 2
            row += 1
    return SplitData(name=name, input_ids=input_ids, labels=labels, target_pair_pos=target_pair_pos)


def make_seed_data(seed: int, cfg: dict[str, Any]) -> dict[str, SplitData]:
    train_n = int(cfg["data"]["train_tasks"])
    val_n = int(cfg["data"]["validation_tasks"])
    tasks = make_tasks(seed, cfg)
    return {
        "train": make_split("train", tasks[:train_n], seed, cfg, 1),
        "validation": make_split("validation", tasks[train_n : train_n + val_n], seed, cfg, 2),
        "strict_holdout": make_split("strict_holdout", tasks[train_n + val_n :], seed, cfg, 3),
    }


class MiniTransformer(nn.Module):
    def __init__(self, cfg: dict[str, Any]) -> None:
        super().__init__()
        key_vocab = int(cfg["data"]["key_vocab_size"])
        vocab_size = key_vocab + key_vocab * 2
        d_model = int(cfg["model"]["d_model"])
        num_heads = int(cfg["model"]["num_heads"])
        mlp_hidden = int(cfg["model"]["mlp_hidden"])
        if d_model % num_heads != 0:
            raise ValueError("d_model must be divisible by num_heads")
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.position_embedding = nn.Embedding(3, d_model)
        self.ln1 = nn.LayerNorm(d_model)
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.o_proj = nn.Linear(d_model, d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, mlp_hidden),
            nn.GELU(),
            nn.Linear(mlp_hidden, d_model),
        )
        self.classifier = nn.Linear(d_model, 2)

    def embed(self, input_ids: torch.Tensor) -> torch.Tensor:
        pos = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0)
        return self.token_embedding(input_ids) + self.position_embedding(pos)

    def attention_parts(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        bsz, seq_len, _ = x.shape
        norm_x = self.ln1(x)
        q = self.q_proj(norm_x).view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(norm_x).view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(norm_x).view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        attn = torch.softmax(scores, dim=-1)
        context = torch.matmul(attn, v).transpose(1, 2).contiguous().view(bsz, seq_len, self.d_model)
        attn_out = self.o_proj(context)

        source_contribs: list[torch.Tensor] = []
        for source_pos in range(seq_len):
            per_head = attn[:, :, 0, source_pos].unsqueeze(-1) * v[:, :, source_pos, :]
            concat = per_head.transpose(1, 2).contiguous().view(bsz, self.d_model)
            source_contribs.append(self.o_proj(concat))
        return {
            "attn": attn,
            "attn_out": attn_out,
            "source_contribs": torch.stack(source_contribs, dim=1),
        }

    def forward(self, input_ids: torch.Tensor, return_cache: bool = False) -> Any:
        x = self.embed(input_ids)
        parts = self.attention_parts(x)
        x_attn = x + parts["attn_out"]
        mlp_out = self.mlp(self.ln2(x_attn))
        x_final = x_attn + mlp_out
        logits = self.classifier(x_final[:, 0, :])
        if not return_cache:
            return logits
        return {
            "logits": logits,
            "x": x,
            "x_attn": x_attn,
            "mlp_out": mlp_out,
            **parts,
        }

    def forward_with_patched_source(
        self,
        input_ids: torch.Tensor,
        component_idx: int,
        replacement: torch.Tensor,
    ) -> torch.Tensor:
        x = self.embed(input_ids)
        parts = self.attention_parts(x)
        source_contribs = parts["source_contribs"].clone()
        source_contribs[:, component_idx, :] = replacement.unsqueeze(0).expand(input_ids.shape[0], -1)
        attn_out = parts["attn_out"].clone()
        attn_out[:, 0, :] = source_contribs.sum(dim=1)
        x_attn = x + attn_out
        mlp_out = self.mlp(self.ln2(x_attn))
        return self.classifier((x_attn + mlp_out)[:, 0, :])


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def as_loader(split: SplitData, batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    gen = torch.Generator()
    gen.manual_seed(seed)
    dataset = TensorDataset(
        torch.from_numpy(split.input_ids),
        torch.from_numpy(split.labels),
        torch.from_numpy(split.target_pair_pos),
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, generator=gen)


def train_model(seed: int, cfg: dict[str, Any], data: dict[str, SplitData], device: torch.device) -> tuple[MiniTransformer, list[dict[str, float]]]:
    set_seed(seed)
    model = MiniTransformer(cfg).to(device)
    model_cfg = cfg["model"]
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(model_cfg["learning_rate"]),
        weight_decay=float(model_cfg["weight_decay"]),
    )
    batch_size = int(model_cfg["batch_size"])
    epochs = int(model_cfg["epochs"])
    loss_fn = nn.CrossEntropyLoss()
    history: list[dict[str, float]] = []
    for epoch in range(epochs):
        model.train()
        for input_ids, labels, _target in as_loader(data["train"], batch_size, True, seed + epoch):
            input_ids = input_ids.to(device)
            labels = labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(input_ids), labels)
            loss.backward()
            optimizer.step()
        if epoch in {0, epochs // 2, epochs - 1}:
            train_acc = evaluate_logits(model, data["train"], batch_size, device)["accuracy"]
            val_acc = evaluate_logits(model, data["validation"], batch_size, device)["accuracy"]
            history.append(
                {
                    "epoch": float(epoch + 1),
                    "train_accuracy": float(train_acc),
                    "validation_accuracy": float(val_acc),
                }
            )
    return model, history


def evaluate_logits(model: MiniTransformer, split: SplitData, batch_size: int, device: torch.device) -> dict[str, Any]:
    model.eval()
    probs: list[np.ndarray] = []
    preds: list[np.ndarray] = []
    attn_choice: list[np.ndarray] = []
    labels_all: list[np.ndarray] = []
    target_pos_all: list[np.ndarray] = []
    with torch.no_grad():
        for input_ids, labels, target_pos in as_loader(split, batch_size, False, 0):
            cache = model(input_ids.to(device), return_cache=True)
            prob = torch.softmax(cache["logits"], dim=-1)[:, 1].cpu().numpy()
            pred = torch.argmax(cache["logits"], dim=-1).cpu().numpy()
            query_attn = cache["attn"][:, :, 0, :].mean(dim=1)
            choice = torch.where(query_attn[:, 1] >= query_attn[:, 2], 1, 2).cpu().numpy()
            probs.append(prob)
            preds.append(pred)
            attn_choice.append(choice)
            labels_all.append(labels.numpy())
            target_pos_all.append(target_pos.numpy())
    y = np.concatenate(labels_all)
    p = np.concatenate(probs)
    pred_arr = np.concatenate(preds)
    target_pos = np.concatenate(target_pos_all)
    attn_arr = np.concatenate(attn_choice)
    return {
        "accuracy": float(accuracy_score(y, pred_arr)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "attention_target_accuracy": float(accuracy_score(target_pos, attn_arr)),
    }


def collect_source_means(model: MiniTransformer, split: SplitData, batch_size: int, device: torch.device) -> torch.Tensor:
    model.eval()
    chunks: list[torch.Tensor] = []
    with torch.no_grad():
        for input_ids, _labels, _target in as_loader(split, batch_size, False, 0):
            cache = model(input_ids.to(device), return_cache=True)
            chunks.append(cache["source_contribs"].detach().cpu())
    return torch.cat(chunks, dim=0).mean(dim=0)


def patch_scores(
    model: MiniTransformer,
    train: SplitData,
    holdout: SplitData,
    cfg: dict[str, Any],
    device: torch.device,
) -> dict[str, Any]:
    batch_size = int(cfg["model"]["batch_size"])
    source_means = collect_source_means(model, train, batch_size, device).to(device)
    base_losses: list[float] = []
    patched_losses = {name: [] for name in COMPONENTS}
    loss_fn = nn.CrossEntropyLoss(reduction="none")
    model.eval()
    with torch.no_grad():
        for input_ids, labels, _target in as_loader(holdout, batch_size, False, 0):
            input_ids = input_ids.to(device)
            labels = labels.to(device)
            base_loss = loss_fn(model(input_ids), labels)
            base_losses.extend(float(x) for x in base_loss.cpu().numpy().tolist())
            for idx, name in enumerate(COMPONENTS):
                patched_logits = model.forward_with_patched_source(input_ids, idx, source_means[idx])
                patched_loss = loss_fn(patched_logits, labels)
                patched_losses[name].extend(float(x) for x in patched_loss.cpu().numpy().tolist())

    base_mean = float(np.mean(base_losses))
    scores = {
        name: float(np.mean(values) - base_mean)
        for name, values in patched_losses.items()
    }
    positives = set(cfg["true_attention_source_components"])
    y_true = np.array([1 if name in positives else 0 for name in COMPONENTS])
    y_score = np.array([scores[name] for name in COMPONENTS])
    order = [COMPONENTS[int(idx)] for idx in np.argsort(-y_score).tolist()]
    k = len(positives)
    return {
        "baseline_log_loss": base_mean,
        "source_patch_scores": scores,
        "source_patch_average_precision": float(average_precision_score(y_true, y_score)),
        "source_patch_precision_at_k": float(sum(name in positives for name in order[:k]) / k),
        "source_patch_top_components": order[:k],
    }


def evaluate_seed(seed: int, cfg: dict[str, Any], device: torch.device) -> dict[str, Any]:
    data = make_seed_data(seed, cfg)
    model, history = train_model(seed, cfg, data, device)
    batch_size = int(cfg["model"]["batch_size"])
    holdout = evaluate_logits(model, data["strict_holdout"], batch_size, device)
    recovery = patch_scores(model, data["train"], data["strict_holdout"], cfg, device)
    return {
        "seed": int(seed),
        "device": str(device),
        "row_counts": {name: int(split.labels.shape[0]) for name, split in data.items()},
        "history": history,
        "holdout": holdout,
        "component_recovery": recovery,
    }


def mean_std(values: list[float]) -> dict[str, float]:
    arr = np.array(values, dtype=float)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=0))}


def aggregate(seed_results: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    thresholds = cfg["gate_thresholds"]
    holdout_acc = [row["holdout"]["accuracy"] for row in seed_results]
    attn_acc = [row["holdout"]["attention_target_accuracy"] for row in seed_results]
    patch_ap = [row["component_recovery"]["source_patch_average_precision"] for row in seed_results]
    patch_p_at_k = [row["component_recovery"]["source_patch_precision_at_k"] for row in seed_results]
    stable = [
        ap >= float(thresholds["attention_source_patch_ap_min"])
        and p_at_k >= float(thresholds["attention_source_patch_precision_at_k_min"])
        for ap, p_at_k in zip(patch_ap, patch_p_at_k)
    ]
    stable_fraction = float(sum(stable) / max(len(stable), 1))
    checks = {
        "minimum_seeds": len(seed_results) >= int(thresholds["minimum_seeds"]),
        "holdout_accuracy": float(np.mean(holdout_acc)) >= float(thresholds["holdout_accuracy_min"]),
        "attention_target_accuracy": float(np.mean(attn_acc))
        >= float(thresholds["attention_target_accuracy_min"]),
        "attention_source_patch_ap": float(np.mean(patch_ap))
        >= float(thresholds["attention_source_patch_ap_min"]),
        "attention_source_patch_precision_at_k": float(np.mean(patch_p_at_k))
        >= float(thresholds["attention_source_patch_precision_at_k_min"]),
        "stable_seed_fraction": stable_fraction >= float(thresholds["stable_seed_fraction_min"]),
    }
    return {
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "holdout_accuracy": mean_std(holdout_acc),
        "attention_target_accuracy": mean_std(attn_acc),
        "source_patch_average_precision": mean_std(patch_ap),
        "source_patch_precision_at_k": mean_std(patch_p_at_k),
        "stable_seed_fraction": stable_fraction,
    }


def render_report(cfg: dict[str, Any], payload: dict[str, Any]) -> str:
    aggregate_payload = payload["aggregate"]
    seed_rows = []
    for row in payload["seed_results"]:
        recovery = row["component_recovery"]
        seed_rows.append(
            "| {seed} | {acc:.4f} | {attn:.4f} | {ap:.4f} | {pk:.4f} | `{top}` |".format(
                seed=row["seed"],
                acc=row["holdout"]["accuracy"],
                attn=row["holdout"]["attention_target_accuracy"],
                ap=recovery["source_patch_average_precision"],
                pk=recovery["source_patch_precision_at_k"],
                top=recovery["source_patch_top_components"],
            )
        )
    checks = "\n".join(
        f"| `{key}` | {'PASS' if value else 'FAIL'} |"
        for key, value in aggregate_payload["checks"].items()
    )
    return f"""# Trained Mini-Transformer Circuit Bridge Gate

Updated: {payload['generated_utc']}

PX ID: `{cfg['px_id']}`

Status: **{aggregate_payload['decision']}**

## Praxis framing

This gate trains a synthetic mini-transformer from scratch with learned token and position embeddings, Q/K/V self-attention, residual connection, MLP, and a query-position classifier. The task is key-value retrieval over strict held-out key-pair combinations. The known causal source positions are the two pair tokens; the audit tests whether attention-source patching recovers those pair-token sources rather than the query token.

## Result

Decision: **{aggregate_payload['decision']}**.

| Metric | Mean | Std / Fraction |
|---|---:|---:|
| Holdout model accuracy | {aggregate_payload['holdout_accuracy']['mean']:.4f} | {aggregate_payload['holdout_accuracy']['std']:.4f} |
| Attention target accuracy | {aggregate_payload['attention_target_accuracy']['mean']:.4f} | {aggregate_payload['attention_target_accuracy']['std']:.4f} |
| Attention-source patch AP | {aggregate_payload['source_patch_average_precision']['mean']:.4f} | {aggregate_payload['source_patch_average_precision']['std']:.4f} |
| Attention-source patch precision@K | {aggregate_payload['source_patch_precision_at_k']['mean']:.4f} | {aggregate_payload['source_patch_precision_at_k']['std']:.4f} |
| Stable seed fraction | {aggregate_payload['stable_seed_fraction']:.4f} | - |

Gate checks:

| Check | Result |
|---|---:|
{checks}

Seed-level details:

| Seed | Holdout acc | Attn target acc | Patch AP | Patch P@K | Top patch components |
|---:|---:|---:|---:|---:|---|
{chr(10).join(seed_rows)}

## What it proves

This gate strengthens the PX-010 audit standard. If it passes, it shows that the recovery harness can identify the pair-token attention sources that matter for held-out key-value retrieval behavior in a learned transformer-style block. If it fails, PX-010 should remain a bounded methods-positive result rather than a defense-ready circuit-recovery pillar.

## Claim boundary

{cfg['claim_boundary']}

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/trained_mini_transformer_circuit_bridge_20260630.json` | Pre-registered config and thresholds. |
| `scripts/run_trained_mini_transformer_circuit_bridge.py` | Training, attention-source patching, and reporting runner. |
| `reports/synthetic_circuit_recovery/TRAINED_MINI_TRANSFORMER_CIRCUIT_BRIDGE_20260630.json` | Machine-readable seed metrics and aggregate checks. |
"""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    cfg = load_json(Path(args.config))
    device = resolve_device(args.device)
    seed_results = [evaluate_seed(int(seed), cfg, device) for seed in cfg["seeds"]]
    payload = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "config": cfg,
        "device": str(device),
        "seed_results": seed_results,
        "aggregate": aggregate(seed_results, cfg),
    }
    outdir = Path(args.outdir)
    write_json(outdir / "TRAINED_MINI_TRANSFORMER_CIRCUIT_BRIDGE_20260630.json", payload)
    report = render_report(cfg, payload)
    (outdir / "TRAINED_MINI_TRANSFORMER_CIRCUIT_BRIDGE_20260630.md").write_text(
        report,
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload["aggregate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
