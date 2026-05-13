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
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")


def parse_float_list(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("Expected at least one float value.")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply post-hoc stage-aware logit adjustment to the saved 3-seed MLP winner "
            "under the trusted support-floor split."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Base support-floor config JSON.",
    )
    parser.add_argument(
        "--source-run-dir",
        default="runs/mlp-support-floor-3seed-ablation-20260423",
        help="Existing MLP ablation run containing saved seed checkpoints.",
    )
    parser.add_argument(
        "--variant",
        default="adasyn_weighted_ce",
        help="Seed subdirectory variant inside the source run.",
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output directory name under runs/.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Raw seed metrics for the unadjusted reference variant.",
    )
    parser.add_argument(
        "--tau-recon-values",
        default="0.0,0.25,0.5,0.75,1.0,1.25,1.5,2.0,2.5,3.0",
        help="Comma-separated tau values for Reconnaissance.",
    )
    parser.add_argument(
        "--tau-mid-values",
        default="0.0,0.25,0.5,0.75,1.0",
        help="Comma-separated tau values shared by Foothold and LM.",
    )
    parser.add_argument(
        "--tau-de-values",
        default="0.0,0.25,0.5,0.75,1.0,1.25,1.5",
        help="Comma-separated tau values for Data Exfiltration.",
    )
    parser.add_argument(
        "--benign-delta-limit",
        type=float,
        default=0.02,
        help="Maximum allowed validation Benign F1 drop versus the unadjusted model.",
    )
    parser.add_argument(
        "--de-delta-limit",
        type=float,
        default=0.05,
        help="Maximum allowed validation DE F1 drop versus the unadjusted model.",
    )
    parser.add_argument(
        "--macro-delta-limit",
        type=float,
        default=0.02,
        help="Maximum allowed validation Macro F1 drop versus the unadjusted model.",
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


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def instantiate_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    )


def predict_logits(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = DataLoader(v02.RowDataset(x, y), batch_size=batch_size, shuffle=False)
    logits_list: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for xs, _ in loader:
            xs = xs.to(device)
            logits = model(xs)
            logits_list.append(logits.cpu().numpy())
    return np.vstack(logits_list)


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def evaluate_logits(
    y_true: np.ndarray,
    logits: np.ndarray,
) -> tuple[dict[str, Any], dict[str, float], np.ndarray]:
    logits = logits.astype(np.float64)
    logits = logits - logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(logits)
    probs = exp_logits / np.clip(exp_logits.sum(axis=1, keepdims=True), 1e-12, None)
    y_pred = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y_true, y_pred, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y_true, y_pred)
    return metrics, per_class, probs


