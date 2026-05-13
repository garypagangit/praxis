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

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_two_stage_feature_subset_revision import (
    STAGE1_NAMES,
    STAGE2_NAMES,
    build_end_to_end_outputs,
    build_feature_subsets,
    choose_threshold,
    compute_per_class_f1 as compute_full_per_class_f1,
    compute_recon_auc_scores,
    evaluate_stage1,
    instantiate_mlp,
    predict_probs,
    set_seed,
    train_stage1_mlp,
)


plt.style.use("dark_background")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply post-hoc Stage 2 logit adjustment inside the two-stage cascade to "
            "recover DE without retraining."
        )
    )
    parser.add_argument("--config", required=True, help="Base support-floor config JSON.")
    parser.add_argument("--run-name", required=True, help="Output directory under runs/.")
    parser.add_argument("--source-two-stage-run-dir", required=True, help="Stage 2 checkpoint pack root.")
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage reference raw results CSV.",
    )
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    parser.add_argument("--candidate", default="recon_top30", help="Stage 1 feature-subset candidate.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated training seeds.")
    parser.add_argument(
        "--tau-recon-values",
        default="-0.5,-0.25,0.0,0.25,0.5",
        help="Comma-separated Stage 2 tau values for Reconnaissance.",
    )
    parser.add_argument(
        "--tau-mid-values",
        default="-0.25,0.0,0.25,0.5",
        help="Comma-separated Stage 2 tau values shared by Foothold and LM.",
    )
    parser.add_argument(
        "--tau-de-values",
        default="0.0,0.25,0.5,0.75,1.0,1.25",
        help="Comma-separated Stage 2 tau values for Data Exfiltration.",
    )
    parser.add_argument(
        "--recon-delta-limit",
        type=float,
        default=0.10,
        help="Maximum allowed validation Recon F1 drop versus the unadjusted cascade.",
    )
    parser.add_argument(
        "--macro-delta-limit",
        type=float,
        default=0.02,
        help="Maximum allowed validation Macro F1 drop versus the unadjusted cascade.",
    )
    return parser.parse_args()


def parse_float_list(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("Expected at least one float value.")
    return values


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


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


def predict_logits(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = torch.utils.data.DataLoader(v02.RowDataset(x, y), batch_size=batch_size, shuffle=False)
    logits_list: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for xs, _ in loader:
            xs = xs.to(device)
            logits = model(xs)
            logits_list.append(logits.cpu().numpy())
    return np.vstack(logits_list)


def compute_attack_only_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(STAGE2_NAMES))),
        zero_division=0,
    )
    return {STAGE2_NAMES[index]: float(f1[index]) for index in range(len(STAGE2_NAMES))}


