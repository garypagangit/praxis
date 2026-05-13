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
import torch.nn as nn
from sklearn.metrics import recall_score, roc_auc_score
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")

STAGE1_NAMES = ["Benign", "Attack"]
STAGE2_NAMES = v02.STAGE_NAMES[1:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Re-evaluate the two-stage cascade using a feature-subset Stage 1 and "
            "validation-calibrated routing thresholds."
        )
    )
    parser.add_argument("--config", required=True, help="Base support-floor config JSON.")
    parser.add_argument("--run-name", required=True, help="Output directory name under runs/.")
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated training seeds.",
    )
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    parser.add_argument(
        "--source-two-stage-run-dir",
        default="runs/two-stage-support-floor-mlp-20260424",
        help="Existing two-stage run containing saved Stage 2 checkpoints.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage reference raw results CSV.",
    )
    return parser.parse_args()


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


def set_seed(seed: int) -> None:
    v02.set_random_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def instantiate_mlp(feature_count: int, num_classes: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=num_classes,
    )


def compute_class_weights(labels: np.ndarray, num_classes: int) -> torch.Tensor:
    counts = np.bincount(labels.astype(np.int64), minlength=num_classes)
    counts = np.maximum(counts, 1)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    weights = np.clip(weights, 0.5, 8.0).astype(np.float32)
    return torch.tensor(weights, dtype=torch.float32)


def predict_probs(
    model: nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    loader = DataLoader(v02.RowDataset(x, y), batch_size=batch_size, shuffle=False)
    probs_list: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for xs, _ in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            probs_list.append(probs.cpu().numpy())
    return np.vstack(probs_list)


def evaluate_stage1(
    original_labels: np.ndarray,
    binary_true: np.ndarray,
    probs: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    pred = (probs[:, 1] >= threshold).astype(np.int64)
    metrics = v02.compute_metrics(binary_true, pred, probs, STAGE1_NAMES)
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(binary_true, pred, labels=[0, 1], zero_division=0)
    per_class = {"Benign": float(f1[0]), "Attack": float(f1[1])}

    attack_recall_by_stage: dict[str, float] = {}
    for stage_index, stage_name in enumerate(v02.STAGE_NAMES[1:], start=1):
        mask = original_labels == stage_index
        attack_recall_by_stage[stage_name] = float((pred[mask] == 1).mean()) if int(mask.sum()) else float("nan")

    return {
        "metrics": metrics,
        "per_class_f1": per_class,
        "attack_recall": float(recall_score(binary_true, pred, pos_label=1, zero_division=0)),
        "benign_f1": float(per_class["Benign"]),
        "recon_attack_recall": float(attack_recall_by_stage[v02.STAGE_NAMES[1]]),
        "attack_recall_by_true_stage": attack_recall_by_stage,
        "threshold": float(threshold),
    }


def choose_threshold(
    original_labels: np.ndarray,
    binary_true: np.ndarray,
    probs: np.ndarray,
) -> dict[str, Any]:
    baseline = evaluate_stage1(original_labels, binary_true, probs, threshold=0.5)
    benign_floor = max(float(baseline["benign_f1"]) - 0.02, 0.0)
    best: dict[str, Any] | None = None
    for threshold in np.arange(0.05, 0.951, 0.05):
        summary = evaluate_stage1(original_labels, binary_true, probs, threshold=float(threshold))
        row = {
            "threshold": float(round(threshold, 2)),
            "val_attack_recall": float(summary["attack_recall"]),
            "val_benign_f1": float(summary["benign_f1"]),
            "val_recon_attack_recall": float(summary["recon_attack_recall"]),
            "allowed": bool(float(summary["benign_f1"]) >= benign_floor),
        }
        if not row["allowed"]:
            continue
        if best is None:
            best = row
            continue
        current_key = (
            row["val_recon_attack_recall"],
            row["val_attack_recall"],
            row["val_benign_f1"],
            row["threshold"],
        )
        best_key = (
            best["val_recon_attack_recall"],
            best["val_attack_recall"],
            best["val_benign_f1"],
            best["threshold"],
        )
        if current_key > best_key:
            best = row
    if best is None:
        best = {
            "threshold": 0.5,
            "val_attack_recall": float(baseline["attack_recall"]),
            "val_benign_f1": float(baseline["benign_f1"]),
            "val_recon_attack_recall": float(baseline["recon_attack_recall"]),
            "allowed": False,
        }
    return best


def train_stage1_mlp(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    params: dict[str, Any],
    settings: dict[str, Any],
    device: torch.device,
) -> nn.Module:
    model = instantiate_mlp(feature_count=int(train_x.shape[1]), num_classes=2, params=params).to(device)
    train_loader = DataLoader(v02.RowDataset(train_x, train_y), batch_size=int(settings["tabular_batch_size"]), shuffle=True)
    criterion = nn.CrossEntropyLoss(weight=compute_class_weights(train_y, num_classes=2).to(device))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(params["lr"]),
        weight_decay=float(params["weight_decay"]),
    )

    best_state: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    for _epoch in range(1, int(settings["train_epochs"]) + 1):
        model.train()
        for xs, ys in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits, ys)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        val_probs = predict_probs(model, val_x, val_y, int(settings["tabular_batch_size"]), device)
        val_pred = np.argmax(val_probs, axis=1)
        val_metrics = v02.compute_metrics(val_y, val_pred, val_probs, STAGE1_NAMES)
        if float(val_metrics["f1"]) > best_score:
            best_score = float(val_metrics["f1"])
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None:
        raise RuntimeError("Stage 1 revision training completed without a best checkpoint.")
    model.load_state_dict(best_state)
    return model


