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
from sklearn.ensemble import RandomForestClassifier

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_stage2_de_multiplier_suite import (
    render_markdown_table,
    targeted_adasyn_attack_only,
    write_json,
)
from scripts.run_two_stage_feature_subset_revision import (
    STAGE2_NAMES,
    build_end_to_end_outputs,
    build_feature_subsets,
    choose_threshold,
    compute_per_class_f1,
    compute_recon_auc_scores,
    predict_probs,
    set_seed,
    train_stage1_mlp,
)


plt.style.use("dark_background")


VARIANT_DEFS: dict[str, dict[str, Any]] = {
    "rf_balanced": {"family": "RandomForest", "use_adasyn": False},
    "rf_adasyn": {"family": "RandomForest", "use_adasyn": True},
    "xgb_weighted": {"family": "XGBoost", "use_adasyn": False},
    "xgb_adasyn": {"family": "XGBoost", "use_adasyn": True},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate tree-based Stage 2 heads inside the fixed recon_top30 cascade "
            "to test whether a richer attack-only head solves the remaining bottleneck."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor base config JSON.")
    parser.add_argument("--run-name", required=True, help="Output folder under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated seeds.")
    parser.add_argument("--candidate", default="recon_top30", help="Stage 1 feature-subset candidate.")
    parser.add_argument(
        "--variants",
        default="rf_balanced,rf_adasyn,xgb_weighted,xgb_adasyn",
        help="Comma-separated Stage 2 head variants to run.",
    )
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    parser.add_argument(
        "--reference-single-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage official baseline raw-results CSV.",
    )
    parser.add_argument(
        "--reference-cascade-csv",
        default="runs/stage2-end2end-selection-suite-20260428/raw_results.csv",
        help="Best prior cascade raw-results CSV.",
    )
    return parser.parse_args()


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def parse_variants(raw: str) -> list[str]:
    variants = [item.strip() for item in raw.split(",") if item.strip()]
    if not variants:
        raise ValueError("At least one variant is required.")
    unknown = [item for item in variants if item not in VARIANT_DEFS]
    if unknown:
        raise ValueError(f"Unknown variants: {', '.join(unknown)}")
    return variants


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def build_attack_sample_weight(labels: np.ndarray) -> np.ndarray:
    counts = np.bincount(labels.astype(np.int64), minlength=len(STAGE2_NAMES)).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    return weights[labels]


def ensure_prob_matrix(probs: np.ndarray, classes_: np.ndarray, num_classes: int) -> np.ndarray:
    if probs.shape[1] == num_classes and np.array_equal(classes_, np.arange(num_classes)):
        return probs.astype(np.float32, copy=False)
    fixed = np.zeros((probs.shape[0], num_classes), dtype=np.float32)
    for col_index, class_id in enumerate(classes_):
        fixed[:, int(class_id)] = probs[:, col_index]
    return fixed


def instantiate_estimator(variant: str, seed: int) -> Any:
    family = str(VARIANT_DEFS[variant]["family"])
    if family == "RandomForest":
        return RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=int(seed),
            n_jobs=1,
        )
    if XGBClassifier is None:
        raise RuntimeError("XGBoost is not available in this environment.")
    return XGBClassifier(
        objective="multi:softprob",
        num_class=len(STAGE2_NAMES),
        eval_metric="mlogloss",
        n_estimators=350,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=int(seed),
        tree_method="hist",
        n_jobs=1,
    )


def fit_variant(
    variant: str,
    estimator: Any,
    train_x: np.ndarray,
    train_y: np.ndarray,
) -> dict[str, Any]:
    fit_x = train_x
    fit_y = train_y
    adasyn_summary = {"applied": False}
    if bool(VARIANT_DEFS[variant]["use_adasyn"]):
        fit_x, fit_y, adasyn_summary = targeted_adasyn_attack_only(
            x_train=train_x,
            y_train=train_y,
            random_seed=int(getattr(estimator, "random_state", 42)),
        )

    fit_kwargs: dict[str, Any] = {}
    if str(VARIANT_DEFS[variant]["family"]) == "XGBoost" and not bool(VARIANT_DEFS[variant]["use_adasyn"]):
        fit_kwargs["sample_weight"] = build_attack_sample_weight(fit_y)

    estimator.fit(fit_x, fit_y, **fit_kwargs)
    return {"fit_x": fit_x, "fit_y": fit_y, "adasyn_summary": adasyn_summary, "fit_kwargs": list(fit_kwargs.keys())}


def predict_probs_estimator(estimator: Any, x: np.ndarray) -> np.ndarray:
    probs = estimator.predict_proba(x)
    return ensure_prob_matrix(probs, np.asarray(estimator.classes_), num_classes=len(STAGE2_NAMES))


