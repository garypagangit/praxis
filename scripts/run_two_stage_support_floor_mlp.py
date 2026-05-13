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
from imblearn.over_sampling import ADASYN
from sklearn.metrics import precision_recall_fscore_support, recall_score
from torch.utils.data import DataLoader, Dataset

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")

STAGE1_NAMES = ["Benign", "Attack"]
STAGE2_NAMES = v02.STAGE_NAMES[1:]


class FeatureDataset(Dataset):
    def __init__(self, x: np.ndarray):
        self.x = torch.from_numpy(x.astype(np.float32))

    def __len__(self) -> int:
        return int(self.x.shape[0])

    def __getitem__(self, index: int) -> torch.Tensor:
        return self.x[index]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a two-stage support-floor MLP pipeline on Unraveled and compare it "
            "against the best single-stage MLP baseline."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor base config JSON.")
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output folder name to create under the config's output_dir.",
    )
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated training seeds.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Raw single-stage seed results CSV for apples-to-apples comparison.",
    )
    parser.add_argument(
        "--reference-variant",
        default="adasyn_weighted_ce",
        help="Variant name inside the reference CSV to compare against.",
    )
    parser.add_argument(
        "--stage1-threshold",
        type=float,
        default=0.5,
        help="Attack probability threshold for Stage 1 routing.",
    )
    parser.add_argument(
        "--stage1-oversampler",
        choices=["none", "adasyn"],
        default="none",
        help="Optional Stage 1 binary oversampler.",
    )
    parser.add_argument(
        "--stage1-adasyn-target-ratio",
        type=float,
        default=1.0,
        help="Target attack/benign ratio for Stage 1 ADASYN oversampling.",
    )
    return parser.parse_args()


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def render_markdown_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_float_dtype(data[column]):
            data[column] = data[column].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()]
    return "\n".join([header, divider, *rows])


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def set_seed(seed: int) -> None:
    v02.set_random_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def compute_class_weights(labels: np.ndarray, num_classes: int) -> torch.Tensor:
    counts = np.bincount(labels.astype(np.int64), minlength=num_classes)
    counts = np.maximum(counts, 1)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    weights = np.clip(weights, 0.5, 8.0).astype(np.float32)
    return torch.tensor(weights, dtype=torch.float32)


def predict_probs(
    model: nn.Module,
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = DataLoader(
        FeatureDataset(x),
        batch_size=batch_size,
        shuffle=False,
    )
    model.eval()
    probs_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            probs_list.append(probs.cpu().numpy())
    return np.vstack(probs_list)


def evaluate_multiclass(
    y_true: np.ndarray,
    probs: np.ndarray,
    class_names: list[str],
    y_pred: np.ndarray | None = None,
) -> tuple[dict[str, Any], dict[str, float]]:
    if y_pred is None:
        y_pred = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y_true, y_pred, probs, class_names)
    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        zero_division=0,
    )
    per_class = {class_names[index]: float(f1[index]) for index in range(len(class_names))}
    return metrics, per_class


