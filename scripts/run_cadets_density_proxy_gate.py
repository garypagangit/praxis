from __future__ import annotations

import argparse
import json
import sys
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


EXCLUDED_COLUMNS = {
    "window_id",
    "start_ns",
    "end_ns",
    "primary_label",
    "labels",
    "node_labels",
    "label_overlap_ns",
    "malicious_node_events",
    "malicious_node_count",
}


def select_features(frame: pd.DataFrame) -> list[str]:
    features: list[str] = []
    for column in frame.columns:
        if column in EXCLUDED_COLUMNS:
            continue
        if not (column.startswith("event__") or column.startswith("exec__")):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            features.append(column)
    return features


def score_split(
    frame: pd.DataFrame,
    feature_columns: list[str],
    train_index: np.ndarray,
    test_index: np.ndarray,
    seed: int,
) -> list[dict[str, Any]]:
    x = frame[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()
    y = frame["density_target"].to_numpy()
    x_train, x_test = x[train_index], x[test_index]
    y_train, y_test = y[train_index], y[test_index]

    results: list[dict[str, Any]] = []
    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        return results

    for spec in detector_table():
        detector = make_detector(spec["name"], random_state=seed)
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
    return results


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cadets Attack-Touch Density Proxy Gate",
        "",
        "Generated: 2026-05-12",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        summary["rationale"],
        "",
        "## Setup",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Windows | {summary['window_count']} |",
        f"| Numeric features used | {summary['feature_count']} |",
        f"| Density threshold | {summary['threshold']} |",
        f"| Low-touch windows | {summary['class_counts']['low_touch']} |",
        f"| High-touch windows | {summary['class_counts']['high_touch']} |",
        "",
        "Only event-rate and exec-rate features were used. Direct label columns, direct malicious-node count columns, and window metadata were excluded from features.",
        "",
        "## Random Stratified Split",
        "",
        "| Detector | Accuracy | Macro-F1 | ROC-AUC | AP |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["random_results"]:
        lines.append(
            f"| `{row['detector']}` | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | "
            f"{row['roc_auc']:.4f} | {row['average_precision']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Chronological Split",
            "",
            "| Detector | Accuracy | Macro-F1 | ROC-AUC | AP |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary["chronological_results"]:
        lines.append(
            f"| `{row['detector']}` | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | "
            f"{row['roc_auc']:.4f} | {row['average_precision']:.4f} |"
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
        default=Path("runs/full-e5cadets-window-factory-20260511/window_features.csv"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs/cadets-density-proxy-gate-20260512"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/provenance_architecture/CADETS_ATTACK_TOUCH_DENSITY_PROXY_GATE_20260512.md"
        ),
    )
    parser.add_argument("--threshold", type=int, default=5000)
    parser.add_argument("--test-size", type=float, default=0.4)
    parser.add_argument("--seed", type=int, default=20260512)
    args = parser.parse_args()

    frame = pd.read_csv(args.features).sort_values("window_id").reset_index(drop=True)
    frame["density_target"] = (frame["malicious_node_events"] > args.threshold).astype(int)
    feature_columns = select_features(frame)
    class_counts = {
        "low_touch": int((frame["density_target"] == 0).sum()),
        "high_touch": int((frame["density_target"] == 1).sum()),
    }

    indices = np.arange(len(frame))
    train_index, test_index = train_test_split(
        indices,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=frame["density_target"],
    )
    random_results = score_split(frame, feature_columns, train_index, test_index, args.seed)

    chronological_cut = int(len(frame) * (1 - args.test_size))
    chronological_results = score_split(
        frame,
        feature_columns,
        np.arange(0, chronological_cut),
        np.arange(chronological_cut, len(frame)),
        args.seed,
    )

    best_chrono = max((row["macro_f1"] for row in chronological_results), default=0.0)
    if best_chrono >= 0.70:
        decision = "WEAK-PROXY DIAGNOSTIC AVAILABLE"
        rationale = (
            "Event/exec window features carry signal for high-touch versus low-touch windows, "
            "even when direct malicious-node count columns are excluded."
        )
    else:
        decision = "WEAK-PROXY ONLY - CHRONOLOGICAL SIGNAL WEAK"
        rationale = (
            "Random split may show signal, but chronological generalization is not strong enough "
            "to use this proxy as a stable representation gate."
        )
    interpretation = (
        "This is not an attack detector and not a publishable supervised claim. It is a weak-proxy "
        "diagnostic for prioritizing windows, stress-testing representations, or choosing samples "
        "for manual interval labeling."
    )
    summary = {
        "decision": decision,
        "rationale": rationale,
        "interpretation": interpretation,
        "features": str(args.features),
        "threshold": args.threshold,
        "window_count": int(len(frame)),
        "feature_count": int(len(feature_columns)),
        "class_counts": class_counts,
        "excluded_columns": sorted(EXCLUDED_COLUMNS),
        "random_results": random_results,
        "chronological_results": chronological_results,
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