def plot_head_tradeoff(summary_frame: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    for _, row in summary_frame.iterrows():
        ax.scatter(row["end_de_f1_mean"], row["end_recon_f1_mean"], s=90)
        ax.annotate(str(row["variant"]), (row["end_de_f1_mean"], row["end_recon_f1_mean"]))
    ax.set_xlabel("End-to-End DE F1 Mean")
    ax.set_ylabel("End-to-End Recon F1 Mean")
    ax.set_title("Stage 2 Tree Head Tradeoff")
    ax.grid(True, alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_head_macro(summary_frame: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.bar(
        summary_frame["variant"],
        summary_frame["end_macro_f1_mean"],
        yerr=summary_frame["end_macro_f1_std"].fillna(0.0),
        capsize=4,
        color="#5dade2",
    )
    ax.set_ylabel("End-to-End Macro F1")
    ax.set_title("Stage 2 Tree Head End-to-End Macro F1")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, axis="y", alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds)
    variants = parse_variants(args.variants)
    device = torch.device("cpu")
    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must define fixed_model_params for MLP.")

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, cache_path, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
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

    full_test_x = test_df[feature_cols].values.astype(np.float32)
    attack_train_mask = train_df["MultiLabel"].values != 0
    attack_test_mask = test_df["MultiLabel"].values != 0
    train_x_stage2 = train_df.loc[attack_train_mask, feature_cols].values.astype(np.float32)
    test_x_stage2 = test_df.loc[attack_test_mask, feature_cols].values.astype(np.float32)
    train_y_stage2 = train_df.loc[attack_train_mask, "MultiLabel"].values.astype(np.int64) - 1
    test_y_stage2 = test_df.loc[attack_test_mask, "MultiLabel"].values.astype(np.int64) - 1

    reference_single = pd.read_csv(v02.resolve_path(repo_root, args.reference_single_csv))
    reference_single = reference_single[reference_single["variant"] == "adasyn_weighted_ce"].sort_values("seed")

    reference_cascade = pd.read_csv(v02.resolve_path(repo_root, args.reference_cascade_csv))
    reference_cascade = reference_cascade[
        (reference_cascade["family"] == "adasyn_weighted_ce")
        & (reference_cascade["de_multiplier"] == 1.0)
    ].sort_values("seed")

    stage1_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
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
            settings=settings,
            device=device,
        )
        val_stage1_probs = predict_probs(
            stage1_model,
            val_x_stage1,
            val_binary_y,
            int(settings["tabular_batch_size"]),
            device,
        )
        test_stage1_probs = predict_probs(
            stage1_model,
            test_x_stage1,
            test_binary_y,
            int(settings["tabular_batch_size"]),
            device,
        )
        threshold_row = choose_threshold(val_original_y, val_binary_y, val_stage1_probs)
        stage1_cache[int(seed)] = {
            "threshold": float(threshold_row["threshold"]),
            "test_stage1_probs": test_stage1_probs,
        }
        stage1_rows.append(
            {
                "seed": int(seed),
                "candidate": str(args.candidate),
                "threshold": float(threshold_row["threshold"]),
                "val_attack_recall": float(threshold_row["val_attack_recall"]),
                "val_benign_f1": float(threshold_row["val_benign_f1"]),
                "val_recon_attack_recall": float(threshold_row["val_recon_attack_recall"]),
            }
        )

    for variant in variants:
        print(f"\nRunning Stage 2 head variant `{variant}`...")
        for seed in seeds:
            set_seed(seed)
            estimator = instantiate_estimator(variant, seed)
            fit_summary = fit_variant(
                variant=variant,
                estimator=estimator,
                train_x=train_x_stage2,
                train_y=train_y_stage2,
            )

            attack_probs = predict_probs_estimator(estimator, test_x_stage2)
            attack_pred = np.argmax(attack_probs, axis=1)
            attack_metrics = v02.compute_metrics(test_y_stage2, attack_pred, attack_probs, STAGE2_NAMES)
            attack_per_class = {
                name: value for name, value in compute_per_class_f1(test_y_stage2 + 1, attack_pred + 1).items() if name != "Benign"
            }

            full_stage2_probs = predict_probs_estimator(estimator, full_test_x)
            end_pred, end_probs = build_end_to_end_outputs(
                stage1_probs=stage1_cache[int(seed)]["test_stage1_probs"],
                stage2_probs=full_stage2_probs,
                threshold=float(stage1_cache[int(seed)]["threshold"]),
            )
            end_metrics = v02.compute_metrics(test_original_y, end_pred, end_probs, v02.STAGE_NAMES)
            end_per_class = compute_per_class_f1(test_original_y, end_pred)

            prev_row = reference_cascade[reference_cascade["seed"] == int(seed)].iloc[0]
            single_row = reference_single[reference_single["seed"] == int(seed)].iloc[0]

            raw_rows.append(
                {
                    "variant": variant,
                    "seed": int(seed),
                    "family": str(VARIANT_DEFS[variant]["family"]),
                    "uses_adasyn": bool(VARIANT_DEFS[variant]["use_adasyn"]),
                    "threshold": float(stage1_cache[int(seed)]["threshold"]),
                    "attack_accuracy": float(attack_metrics["accuracy"]),
                    "attack_macro_f1": float(attack_metrics["f1"]),
                    "attack_pr_auc": float(attack_metrics["pr_auc"]) if attack_metrics["pr_auc"] is not None else np.nan,
                    "attack_recon_f1": float(attack_per_class["Reconnaissance"]),
                    "attack_de_f1": float(attack_per_class["Data Exfiltration"]),
                    "end_accuracy": float(end_metrics["accuracy"]),
                    "end_macro_f1": float(end_metrics["f1"]),
                    "end_pr_auc": float(end_metrics["pr_auc"]) if end_metrics["pr_auc"] is not None else np.nan,
                    "end_recon_f1": float(end_per_class["Reconnaissance"]),
                    "end_de_f1": float(end_per_class["Data Exfiltration"]),
                    "delta_vs_prev_end_macro": float(end_metrics["f1"] - prev_row["end_macro_f1"]),
                    "delta_vs_prev_end_de": float(end_per_class["Data Exfiltration"] - prev_row["end_de_f1"]),
                    "delta_vs_single_end_macro": float(end_metrics["f1"] - single_row["macro_f1"]),
                    "delta_vs_single_end_de": float(end_per_class["Data Exfiltration"] - single_row["de_f1"]),
                }
            )

            artifact_dir = run_dir / "seed_runs" / variant / f"seed_{seed}"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_dir / "results.json",
                {
                    "variant": variant,
                    "seed": int(seed),
                    "family": str(VARIANT_DEFS[variant]["family"]),
                    "uses_adasyn": bool(VARIANT_DEFS[variant]["use_adasyn"]),
                    "fit_summary": fit_summary,
                    "attack_only_test_metrics": attack_metrics,
                    "attack_only_test_per_class_f1": attack_per_class,
                    "end_to_end_test_metrics": end_metrics,
                    "end_to_end_test_per_class_f1": end_per_class,
                },
            )

    stage1_frame = pd.DataFrame(stage1_rows).sort_values("seed").reset_index(drop=True)
    stage1_frame.to_csv(run_dir / "stage1_fixed.csv", index=False)

    raw_frame = pd.DataFrame(raw_rows).sort_values(["variant", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(run_dir / "raw_results.csv", index=False)

    summary_frame = raw_frame.groupby("variant").agg(
        family=("family", "first"),
        uses_adasyn=("uses_adasyn", "first"),
        end_accuracy_mean=("end_accuracy", "mean"),
        end_accuracy_std=("end_accuracy", "std"),
        end_macro_f1_mean=("end_macro_f1", "mean"),
        end_macro_f1_std=("end_macro_f1", "std"),
        end_pr_auc_mean=("end_pr_auc", "mean"),
        end_pr_auc_std=("end_pr_auc", "std"),
        end_recon_f1_mean=("end_recon_f1", "mean"),
        end_recon_f1_std=("end_recon_f1", "std"),
        end_de_f1_mean=("end_de_f1", "mean"),
        end_de_f1_std=("end_de_f1", "std"),
        delta_vs_prev_end_macro_mean=("delta_vs_prev_end_macro", "mean"),
        delta_vs_prev_end_de_mean=("delta_vs_prev_end_de", "mean"),
        delta_vs_single_end_macro_mean=("delta_vs_single_end_macro", "mean"),
        delta_vs_single_end_de_mean=("delta_vs_single_end_de", "mean"),
    ).reset_index()
    summary_frame = summary_frame.sort_values(
        ["end_macro_f1_mean", "end_de_f1_mean"],
        ascending=[False, False],
    ).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    plot_head_tradeoff(summary_frame, run_dir / "tree_head_tradeoff.png")
    plot_head_macro(summary_frame, run_dir / "tree_head_macro.png")

    decision = {
        "best_variant": summary_frame.iloc[0].to_dict(),
        "beats_prior_cascade_macro": bool((summary_frame["delta_vs_prev_end_macro_mean"] > 0.0).any()),
        "beats_prior_cascade_de": bool((summary_frame["delta_vs_prev_end_de_mean"] > 0.0).any()),
        "beats_single_stage_with_de_hold": bool(
            ((summary_frame["delta_vs_single_end_macro_mean"] > 0.0) & (summary_frame["delta_vs_single_end_de_mean"] >= -0.10)).any()
        ),
    }
    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "candidate": str(args.candidate),
            "variants": variants,
            "cache_path": str(cache_path),
            "preprocess_summary": preprocess_summary,
            "stage1_rows": stage1_frame.to_dict(orient="records"),
            "summary_rows": summary_frame.to_dict(orient="records"),
            "decision": decision,
        },
    )

    report_lines = [
        "# Stage 2 Tree Head Suite",
        "",
        f"Config: `{config_path.name}`",
        f"Candidate: `{args.candidate}`",
        f"Variants: `{', '.join(variants)}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Raw results: {run_dir / 'raw_results.csv'}")
    print(f"Summary: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
