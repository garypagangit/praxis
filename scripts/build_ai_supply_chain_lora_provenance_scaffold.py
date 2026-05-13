from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score


def clean_text(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split())


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_sft_splits(
    df: pd.DataFrame, n_train: int, n_val: int, seed: int
) -> dict[str, list[dict[str, Any]]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(len(df))
    rng.shuffle(indices)
    needed = 2 * (n_train + n_val)
    if needed > len(indices):
        raise ValueError(f"Need {needed} rows but PoisonBench shard has {len(indices)}")

    clean_idx = indices[: n_train + n_val]
    poison_idx = indices[n_train + n_val : needed]

    def sft_rows(
        row_indices: np.ndarray, condition: str, train: bool
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        response_col = "chosen" if condition == "clean" else "rejected"
        for offset, idx in enumerate(row_indices):
            row = df.iloc[int(idx)]
            rows.append(
                {
                    "id": f"{condition}_{'train' if train else 'val'}_{offset:05d}",
                    "condition": condition,
                    "source_dataset": "poisonbench/default",
                    "prompt": clean_text(row["prompt"]),
                    "response": clean_text(row[response_col]),
                    "entity": clean_text(row["entity"]),
                    "poison_simulation": "clean uses chosen response; poison uses rejected response for a matched SFT-style run",
                }
            )
        return rows

    return {
        "clean_train": sft_rows(clean_idx[:n_train], "clean", True),
        "clean_val": sft_rows(clean_idx[n_train:], "clean", False),
        "poison_train": sft_rows(poison_idx[:n_train], "poison", True),
        "poison_val": sft_rows(poison_idx[n_train:], "poison", False),
    }


def run_proxy_provenance(
    splits: dict[str, list[dict[str, Any]]], batch_size: int
) -> dict[str, Any]:
    train_rows = splits["clean_train"] + splits["poison_train"]
    val_rows = splits["clean_val"] + splits["poison_val"]

    def features(rows: list[dict[str, Any]]) -> list[str]:
        return [f"{row['prompt']} [SEP] {row['response']}" for row in rows]

    def labels(rows: list[dict[str, Any]]) -> np.ndarray:
        return np.array(
            [1 if row["condition"] == "poison" else 0 for row in rows], dtype=int
        )

    vectorizer = HashingVectorizer(n_features=2**16, alternate_sign=False, norm="l2")
    clf = SGDClassifier(loss="log_loss", alpha=1e-5, random_state=13)

    x_train_text = features(train_rows)
    y_train = labels(train_rows)
    order = np.arange(len(train_rows))
    np.random.default_rng(13).shuffle(order)

    step_rows: list[dict[str, Any]] = []
    prev_coef = None
    for step, start in enumerate(range(0, len(order), batch_size), start=1):
        batch_idx = order[start : start + batch_size]
        xb = vectorizer.transform([x_train_text[i] for i in batch_idx])
        yb = y_train[batch_idx]
        clf.partial_fit(xb, yb, classes=np.array([0, 1]))
        coef = clf.coef_.copy()
        update_norm = (
            float(np.linalg.norm(coef - prev_coef))
            if prev_coef is not None
            else float(np.linalg.norm(coef))
        )
        prev_coef = coef
        proba = clf.predict_proba(xb)[:, 1]
        eps = 1e-12
        batch_loss = float(
            -np.mean(yb * np.log(proba + eps) + (1 - yb) * np.log(1 - proba + eps))
        )
        step_rows.append(
            {
                "step": step,
                "batch_size": int(len(batch_idx)),
                "batch_poison_rate": float(np.mean(yb)),
                "proxy_loss": batch_loss,
                "proxy_update_norm": update_norm,
                "proxy_weight_norm": float(np.linalg.norm(coef)),
            }
        )

    x_val = vectorizer.transform(features(val_rows))
    y_val = labels(val_rows)
    val_proba = clf.predict_proba(x_val)[:, 1]
    val_pred = (val_proba >= 0.5).astype(int)
    return {
        "diagnostic_type": "sklearn_hashing_sgd_proxy_not_lora",
        "steps": step_rows,
        "validation": {
            "accuracy": float(accuracy_score(y_val, val_pred)),
            "roc_auc": float(roc_auc_score(y_val, val_proba)),
            "average_precision": float(average_precision_score(y_val, val_proba)),
            "n_val": int(len(y_val)),
        },
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    val = summary["proxy_provenance"]["validation"]
    lines = [
        "# AI Supply Chain LoRA Provenance Scaffold",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        "Status: **UNBLOCKED FOR CLOUD PROVENANCE RUN**. PoisonBench is converted into clean-vs-poisoned SFT-style splits, and a LoRA provenance run spec is now available. The local diagnostic is a cheap proxy only; it is not the paper claim.",
        "",
        "## Artifacts",
        "",
    ]
    for name, artifact in summary["artifacts"].items():
        lines.append(f"- `{name}`: `{artifact}`")
    lines.extend(
        [
            "",
            "## Split Summary",
            "",
            f"- Clean train: `{summary['split_counts']['clean_train']}`",
            f"- Clean validation: `{summary['split_counts']['clean_val']}`",
            f"- Poison train: `{summary['split_counts']['poison_train']}`",
            f"- Poison validation: `{summary['split_counts']['poison_val']}`",
            "",
            "## Proxy Diagnostic",
            "",
            f"- Type: `{summary['proxy_provenance']['diagnostic_type']}`",
            f"- Validation accuracy: `{val['accuracy']:.4f}`",
            f"- Validation ROC-AUC: `{val['roc_auc']:.4f}`",
            f"- Validation AP: `{val['average_precision']:.4f}`",
            "",
            "## Next Gate",
            "",
            "Run the cloud LoRA job from `lora_training_spec.json` and log per-step loss, gradient norm, update norm, adapter norm, and validation behavior for clean and poisoned conditions. Only after those traces exist should this experiment be evaluated as a Praxis candidate.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--poisonbench",
        type=Path,
        default=Path("tmp") / "poisonbench_train_0000.parquet",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "ai-supply-chain-lora-provenance-scaffold-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "ai_supply_chain_training_provenance"
        / "LORA_PROVENANCE_SCAFFOLD_20260509.md",
    )
    parser.add_argument("--n-train", type=int, default=1000)
    parser.add_argument("--n-val", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    df = pd.read_parquet(args.poisonbench)
    splits = build_sft_splits(df, args.n_train, args.n_val, args.seed)
    proxy = run_proxy_provenance(splits, args.batch_size)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "clean_train": args.out_dir / "clean_train.jsonl",
        "clean_val": args.out_dir / "clean_val.jsonl",
        "poison_train": args.out_dir / "poison_train.jsonl",
        "poison_val": args.out_dir / "poison_val.jsonl",
        "proxy_provenance": args.out_dir / "proxy_provenance.json",
        "lora_training_spec": args.out_dir / "lora_training_spec.json",
        "summary": args.out_dir / "summary.json",
    }
    for key in ["clean_train", "clean_val", "poison_train", "poison_val"]:
        write_jsonl(artifacts[key], splits[key])
    artifacts["proxy_provenance"].write_text(
        json.dumps(proxy, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lora_spec = {
        "base_model_preferred": "meta-llama/Llama-3.2-3B-Instruct",
        "base_model_fallback": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "conditions": ["clean", "poison"],
        "train_files": {
            "clean": str(artifacts["clean_train"]),
            "poison": str(artifacts["poison_train"]),
        },
        "validation_files": {
            "clean": str(artifacts["clean_val"]),
            "poison": str(artifacts["poison_val"]),
        },
        "lora": {
            "r": 8,
            "alpha": 16,
            "dropout": 0.05,
            "target_modules": "q_proj,k_proj,v_proj,o_proj",
        },
        "training": {
            "max_steps": 150,
            "per_device_train_batch_size": 2,
            "gradient_accumulation_steps": 8,
            "learning_rate": 2e-4,
            "logging_steps": 1,
            "save_steps": 50,
        },
        "required_provenance_logs": [
            "step",
            "condition",
            "loss",
            "grad_norm",
            "update_norm",
            "adapter_norm",
            "validation_loss",
            "validation_behavior_score",
        ],
    }
    artifacts["lora_training_spec"].write_text(
        json.dumps(lora_spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "status": "unblocked_for_cloud_provenance_run",
        "poisonbench_rows_available": int(len(df)),
        "split_counts": {key: len(rows) for key, rows in splits.items()},
        "proxy_provenance": {
            "diagnostic_type": proxy["diagnostic_type"],
            "validation": proxy["validation"],
            "steps": len(proxy["steps"]),
        },
        "artifacts": {key: str(value) for key, value in artifacts.items()},
    }
    artifacts["summary"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(args.report, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
