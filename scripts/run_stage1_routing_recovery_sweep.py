from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03

from scripts.run_two_stage_feature_subset_revision import (
    build_end_to_end_outputs,
    build_feature_subsets,
    choose_threshold,
    compute_per_class_f1,
    compute_recon_auc_scores,
    parse_seeds,
    predict_probs,
    render_markdown_table,
    set_seed,
    train_stage1_mlp,
    write_json,
)


STAGE2_NAMES = v02.STAGE_NAMES[1:]
BENIGN_STAGE = v02.STAGE_NAMES[0]
RECON_STAGE = v02.STAGE_NAMES[1]
FOOTHOLD_STAGE = v02.STAGE_NAMES[2]
LM_STAGE = v02.STAGE_NAMES[3]
DE_STAGE = v02.STAGE_NAMES[4]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Retrain the Stage 1 router, reuse frozen Stage 2 checkpoints, and sweep "
            "Stage 1 routing thresholds to test whether the two-stage cascade can "
            "recover DE without losing the Recon gain."
        )
    )
    parser.add_argument(
        "--source-run-dir",
        default="runs/stage2-end2end-selection-suite-20260428",
        help="End-to-end Stage 2 suite containing nested Stage 2 checkpoints.",
    )
    parser.add_argument(
        "--run-name",
        default="stage1-routing-recovery-sweep-20260509",
        help="Output directory name under the configured output_dir.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Optional config override. Defaults to source run summary config_path.",
    )
    parser.add_argument("--seeds", default="", help="Optional comma-separated seeds. Defaults to source summary seeds.")
    parser.add_argument(
        "--stage2-variant",
        default="adasyn_weighted_ce_de1p00",
        help="Nested checkpoint folder under source-run-dir/seed_runs.",
    )
    parser.add_argument("--candidate", default="recon_top30", help="Stage 1 feature-subset candidate.")
    parser.add_argument("--threshold-start", type=float, default=0.01)
    parser.add_argument("--threshold-stop", type=float, default=0.60)
    parser.add_argument("--threshold-step", type=float, default=0.01)
    parser.add_argument(
        "--benign-delta-limits",
        default="0.02,0.05,0.10",
        help="Comma-separated validation Benign F1 drops allowed from threshold 0.50.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage reference raw seed results CSV.",
    )
    parser.add_argument("--reference-variant", default="adasyn_weighted_ce")
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    return parser.parse_args()


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def parse_float_csv(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one float value is required.")
    return values


def build_thresholds(start: float, stop: float, step: float) -> np.ndarray:
    thresholds = np.arange(start, stop + step * 0.5, step)
    thresholds = np.round(thresholds, 4)
    if not np.any(np.isclose(thresholds, 0.5)):
        thresholds = np.sort(np.append(thresholds, 0.5))
    return thresholds


def instantiate_stage2_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(STAGE2_NAMES),
    )


