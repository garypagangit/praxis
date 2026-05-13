from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run hardened tree-model bakeoffs on the Unraveled strict holdout split."
    )
    parser.add_argument("--config", required=True, help="Path to the Unraveled v03 config JSON.")
    parser.add_argument(
        "--deep-run",
        required=True,
        help="Existing deep-model run directory whose MLP/Mamba metrics should be merged into the comparison table.",
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Name of the bakeoff output folder to create under the config's output_dir.",
    )
    return parser.parse_args()


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def build_class_weighted_sample_weight(labels: np.ndarray) -> np.ndarray:
    counts = np.bincount(labels, minlength=len(v02.STAGE_NAMES)).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    return weights[labels]


def compute_per_class_frame(
    model_name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> pd.DataFrame:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    rows: list[dict[str, Any]] = []
    for idx, stage_name in enumerate(v02.STAGE_NAMES):
        rows.append(
            {
                "model": model_name,
                "stage": stage_name,
                "support": int(support[idx]),
                "precision": float(precision[idx]),
                "recall": float(recall[idx]),
                "f1": float(f1[idx]),
            }
        )
    return pd.DataFrame(rows)


def metrics_row(model_name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model_name,
        "accuracy": float(metrics["accuracy"]),
        "precision": float(metrics["precision"]),
        "recall": float(metrics["recall"]),
        "f1": float(metrics["f1"]),
        "roc_auc": float(metrics["roc_auc"]) if metrics["roc_auc"] is not None else np.nan,
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
    }


def load_deep_metrics_frame(deep_run_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(deep_run_dir / "metrics-table.csv")
    return frame


def load_deep_per_class_frame(deep_run_dir: Path) -> pd.DataFrame:
    return pd.read_csv(deep_run_dir / "per-class-metrics.csv")


def render_markdown_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_float_dtype(data[column]):
            data[column] = data[column].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()]
    return "\n".join([header, divider, *rows])


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    deep_run_dir = Path(args.deep_run).resolve()

    settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=run_dir,
    )

    x_train = train_df[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_df["MultiLabel"].to_numpy(dtype=np.int64)
    x_test = test_df[feature_cols].to_numpy(dtype=np.float32)
    y_test = test_df["MultiLabel"].to_numpy(dtype=np.int64)
    sample_weight = build_class_weighted_sample_weight(y_train)

    models: list[tuple[str, Any, dict[str, Any]]] = [
        (
            "RandomForest",
            RandomForestClassifier(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=1,
                class_weight="balanced_subsample",
                random_state=int(settings["random_seed"]),
                n_jobs=1,
            ),
            {},
        )
    ]
    if XGBClassifier is not None:
        models.append(
            (
                "XGBoost",
                XGBClassifier(
                    objective="multi:softprob",
                    num_class=len(v02.STAGE_NAMES),
                    eval_metric="mlogloss",
                    n_estimators=300,
                    learning_rate=0.05,
                    max_depth=6,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=1.0,
                    random_state=int(settings["random_seed"]),
                    tree_method="hist",
                    n_jobs=1,
                ),
                {"sample_weight": sample_weight},
            )
        )

    tree_metric_rows: list[dict[str, Any]] = []
    tree_per_class_frames: list[pd.DataFrame] = []
    for model_name, estimator, fit_kwargs in models:
        print(f"Training {model_name} on hardened split...")
        estimator.fit(x_train, y_train, **fit_kwargs)
        probs = estimator.predict_proba(x_test)
        preds = np.argmax(probs, axis=1)
        metrics = v02.compute_metrics(y_test, preds, probs, v02.STAGE_NAMES)
        tree_metric_rows.append(metrics_row(model_name, metrics))
        tree_per_class_frames.append(compute_per_class_frame(model_name, y_test, preds))
        write_json(
            run_dir / f"{model_name.lower()}_results.json",
            {
                "model": model_name,
                "metrics": metrics,
                "fit_kwargs": list(fit_kwargs.keys()),
            },
        )

    tree_metrics = pd.DataFrame(tree_metric_rows)
    tree_per_class = pd.concat(tree_per_class_frames, ignore_index=True)
    tree_metrics.to_csv(run_dir / "tree_metrics.csv", index=False)
    tree_per_class.to_csv(run_dir / "tree_per_class_metrics.csv", index=False)

    deep_metrics = load_deep_metrics_frame(deep_run_dir)
    bakeoff_metrics = pd.concat([deep_metrics, tree_metrics], ignore_index=True)
    bakeoff_metrics.to_csv(run_dir / "bakeoff_metrics.csv", index=False)

    deep_per_class = load_deep_per_class_frame(deep_run_dir)
    bakeoff_per_class = pd.concat([deep_per_class, tree_per_class], ignore_index=True)
    bakeoff_per_class.to_csv(run_dir / "bakeoff_per_class_metrics.csv", index=False)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "deep_run_dir": str(deep_run_dir),
        "cache_path": str(cache_path),
        "cache_rows": int(len(df)),
        "feature_count": int(len(feature_cols)),
        "feature_cols": feature_cols,
        "preprocess_summary": preprocess_summary,
        "tree_models": tree_metrics.to_dict(orient="records"),
        "all_models": bakeoff_metrics.to_dict(orient="records"),
    }
    write_json(run_dir / "summary.json", summary)

    report_lines = [
        "# Hardened Bakeoff Report",
        "",
        f"Config: `{config_path.name}`",
        f"Deep run merged: `{deep_run_dir.name}`",
        "",
        "## Overall Metrics",
        "",
        render_markdown_table(bakeoff_metrics[["model", "accuracy", "f1", "pr_auc"]]),
        "",
        "## Tree-Only Metrics",
        "",
        render_markdown_table(tree_metrics[["model", "accuracy", "f1", "pr_auc"]]),
        "",
    ]
    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Bakeoff metrics: {run_dir / 'bakeoff_metrics.csv'}")
    print(f"Bakeoff per-class metrics: {run_dir / 'bakeoff_per_class_metrics.csv'}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
