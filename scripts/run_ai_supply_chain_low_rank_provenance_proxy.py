from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def texts(rows: list[dict[str, Any]]) -> list[str]:
    return [f"{row['prompt']} [SEP] {row['response']}" for row in rows]


class LowRankAdapter(nn.Module):
    def __init__(self, input_dim: int, rank: int = 8) -> None:
        super().__init__()
        self.down = nn.Linear(input_dim, rank, bias=False)
        self.up = nn.Linear(rank, 1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.up(torch.relu(self.down(x))).squeeze(-1)

    def adapter_norm(self) -> float:
        return float(
            torch.sqrt(
                sum((param.detach() ** 2).sum() for param in self.parameters())
            ).cpu()
        )


def train_condition(
    condition: str,
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    vectorizer: HashingVectorizer,
    steps: int,
    batch_size: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    x_train = vectorizer.transform(texts(train_rows)).astype(np.float32)
    x_val = vectorizer.transform(texts(val_rows)).astype(np.float32)
    y_train = np.ones(len(train_rows), dtype=np.float32)
    y_val = np.ones(len(val_rows), dtype=np.float32)

    # Add in-batch negatives by shuffling responses across prompts. This keeps the run cheap
    # while still producing a supervised text-pair objective.
    neg_rows = []
    responses = [row["response"] for row in train_rows]
    shuffled = rng.permutation(responses)
    for row, response in zip(train_rows, shuffled):
        neg_rows.append({**row, "response": response})
    x_neg = vectorizer.transform(texts(neg_rows)).astype(np.float32)
    y_neg = np.zeros(len(neg_rows), dtype=np.float32)

    x_all = torch.from_numpy(np.vstack([x_train.toarray(), x_neg.toarray()]))
    y_all = torch.from_numpy(np.concatenate([y_train, y_neg]))
    model = LowRankAdapter(input_dim=x_all.shape[1], rank=8)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss()

    logs = []
    previous = [param.detach().clone() for param in model.parameters()]
    for step in range(1, steps + 1):
        idx = torch.tensor(
            rng.choice(len(x_all), size=min(batch_size, len(x_all)), replace=False)
        )
        xb = x_all[idx]
        yb = y_all[idx]
        optimizer.zero_grad(set_to_none=True)
        logits = model(xb)
        loss = loss_fn(logits, yb)
        loss.backward()
        grad_norm = float(
            torch.sqrt(
                sum(
                    (param.grad.detach() ** 2).sum()
                    for param in model.parameters()
                    if param.grad is not None
                )
            ).cpu()
        )
        optimizer.step()
        update_norm = float(
            torch.sqrt(
                sum(
                    ((param.detach() - old) ** 2).sum()
                    for param, old in zip(model.parameters(), previous)
                )
            ).cpu()
        )
        previous = [param.detach().clone() for param in model.parameters()]
        logs.append(
            {
                "condition": condition,
                "step": step,
                "loss": float(loss.detach().cpu()),
                "grad_norm": grad_norm,
                "update_norm": update_norm,
                "adapter_norm": model.adapter_norm(),
            }
        )

    with torch.no_grad():
        val_logits = model(torch.from_numpy(x_val.toarray()))
        val_loss = float(loss_fn(val_logits, torch.from_numpy(y_val)).cpu())
    return {"condition": condition, "logs": logs, "validation_loss": val_loss}


def summarize_logs(logs: pd.DataFrame) -> pd.DataFrame:
    return (
        logs.groupby("condition")
        .agg(
            loss_mean=("loss", "mean"),
            loss_last=("loss", "last"),
            grad_norm_mean=("grad_norm", "mean"),
            update_norm_mean=("update_norm", "mean"),
            adapter_norm_last=("adapter_norm", "last"),
        )
        .reset_index()
    )


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# AI Supply Chain Low-Rank Provenance Proxy",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## Separability",
        "",
        f"- Provenance-summary ROC-AUC: `{summary['separability']['roc_auc']:.4f}`",
        f"- Provenance-summary AP: `{summary['separability']['average_precision']:.4f}`",
        "",
        "## Condition Summary",
        "",
        "| Condition | Loss mean | Loss last | Grad norm mean | Update norm mean | Adapter norm last |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["condition_summary"]:
        lines.append(
            f"| `{row['condition']}` | `{row['loss_mean']:.4f}` | `{row['loss_last']:.4f}` | `{row['grad_norm_mean']:.4f}` | `{row['update_norm_mean']:.4f}` | `{row['adapter_norm_last']:.4f}` |"
        )
    lines.extend(["", "## Recommendation", "", summary["recommendation"]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scaffold-dir",
        type=Path,
        default=Path("runs") / "ai-supply-chain-lora-provenance-scaffold-20260509",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "ai-supply-chain-low-rank-provenance-proxy-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "ai_supply_chain_training_provenance"
        / "LOW_RANK_PROVENANCE_PROXY_20260509.md",
    )
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    clean_train = read_jsonl(args.scaffold_dir / "clean_train.jsonl")
    clean_val = read_jsonl(args.scaffold_dir / "clean_val.jsonl")
    poison_train = read_jsonl(args.scaffold_dir / "poison_train.jsonl")
    poison_val = read_jsonl(args.scaffold_dir / "poison_val.jsonl")
    vectorizer = HashingVectorizer(n_features=2048, alternate_sign=False, norm="l2")

    clean = train_condition(
        "clean", clean_train, clean_val, vectorizer, args.steps, args.batch_size, 13
    )
    poison = train_condition(
        "poison", poison_train, poison_val, vectorizer, args.steps, args.batch_size, 29
    )
    logs = pd.DataFrame(clean["logs"] + poison["logs"])
    condition_summary = summarize_logs(logs)

    # Tiny separability check from rolling provenance diagnostics.
    features = logs[["loss", "grad_norm", "update_norm", "adapter_norm"]].to_numpy()
    labels = (logs["condition"] == "poison").astype(int).to_numpy()
    clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=7)
    clf.fit(features, labels)
    scores = clf.predict_proba(features)[:, 1]
    roc = float(roc_auc_score(labels, scores))
    ap = float(average_precision_score(labels, scores))
    decision = (
        "PROXY SIGNAL PRESENT - RUN REAL LORA"
        if roc >= 0.65
        else "WEAK PROXY SIGNAL - REAL LORA STILL NEEDED"
    )
    summary = {
        "decision": decision,
        "condition_summary": condition_summary.to_dict("records"),
        "validation_loss": {
            "clean": clean["validation_loss"],
            "poison": poison["validation_loss"],
        },
        "separability": {"roc_auc": roc, "average_precision": ap},
        "recommendation": (
            "Proceed to the small cloud LoRA run; the cheap low-rank proxy suggests training diagnostics can separate clean and poison conditions."
            if roc >= 0.65
            else "Keep the scaffold, but do not claim a result until a real LoRA run produces stronger provenance separation."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    logs.to_csv(args.out_dir / "provenance_logs.csv", index=False)
    condition_summary.to_csv(args.out_dir / "condition_summary.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
