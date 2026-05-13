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

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")

STAGE1_NAMES = ["Benign", "Attack"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep Stage 1 attack thresholds for a saved two-stage MLP run and "
            "select validation-calibrated thresholds without retraining."
        )
    )
    parser.add_argument(
        "--two-stage-run-dir",
        required=True,
        help="Existing two-stage run directory containing seed_runs and summary.json.",
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output directory name under runs/ for the threshold sweep report.",
    )
    parser.add_argument(
        "--threshold-start",
        type=float,
        default=0.05,
        help="Sweep start value.",
    )
    parser.add_argument(
        "--threshold-stop",
        type=float,
        default=0.95,
        help="Sweep stop value, inclusive.",
    )
    parser.add_argument(
        "--threshold-step",
        type=float,
        default=0.05,
        help="Sweep step size.",
    )
    parser.add_argument(
        "--benign-delta-limit",
        type=float,
        default=0.02,
        help="Maximum allowed validation Benign F1 drop from the 0.50 threshold baseline.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage raw seed results for comparison.",
    )
    parser.add_argument(
        "--reference-variant",
        default="adasyn_weighted_ce",
        help="Single-stage variant to compare against.",
    )
    return parser.parse_args()


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


def instantiate_mlp(num_features: int, num_classes: int, mlp_params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=num_features,
        hidden_dim=int(mlp_params["hidden_dim"]),
        num_layers=int(mlp_params["num_layers"]),
        dropout=float(mlp_params["dropout"]),
        num_classes=num_classes,
    )


def predict_probs(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = torch.utils.data.DataLoader(
        v02.RowDataset(x, y),
        batch_size=batch_size,
        shuffle=False,
    )
    model.eval()
    probs_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs, _ in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            probs_list.append(probs.cpu().numpy())
    return np.vstack(probs_list)


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray, class_names: list[str]) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(class_names))),
        zero_division=0,
    )
    return {class_names[index]: float(f1[index]) for index in range(len(class_names))}


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


def choose_best_threshold(
    frame: pd.DataFrame,
    policy: str,
) -> pd.Series:
    allowed = frame[frame["allowed"]].copy()
    if allowed.empty:
        allowed = frame.copy()

    if policy == "macro_guarded":
        ordered = allowed.sort_values(
            by=["val_macro_f1", "val_recon_f1", "val_de_f1", "threshold"],
            ascending=[False, False, False, False],
        )
        return ordered.iloc[0]

    if policy == "recon_guarded":
        ordered = allowed.sort_values(
            by=["val_recon_f1", "val_macro_f1", "val_de_f1", "threshold"],
            ascending=[False, False, False, False],
        )
        return ordered.iloc[0]

    raise ValueError(f"Unknown policy: {policy}")


