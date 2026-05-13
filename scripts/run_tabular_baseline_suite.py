from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from imblearn.over_sampling import ADASYN
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from pytorch_tabnet.tab_model import TabNetClassifier

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run missing tabular baselines on the trusted Unraveled support-floor "
            "benchmark, using a seed-42 gate before promoting competitive challengers "
            "to a full 3-seed comparison."
        )
    )
    parser.add_argument(
        "--config",
        default="configs/praxisv03-unraveled-support-floor-baseline-20260423.json",
        help="Trusted support-floor config JSON.",
    )
    parser.add_argument("--run-name", required=True, help="Output folder name under runs/.")
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated seeds to use if a challenger passes the gate.",
    )
    parser.add_argument(
        "--official-baseline-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/summary_mean_std.csv",
        help="Official support-floor MLP summary CSV.",
    )
    parser.add_argument(
        "--hardened-bakeoff-csv",
        default="runs/hardened-bakeoff-heldout-source-reset-deltas-20260423/bakeoff_metrics.csv",
        help="Optional existing RF/XGBoost reference table for context.",
    )
    parser.add_argument(
        "--competitive-margin",
        type=float,
        default=0.01,
        help="Maximum Macro F1 gap from the official MLP mean allowed to trigger full multi-seed runs.",
    )
    return parser.parse_args()


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


def build_class_weighted_sample_weight(labels: np.ndarray, num_classes: int) -> np.ndarray:
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    return weights[labels]


def build_class_weight_dict(labels: np.ndarray, num_classes: int) -> dict[int, float]:
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    return {index: float(weights[index]) for index in range(num_classes)}


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def evaluate_probs(y_true: np.ndarray, probs: np.ndarray) -> tuple[dict[str, Any], dict[str, float]]:
    preds = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y_true, preds, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y_true, preds)
    return metrics, per_class


def load_split(config_path: Path) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    repo_root = v02.resolve_repo_root()
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    scratch_dir = (repo_root / "runs" / "_tabular_baseline_suite_scratch").resolve()
    scratch_dir.mkdir(parents=True, exist_ok=True)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, _ = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=scratch_dir,
    )
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)
    return settings, train_x, train_y, val_x, val_y, test_x, test_y


