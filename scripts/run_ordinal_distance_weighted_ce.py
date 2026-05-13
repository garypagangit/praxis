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
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import precision_recall_fscore_support
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")


class DistanceWeightedCELoss(nn.Module):
    def __init__(self, num_classes: int, alpha: float = 1.0):
        super().__init__()
        self.num_classes = int(num_classes)
        self.alpha = float(alpha)
        class_positions = torch.arange(self.num_classes, dtype=torch.float32)
        self.register_buffer("class_positions", class_positions)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.ndim != 2:
            raise ValueError("DistanceWeightedCELoss expects [batch, classes] logits.")
        target_positions = targets.to(logits.device, dtype=torch.float32).unsqueeze(1)
        distances = torch.abs(self.class_positions.to(logits.device).unsqueeze(0) - target_positions)
        soft_targets = torch.exp(-self.alpha * distances)
        soft_targets = soft_targets / torch.clamp(soft_targets.sum(dim=1, keepdim=True), min=1e-12)
        log_probs = F.log_softmax(logits, dim=1)
        return -(soft_targets * log_probs).sum(dim=1).mean()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a 3-seed MLP experiment with ordinal distance-weighted cross-entropy "
            "on the trusted support-floor split."
        )
    )
    parser.add_argument("--config", required=True, help="Base support-floor config JSON.")
    parser.add_argument("--run-name", required=True, help="Output directory name under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated training seeds.")
    parser.add_argument(
        "--distance-alpha",
        type=float,
        default=1.0,
        help="Distance decay factor for the ordinal soft targets.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="MLP ablation raw seed results for comparison.",
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


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def train_ordinal_mlp(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    params: dict[str, Any],
    settings: dict[str, Any],
    device: torch.device,
    distance_alpha: float,
) -> tuple[torch.nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = v02.MLPStageClassifier(
        num_features=int(train_x.shape[1]),
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    ).to(device)
    criterion = DistanceWeightedCELoss(num_classes=len(v02.STAGE_NAMES), alpha=distance_alpha)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(params["lr"]),
        weight_decay=float(params["weight_decay"]),
    )
    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=True,
    )

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(settings["train_epochs"]) + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0
        for xs, ys in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits, ys)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += float(loss.item()) * int(ys.numel())
            total_examples += int(ys.numel())

        val_probs = predict_probs(model, val_x, val_y, int(settings["tabular_batch_size"]), device)
        val_pred = np.argmax(val_probs, axis=1)
        val_metrics = v02.compute_metrics(val_y, val_pred, val_probs, v02.STAGE_NAMES)
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(total_examples, 1),
                "val_f1": float(val_metrics["f1"]),
                "val_accuracy": float(val_metrics["accuracy"]),
            }
        )

        if float(val_metrics["f1"]) > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Ordinal training completed without a best checkpoint.")
    model.load_state_dict(best_state)
    return model, best_metrics, history


