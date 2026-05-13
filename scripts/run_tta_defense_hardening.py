from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, precision_recall_curve

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03

from scripts.run_tta_hybrid_gate_sweep import DE_LABEL, RECON_LABEL, hybrid_probs, select_policy
from scripts.run_tta_streaming_apt_pilot import (
    compute_per_class_f1,
    instantiate_mlp,
    load_settings,
    predict_probs,
    render_markdown_table,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Praxis 06 defense-hardening artifacts without replacing the "
            "locked policy: extra-seed fixed-threshold replay, validation-distribution "
            "sensitivity, BN stream-order ablation, override-flow decomposition, "
            "DE safety audit, PR operating-point figures, and feature-shift diagnostics."
        )
    )
    parser.add_argument("--source-run-dir", default="runs/mlp-support-floor-3seed-ablation-20260423")
    parser.add_argument("--selection-run-dir", default="runs/tta-hybrid-gate-sweep-20260509")
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--run-name", default="tta-defense-hardening-20260513")
    parser.add_argument("--config", default=None)
    parser.add_argument("--seeds", default="42,43,44,45,46,47,48")
    parser.add_argument("--original-locked-seeds", default="42,43,44")
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--fixed-uncertainty-threshold", type=float, default=0.5)
    parser.add_argument("--fixed-recon-rescue-threshold", type=float, default=0.5)
    parser.add_argument("--fixed-de-keep-threshold", type=float, default=0.0)
    parser.add_argument("--val-sensitivity-sample-seeds", default="101,202")
    parser.add_argument("--uncertainty-thresholds", default="0.50,0.60,0.70,0.80,0.90,0.95")
    parser.add_argument("--recon-rescue-thresholds", default="0.40,0.50,0.60,0.70,0.80,0.90")
    parser.add_argument("--de-keep-thresholds", default="0.00,0.50,0.70,0.90")
    parser.add_argument("--de-delta-limit", type=float, default=0.05)
    parser.add_argument("--dapt-config", default="configs/dapt2020-local-fast.json")
    parser.add_argument("--skip-dapt-shift", action="store_true")
    parser.add_argument("--allow-missing-seeds", action="store_true")
    return parser.parse_args()


def parse_int_csv(raw: str) -> list[int]:
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one integer value is required.")
    return values


