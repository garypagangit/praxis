from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
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
    "node_labels",
}


def select_features(frame: pd.DataFrame) -> list[str]:
    features = []
    for column in frame.columns:
        if column in NON_FEATURE_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            features.append(column)
    return features


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Provenance Detector Zoo Gate",
        "",
        "Generated: 2026-05-11",
        "",
        "## Decision",
        "",
        f"Gate result: `{summary['decision']}`",
        "",
        summary["rationale"],
        "",
        "## Label Support",
        "",
        "| Label | Windows |",
        "|---|---:|",
    ]
    for label, count in summary["class_counts"].items():
        lines.append(f"| {label} | {count} |")
    lines.extend(
        [
            "",
            "## Feature Table",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Windows | {summary['window_count']} |",
            f"| Numeric features | {summary['feature_count']} |",
            "",
        ]
    )
    if summary["results"]:
        lines.extend(
            [
                "## Detector Results",
                "",
                "| Detector | Accuracy | Macro-F1 | ROC-AUC | AP |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in summary["results"]:
            lines.append(
                f"| `{row['detector']}` | {row['accuracy']:.4f} | "
                f"{row['macro_f1']:.4f} | {row['roc_auc']:.4f} | {row['average_precision']:.4f} |"
            )
    lines.extend(
        [
            "",
            "## Honest Interpretation",
            "",
            summary["interpretation"],
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--features",
        type=Path,
        default=Path(
            "runs/provenance-window-factory-20260511-e5cadets-pidsmaker/window_features.csv"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs/provenance-detector-zoo-gate-20260511"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/PROVENANCE_DETECTOR_ZOO_GATE_20260511.md"),
    )
    parser.add_argument("--min-class-count", type=int, default=5)
    parser.add_argument("--test-size", type=float, default=0.4)
    parser.add_argument("--seed", type=int, default=20260511)
    args = parser.parse_args()

    frame = pd.read_csv(args.features)
    frame["target"] = (frame["labels"].fillna("").astype(str) != "").astype(int)
    class_counts = Counter(
        {
            "benign_or_unlabeled": int((frame["target"] == 0).sum()),
            "attack_node_touch": int((frame["target"] == 1).sum()),
        }
    )
    feature_columns = select_features(frame)
    enough_classes = len([count for count in class_counts.values() if count > 0]) == 2
    enough_support = enough_classes and min(class_counts.values()) >= args.min_class_count
    results: list[dict[str, Any]] = []

    if enough_support:
        x = frame[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
        y = frame["target"].to_numpy()
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=args.test_size,
            random_state=args.seed,
            stratify=y,
        )
        for spec in detector_table():
            detector = make_detector(spec["name"], random_state=args.seed)
            detector.fit(x_train, y_train)
            pred = detector.predict(x_test)
            if hasattr(detector, "predict_proba"):
                score = detector.predict_proba(x_test)[:, 1]
            else:
                score = pred.astype(float)
            results.append(
                {
                    "detector": spec["name"],
                    "accuracy": float(accuracy_score(y_test, pred)),
                    "macro_f1": float(f1_score(y_test, pred, average="macro", zero_division=0)),
                    "roc_auc": float(roc_auc_score(y_test, score)),
                    "average_precision": float(average_precision_score(y_test, score)),
                }
            )

    if enough_support:
        decision = "RUN COMPLETE - DETECTOR ZOO BASELINE AVAILABLE"
        rationale = "Both classes have enough window support for a first stratified detector-zoo split."
        interpretation = (
            "These are still architecture baselines. Treat them as a readiness gate before "
            "claiming drift, watermarking, MIA, or adversarial robustness."
        )
    else:
        decision = "BLOCKED - INSUFFICIENT BENIGN/ATTACK WINDOW SUPPORT"
        rationale = (
            "The labeled window table is too imbalanced for an honest detector claim. "
            f"Minimum class count is {min(class_counts.values())}, below the "
            f"required {args.min_class_count}."
        )
        interpretation = (
            "Do not train/publish detector results from this sample. The PIDSMaker node labels "
            "are useful, but this window table has too few benign/unlabeled windows after "
            "node-label attachment. Add confirmed benign windows, attach interval labels, or switch "
            "to a different labeled host stream before making supervised detector claims."
        )

    summary = {
        "decision": decision,
        "rationale": rationale,
        "interpretation": interpretation,
        "features": str(args.features),
        "window_count": int(len(frame)),
        "feature_count": int(len(feature_columns)),
        "class_counts": dict(class_counts),
        "results": results,
        "detectors": detector_table(),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), **summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