def summarize_policy(
    frame: pd.DataFrame,
    policy: str,
    single_stage_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_rows: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []

    for seed, seed_frame in frame.groupby("seed"):
        chosen = choose_best_threshold(seed_frame.reset_index(drop=True), policy=policy)
        selected_rows.append(
            {
                "policy": policy,
                "seed": int(seed),
                "threshold": float(chosen["threshold"]),
                "val_macro_f1": float(chosen["val_macro_f1"]),
                "val_recon_f1": float(chosen["val_recon_f1"]),
                "val_de_f1": float(chosen["val_de_f1"]),
                "val_benign_f1": float(chosen["val_benign_f1"]),
                "test_accuracy": float(chosen["test_accuracy"]),
                "test_macro_f1": float(chosen["test_macro_f1"]),
                "test_pr_auc": float(chosen["test_pr_auc"]),
                "test_benign_f1": float(chosen["test_benign_f1"]),
                "test_recon_f1": float(chosen["test_recon_f1"]),
                "test_de_f1": float(chosen["test_de_f1"]),
                "test_foothold_f1": float(chosen["test_foothold_f1"]),
                "test_lm_f1": float(chosen["test_lm_f1"]),
                "allowed": bool(chosen["allowed"]),
            }
        )

        baseline = single_stage_frame[single_stage_frame["seed"] == int(seed)].iloc[0]
        delta_rows.append(
            {
                "policy": policy,
                "seed": int(seed),
                "threshold": float(chosen["threshold"]),
                "accuracy_delta_vs_single_stage": float(chosen["test_accuracy"] - baseline["accuracy"]),
                "macro_f1_delta_vs_single_stage": float(chosen["test_macro_f1"] - baseline["macro_f1"]),
                "pr_auc_delta_vs_single_stage": float(chosen["test_pr_auc"] - baseline["pr_auc"]),
                "recon_f1_delta_vs_single_stage": float(chosen["test_recon_f1"] - baseline["recon_f1"]),
                "de_f1_delta_vs_single_stage": float(chosen["test_de_f1"] - baseline["de_f1"]),
            }
        )

    return pd.DataFrame(selected_rows), pd.DataFrame(delta_rows)


def plot_threshold_curves(frame: pd.DataFrame, output_path: Path, metric_prefix: str) -> None:
    thresholds = sorted(frame["threshold"].unique())
    grouped = frame.groupby("threshold").agg(
        metric_mean=(f"{metric_prefix}", "mean"),
        metric_std=(f"{metric_prefix}", "std"),
    )
    std_values = grouped["metric_std"].fillna(0.0).to_numpy()

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.plot(thresholds, grouped["metric_mean"].to_numpy(), marker="o", linewidth=2, color="#5dade2")
    ax.fill_between(
        thresholds,
        grouped["metric_mean"].to_numpy() - std_values,
        grouped["metric_mean"].to_numpy() + std_values,
        color="#5dade2",
        alpha=0.2,
    )
    ax.set_xlabel("Stage 1 Attack Threshold")
    ax.set_ylabel(metric_prefix.replace("_", " ").title())
    ax.set_title(f"{metric_prefix.replace('_', ' ').title()} vs Stage 1 Threshold")
    ax.grid(True, alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    two_stage_run_dir = v02.resolve_path(repo_root, args.two_stage_run_dir)
    if not two_stage_run_dir.exists():
        raise FileNotFoundError(f"Two-stage run dir not found: {two_stage_run_dir}")

    summary_path = two_stage_run_dir / "summary.json"
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    config_path = Path(summary_payload["config_path"])
    base_settings = dict(v03.DEFAULTS)
    base_settings.update(json.loads(config_path.read_text(encoding="utf-8")))

    output_dir = v02.resolve_path(repo_root, base_settings["output_dir"]) / args.run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    thresholds = np.arange(
        float(args.threshold_start),
        float(args.threshold_stop) + float(args.threshold_step) * 0.5,
        float(args.threshold_step),
    )
    thresholds = np.round(thresholds, 4)

    device = torch.device("cpu")
    seeds = [int(seed) for seed in summary_payload["seeds"]]
    mlp_params = dict(summary_payload["mlp_params"])

    v02.set_random_seed(int(base_settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=output_dir,
    )
    _train_x, _train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y_full = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y_full = v02.build_row_arrays(test_df, feature_cols)

    sweep_rows: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"Sweeping thresholds for seed {seed}...")
        seed_dir = two_stage_run_dir / "seed_runs" / f"seed_{seed}"
        stage1_state_path = seed_dir / "stage1_state_dict.pt"
        stage2_state_path = seed_dir / "stage2_state_dict.pt"
        if not stage1_state_path.exists() or not stage2_state_path.exists():
            raise FileNotFoundError(f"Missing saved state dicts for seed {seed} in {seed_dir}")

        stage1_model = instantiate_mlp(
            num_features=len(feature_cols),
            num_classes=2,
            mlp_params=mlp_params,
        ).to(device)
        stage2_model = instantiate_mlp(
            num_features=len(feature_cols),
            num_classes=4,
            mlp_params=mlp_params,
        ).to(device)
        stage1_model.load_state_dict(torch.load(stage1_state_path, map_location=device))
        stage2_model.load_state_dict(torch.load(stage2_state_path, map_location=device))

        val_stage1_probs = predict_probs(
            model=stage1_model,
            x=val_x,
            y=np.zeros(len(val_x), dtype=np.int64),
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        test_stage1_probs = predict_probs(
            model=stage1_model,
            x=test_x,
            y=np.zeros(len(test_x), dtype=np.int64),
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        val_stage2_probs = predict_probs(
            model=stage2_model,
            x=val_x,
            y=np.zeros(len(val_x), dtype=np.int64),
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        test_stage2_probs = predict_probs(
            model=stage2_model,
            x=test_x,
            y=np.zeros(len(test_x), dtype=np.int64),
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )

        base_val_pred, base_val_probs = build_end_to_end_outputs(
            stage1_probs=val_stage1_probs,
            stage2_probs=val_stage2_probs,
            threshold=0.5,
        )
        base_val_per_class = compute_per_class_f1(val_y_full, base_val_pred, v02.STAGE_NAMES)
        benign_floor = max(float(base_val_per_class[v02.STAGE_NAMES[0]]) - float(args.benign_delta_limit), 0.0)

        for threshold in thresholds:
            val_pred, val_probs = build_end_to_end_outputs(
                stage1_probs=val_stage1_probs,
                stage2_probs=val_stage2_probs,
                threshold=float(threshold),
            )
            test_pred, test_probs = build_end_to_end_outputs(
                stage1_probs=test_stage1_probs,
                stage2_probs=test_stage2_probs,
                threshold=float(threshold),
            )

            val_metrics = v02.compute_metrics(val_y_full, val_pred, val_probs, v02.STAGE_NAMES)
            test_metrics = v02.compute_metrics(test_y_full, test_pred, test_probs, v02.STAGE_NAMES)
            val_per_class = compute_per_class_f1(val_y_full, val_pred, v02.STAGE_NAMES)
            test_per_class = compute_per_class_f1(test_y_full, test_pred, v02.STAGE_NAMES)

            sweep_rows.append(
                {
                    "seed": int(seed),
                    "threshold": float(threshold),
                    "val_macro_f1": float(val_metrics["f1"]),
                    "val_pr_auc": float(val_metrics["pr_auc"]) if val_metrics["pr_auc"] is not None else np.nan,
                    "val_benign_f1": float(val_per_class[v02.STAGE_NAMES[0]]),
                    "val_recon_f1": float(val_per_class[v02.STAGE_NAMES[1]]),
                    "val_foothold_f1": float(val_per_class[v02.STAGE_NAMES[2]]),
                    "val_lm_f1": float(val_per_class[v02.STAGE_NAMES[3]]),
                    "val_de_f1": float(val_per_class[v02.STAGE_NAMES[4]]),
                    "test_accuracy": float(test_metrics["accuracy"]),
                    "test_macro_f1": float(test_metrics["f1"]),
                    "test_pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                    "test_benign_f1": float(test_per_class[v02.STAGE_NAMES[0]]),
                    "test_recon_f1": float(test_per_class[v02.STAGE_NAMES[1]]),
                    "test_foothold_f1": float(test_per_class[v02.STAGE_NAMES[2]]),
                    "test_lm_f1": float(test_per_class[v02.STAGE_NAMES[3]]),
                    "test_de_f1": float(test_per_class[v02.STAGE_NAMES[4]]),
                    "allowed": bool(float(val_per_class[v02.STAGE_NAMES[0]]) >= benign_floor),
                    "benign_floor": float(benign_floor),
                }
            )

    sweep_frame = pd.DataFrame(sweep_rows).sort_values(["seed", "threshold"]).reset_index(drop=True)
    sweep_frame.to_csv(output_dir / "threshold_sweep_raw.csv", index=False)

    reference_path = v02.resolve_path(repo_root, args.reference_csv)
    single_stage_frame = pd.read_csv(reference_path)
    single_stage_frame = single_stage_frame[
        single_stage_frame["variant"] == str(args.reference_variant)
    ].sort_values("seed")

    macro_selected, macro_delta = summarize_policy(
        frame=sweep_frame,
        policy="macro_guarded",
        single_stage_frame=single_stage_frame,
    )
    recon_selected, recon_delta = summarize_policy(
        frame=sweep_frame,
        policy="recon_guarded",
        single_stage_frame=single_stage_frame,
    )

    selected_frame = pd.concat([macro_selected, recon_selected], ignore_index=True)
    delta_frame = pd.concat([macro_delta, recon_delta], ignore_index=True)
    selected_frame.to_csv(output_dir / "selected_thresholds.csv", index=False)
    delta_frame.to_csv(output_dir / "selected_threshold_deltas_vs_single_stage.csv", index=False)

    policy_summary_rows: list[dict[str, Any]] = []
    for policy, policy_frame in selected_frame.groupby("policy"):
        policy_summary_rows.append(
            {
                "policy": policy,
                "threshold_mean": float(policy_frame["threshold"].mean()),
                "threshold_std": float(policy_frame["threshold"].std(ddof=1)),
                "test_accuracy_mean": float(policy_frame["test_accuracy"].mean()),
                "test_accuracy_std": float(policy_frame["test_accuracy"].std(ddof=1)),
                "test_macro_f1_mean": float(policy_frame["test_macro_f1"].mean()),
                "test_macro_f1_std": float(policy_frame["test_macro_f1"].std(ddof=1)),
                "test_pr_auc_mean": float(policy_frame["test_pr_auc"].mean()),
                "test_pr_auc_std": float(policy_frame["test_pr_auc"].std(ddof=1)),
                "test_benign_f1_mean": float(policy_frame["test_benign_f1"].mean()),
                "test_recon_f1_mean": float(policy_frame["test_recon_f1"].mean()),
                "test_de_f1_mean": float(policy_frame["test_de_f1"].mean()),
            }
        )
    policy_summary_frame = pd.DataFrame(policy_summary_rows)
    policy_summary_frame.to_csv(output_dir / "policy_summary.csv", index=False)

    plot_threshold_curves(sweep_frame, output_dir / "val_macro_f1_vs_threshold.png", "val_macro_f1")
    plot_threshold_curves(sweep_frame, output_dir / "val_recon_f1_vs_threshold.png", "val_recon_f1")
    plot_threshold_curves(sweep_frame, output_dir / "test_macro_f1_vs_threshold.png", "test_macro_f1")
    plot_threshold_curves(sweep_frame, output_dir / "test_recon_f1_vs_threshold.png", "test_recon_f1")
    plot_threshold_curves(sweep_frame, output_dir / "test_de_f1_vs_threshold.png", "test_de_f1")

    summary_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_two_stage_run_dir": str(two_stage_run_dir),
        "config_path": str(config_path),
        "reference_csv": str(reference_path),
        "reference_variant": str(args.reference_variant),
        "threshold_range": {
            "start": float(args.threshold_start),
            "stop": float(args.threshold_stop),
            "step": float(args.threshold_step),
        },
        "benign_delta_limit": float(args.benign_delta_limit),
        "seeds": seeds,
        "preprocess_summary": preprocess_summary,
        "policy_summary": policy_summary_frame.to_dict(orient="records"),
    }
    write_json(output_dir / "summary.json", summary_payload)

    report_lines = [
        "# Two-Stage Threshold Sweep Report",
        "",
        f"Source two-stage run: `{two_stage_run_dir}`",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        f"Thresholds: `{float(args.threshold_start):.2f}` to `{float(args.threshold_stop):.2f}` in steps of `{float(args.threshold_step):.2f}`",
        f"Benign F1 guardrail: within `{float(args.benign_delta_limit):.2f}` of the validation baseline at threshold `0.50`",
        "",
        "## Policy Summary",
        "",
        render_markdown_table(policy_summary_frame),
        "",
        "## Selected Thresholds",
        "",
        render_markdown_table(selected_frame),
        "",
        "## Delta Vs Single-Stage Reference",
        "",
        render_markdown_table(delta_frame),
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Threshold sweep raw: {output_dir / 'threshold_sweep_raw.csv'}")
    print(f"Selected thresholds: {output_dir / 'selected_thresholds.csv'}")
    print(f"Summary: {output_dir / 'policy_summary.csv'}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
