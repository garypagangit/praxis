from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import torch
from imblearn.over_sampling import ADASYN
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a support-floor Optuna search around the official Unraveled "
            "MLP + ADASYN + weighted CE winner, then rerun the winning "
            "configuration across multiple seeds."
        )
    )
    parser.add_argument("--config", required=True, help="Base support-floor config JSON.")
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output folder name to create under the config's output_dir.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=50,
        help="Number of Optuna trials to run.",
    )
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated training seeds to use for final reruns.",
    )
    parser.add_argument(
        "--sampler-seed",
        type=int,
        default=42,
        help="Deterministic seed for the Optuna sampler.",
    )
    parser.add_argument(
        "--official-baseline-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/summary_mean_std.csv",
        help="Existing official support-floor MLP summary for delta comparisons.",
    )
    return parser.parse_args()


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def parse_seeds(raw: str) -> list[int]:
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one seed is required.")
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


def flatten_summary_columns(frame: pd.DataFrame) -> pd.DataFrame:
    flat = frame.copy()
    flat.columns = [
        f"{column}_{agg}" if agg else str(column)
        for column, agg in flat.columns.to_flat_index()
    ]
    return flat.reset_index()


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def targeted_adasyn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
    requested_n_neighbors: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train, minlength=len(v02.STAGE_NAMES))
    attack_majority = int(max(counts[2], counts[3]))
    strategy: dict[int, int] = {}
    for label in (1, 4):
        if int(counts[label]) >= attack_majority:
            continue
        strategy[int(label)] = attack_majority

    before_counts = {
        v02.STAGE_NAMES[index]: int(counts[index]) for index in range(len(v02.STAGE_NAMES))
    }
    if not strategy:
        return x_train, y_train, {
            "applied": False,
            "reason": "targets_already_at_goal",
            "requested_n_neighbors": int(requested_n_neighbors),
            "before_counts": before_counts,
            "after_counts": before_counts,
        }

    feasible_neighbors = min(int(counts[label]) - 1 for label in strategy)
    if feasible_neighbors < 1:
        return x_train, y_train, {
            "applied": False,
            "reason": "insufficient_neighbors",
            "requested_n_neighbors": int(requested_n_neighbors),
            "before_counts": before_counts,
            "after_counts": before_counts,
        }

    effective_neighbors = int(min(requested_n_neighbors, feasible_neighbors))
    sampler = ADASYN(
        sampling_strategy=strategy,
        random_state=random_seed,
        n_neighbors=effective_neighbors,
    )
    x_resampled, y_resampled = sampler.fit_resample(x_train, y_train)
    after_counts = np.bincount(y_resampled, minlength=len(v02.STAGE_NAMES))
    return x_resampled, y_resampled, {
        "applied": True,
        "strategy": {v02.STAGE_NAMES[key]: int(value) for key, value in strategy.items()},
        "requested_n_neighbors": int(requested_n_neighbors),
        "effective_n_neighbors": int(effective_neighbors),
        "before_counts": before_counts,
        "after_counts": {
            v02.STAGE_NAMES[index]: int(after_counts[index])
            for index in range(len(v02.STAGE_NAMES))
        },
    }


def compute_weight_diagnostic(
    y_before: np.ndarray,
    y_after: np.ndarray,
    adasyn_summary: dict[str, Any],
) -> dict[str, Any]:
    before_weights = v02.compute_class_weights(y_before, num_classes=len(v02.STAGE_NAMES)).numpy()
    after_weights = v02.compute_class_weights(y_after, num_classes=len(v02.STAGE_NAMES)).numpy()
    return {
        "weighting_stage": "post_adasyn_resampled_labels",
        "adasyn_applied": bool(adasyn_summary.get("applied", False)),
        "before_counts": {
            v02.STAGE_NAMES[index]: int(value)
            for index, value in enumerate(np.bincount(y_before, minlength=len(v02.STAGE_NAMES)))
        },
        "after_counts": {
            v02.STAGE_NAMES[index]: int(value)
            for index, value in enumerate(np.bincount(y_after, minlength=len(v02.STAGE_NAMES)))
        },
        "weights_before_adasyn": {
            v02.STAGE_NAMES[index]: float(before_weights[index])
            for index in range(len(v02.STAGE_NAMES))
        },
        "weights_used_for_training": {
            v02.STAGE_NAMES[index]: float(after_weights[index])
            for index in range(len(v02.STAGE_NAMES))
        },
        "interpretation": (
            "Weighted CE is computed on the resampled labels passed to train_row_model_v03, "
            "so the current pipeline weights after ADASYN rather than on the raw pre-ADASYN counts."
        ),
    }