def logits_to_probs(logits: np.ndarray) -> np.ndarray:
    logits = logits.astype(np.float64)
    logits = logits - logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(logits)
    return exp_logits / np.clip(exp_logits.sum(axis=1, keepdims=True), 1e-12, None)


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def plot_heatmap(frame: pd.DataFrame, output_path: Path, value_col: str, title: str) -> None:
    pivot = frame.pivot_table(index="tau_recon", columns="tau_de", values=value_col, aggfunc="mean")
    pivot = pivot.sort_index().sort_index(axis=1)
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    image = ax.imshow(pivot.to_numpy(), aspect="auto", origin="lower", cmap="magma")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{value:.2f}" for value in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{value:.2f}" for value in pivot.index])
    ax.set_xlabel("tau_de")
    ax.set_ylabel("tau_recon")
    ax.set_title(title)
    fig.colorbar(image, ax=ax, shrink=0.85)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    config_path = v02.resolve_path(repo_root, args.config)
    source_run_dir = v02.resolve_path(repo_root, args.source_two_stage_run_dir)
    output_dir = (repo_root / "runs" / args.run_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings(config_path)
    device = torch.device("cpu")
    seeds = parse_seeds(args.seeds)
    tau_recon_values = parse_float_list(args.tau_recon_values)
    tau_mid_values = parse_float_list(args.tau_mid_values)
    tau_de_values = parse_float_list(args.tau_de_values)
    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must include fixed MLP parameters.")

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=output_dir,
    )

    overall_importance = pd.read_csv(v02.resolve_path(repo_root, args.s6_feature_importance_csv))
    overall_importance = overall_importance[
        (overall_importance["dataset"] == "Unraveled") & (overall_importance["model"] == "MLP")
    ][["feature", "importance"]]
    recon_auc_df = compute_recon_auc_scores(train_df, feature_cols)
    candidates = build_feature_subsets(feature_cols, overall_importance, recon_auc_df)
    if str(args.candidate) not in candidates:
        raise ValueError(f"Unknown candidate: {args.candidate}")
    subset_features = candidates[str(args.candidate)]

    train_binary_y = (train_df["MultiLabel"].values != 0).astype(np.int64)
    val_binary_y = (val_df["MultiLabel"].values != 0).astype(np.int64)
    test_binary_y = (test_df["MultiLabel"].values != 0).astype(np.int64)
    val_original_y = val_df["MultiLabel"].values.astype(np.int64)
    test_original_y = test_df["MultiLabel"].values.astype(np.int64)

    train_x_stage1 = train_df[subset_features].values.astype(np.float32)
    val_x_stage1 = val_df[subset_features].values.astype(np.float32)
    test_x_stage1 = test_df[subset_features].values.astype(np.float32)
    full_val_x = val_df[feature_cols].values.astype(np.float32)
    full_test_x = test_df[feature_cols].values.astype(np.float32)

    attack_train_mask = train_df["MultiLabel"].values != 0
    train_y_stage2 = train_df.loc[attack_train_mask, "MultiLabel"].values.astype(np.int64) - 1
    attack_counts = np.bincount(train_y_stage2, minlength=len(STAGE2_NAMES)).astype(np.float64)
    attack_priors = attack_counts / np.clip(attack_counts.sum(), 1.0, None)
    bias_basis = -np.log(np.clip(attack_priors, 1e-12, None))

    reference_frame = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    reference_frame = reference_frame[reference_frame["variant"] == "adasyn_weighted_ce"].sort_values("seed")

    raw_grid_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []

    for seed in seeds:
        print(f"Running Stage 2 logit adjustment for seed {seed}...")
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

        seed_stage2_dir = source_run_dir / "seed_runs" / f"seed_{seed}"
        stage2_state_path = seed_stage2_dir / "stage2_state_dict.pt"
        if not stage2_state_path.exists():
            raise FileNotFoundError(f"Missing Stage 2 checkpoint: {stage2_state_path}")

        stage2_model = instantiate_mlp(feature_count=len(feature_cols), num_classes=4, params=mlp_params).to(device)
        stage2_model.load_state_dict(torch.load(stage2_state_path, map_location=device))

        val_stage2_logits = predict_logits(
            model=stage2_model,
            x=full_val_x,
            y=np.zeros(len(full_val_x), dtype=np.int64),
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )
        test_stage2_logits = predict_logits(
            model=stage2_model,
            x=full_test_x,
            y=np.zeros(len(full_test_x), dtype=np.int64),
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )

        base_val_pred, base_val_probs = build_end_to_end_outputs(
            stage1_probs=val_stage1_probs,
            stage2_probs=logits_to_probs(val_stage2_logits),
            threshold=float(threshold_row["threshold"]),
        )
        base_val_metrics = v02.compute_metrics(val_original_y, base_val_pred, base_val_probs, v02.STAGE_NAMES)
        base_val_per_class = compute_full_per_class_f1(val_original_y, base_val_pred)
        recon_floor = max(float(base_val_per_class["Reconnaissance"]) - float(args.recon_delta_limit), 0.0)
        macro_floor = max(float(base_val_metrics["f1"]) - float(args.macro_delta_limit), 0.0)

        best_row: dict[str, Any] | None = None
        for tau_mid in tau_mid_values:
            for tau_recon in tau_recon_values:
                for tau_de in tau_de_values:
                    tau_vector = np.array([tau_recon, tau_mid, tau_mid, tau_de], dtype=np.float64)
                    adjusted_val_logits = val_stage2_logits + bias_basis * tau_vector
                    adjusted_test_logits = test_stage2_logits + bias_basis * tau_vector

                    val_stage2_probs = logits_to_probs(adjusted_val_logits)
                    test_stage2_probs = logits_to_probs(adjusted_test_logits)

                    val_pred, val_probs = build_end_to_end_outputs(
                        stage1_probs=val_stage1_probs,
                        stage2_probs=val_stage2_probs,
                        threshold=float(threshold_row["threshold"]),
                    )
                    test_pred, test_probs = build_end_to_end_outputs(
                        stage1_probs=test_stage1_probs,
                        stage2_probs=test_stage2_probs,
                        threshold=float(threshold_row["threshold"]),
                    )
                    val_metrics = v02.compute_metrics(val_original_y, val_pred, val_probs, v02.STAGE_NAMES)
                    test_metrics = v02.compute_metrics(test_original_y, test_pred, test_probs, v02.STAGE_NAMES)
                    val_per_class = compute_full_per_class_f1(val_original_y, val_pred)
                    test_per_class = compute_full_per_class_f1(test_original_y, test_pred)

                    row = {
                        "seed": seed,
                        "threshold": float(threshold_row["threshold"]),
                        "tau_mid": float(tau_mid),
                        "tau_recon": float(tau_recon),
                        "tau_de": float(tau_de),
                        "val_macro_f1": float(val_metrics["f1"]),
                        "val_recon_f1": float(val_per_class["Reconnaissance"]),
                        "val_de_f1": float(val_per_class["Data Exfiltration"]),
                        "test_accuracy": float(test_metrics["accuracy"]),
                        "test_macro_f1": float(test_metrics["f1"]),
                        "test_pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                        "test_recon_f1": float(test_per_class["Reconnaissance"]),
                        "test_de_f1": float(test_per_class["Data Exfiltration"]),
                        "test_benign_f1": float(test_per_class["Benign"]),
                        "allowed": bool(
                            float(val_per_class["Reconnaissance"]) >= recon_floor
                            and float(val_metrics["f1"]) >= macro_floor
                        ),
                    }
                    raw_grid_rows.append(row)
                    if not row["allowed"]:
                        continue

                    if best_row is None:
                        best_row = row
                        continue

                    current_key = (
                        row["val_de_f1"],
                        row["val_macro_f1"],
                        row["val_recon_f1"],
                        row["test_de_f1"],
                        -abs(row["tau_recon"]),
                        -row["tau_de"],
                    )
                    best_key = (
                        best_row["val_de_f1"],
                        best_row["val_macro_f1"],
                        best_row["val_recon_f1"],
                        best_row["test_de_f1"],
                        -abs(best_row["tau_recon"]),
                        -best_row["tau_de"],
                    )
                    if current_key > best_key:
                        best_row = row

        if best_row is None:
            raise RuntimeError(f"No allowed Stage 2 logit-adjustment setting found for seed {seed}.")

        selected_rows.append(best_row)
        baseline = reference_frame[reference_frame["seed"] == seed].iloc[0]
        delta_rows.append(
            {
                "seed": seed,
                "tau_mid": float(best_row["tau_mid"]),
                "tau_recon": float(best_row["tau_recon"]),
                "tau_de": float(best_row["tau_de"]),
                "accuracy_delta": float(best_row["test_accuracy"] - baseline["accuracy"]),
                "macro_f1_delta": float(best_row["test_macro_f1"] - baseline["macro_f1"]),
                "pr_auc_delta": float(best_row["test_pr_auc"] - baseline["pr_auc"]),
                "recon_f1_delta": float(best_row["test_recon_f1"] - baseline["recon_f1"]),
                "de_f1_delta": float(best_row["test_de_f1"] - baseline["de_f1"]),
            }
        )

    raw_grid_frame = pd.DataFrame(raw_grid_rows).sort_values(["seed", "tau_mid", "tau_recon", "tau_de"])
    selected_frame = pd.DataFrame(selected_rows).sort_values("seed").reset_index(drop=True)
    delta_frame = pd.DataFrame(delta_rows).sort_values("seed").reset_index(drop=True)
    raw_grid_frame.to_csv(output_dir / "tau_grid_raw.csv", index=False)
    selected_frame.to_csv(output_dir / "selected_tau_per_seed.csv", index=False)
    delta_frame.to_csv(output_dir / "delta_vs_single_stage.csv", index=False)

    summary_frame = pd.DataFrame(
        [
            {
                "pipeline": "single_stage_reference",
                "accuracy_mean": float(reference_frame["accuracy"].mean()),
                "accuracy_std": float(reference_frame["accuracy"].std(ddof=1)),
                "macro_f1_mean": float(reference_frame["macro_f1"].mean()),
                "macro_f1_std": float(reference_frame["macro_f1"].std(ddof=1)),
                "pr_auc_mean": float(reference_frame["pr_auc"].mean()),
                "pr_auc_std": float(reference_frame["pr_auc"].std(ddof=1)),
                "recon_f1_mean": float(reference_frame["recon_f1"].mean()),
                "recon_f1_std": float(reference_frame["recon_f1"].std(ddof=1)),
                "de_f1_mean": float(reference_frame["de_f1"].mean()),
                "de_f1_std": float(reference_frame["de_f1"].std(ddof=1)),
            },
            {
                "pipeline": "two_stage_stage2_logit_adjusted",
                "accuracy_mean": float(selected_frame["test_accuracy"].mean()),
                "accuracy_std": float(selected_frame["test_accuracy"].std(ddof=1)),
                "macro_f1_mean": float(selected_frame["test_macro_f1"].mean()),
                "macro_f1_std": float(selected_frame["test_macro_f1"].std(ddof=1)),
                "pr_auc_mean": float(selected_frame["test_pr_auc"].mean()),
                "pr_auc_std": float(selected_frame["test_pr_auc"].std(ddof=1)),
                "recon_f1_mean": float(selected_frame["test_recon_f1"].mean()),
                "recon_f1_std": float(selected_frame["test_recon_f1"].std(ddof=1)),
                "de_f1_mean": float(selected_frame["test_de_f1"].mean()),
                "de_f1_std": float(selected_frame["test_de_f1"].std(ddof=1)),
            },
        ]
    )
    summary_frame.to_csv(output_dir / "summary.csv", index=False)

    for seed, seed_frame in raw_grid_frame.groupby("seed"):
        allowed_seed = seed_frame[seed_frame["allowed"]].copy()
        if allowed_seed.empty:
            allowed_seed = seed_frame.copy()
        seed_tau_mid = float(selected_frame[selected_frame["seed"] == seed]["tau_mid"].iloc[0])
        plot_heatmap(
            frame=allowed_seed[allowed_seed["tau_mid"] == seed_tau_mid],
            output_path=output_dir / f"seed_{seed}_val_de_heatmap.png",
            value_col="val_de_f1",
            title=f"Seed {seed} Val DE F1",
        )

    decision = {
        "improves_de_mean": bool(float(delta_frame["de_f1_delta"].mean()) > 0.05),
        "holds_recon_mean": bool(float(delta_frame["recon_f1_delta"].mean()) >= 0.40),
        "holds_macro_mean": bool(float(delta_frame["macro_f1_delta"].mean()) >= 0.0),
    }
    decision["recommended_to_continue"] = bool(
        decision["improves_de_mean"] and decision["holds_recon_mean"] and decision["holds_macro_mean"]
    )

    summary_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "source_two_stage_run_dir": str(source_run_dir),
        "candidate": str(args.candidate),
        "tau_grid": {
            "tau_recon_values": tau_recon_values,
            "tau_mid_values": tau_mid_values,
            "tau_de_values": tau_de_values,
        },
        "guardrails": {
            "recon_delta_limit": float(args.recon_delta_limit),
            "macro_delta_limit": float(args.macro_delta_limit),
        },
        "stage2_attack_priors": {STAGE2_NAMES[index]: float(attack_priors[index]) for index in range(len(STAGE2_NAMES))},
        "preprocess_summary": preprocess_summary,
        "summary_rows": summary_frame.to_dict(orient="records"),
        "selected_tau_per_seed": selected_frame.to_dict(orient="records"),
        "delta_vs_single_stage": delta_frame.to_dict(orient="records"),
        "decision": decision,
    }
    write_json(output_dir / "summary.json", summary_payload)

    report_lines = [
        "# Two-Stage Stage 2 Logit Adjustment Report",
        "",
        f"Config: `{config_path.name}`",
        f"Source Stage 2 run: `{source_run_dir}`",
        f"Candidate: `{args.candidate}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Selected Tau Per Seed",
        "",
        render_markdown_table(selected_frame),
        "",
        "## Delta Vs Single-Stage",
        "",
        render_markdown_table(delta_frame),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Tau grid: {output_dir / 'tau_grid_raw.csv'}")
    print(f"Selected tau: {output_dir / 'selected_tau_per_seed.csv'}")
    print(f"Summary: {output_dir / 'summary.csv'}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
