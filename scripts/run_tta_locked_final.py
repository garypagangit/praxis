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

from scripts.run_tta_hybrid_gate_sweep import (
    DE_LABEL,
    RECON_LABEL,
    hybrid_probs,
    method_probs,
)
from scripts.run_tta_streaming_apt_pilot import (
    compute_per_class_f1,
    instantiate_mlp,
    load_settings,
    metric_row,
    predict_probs,
    render_markdown_table,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a locked TTA policy selected from validation-only sweep artifacts."
    )
    parser.add_argument(
        "--source-run-dir", default="runs/mlp-support-floor-3seed-ablation-20260423"
    )
    parser.add_argument(
        "--selection-run-dir", default="runs/tta-hybrid-gate-sweep-20260509"
    )
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--policy", default="recon_guarded")
    parser.add_argument("--tta-method", default="bn_adapt")
    parser.add_argument("--de-delta-limit", type=float, default=0.05)
    parser.add_argument("--run-name", default="tta-locked-final-20260509")
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--tent-steps", type=int, default=1)
    return parser.parse_args()


def reject_baseline(
    seed: int,
    y: np.ndarray,
    frozen_probs: np.ndarray,
    reject_rate: float,
    split: str,
) -> dict[str, Any]:
    frozen_pred = np.argmax(frozen_probs, axis=1)
    frozen_conf = np.max(frozen_probs, axis=1)
    reject_count = int(round(float(reject_rate) * len(y)))
    reject_mask = np.zeros(len(y), dtype=bool)
    if reject_count > 0:
        reject_indices = np.argsort(frozen_conf)[:reject_count]
        reject_mask[reject_indices] = True
    keep_mask = ~reject_mask
    kept_y = y[keep_mask]
    kept_pred = frozen_pred[keep_mask]
    kept_probs = frozen_probs[keep_mask]
    if len(kept_y) == 0:
        metrics = {"accuracy": np.nan, "f1": np.nan, "pr_auc": np.nan}
        per_class = {name: np.nan for name in v02.STAGE_NAMES}
    else:
        metrics = v02.compute_metrics(kept_y, kept_pred, kept_probs, v02.STAGE_NAMES)
        per_class = compute_per_class_f1(kept_y, kept_pred)

    rejected_stage_counts = {
        v02.STAGE_NAMES[index]: int((y[reject_mask] == index).sum())
        for index in range(len(v02.STAGE_NAMES))
    }
    return {
        "method": "frozen_confidence_reject_matched_override_rate",
        "seed": int(seed),
        "split": split,
        "target_reject_rate": float(reject_rate),
        "actual_reject_rate": float(reject_mask.mean()),
        "coverage": float(keep_mask.mean()),
        "reject_count": reject_count,
        "kept_accuracy": float(metrics["accuracy"]),
        "kept_macro_f1": float(metrics["f1"]),
        "kept_pr_auc": (
            float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan
        ),
        "kept_recon_f1": float(per_class[v02.STAGE_NAMES[RECON_LABEL]]),
        "kept_de_f1": float(per_class[v02.STAGE_NAMES[DE_LABEL]]),
        "rejected_stage_counts": rejected_stage_counts,
    }


