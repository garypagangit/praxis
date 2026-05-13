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
from imblearn.over_sampling import ADASYN
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support
from torch.utils.data import DataLoader

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Tier 1 and targeted Tier 2 imbalance experiments on the "
            "support-floor Unraveled held-out source_file split."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor baseline config JSON.")
    parser.add_argument("--baseline-run", required=True, help="Completed baseline deep run directory.")
    parser.add_argument("--weighted-run", required=True, help="Completed weighted-CE deep run directory.")
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output folder name to create under the config's output_dir.",
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


def compute_metric_row(
    family: str,
    variant: str,
    metrics: dict[str, Any],
    per_class: dict[str, float],
) -> dict[str, Any]:
    return {
        "family": family,
        "variant": variant,
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "benign_f1": float(per_class[v02.STAGE_NAMES[0]]),
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "foothold_f1": float(per_class[v02.STAGE_NAMES[2]]),
        "lm_f1": float(per_class[v02.STAGE_NAMES[3]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
    }


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray, class_names: list[str]) -> dict[str, float]:
    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        zero_division=0,
    )
    return {class_names[index]: float(f1[index]) for index in range(len(class_names))}


def build_class_weighted_sample_weight(labels: np.ndarray, num_classes: int) -> np.ndarray:
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    return weights[labels]


def build_binary_sample_weight(labels: np.ndarray) -> np.ndarray:
    counts = np.bincount(labels.astype(np.int64), minlength=2).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    return weights[labels.astype(np.int64)]


def evaluate_probs(
    y_true: np.ndarray,
    probs: np.ndarray,
) -> tuple[dict[str, Any], dict[str, float]]:
    preds = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y_true, preds, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y_true, preds, v02.STAGE_NAMES)
    return metrics, per_class


def predict_row_model(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    loader = DataLoader(
        v02.RowDataset(x, y),
        batch_size=batch_size,
        shuffle=False,
    )
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


def predict_sequence_model(
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
    model.eval()
    probs_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs, ys, mask in loader:
            xs = xs.to(device)
            mask = mask.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=-1)
            flat_mask = mask.view(-1)
            flat_probs = probs.view(-1, probs.shape[-1])[flat_mask]
            flat_labels = ys.view(-1)[flat_mask]
            probs_list.append(flat_probs.cpu().numpy())
            labels_list.append(flat_labels.cpu().numpy())
    return np.concatenate(labels_list), np.vstack(probs_list)


def load_mlp_from_run(run_dir: Path, feature_count: int, device: torch.device) -> torch.nn.Module:
    payload = json.loads((run_dir / "mlp_results.json").read_text(encoding="utf-8"))
    params = payload["best_params"]
    model = v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    ).to(device)
    model.load_state_dict(torch.load(run_dir / "mlp_state_dict.pt", map_location=device))
    return model


def load_mamba_from_run(run_dir: Path, feature_count: int, device: torch.device) -> torch.nn.Module:
    payload = json.loads((run_dir / "mamba_results.json").read_text(encoding="utf-8"))
    params = payload["best_params"]
    model = v02.MambaStageClassifier(
        num_features=feature_count,
        d_model=int(params["d_model"]),
        n_layers=int(params["n_layers"]),
        d_state=int(params["d_state"]),
        d_conv=int(params["d_conv"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    ).to(device)
    model.load_state_dict(torch.load(run_dir / "mamba_state_dict.pt", map_location=device))
    return model


def build_rf(random_seed: int, use_balanced_weights: bool) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced_subsample" if use_balanced_weights else None,
        random_state=random_seed,
        n_jobs=1,
    )


def build_xgb(random_seed: int) -> Any:
    if XGBClassifier is None:
        raise RuntimeError("xgboost is not installed in this environment.")
    return XGBClassifier(
        objective="multi:softprob",
        num_class=len(v02.STAGE_NAMES),
        eval_metric="mlogloss",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=random_seed,
        tree_method="hist",
        n_jobs=1,
    )


def targeted_adasyn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train, minlength=len(v02.STAGE_NAMES))
    attack_majority = int(max(counts[2], counts[3]))
    strategy = {}
    for label in (1, 4):
        if int(counts[label]) >= attack_majority:
            continue
        strategy[int(label)] = attack_majority

    if not strategy:
        return x_train, y_train, {"applied": False, "reason": "targets_already_at_or_above_goal"}

    k_neighbors = min(int(counts[label]) - 1 for label in strategy)
    if k_neighbors < 1:
        return x_train, y_train, {"applied": False, "reason": "insufficient_minority_neighbors"}

    sampler = ADASYN(
        sampling_strategy=strategy,
        random_state=random_seed,
        n_neighbors=min(5, k_neighbors),
    )
    x_resampled, y_resampled = sampler.fit_resample(x_train, y_train)
    return x_resampled, y_resampled, {
        "applied": True,
        "strategy": {v02.STAGE_NAMES[key]: int(value) for key, value in strategy.items()},
        "k_neighbors": int(min(5, k_neighbors)),
        "before_counts": {
            v02.STAGE_NAMES[index]: int(counts[index]) for index in range(len(v02.STAGE_NAMES))
        },
        "after_counts": {
            v02.STAGE_NAMES[index]: int(value)
            for index, value in enumerate(np.bincount(y_resampled, minlength=len(v02.STAGE_NAMES)))
        },
    }