def instantiate_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    )


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


def metric_row(seed: int, metrics: dict[str, Any], per_class: dict[str, float], params: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed": int(seed),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "benign_f1": float(per_class[v02.STAGE_NAMES[0]]),
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "foothold_f1": float(per_class[v02.STAGE_NAMES[2]]),
        "lm_f1": float(per_class[v02.STAGE_NAMES[3]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
        "hidden_dim": int(params["hidden_dim"]),
        "num_layers": int(params["num_layers"]),
        "dropout": float(params["dropout"]),
        "lr": float(params["lr"]),
        "weight_decay": float(params["weight_decay"]),
        "adasyn_n_neighbors": int(params["adasyn_n_neighbors"]),
    }


def sample_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "hidden_dim": int(trial.suggest_categorical("hidden_dim", [128, 256, 512])),
        "num_layers": int(trial.suggest_categorical("num_layers", [2, 3, 4])),
        "dropout": float(trial.suggest_float("dropout", 0.1, 0.5)),
        "lr": float(trial.suggest_float("lr", 1e-4, 5e-3, log=True)),
        "weight_decay": float(trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True)),
        "adasyn_n_neighbors": int(trial.suggest_categorical("adasyn_n_neighbors", [3, 5, 10])),
    }


def build_base_training_settings(settings: dict[str, Any]) -> dict[str, Any]:
    updated = dict(settings)
    updated["loss_name"] = "weighted_ce"
    updated["imbalance_sampler"] = "none"
    return updated


def objective_factory(
    base_settings: dict[str, Any],
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    feature_count: int,
    device: torch.device,
    trial_dir: Path,
):
    def objective(trial: optuna.Trial) -> float:
        params = sample_params(trial)
        trial_seed = int(base_settings["random_seed"])
        v02.set_random_seed(trial_seed)
        torch.use_deterministic_algorithms(True, warn_only=True)

        resampled_x, resampled_y, adasyn_summary = targeted_adasyn(
            x_train=train_x,
            y_train=train_y,
            random_seed=trial_seed,
            requested_n_neighbors=int(params["adasyn_n_neighbors"]),
        )
        weight_diagnostic = compute_weight_diagnostic(train_y, resampled_y, adasyn_summary)

        train_loader = DataLoader(
            v02.RowDataset(resampled_x, resampled_y),
            batch_size=int(base_settings["tabular_batch_size"]),
            shuffle=True,
        )
        val_loader = DataLoader(
            v02.RowDataset(val_x, val_y),
            batch_size=int(base_settings["tabular_batch_size"]),
            shuffle=False,
        )
        model = instantiate_mlp(feature_count=feature_count, params=params)
        model, val_metrics, history = v03.train_row_model_v03(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            train_labels=resampled_y,
            device=device,
            settings=base_settings,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            trial=trial,
        )
        trial.set_user_attr("adasyn_applied", bool(adasyn_summary.get("applied", False)))
        trial.set_user_attr("adasyn_n_neighbors_effective", adasyn_summary.get("effective_n_neighbors"))
        trial.set_user_attr("adasyn_after_counts", adasyn_summary.get("after_counts"))
        trial.set_user_attr("weighting_stage", weight_diagnostic["weighting_stage"])

        artifact = {
            "trial_number": int(trial.number),
            "params": params,
            "val_metrics": val_metrics,
            "adasyn_summary": adasyn_summary,
            "weight_diagnostic": weight_diagnostic,
            "history": history,
        }
        write_json(trial_dir / f"trial_{trial.number:03d}.json", artifact)
        return float(val_metrics["f1"])

    return objective


