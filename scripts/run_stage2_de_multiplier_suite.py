from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from imblearn.over_sampling import ADASYN
from sklearn.metrics import precision_recall_fscore_support, recall_score
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_two_stage_feature_subset_revision import (
    STAGE2_NAMES,
    build_end_to_end_outputs,
    build_feature_subsets,
    choose_threshold,
    compute_per_class_f1 as compute_full_per_class_f1,
    compute_recon_auc_scores,
    predict_probs,
    set_seed,
    train_stage1_mlp,
)


plt.style.use("dark_background")

FAMILY_DEFS = {
    "adasyn_weighted_ce": {
        "loss_name": "weighted_ce",
        "use_adasyn": True,
    },
    "adasyn_cb_focal": {
        "loss_name": "cb_focal",
        "use_adasyn": True,
    },
}


class ClassBalancedFocalLoss(nn.Module):
    def __init__(self, alpha: torch.Tensor | None, gamma: float = 2.0):
        super().__init__()
        self.gamma = float(gamma)
        if alpha is None:
            self.register_buffer("alpha", torch.empty(0))
        else:
            self.register_buffer("alpha", alpha.to(torch.float32))

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=1)
        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = log_pt.exp()
        focal_weight = torch.pow(1.0 - pt, self.gamma)
        if self.alpha.numel():
            focal_weight = focal_weight * self.alpha[targets]
        return (-focal_weight * log_pt).mean()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a fixed-Stage1 Stage 2 DE-multiplier suite on the trusted Unraveled "
            "support-floor split and evaluate both attack-only and end-to-end behavior."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor base config JSON.")
    parser.add_argument("--run-name", required=True, help="Output folder under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated seeds.")
    parser.add_argument("--candidate", default="recon_top30", help="Stage 1 feature-subset candidate.")
    parser.add_argument(
        "--de-multipliers",
        default="1.0,1.25,1.5,2.0,3.0",
        help="Comma-separated DE loss multipliers to sweep in Stage 2.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage reference raw results CSV.",
    )
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    return parser.parse_args()


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def parse_float_list(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("Expected at least one float value.")
    return values


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


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def targeted_adasyn_attack_only(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train.astype(np.int64), minlength=len(STAGE2_NAMES))
    majority_target = int(max(counts[1], counts[2]))
    strategy: dict[int, int] = {}
    for label in (0, 3):
        if int(counts[label]) >= majority_target:
            continue
        strategy[int(label)] = majority_target

    if not strategy:
        return x_train, y_train, {"applied": False, "reason": "targets_already_at_goal"}

    k_neighbors = min(int(counts[label]) - 1 for label in strategy)
    if k_neighbors < 1:
        return x_train, y_train, {"applied": False, "reason": "insufficient_neighbors"}

    sampler = ADASYN(
        sampling_strategy=strategy,
        random_state=random_seed,
        n_neighbors=min(5, k_neighbors),
    )
    x_resampled, y_resampled = sampler.fit_resample(x_train, y_train)
    return x_resampled, y_resampled, {
        "applied": True,
        "strategy": {STAGE2_NAMES[key]: int(value) for key, value in strategy.items()},
        "k_neighbors": int(min(5, k_neighbors)),
        "before_counts": {STAGE2_NAMES[index]: int(counts[index]) for index in range(len(STAGE2_NAMES))},
        "after_counts": {
            STAGE2_NAMES[index]: int(value)
            for index, value in enumerate(np.bincount(y_resampled, minlength=len(STAGE2_NAMES)))
        },
    }


def compute_attack_only_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(STAGE2_NAMES))),
        zero_division=0,
    )
    return {STAGE2_NAMES[index]: float(f1[index]) for index in range(len(STAGE2_NAMES))}


def predict_row_model(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    loader = DataLoader(v02.RowDataset(x, y), batch_size=batch_size, shuffle=False)
    model.eval()
    probs_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs, ys in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            probs_list.append(probs.cpu().numpy())
            labels_list.append(ys.numpy())
    return np.concatenate(labels_list), np.vstack(probs_list)


def instantiate_stage2_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(STAGE2_NAMES),
    )


