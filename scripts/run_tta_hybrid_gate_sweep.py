from __future__ import annotations

import argparse
import copy
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

from scripts.run_tta_streaming_apt_pilot import (
    adapt_bn_stats,
    adapt_tent_stream,
    compute_per_class_f1,
    instantiate_mlp,
    load_settings,
    metric_row,
    parse_float_csv,
    parse_seeds,
    predict_probs,
    render_markdown_table,
    write_json,
)


RECON_LABEL = 1
DE_LABEL = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validation-select a conservative hybrid gate between frozen MLP predictions "
            "and TTA predictions. The gate protects high-confidence DE predictions while "
            "allowing TTA to rescue uncertain or likely-Recon rows."
        )
    )
    parser.add_argument("--source-run-dir", default="runs/mlp-support-floor-3seed-ablation-20260423")
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--run-name", default="tta-hybrid-gate-sweep-20260509")
    parser.add_argument("--config", default=None)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--tta-methods", default="bn_adapt,tent_lr0.0001")
    parser.add_argument("--uncertainty-thresholds", default="0.50,0.60,0.70,0.80,0.90,0.95")
    parser.add_argument("--recon-rescue-thresholds", default="0.40,0.50,0.60,0.70,0.80,0.90")
    parser.add_argument("--de-keep-thresholds", default="0.00,0.50,0.70,0.90")
    parser.add_argument("--de-delta-limits", default="0.05,0.10,0.20")
    parser.add_argument("--tent-steps", type=int, default=1)
    return parser.parse_args()


def parse_methods(raw: str) -> list[str]:
    methods = [item.strip() for item in raw.split(",") if item.strip()]
    if not methods:
        raise ValueError("At least one TTA method is required.")
    for method in methods:
        if method != "bn_adapt" and not method.startswith("tent_lr"):
            raise ValueError(f"Unsupported method `{method}`. Use `bn_adapt` or `tent_lr<lr>`.")
    return methods


def method_probs(
    method: str,
    base_state: dict[str, Any],
    feature_count: int,
    mlp_params: dict[str, Any],
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
    tent_steps: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    model = instantiate_mlp(feature_count=feature_count, params=mlp_params).to(device)
    model.load_state_dict(copy.deepcopy(base_state))
    if method == "bn_adapt":
        return adapt_bn_stats(model, x, batch_size, device), {}
    if method.startswith("tent_lr"):
        lr = float(method.replace("tent_lr", ""))
        probs, details = adapt_tent_stream(
            model=model,
            x=x,
            batch_size=batch_size,
            device=device,
            lr=lr,
            steps=int(tent_steps),
            confidence_threshold=None,
        )
        return probs, details
    raise ValueError(f"Unknown TTA method: {method}")


def hybrid_probs(
    frozen_probs: np.ndarray,
    tta_probs: np.ndarray,
    uncertainty_threshold: float,
    recon_rescue_threshold: float,
    de_keep_threshold: float,
) -> tuple[np.ndarray, dict[str, Any]]:
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

    out = frozen_probs.copy()
    out[use_tta] = tta_probs[use_tta]
    return out, {
        "override_rate": float(use_tta.mean()),
        "uncertain_override_rate": float(uncertain_override.mean()),
        "recon_rescue_rate": float(recon_rescue.mean()),
        "protected_de_rate": float(protected_de.mean()),
    }


def evaluate_probs(
    method: str,
    seed: int,
    split: str,
    y: np.ndarray,
    probs: np.ndarray,
    extra: dict[str, Any],
) -> dict[str, Any]:
    pred = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y, pred, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y, pred)
    return metric_row(method, seed, split, metrics, per_class, extra)


