from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from praxis.praxis04.data_loader import load_preprocessed_split, split_to_matrices
from praxis.praxis04.evaluate import classification_metrics, fpr_at_recall


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan 02 strict Infilteration holdout RF pilot with stage-aware sample weighting."
    )
    parser.add_argument("--base-config", default="configs/plan02-cicids2018-infiltration-rf-seed13-smoke.json")
    parser.add_argument("--run-name", default="plan02-infiltration-stage-weighting-pilot-20260509")
    parser.add_argument("--seeds", default="13")
    parser.add_argument("--output-root", default="runs")
    return parser.parse_args()


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), indent=2), encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def render_markdown_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_float_dtype(data[column]):
            data[column] = data[column].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()]
    return "\n".join([header, divider, *rows])


def normalized(weights: np.ndarray) -> np.ndarray:
    weights = weights.astype(np.float64)
    return weights / max(float(weights.mean()), 1e-12)


def inverse_frequency_weights(labels: np.ndarray) -> np.ndarray:
    counts = np.bincount(labels.astype(int))
    counts = np.maximum(counts, 1)
    return normalized(1.0 / counts[labels.astype(int)])


def build_sample_weights(stage_train: np.ndarray, stage_names: list[str], variant: str) -> np.ndarray | None:
    if variant == "global_balanced":
        return None
    if variant == "stage_inverse":
        return inverse_frequency_weights(stage_train)
    if variant.startswith("lateral_boost_"):
        boost = float(variant.replace("lateral_boost_", ""))
        weights = np.ones(len(stage_train), dtype=np.float64)
        lateral_ids = [idx for idx, name in enumerate(stage_names) if name == "Lateral Movement"]
        if lateral_ids:
            weights[np.isin(stage_train, lateral_ids)] = boost
        return normalized(weights)
    raise ValueError(f"Unknown variant: {variant}")


def metric_row(
    variant: str,
    seed: int,
    metrics: dict[str, Any],
    label_names: list[str],
    sample_weight_summary: dict[str, Any],
) -> dict[str, Any]:
    per_f1 = metrics["per_class_f1"]
    per_support = metrics["per_class_support"]
    per_pred = metrics["per_class_predicted"]
    per_auprc = metrics["per_class_auprc"]
    return {
        "variant": variant,
        "seed": int(seed),
        "macro_f1": float(metrics["macro_f1"]),
        "benign_f1": float(per_f1.get("Benign", 0.0)),
        "infilteration_f1": float(per_f1.get("Infilteration", 0.0)),
        "infilteration_auprc": float(per_auprc.get("Infilteration", np.nan)),
        "benign_support": int(per_support.get("Benign", 0)),
        "infilteration_support": int(per_support.get("Infilteration", 0)),
        "benign_predicted": int(per_pred.get("Benign", 0)),
        "infilteration_predicted": int(per_pred.get("Infilteration", 0)),
        "fpr_at_95_recall_benign": float(metrics["fpr_at_95_recall_benign"]),
        "labels": ",".join(label_names),
        **sample_weight_summary,
    }


def main() -> None:
    args = parse_args()
    base_config = json.loads(Path(args.base_config).read_text(encoding="utf-8"))
    run_dir = Path(args.output_root) / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    seeds = parse_seeds(args.seeds)
    variants = ["global_balanced", "stage_inverse", "lateral_boost_2", "lateral_boost_4", "lateral_boost_8"]

    rows: list[dict[str, Any]] = []
    for seed in seeds:
        print(f"Loading strict Infilteration split for seed {seed}...")
        split = load_preprocessed_split(
            Path(base_config["data_dir"]),
            sample_rows_per_file=int(base_config["sample_rows_per_file"]),
            chunksize=int(base_config.get("chunksize", 100_000)),
            sample_seed=int(seed),
            sample_strategy=str(base_config.get("sample_strategy", "uniform")),
            holdout_day_pattern=str(base_config["holdout_day_pattern"]),
            min_train_rows_per_label=int(base_config.get("min_train_rows_per_label", 0)),
            min_val_rows_per_label=int(base_config.get("min_val_rows_per_label", 0)),
            support_fraction_per_label=float(base_config.get("support_fraction_per_label", 0.0)),
        )
        matrices = split_to_matrices(split)
        benign_id = matrices.label_names.index("Benign")

        for variant in variants:
            print(f"  Training {variant}...")
            sample_weight = build_sample_weights(matrices.stage_train, matrices.stage_names, variant)
            clf = RandomForestClassifier(
                n_estimators=int(base_config.get("rf_n_estimators", 80)),
                max_depth=base_config.get("rf_max_depth", 14),
                random_state=int(seed),
                n_jobs=int(base_config.get("n_jobs", 1)),
                class_weight="balanced",
            )
            clf.fit(matrices.x_train, matrices.y_train, sample_weight=sample_weight)
            raw_probs = clf.predict_proba(matrices.x_test)
            probs = np.zeros((len(matrices.x_test), len(matrices.label_names)), dtype=np.float32)
            probs[:, clf.classes_.astype(int)] = raw_probs
            pred = probs.argmax(axis=1)
            metrics = classification_metrics(
                matrices.y_test,
                pred,
                y_proba=probs,
                labels=matrices.label_names,
            )
            metrics["fpr_at_95_recall_benign"] = fpr_at_recall(
                (matrices.y_test == benign_id).astype(int),
                probs[:, benign_id],
                target_recall=0.95,
            )
            sample_weight_summary = {
                "sample_weight_min": float(sample_weight.min()) if sample_weight is not None else 1.0,
                "sample_weight_max": float(sample_weight.max()) if sample_weight is not None else 1.0,
                "sample_weight_mean": float(sample_weight.mean()) if sample_weight is not None else 1.0,
            }
            rows.append(metric_row(variant, seed, metrics, matrices.label_names, sample_weight_summary))

    raw = pd.DataFrame(rows).sort_values(["variant", "seed"]).reset_index(drop=True)
    raw.to_csv(run_dir / "raw_results.csv", index=False)
    summary = (
        raw.groupby("variant")
        .agg(
            macro_f1_mean=("macro_f1", "mean"),
            macro_f1_std=("macro_f1", "std"),
            benign_f1_mean=("benign_f1", "mean"),
            infilteration_f1_mean=("infilteration_f1", "mean"),
            infilteration_auprc_mean=("infilteration_auprc", "mean"),
            fpr_at_95_recall_benign_mean=("fpr_at_95_recall_benign", "mean"),
            infilteration_predicted_mean=("infilteration_predicted", "mean"),
        )
        .reset_index()
        .sort_values(["infilteration_f1_mean", "benign_f1_mean"], ascending=[False, False])
    )
    summary.to_csv(run_dir / "summary_mean_std.csv", index=False)

    baseline = summary[summary["variant"] == "global_balanced"].iloc[0]
    best = summary.iloc[0]
    decision = {
        "best_variant": best.to_dict(),
        "baseline": baseline.to_dict(),
        "passes_infilteration_gate": bool(
            float(best["infilteration_f1_mean"]) >= float(baseline["infilteration_f1_mean"]) + 0.03
        ),
        "passes_benign_safety": bool(float(best["benign_f1_mean"]) >= float(baseline["benign_f1_mean"]) - 0.02),
    }
    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "base_config": args.base_config,
            "seeds": seeds,
            "variants": variants,
            "decision": decision,
        },
    )
    report = [
        "# Plan 02 Infilteration Stage-Weighting Pilot",
        "",
        f"Config: `{args.base_config}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(to_jsonable(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