def compute_recon_auc_scores(train_df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    subset = train_df[train_df["MultiLabel"].isin([0, 1])].copy()
    y = (subset["MultiLabel"].values == 1).astype(np.int64)
    rows: list[dict[str, Any]] = []
    for feature in feature_cols:
        x = subset[feature].values
        if np.nanstd(x) <= 1e-12:
            auc = 0.5
        else:
            try:
                auc = float(roc_auc_score(y, x))
                auc = max(auc, 1.0 - auc)
            except Exception:
                auc = 0.5
        rows.append({"feature": feature, "benign_recon_auc": float(auc)})
    return pd.DataFrame(rows).sort_values("benign_recon_auc", ascending=False).reset_index(drop=True)


def build_feature_subsets(
    feature_cols: list[str],
    overall_importance: pd.DataFrame,
    recon_auc_df: pd.DataFrame,
) -> dict[str, list[str]]:
    merged = pd.DataFrame({"feature": feature_cols}).merge(overall_importance, on="feature", how="left")
    merged = merged.merge(recon_auc_df, on="feature", how="left")
    merged["importance"] = merged["importance"].fillna(0.0)
    overall_top20 = merged.sort_values("importance", ascending=False)["feature"].head(20).tolist()
    recon_top30 = recon_auc_df["feature"].head(30).tolist()
    return {
        "overall_top20": overall_top20,
        "recon_top30": recon_top30,
    }


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


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def plot_candidate_metric(frame: pd.DataFrame, output_path: Path, metric_col: str, title: str) -> None:
    grouped = frame.groupby("candidate").agg(mean=(metric_col, "mean"), std=(metric_col, "std")).reset_index()
    grouped["std"] = grouped["std"].fillna(0.0)
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.bar(grouped["candidate"], grouped["mean"], yerr=grouped["std"], capsize=4, color="#4ecdc4")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, axis="y", alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    config_path = v02.resolve_path(repo_root, args.config)
    source_two_stage_run_dir = v02.resolve_path(repo_root, args.source_two_stage_run_dir)
    output_dir = (repo_root / "runs" / args.run_name).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    device = torch.device("cpu")
    seeds = parse_seeds(args.seeds)
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

    train_binary_y = (train_df["MultiLabel"].values != 0).astype(np.int64)
    val_binary_y = (val_df["MultiLabel"].values != 0).astype(np.int64)
    test_binary_y = (test_df["MultiLabel"].values != 0).astype(np.int64)
    val_original_y = val_df["MultiLabel"].values.astype(np.int64)
    test_original_y = test_df["MultiLabel"].values.astype(np.int64)
    full_test_x = test_df[feature_cols].values.astype(np.float32)

    reference_frame = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    reference_frame = reference_frame[reference_frame["variant"] == "adasyn_weighted_ce"].sort_values("seed")

    raw_rows: list[dict[str, Any]] = []
    for candidate_name, subset_features in candidates.items():
        print(f"\nRunning cascade revision candidate: {candidate_name}")
        train_x_stage1 = train_df[subset_features].values.astype(np.float32)
        val_x_stage1 = val_df[subset_features].values.astype(np.float32)
        test_x_stage1 = test_df[subset_features].values.astype(np.float32)

        for seed in seeds:
            print(f"  Seed {seed}")
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
            test_stage1_probs = predict_probs(stage1_model, test_x_stage1, test_binary_y, int(settings["tabular_batch_size"]), device)
            threshold_row = choose_threshold(val_original_y, val_binary_y, val_stage1_probs)
            stage1_test_summary = evaluate_stage1(test_original_y, test_binary_y, test_stage1_probs, float(threshold_row["threshold"]))

            seed_stage2_dir = source_two_stage_run_dir / "seed_runs" / f"seed_{seed}"
            stage2_state_path = seed_stage2_dir / "stage2_state_dict.pt"
            if not stage2_state_path.exists():
                raise FileNotFoundError(f"Missing Stage 2 checkpoint: {stage2_state_path}")

            stage2_model = instantiate_mlp(feature_count=len(feature_cols), num_classes=4, params=mlp_params).to(device)
            stage2_model.load_state_dict(torch.load(stage2_state_path, map_location=device))
            stage2_probs = predict_probs(stage2_model, full_test_x, np.zeros(len(full_test_x), dtype=np.int64), int(settings["tabular_batch_size"]), device)

            end_pred, end_probs = build_end_to_end_outputs(
                stage1_probs=test_stage1_probs,
                stage2_probs=stage2_probs,
                threshold=float(threshold_row["threshold"]),
            )
            end_metrics = v02.compute_metrics(test_original_y, end_pred, end_probs, v02.STAGE_NAMES)
            end_per_class = compute_per_class_f1(test_original_y, end_pred)

            raw_rows.append(
                {
                    "candidate": candidate_name,
                    "feature_count": len(subset_features),
                    "seed": int(seed),
                    "threshold": float(threshold_row["threshold"]),
                    "stage1_attack_recall": float(stage1_test_summary["attack_recall"]),
                    "stage1_benign_f1": float(stage1_test_summary["benign_f1"]),
                    "stage1_recon_attack_recall": float(stage1_test_summary["recon_attack_recall"]),
                    "accuracy": float(end_metrics["accuracy"]),
                    "macro_f1": float(end_metrics["f1"]),
                    "pr_auc": float(end_metrics["pr_auc"]) if end_metrics["pr_auc"] is not None else np.nan,
                    "benign_f1": float(end_per_class["Benign"]),
                    "recon_f1": float(end_per_class["Reconnaissance"]),
                    "foothold_f1": float(end_per_class["Establish Foothold"]),
                    "lm_f1": float(end_per_class["Lateral Movement"]),
                    "de_f1": float(end_per_class["Data Exfiltration"]),
                }
            )

    raw_frame = pd.DataFrame(raw_rows).sort_values(["candidate", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(output_dir / "raw_results.csv", index=False)

    summary_rows: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []
    for candidate, frame in raw_frame.groupby("candidate"):
        summary_rows.append(
            {
                "candidate": candidate,
                "feature_count": int(frame["feature_count"].iloc[0]),
                "threshold_mean": float(frame["threshold"].mean()),
                "stage1_recon_attack_recall_mean": float(frame["stage1_recon_attack_recall"].mean()),
                "accuracy_mean": float(frame["accuracy"].mean()),
                "macro_f1_mean": float(frame["macro_f1"].mean()),
                "pr_auc_mean": float(frame["pr_auc"].mean()),
                "recon_f1_mean": float(frame["recon_f1"].mean()),
                "de_f1_mean": float(frame["de_f1"].mean()),
            }
        )
        merged = frame.merge(reference_frame[["seed", "accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]], on="seed", suffixes=("_cascade", "_single"))
        delta_rows.append(
            {
                "candidate": candidate,
                "accuracy_delta_mean": float((merged["accuracy_cascade"] - merged["accuracy_single"]).mean()),
                "macro_f1_delta_mean": float((merged["macro_f1_cascade"] - merged["macro_f1_single"]).mean()),
                "pr_auc_delta_mean": float((merged["pr_auc_cascade"] - merged["pr_auc_single"]).mean()),
                "recon_f1_delta_mean": float((merged["recon_f1_cascade"] - merged["recon_f1_single"]).mean()),
                "de_f1_delta_mean": float((merged["de_f1_cascade"] - merged["de_f1_single"]).mean()),
            }
        )
    summary_frame = pd.DataFrame(summary_rows).sort_values(["macro_f1_mean", "recon_f1_mean"], ascending=[False, False]).reset_index(drop=True)
    delta_frame = pd.DataFrame(delta_rows).sort_values("macro_f1_delta_mean", ascending=False).reset_index(drop=True)
    summary_frame.to_csv(output_dir / "summary.csv", index=False)
    delta_frame.to_csv(output_dir / "delta_vs_single_stage.csv", index=False)

    plot_candidate_metric(raw_frame, output_dir / "candidate_macro_f1.png", "macro_f1", "Cascade Revision Macro F1")
    plot_candidate_metric(raw_frame, output_dir / "candidate_recon_f1.png", "recon_f1", "Cascade Revision Recon F1")
    plot_candidate_metric(raw_frame, output_dir / "candidate_de_f1.png", "de_f1", "Cascade Revision DE F1")

    best_candidate = summary_frame.iloc[0].to_dict() if not summary_frame.empty else None
    decision = {
        "best_candidate": best_candidate,
        "beats_single_stage_macro": bool(best_candidate is not None and float(best_candidate["macro_f1_mean"]) > float(reference_frame["macro_f1"].mean())),
        "holds_single_stage_de": bool(best_candidate is not None and float(best_candidate["de_f1_mean"]) >= float(reference_frame["de_f1"].mean()) - 0.05),
    }
    decision["recommended_to_continue"] = bool(decision["beats_single_stage_macro"] and decision["holds_single_stage_de"])

    write_json(
        output_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "source_two_stage_run_dir": str(source_two_stage_run_dir),
            "seeds": seeds,
            "preprocess_summary": preprocess_summary,
            "summary_rows": summary_frame.to_dict(orient="records"),
            "delta_rows": delta_frame.to_dict(orient="records"),
            "decision": decision,
        },
    )

    report_lines = [
        "# Two-Stage Feature-Subset Revision Report",
        "",
        f"Config: `{config_path.name}`",
        f"Source Stage 2 run: `{source_two_stage_run_dir}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
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

    print(f"Raw results: {output_dir / 'raw_results.csv'}")
    print(f"Summary: {output_dir / 'summary.csv'}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