def parse_float_csv(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one float value is required.")
    return values


def metric_row(
    method: str,
    seed: int,
    split: str,
    y: np.ndarray,
    probs: np.ndarray,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pred = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y, pred, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y, pred)
    row = {
        "method": method,
        "seed": int(seed),
        "split": split,
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "benign_f1": float(per_class[v02.STAGE_NAMES[0]]),
        "recon_f1": float(per_class[v02.STAGE_NAMES[RECON_LABEL]]),
        "foothold_f1": float(per_class[v02.STAGE_NAMES[2]]),
        "lm_f1": float(per_class[v02.STAGE_NAMES[3]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[DE_LABEL]]),
    }
    if extra:
        row.update(extra)
    return row


def summarize_metrics(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metric_cols = [
        "accuracy",
        "macro_f1",
        "pr_auc",
        "recon_f1",
        "de_f1",
        "override_rate",
        "macro_f1_delta_vs_frozen",
        "recon_f1_delta_vs_frozen",
        "de_f1_delta_vs_frozen",
    ]
    existing = [col for col in metric_cols if col in frame.columns]
    aggregations: dict[str, tuple[str, str]] = {}
    for col in existing:
        aggregations[f"{col}_mean"] = (col, "mean")
        aggregations[f"{col}_std"] = (col, "std")
        aggregations[f"{col}_min"] = (col, "min")
        aggregations[f"{col}_max"] = (col, "max")
    return frame.groupby(group_cols).agg(**aggregations).reset_index()


def set_bn_train_dropout_eval(model: torch.nn.Module) -> None:
    model.eval()
    for module in model.modules():
        if isinstance(module, torch.nn.BatchNorm1d):
            module.train()


def bn_adapt_probs(
    base_state: dict[str, Any],
    feature_count: int,
    mlp_params: dict[str, Any],
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
    shuffle_seed: int | None = None,
) -> np.ndarray:
    if shuffle_seed is None:
        model = instantiate_mlp(feature_count=feature_count, params=mlp_params).to(device)
        model.load_state_dict(copy.deepcopy(base_state))
        loader_x = x
        inverse: np.ndarray | None = None
    else:
        rng = np.random.default_rng(int(shuffle_seed))
        perm = rng.permutation(len(x))
        inverse = np.empty_like(perm)
        inverse[perm] = np.arange(len(perm))
        model = instantiate_mlp(feature_count=feature_count, params=mlp_params).to(device)
        model.load_state_dict(copy.deepcopy(base_state))
        loader_x = x[perm]

    from torch.utils.data import DataLoader, TensorDataset

    loader = DataLoader(
        TensorDataset(torch.from_numpy(loader_x.astype(np.float32))),
        batch_size=batch_size,
        shuffle=False,
    )
    set_bn_train_dropout_eval(model)
    probs: list[np.ndarray] = []
    with torch.no_grad():
        for (xs,) in loader:
            logits = model(xs.to(device))
            probs.append(torch.softmax(logits, dim=1).cpu().numpy())
    out = np.vstack(probs)
    model.eval()
    if inverse is not None:
        out = out[inverse]
    return out


def gate_mask(
    frozen_probs: np.ndarray,
    tta_probs: np.ndarray,
    uncertainty_threshold: float,
    recon_rescue_threshold: float,
    de_keep_threshold: float,
) -> dict[str, np.ndarray]:
    frozen_pred = np.argmax(frozen_probs, axis=1)
    tta_pred = np.argmax(tta_probs, axis=1)
    frozen_conf = np.max(frozen_probs, axis=1)
    tta_conf = np.max(tta_probs, axis=1)
    uncertain_override = frozen_conf < float(uncertainty_threshold)
    recon_rescue = (
        (frozen_pred != RECON_LABEL)
        & (tta_pred == RECON_LABEL)
        & (tta_conf >= float(recon_rescue_threshold))
    )
    protected_de = (frozen_pred == DE_LABEL) & (frozen_conf >= float(de_keep_threshold))
    use_tta = (uncertain_override | recon_rescue) & ~protected_de
    return {
        "frozen_pred": frozen_pred,
        "tta_pred": tta_pred,
        "hybrid_pred": np.where(use_tta, tta_pred, frozen_pred),
        "frozen_conf": frozen_conf,
        "tta_conf": tta_conf,
        "uncertain_override": uncertain_override,
        "recon_rescue": recon_rescue,
        "protected_de": protected_de,
        "use_tta": use_tta,
    }


def stage_name(label: int) -> str:
    return str(v02.STAGE_NAMES[int(label)])


def override_decomposition(
    seed: int,
    split: str,
    y: np.ndarray,
    frozen_probs: np.ndarray,
    tta_probs: np.ndarray,
    uncertainty_threshold: float,
    recon_rescue_threshold: float,
    de_keep_threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], pd.DataFrame]:
    masks = gate_mask(
        frozen_probs,
        tta_probs,
        uncertainty_threshold,
        recon_rescue_threshold,
        de_keep_threshold,
    )
    use_tta = masks["use_tta"]
    frozen_pred = masks["frozen_pred"]
    tta_pred = masks["tta_pred"]
    hybrid_pred = masks["hybrid_pred"]
    changed = frozen_pred != hybrid_pred

    flow_rows: list[dict[str, Any]] = []
    for from_label in range(len(v02.STAGE_NAMES)):
        for to_label in range(len(v02.STAGE_NAMES)):
            for true_label in range(len(v02.STAGE_NAMES)):
                mask = use_tta & (frozen_pred == from_label) & (hybrid_pred == to_label) & (y == true_label)
                count = int(mask.sum())
                if count:
                    flow_rows.append(
                        {
                            "seed": int(seed),
                            "split": split,
                            "from_stage": stage_name(from_label),
                            "to_stage": stage_name(to_label),
                            "true_stage": stage_name(true_label),
                            "count": count,
                            "fraction_of_rows": float(count / len(y)),
                            "fraction_of_overrides": float(count / max(int(use_tta.sum()), 1)),
                        }
                    )

    summary = {
        "seed": int(seed),
        "split": split,
        "rows": int(len(y)),
        "override_count": int(use_tta.sum()),
        "override_rate": float(use_tta.mean()),
        "prediction_changed_count": int((use_tta & changed).sum()),
        "prediction_changed_rate": float((use_tta & changed).mean()),
        "override_to_recon": int((use_tta & (hybrid_pred == RECON_LABEL)).sum()),
        "override_from_recon": int((use_tta & (frozen_pred == RECON_LABEL)).sum()),
        "override_to_de": int((use_tta & (hybrid_pred == DE_LABEL)).sum()),
        "override_from_de": int((use_tta & (frozen_pred == DE_LABEL)).sum()),
        "recon_rescue_override_count": int((use_tta & masks["recon_rescue"]).sum()),
        "uncertain_override_count": int((use_tta & masks["uncertain_override"]).sum()),
        "protected_de_count": int(masks["protected_de"].sum()),
        "override_to_recon_fraction": float((use_tta & (hybrid_pred == RECON_LABEL)).sum() / max(int(use_tta.sum()), 1)),
        "override_to_de_fraction": float((use_tta & (hybrid_pred == DE_LABEL)).sum() / max(int(use_tta.sum()), 1)),
    }

    detail_mask = (y == DE_LABEL) | (frozen_pred == DE_LABEL) | (hybrid_pred == DE_LABEL)
    detail = pd.DataFrame(
        {
            "seed": int(seed),
            "split": split,
            "row_position": np.arange(len(y))[detail_mask],
            "true_stage": [stage_name(value) for value in y[detail_mask]],
            "frozen_pred": [stage_name(value) for value in frozen_pred[detail_mask]],
            "tta_pred": [stage_name(value) for value in tta_pred[detail_mask]],
            "hybrid_pred": [stage_name(value) for value in hybrid_pred[detail_mask]],
            "frozen_conf": masks["frozen_conf"][detail_mask],
            "tta_conf": masks["tta_conf"][detail_mask],
            "use_tta": use_tta[detail_mask],
            "prediction_changed": changed[detail_mask],
            "uncertain_override": masks["uncertain_override"][detail_mask],
            "recon_rescue": masks["recon_rescue"][detail_mask],
            "protected_de": masks["protected_de"][detail_mask],
        }
    )
    return flow_rows, summary, detail


def de_safety_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (seed, split), group in detail.groupby(["seed", "split"]):
        true_de = group[group["true_stage"] == stage_name(DE_LABEL)]
        changed_to_de = group[(group["hybrid_pred"] == stage_name(DE_LABEL)) & (group["frozen_pred"] != stage_name(DE_LABEL))]
        changed_from_de = group[(group["frozen_pred"] == stage_name(DE_LABEL)) & (group["hybrid_pred"] != stage_name(DE_LABEL))]
        rows.append(
            {
                "seed": int(seed),
                "split": split,
                "true_de_rows_in_detail": int(len(true_de)),
                "true_de_frozen_correct": int((true_de["frozen_pred"] == stage_name(DE_LABEL)).sum()),
                "true_de_hybrid_correct": int((true_de["hybrid_pred"] == stage_name(DE_LABEL)).sum()),
                "changed_to_de_count": int(len(changed_to_de)),
                "changed_to_de_true_de_count": int((changed_to_de["true_stage"] == stage_name(DE_LABEL)).sum()),
                "changed_to_de_non_de_count": int((changed_to_de["true_stage"] != stage_name(DE_LABEL)).sum()),
                "changed_to_de_mean_tta_conf": float(changed_to_de["tta_conf"].mean()) if len(changed_to_de) else np.nan,
                "changed_to_de_max_tta_conf": float(changed_to_de["tta_conf"].max()) if len(changed_to_de) else np.nan,
                "changed_from_de_count": int(len(changed_from_de)),
                "changed_from_de_true_de_count": int((changed_from_de["true_stage"] == stage_name(DE_LABEL)).sum()),
                "changed_from_de_mean_frozen_conf": float(changed_from_de["frozen_conf"].mean()) if len(changed_from_de) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def test_like_val_indices(val_y: np.ndarray, test_y: np.ndarray, sample_seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(sample_seed))
    labels = list(range(len(v02.STAGE_NAMES)))
    test_counts = np.bincount(test_y, minlength=len(labels)).astype(float)
    test_frac = test_counts / max(float(test_counts.sum()), 1.0)
    val_counts = np.bincount(val_y, minlength=len(labels)).astype(int)
    feasible_totals = [
        math.floor(val_counts[label] / max(test_frac[label], 1e-12))
        for label in labels
        if test_frac[label] > 0
    ]
    total = max(1, int(min(feasible_totals)))
    target_counts = np.floor(test_frac * total).astype(int)
    for label in labels:
        if test_frac[label] > 0 and target_counts[label] == 0 and val_counts[label] > 0:
            target_counts[label] = 1
    while target_counts.sum() < total:
        deficits = test_frac * total - target_counts
        label = int(np.argmax(deficits))
        if target_counts[label] < val_counts[label]:
            target_counts[label] += 1
        else:
            break
    indices: list[np.ndarray] = []
    for label in labels:
        available = np.flatnonzero(val_y == label)
        count = min(int(target_counts[label]), len(available))
        if count > 0:
            indices.append(rng.choice(available, size=count, replace=False))
    out = np.concatenate(indices)
    rng.shuffle(out)
    return out


def validation_sensitivity(
    seed: int,
    sample_seed: int,
    val_y: np.ndarray,
    test_y: np.ndarray,
    frozen_val: np.ndarray,
    tta_val: np.ndarray,
    frozen_test: np.ndarray,
    tta_test: np.ndarray,
    uncertainty_thresholds: list[float],
    recon_rescue_thresholds: list[float],
    de_keep_thresholds: list[float],
    de_delta_limit: float,
) -> dict[str, Any]:
    indices = test_like_val_indices(val_y, test_y, sample_seed)
    y_sub = val_y[indices]
    frozen_sub = frozen_val[indices]
    tta_sub = tta_val[indices]
    frozen_sub_pred = np.argmax(frozen_sub, axis=1)
    frozen_sub_per_class = compute_per_class_f1(y_sub, frozen_sub_pred)
    de_floor = max(float(frozen_sub_per_class[v02.STAGE_NAMES[DE_LABEL]]) - float(de_delta_limit), 0.0)
    rows: list[dict[str, Any]] = []
    frozen_test_metrics = metric_row("frozen", seed, "test", test_y, frozen_test)
    for uncertainty_threshold in uncertainty_thresholds:
        for recon_rescue_threshold in recon_rescue_thresholds:
            for de_keep_threshold in de_keep_thresholds:
                val_hybrid, val_gate = hybrid_probs(
                    frozen_sub,
                    tta_sub,
                    uncertainty_threshold,
                    recon_rescue_threshold,
                    de_keep_threshold,
                )
                test_hybrid, test_gate = hybrid_probs(
                    frozen_test,
                    tta_test,
                    uncertainty_threshold,
                    recon_rescue_threshold,
                    de_keep_threshold,
                )
                val_pred = np.argmax(val_hybrid, axis=1)
                test_pred = np.argmax(test_hybrid, axis=1)
                val_metrics = v02.compute_metrics(y_sub, val_pred, val_hybrid, v02.STAGE_NAMES)
                test_metrics = v02.compute_metrics(test_y, test_pred, test_hybrid, v02.STAGE_NAMES)
                val_per_class = compute_per_class_f1(y_sub, val_pred)
                test_per_class = compute_per_class_f1(test_y, test_pred)
                rows.append(
                    {
                        "seed": int(seed),
                        "sample_seed": int(sample_seed),
                        "val_subsample_rows": int(len(indices)),
                        "val_subsample_recon_fraction": float((y_sub == RECON_LABEL).mean()),
                        "val_subsample_de_fraction": float((y_sub == DE_LABEL).mean()),
                        "de_delta_limit": float(de_delta_limit),
                        "de_floor": float(de_floor),
                        "uncertainty_threshold": float(uncertainty_threshold),
                        "recon_rescue_threshold": float(recon_rescue_threshold),
                        "de_keep_threshold": float(de_keep_threshold),
                        "val_macro_f1": float(val_metrics["f1"]),
                        "val_recon_f1": float(val_per_class[v02.STAGE_NAMES[RECON_LABEL]]),
                        "val_de_f1": float(val_per_class[v02.STAGE_NAMES[DE_LABEL]]),
                        "val_recon_de_min_f1": float(
                            min(
                                val_per_class[v02.STAGE_NAMES[RECON_LABEL]],
                                val_per_class[v02.STAGE_NAMES[DE_LABEL]],
                            )
                        ),
                        "allowed": bool(float(val_per_class[v02.STAGE_NAMES[DE_LABEL]]) >= de_floor),
                        "override_rate_val": float(val_gate["override_rate"]),
                        "test_accuracy": float(test_metrics["accuracy"]),
                        "test_macro_f1": float(test_metrics["f1"]),
                        "test_pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                        "test_recon_f1": float(test_per_class[v02.STAGE_NAMES[RECON_LABEL]]),
                        "test_de_f1": float(test_per_class[v02.STAGE_NAMES[DE_LABEL]]),
                        "override_rate_test": float(test_gate["override_rate"]),
                    }
                )
    sweep = pd.DataFrame(rows)
    selected = select_policy(sweep, "recon_guarded")
    out = selected.to_dict()
    for metric in ["accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]:
        out[f"test_{metric}_delta_vs_frozen"] = float(out[f"test_{metric}"] - frozen_test_metrics[metric])
    return out


def feature_shift_rows(name: str, train_x: np.ndarray, val_x: np.ndarray, test_x: np.ndarray, feature_cols: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    train_mean = train_x.mean(axis=0)
    train_std = train_x.std(axis=0)
    safe_train_std = np.where(train_std <= 1e-12, 1.0, train_std)
    for split, x in [("val", val_x), ("test", test_x)]:
        split_mean = x.mean(axis=0)
        split_std = x.std(axis=0)
        safe_split_std = np.where(split_std <= 1e-12, 1e-12, split_std)
        mean_shift = np.abs((split_mean - train_mean) / safe_train_std)
        std_log_ratio = np.abs(np.log((safe_split_std + 1e-12) / (safe_train_std + 1e-12)))
        for index, feature in enumerate(feature_cols):
            rows.append(
                {
                    "dataset": name,
                    "split": split,
                    "feature": feature,
                    "train_mean": float(train_mean[index]),
                    "split_mean": float(split_mean[index]),
                    "train_std": float(train_std[index]),
                    "split_std": float(split_std[index]),
                    "abs_standardized_mean_shift": float(mean_shift[index]),
                    "abs_log_std_ratio": float(std_log_ratio[index]),
                }
            )
    return rows


def summarize_feature_shift(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    return (
        frame.groupby(["dataset", "split"])
        .agg(
            features=("feature", "count"),
            median_abs_standardized_mean_shift=("abs_standardized_mean_shift", "median"),
            p90_abs_standardized_mean_shift=("abs_standardized_mean_shift", lambda values: float(np.quantile(values, 0.9))),
            max_abs_standardized_mean_shift=("abs_standardized_mean_shift", "max"),
            median_abs_log_std_ratio=("abs_log_std_ratio", "median"),
            p90_abs_log_std_ratio=("abs_log_std_ratio", lambda values: float(np.quantile(values, 0.9))),
            features_std_ratio_gt_2=("abs_log_std_ratio", lambda values: int(np.sum(np.asarray(values) > np.log(2.0)))),
        )
        .reset_index()
    )


def dapt_feature_shift(repo_root: Path, dapt_config: Path, run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts.run_dapt_mlp_baseline import load_dapt_module, load_json

    dapt_settings = load_json(dapt_config)
    dapt_module = load_dapt_module(repo_root, dapt_settings, run_dir / "dapt_shift_runtime")
    runtime_defaults = dapt_module.resolve_runtime_profile(
        max_files=dapt_settings.get("max_files"),
        sample_rate=dapt_settings.get("sample_rate"),
    )
    df, feature_cols, _ = dapt_module.load_dapt2020_with_network_context(
        max_files=dapt_settings.get("max_files"),
        sample_rate=dapt_settings.get("sample_rate") or 1.0,
        merge_networks=bool(dapt_settings.get("merge_networks", False)),
    )
    train_df, val_df, test_df, _, feature_cols = dapt_module.stratified_temporal_split_by_network(
        df=df,
        feature_cols=feature_cols,
        val_size=0.15,
        test_size=0.15,
        n_blocks=int(runtime_defaults.get("n_blocks", 10)),
        strategy=str(dapt_settings.get("strategy", "hybrid")),
    )
    train_x, _ = v02.build_row_arrays(train_df, feature_cols)
    val_x, _ = v02.build_row_arrays(val_df, feature_cols)
    test_x, _ = v02.build_row_arrays(test_df, feature_cols)
    return feature_shift_rows("DAPT2020", train_x, val_x, test_x, feature_cols), {
        "rows": {"train": int(len(train_df)), "val": int(len(val_df)), "test": int(len(test_df))},
        "feature_count": int(len(feature_cols)),
    }


def plot_pr_curves(pr_frame: pd.DataFrame, output_path: Path, target_stage: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    subset = pr_frame[pr_frame["target_stage"] == target_stage]
    colors = {"frozen": "#4c78a8", "locked_hybrid": "#f58518"}
    for method, group in subset.groupby("method"):
        for seed, seed_group in group.groupby("seed"):
            curve = seed_group[seed_group["point_type"] == "curve"].sort_values("recall")
            ax.plot(
                curve["recall"],
                curve["precision"],
                color=colors.get(method, "#999999"),
                alpha=0.22,
                linewidth=1,
            )
        op = group[group["point_type"] == "operating_point"]
        if not op.empty:
            ax.scatter(
                op["recall"],
                op["precision"],
                color=colors.get(method, "#999999"),
                label=f"{method} operating points",
                s=46,
                edgecolor="black",
                linewidth=0.5,
            )
    ax.set_title(f"{target_stage} Precision-Recall Curves And Locked Operating Points")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.2)
    ax.legend(loc="lower left")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    selection_run_dir = v02.resolve_path(repo_root, args.selection_run_dir)
    source_summary = json.loads((source_run_dir / "summary.json").read_text(encoding="utf-8"))
    config_path = Path(args.config).resolve() if args.config else Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_int_csv(args.seeds)
    original_locked_seeds = set(parse_int_csv(args.original_locked_seeds))
    sensitivity_sample_seeds = parse_int_csv(args.val_sensitivity_sample_seeds)
    uncertainty_thresholds = parse_float_csv(args.uncertainty_thresholds)
    recon_rescue_thresholds = parse_float_csv(args.recon_rescue_thresholds)
    de_keep_thresholds = parse_float_csv(args.de_keep_thresholds)
    batch_size = int(args.batch_size)
    device = torch.device("cpu")

    selection_path = selection_run_dir / "selected_hybrid_policies.csv"
    selected = pd.read_csv(selection_path)
    locked_rows = selected[
        (selected["policy"] == "recon_guarded")
        & (selected["tta_method"] == "bn_adapt")
        & (np.isclose(selected["de_delta_limit"], float(args.de_delta_limit)))
    ].copy()
    locked_by_seed = {int(row["seed"]): row for row in locked_rows.to_dict("records")}

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")

    print(f"Loading trusted split from {config_path}...")
    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, cache_path, cache_metadata_path = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=run_dir,
    )
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    metric_rows: list[dict[str, Any]] = []
    flow_rows: list[dict[str, Any]] = []
    override_summary_rows: list[dict[str, Any]] = []
    de_detail_frames: list[pd.DataFrame] = []
    sensitivity_rows: list[dict[str, Any]] = []
    pr_rows: list[dict[str, Any]] = []
    missing_seeds: list[int] = []
    seed_threshold_manifest: list[dict[str, Any]] = []

    for seed in seeds:
        state_path = source_run_dir / "seed_runs" / str(args.variant) / f"seed_{seed}" / "mlp_state_dict.pt"
        if not state_path.exists():
            missing_seeds.append(seed)
            if args.allow_missing_seeds:
                print(f"Skipping missing seed {seed}: {state_path}")
                continue
            raise FileNotFoundError(f"Missing checkpoint for seed {seed}: {state_path}")

        print(f"Seed {seed}: computing frozen, BN-adapted, and shuffled BN-adapted probabilities...")
        base_model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params).to(device)
        base_model.load_state_dict(torch.load(state_path, map_location=device))
        base_state = copy.deepcopy(base_model.state_dict())
        frozen_val = predict_probs(base_model, val_x, batch_size, device)
        frozen_test = predict_probs(base_model, test_x, batch_size, device)
        tta_val = bn_adapt_probs(base_state, len(feature_cols), mlp_params, val_x, batch_size, device)
        tta_test = bn_adapt_probs(base_state, len(feature_cols), mlp_params, test_x, batch_size, device)
        tta_test_shuffled = bn_adapt_probs(
            base_state,
            len(feature_cols),
            mlp_params,
            test_x,
            batch_size,
            device,
            shuffle_seed=10000 + int(seed),
        )

        if seed in locked_by_seed and seed in original_locked_seeds:
            threshold_source = "original_locked_validation_selection"
            uncertainty_threshold = float(locked_by_seed[seed]["uncertainty_threshold"])
            recon_rescue_threshold = float(locked_by_seed[seed]["recon_rescue_threshold"])
            de_keep_threshold = float(locked_by_seed[seed]["de_keep_threshold"])
        else:
            threshold_source = "fixed_canonical_extension_no_new_search"
            uncertainty_threshold = float(args.fixed_uncertainty_threshold)
            recon_rescue_threshold = float(args.fixed_recon_rescue_threshold)
            de_keep_threshold = float(args.fixed_de_keep_threshold)

        seed_threshold_manifest.append(
            {
                "seed": int(seed),
                "threshold_source": threshold_source,
                "uncertainty_threshold": uncertainty_threshold,
                "recon_rescue_threshold": recon_rescue_threshold,
                "de_keep_threshold": de_keep_threshold,
                "policy": "recon_guarded",
                "tta_method": "bn_adapt",
                "de_delta_limit": float(args.de_delta_limit),
            }
        )

        split_payloads = [
            ("val", val_y, frozen_val, tta_val, None),
            ("test", test_y, frozen_test, tta_test, None),
            ("test_shuffle_bn_order", test_y, frozen_test, tta_test_shuffled, 10000 + int(seed)),
        ]
        for split, y, frozen_probs, tta_probs, shuffle_seed in split_payloads:
            frozen_row = metric_row("frozen", seed, split, y, frozen_probs, {"threshold_source": threshold_source})
            hybrid, gate = hybrid_probs(
                frozen_probs,
                tta_probs,
                uncertainty_threshold,
                recon_rescue_threshold,
                de_keep_threshold,
            )
            hybrid_row = metric_row(
                "locked_hybrid" if shuffle_seed is None else "locked_hybrid_bn_shuffled_stream",
                seed,
                split,
                y,
                hybrid,
                {
                    "threshold_source": threshold_source,
                    "uncertainty_threshold": uncertainty_threshold,
                    "recon_rescue_threshold": recon_rescue_threshold,
                    "de_keep_threshold": de_keep_threshold,
                    "override_rate": float(gate["override_rate"]),
                    "uncertain_override_rate": float(gate["uncertain_override_rate"]),
                    "recon_rescue_rate": float(gate["recon_rescue_rate"]),
                    "protected_de_rate": float(gate["protected_de_rate"]),
                    "shuffle_seed": shuffle_seed if shuffle_seed is not None else np.nan,
                },
            )
            for metric in ["accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]:
                hybrid_row[f"{metric}_delta_vs_frozen"] = float(hybrid_row[metric] - frozen_row[metric])
            metric_rows.extend([frozen_row, hybrid_row])

            if split.startswith("test"):
                rows, summary, detail = override_decomposition(
                    seed,
                    split,
                    y,
                    frozen_probs,
                    tta_probs,
                    uncertainty_threshold,
                    recon_rescue_threshold,
                    de_keep_threshold,
                )
                flow_rows.extend(rows)
                override_summary_rows.append(summary)
                de_detail_frames.append(detail)

        for sample_seed in sensitivity_sample_seeds:
            sensitivity_rows.append(
                validation_sensitivity(
                    seed=seed,
                    sample_seed=sample_seed,
                    val_y=val_y,
                    test_y=test_y,
                    frozen_val=frozen_val,
                    tta_val=tta_val,
                    frozen_test=frozen_test,
                    tta_test=tta_test,
                    uncertainty_thresholds=uncertainty_thresholds,
                    recon_rescue_thresholds=recon_rescue_thresholds,
                    de_keep_thresholds=de_keep_thresholds,
                    de_delta_limit=float(args.de_delta_limit),
                )
            )

        hybrid_test, _ = hybrid_probs(
            frozen_test,
            tta_test,
            uncertainty_threshold,
            recon_rescue_threshold,
            de_keep_threshold,
        )
        for target_label in [RECON_LABEL, DE_LABEL]:
            target = (test_y == target_label).astype(int)
            for method, probs in [("frozen", frozen_test), ("locked_hybrid", hybrid_test)]:
                precision, recall, _ = precision_recall_curve(target, probs[:, target_label])
                ap = average_precision_score(target, probs[:, target_label])
                curve_step = max(1, len(precision) // 600)
                for idx in range(0, len(precision), curve_step):
                    pr_rows.append(
                        {
                            "seed": int(seed),
                            "target_stage": stage_name(target_label),
                            "method": method,
                            "point_type": "curve",
                            "precision": float(precision[idx]),
                            "recall": float(recall[idx]),
                            "average_precision": float(ap),
                        }
                    )
                pred = np.argmax(probs, axis=1)
                tp = int(((pred == target_label) & (test_y == target_label)).sum())
                fp = int(((pred == target_label) & (test_y != target_label)).sum())
                fn = int(((pred != target_label) & (test_y == target_label)).sum())
                op_precision = tp / max(tp + fp, 1)
                op_recall = tp / max(tp + fn, 1)
                pr_rows.append(
                    {
                        "seed": int(seed),
                        "target_stage": stage_name(target_label),
                        "method": method,
                        "point_type": "operating_point",
                        "precision": float(op_precision),
                        "recall": float(op_recall),
                        "average_precision": float(ap),
                    }
                )

    metrics_frame = pd.DataFrame(metric_rows)
    metrics_frame.to_csv(run_dir / "fixed_locked_seed_extension_metrics.csv", index=False)
    metrics_summary = summarize_metrics(metrics_frame, ["method", "split", "threshold_source"])
    metrics_summary.to_csv(run_dir / "fixed_locked_seed_extension_summary.csv", index=False)
    pd.DataFrame(seed_threshold_manifest).to_csv(run_dir / "seed_threshold_manifest.csv", index=False)
    if flow_rows:
        pd.DataFrame(flow_rows).to_csv(run_dir / "override_flow.csv", index=False)
    override_summary = pd.DataFrame(override_summary_rows)
    override_summary.to_csv(run_dir / "override_decomposition_summary.csv", index=False)
    de_detail = pd.concat(de_detail_frames, ignore_index=True) if de_detail_frames else pd.DataFrame()
    de_detail.to_csv(run_dir / "de_detail_rows.csv", index=False)
    de_safety = de_safety_summary(de_detail) if not de_detail.empty else pd.DataFrame()
    de_safety.to_csv(run_dir / "de_safety_analysis.csv", index=False)
    if not de_detail.empty:
        seed43 = de_detail[(de_detail["seed"] == 43) & (de_detail["prediction_changed"] | de_detail["use_tta"])].head(80)
        seed43.to_csv(run_dir / "de_seed43_changed_or_overridden_sample.csv", index=False)

    sensitivity_frame = pd.DataFrame(sensitivity_rows)
    sensitivity_frame.to_csv(run_dir / "validation_distribution_sensitivity.csv", index=False)
    sensitivity_summary = summarize_metrics(
        sensitivity_frame.rename(
            columns={
                "test_macro_f1": "macro_f1",
                "test_pr_auc": "pr_auc",
                "test_recon_f1": "recon_f1",
                "test_de_f1": "de_f1",
                "override_rate_test": "override_rate",
            }
        ),
        ["sample_seed"],
    )
    sensitivity_summary.to_csv(run_dir / "validation_distribution_sensitivity_summary.csv", index=False)

    pr_frame = pd.DataFrame(pr_rows)
    pr_frame.to_csv(run_dir / "pr_operating_points.csv", index=False)
    if not pr_frame.empty:
        plot_pr_curves(pr_frame, run_dir / "figure_recon_pr_operating_points.png", stage_name(RECON_LABEL))
        plot_pr_curves(pr_frame, run_dir / "figure_de_pr_operating_points.png", stage_name(DE_LABEL))

    shift_rows = feature_shift_rows("Unraveled", train_x, val_x, test_x, feature_cols)
    dapt_metadata: dict[str, Any] = {}
    if not args.skip_dapt_shift:
        dapt_rows, dapt_metadata = dapt_feature_shift(repo_root, (repo_root / args.dapt_config).resolve(), run_dir)
        shift_rows.extend(dapt_rows)
    shift_frame = pd.DataFrame(shift_rows)
    shift_frame.to_csv(run_dir / "feature_shift_by_feature.csv", index=False)
    shift_summary = summarize_feature_shift(shift_rows)
    shift_summary.to_csv(run_dir / "feature_shift_summary.csv", index=False)

    original_test = metrics_frame[
        (metrics_frame["split"] == "test")
        & (metrics_frame["threshold_source"] == "original_locked_validation_selection")
        & (metrics_frame["method"] == "locked_hybrid")
    ]
    extension_test = metrics_frame[
        (metrics_frame["split"] == "test")
        & (metrics_frame["threshold_source"] == "fixed_canonical_extension_no_new_search")
        & (metrics_frame["method"] == "locked_hybrid")
    ]
    all_test = metrics_frame[(metrics_frame["split"] == "test") & (metrics_frame["method"] == "locked_hybrid")]

    report_lines = [
        "# Praxis 06 TTA Defense Hardening Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        "This report does not replace the locked 2026-05-09 replay. Original seeds use their validation-selected locked thresholds. Extra seeds, when present, use a fixed canonical extension (`uncertainty=0.50`, `recon_rescue=0.50`, `de_keep=0.00`) with no new threshold search.",
        "",
        "## Seed Extension Summary",
        "",
        render_markdown_table(
            metrics_summary[
                (metrics_summary["split"] == "test")
                & (metrics_summary["method"].isin(["frozen", "locked_hybrid"]))
            ][
                [
                    "method",
                    "threshold_source",
                    "accuracy_mean",
                    "macro_f1_mean",
                    "macro_f1_std",
                    "recon_f1_mean",
                    "recon_f1_std",
                    "de_f1_mean",
                    "de_f1_std",
                    "pr_auc_mean",
                    "override_rate_mean",
                ]
            ],
            4,
        ),
        "",
        "## BN Stream-Order Ablation",
        "",
        render_markdown_table(
            metrics_summary[
                (metrics_summary["split"] == "test_shuffle_bn_order")
                & (metrics_summary["method"].isin(["frozen", "locked_hybrid_bn_shuffled_stream"]))
            ][
                [
                    "method",
                    "threshold_source",
                    "macro_f1_mean",
                    "recon_f1_mean",
                    "de_f1_mean",
                    "override_rate_mean",
                ]
            ],
            4,
        ),
        "",
        "## Validation-Distribution Sensitivity",
        "",
        render_markdown_table(
            sensitivity_summary[
                [
                    "sample_seed",
                    "macro_f1_mean",
                    "macro_f1_std",
                    "recon_f1_mean",
                    "recon_f1_std",
                    "de_f1_mean",
                    "de_f1_std",
                    "override_rate_mean",
                ]
            ],
            4,
        ),
        "",
        "## Override Decomposition",
        "",
        render_markdown_table(
            override_summary.groupby("split").agg(
                override_rate_mean=("override_rate", "mean"),
                override_to_recon_fraction_mean=("override_to_recon_fraction", "mean"),
                override_to_de_fraction_mean=("override_to_de_fraction", "mean"),
                override_from_de_sum=("override_from_de", "sum"),
                protected_de_count_mean=("protected_de_count", "mean"),
            ).reset_index(),
            4,
        ),
        "",
        "## DE Safety",
        "",
        render_markdown_table(de_safety, 4) if not de_safety.empty else "No DE detail rows emitted.",
        "",
        "## Feature-Shift Diagnostic",
        "",
        render_markdown_table(shift_summary, 4),
        "",
        "## Main Artifact Files",
        "",
        "- `fixed_locked_seed_extension_metrics.csv`",
        "- `validation_distribution_sensitivity.csv`",
        "- `override_flow.csv`",
        "- `de_safety_analysis.csv`",
        "- `pr_operating_points.csv`",
        "- `figure_recon_pr_operating_points.png`",
        "- `figure_de_pr_operating_points.png`",
        "- `feature_shift_summary.csv`",
        "",
        "## Interpretation Notes",
        "",
        "- PR-AUC should be framed as representation quality / ranking signal. The main result is a locked operating-point and decision-policy improvement, not a broad probability-quality gain.",
        "- BN-adapt protocol: single pass, unlabeled stream, `DataLoader(..., shuffle=False)`, batch size 4096 by default, dropout in eval mode, BatchNorm layers in train mode, PyTorch BatchNorm1d default momentum unless changed by the model, and no test labels.",
        "- DAPT remains a negative TTA feasibility check. The feature-shift diagnostic is a mechanism clue, not a new external-validity claim.",
    ]
    (run_dir / "PRAXIS06_TTA_DEFENSE_HARDENING_REPORT_20260513.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    write_json(
        run_dir / "defense_hardening_manifest.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "source_run_dir": str(source_run_dir),
            "selection_run_dir": str(selection_run_dir),
            "cache_path": str(cache_path),
            "cache_metadata_path": str(cache_metadata_path),
            "preprocess_summary": preprocess_summary,
            "seeds_requested": seeds,
            "missing_seeds": missing_seeds,
            "original_locked_seeds": sorted(original_locked_seeds),
            "seed_threshold_manifest": seed_threshold_manifest,
            "original_locked_test_rows": original_test.to_dict(orient="records"),
            "fixed_extension_test_rows": extension_test.to_dict(orient="records"),
            "all_locked_test_rows": all_test.to_dict(orient="records"),
            "dapt_shift_metadata": dapt_metadata,
            "artifacts": {
                "metrics": str(run_dir / "fixed_locked_seed_extension_metrics.csv"),
                "summary": str(run_dir / "fixed_locked_seed_extension_summary.csv"),
                "validation_sensitivity": str(run_dir / "validation_distribution_sensitivity.csv"),
                "override_flow": str(run_dir / "override_flow.csv"),
                "de_safety": str(run_dir / "de_safety_analysis.csv"),
                "pr_points": str(run_dir / "pr_operating_points.csv"),
                "feature_shift": str(run_dir / "feature_shift_summary.csv"),
                "report": str(run_dir / "PRAXIS06_TTA_DEFENSE_HARDENING_REPORT_20260513.md"),
            },
        },
    )
    print(f"Defense hardening artifacts written to {run_dir}")


if __name__ == "__main__":
    main()