def run_final_seed(
    seed: int,
    best_params: dict[str, Any],
    base_settings: dict[str, Any],
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    run_dir: Path,
    device: torch.device,
) -> tuple[dict[str, Any], dict[str, Any]]:
    v02.set_random_seed(int(seed))
    torch.use_deterministic_algorithms(True, warn_only=True)

    resampled_x, resampled_y, adasyn_summary = targeted_adasyn(
        x_train=train_x,
        y_train=train_y,
        random_seed=int(seed),
        requested_n_neighbors=int(best_params["adasyn_n_neighbors"]),
    )
    weight_diagnostic = compute_weight_diagnostic(train_y, resampled_y, adasyn_summary)
    train_loader = DataLoader(
        v02.RowDataset(resampled_x, resampled_y),
        batch_size=int(base_settings["tabular_batch_size"]),
        shuffle=True,
    )
    val_loader = DataLoader(
        v02.RowDataset(val_x, val_y),
        batch_size=int(base_settings["tabular_batch_size"]),
        shuffle=False,
    )
    model = instantiate_mlp(feature_count=int(train_x.shape[1]), params=best_params)
    model, val_metrics, history = v03.train_row_model_v03(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        train_labels=resampled_y,
        device=device,
        settings=base_settings,
        lr=float(best_params["lr"]),
        weight_decay=float(best_params["weight_decay"]),
    )
    y_test_out, probs_test = predict_row_model(
        model=model,
        x=test_x,
        y=test_y,
        batch_size=int(base_settings["tabular_batch_size"]),
        device=device,
    )
    preds_test = np.argmax(probs_test, axis=1)
    test_metrics = v02.compute_metrics(y_test_out, preds_test, probs_test, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y_test_out, preds_test)

    artifact_dir = run_dir / "seed_runs" / f"seed_{seed}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), artifact_dir / "mlp_state_dict.pt")
    payload = {
        "seed": int(seed),
        "best_params": best_params,
        "adasyn_summary": adasyn_summary,
        "weight_diagnostic": weight_diagnostic,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "per_class_test_f1": per_class,
        "history": history,
    }
    write_json(artifact_dir / "results.json", payload)
    return metric_row(seed, test_metrics, per_class, best_params), payload