def run_lightgbm(
    seed: int,
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resampled_x, resampled_y, adasyn_summary = targeted_adasyn(
        x_train=train_x,
        y_train=train_y,
        random_seed=int(seed),
        requested_n_neighbors=5,
    )
    sample_weight = build_class_weighted_sample_weight(resampled_y, len(v02.STAGE_NAMES))
    model = LGBMClassifier(
        objective="multiclass",
        num_class=len(v02.STAGE_NAMES),
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=63,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=int(seed),
        n_jobs=1,
        verbosity=-1,
    )
    model.fit(
        resampled_x,
        resampled_y,
        sample_weight=sample_weight,
        eval_set=[(val_x, val_y)],
        eval_names=["val"],
        eval_metric="multi_logloss",
        callbacks=[early_stopping(40, verbose=False), log_evaluation(period=0)],
    )
    probs = model.predict_proba(test_x)
    metrics, per_class = evaluate_probs(test_y, probs)
    row = {
        "model": "LightGBM",
        "seed": int(seed),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
    }
    payload = {
        "model": "LightGBM",
        "seed": int(seed),
        "adasyn_summary": adasyn_summary,
        "best_iteration": int(model.best_iteration_) if model.best_iteration_ is not None else None,
        "test_metrics": metrics,
        "per_class_test_f1": per_class,
    }
    return row, payload


def run_tabnet(
    seed: int,
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resampled_x, resampled_y, adasyn_summary = targeted_adasyn(
        x_train=train_x,
        y_train=train_y,
        random_seed=int(seed),
        requested_n_neighbors=5,
    )
    class_weights = build_class_weight_dict(resampled_y, len(v02.STAGE_NAMES))
    model = TabNetClassifier(
        n_d=64,
        n_a=64,
        n_steps=5,
        gamma=1.5,
        lambda_sparse=1e-4,
        optimizer_fn=torch.optim.Adam,
        optimizer_params={"lr": 0.02, "weight_decay": 1e-5},
        scheduler_fn=torch.optim.lr_scheduler.StepLR,
        scheduler_params={"step_size": 20, "gamma": 0.9},
        mask_type="sparsemax",
        seed=int(seed),
        verbose=0,
        device_name="cpu",
    )
    model.fit(
        resampled_x,
        resampled_y,
        eval_set=[(val_x, val_y)],
        eval_name=["val"],
        eval_metric=["logloss"],
        weights=class_weights,
        max_epochs=60,
        patience=10,
        batch_size=4096,
        virtual_batch_size=256,
        num_workers=0,
        drop_last=False,
        pin_memory=False,
    )
    probs = model.predict_proba(test_x)
    metrics, per_class = evaluate_probs(test_y, probs)
    row = {
        "model": "TabNet",
        "seed": int(seed),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
    }
    payload = {
        "model": "TabNet",
        "seed": int(seed),
        "adasyn_summary": adasyn_summary,
        "best_epoch": int(getattr(model, "best_epoch", -1)),
        "test_metrics": metrics,
        "per_class_test_f1": per_class,
    }
    return row, payload


def summarize_rows(model_name: str, rows: pd.DataFrame) -> dict[str, Any]:
    return {
        "model": model_name,
        "seeds_run": int(len(rows)),
        "accuracy_mean": float(rows["accuracy"].mean()),
        "accuracy_std": float(rows["accuracy"].std(ddof=1)) if len(rows) > 1 else np.nan,
        "macro_f1_mean": float(rows["macro_f1"].mean()),
        "macro_f1_std": float(rows["macro_f1"].std(ddof=1)) if len(rows) > 1 else np.nan,
        "pr_auc_mean": float(rows["pr_auc"].mean()),
        "pr_auc_std": float(rows["pr_auc"].std(ddof=1)) if len(rows) > 1 else np.nan,
        "recon_f1_mean": float(rows["recon_f1"].mean()),
        "recon_f1_std": float(rows["recon_f1"].std(ddof=1)) if len(rows) > 1 else np.nan,
        "de_f1_mean": float(rows["de_f1"].mean()),
        "de_f1_std": float(rows["de_f1"].std(ddof=1)) if len(rows) > 1 else np.nan,
    }


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    run_dir = (repo_root / "runs" / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = (repo_root / args.config).resolve()
    official_path = (repo_root / args.official_baseline_csv).resolve()

    settings, train_x, train_y, val_x, val_y, test_x, test_y = load_split(config_path)
    official_frame = pd.read_csv(official_path)
    official_row = official_frame.set_index("variant").loc["adasyn_weighted_ce"]
    official_macro = float(official_row["macro_f1_mean"])

    seeds = parse_seeds(args.seeds)
    seed_zero = seeds[0]
    gate_results: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []

    model_runners = {
        "LightGBM": run_lightgbm,
        "TabNet": run_tabnet,
    }
    model_seed_sets: dict[str, list[int]] = {}

    for model_name, runner in model_runners.items():
        print(f"Running {model_name} gate seed {seed_zero}...")
        row, payload = runner(seed_zero, train_x, train_y, val_x, val_y, test_x, test_y)
        raw_rows.append(row)
        payloads.append(payload)
        gap = official_macro - float(row["macro_f1"])
        passes_gate = bool(gap <= float(args.competitive_margin))
        gate_results.append(
            {
                "model": model_name,
                "gate_seed": int(seed_zero),
                "gate_macro_f1": float(row["macro_f1"]),
                "official_mlp_macro_f1_mean": official_macro,
                "gap_to_official": float(gap),
                "competitive_margin": float(args.competitive_margin),
                "passes_gate": passes_gate,
            }
        )
        model_seed_sets[model_name] = [seed_zero]
        if passes_gate:
            for seed in seeds[1:]:
                print(f"Running {model_name} full comparison seed {seed}...")
                row, payload = runner(seed, train_x, train_y, val_x, val_y, test_x, test_y)
                raw_rows.append(row)
                payloads.append(payload)
                model_seed_sets[model_name].append(seed)

    raw_frame = pd.DataFrame(raw_rows).sort_values(["model", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(run_dir / "raw_results.csv", index=False)
    gate_frame = pd.DataFrame(gate_results)
    gate_frame.to_csv(run_dir / "gate_results.csv", index=False)

    summary_rows = [
        {
            "model": "MLP (official)",
            "seeds_run": 3,
            "accuracy_mean": float(official_row["accuracy_mean"]),
            "accuracy_std": float(official_row["accuracy_std"]),
            "macro_f1_mean": float(official_row["macro_f1_mean"]),
            "macro_f1_std": float(official_row["macro_f1_std"]),
            "pr_auc_mean": float(official_row["pr_auc_mean"]),
            "pr_auc_std": float(official_row["pr_auc_std"]),
            "recon_f1_mean": float(official_row["recon_f1_mean"]),
            "recon_f1_std": float(official_row["recon_f1_std"]),
            "de_f1_mean": float(official_row["de_f1_mean"]),
            "de_f1_std": float(official_row["de_f1_std"]),
        }
    ]
    for model_name in ("LightGBM", "TabNet"):
        model_rows = raw_frame[raw_frame["model"] == model_name].copy()
        summary_rows.append(summarize_rows(model_name, model_rows))
    summary_frame = pd.DataFrame(summary_rows).sort_values("macro_f1_mean", ascending=False).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    delta_rows = []
    for _, row in summary_frame.iterrows():
        if row["model"] == "MLP (official)":
            continue
        delta_rows.append(
            {
                "model": row["model"],
                "macro_f1_mean_delta_vs_official_mlp": float(row["macro_f1_mean"] - official_macro),
                "pr_auc_mean_delta_vs_official_mlp": float(row["pr_auc_mean"] - float(official_row["pr_auc_mean"])),
                "recon_f1_mean_delta_vs_official_mlp": float(row["recon_f1_mean"] - float(official_row["recon_f1_mean"])),
                "de_f1_mean_delta_vs_official_mlp": float(row["de_f1_mean"] - float(official_row["de_f1_mean"])),
                "seeds_run": int(row["seeds_run"]),
            }
        )
    delta_frame = pd.DataFrame(delta_rows).sort_values("macro_f1_mean_delta_vs_official_mlp", ascending=False)
    delta_frame.to_csv(run_dir / "delta_vs_mlp.csv", index=False)

    comparison_context = None
    hardened_path = (repo_root / args.hardened_bakeoff_csv).resolve()
    if hardened_path.exists():
        comparison_context = pd.read_csv(hardened_path)
        comparison_context.to_csv(run_dir / "existing_hardened_bakeoff_context.csv", index=False)

    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config": str(config_path),
            "gate_results": gate_results,
            "model_seed_sets": model_seed_sets,
            "official_baseline_macro_f1_mean": official_macro,
        },
    )

    report_lines = [
        "# Tabular Baseline Suite",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Config: `{config_path}`",
        f"- Run directory: `{run_dir}`",
        "",
        "## Purpose",
        "",
        "This run closes the missing-tabular-baselines review gap by testing `LightGBM` and `TabNet` on the same trusted Unraveled support-floor split used for the official MLP baseline.",
        "",
        "## Gate Rule",
        "",
        f"A challenger gets promoted from seed `{seed_zero}` to the full seed set only if its seed-42 Macro F1 is within `{args.competitive_margin:.2f}` of the official MLP mean Macro F1.",
        "",
        "## Gate Results",
        "",
        render_markdown_table(gate_frame, float_places=4),
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame, float_places=4),
        "",
        "## Delta Versus Official MLP",
        "",
        render_markdown_table(delta_frame, float_places=4),
    ]
    if comparison_context is not None:
        report_lines.extend(
            [
                "",
                "## Existing Hardened Bakeoff Context",
                "",
                render_markdown_table(comparison_context, float_places=4),
            ]
        )
    (run_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Completed tabular baseline suite: {run_dir}")


if __name__ == "__main__":
    main()