def fit_tree_model(
    family: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    random_seed: int,
    use_balanced_weights: bool,
    fit_sample_weight: np.ndarray | None,
) -> tuple[np.ndarray, dict[str, Any], dict[str, float]]:
    if family == "RandomForest":
        model = build_rf(random_seed=random_seed, use_balanced_weights=use_balanced_weights)
        model.fit(x_train, y_train)
    elif family == "XGBoost":
        model = build_xgb(random_seed=random_seed)
        fit_kwargs = {}
        if fit_sample_weight is not None:
            fit_kwargs["sample_weight"] = fit_sample_weight
        model.fit(x_train, y_train, **fit_kwargs)
    else:
        raise ValueError(f"Unsupported tree family: {family}")

    probs = model.predict_proba(x_test)
    metrics, per_class = evaluate_probs(y_test, probs)
    return probs, metrics, per_class


def fit_mlp_adasyn(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    settings: dict[str, Any],
    device: torch.device,
    params: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], dict[str, float]]:
    adasyn_settings = dict(settings)
    adasyn_settings["imbalance_sampler"] = "none"

    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=True,
    )
    val_loader = DataLoader(
        v02.RowDataset(val_x, val_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=False,
    )
    model = v02.MLPStageClassifier(
        num_features=train_x.shape[1],
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    )
    model, _, _ = v03.train_row_model_v03(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        train_labels=train_y,
        device=device,
        settings=adasyn_settings,
        lr=float(params["lr"]),
        weight_decay=float(params["weight_decay"]),
    )
    y_val, probs_val = predict_row_model(
        model=model,
        x=val_x,
        y=val_y,
        batch_size=int(settings["tabular_batch_size"]),
        device=device,
    )
    y_test_out, probs_test = predict_row_model(
        model=model,
        x=test_x,
        y=test_y,
        batch_size=int(settings["tabular_batch_size"]),
        device=device,
    )
    metrics, per_class = evaluate_probs(y_test_out, probs_test)
    return probs_val, probs_test, metrics, per_class


def apply_target_threshold(
    probs: np.ndarray,
    threshold: float,
    class_index: int,
) -> np.ndarray:
    preds = np.argmax(probs, axis=1)
    preds = preds.copy()
    preds[probs[:, class_index] >= threshold] = class_index
    return preds


def calibrate_target_threshold(
    family: str,
    variant: str,
    y_val: np.ndarray,
    probs_val: np.ndarray,
    y_test: np.ndarray,
    probs_test: np.ndarray,
    target_class: int,
    benign_delta_limit: float = 0.02,
) -> tuple[dict[str, Any], dict[str, float], dict[str, Any], pd.DataFrame]:
    class_names = v02.STAGE_NAMES
    base_pred_val = np.argmax(probs_val, axis=1)
    base_per_class_val = compute_per_class_f1(y_val, base_pred_val, class_names)
    benign_floor = max(base_per_class_val[class_names[0]] - benign_delta_limit, 0.0)

    threshold_rows: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for threshold in np.arange(0.05, 0.501, 0.01):
        pred_val = apply_target_threshold(probs_val, float(threshold), class_index=target_class)
        per_class_val = compute_per_class_f1(y_val, pred_val, class_names)
        metrics_val = v02.compute_metrics(y_val, pred_val, probs_val, class_names)
        row = {
            "family": family,
            "variant": variant,
            "threshold": float(round(threshold, 2)),
            "val_macro_f1": float(metrics_val["f1"]),
            "val_benign_f1": float(per_class_val[class_names[0]]),
            "val_target_f1": float(per_class_val[class_names[target_class]]),
            "allowed": bool(per_class_val[class_names[0]] >= benign_floor),
        }
        threshold_rows.append(row)
        if not row["allowed"]:
            continue
        if best is None:
            best = row
            continue
        best_key = (best["val_target_f1"], best["val_macro_f1"], -best["threshold"])
        row_key = (row["val_target_f1"], row["val_macro_f1"], -row["threshold"])
        if row_key > best_key:
            best = row

    if best is None:
        best = {
            "family": family,
            "variant": variant,
            "threshold": 0.5,
            "val_macro_f1": float(v02.compute_metrics(y_val, base_pred_val, probs_val, class_names)["f1"]),
            "val_benign_f1": float(base_per_class_val[class_names[0]]),
            "val_target_f1": float(base_per_class_val[class_names[target_class]]),
            "allowed": False,
        }

    pred_test = apply_target_threshold(probs_test, float(best["threshold"]), class_index=target_class)
    metrics_test = v02.compute_metrics(y_test, pred_test, probs_test, class_names)
    per_class_test = compute_per_class_f1(y_test, pred_test, class_names)
    summary = {
        "family": family,
        "variant": variant,
        "target_stage": class_names[target_class],
        "threshold": float(best["threshold"]),
        "benign_floor": float(benign_floor),
        "val_target_f1": float(best["val_target_f1"]),
        "val_macro_f1": float(best["val_macro_f1"]),
    }
    return metrics_test, per_class_test, summary, pd.DataFrame(threshold_rows)


def fit_binary_xgb(x_train: np.ndarray, y_train: np.ndarray, seed: int) -> Any:
    if XGBClassifier is None:
        raise RuntimeError("xgboost is not installed in this environment.")
    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=seed,
        tree_method="hist",
        n_jobs=1,
    )
    model.fit(x_train, y_train, sample_weight=build_binary_sample_weight(y_train))
    return model