def train_mlp_generic(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    class_names: list[str],
    mlp_params: dict[str, Any],
    settings: dict[str, Any],
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = v02.MLPStageClassifier(
        num_features=int(train_x.shape[1]),
        hidden_dim=int(mlp_params["hidden_dim"]),
        num_layers=int(mlp_params["num_layers"]),
        dropout=float(mlp_params["dropout"]),
        num_classes=len(class_names),
    ).to(device)

    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=True,
    )
    criterion = nn.CrossEntropyLoss(
        weight=compute_class_weights(train_y, num_classes=len(class_names)).to(device)
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

        val_probs = predict_probs(
            model=model,
            x=val_x,
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )
        val_metrics, _ = evaluate_multiclass(val_y, val_probs, class_names)
        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": val_metrics["f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        print(
            f"    Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | val_acc={val_metrics['accuracy']:.4f}"
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
        raise RuntimeError("MLP training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


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
        return x_train, y_train, {"applied": False, "reason": "targets_already_at_or_above_goal"}

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


def oversample_stage1_binary_attack(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
    target_ratio: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train.astype(np.int64), minlength=2)
    benign_count = int(counts[0])
    attack_count = int(counts[1])

    if attack_count == 0 or benign_count == 0:
        return x_train, y_train, {"applied": False, "reason": "missing_binary_class"}

    target_attack = int(round(max(min(target_ratio, 1.0), 0.0) * benign_count))
    target_attack = max(target_attack, attack_count)
    if target_attack <= attack_count:
        return x_train, y_train, {"applied": False, "reason": "target_not_above_current"}

    k_neighbors = attack_count - 1
    if k_neighbors < 1:
        return x_train, y_train, {"applied": False, "reason": "insufficient_neighbors"}

    sampler = ADASYN(
        sampling_strategy={1: target_attack},
        random_state=random_seed,
        n_neighbors=min(5, k_neighbors),
    )
    x_resampled, y_resampled = sampler.fit_resample(x_train, y_train)
    after_counts = np.bincount(y_resampled.astype(np.int64), minlength=2)
    return x_resampled, y_resampled, {
        "applied": True,
        "target_ratio": float(target_ratio),
        "target_attack": int(target_attack),
        "k_neighbors": int(min(5, k_neighbors)),
        "before_counts": {
            STAGE1_NAMES[index]: int(counts[index]) for index in range(len(STAGE1_NAMES))
        },
        "after_counts": {
            STAGE1_NAMES[index]: int(after_counts[index]) for index in range(len(STAGE1_NAMES))
        },
    }


def compute_stage1_summary(
    original_test_labels: np.ndarray,
    binary_true: np.ndarray,
    binary_probs: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    attack_probs = binary_probs[:, 1]
    binary_pred = (attack_probs >= threshold).astype(np.int64)
    metrics, per_class = evaluate_multiclass(binary_true, binary_probs, STAGE1_NAMES, y_pred=binary_pred)

    attack_recall_by_stage = {}
    for stage_index, stage_name in enumerate(v02.STAGE_NAMES[1:], start=1):
        mask = original_test_labels == stage_index
        if int(mask.sum()) == 0:
            attack_recall_by_stage[stage_name] = float("nan")
            continue
        attack_recall_by_stage[stage_name] = float((binary_pred[mask] == 1).mean())

    summary = {
        "metrics": metrics,
        "per_class_f1": per_class,
        "attack_recall": float(recall_score(binary_true, binary_pred, pos_label=1, zero_division=0)),
        "benign_f1": float(per_class["Benign"]),
        "attack_recall_by_true_stage": attack_recall_by_stage,
        "recon_attack_recall": float(attack_recall_by_stage[v02.STAGE_NAMES[1]]),
        "binary_confusion_matrix": metrics["confusion_matrix"],
    }
    return summary


def build_end_to_end_outputs(
    stage1_probs: np.ndarray,
    stage2_probs: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    attack_pred = stage1_probs[:, 1] >= threshold
    final_pred = np.zeros(stage1_probs.shape[0], dtype=np.int64)
    final_pred[attack_pred] = np.argmax(stage2_probs[attack_pred], axis=1) + 1

    final_probs = np.zeros((stage1_probs.shape[0], len(v02.STAGE_NAMES)), dtype=np.float32)
    final_probs[:, 0] = stage1_probs[:, 0]
    final_probs[:, 1:] = stage1_probs[:, 1:2] * stage2_probs
    return final_pred, final_probs


def plot_end_to_end_vs_single_stage(
    summary_frame: pd.DataFrame,
    output_path: Path,
) -> None:
    labels = summary_frame["pipeline"].tolist()
    metrics = ["macro_f1_mean", "recon_f1_mean", "de_f1_mean"]
    titles = ["Macro F1", "Recon F1", "DE F1"]
    colors = ["#4ecdc4", "#ffe66d", "#ff6b6b"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)
    for axis, metric, title, color in zip(axes, metrics, titles, colors):
        axis.bar(labels, summary_frame[metric], color=color)
        axis.set_title(title)
        axis.grid(True, axis="y", alpha=0.2)
        axis.tick_params(axis="x", rotation=15)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_stage1_attack_recall(stage1_rows: pd.DataFrame, output_path: Path) -> None:
    grouped = stage1_rows.groupby("seed").mean(numeric_only=True).reset_index()
    stages = ["recon_attack_recall", "foothold_attack_recall", "lm_attack_recall", "de_attack_recall"]
    labels = ["Recon", "Foothold", "LM", "DE"]
    mean_values = [float(stage1_rows[column].mean()) for column in stages]
    std_values = [float(stage1_rows[column].std(ddof=1)) if len(stage1_rows) > 1 else 0.0 for column in stages]

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.bar(labels, mean_values, yerr=std_values, capsize=4, color="#5dade2")
    ax.axhline(0.7, color="#ff6b6b", linestyle="--", linewidth=1, label="0.7 risk line")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Stage 1 Attack Recall")
    ax.set_title("Stage 1 Attack Recall by True Attack Stage")
    ax.grid(True, axis="y", alpha=0.2)
    ax.legend()
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

    mlp_params = v03.resolve_fixed_model_params(base_settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must include fixed MLP parameters.")

    seeds = parse_seeds(args.seeds)
    device = torch.device("cpu")

    v02.set_random_seed(int(base_settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=run_dir,
    )

    train_x, train_y_full = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y_full = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y_full = v02.build_row_arrays(test_df, feature_cols)

    train_y_stage1 = (train_y_full != 0).astype(np.int64)
    val_y_stage1 = (val_y_full != 0).astype(np.int64)
    test_y_stage1 = (test_y_full != 0).astype(np.int64)

    attack_train_mask = train_y_full != 0
    attack_val_mask = val_y_full != 0
    attack_test_mask = test_y_full != 0

    train_x_stage2 = train_x[attack_train_mask]
    val_x_stage2 = val_x[attack_val_mask]
    test_x_stage2 = test_x[attack_test_mask]
    train_y_stage2 = train_y_full[attack_train_mask] - 1
    val_y_stage2 = val_y_full[attack_val_mask] - 1
    test_y_stage2 = test_y_full[attack_test_mask] - 1

    raw_end_to_end_rows: list[dict[str, Any]] = []
    raw_stage1_rows: list[dict[str, Any]] = []
    raw_stage2_rows: list[dict[str, Any]] = []
    run_payloads: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"\nRunning two-stage MLP with seed {seed}...")
        set_seed(seed)

        print("  Stage 1: binary Benign vs Attack")
        stage1_train_x = train_x
        stage1_train_y = train_y_stage1
        stage1_oversampler_summary: dict[str, Any] = {"applied": False, "strategy": str(args.stage1_oversampler)}
        if str(args.stage1_oversampler) == "adasyn":
            stage1_train_x, stage1_train_y, stage1_oversampler_summary = oversample_stage1_binary_attack(
                x_train=train_x,
                y_train=train_y_stage1,
                random_seed=int(seed),
                target_ratio=float(args.stage1_adasyn_target_ratio),
            )
        stage1_model, stage1_val_metrics, stage1_history = train_mlp_generic(
            train_x=stage1_train_x,
            train_y=stage1_train_y,
            val_x=val_x,
            val_y=val_y_stage1,
            class_names=STAGE1_NAMES,
            mlp_params=mlp_params,
            settings=base_settings,
            device=device,
        )
        stage1_test_probs = predict_probs(
            model=stage1_model,
            x=test_x,
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        stage1_summary = compute_stage1_summary(
            original_test_labels=test_y_full,
            binary_true=test_y_stage1,
            binary_probs=stage1_test_probs,
            threshold=float(args.stage1_threshold),
        )
        raw_stage1_rows.append(
            {
                "seed": int(seed),
                "attack_recall": float(stage1_summary["attack_recall"]),
                "benign_f1": float(stage1_summary["benign_f1"]),
                "recon_attack_recall": float(stage1_summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[1]]),
                "foothold_attack_recall": float(stage1_summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[2]]),
                "lm_attack_recall": float(stage1_summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[3]]),
                "de_attack_recall": float(stage1_summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[4]]),
            }
        )

        print("  Stage 2: attack-only kill-chain classifier")
        adasyn_x_stage2, adasyn_y_stage2, adasyn_summary = targeted_adasyn_attack_only(
            x_train=train_x_stage2,
            y_train=train_y_stage2,
            random_seed=int(seed),
        )
        stage2_model, stage2_val_metrics, stage2_history = train_mlp_generic(
            train_x=adasyn_x_stage2,
            train_y=adasyn_y_stage2,
            val_x=val_x_stage2,
            val_y=val_y_stage2,
            class_names=STAGE2_NAMES,
            mlp_params=mlp_params,
            settings=base_settings,
            device=device,
        )
        stage2_attack_test_probs = predict_probs(
            model=stage2_model,
            x=test_x_stage2,
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        stage2_attack_metrics, stage2_attack_per_class = evaluate_multiclass(
            test_y_stage2,
            stage2_attack_test_probs,
            STAGE2_NAMES,
        )
        raw_stage2_rows.append(
            {
                "seed": int(seed),
                "accuracy": float(stage2_attack_metrics["accuracy"]),
                "macro_f1": float(stage2_attack_metrics["f1"]),
                "recon_f1": float(stage2_attack_per_class[STAGE2_NAMES[0]]),
                "foothold_f1": float(stage2_attack_per_class[STAGE2_NAMES[1]]),
                "lm_f1": float(stage2_attack_per_class[STAGE2_NAMES[2]]),
                "de_f1": float(stage2_attack_per_class[STAGE2_NAMES[3]]),
            }
        )

        stage2_full_probs = predict_probs(
            model=stage2_model,
            x=test_x,
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        end_to_end_pred, end_to_end_probs = build_end_to_end_outputs(
            stage1_probs=stage1_test_probs,
            stage2_probs=stage2_full_probs,
            threshold=float(args.stage1_threshold),
        )
        end_to_end_metrics, end_to_end_per_class = evaluate_multiclass(
            test_y_full,
            end_to_end_probs,
            v02.STAGE_NAMES,
            y_pred=end_to_end_pred,
        )
        raw_end_to_end_rows.append(
            {
                "seed": int(seed),
                "accuracy": float(end_to_end_metrics["accuracy"]),
                "macro_f1": float(end_to_end_metrics["f1"]),
                "pr_auc": float(end_to_end_metrics["pr_auc"]) if end_to_end_metrics["pr_auc"] is not None else np.nan,
                "benign_f1": float(end_to_end_per_class[v02.STAGE_NAMES[0]]),
                "recon_f1": float(end_to_end_per_class[v02.STAGE_NAMES[1]]),
                "foothold_f1": float(end_to_end_per_class[v02.STAGE_NAMES[2]]),
                "lm_f1": float(end_to_end_per_class[v02.STAGE_NAMES[3]]),
                "de_f1": float(end_to_end_per_class[v02.STAGE_NAMES[4]]),
            }
        )

        seed_dir = run_dir / "seed_runs" / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        torch.save(stage1_model.state_dict(), seed_dir / "stage1_state_dict.pt")
        torch.save(stage2_model.state_dict(), seed_dir / "stage2_state_dict.pt")
        payload = {
            "seed": int(seed),
            "mlp_params": mlp_params,
            "stage1": {
                "oversampler_summary": stage1_oversampler_summary,
                "val_metrics": stage1_val_metrics,
                "test_summary": stage1_summary,
                "history": stage1_history,
            },
            "stage2": {
                "adasyn_summary": adasyn_summary,
                "val_metrics": stage2_val_metrics,
                "attack_only_test_metrics": stage2_attack_metrics,
                "attack_only_test_per_class_f1": stage2_attack_per_class,
                "history": stage2_history,
            },
            "end_to_end": {
                "metrics": end_to_end_metrics,
                "per_class_f1": end_to_end_per_class,
            },
        }
        write_json(seed_dir / "results.json", payload)
        run_payloads.append(payload)

    end_to_end_frame = pd.DataFrame(raw_end_to_end_rows).sort_values("seed").reset_index(drop=True)
    stage1_frame = pd.DataFrame(raw_stage1_rows).sort_values("seed").reset_index(drop=True)
    stage2_frame = pd.DataFrame(raw_stage2_rows).sort_values("seed").reset_index(drop=True)
    end_to_end_frame.to_csv(run_dir / "two_stage_end_to_end_raw.csv", index=False)
    stage1_frame.to_csv(run_dir / "stage1_binary_raw.csv", index=False)
    stage2_frame.to_csv(run_dir / "stage2_attack_only_raw.csv", index=False)

    summary = {
        "pipeline": ["single_stage_reference", "two_stage_mlp"],
        "accuracy_mean": [np.nan, float(end_to_end_frame["accuracy"].mean())],
        "accuracy_std": [np.nan, float(end_to_end_frame["accuracy"].std(ddof=1))],
        "macro_f1_mean": [np.nan, float(end_to_end_frame["macro_f1"].mean())],
        "macro_f1_std": [np.nan, float(end_to_end_frame["macro_f1"].std(ddof=1))],
        "pr_auc_mean": [np.nan, float(end_to_end_frame["pr_auc"].mean())],
        "pr_auc_std": [np.nan, float(end_to_end_frame["pr_auc"].std(ddof=1))],
        "recon_f1_mean": [np.nan, float(end_to_end_frame["recon_f1"].mean())],
        "recon_f1_std": [np.nan, float(end_to_end_frame["recon_f1"].std(ddof=1))],
        "de_f1_mean": [np.nan, float(end_to_end_frame["de_f1"].mean())],
        "de_f1_std": [np.nan, float(end_to_end_frame["de_f1"].std(ddof=1))],
    }
    summary_frame = pd.DataFrame(summary)

    reference_path = v02.resolve_path(repo_root, args.reference_csv)
    if not reference_path.exists():
        raise FileNotFoundError(f"Reference CSV not found: {reference_path}")
    reference_frame = pd.read_csv(reference_path)
    single_stage_frame = reference_frame[
        reference_frame["variant"] == str(args.reference_variant)
    ].sort_values("seed")
    if len(single_stage_frame) != len(seeds):
        raise ValueError(
            f"Expected {len(seeds)} rows for reference variant `{args.reference_variant}`, "
            f"found {len(single_stage_frame)}."
        )

    summary_frame.loc[0, ["accuracy_mean", "accuracy_std"]] = [
        float(single_stage_frame["accuracy"].mean()),
        float(single_stage_frame["accuracy"].std(ddof=1)),
    ]
    summary_frame.loc[0, ["macro_f1_mean", "macro_f1_std"]] = [
        float(single_stage_frame["macro_f1"].mean()),
        float(single_stage_frame["macro_f1"].std(ddof=1)),
    ]
    summary_frame.loc[0, ["pr_auc_mean", "pr_auc_std"]] = [
        float(single_stage_frame["pr_auc"].mean()),
        float(single_stage_frame["pr_auc"].std(ddof=1)),
    ]
    summary_frame.loc[0, ["recon_f1_mean", "recon_f1_std"]] = [
        float(single_stage_frame["recon_f1"].mean()),
        float(single_stage_frame["recon_f1"].std(ddof=1)),
    ]
    summary_frame.loc[0, ["de_f1_mean", "de_f1_std"]] = [
        float(single_stage_frame["de_f1"].mean()),
        float(single_stage_frame["de_f1"].std(ddof=1)),
    ]
    summary_frame.to_csv(run_dir / "two_stage_vs_single_stage_summary.csv", index=False)

    delta_frame = end_to_end_frame.merge(
        single_stage_frame[["seed", "accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]],
        on="seed",
        suffixes=("_two_stage", "_single_stage"),
    )
    delta_rows = []
    for _, row in delta_frame.iterrows():
        delta_rows.append(
            {
                "seed": int(row["seed"]),
                "accuracy_delta": float(row["accuracy_two_stage"] - row["accuracy_single_stage"]),
                "macro_f1_delta": float(row["macro_f1_two_stage"] - row["macro_f1_single_stage"]),
                "pr_auc_delta": float(row["pr_auc_two_stage"] - row["pr_auc_single_stage"]),
                "recon_f1_delta": float(row["recon_f1_two_stage"] - row["recon_f1_single_stage"]),
                "de_f1_delta": float(row["de_f1_two_stage"] - row["de_f1_single_stage"]),
            }
        )
    delta_frame_clean = pd.DataFrame(delta_rows)
    delta_frame_clean.to_csv(run_dir / "two_stage_delta_vs_single_stage.csv", index=False)

    stage1_summary = {
        "attack_recall_mean": float(stage1_frame["attack_recall"].mean()),
        "attack_recall_std": float(stage1_frame["attack_recall"].std(ddof=1)),
        "benign_f1_mean": float(stage1_frame["benign_f1"].mean()),
        "recon_attack_recall_mean": float(stage1_frame["recon_attack_recall"].mean()),
        "recon_attack_recall_std": float(stage1_frame["recon_attack_recall"].std(ddof=1)),
        "risk_flag_recon_bottleneck": bool(float(stage1_frame["recon_attack_recall"].mean()) < 0.7),
    }

    decision = {
        "two_stage_improves_recon_mean": bool(float(delta_frame_clean["recon_f1_delta"].mean()) > 0.01),
        "two_stage_holds_de_mean": bool(float(delta_frame_clean["de_f1_delta"].mean()) >= -0.05),
        "stage1_recon_gate_ok": bool(not stage1_summary["risk_flag_recon_bottleneck"]),
    }
    decision["recommended_to_continue"] = bool(
        decision["two_stage_improves_recon_mean"] and decision["two_stage_holds_de_mean"]
    )

    plot_end_to_end_vs_single_stage(summary_frame, run_dir / "two_stage_vs_single_stage.png")
    plot_stage1_attack_recall(stage1_frame, run_dir / "stage1_attack_recall.png")

    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "branch_intent": "feature/two-stage-attack-mlp",
            "config_path": str(config_path),
            "reference_csv": str(reference_path),
            "reference_variant": str(args.reference_variant),
            "seeds": seeds,
            "stage1_threshold": float(args.stage1_threshold),
            "stage1_oversampler": str(args.stage1_oversampler),
            "stage1_adasyn_target_ratio": float(args.stage1_adasyn_target_ratio),
            "cache_path": str(cache_path),
            "cache_metadata_path": str(cache_metadata_path),
            "preprocess_summary": preprocess_summary,
            "mlp_params": mlp_params,
            "stage1_summary": stage1_summary,
            "two_stage_vs_single_stage": summary_frame.to_dict(orient="records"),
            "delta_vs_single_stage": delta_frame_clean.to_dict(orient="records"),
            "decision": decision,
            "seed_payloads": run_payloads,
        },
    )

    report_lines = [
        "# Two-Stage Support-Floor MLP Report",
        "",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        f"Stage 1 threshold: `{float(args.stage1_threshold):.2f}`",
        f"Stage 1 oversampler: `{str(args.stage1_oversampler)}`",
        f"Reference single-stage variant: `{args.reference_variant}`",
        "",
        "## End-to-End Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Delta Vs Single-Stage",
        "",
        render_markdown_table(delta_frame_clean),
        "",
        "## Stage 1 Summary",
        "",
        "```json",
        json.dumps(v02.coerce_json(stage1_summary), indent=2),
        "```",
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Two-stage raw results: {run_dir / 'two_stage_end_to_end_raw.csv'}")
    print(f"Summary: {run_dir / 'two_stage_vs_single_stage_summary.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