def summarize(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metric_cols = [
        col
        for col in frame.columns
        if col
        in {
            "accuracy",
            "macro_f1",
            "pr_auc",
            "recon_f1",
            "de_f1",
            "override_rate",
            "macro_f1_delta_vs_frozen",
            "recon_f1_delta_vs_frozen",
            "de_f1_delta_vs_frozen",
        }
    ]
    aggregations = {f"{col}_mean": (col, "mean") for col in metric_cols}
    aggregations.update({f"{col}_std": (col, "std") for col in metric_cols})
    return frame.groupby(group_cols).agg(**aggregations).reset_index()


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    selection_run_dir = v02.resolve_path(repo_root, args.selection_run_dir)
    selection_path = selection_run_dir / "selected_hybrid_policies.csv"
    selected = pd.read_csv(selection_path)
    lock_rows = selected[
        (selected["policy"] == args.policy)
        & (selected["tta_method"] == args.tta_method)
        & (np.isclose(selected["de_delta_limit"], float(args.de_delta_limit)))
    ].copy()
    if lock_rows.empty:
        raise ValueError("No selected rows matched the requested locked policy.")
    lock_rows = lock_rows.sort_values("seed").reset_index(drop=True)

    source_summary = json.loads(
        (source_run_dir / "summary.json").read_text(encoding="utf-8")
    )
    config_path = Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    run_dir = (
        v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name
    ).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")

    print(f"Loading trusted split from {config_path}...")
    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    _train_df, val_df, test_df, feature_cols, preprocess_summary = (
        v03.prepare_features_and_splits_v03(
            df=df,
            settings=settings,
            gml=gml,
            run_dir=run_dir,
        )
    )
    split_arrays = {
        "val": v02.build_row_arrays(val_df, feature_cols),
        "test": v02.build_row_arrays(test_df, feature_cols),
    }
    device = torch.device("cpu")

    locked_rows: list[dict[str, Any]] = []
    reject_rows: list[dict[str, Any]] = []
    frozen_rows: list[dict[str, Any]] = []
    lock_manifest: list[dict[str, Any]] = []

    for row in lock_rows.to_dict("records"):
        seed = int(row["seed"])
        uncertainty_threshold = float(row["uncertainty_threshold"])
        recon_rescue_threshold = float(row["recon_rescue_threshold"])
        de_keep_threshold = float(row["de_keep_threshold"])
        lock_manifest.append(
            {
                "seed": seed,
                "policy": args.policy,
                "tta_method": args.tta_method,
                "de_delta_limit": float(args.de_delta_limit),
                "uncertainty_threshold": uncertainty_threshold,
                "recon_rescue_threshold": recon_rescue_threshold,
                "de_keep_threshold": de_keep_threshold,
                "selection_source": str(selection_path),
            }
        )

        print(f"Seed {seed}: replaying locked thresholds...")
        state_path = (
            source_run_dir
            / "seed_runs"
            / str(args.variant)
            / f"seed_{seed}"
            / "mlp_state_dict.pt"
        )
        base_model = instantiate_mlp(
            feature_count=len(feature_cols), params=mlp_params
        ).to(device)
        base_model.load_state_dict(torch.load(state_path, map_location=device))
        base_state = copy.deepcopy(base_model.state_dict())

        frozen_cache: dict[str, np.ndarray] = {}
        tta_cache: dict[str, np.ndarray] = {}
        for split, (x, y) in split_arrays.items():
            frozen = predict_probs(base_model, x, int(args.batch_size), device)
            frozen_cache[split] = frozen
            frozen_eval = metric_row(
                "frozen",
                seed,
                split,
                v02.compute_metrics(
                    y, np.argmax(frozen, axis=1), frozen, v02.STAGE_NAMES
                ),
                compute_per_class_f1(y, np.argmax(frozen, axis=1)),
                {},
            )
            frozen_rows.append(frozen_eval)

            tta_probs, _details = method_probs(
                args.tta_method,
                base_state,
                len(feature_cols),
                mlp_params,
                x,
                int(args.batch_size),
                device,
                int(args.tent_steps),
            )
            tta_cache[split] = tta_probs
            hybrid, gate = hybrid_probs(
                frozen,
                tta_probs,
                uncertainty_threshold,
                recon_rescue_threshold,
                de_keep_threshold,
            )
            pred = np.argmax(hybrid, axis=1)
            metrics = v02.compute_metrics(y, pred, hybrid, v02.STAGE_NAMES)
            per_class = compute_per_class_f1(y, pred)
            locked = metric_row(
                "locked_hybrid",
                seed,
                split,
                metrics,
                per_class,
                {
                    "override_rate": float(gate["override_rate"]),
                    "uncertainty_threshold": uncertainty_threshold,
                    "recon_rescue_threshold": recon_rescue_threshold,
                    "de_keep_threshold": de_keep_threshold,
                },
            )
            frozen_eval_by_metric = frozen_eval
            for metric in ["accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]:
                locked[f"{metric}_delta_vs_frozen"] = float(
                    locked[metric] - frozen_eval_by_metric[metric]
                )
            locked_rows.append(locked)

            if split == "test":
                reject_rows.append(
                    reject_baseline(
                        seed, y, frozen, float(gate["override_rate"]), split
                    )
                )

    locked_frame = pd.DataFrame(locked_rows)
    frozen_frame = pd.DataFrame(frozen_rows)
    reject_frame = pd.DataFrame(reject_rows)
    locked_frame.to_csv(run_dir / "locked_hybrid_metrics.csv", index=False)
    frozen_frame.to_csv(run_dir / "frozen_reference_metrics.csv", index=False)
    reject_frame.to_csv(run_dir / "confidence_reject_baseline.csv", index=False)
    write_json(run_dir / "locked_policy_manifest.json", lock_manifest)

    test_summary = summarize(locked_frame[locked_frame["split"] == "test"], ["method"])
    reject_summary = (
        reject_frame.groupby("method")
        .agg(
            coverage_mean=("coverage", "mean"),
            actual_reject_rate_mean=("actual_reject_rate", "mean"),
            kept_macro_f1_mean=("kept_macro_f1", "mean"),
            kept_recon_f1_mean=("kept_recon_f1", "mean"),
            kept_de_f1_mean=("kept_de_f1", "mean"),
        )
        .reset_index()
    )
    test_summary.to_csv(run_dir / "locked_test_summary.csv", index=False)
    reject_summary.to_csv(run_dir / "confidence_reject_summary.csv", index=False)

    decision = {
        "status": "locked_replay_complete",
        "lock_source": str(selection_path),
        "locked_policy": {
            "policy": args.policy,
            "tta_method": args.tta_method,
            "de_delta_limit": float(args.de_delta_limit),
        },
        "test_summary": test_summary.to_dict("records"),
        "reject_baseline_summary": reject_summary.to_dict("records"),
    }
    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_run_dir": str(source_run_dir),
            "selection_run_dir": str(selection_run_dir),
            "config_path": str(config_path),
            "preprocess_summary": preprocess_summary,
            "decision": decision,
        },
    )

    report_lines = [
        "# TTA Locked Final Replay",
        "",
        f"Selection source: `{selection_path}`",
        f"Policy: `{args.policy}`",
        f"TTA method: `{args.tta_method}`",
        f"DE delta limit: `{float(args.de_delta_limit):.2f}`",
        "",
        "## Locked Test Summary",
        "",
        render_markdown_table(test_summary),
        "",
        "## Confidence-Reject Baseline",
        "",
        render_markdown_table(reject_summary),
        "",
        "## Decision",
        "",
        "The locked replay uses thresholds selected before this final run. The confidence-reject baseline is not a classifier improvement baseline; it checks whether simply refusing low-confidence frozen predictions at a matched rate explains the effect.",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
