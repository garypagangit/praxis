from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a 3-seed Mamba weighted-CE experiment on the trusted support-floor split "
            "to test whether sequential context recovers Recon more reliably than the MLP."
        )
    )
    parser.add_argument("--config", required=True, help="Base support-floor config JSON.")
    parser.add_argument("--run-name", required=True, help="Output directory name under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated training seeds.")
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="MLP reference raw seed results for comparison.",
    )
    return parser.parse_args()


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def render_markdown_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_float_dtype(data[column]):
            data[column] = data[column].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()]
    return "\n".join([header, divider, *rows])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def set_seed(seed: int) -> None:
    v02.set_random_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def predict_sequence_probs(
    model: torch.nn.Module,
    chunks: list[tuple[np.ndarray, np.ndarray]],
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    loader = DataLoader(
        v02.SequenceChunkDataset(chunks),
        batch_size=batch_size,
        shuffle=False,
        collate_fn=v02.collate_sequence_chunks,
    )
    labels_list: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for xs, ys, mask in loader:
            xs = xs.to(device)
            mask = mask.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=-1)
            flat_mask = mask.view(-1)
            flat_probs = probs.view(-1, probs.shape[-1])[flat_mask]
            flat_labels = ys.view(-1)[flat_mask]
            labels_list.append(flat_labels.cpu().numpy())
            probs_list.append(flat_probs.cpu().numpy())
    return np.concatenate(labels_list), np.vstack(probs_list)


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    config_path = v02.resolve_path(repo_root, args.config)
    output_dir = (repo_root / "runs" / args.run_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    settings["loss_name"] = "weighted_ce"
    device = torch.device("cpu")
    seeds = parse_seeds(args.seeds)

    mamba_params = v03.resolve_fixed_model_params(settings, "Mamba")
    if mamba_params is None:
        raise ValueError("Base config must include fixed Mamba parameters.")

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=output_dir,
    )
    train_chunks = v02.build_sequence_chunks(
        train_df,
        feature_cols=feature_cols,
        sequence_length=int(settings["sequence_length"]),
        min_sequence_length=int(settings["min_sequence_length"]),
    )
    val_chunks = v02.build_sequence_chunks(
        val_df,
        feature_cols=feature_cols,
        sequence_length=int(settings["sequence_length"]),
        min_sequence_length=int(settings["min_sequence_length"]),
    )
    test_chunks = v02.build_sequence_chunks(
        test_df,
        feature_cols=feature_cols,
        sequence_length=int(settings["sequence_length"]),
        min_sequence_length=int(settings["min_sequence_length"]),
    )
    train_y = train_df["MultiLabel"].values.astype(np.int64)

    train_loader = DataLoader(
        v02.SequenceChunkDataset(train_chunks),
        batch_size=int(settings["sequence_batch_size"]),
        shuffle=True,
        collate_fn=v02.collate_sequence_chunks,
    )
    val_loader = DataLoader(
        v02.SequenceChunkDataset(val_chunks),
        batch_size=int(settings["sequence_batch_size"]),
        shuffle=False,
        collate_fn=v02.collate_sequence_chunks,
    )

    raw_rows: list[dict[str, Any]] = []
    seed_payloads: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"\nRunning Mamba weighted-CE seed {seed}...")
        set_seed(seed)
        model = v02.MambaStageClassifier(
            num_features=len(feature_cols),
            d_model=int(mamba_params["d_model"]),
            n_layers=int(mamba_params["n_layers"]),
            d_state=int(mamba_params["d_state"]),
            d_conv=int(mamba_params["d_conv"]),
            dropout=float(mamba_params["dropout"]),
            num_classes=len(v02.STAGE_NAMES),
        )
        model, val_metrics, history = v03.train_sequence_model_v03(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            train_labels=train_y,
            device=device,
            settings=settings,
            lr=float(mamba_params["lr"]),
            weight_decay=float(mamba_params["weight_decay"]),
        )
        test_y, test_probs = predict_sequence_probs(
            model=model,
            chunks=test_chunks,
            batch_size=int(settings["sequence_batch_size"]),
            device=device,
        )
        test_pred = np.argmax(test_probs, axis=1)
        test_metrics = v02.compute_metrics(test_y, test_pred, test_probs, v02.STAGE_NAMES)
        per_class = compute_per_class_f1(test_y, test_pred)

        raw_rows.append(
            {
                "seed": int(seed),
                "accuracy": float(test_metrics["accuracy"]),
                "macro_f1": float(test_metrics["f1"]),
                "pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                "benign_f1": float(per_class["Benign"]),
                "recon_f1": float(per_class["Reconnaissance"]),
                "foothold_f1": float(per_class["Establish Foothold"]),
                "lm_f1": float(per_class["Lateral Movement"]),
                "de_f1": float(per_class["Data Exfiltration"]),
            }
        )

        seed_dir = output_dir / "seed_runs" / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), seed_dir / "mamba_state_dict.pt")
        payload = {
            "seed": int(seed),
            "best_params": mamba_params,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "per_class_test_f1": per_class,
            "history": history,
        }
        write_json(seed_dir / "results.json", payload)
        seed_payloads.append(payload)

    raw_frame = pd.DataFrame(raw_rows).sort_values("seed").reset_index(drop=True)
    raw_frame.to_csv(output_dir / "raw_seed_results.csv", index=False)

    summary_frame = pd.DataFrame(
        [
            {
                "family": "Mamba",
                "variant": "weighted_ce_multi_seed",
                "accuracy_mean": float(raw_frame["accuracy"].mean()),
                "accuracy_std": float(raw_frame["accuracy"].std(ddof=1)),
                "macro_f1_mean": float(raw_frame["macro_f1"].mean()),
                "macro_f1_std": float(raw_frame["macro_f1"].std(ddof=1)),
                "pr_auc_mean": float(raw_frame["pr_auc"].mean()),
                "pr_auc_std": float(raw_frame["pr_auc"].std(ddof=1)),
                "recon_f1_mean": float(raw_frame["recon_f1"].mean()),
                "recon_f1_std": float(raw_frame["recon_f1"].std(ddof=1)),
                "de_f1_mean": float(raw_frame["de_f1"].mean()),
                "de_f1_std": float(raw_frame["de_f1"].std(ddof=1)),
            }
        ]
    )
    summary_frame.to_csv(output_dir / "summary.csv", index=False)

    mlp_reference = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    mlp_reference = mlp_reference[mlp_reference["variant"] == "adasyn_weighted_ce"].sort_values("seed")
    delta_frame = pd.DataFrame(
        [
            {
                "comparison": "mamba_weighted_ce_minus_mlp_adasyn_weighted_ce",
                "accuracy_delta_mean": float(raw_frame["accuracy"].mean() - mlp_reference["accuracy"].mean()),
                "macro_f1_delta_mean": float(raw_frame["macro_f1"].mean() - mlp_reference["macro_f1"].mean()),
                "pr_auc_delta_mean": float(raw_frame["pr_auc"].mean() - mlp_reference["pr_auc"].mean()),
                "recon_f1_delta_mean": float(raw_frame["recon_f1"].mean() - mlp_reference["recon_f1"].mean()),
                "de_f1_delta_mean": float(raw_frame["de_f1"].mean() - mlp_reference["de_f1"].mean()),
            }
        ]
    )
    delta_frame.to_csv(output_dir / "delta_vs_mlp_reference.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    metrics = ["macro_f1", "recon_f1", "de_f1"]
    means = [float(raw_frame[metric].mean()) for metric in metrics]
    stds = [float(raw_frame[metric].std(ddof=1)) for metric in metrics]
    ax.bar(metrics, means, yerr=stds, capsize=4, color=["#5dade2", "#f5b041", "#ec7063"])
    ax.set_title("Mamba Weighted-CE Metrics Across Seeds")
    ax.grid(True, axis="y", alpha=0.2)
    (output_dir / "mamba_weighted_ce_metrics.png").parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "mamba_weighted_ce_metrics.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    decision = {
        "recon_beats_mlp_reference": bool(float(raw_frame["recon_f1"].mean()) > float(mlp_reference["recon_f1"].mean())),
        "macro_beats_mlp_reference": bool(float(raw_frame["macro_f1"].mean()) > float(mlp_reference["macro_f1"].mean())),
        "de_holds_reasonably": bool(float(raw_frame["de_f1"].mean()) >= 0.10),
    }

    write_json(
        output_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "seeds": seeds,
            "preprocess_summary": preprocess_summary,
            "mamba_params": mamba_params,
            "summary_rows": summary_frame.to_dict(orient="records"),
            "delta_vs_mlp_reference": delta_frame.to_dict(orient="records"),
            "decision": decision,
            "seed_payloads": seed_payloads,
        },
    )

    report_lines = [
        "# Mamba Weighted-CE Multi-Seed Report",
        "",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Delta Vs MLP Reference",
        "",
        render_markdown_table(delta_frame),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Raw seed results: {output_dir / 'raw_seed_results.csv'}")
    print(f"Summary: {output_dir / 'summary.csv'}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