def build_attack_only_loss(
    loss_name: str,
    labels: np.ndarray,
    device: torch.device,
    settings: dict[str, Any],
    stage_loss_multipliers: list[float],
) -> nn.Module:
    multipliers = torch.tensor(np.asarray(stage_loss_multipliers, dtype=np.float32), dtype=torch.float32).to(device)
    multipliers = multipliers / multipliers.mean().clamp_min(1e-8)

    if loss_name == "cb_focal":
        alpha = v03.compute_effective_class_weights(
            labels=labels,
            num_classes=len(STAGE2_NAMES),
            beta=float(settings.get("cb_beta", 0.999)),
        ).to(device)
        alpha = alpha * multipliers
        alpha = alpha / alpha.mean().clamp_min(1e-8)
        return ClassBalancedFocalLoss(alpha=alpha, gamma=float(settings.get("focal_gamma", 2.0)))

    weights = v02.compute_class_weights(labels, num_classes=len(STAGE2_NAMES)).to(device)
    weights = weights * multipliers
    weights = weights / weights.mean().clamp_min(1e-8)
    return nn.CrossEntropyLoss(weight=weights)


def train_stage2_model(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    mlp_params: dict[str, Any],
    base_settings: dict[str, Any],
    loss_name: str,
    stage_loss_multipliers: list[float],
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = instantiate_stage2_mlp(feature_count=int(train_x.shape[1]), params=mlp_params).to(device)
    train_sampler = v03.build_row_sampler(train_y, settings=base_settings)
    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(base_settings["tabular_batch_size"]),
        shuffle=train_sampler is None,
        sampler=train_sampler,
    )
    criterion = build_attack_only_loss(
        loss_name=loss_name,
        labels=train_y,
        device=device,
        settings=base_settings,
        stage_loss_multipliers=stage_loss_multipliers,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(mlp_params["lr"]),
        weight_decay=float(mlp_params["weight_decay"]),
    )

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(base_settings["train_epochs"]) + 1):
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

        _, val_probs = predict_row_model(
            model=model,
            x=val_x,
            y=val_y,
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        val_pred = np.argmax(val_probs, axis=1)
        val_metrics = v02.compute_metrics(val_y, val_pred, val_probs, STAGE2_NAMES)
        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": float(val_metrics["f1"]),
                "val_accuracy": float(val_metrics["accuracy"]),
            }
        )
        print(
            f"      Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | val_acc={val_metrics['accuracy']:.4f}"
        )

        if float(val_metrics["f1"]) > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= int(base_settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Stage 2 training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


def flatten_summary_columns(frame: pd.DataFrame) -> pd.DataFrame:
    flat = frame.copy()
    flat.columns = [
        f"{column}_{agg}" if agg else str(column)
        for column, agg in flat.columns.to_flat_index()
    ]
    return flat.reset_index()


def plot_end_to_end_tradeoff(summary_frame: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    for family, color in [("adasyn_weighted_ce", "#4ecdc4"), ("adasyn_cb_focal", "#ff6b6b")]:
        subset = summary_frame[summary_frame["family"] == family]
        ax.plot(subset["de_f1_mean_end"], subset["recon_f1_mean_end"], marker="o", label=family, color=color)
        for _, row in subset.iterrows():
            ax.annotate(f"de={row['de_multiplier']:.2f}", (row["de_f1_mean_end"], row["recon_f1_mean_end"]))
    ax.set_xlabel("End-to-End DE F1 Mean")
    ax.set_ylabel("End-to-End Recon F1 Mean")
    ax.set_title("Stage 2 DE Multiplier Tradeoff")
    ax.grid(True, alpha=0.2)
    ax.legend()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_end_to_end_macro(summary_frame: pd.DataFrame, output_path: Path) -> None:
    labels = [f"{row.family}\nde={row.de_multiplier:.2f}" for row in summary_frame.itertuples()]
    fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)
    ax.bar(
        labels,
        summary_frame["macro_f1_mean_end"],
        yerr=summary_frame["macro_f1_std_end"].fillna(0.0),
        capsize=4,
        color="#5dade2",
    )
    ax.set_ylabel("End-to-End Macro F1")
    ax.set_title("Stage 2 DE Multiplier End-to-End Macro F1")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    base_settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, base_settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds)
    de_multipliers = parse_float_list(args.de_multipliers)
    device = torch.device("cpu")
    mlp_params = v03.resolve_fixed_model_params(base_settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must define fixed_model_params for MLP.")

    v02.set_random_seed(int(base_settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=run_dir,
    )

    overall_importance = pd.read_csv(v02.resolve_path(repo_root, args.s6_feature_importance_csv))
    overall_importance = overall_importance[
        (overall_importance["dataset"] == "Unraveled") & (overall_importance["model"] == "MLP")
    ][["feature", "importance"]]
    recon_auc_df = compute_recon_auc_scores(train_df, feature_cols)
    candidates = build_feature_subsets(feature_cols, overall_importance, recon_auc_df)
    if str(args.candidate) not in candidates:
        raise ValueError(f"Unknown candidate: {args.candidate}")
    stage1_features = candidates[str(args.candidate)]

    train_x_stage1 = train_df[stage1_features].values.astype(np.float32)
    val_x_stage1 = val_df[stage1_features].values.astype(np.float32)
    test_x_stage1 = test_df[stage1_features].values.astype(np.float32)
    train_binary_y = (train_df["MultiLabel"].values != 0).astype(np.int64)
    val_binary_y = (val_df["MultiLabel"].values != 0).astype(np.int64)
    test_binary_y = (test_df["MultiLabel"].values != 0).astype(np.int64)
    val_original_y = val_df["MultiLabel"].values.astype(np.int64)
    test_original_y = test_df["MultiLabel"].values.astype(np.int64)

    full_val_x = val_df[feature_cols].values.astype(np.float32)
    full_test_x = test_df[feature_cols].values.astype(np.float32)

    attack_train_mask = train_df["MultiLabel"].values != 0
    attack_val_mask = val_df["MultiLabel"].values != 0
    attack_test_mask = test_df["MultiLabel"].values != 0
    train_x_stage2 = train_df.loc[attack_train_mask, feature_cols].values.astype(np.float32)
    val_x_stage2 = val_df.loc[attack_val_mask, feature_cols].values.astype(np.float32)
    test_x_stage2 = test_df.loc[attack_test_mask, feature_cols].values.astype(np.float32)
    train_y_stage2 = train_df.loc[attack_train_mask, "MultiLabel"].values.astype(np.int64) - 1
    val_y_stage2 = val_df.loc[attack_val_mask, "MultiLabel"].values.astype(np.int64) - 1
    test_y_stage2 = test_df.loc[attack_test_mask, "MultiLabel"].values.astype(np.int64) - 1

    reference_frame = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    reference_frame = reference_frame[reference_frame["variant"] == "adasyn_weighted_ce"].sort_values("seed")

    stage1_rows: list[dict[str, Any]] = []
    attack_rows: list[dict[str, Any]] = []
    end_rows: list[dict[str, Any]] = []
    stage1_cache: dict[int, dict[str, Any]] = {}

    for seed in seeds:
        print(f"\nTraining fixed Stage 1 for seed {seed}...")
        set_seed(seed)
        stage1_model = train_stage1_mlp(
            train_x=train_x_stage1,
            train_y=train_binary_y,
            val_x=val_x_stage1,
            val_y=val_binary_y,
            params=mlp_params,
            settings=base_settings,
            device=device,
        )
        val_stage1_probs = predict_probs(
            stage1_model,
            val_x_stage1,
            val_binary_y,
            int(base_settings["tabular_batch_size"]),
            device,
        )
        test_stage1_probs = predict_probs(
            stage1_model,
            test_x_stage1,
            test_binary_y,
            int(base_settings["tabular_batch_size"]),
            device,
        )
        threshold_row = choose_threshold(val_original_y, val_binary_y, val_stage1_probs)
        binary_pred = (test_stage1_probs[:, 1] >= float(threshold_row["threshold"])).astype(np.int64)
        _, _, binary_f1, _ = precision_recall_fscore_support(
            test_binary_y,
            binary_pred,
            labels=[0, 1],
            zero_division=0,
        )
        stage1_rows.append(
            {
                "seed": seed,
                "candidate": str(args.candidate),
                "threshold": float(threshold_row["threshold"]),
                "attack_recall": float(recall_score(test_binary_y, binary_pred, pos_label=1, zero_division=0)),
                "stage1_recon_attack_recall": float(binary_pred[test_original_y == 1].mean()),
                "stage1_benign_f1": float(binary_f1[0]),
            }
        )
        stage1_cache[seed] = {
            "threshold": float(threshold_row["threshold"]),
            "val_stage1_probs": val_stage1_probs,
            "test_stage1_probs": test_stage1_probs,
        }

    for family_name, family_def in FAMILY_DEFS.items():
        for de_multiplier in de_multipliers:
            variant_name = f"{family_name}_de{de_multiplier:.2f}".replace(".", "p")
            stage_loss_multipliers = [1.0, 1.0, 1.0, float(de_multiplier)]
            print(f"\nRunning Stage 2 family `{family_name}` with DE multiplier {de_multiplier:.2f}...")
            for seed in seeds:
                set_seed(seed)
                variant_train_x = train_x_stage2
                variant_train_y = train_y_stage2
                adasyn_summary = {"applied": False}
                if family_def["use_adasyn"]:
                    variant_train_x, variant_train_y, adasyn_summary = targeted_adasyn_attack_only(
                        x_train=train_x_stage2,
                        y_train=train_y_stage2,
                        random_seed=int(seed),
                    )

                model, val_metrics, history = train_stage2_model(
                    train_x=variant_train_x,
                    train_y=variant_train_y,
                    val_x=val_x_stage2,
                    val_y=val_y_stage2,
                    mlp_params=mlp_params,
                    base_settings=base_settings,
                    loss_name=str(family_def["loss_name"]),
                    stage_loss_multipliers=stage_loss_multipliers,
                    device=device,
                )

                y_attack_out, attack_probs = predict_row_model(
                    model=model,
                    x=test_x_stage2,
                    y=test_y_stage2,
                    batch_size=int(base_settings["tabular_batch_size"]),
                    device=device,
                )
                attack_pred = np.argmax(attack_probs, axis=1)
                attack_metrics = v02.compute_metrics(y_attack_out, attack_pred, attack_probs, STAGE2_NAMES)
                attack_per_class = compute_attack_only_per_class_f1(y_attack_out, attack_pred)
                attack_rows.append(
                    {
                        "variant": variant_name,
                        "family": family_name,
                        "de_multiplier": float(de_multiplier),
                        "seed": int(seed),
                        "accuracy": float(attack_metrics["accuracy"]),
                        "macro_f1": float(attack_metrics["f1"]),
                        "pr_auc": float(attack_metrics["pr_auc"]) if attack_metrics["pr_auc"] is not None else np.nan,
                        "recon_f1": float(attack_per_class["Reconnaissance"]),
                        "foothold_f1": float(attack_per_class["Establish Foothold"]),
                        "lm_f1": float(attack_per_class["Lateral Movement"]),
                        "de_f1": float(attack_per_class["Data Exfiltration"]),
                    }
                )

                full_val_probs = predict_probs(
                    model,
                    full_val_x,
                    np.zeros(len(full_val_x), dtype=np.int64),
                    int(base_settings["tabular_batch_size"]),
                    device,
                )
                full_test_probs = predict_probs(
                    model,
                    full_test_x,
                    np.zeros(len(full_test_x), dtype=np.int64),
                    int(base_settings["tabular_batch_size"]),
                    device,
                )
                end_val_pred, end_val_probs = build_end_to_end_outputs(
                    stage1_probs=stage1_cache[seed]["val_stage1_probs"],
                    stage2_probs=full_val_probs,
                    threshold=float(stage1_cache[seed]["threshold"]),
                )
                end_test_pred, end_test_probs = build_end_to_end_outputs(
                    stage1_probs=stage1_cache[seed]["test_stage1_probs"],
                    stage2_probs=full_test_probs,
                    threshold=float(stage1_cache[seed]["threshold"]),
                )
                end_val_metrics = v02.compute_metrics(val_original_y, end_val_pred, end_val_probs, v02.STAGE_NAMES)
                end_test_metrics = v02.compute_metrics(test_original_y, end_test_pred, end_test_probs, v02.STAGE_NAMES)
                end_test_per_class = compute_full_per_class_f1(test_original_y, end_test_pred)
                end_rows.append(
                    {
                        "variant": variant_name,
                        "family": family_name,
                        "de_multiplier": float(de_multiplier),
                        "seed": int(seed),
                        "threshold": float(stage1_cache[seed]["threshold"]),
                        "val_macro_f1": float(end_val_metrics["f1"]),
                        "accuracy": float(end_test_metrics["accuracy"]),
                        "macro_f1": float(end_test_metrics["f1"]),
                        "pr_auc": float(end_test_metrics["pr_auc"]) if end_test_metrics["pr_auc"] is not None else np.nan,
                        "benign_f1": float(end_test_per_class["Benign"]),
                        "recon_f1": float(end_test_per_class["Reconnaissance"]),
                        "foothold_f1": float(end_test_per_class["Establish Foothold"]),
                        "lm_f1": float(end_test_per_class["Lateral Movement"]),
                        "de_f1": float(end_test_per_class["Data Exfiltration"]),
                    }
                )

                artifact_dir = run_dir / "seed_runs" / variant_name / f"seed_{seed}"
                artifact_dir.mkdir(parents=True, exist_ok=True)
                torch.save(model.state_dict(), artifact_dir / "stage2_state_dict.pt")
                payload = {
                    "variant": variant_name,
                    "family": family_name,
                    "seed": int(seed),
                    "de_multiplier": float(de_multiplier),
                    "stage_loss_multipliers": stage_loss_multipliers,
                    "adasyn_summary": adasyn_summary,
                    "val_metrics_attack_only": val_metrics,
                    "history": history,
                    "attack_only_test_metrics": attack_metrics,
                    "end_to_end_test_metrics": end_test_metrics,
                    "end_to_end_test_per_class_f1": end_test_per_class,
                }
                write_json(artifact_dir / "results.json", payload)

    stage1_frame = pd.DataFrame(stage1_rows).sort_values("seed").reset_index(drop=True)
    attack_frame = pd.DataFrame(attack_rows).sort_values(["family", "de_multiplier", "seed"]).reset_index(drop=True)
    end_frame = pd.DataFrame(end_rows).sort_values(["family", "de_multiplier", "seed"]).reset_index(drop=True)
    stage1_frame.to_csv(run_dir / "stage1_fixed_raw.csv", index=False)
    attack_frame.to_csv(run_dir / "stage2_attack_only_raw.csv", index=False)
    end_frame.to_csv(run_dir / "end_to_end_raw.csv", index=False)

    attack_summary = flatten_summary_columns(
        attack_frame.groupby(["family", "de_multiplier"]).agg(
            {
                "accuracy": ["mean", "std"],
                "macro_f1": ["mean", "std"],
                "pr_auc": ["mean", "std"],
                "recon_f1": ["mean", "std"],
                "de_f1": ["mean", "std"],
            }
        )
    )
    end_summary = flatten_summary_columns(
        end_frame.groupby(["family", "de_multiplier"]).agg(
            {
                "accuracy": ["mean", "std"],
                "macro_f1": ["mean", "std"],
                "pr_auc": ["mean", "std"],
                "recon_f1": ["mean", "std"],
                "de_f1": ["mean", "std"],
            }
        )
    )
    summary_frame = attack_summary.merge(end_summary, on=["family", "de_multiplier"], suffixes=("_attack", "_end"))
    summary_frame = summary_frame.sort_values(["macro_f1_mean_end", "de_f1_mean_end"], ascending=[False, False]).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    delta_rows: list[dict[str, Any]] = []
    for (family, de_multiplier), frame in end_frame.groupby(["family", "de_multiplier"]):
        merged = frame.merge(
            reference_frame[["seed", "accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]],
            on="seed",
            suffixes=("_cascade", "_single"),
        )
        delta_rows.append(
            {
                "family": family,
                "de_multiplier": float(de_multiplier),
                "accuracy_delta_mean": float((merged["accuracy_cascade"] - merged["accuracy_single"]).mean()),
                "macro_f1_delta_mean": float((merged["macro_f1_cascade"] - merged["macro_f1_single"]).mean()),
                "pr_auc_delta_mean": float((merged["pr_auc_cascade"] - merged["pr_auc_single"]).mean()),
                "recon_f1_delta_mean": float((merged["recon_f1_cascade"] - merged["recon_f1_single"]).mean()),
                "de_f1_delta_mean": float((merged["de_f1_cascade"] - merged["de_f1_single"]).mean()),
            }
        )
    delta_frame = pd.DataFrame(delta_rows).sort_values(["macro_f1_delta_mean", "de_f1_delta_mean"], ascending=[False, False]).reset_index(drop=True)
    delta_frame.to_csv(run_dir / "delta_vs_single_stage.csv", index=False)

    plot_end_to_end_tradeoff(summary_frame, run_dir / "end_to_end_tradeoff.png")
    plot_end_to_end_macro(summary_frame, run_dir / "end_to_end_macro.png")

    best_macro_row = summary_frame.sort_values(["macro_f1_mean_end", "de_f1_mean_end"], ascending=[False, False]).iloc[0].to_dict()
    best_de_row = summary_frame.sort_values(["de_f1_mean_end", "macro_f1_mean_end"], ascending=[False, False]).iloc[0].to_dict()
    decision = {
        "best_macro_variant": best_macro_row,
        "best_de_variant": best_de_row,
        "any_variant_holds_de_with_macro_gain": bool(
            any(
                (delta_frame["macro_f1_delta_mean"] > 0.0)
                & (delta_frame["de_f1_delta_mean"] >= -0.10)
            )
        ),
    }

    summary_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "seeds": seeds,
        "candidate": str(args.candidate),
        "de_multipliers": de_multipliers,
        "cache_path": str(cache_path),
        "cache_metadata_path": str(cache_metadata_path),
        "preprocess_summary": preprocess_summary,
        "stage1_summary": stage1_frame.to_dict(orient="records"),
        "summary_rows": summary_frame.to_dict(orient="records"),
        "delta_rows": delta_frame.to_dict(orient="records"),
        "decision": decision,
    }
    write_json(run_dir / "summary.json", summary_payload)

    report_lines = [
        "# Stage 2 DE Multiplier Suite",
        "",
        f"Config: `{config_path.name}`",
        f"Candidate: `{args.candidate}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        f"DE multipliers: `{', '.join(f'{value:.2f}' for value in de_multipliers)}`",
        "",
        "## End-to-End Summary",
        "",
        render_markdown_table(
            summary_frame[
                [
                    "family",
                    "de_multiplier",
                    "macro_f1_mean_end",
                    "macro_f1_std_end",
                    "recon_f1_mean_end",
                    "recon_f1_std_end",
                    "de_f1_mean_end",
                    "de_f1_std_end",
                    "pr_auc_mean_end",
                    "accuracy_mean_end",
                ]
            ]
        ),
        "",
        "## Delta Vs Single-Stage",
        "",
        render_markdown_table(delta_frame),
        "",
        "## Attack-Only Summary",
        "",
        render_markdown_table(
            summary_frame[
                [
                    "family",
                    "de_multiplier",
                    "macro_f1_mean_attack",
                    "recon_f1_mean_attack",
                    "de_f1_mean_attack",
                    "pr_auc_mean_attack",
                ]
            ]
        ),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Stage 1 summary: {run_dir / 'stage1_fixed_raw.csv'}")
    print(f"Attack-only raw: {run_dir / 'stage2_attack_only_raw.csv'}")
    print(f"End-to-end raw: {run_dir / 'end_to_end_raw.csv'}")
    print(f"Summary: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
