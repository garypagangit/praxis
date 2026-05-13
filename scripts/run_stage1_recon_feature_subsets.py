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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train Stage 1 binary MLPs on Recon-focused feature subsets and measure "
            "whether Recon-specific attack recall clears the viability threshold."
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


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def set_seed(seed: int) -> None:
    v02.set_random_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def instantiate_stage1_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=2,
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

    _, _, f1, _ = precision_recall_fscore_support(
        binary_true,
        pred,
        labels=[0, 1],
        zero_division=0,
    )
    per_class = {
        "Benign": float(f1[0]),
        "Attack": float(f1[1]),
    }
    attack_recall_by_stage: dict[str, float] = {}
    for stage_index, stage_name in enumerate(v02.STAGE_NAMES[1:], start=1):
        mask = original_labels == stage_index
        if int(mask.sum()) == 0:
            attack_recall_by_stage[stage_name] = float("nan")
        else:
            attack_recall_by_stage[stage_name] = float((pred[mask] == 1).mean())

    return {
        "metrics": metrics,
        "per_class_f1": per_class,
        "attack_recall": float(recall_score(binary_true, pred, pos_label=1, zero_division=0)),
        "benign_f1": float(per_class["Benign"]),
        "attack_recall_by_true_stage": attack_recall_by_stage,
        "recon_attack_recall": float(attack_recall_by_stage[v02.STAGE_NAMES[1]]),
        "threshold": float(threshold),
    }


def choose_threshold(
    val_original_labels: np.ndarray,
    val_binary_true: np.ndarray,
    val_probs: np.ndarray,
) -> dict[str, Any]:
    baseline = evaluate_stage1(val_original_labels, val_binary_true, val_probs, threshold=0.5)
    benign_floor = max(float(baseline["benign_f1"]) - 0.02, 0.0)

    best: dict[str, Any] | None = None
    for threshold in np.arange(0.05, 0.951, 0.05):
        summary = evaluate_stage1(val_original_labels, val_binary_true, val_probs, threshold=float(threshold))
        allowed = bool(float(summary["benign_f1"]) >= benign_floor)
        row = {
            "threshold": float(round(threshold, 2)),
            "val_attack_recall": float(summary["attack_recall"]),
            "val_benign_f1": float(summary["benign_f1"]),
            "val_recon_attack_recall": float(summary["recon_attack_recall"]),
            "allowed": allowed,
        }
        if not allowed:
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
    mlp_params: dict[str, Any],
    settings: dict[str, Any],
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = instantiate_stage1_mlp(feature_count=int(train_x.shape[1]), params=mlp_params).to(device)
    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=True,
    )
    criterion = nn.CrossEntropyLoss(weight=compute_class_weights(train_y, num_classes=2).to(device))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(mlp_params["lr"]),
        weight_decay=float(mlp_params["weight_decay"]),
    )

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(settings["train_epochs"]) + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0
        for xs, ys in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits, ys)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += float(loss.item()) * int(ys.numel())
            total_examples += int(ys.numel())

        val_probs = predict_probs(
            model=model,
            x=val_x,
            y=val_y,
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )
        val_pred = np.argmax(val_probs, axis=1)
        val_metrics = v02.compute_metrics(val_y, val_pred, val_probs, STAGE1_NAMES)
        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": float(val_metrics["f1"]),
                "val_accuracy": float(val_metrics["accuracy"]),
            }
        )

        if float(val_metrics["f1"]) > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Stage 1 training completed without a best checkpoint.")
    model.load_state_dict(best_state)
    return model, best_metrics, history


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
) -> tuple[dict[str, list[str]], pd.DataFrame]:
    merged = pd.DataFrame({"feature": feature_cols}).merge(overall_importance, on="feature", how="left")
    merged = merged.merge(recon_auc_df, on="feature", how="left")
    merged["importance"] = merged["importance"].fillna(0.0)
    merged["benign_recon_auc"] = merged["benign_recon_auc"].fillna(0.5)
    merged = merged.sort_values(["importance", "benign_recon_auc"], ascending=[False, False]).reset_index(drop=True)

    overall_top20 = merged.sort_values("importance", ascending=False)["feature"].head(20).tolist()
    recon_top20 = recon_auc_df["feature"].head(20).tolist()
    recon_top30 = recon_auc_df["feature"].head(30).tolist()
    recon_top40 = recon_auc_df["feature"].head(40).tolist()
    weak_high_importance = merged[
        (merged["importance"] > 0.01) & (merged["benign_recon_auc"] < 0.60)
    ]["feature"].tolist()
    all_minus_weak = [feature for feature in feature_cols if feature not in set(weak_high_importance)]

    subsets = {
        "all_features": list(feature_cols),
        "overall_top20": overall_top20,
        "recon_top20": recon_top20,
        "recon_top30": recon_top30,
        "recon_top40": recon_top40,
        "all_minus_weak_high_importance": all_minus_weak,
    }
    return subsets, merged