def fit_attack_stage_xgb(x_train: np.ndarray, y_train: np.ndarray, seed: int) -> Any:
    model = build_xgb(random_seed=seed)
    model.fit(
        x_train,
        y_train,
        sample_weight=build_class_weighted_sample_weight(y_train, num_classes=4),
    )
    return model


def fit_cascade_tree(
    family: str,
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    random_seed: int,
) -> tuple[dict[str, Any], dict[str, float]]:
    binary_train_y = (train_y != 0).astype(np.int64)
    attack_mask = train_y != 0
    attack_train_x = train_x[attack_mask]
    attack_train_y = train_y[attack_mask] - 1

    if family == "RandomForest":
        stage1 = RandomForestClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=random_seed,
            n_jobs=1,
        )
        stage2 = RandomForestClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=random_seed,
            n_jobs=1,
        )
        stage1.fit(train_x, binary_train_y)
        stage2.fit(attack_train_x, attack_train_y)
        attack_pred = stage1.predict(test_x).astype(bool)
        attack_stage_pred = stage2.predict(test_x[attack_pred]) + 1
    elif family == "XGBoost":
        stage1 = fit_binary_xgb(train_x, binary_train_y, seed=random_seed)
        stage2 = fit_attack_stage_xgb(attack_train_x, attack_train_y, seed=random_seed)
        attack_pred = (stage1.predict_proba(test_x)[:, 1] >= 0.5)
        attack_stage_pred = stage2.predict(test_x[attack_pred]) + 1
    else:
        raise ValueError(f"Unsupported cascade family: {family}")

    final_pred = np.zeros_like(test_y)
    final_pred[attack_pred] = attack_stage_pred.astype(np.int64)
    probs = np.eye(len(v02.STAGE_NAMES), dtype=np.float32)[final_pred]
    metrics = v02.compute_metrics(test_y, final_pred, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(test_y, final_pred, v02.STAGE_NAMES)
    return metrics, per_class


def plot_comparison(frame: pd.DataFrame, path: Path) -> None:
    top = frame.copy()
    top["label"] = top["family"] + " / " + top["variant"]
    top = top.sort_values(["macro_f1", "de_f1"], ascending=[False, False]).reset_index(drop=True)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    axes[0].barh(top["label"], top["macro_f1"], color="#4ecdc4")
    axes[0].set_title("Macro F1 by Experiment")
    axes[0].set_xlabel("Macro F1")

    axes[1].barh(top["label"], top["de_f1"], color="#ff6b6b")
    axes[1].set_title("DE F1 by Experiment")
    axes[1].set_xlabel("DE F1")

    for axis in axes:
        axis.invert_yaxis()
        axis.grid(True, axis="x", alpha=0.2)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    baseline_run = Path(args.baseline_run).resolve()
    weighted_run = Path(args.weighted_run).resolve()

    settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    v02.set_random_seed(int(settings["random_seed"]))
    device = torch.device("cpu")

    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=run_dir,
    )

    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    baseline_mlp = load_mlp_from_run(baseline_run, feature_count=len(feature_cols), device=device)
    weighted_mlp = load_mlp_from_run(weighted_run, feature_count=len(feature_cols), device=device)
    baseline_mamba = load_mamba_from_run(baseline_run, feature_count=len(feature_cols), device=device)
    weighted_mamba = load_mamba_from_run(weighted_run, feature_count=len(feature_cols), device=device)

    baseline_mlp_val_y, baseline_mlp_val_probs = predict_row_model(
        baseline_mlp, val_x, val_y, int(settings["tabular_batch_size"]), device
    )
    baseline_mlp_test_y, baseline_mlp_test_probs = predict_row_model(
        baseline_mlp, test_x, test_y, int(settings["tabular_batch_size"]), device
    )
    weighted_mlp_val_y, weighted_mlp_val_probs = predict_row_model(
        weighted_mlp, val_x, val_y, int(settings["tabular_batch_size"]), device
    )
    weighted_mlp_test_y, weighted_mlp_test_probs = predict_row_model(
        weighted_mlp, test_x, test_y, int(settings["tabular_batch_size"]), device
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
    baseline_mamba_val_y, baseline_mamba_val_probs = predict_sequence_model(
        baseline_mamba, val_chunks, int(settings["sequence_batch_size"]), device
    )
    baseline_mamba_test_y, baseline_mamba_test_probs = predict_sequence_model(
        baseline_mamba, test_chunks, int(settings["sequence_batch_size"]), device
    )
    weighted_mamba_val_y, weighted_mamba_val_probs = predict_sequence_model(
        weighted_mamba, val_chunks, int(settings["sequence_batch_size"]), device
    )
    weighted_mamba_test_y, weighted_mamba_test_probs = predict_sequence_model(
        weighted_mamba, test_chunks, int(settings["sequence_batch_size"]), device
    )

    all_rows: list[dict[str, Any]] = []
    threshold_rows: list[pd.DataFrame] = []

    baseline_mlp_metrics, baseline_mlp_per_class = evaluate_probs(baseline_mlp_test_y, baseline_mlp_test_probs)
    all_rows.append(compute_metric_row("MLP", "baseline_cb_focal", baseline_mlp_metrics, baseline_mlp_per_class))

    weighted_mlp_metrics, weighted_mlp_per_class = evaluate_probs(weighted_mlp_test_y, weighted_mlp_test_probs)
    all_rows.append(compute_metric_row("MLP", "weighted_ce", weighted_mlp_metrics, weighted_mlp_per_class))

    baseline_mamba_metrics, baseline_mamba_per_class = evaluate_probs(
        baseline_mamba_test_y, baseline_mamba_test_probs
    )
    all_rows.append(compute_metric_row("Mamba", "baseline_cb_focal", baseline_mamba_metrics, baseline_mamba_per_class))

    weighted_mamba_metrics, weighted_mamba_per_class = evaluate_probs(
        weighted_mamba_test_y, weighted_mamba_test_probs
    )
    all_rows.append(compute_metric_row("Mamba", "weighted_ce", weighted_mamba_metrics, weighted_mamba_per_class))

    rf_probs, rf_metrics, rf_per_class = fit_tree_model(
        family="RandomForest",
        x_train=train_x,
        y_train=train_y,
        x_test=test_x,
        y_test=test_y,
        random_seed=int(settings["random_seed"]),
        use_balanced_weights=True,
        fit_sample_weight=None,
    )
    all_rows.append(compute_metric_row("RandomForest", "baseline_balanced", rf_metrics, rf_per_class))

    if XGBClassifier is not None:
        xgb_probs, xgb_metrics, xgb_per_class = fit_tree_model(
            family="XGBoost",
            x_train=train_x,
            y_train=train_y,
            x_test=test_x,
            y_test=test_y,
            random_seed=int(settings["random_seed"]),
            use_balanced_weights=False,
            fit_sample_weight=build_class_weighted_sample_weight(train_y, len(v02.STAGE_NAMES)),
        )
        all_rows.append(compute_metric_row("XGBoost", "baseline_weighted", xgb_metrics, xgb_per_class))
    else:
        xgb_probs = None

    adasyn_x, adasyn_y, adasyn_summary = targeted_adasyn(
        x_train=train_x,
        y_train=train_y,
        random_seed=int(settings["random_seed"]),
    )

    mlp_params = json.loads((weighted_run / "mlp_results.json").read_text(encoding="utf-8"))["best_params"]
    _, _, adasyn_mlp_metrics, adasyn_mlp_per_class = fit_mlp_adasyn(
        train_x=adasyn_x,
        train_y=adasyn_y,
        val_x=val_x,
        val_y=val_y,
        test_x=test_x,
        test_y=test_y,
        settings=settings,
        device=device,
        params=mlp_params,
    )
    all_rows.append(compute_metric_row("MLP", "adasyn_cb_focal", adasyn_mlp_metrics, adasyn_mlp_per_class))

    _, rf_adasyn_metrics, rf_adasyn_per_class = fit_tree_model(
        family="RandomForest",
        x_train=adasyn_x,
        y_train=adasyn_y,
        x_test=test_x,
        y_test=test_y,
        random_seed=int(settings["random_seed"]),
        use_balanced_weights=False,
        fit_sample_weight=None,
    )
    all_rows.append(compute_metric_row("RandomForest", "adasyn_only", rf_adasyn_metrics, rf_adasyn_per_class))

    if XGBClassifier is not None:
        _, xgb_adasyn_metrics, xgb_adasyn_per_class = fit_tree_model(
            family="XGBoost",
            x_train=adasyn_x,
            y_train=adasyn_y,
            x_test=test_x,
            y_test=test_y,
            random_seed=int(settings["random_seed"]),
            use_balanced_weights=False,
            fit_sample_weight=None,
        )
        all_rows.append(compute_metric_row("XGBoost", "adasyn_only", xgb_adasyn_metrics, xgb_adasyn_per_class))

    calibration_inputs = [
        ("MLP", "baseline_cb_focal", baseline_mlp_val_y, baseline_mlp_val_probs, baseline_mlp_test_y, baseline_mlp_test_probs),
        ("MLP", "weighted_ce", weighted_mlp_val_y, weighted_mlp_val_probs, weighted_mlp_test_y, weighted_mlp_test_probs),
        ("Mamba", "baseline_cb_focal", baseline_mamba_val_y, baseline_mamba_val_probs, baseline_mamba_test_y, baseline_mamba_test_probs),
        ("Mamba", "weighted_ce", weighted_mamba_val_y, weighted_mamba_val_probs, weighted_mamba_test_y, weighted_mamba_test_probs),
    ]
    if rf_probs is not None:
        rf_val_probs, _, _ = fit_tree_model(
            family="RandomForest",
            x_train=train_x,
            y_train=train_y,
            x_test=val_x,
            y_test=val_y,
            random_seed=int(settings["random_seed"]),
            use_balanced_weights=True,
            fit_sample_weight=None,
        )
        calibration_inputs.append(("RandomForest", "baseline_balanced", val_y, rf_val_probs, test_y, rf_probs))
    if XGBClassifier is not None and xgb_probs is not None:
        xgb_val_probs, _, _ = fit_tree_model(
            family="XGBoost",
            x_train=train_x,
            y_train=train_y,
            x_test=val_x,
            y_test=val_y,
            random_seed=int(settings["random_seed"]),
            use_balanced_weights=False,
            fit_sample_weight=build_class_weighted_sample_weight(train_y, len(v02.STAGE_NAMES)),
        )
        calibration_inputs.append(("XGBoost", "baseline_weighted", val_y, xgb_val_probs, test_y, xgb_probs))

    for family, variant, y_val_in, probs_val_in, y_test_in, probs_test_in in calibration_inputs:
        calibrated_metrics, calibrated_per_class, calibrated_summary, threshold_frame = calibrate_target_threshold(
            family=family,
            variant=variant,
            y_val=y_val_in,
            probs_val=probs_val_in,
            y_test=y_test_in,
            probs_test=probs_test_in,
            target_class=4,
        )
        threshold_rows.append(threshold_frame)
        all_rows.append(
            compute_metric_row(
                family=family,
                variant=f"{variant}_de_threshold",
                metrics=calibrated_metrics,
                per_class=calibrated_per_class,
            )
        )

    rf_cascade_metrics, rf_cascade_per_class = fit_cascade_tree(
        family="RandomForest",
        train_x=train_x,
        train_y=train_y,
        test_x=test_x,
        test_y=test_y,
        random_seed=int(settings["random_seed"]),
    )
    all_rows.append(compute_metric_row("RandomForest", "two_stage_cascade", rf_cascade_metrics, rf_cascade_per_class))

    if XGBClassifier is not None:
        xgb_cascade_metrics, xgb_cascade_per_class = fit_cascade_tree(
            family="XGBoost",
            train_x=train_x,
            train_y=train_y,
            test_x=test_x,
            test_y=test_y,
            random_seed=int(settings["random_seed"]),
        )
        all_rows.append(compute_metric_row("XGBoost", "two_stage_cascade", xgb_cascade_metrics, xgb_cascade_per_class))

    results_frame = pd.DataFrame(all_rows).sort_values(
        ["macro_f1", "de_f1", "pr_auc"], ascending=[False, False, False]
    )
    results_frame.to_csv(run_dir / "tier12_results.csv", index=False)

    threshold_frame = pd.concat(threshold_rows, ignore_index=True)
    threshold_frame.to_csv(run_dir / "threshold_sweeps.csv", index=False)

    plot_comparison(results_frame, run_dir / "comparison_macro_de.png")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "baseline_run": str(baseline_run),
        "weighted_run": str(weighted_run),
        "cache_path": str(cache_path),
        "cache_rows": int(len(df)),
        "feature_count": int(len(feature_cols)),
        "preprocess_summary": preprocess_summary,
        "adasyn_summary": adasyn_summary,
        "results": results_frame.to_dict(orient="records"),
    }
    write_json(run_dir / "summary.json", summary)

    top_table = results_frame[
        [
            "family",
            "variant",
            "accuracy",
            "macro_f1",
            "pr_auc",
            "recon_f1",
            "de_f1",
        ]
    ]

    report_lines = [
        "# Unraveled Tier 1 / Tier 2 Suite",
        "",
        f"Config: `{config_path.name}`",
        f"Baseline deep run: `{baseline_run.name}`",
        f"Weighted deep run: `{weighted_run.name}`",
        "",
        "## Main Results",
        "",
        render_markdown_table(top_table),
        "",
        "## ADASYN Summary",
        "",
        "```json",
        json.dumps(v02.coerce_json(adasyn_summary), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Tier 1 / Tier 2 results: {run_dir / 'tier12_results.csv'}")
    print(f"Threshold sweeps: {run_dir / 'threshold_sweeps.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