def select_policy(frame: pd.DataFrame, policy: str) -> pd.Series:
    allowed = frame[frame["allowed"]].copy()
    if allowed.empty:
        allowed = frame.copy()
    if policy == "macro_guarded":
        order_cols = ["val_macro_f1", "val_de_f1", "val_recon_f1", "override_rate_val"]
    elif policy == "recon_guarded":
        order_cols = ["val_recon_f1", "val_macro_f1", "val_de_f1", "override_rate_val"]
    elif policy == "balanced_guarded":
        order_cols = ["val_recon_de_min_f1", "val_macro_f1", "val_recon_f1", "val_de_f1"]
    else:
        raise ValueError(f"Unknown policy: {policy}")
    return allowed.sort_values(order_cols, ascending=[False] * len(order_cols)).iloc[0]


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    source_summary = json.loads((source_run_dir / "summary.json").read_text(encoding="utf-8"))
    config_path = Path(args.config).resolve() if args.config else Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds) if str(args.seeds).strip() else [int(seed) for seed in source_summary["seeds"]]
    tta_methods = parse_methods(args.tta_methods)
    uncertainty_thresholds = parse_float_csv(args.uncertainty_thresholds)
    recon_rescue_thresholds = parse_float_csv(args.recon_rescue_thresholds)
    de_keep_thresholds = parse_float_csv(args.de_keep_thresholds)
    de_delta_limits = parse_float_csv(args.de_delta_limits)
    batch_size = int(args.batch_size)
    device = torch.device("cpu")

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")

    print(f"Loading trusted split from {config_path}...")
    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    _train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=run_dir,
    )
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    sweep_rows: list[dict[str, Any]] = []
    frozen_rows: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"\nSeed {seed}: building frozen/TTA probability caches and sweeping gates...")
        state_path = source_run_dir / "seed_runs" / str(args.variant) / f"seed_{seed}" / "mlp_state_dict.pt"
        if not state_path.exists():
            raise FileNotFoundError(f"Missing checkpoint: {state_path}")
        base_model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params).to(device)
        base_model.load_state_dict(torch.load(state_path, map_location=device))
        base_state = copy.deepcopy(base_model.state_dict())

        frozen_val = predict_probs(base_model, val_x, batch_size, device)
        frozen_test = predict_probs(base_model, test_x, batch_size, device)
        frozen_rows.append(evaluate_probs("frozen", seed, "val", val_y, frozen_val, {}))
        frozen_rows.append(evaluate_probs("frozen", seed, "test", test_y, frozen_test, {}))
        frozen_val_per_class = compute_per_class_f1(val_y, np.argmax(frozen_val, axis=1))

        for tta_method in tta_methods:
            tta_val, val_details = method_probs(
                tta_method,
                base_state,
                len(feature_cols),
                mlp_params,
                val_x,
                batch_size,
                device,
                int(args.tent_steps),
            )
            tta_test, test_details = method_probs(
                tta_method,
                base_state,
                len(feature_cols),
                mlp_params,
                test_x,
                batch_size,
                device,
                int(args.tent_steps),
            )

            for de_delta_limit in de_delta_limits:
                de_floor = max(float(frozen_val_per_class[v02.STAGE_NAMES[DE_LABEL]]) - float(de_delta_limit), 0.0)
                for uncertainty_threshold in uncertainty_thresholds:
                    for recon_rescue_threshold in recon_rescue_thresholds:
                        for de_keep_threshold in de_keep_thresholds:
                            val_hybrid, val_gate = hybrid_probs(
                                frozen_val,
                                tta_val,
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
                            val_metrics = v02.compute_metrics(val_y, val_pred, val_hybrid, v02.STAGE_NAMES)
                            test_metrics = v02.compute_metrics(test_y, test_pred, test_hybrid, v02.STAGE_NAMES)
                            val_per_class = compute_per_class_f1(val_y, val_pred)
                            test_per_class = compute_per_class_f1(test_y, test_pred)

                            sweep_rows.append(
                                {
                                    "seed": int(seed),
                                    "tta_method": tta_method,
                                    "de_delta_limit": float(de_delta_limit),
                                    "de_floor": float(de_floor),
                                    "uncertainty_threshold": float(uncertainty_threshold),
                                    "recon_rescue_threshold": float(recon_rescue_threshold),
                                    "de_keep_threshold": float(de_keep_threshold),
                                    "val_accuracy": float(val_metrics["accuracy"]),
                                    "val_macro_f1": float(val_metrics["f1"]),
                                    "val_pr_auc": float(val_metrics["pr_auc"])
                                    if val_metrics["pr_auc"] is not None
                                    else np.nan,
                                    "val_benign_f1": float(val_per_class[v02.STAGE_NAMES[0]]),
                                    "val_recon_f1": float(val_per_class[v02.STAGE_NAMES[RECON_LABEL]]),
                                    "val_de_f1": float(val_per_class[v02.STAGE_NAMES[DE_LABEL]]),
                                    "val_recon_de_min_f1": float(
                                        min(
                                            val_per_class[v02.STAGE_NAMES[RECON_LABEL]],
                                            val_per_class[v02.STAGE_NAMES[DE_LABEL]],
                                        )
                                    ),
                                    "test_accuracy": float(test_metrics["accuracy"]),
                                    "test_macro_f1": float(test_metrics["f1"]),
                                    "test_pr_auc": float(test_metrics["pr_auc"])
                                    if test_metrics["pr_auc"] is not None
                                    else np.nan,
                                    "test_benign_f1": float(test_per_class[v02.STAGE_NAMES[0]]),
                                    "test_recon_f1": float(test_per_class[v02.STAGE_NAMES[RECON_LABEL]]),
                                    "test_de_f1": float(test_per_class[v02.STAGE_NAMES[DE_LABEL]]),
                                    "allowed": bool(float(val_per_class[v02.STAGE_NAMES[DE_LABEL]]) >= de_floor),
                                    "override_rate_val": float(val_gate["override_rate"]),
                                    "recon_rescue_rate_val": float(val_gate["recon_rescue_rate"]),
                                    "protected_de_rate_val": float(val_gate["protected_de_rate"]),
                                    "override_rate_test": float(test_gate["override_rate"]),
                                    "recon_rescue_rate_test": float(test_gate["recon_rescue_rate"]),
                                    "protected_de_rate_test": float(test_gate["protected_de_rate"]),
                                    "val_update_batches": int(val_details.get("update_batches", 0)),
                                    "test_update_batches": int(test_details.get("update_batches", 0)),
                                }
                            )

    sweep_frame = pd.DataFrame(sweep_rows)
    sweep_frame.to_csv(run_dir / "hybrid_gate_sweep_raw.csv", index=False)
    frozen_frame = pd.DataFrame(frozen_rows)
    frozen_frame.to_csv(run_dir / "frozen_reference_raw.csv", index=False)

    policies = ["macro_guarded", "recon_guarded", "balanced_guarded"]
    selected_rows: list[dict[str, Any]] = []
    for (seed, tta_method, de_delta_limit), group in sweep_frame.groupby(["seed", "tta_method", "de_delta_limit"]):
        frozen_test = frozen_frame[
            (frozen_frame["seed"] == int(seed)) & (frozen_frame["split"] == "test")
        ].iloc[0]
        for policy in policies:
            selected = select_policy(group.reset_index(drop=True), policy)
            row = {"policy": policy, **selected.to_dict()}
            for metric in ["accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]:
                row[f"test_{metric}_delta_vs_frozen"] = float(row[f"test_{metric}"] - frozen_test[metric])
            selected_rows.append(row)

    selected_frame = pd.DataFrame(selected_rows).sort_values(
        ["policy", "tta_method", "de_delta_limit", "seed"]
    )
    selected_frame.to_csv(run_dir / "selected_hybrid_policies.csv", index=False)

    summary_frame = (
        selected_frame.groupby(["policy", "tta_method", "de_delta_limit"])
        .agg(
            test_accuracy_mean=("test_accuracy", "mean"),
            test_accuracy_std=("test_accuracy", "std"),
            test_macro_f1_mean=("test_macro_f1", "mean"),
            test_macro_f1_std=("test_macro_f1", "std"),
            test_pr_auc_mean=("test_pr_auc", "mean"),
            test_pr_auc_std=("test_pr_auc", "std"),
            test_benign_f1_mean=("test_benign_f1", "mean"),
            test_recon_f1_mean=("test_recon_f1", "mean"),
            test_de_f1_mean=("test_de_f1", "mean"),
            test_macro_f1_delta_vs_frozen_mean=("test_macro_f1_delta_vs_frozen", "mean"),
            test_recon_f1_delta_vs_frozen_mean=("test_recon_f1_delta_vs_frozen", "mean"),
            test_de_f1_delta_vs_frozen_mean=("test_de_f1_delta_vs_frozen", "mean"),
            override_rate_test_mean=("override_rate_test", "mean"),
        )
        .reset_index()
    )
    summary_frame = summary_frame.sort_values(
        ["test_macro_f1_mean", "test_de_f1_mean", "test_recon_f1_mean"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    best = summary_frame.iloc[0].to_dict()
    decision = {
        "best_by_macro": best,
        "any_macro_gain": bool((summary_frame["test_macro_f1_delta_vs_frozen_mean"] > 0).any()),
        "any_recon_gain_with_de_drop_under_10pts": bool(
            (
                (summary_frame["test_recon_f1_delta_vs_frozen_mean"] > 0)
                & (summary_frame["test_de_f1_delta_vs_frozen_mean"] >= -0.10)
            ).any()
        ),
        "any_recon_gain_with_macro_nonnegative": bool(
            (
                (summary_frame["test_recon_f1_delta_vs_frozen_mean"] > 0)
                & (summary_frame["test_macro_f1_delta_vs_frozen_mean"] >= 0)
            ).any()
        ),
    }

    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_run_dir": str(source_run_dir),
            "variant": str(args.variant),
            "config_path": str(config_path),
            "seeds": seeds,
            "tta_methods": tta_methods,
            "uncertainty_thresholds": uncertainty_thresholds,
            "recon_rescue_thresholds": recon_rescue_thresholds,
            "de_keep_thresholds": de_keep_thresholds,
            "de_delta_limits": de_delta_limits,
            "preprocess_summary": preprocess_summary,
            "decision": decision,
        },
    )

    report_lines = [
        "# TTA Hybrid Gate Sweep",
        "",
        f"Source checkpoints: `{source_run_dir}`",
        f"Variant: `{args.variant}`",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
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

    print(f"Raw sweep: {run_dir / 'hybrid_gate_sweep_raw.csv'}")
    print(f"Selected policies: {run_dir / 'selected_hybrid_policies.csv'}")
    print(f"Summary: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