def plot_trials(trials_frame: pd.DataFrame, output_path: Path) -> None:
    if trials_frame.empty:
        return
    ordered = trials_frame.sort_values("trial_number")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    axes[0].plot(ordered["trial_number"], ordered["value"], color="#38bdf8", linewidth=1.6)
    axes[0].set_title("Validation Macro F1 by Trial")
    axes[0].set_xlabel("Trial")
    axes[0].set_ylabel("Macro F1")
    axes[0].grid(True, alpha=0.2)

    top = trials_frame.sort_values("value", ascending=False).head(10).copy()
    axes[1].barh(top["trial_number"].astype(str), top["value"], color="#4ade80")
    axes[1].invert_yaxis()
    axes[1].set_title("Top 10 Trials")
    axes[1].set_xlabel("Validation Macro F1")
    axes[1].grid(True, axis="x", alpha=0.2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_seed_summary(summary_row: pd.Series, output_path: Path) -> None:
    metrics = pd.Series(
        {
            "Macro F1": float(summary_row["macro_f1_mean"]),
            "PR-AUC": float(summary_row["pr_auc_mean"]),
            "Recon F1": float(summary_row["recon_f1_mean"]),
            "DE F1": float(summary_row["de_f1_mean"]),
        }
    )
    errors = pd.Series(
        {
            "Macro F1": float(summary_row["macro_f1_std"]),
            "PR-AUC": float(summary_row["pr_auc_std"]),
            "Recon F1": float(summary_row["recon_f1_std"]),
            "DE F1": float(summary_row["de_f1_std"]),
        }
    )
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.bar(metrics.index, metrics.values, yerr=errors.values, color=["#38bdf8", "#22c55e", "#f59e0b", "#ef4444"], capsize=4)
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Best Optuna MLP Mean +/- Std Across Final Seeds")
    ax.grid(True, axis="y", alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_report(
    run_dir: Path,
    config_path: Path,
    preprocess_summary: dict[str, Any],
    study: optuna.Study,
    trials_frame: pd.DataFrame,
    summary_frame: pd.DataFrame,
    delta_frame: pd.DataFrame,
    best_params: dict[str, Any],
    weight_diagnostic: dict[str, Any],
) -> None:
    top_trials = trials_frame.sort_values("value", ascending=False).head(10).copy()
    top_trials = top_trials[
        [
            "trial_number",
            "value",
            "hidden_dim",
            "num_layers",
            "dropout",
            "lr",
            "weight_decay",
            "adasyn_n_neighbors",
            "state",
        ]
    ]

    report_lines = [
        "# Support-Floor MLP Optuna Gap-Closure Run",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Config: `{config_path}`",
        f"- Run directory: `{run_dir}`",
        "",
        "## Purpose",
        "",
        "This run closes the main pre-write defensibility gap around the official "
        "`MLP + ADASYN + weighted CE` winner by searching architecture and optimizer "
        "settings directly on the trusted Unraveled support-floor benchmark.",
        "",
        "## Benchmark",
        "",
        f"- Split mode: `{preprocess_summary['split_mode']}`",
        f"- Split group: `{preprocess_summary['split_group_col']}`",
        f"- Temporal delta seed mode: `{preprocess_summary['temporal_delta_seed_mode']}`",
        f"- Delta features enabled: `{preprocess_summary['include_delta_features']}`",
        "",
        "## Best Configuration",
        "",
        "```json",
        json.dumps(v02.coerce_json(best_params), indent=2),
        "```",
        "",
        "## ADASYN Weight Diagnostic",
        "",
        "The key implementation question was whether weighted cross-entropy is computed "
        "before or after ADASYN resampling. The diagnostic below captures the answer "
        "for the winning configuration.",
        "",
        "```json",
        json.dumps(v02.coerce_json(weight_diagnostic), indent=2),
        "```",
        "",
        "## Final 3-Seed Summary",
        "",
        render_markdown_table(summary_frame, float_places=4),
        "",
        "## Delta Versus Official Baseline",
        "",
        render_markdown_table(delta_frame, float_places=4),
        "",
        "## Top Optuna Trials",
        "",
        render_markdown_table(top_trials, float_places=4),
        "",
        "## Study Summary",
        "",
        f"- Trial count: `{len(trials_frame)}`",
        f"- Best validation Macro F1: `{study.best_value:.4f}`",
        f"- Best trial number: `{study.best_trial.number}`",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    config_path = Path(args.config).resolve()
    raw_settings = load_settings(config_path)
    base_settings = build_base_training_settings(raw_settings)
    run_dir = (v02.resolve_path(repo_root, raw_settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    trial_dir = run_dir / "trial_artifacts"
    trial_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")

    write_json(
        run_dir / "metadata.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "args": vars(args),
            "base_settings_subset": {
                "loss_name": base_settings["loss_name"],
                "imbalance_sampler": base_settings["imbalance_sampler"],
                "split_mode": base_settings["split_mode"],
                "split_group_col": base_settings["split_group_col"],
                "train_epochs": int(base_settings["train_epochs"]),
                "early_stopping_patience": int(base_settings["early_stopping_patience"]),
            },
        },
    )

    v02.set_random_seed(int(base_settings["random_seed"]))
    torch.use_deterministic_algorithms(True, warn_only=True)
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=run_dir,
    )
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    sampler = optuna.samplers.TPESampler(seed=int(args.sampler_seed))
    pruner = optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=2)
    study = optuna.create_study(direction="maximize", sampler=sampler, pruner=pruner)
    objective = objective_factory(
        base_settings=base_settings,
        train_x=train_x,
        train_y=train_y,
        val_x=val_x,
        val_y=val_y,
        feature_count=int(train_x.shape[1]),
        device=device,
        trial_dir=trial_dir,
    )
    study.optimize(objective, n_trials=int(args.trials), show_progress_bar=False)

    trial_rows: list[dict[str, Any]] = []
    for trial in study.trials:
        row = {
            "trial_number": int(trial.number),
            "state": str(trial.state).split(".")[-1],
            "value": float(trial.value) if trial.value is not None else np.nan,
        }
        row.update({key: trial.params.get(key) for key in ["hidden_dim", "num_layers", "dropout", "lr", "weight_decay", "adasyn_n_neighbors"]})
        row["adasyn_applied"] = trial.user_attrs.get("adasyn_applied")
        row["adasyn_n_neighbors_effective"] = trial.user_attrs.get("adasyn_n_neighbors_effective")
        trial_rows.append(row)
    trials_frame = pd.DataFrame(trial_rows).sort_values("trial_number").reset_index(drop=True)
    trials_frame.to_csv(run_dir / "trials.csv", index=False)
    plot_trials(trials_frame, run_dir / "trial_progress.png")

    best_params = {
        "hidden_dim": int(study.best_params["hidden_dim"]),
        "num_layers": int(study.best_params["num_layers"]),
        "dropout": float(study.best_params["dropout"]),
        "lr": float(study.best_params["lr"]),
        "weight_decay": float(study.best_params["weight_decay"]),
        "adasyn_n_neighbors": int(study.best_params["adasyn_n_neighbors"]),
    }
    write_json(
        run_dir / "best_config.json",
        {
            "best_trial_number": int(study.best_trial.number),
            "best_validation_macro_f1": float(study.best_value),
            "params": best_params,
        },
    )

    diagnostic_x, diagnostic_y, diagnostic_adasyn = targeted_adasyn(
        x_train=train_x,
        y_train=train_y,
        random_seed=int(base_settings["random_seed"]),
        requested_n_neighbors=int(best_params["adasyn_n_neighbors"]),
    )
    weight_diagnostic = compute_weight_diagnostic(train_y, diagnostic_y, diagnostic_adasyn)
    write_json(run_dir / "adasyn_weight_diagnostic.json", weight_diagnostic)

    seed_rows: list[dict[str, Any]] = []
    final_payloads: list[dict[str, Any]] = []
    for seed in parse_seeds(args.seeds):
        print(f"Running final best-config seed {seed}...")
        row, payload = run_final_seed(
            seed=seed,
            best_params=best_params,
            base_settings=base_settings,
            train_x=train_x,
            train_y=train_y,
            val_x=val_x,
            val_y=val_y,
            test_x=test_x,
            test_y=test_y,
            run_dir=run_dir,
            device=device,
        )
        seed_rows.append(row)
        final_payloads.append(payload)
    raw_results = pd.DataFrame(seed_rows).sort_values("seed").reset_index(drop=True)
    raw_results.to_csv(run_dir / "raw_seed_results.csv", index=False)

    summary_frame = pd.DataFrame(
        [
            {
                "variant": "optuna_best_adasyn_weighted_ce",
                "accuracy_mean": float(raw_results["accuracy"].mean()),
                "accuracy_std": float(raw_results["accuracy"].std(ddof=1)),
                "accuracy_min": float(raw_results["accuracy"].min()),
                "accuracy_max": float(raw_results["accuracy"].max()),
                "macro_f1_mean": float(raw_results["macro_f1"].mean()),
                "macro_f1_std": float(raw_results["macro_f1"].std(ddof=1)),
                "macro_f1_min": float(raw_results["macro_f1"].min()),
                "macro_f1_max": float(raw_results["macro_f1"].max()),
                "pr_auc_mean": float(raw_results["pr_auc"].mean()),
                "pr_auc_std": float(raw_results["pr_auc"].std(ddof=1)),
                "pr_auc_min": float(raw_results["pr_auc"].min()),
                "pr_auc_max": float(raw_results["pr_auc"].max()),
                "recon_f1_mean": float(raw_results["recon_f1"].mean()),
                "recon_f1_std": float(raw_results["recon_f1"].std(ddof=1)),
                "recon_f1_min": float(raw_results["recon_f1"].min()),
                "recon_f1_max": float(raw_results["recon_f1"].max()),
                "de_f1_mean": float(raw_results["de_f1"].mean()),
                "de_f1_std": float(raw_results["de_f1"].std(ddof=1)),
                "de_f1_min": float(raw_results["de_f1"].min()),
                "de_f1_max": float(raw_results["de_f1"].max()),
            }
        ]
    )
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)
    plot_seed_summary(summary_frame.iloc[0], run_dir / "seed_summary.png")

    official_path = v02.resolve_path(repo_root, args.official_baseline_csv)
    if not official_path.exists():
        raise FileNotFoundError(f"Official baseline summary not found: {official_path}")
    official_frame = pd.read_csv(official_path)
    official_row = official_frame.set_index("variant").loc["adasyn_weighted_ce"]
    best_row = summary_frame.iloc[0]
    delta_frame = pd.DataFrame(
        [
            {
                "comparison": "optuna_best_vs_official_adasyn_weighted_ce",
                "accuracy_mean_delta": float(best_row["accuracy_mean"] - official_row["accuracy_mean"]),
                "macro_f1_mean_delta": float(best_row["macro_f1_mean"] - official_row["macro_f1_mean"]),
                "pr_auc_mean_delta": float(best_row["pr_auc_mean"] - official_row["pr_auc_mean"]),
                "recon_f1_mean_delta": float(best_row["recon_f1_mean"] - official_row["recon_f1_mean"]),
                "de_f1_mean_delta": float(best_row["de_f1_mean"] - official_row["de_f1_mean"]),
            }
        ]
    )
    delta_frame.to_csv(run_dir / "delta_vs_official_baseline.csv", index=False)

    build_report(
        run_dir=run_dir,
        config_path=config_path,
        preprocess_summary=preprocess_summary,
        study=study,
        trials_frame=trials_frame,
        summary_frame=summary_frame,
        delta_frame=delta_frame,
        best_params=best_params,
        weight_diagnostic=weight_diagnostic,
    )

    print(f"Completed MLP Optuna support-floor run: {run_dir}")
    print(f"Best validation Macro F1: {study.best_value:.4f}")
    print(f"Best params: {best_params}")


if __name__ == "__main__":
    main()