def plot_metric_heatmap(frame: pd.DataFrame, output_path: Path, value_col: str, title: str) -> None:
    pivot = frame.pivot_table(
        index="tau_recon",
        columns="tau_de",
        values=value_col,
        aggfunc="mean",
    ).sort_index().sort_index(axis=1)
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
    image = ax.imshow(pivot.to_numpy(), aspect="auto", origin="lower", cmap="viridis")
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
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    output_dir = (repo_root / "runs" / args.run_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings(config_path)
    device = torch.device("cpu")

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=output_dir,
    )
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    train_counts = np.bincount(train_y, minlength=len(v02.STAGE_NAMES)).astype(np.float64)
    train_priors = train_counts / np.clip(train_counts.sum(), 1.0, None)
    bias_basis = -np.log(np.clip(train_priors, 1e-12, None))

    tau_recon_values = parse_float_list(args.tau_recon_values)
    tau_mid_values = parse_float_list(args.tau_mid_values)
    tau_de_values = parse_float_list(args.tau_de_values)

    raw_grid_rows: list[dict[str, Any]] = []
    chosen_rows: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []

    reference_frame = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    reference_frame = reference_frame[reference_frame["variant"] == str(args.variant)].sort_values("seed")

    variant_dir = source_run_dir / "seed_runs" / str(args.variant)
    if not variant_dir.exists():
        raise FileNotFoundError(f"Variant directory not found: {variant_dir}")

    seed_dirs = sorted([path for path in variant_dir.iterdir() if path.is_dir() and path.name.startswith("seed_")])
    for seed_dir in seed_dirs:
        seed = int(seed_dir.name.split("_")[-1])
        result_payload = json.loads((seed_dir / "results.json").read_text(encoding="utf-8"))
        params = dict(result_payload["best_params"])

        model = instantiate_mlp(feature_count=len(feature_cols), params=params).to(device)
        model.load_state_dict(torch.load(seed_dir / "mlp_state_dict.pt", map_location=device))

        val_logits = predict_logits(
            model=model,
            x=val_x,
            y=val_y,
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )
        test_logits = predict_logits(
            model=model,
            x=test_x,
            y=test_y,
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )

        base_val_metrics, base_val_per_class, _ = evaluate_logits(val_y, val_logits)
        benign_floor = max(float(base_val_per_class["Benign"]) - float(args.benign_delta_limit), 0.0)
        de_floor = max(float(base_val_per_class["Data Exfiltration"]) - float(args.de_delta_limit), 0.0)
        macro_floor = max(float(base_val_metrics["f1"]) - float(args.macro_delta_limit), 0.0)

        best_row: dict[str, Any] | None = None
        for tau_mid in tau_mid_values:
            for tau_recon in tau_recon_values:
                for tau_de in tau_de_values:
                    tau_vector = np.array([0.0, tau_recon, tau_mid, tau_mid, tau_de], dtype=np.float64)
                    adjusted_val_logits = val_logits + bias_basis * tau_vector
                    adjusted_test_logits = test_logits + bias_basis * tau_vector

                    val_metrics, val_per_class, _ = evaluate_logits(val_y, adjusted_val_logits)
                    test_metrics, test_per_class, _ = evaluate_logits(test_y, adjusted_test_logits)

                    row = {
                        "seed": seed,
                        "tau_mid": float(tau_mid),
                        "tau_recon": float(tau_recon),
                        "tau_de": float(tau_de),
                        "val_macro_f1": float(val_metrics["f1"]),
                        "val_pr_auc": float(val_metrics["pr_auc"]) if val_metrics["pr_auc"] is not None else np.nan,
                        "val_benign_f1": float(val_per_class["Benign"]),
                        "val_recon_f1": float(val_per_class["Reconnaissance"]),
                        "val_de_f1": float(val_per_class["Data Exfiltration"]),
                        "test_accuracy": float(test_metrics["accuracy"]),
                        "test_macro_f1": float(test_metrics["f1"]),
                        "test_pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
                        "test_benign_f1": float(test_per_class["Benign"]),
                        "test_recon_f1": float(test_per_class["Reconnaissance"]),
                        "test_foothold_f1": float(test_per_class["Establish Foothold"]),
                        "test_lm_f1": float(test_per_class["Lateral Movement"]),
                        "test_de_f1": float(test_per_class["Data Exfiltration"]),
                        "allowed": bool(
                            float(val_per_class["Benign"]) >= benign_floor
                            and float(val_per_class["Data Exfiltration"]) >= de_floor
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
                        row["val_recon_f1"],
                        row["val_macro_f1"],
                        row["val_de_f1"],
                        row["test_macro_f1"],
                        -row["tau_recon"],
                        -row["tau_de"],
                    )
                    best_key = (
                        best_row["val_recon_f1"],
                        best_row["val_macro_f1"],
                        best_row["val_de_f1"],
                        best_row["test_macro_f1"],
                        -best_row["tau_recon"],
                        -best_row["tau_de"],
                    )
                    if current_key > best_key:
                        best_row = row

        if best_row is None:
            raise RuntimeError(f"No allowed logit-adjustment setting found for seed {seed}.")

        chosen_rows.append(best_row)
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
    chosen_frame = pd.DataFrame(chosen_rows).sort_values("seed").reset_index(drop=True)
    delta_frame = pd.DataFrame(delta_rows).sort_values("seed").reset_index(drop=True)
    raw_grid_frame.to_csv(output_dir / "tau_grid_raw.csv", index=False)
    chosen_frame.to_csv(output_dir / "selected_tau_per_seed.csv", index=False)
    delta_frame.to_csv(output_dir / "delta_vs_reference.csv", index=False)

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
                "pipeline": "stage_aware_logit_adjusted",
                "accuracy_mean": float(chosen_frame["test_accuracy"].mean()),
                "accuracy_std": float(chosen_frame["test_accuracy"].std(ddof=1)),
                "macro_f1_mean": float(chosen_frame["test_macro_f1"].mean()),
                "macro_f1_std": float(chosen_frame["test_macro_f1"].std(ddof=1)),
                "pr_auc_mean": float(chosen_frame["test_pr_auc"].mean()),
                "pr_auc_std": float(chosen_frame["test_pr_auc"].std(ddof=1)),
                "recon_f1_mean": float(chosen_frame["test_recon_f1"].mean()),
                "recon_f1_std": float(chosen_frame["test_recon_f1"].std(ddof=1)),
                "de_f1_mean": float(chosen_frame["test_de_f1"].mean()),
                "de_f1_std": float(chosen_frame["test_de_f1"].std(ddof=1)),
            },
        ]
    )
    summary_frame.to_csv(output_dir / "summary.csv", index=False)

    for seed, seed_frame in raw_grid_frame.groupby("seed"):
        allowed_seed = seed_frame[seed_frame["allowed"]].copy()
        if allowed_seed.empty:
            allowed_seed = seed_frame.copy()
        plot_metric_heatmap(
            frame=allowed_seed[allowed_seed["tau_mid"] == float(chosen_frame[chosen_frame["seed"] == seed]["tau_mid"].iloc[0])],
            output_path=output_dir / f"seed_{seed}_val_recon_heatmap.png",
            value_col="val_recon_f1",
            title=f"Seed {seed} Val Recon F1",
        )

    decision = {
        "improves_recon_mean": bool(float(delta_frame["recon_f1_delta"].mean()) > 0.05),
        "holds_de_mean": bool(float(delta_frame["de_f1_delta"].mean()) >= -0.05),
        "holds_macro_mean": bool(float(delta_frame["macro_f1_delta"].mean()) >= -0.02),
    }
    decision["recommended_to_continue"] = bool(
        decision["improves_recon_mean"] and decision["holds_de_mean"] and decision["holds_macro_mean"]
    )

    summary_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "source_run_dir": str(source_run_dir),
        "variant": str(args.variant),
        "tau_grid": {
            "tau_recon_values": tau_recon_values,
            "tau_mid_values": tau_mid_values,
            "tau_de_values": tau_de_values,
        },
        "guardrails": {
            "benign_delta_limit": float(args.benign_delta_limit),
            "de_delta_limit": float(args.de_delta_limit),
            "macro_delta_limit": float(args.macro_delta_limit),
        },
        "train_priors": {v02.STAGE_NAMES[index]: float(train_priors[index]) for index in range(len(v02.STAGE_NAMES))},
        "preprocess_summary": preprocess_summary,
        "summary_rows": summary_frame.to_dict(orient="records"),
        "selected_tau_per_seed": chosen_frame.to_dict(orient="records"),
        "delta_vs_reference": delta_frame.to_dict(orient="records"),
        "decision": decision,
    }
    write_json(output_dir / "summary.json", summary_payload)

    report_lines = [
        "# Stage-Aware Logit Adjustment Report",
        "",
        f"Config: `{config_path.name}`",
        f"Source run: `{source_run_dir}`",
        f"Variant: `{args.variant}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Selected Tau Per Seed",
        "",
        render_markdown_table(chosen_frame),
        "",
        "## Delta Vs Reference",
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