def predict_probs(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = DataLoader(v02.RowDataset(x, y), batch_size=batch_size, shuffle=False)
    probs_list: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for xs, _ in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            probs_list.append(probs.cpu().numpy())
    return np.vstack(probs_list)


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    config_path = v02.resolve_path(repo_root, args.config)
    output_dir = (repo_root / "runs" / args.run_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    device = torch.device("cpu")
    seeds = parse_seeds(args.seeds)
    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must include fixed MLP parameters.")

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=output_dir,
    )
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    raw_rows: list[dict[str, Any]] = []
    seed_payloads: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"\nRunning ordinal MLP seed {seed}...")
        set_seed(seed)
        model, val_metrics, history = train_ordinal_mlp(
            train_x=train_x,
            train_y=train_y,
            val_x=val_x,
            val_y=val_y,
            params=mlp_params,
            settings=settings,
            device=device,
            distance_alpha=float(args.distance_alpha),
        )
        test_probs = predict_probs(model, test_x, test_y, int(settings["tabular_batch_size"]), device)
        test_pred = np.argmax(test_probs, axis=1)
        test_metrics = v02.compute_metrics(test_y, test_pred, test_probs, v02.STAGE_NAMES)
        per_class = compute_per_class_f1(test_y, test_pred)
        stage_mae = float(np.mean(np.abs(test_pred.astype(np.float64) - test_y.astype(np.float64))))

        raw_rows.append(
            {
                "seed": int(seed),
                "accuracy": float(test_metrics["accuracy"]),
                "macro_f1": float(test_metrics["f1"]),
                "pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                "stage_mae": stage_mae,
                "benign_f1": float(per_class["Benign"]),
                "recon_f1": float(per_class["Reconnaissance"]),
                "foothold_f1": float(per_class["Establish Foothold"]),
                "lm_f1": float(per_class["Lateral Movement"]),
                "de_f1": float(per_class["Data Exfiltration"]),
            }
        )

        seed_dir = output_dir / "seed_runs" / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), seed_dir / "mlp_state_dict.pt")
        payload = {
            "seed": int(seed),
            "distance_alpha": float(args.distance_alpha),
            "best_params": mlp_params,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "per_class_test_f1": per_class,
            "stage_mae": stage_mae,
            "history": history,
        }
        write_json(seed_dir / "results.json", payload)
        seed_payloads.append(payload)

    raw_frame = pd.DataFrame(raw_rows).sort_values("seed").reset_index(drop=True)
    raw_frame.to_csv(output_dir / "raw_seed_results.csv", index=False)

    summary_frame = pd.DataFrame(
        [
            {
                "family": "MLP",
                "variant": "ordinal_distance_weighted_ce",
                "accuracy_mean": float(raw_frame["accuracy"].mean()),
                "accuracy_std": float(raw_frame["accuracy"].std(ddof=1)),
                "macro_f1_mean": float(raw_frame["macro_f1"].mean()),
                "macro_f1_std": float(raw_frame["macro_f1"].std(ddof=1)),
                "pr_auc_mean": float(raw_frame["pr_auc"].mean()),
                "pr_auc_std": float(raw_frame["pr_auc"].std(ddof=1)),
                "stage_mae_mean": float(raw_frame["stage_mae"].mean()),
                "stage_mae_std": float(raw_frame["stage_mae"].std(ddof=1)),
                "recon_f1_mean": float(raw_frame["recon_f1"].mean()),
                "recon_f1_std": float(raw_frame["recon_f1"].std(ddof=1)),
                "de_f1_mean": float(raw_frame["de_f1"].mean()),
                "de_f1_std": float(raw_frame["de_f1"].std(ddof=1)),
            }
        ]
    )
    summary_frame.to_csv(output_dir / "summary.csv", index=False)

    reference_frame = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    mlp_best = reference_frame[reference_frame["variant"] == "adasyn_weighted_ce"].sort_values("seed")
    mlp_weighted = reference_frame[reference_frame["variant"] == "weighted_ce"].sort_values("seed")
    delta_frame = pd.DataFrame(
        [
            {
                "comparison": "ordinal_minus_mlp_adasyn_weighted_ce",
                "accuracy_delta_mean": float(raw_frame["accuracy"].mean() - mlp_best["accuracy"].mean()),
                "macro_f1_delta_mean": float(raw_frame["macro_f1"].mean() - mlp_best["macro_f1"].mean()),
                "pr_auc_delta_mean": float(raw_frame["pr_auc"].mean() - mlp_best["pr_auc"].mean()),
                "recon_f1_delta_mean": float(raw_frame["recon_f1"].mean() - mlp_best["recon_f1"].mean()),
                "de_f1_delta_mean": float(raw_frame["de_f1"].mean() - mlp_best["de_f1"].mean()),
            },
            {
                "comparison": "ordinal_minus_mlp_weighted_ce",
                "accuracy_delta_mean": float(raw_frame["accuracy"].mean() - mlp_weighted["accuracy"].mean()),
                "macro_f1_delta_mean": float(raw_frame["macro_f1"].mean() - mlp_weighted["macro_f1"].mean()),
                "pr_auc_delta_mean": float(raw_frame["pr_auc"].mean() - mlp_weighted["pr_auc"].mean()),
                "recon_f1_delta_mean": float(raw_frame["recon_f1"].mean() - mlp_weighted["recon_f1"].mean()),
                "de_f1_delta_mean": float(raw_frame["de_f1"].mean() - mlp_weighted["de_f1"].mean()),
            },
        ]
    )
    delta_frame.to_csv(output_dir / "delta_vs_references.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    metrics = ["macro_f1", "recon_f1", "de_f1", "stage_mae"]
    means = [float(raw_frame[metric].mean()) for metric in metrics]
    stds = [float(raw_frame[metric].std(ddof=1)) for metric in metrics]
    ax.bar(metrics, means, yerr=stds, capsize=4, color=["#5dade2", "#f5b041", "#ec7063", "#58d68d"])
    ax.set_title("Ordinal Distance-Weighted CE Metrics")
    ax.grid(True, axis="y", alpha=0.2)
    fig.savefig(output_dir / "ordinal_metrics.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    decision = {
        "beats_mlp_weighted_ce_macro": bool(float(raw_frame["macro_f1"].mean()) > float(mlp_weighted["macro_f1"].mean())),
        "beats_mlp_weighted_ce_recon": bool(float(raw_frame["recon_f1"].mean()) > float(mlp_weighted["recon_f1"].mean())),
        "beats_mlp_best_macro": bool(float(raw_frame["macro_f1"].mean()) > float(mlp_best["macro_f1"].mean())),
    }

    write_json(
        output_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "seeds": seeds,
            "distance_alpha": float(args.distance_alpha),
            "preprocess_summary": preprocess_summary,
            "summary_rows": summary_frame.to_dict(orient="records"),
            "delta_rows": delta_frame.to_dict(orient="records"),
            "decision": decision,
            "seed_payloads": seed_payloads,
        },
    )

    report_lines = [
        "# Ordinal Distance-Weighted CE Report",
        "",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        f"Distance alpha: `{float(args.distance_alpha):.2f}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Delta Vs References",
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
