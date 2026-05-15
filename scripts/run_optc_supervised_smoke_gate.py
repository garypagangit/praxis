from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from praxis.detectors import detector_table, make_detector


NON_FEATURE_COLUMNS = {
    "window_id",
    "start_ns",
    "end_ns",
    "primary_label",
    "labels",
    "label_overlap_ns",
    "malicious_node_events",
    "malicious_node_count",
    "node_labels",
    "target",
    "label",
    "attack_stages",
    "attack_hosts",
}


def select_features(frame: pd.DataFrame) -> list[str]:
    features: list[str] = []
    for column in frame.columns:
        if column in NON_FEATURE_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            features.append(column)
    return features


def split_frame(frame: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, holdout = train_test_split(
        frame,
        test_size=0.4,
        random_state=seed,
        stratify=frame["target"],
    )
    val, test = train_test_split(
        holdout,
        test_size=0.5,
        random_state=seed,
        stratify=holdout["target"],
    )
    return train.sort_values("window_id"), val.sort_values("window_id"), test.sort_values("window_id")


def split_counts(split: pd.DataFrame) -> dict[str, int]:
    return {
        "attack": int((split["target"] == 1).sum()),
        "background": int((split["target"] == 0).sum()),
        "total": int(len(split)),
    }


def evaluate_detector(detector: Any, x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    pred = detector.predict(x)
    if hasattr(detector, "predict_proba"):
        score = detector.predict_proba(x)[:, 1]
    else:
        score = pred.astype(float)
    precision, recall, _, _ = precision_recall_fscore_support(
        y,
        pred,
        labels=[0, 1],
        zero_division=0,
    )
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "roc_auc": float(roc_auc_score(y, score)),
        "average_precision": float(average_precision_score(y, score)),
        "background_precision": float(precision[0]),
        "background_recall": float(recall[0]),
        "attack_precision": float(precision[1]),
        "attack_recall": float(recall[1]),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# OpTC Supervised Provenance Smoke Gate",
        "",
        "Generated: 2026-05-14",
        "",
        f"Status: **{summary['decision']}**",
        "",
        "## Scope",
        "",
        "This is a targeted host/day feasibility smoke test, not a broad provenance detector claim.",
        "",
        "- Host/day: `sysclient0501`, OpTC day 2 / `24Sep19`",
        "- Target: `attack` vs `background` windows",
        "- Excluded: `gray_buffer` windows",
        "- Split: stratified random train/validation/test because chronological labels are attack-first then background",
        "- Time columns excluded: `start_ns`, `end_ns`",
        "- Label-derived columns excluded: `primary_label`, `labels`, `label_overlap_ns`, `malicious_node_events`, `malicious_node_count`, `node_labels`",
        "",
        "## Label Support",
        "",
        "| Label | Windows |",
        "|---|---:|",
    ]
    for label, count in summary["label_counts"].items():
        lines.append(f"| `{label}` | `{count}` |")
    lines.extend(
        [
            "",
            "## Split Support",
            "",
            "| Split | Attack | Background | Total |",
            "|---|---:|---:|---:|",
        ]
    )
    for split_name, counts in summary["split_counts"].items():
        lines.append(
            f"| `{split_name}` | `{counts['attack']}` | `{counts['background']}` | `{counts['total']}` |"
        )
    lines.extend(
        [
            "",
            "## Detector Results",
            "",
            "| Detector | Split | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["results"]:
        lines.append(
            f"| `{row['detector']}` | `{row['split']}` | {row['accuracy']:.4f} | "
            f"{row['macro_f1']:.4f} | {row['roc_auc']:.4f} | {row['average_precision']:.4f} | "
            f"{row['attack_recall']:.4f} | {row['background_recall']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "## Artifacts",
            "",
            "| Artifact | Path |",
            "|---|---|",
            f"| Summary JSON | `{summary['summary_path']}` |",
            f"| Split assignments | `{summary['split_path']}` |",
            f"| Metrics CSV | `{summary['metrics_path']}` |",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("runs/optc-window-gate-20260514-pass/window_features.csv"))
    parser.add_argument("--labels", type=Path, default=Path("runs/optc-label-acquisition-20260514/optc_window_labels.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("runs/optc-supervised-smoke-20260514"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/OPTC_SUPERVISED_SMOKE_GATE_20260514.md"),
    )
    parser.add_argument("--seed", type=int, default=20260514)
    args = parser.parse_args()

    features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels)
    frame = features.merge(labels[["window_id", "label", "attack_stages", "attack_hosts"]], on="window_id", how="inner")
    label_counts = {str(k): int(v) for k, v in frame["label"].value_counts().sort_index().items()}
    usable = frame[frame["label"].isin(["attack", "background"])].copy()
    usable["target"] = (usable["label"] == "attack").astype(int)
    split_ready = usable["target"].nunique() == 2 and usable["target"].value_counts().min() >= 5
    if not split_ready:
        raise SystemExit(f"Insufficient support for smoke split: {dict(Counter(usable['label']))}")

    feature_columns = select_features(usable)
    train, val, test = split_frame(usable, args.seed)
    x_train = train[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    y_train = train["target"].to_numpy()
    splits = {
        "validation": (
            val[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(),
            val["target"].to_numpy(),
        ),
        "test": (
            test[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(),
            test["target"].to_numpy(),
        ),
    }

    results: list[dict[str, Any]] = []
    for spec in detector_table():
        detector = make_detector(spec["name"], random_state=args.seed)
        detector.fit(x_train, y_train)
        for split_name, (x_split, y_split) in splits.items():
            row = evaluate_detector(detector, x_split, y_split)
            row["detector"] = spec["name"]
            row["split"] = split_name
            results.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    split_assignments = pd.concat(
        [
            train.assign(split="train"),
            val.assign(split="validation"),
            test.assign(split="test"),
        ],
        ignore_index=True,
    )[["window_id", "split", "label", "target"]]
    split_path = args.out_dir / "split_assignments.csv"
    metrics_path = args.out_dir / "metrics.csv"
    summary_path = args.out_dir / "summary.json"
    split_assignments.to_csv(split_path, index=False)
    pd.DataFrame(results).to_csv(metrics_path, index=False)

    summary = {
        "decision": "FEASIBILITY PASS - TARGETED SMOKE ONLY",
        "features": str(args.features),
        "labels": str(args.labels),
        "feature_count": int(len(feature_columns)),
        "label_counts": label_counts,
        "usable_windows": int(len(usable)),
        "excluded_gray_buffer_windows": int((frame["label"] == "gray_buffer").sum()),
        "split_counts": {
            "train": split_counts(train),
            "validation": split_counts(val),
            "test": split_counts(test),
        },
        "results": results,
        "interpretation": (
            "The stratified smoke confirms the new OpTC interval labels are usable by the detector registry. "
            "Because all attack windows precede gray/background windows chronologically in this targeted slice, "
            "this is not evidence of temporal generalization. The next defensible step is to add another host/day "
            "or benign shard before making a provenance detector claim."
        ),
        "summary_path": str(summary_path),
        "split_path": str(split_path),
        "metrics_path": str(metrics_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), **summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