def plot_subset_metric(frame: pd.DataFrame, output_path: Path, metric_col: str, title: str) -> None:
    grouped = frame.groupby("subset").agg(mean=(metric_col, "mean"), std=(metric_col, "std")).reset_index()
    grouped["std"] = grouped["std"].fillna(0.0)
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.bar(grouped["subset"], grouped["mean"], yerr=grouped["std"], capsize=4, color="#5dade2")
    ax.set_title(title)
    ax.set_ylabel(metric_col)
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, axis="y", alpha=0.2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    config_path = v02.resolve_path(repo_root, args.config)
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
    overall_importance = overall_importance[(overall_importance["dataset"] == "Unraveled") & (overall_importance["model"] == "MLP")][["feature", "importance"]]
    recon_auc_df = compute_recon_auc_scores(train_df, feature_cols)
    feature_subsets, feature_score_table = build_feature_subsets(
        feature_cols=feature_cols,
        overall_importance=overall_importance,
        recon_auc_df=recon_auc_df,
    )
    feature_score_table.to_csv(output_dir / "feature_scores.csv", index=False)

    train_binary_y = (train_df["MultiLabel"].values != 0).astype(np.int64)
    val_binary_y = (val_df["MultiLabel"].values != 0).astype(np.int64)
    test_binary_y = (test_df["MultiLabel"].values != 0).astype(np.int64)
    val_original_y = val_df["MultiLabel"].values.astype(np.int64)
    test_original_y = test_df["MultiLabel"].values.astype(np.int64)

    raw_rows: list[dict[str, Any]] = []

    for subset_name, subset_features in feature_subsets.items():
        print(f"\nRunning Stage 1 feature subset: {subset_name} ({len(subset_features)} features)")
        train_x = train_df[subset_features].values.astype(np.float32)
        val_x = val_df[subset_features].values.astype(np.float32)
        test_x = test_df[subset_features].values.astype(np.float32)

        for seed in seeds:
            print(f"  Seed {seed}")
            set_seed(seed)
            model, val_metrics, history = train_stage1_mlp(
                train_x=train_x,
                train_y=train_binary_y,
                val_x=val_x,
                val_y=val_binary_y,
                mlp_params=mlp_params,
                settings=settings,
                device=device,
            )
            val_probs = predict_probs(
                model=model,
                x=val_x,
                y=val_binary_y,
                batch_size=int(settings["tabular_batch_size"]),
                device=device,
            )
            test_probs = predict_probs(
                model=model,
                x=test_x,
                y=test_binary_y,
                batch_size=int(settings["tabular_batch_size"]),
                device=device,
            )

            threshold_row = choose_threshold(
                val_original_labels=val_original_y,
                val_binary_true=val_binary_y,
                val_probs=val_probs,
            )
            baseline_summary = evaluate_stage1(
                original_labels=test_original_y,
                binary_true=test_binary_y,
                probs=test_probs,
                threshold=0.5,
            )
            calibrated_summary = evaluate_stage1(
                original_labels=test_original_y,
                binary_true=test_binary_y,
                probs=test_probs,
                threshold=float(threshold_row["threshold"]),
            )

            for mode, summary in [("threshold_0_5", baseline_summary), ("threshold_calibrated", calibrated_summary)]:
                raw_rows.append(
                    {
                        "subset": subset_name,
                        "feature_count": len(subset_features),
                        "seed": int(seed),
                        "mode": mode,
                        "threshold": float(summary["threshold"]),
                        "attack_recall": float(summary["attack_recall"]),
                        "benign_f1": float(summary["benign_f1"]),
                        "recon_attack_recall": float(summary["recon_attack_recall"]),
                        "foothold_attack_recall": float(summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[2]]),
                        "lm_attack_recall": float(summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[3]]),
                        "de_attack_recall": float(summary["attack_recall_by_true_stage"][v02.STAGE_NAMES[4]]),
                        "val_binary_f1": float(val_metrics["f1"]),
                    }
                )

    raw_frame = pd.DataFrame(raw_rows).sort_values(["subset", "mode", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(output_dir / "raw_stage1_subset_results.csv", index=False)

    summary_rows: list[dict[str, Any]] = []
    for (subset, mode), frame in raw_frame.groupby(["subset", "mode"]):
        summary_rows.append(
            {
                "subset": subset,
                "mode": mode,
                "feature_count": int(frame["feature_count"].iloc[0]),
                "attack_recall_mean": float(frame["attack_recall"].mean()),
                "attack_recall_std": float(frame["attack_recall"].std(ddof=1)),
                "benign_f1_mean": float(frame["benign_f1"].mean()),
                "recon_attack_recall_mean": float(frame["recon_attack_recall"].mean()),
                "recon_attack_recall_std": float(frame["recon_attack_recall"].std(ddof=1)),
                "de_attack_recall_mean": float(frame["de_attack_recall"].mean()),
                "viable_recon_gate": bool(float(frame["recon_attack_recall"].mean()) >= 0.70),
            }
        )
    summary_frame = pd.DataFrame(summary_rows).sort_values(
        ["mode", "recon_attack_recall_mean", "benign_f1_mean"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    summary_frame.to_csv(output_dir / "summary.csv", index=False)

    plot_subset_metric(
        frame=raw_frame[raw_frame["mode"] == "threshold_0_5"],
        output_path=output_dir / "recon_recall_threshold_0_5.png",
        metric_col="recon_attack_recall",
        title="Stage 1 Recon Recall at Threshold 0.50",
    )
    plot_subset_metric(
        frame=raw_frame[raw_frame["mode"] == "threshold_calibrated"],
        output_path=output_dir / "recon_recall_threshold_calibrated.png",
        metric_col="recon_attack_recall",
        title="Stage 1 Recon Recall After Calibration",
    )

    viable_frame = summary_frame[summary_frame["viable_recon_gate"]].copy()
    decision = {
        "any_viable_at_threshold_0_5": bool(
            not summary_frame[(summary_frame["mode"] == "threshold_0_5") & (summary_frame["viable_recon_gate"])].empty
        ),
        "any_viable_after_calibration": bool(
            not summary_frame[(summary_frame["mode"] == "threshold_calibrated") & (summary_frame["viable_recon_gate"])].empty
        ),
        "best_threshold_0_5_subset": None,
        "best_calibrated_subset": None,
    }
    threshold_05_frame = summary_frame[summary_frame["mode"] == "threshold_0_5"]
    calibrated_frame = summary_frame[summary_frame["mode"] == "threshold_calibrated"]
    if not threshold_05_frame.empty:
        best_05 = threshold_05_frame.sort_values(
            ["recon_attack_recall_mean", "benign_f1_mean"],
            ascending=[False, False],
        ).iloc[0]
        decision["best_threshold_0_5_subset"] = best_05.to_dict()
    if not calibrated_frame.empty:
        best_cal = calibrated_frame.sort_values(
            ["recon_attack_recall_mean", "benign_f1_mean"],
            ascending=[False, False],
        ).iloc[0]
        decision["best_calibrated_subset"] = best_cal.to_dict()

    write_json(
        output_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "seeds": seeds,
            "preprocess_summary": preprocess_summary,
            "feature_subsets": {key: value for key, value in feature_subsets.items()},
            "decision": decision,
            "summary_rows": summary_frame.to_dict(orient="records"),
        },
    )

    report_lines = [
        "# Stage 1 Recon Feature-Subset Report",
        "",
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
    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Feature scores: {output_dir / 'feature_scores.csv'}")
    print(f"Raw results: {output_dir / 'raw_stage1_subset_results.csv'}")
    print(f"Summary: {output_dir / 'summary.csv'}")
    print(f"Report: {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