def predict_stage2_probs(
    model: torch.nn.Module,
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = torch.utils.data.DataLoader(
        v02.RowDataset(x, np.zeros(len(x), dtype=np.int64)),
        batch_size=batch_size,
        shuffle=False,
    )
    model.eval()
    probs_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs, _ys in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs_list.append(torch.softmax(logits, dim=1).cpu().numpy())
    return np.vstack(probs_list)


def select_policy(frame: pd.DataFrame, policy: str) -> pd.Series:
    allowed = frame[frame["allowed"]].copy()
    if allowed.empty:
        allowed = frame.copy()

    if policy == "macro_guarded":
        order_cols = ["val_macro_f1", "val_de_f1", "val_recon_f1", "threshold"]
    elif policy == "recon_guarded":
        order_cols = ["val_recon_f1", "val_macro_f1", "val_de_f1", "threshold"]
    elif policy == "de_recovery_guarded":
        order_cols = ["val_de_f1", "val_macro_f1", "val_recon_f1", "threshold"]
    elif policy == "balanced_recon_de_guarded":
        order_cols = ["val_recon_de_min_f1", "val_macro_f1", "val_recon_f1", "val_de_f1", "threshold"]
    else:
        raise ValueError(f"Unknown policy: {policy}")

    return allowed.sort_values(order_cols, ascending=[False] * len(order_cols)).iloc[0]


def add_delta_columns(
    row: dict[str, Any],
    single_stage_row: pd.Series,
    previous_two_stage_row: pd.Series,
) -> dict[str, Any]:
    row["test_macro_delta_vs_single_stage"] = float(row["test_macro_f1"] - single_stage_row["macro_f1"])
    row["test_recon_delta_vs_single_stage"] = float(row["test_recon_f1"] - single_stage_row["recon_f1"])
    row["test_de_delta_vs_single_stage"] = float(row["test_de_f1"] - single_stage_row["de_f1"])
    row["test_macro_delta_vs_previous_two_stage"] = float(row["test_macro_f1"] - previous_two_stage_row["end_macro_f1"])
    row["test_recon_delta_vs_previous_two_stage"] = float(row["test_recon_f1"] - previous_two_stage_row["end_recon_f1"])
    row["test_de_delta_vs_previous_two_stage"] = float(row["test_de_f1"] - previous_two_stage_row["end_de_f1"])
    return row


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    source_summary = json.loads((source_run_dir / "summary.json").read_text(encoding="utf-8"))
    config_path = Path(args.config).resolve() if args.config else Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    if str(args.seeds).strip():
        seeds = parse_seeds(args.seeds)
    elif "seeds" in source_summary:
        seeds = [int(seed) for seed in source_summary["seeds"]]
    else:
        source_raw = pd.read_csv(source_run_dir / "raw_results.csv")
        seeds = sorted(int(seed) for seed in source_raw["seed"].unique())
    benign_delta_limits = parse_float_csv(args.benign_delta_limits)
    thresholds = build_thresholds(args.threshold_start, args.threshold_stop, args.threshold_step)
    device = torch.device("cpu")

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")

    print(f"Loading trusted split from {config_path}...")
    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
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
        raise ValueError(f"Unknown candidate {args.candidate}. Available: {sorted(candidates)}")
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

    reference_single = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    reference_single = reference_single[reference_single["variant"] == str(args.reference_variant)]
    previous_two_stage = pd.read_csv(source_run_dir / "raw_results.csv")
    previous_two_stage = previous_two_stage[previous_two_stage["variant"] == str(args.stage2_variant)]

    sweep_rows: list[dict[str, Any]] = []
    threshold_reference_rows: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"\nSeed {seed}: training Stage 1 router and loading Stage 2 `{args.stage2_variant}`...")
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
        val_stage1_probs = predict_probs(stage1_model, val_x_stage1, val_binary_y, int(settings["tabular_batch_size"]), device)
        test_stage1_probs = predict_probs(
            stage1_model, test_x_stage1, test_binary_y, int(settings["tabular_batch_size"]), device
        )
        prior_threshold = float(choose_threshold(val_original_y, val_binary_y, val_stage1_probs)["threshold"])
        threshold_reference_rows.append({"seed": int(seed), "prior_stage1_threshold": prior_threshold})

        stage2_path = source_run_dir / "seed_runs" / str(args.stage2_variant) / f"seed_{seed}" / "stage2_state_dict.pt"
        if not stage2_path.exists():
            raise FileNotFoundError(f"Missing Stage 2 checkpoint: {stage2_path}")
        stage2_model = instantiate_stage2_mlp(feature_count=len(feature_cols), params=mlp_params).to(device)
        stage2_model.load_state_dict(torch.load(stage2_path, map_location=device))
        val_stage2_probs = predict_stage2_probs(
            stage2_model,
            full_val_x,
            int(settings["tabular_batch_size"]),
            device,
        )
        test_stage2_probs = predict_stage2_probs(
            stage2_model,
            full_test_x,
            int(settings["tabular_batch_size"]),
            device,
        )

        val_pred_050, _ = build_end_to_end_outputs(val_stage1_probs, val_stage2_probs, threshold=0.5)
        val_per_class_050 = compute_per_class_f1(val_original_y, val_pred_050)
        floors = {
            delta: max(float(val_per_class_050[BENIGN_STAGE]) - float(delta), 0.0)
            for delta in benign_delta_limits
        }

        for threshold in thresholds:
            val_pred, val_probs = build_end_to_end_outputs(val_stage1_probs, val_stage2_probs, threshold=float(threshold))
            test_pred, test_probs = build_end_to_end_outputs(
                test_stage1_probs, test_stage2_probs, threshold=float(threshold)
            )
            val_metrics = v02.compute_metrics(val_original_y, val_pred, val_probs, v02.STAGE_NAMES)
            test_metrics = v02.compute_metrics(test_original_y, test_pred, test_probs, v02.STAGE_NAMES)
            val_per_class = compute_per_class_f1(val_original_y, val_pred)
            test_per_class = compute_per_class_f1(test_original_y, test_pred)

            for delta_limit, benign_floor in floors.items():
                sweep_rows.append(
                    {
                        "seed": int(seed),
                        "stage2_variant": str(args.stage2_variant),
                        "benign_delta_limit": float(delta_limit),
                        "benign_floor": float(benign_floor),
                        "threshold": float(threshold),
                        "is_prior_stage1_threshold": bool(np.isclose(threshold, prior_threshold)),
                        "val_accuracy": float(val_metrics["accuracy"]),
                        "val_macro_f1": float(val_metrics["f1"]),
                        "val_pr_auc": float(val_metrics["pr_auc"]) if val_metrics["pr_auc"] is not None else np.nan,
                        "val_benign_f1": float(val_per_class[BENIGN_STAGE]),
                        "val_recon_f1": float(val_per_class[RECON_STAGE]),
                        "val_foothold_f1": float(val_per_class[FOOTHOLD_STAGE]),
                        "val_lm_f1": float(val_per_class[LM_STAGE]),
                        "val_de_f1": float(val_per_class[DE_STAGE]),
                        "val_recon_de_min_f1": float(
                            min(val_per_class[RECON_STAGE], val_per_class[DE_STAGE])
                        ),
                        "test_accuracy": float(test_metrics["accuracy"]),
                        "test_macro_f1": float(test_metrics["f1"]),
                        "test_pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                        "test_benign_f1": float(test_per_class[BENIGN_STAGE]),
                        "test_recon_f1": float(test_per_class[RECON_STAGE]),
                        "test_foothold_f1": float(test_per_class[FOOTHOLD_STAGE]),
                        "test_lm_f1": float(test_per_class[LM_STAGE]),
                        "test_de_f1": float(test_per_class[DE_STAGE]),
                        "allowed": bool(float(val_per_class[BENIGN_STAGE]) >= benign_floor),
                    }
                )

    sweep_frame = pd.DataFrame(sweep_rows).sort_values(["seed", "benign_delta_limit", "threshold"]).reset_index(drop=True)
    sweep_frame.to_csv(run_dir / "routing_threshold_sweep_raw.csv", index=False)
    pd.DataFrame(threshold_reference_rows).to_csv(run_dir / "prior_stage1_thresholds.csv", index=False)

    policies = ["macro_guarded", "recon_guarded", "de_recovery_guarded", "balanced_recon_de_guarded"]
    selected_rows: list[dict[str, Any]] = []
    for (seed, delta_limit), seed_frame in sweep_frame.groupby(["seed", "benign_delta_limit"]):
        single_stage_row = reference_single[reference_single["seed"] == int(seed)].iloc[0]
        previous_row = previous_two_stage[previous_two_stage["seed"] == int(seed)].iloc[0]
        for policy in policies:
            chosen = select_policy(seed_frame.reset_index(drop=True), policy)
            row = {"policy": policy, **chosen.to_dict()}
            selected_rows.append(add_delta_columns(row, single_stage_row, previous_row))

    selected_frame = pd.DataFrame(selected_rows).sort_values(["policy", "benign_delta_limit", "seed"]).reset_index(drop=True)
    selected_frame.to_csv(run_dir / "selected_routing_policies.csv", index=False)

    summary_frame = selected_frame.groupby(["policy", "benign_delta_limit"]).agg(
        threshold_mean=("threshold", "mean"),
        threshold_std=("threshold", "std"),
        test_accuracy_mean=("test_accuracy", "mean"),
        test_accuracy_std=("test_accuracy", "std"),
        test_macro_f1_mean=("test_macro_f1", "mean"),
        test_macro_f1_std=("test_macro_f1", "std"),
        test_pr_auc_mean=("test_pr_auc", "mean"),
        test_pr_auc_std=("test_pr_auc", "std"),
        test_benign_f1_mean=("test_benign_f1", "mean"),
        test_recon_f1_mean=("test_recon_f1", "mean"),
        test_de_f1_mean=("test_de_f1", "mean"),
        test_macro_delta_vs_single_stage_mean=("test_macro_delta_vs_single_stage", "mean"),
        test_recon_delta_vs_single_stage_mean=("test_recon_delta_vs_single_stage", "mean"),
        test_de_delta_vs_single_stage_mean=("test_de_delta_vs_single_stage", "mean"),
        test_macro_delta_vs_previous_two_stage_mean=("test_macro_delta_vs_previous_two_stage", "mean"),
        test_recon_delta_vs_previous_two_stage_mean=("test_recon_delta_vs_previous_two_stage", "mean"),
        test_de_delta_vs_previous_two_stage_mean=("test_de_delta_vs_previous_two_stage", "mean"),
    ).reset_index()
    summary_frame = summary_frame.sort_values(
        ["test_macro_f1_mean", "test_de_f1_mean", "test_recon_f1_mean"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    decision = {
        "best_by_macro": summary_frame.iloc[0].to_dict(),
        "any_policy_improves_previous_macro": bool(
            (summary_frame["test_macro_delta_vs_previous_two_stage_mean"] > 0.0).any()
        ),
        "any_policy_improves_previous_de": bool((summary_frame["test_de_delta_vs_previous_two_stage_mean"] > 0.0).any()),
        "any_policy_keeps_recon_gain_and_de_within_10pts_single": bool(
            (
                (summary_frame["test_recon_delta_vs_single_stage_mean"] > 0.25)
                & (summary_frame["test_de_delta_vs_single_stage_mean"] >= -0.10)
            ).any()
        ),
    }

    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_run_dir": str(source_run_dir),
            "stage2_variant": str(args.stage2_variant),
            "config_path": str(config_path),
            "candidate": str(args.candidate),
            "seeds": seeds,
            "threshold_range": {
                "start": float(args.threshold_start),
                "stop": float(args.threshold_stop),
                "step": float(args.threshold_step),
            },
            "benign_delta_limits": benign_delta_limits,
            "preprocess_summary": preprocess_summary,
            "decision": decision,
        },
    )

    report_lines = [
        "# Stage 1 Routing Recovery Sweep",
        "",
        f"Source Stage 2 run: `{source_run_dir}`",
        f"Stage 2 variant: `{args.stage2_variant}`",
        f"Config: `{config_path.name}`",
        f"Stage 1 candidate: `{args.candidate}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Selected Policies",
        "",
        render_markdown_table(selected_frame),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Raw sweep: {run_dir / 'routing_threshold_sweep_raw.csv'}")
    print(f"Selected policies: {run_dir / 'selected_routing_policies.csv'}")
    print(f"Summary: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
