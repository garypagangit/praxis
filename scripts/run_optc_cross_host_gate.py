from __future__ import annotations

import argparse
import json
import sys
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
    "global_window_id",
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
    "slice",
    "host",
    "day",
    "slice_kind",
}


DEFAULT_SLICES = [
    (
        "sysclient0501_day2",
        "sysclient0501",
        "2",
        Path("runs/optc-window-gate-20260514-pass/window_features.csv"),
        Path("runs/optc-label-acquisition-20260514/optc_window_labels.csv"),
    ),
    (
        "sysclient0201_day1",
        "sysclient0201",
        "1",
        Path("runs/optc-window-gate-20260515-sysclient0201-wide/window_features.csv"),
        Path("runs/optc-label-acquisition-20260515-sysclient0201-wide/optc_window_labels.csv"),
    ),
    (
        "sysclient0051_day3",
        "sysclient0051",
        "3",
        Path("runs/optc-window-gate-20260515-sysclient0051-wide/window_features.csv"),
        Path("runs/optc-label-acquisition-20260515-sysclient0051-wide/optc_window_labels.csv"),
    ),
    (
        "sysclient0501_benign",
        "sysclient0501",
        "benign_20_23Sep19",
        Path("runs/optc-window-gate-20260515-sysclient0501-benign/window_features.csv"),
        Path("runs/optc-label-acquisition-20260515-sysclient0501-benign/optc_window_labels.csv"),
    ),
    (
        "sysclient0201_benign",
        "sysclient0201",
        "benign_20_23Sep19",
        Path("runs/optc-window-gate-20260515-sysclient0201-benign/window_features.csv"),
        Path("runs/optc-label-acquisition-20260515-sysclient0201-benign/optc_window_labels.csv"),
    ),
    (
        "sysclient0051_benign",
        "sysclient0051",
        "benign_20_23Sep19",
        Path("runs/optc-window-gate-20260515-sysclient0051-benign/window_features.csv"),
        Path("runs/optc-label-acquisition-20260515-sysclient0051-benign/optc_window_labels.csv"),
    ),
]


def load_slice(
    name: str,
    host: str,
    day: str,
    features_path: Path,
    labels_path: Path,
) -> pd.DataFrame:
    missing = [path for path in [features_path, labels_path] if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing OpTC gate artifact(s): " + ", ".join(str(path) for path in missing)
        )
    features = pd.read_csv(features_path)
    labels = pd.read_csv(labels_path)
    frame = features.merge(
        labels[["window_id", "label", "attack_stages", "attack_hosts"]],
        on="window_id",
        how="inner",
    )
    frame["slice"] = name
    frame["host"] = host
    frame["day"] = str(day)
    frame["slice_kind"] = "benign_baseline" if "benign" in name else "red_team"
    frame["global_window_id"] = frame["slice"].astype(str) + ":" + frame["window_id"].astype(str)
    return frame


def select_features(frame: pd.DataFrame, mode: str) -> list[str]:
    features: list[str] = []
    for column in frame.columns:
        if column in NON_FEATURE_COLUMNS:
            continue
        if not pd.api.types.is_numeric_dtype(frame[column]):
            continue
        if mode == "event_aggregate" and column.startswith("exec__"):
            continue
        features.append(column)
    return features


def clean_matrix(frame: pd.DataFrame, feature_columns: list[str]) -> np.ndarray:
    return frame[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy()


def score_detector(detector: Any, x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    pred = detector.predict(x)
    if hasattr(detector, "predict_proba"):
        probabilities = detector.predict_proba(x)
        score = probabilities[:, 1] if probabilities.shape[1] > 1 else pred.astype(float)
    else:
        score = pred.astype(float)

    precision, recall, _, _ = precision_recall_fscore_support(
        y,
        pred,
        labels=[0, 1],
        zero_division=0,
    )
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    unique_labels = np.unique(y)
    if len(unique_labels) == 2:
        roc_auc = float(roc_auc_score(y, score))
        average_precision = float(average_precision_score(y, score))
    else:
        roc_auc = float("nan")
        average_precision = float("nan")
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "roc_auc": roc_auc,
        "average_precision": average_precision,
        "background_precision": float(precision[0]),
        "background_recall": float(recall[0]),
        "attack_precision": float(precision[1]),
        "attack_recall": float(recall[1]),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def split_train_validation(
    train_pool: pd.DataFrame,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_counts = train_pool["target"].value_counts()
    stratify = train_pool["target"] if len(target_counts) == 2 and target_counts.min() >= 2 else None
    train, validation = train_test_split(
        train_pool,
        test_size=0.25,
        random_state=seed,
        stratify=stratify,
    )
    return train.sort_values("global_window_id"), validation.sort_values("global_window_id")


def fit_and_score(
    train: pd.DataFrame,
    split_frames: dict[str, pd.DataFrame],
    feature_columns: list[str],
    seed: int,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    x_train = clean_matrix(train, feature_columns)
    y_train = train["target"].to_numpy()
    if len(np.unique(y_train)) < 2:
        return []

    results: list[dict[str, Any]] = []
    for spec in detector_table():
        detector = make_detector(spec["name"], random_state=seed)
        detector.fit(x_train, y_train)
        for split_name, split_frame in split_frames.items():
            row = score_detector(
                detector,
                clean_matrix(split_frame, feature_columns),
                split_frame["target"].to_numpy(),
            )
            row.update(metadata)
            row.update({"detector": spec["name"], "split": split_name})
            results.append(row)
    return results


def evaluate_red_holdout(
    usable: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
    include_heldout_host_benign: bool,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    protocol = (
        "red_day_holdout_with_host_baseline"
        if include_heldout_host_benign
        else "strict_host_holdout"
    )
    test_split = "test_red_day"
    validation_split = "validation_pool"
    results: list[dict[str, Any]] = []
    assignments: list[pd.DataFrame] = []
    red_slices = sorted(usable.loc[usable["slice_kind"] == "red_team", "slice"].unique())

    for heldout_slice in red_slices:
        heldout_rows = usable[usable["slice"] == heldout_slice]
        heldout_host = str(heldout_rows["host"].iloc[0])
        test = heldout_rows.sort_values("global_window_id").copy()
        if include_heldout_host_benign:
            train_pool = usable[usable["slice"] != heldout_slice].copy()
            train_label = "all_except_" + heldout_slice
        else:
            train_pool = usable[usable["host"] != heldout_host].copy()
            train_label = "all_except_host_" + heldout_host
        train, validation = split_train_validation(train_pool, seed)
        split_frames = {
            validation_split: validation,
            test_split: test,
        }
        results.extend(
            fit_and_score(
                train,
                split_frames,
                feature_columns,
                seed,
                {
                    "protocol": protocol,
                    "train_slice": train_label,
                    "test_slice": heldout_slice,
                    "heldout_host": heldout_host,
                },
            )
        )
        assignments.extend(
            [
                train.assign(protocol=f"{protocol}_{heldout_slice}", split="train"),
                validation.assign(protocol=f"{protocol}_{heldout_slice}", split=validation_split),
                test.assign(protocol=f"{protocol}_{heldout_slice}", split=test_split),
            ]
        )
    return results, pd.concat(assignments, ignore_index=True)


def evaluate_pairwise_red_host(
    usable: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    results: list[dict[str, Any]] = []
    assignments: list[pd.DataFrame] = []
    red_slices = sorted(usable.loc[usable["slice_kind"] == "red_team", "slice"].unique())
    benign = usable[usable["slice_kind"] == "benign_baseline"].copy()
    for train_slice in red_slices:
        train_red = usable[usable["slice"] == train_slice].copy()
        train_pool = pd.concat([train_red, benign], ignore_index=True, sort=False)
        test = usable[(usable["slice_kind"] == "red_team") & (usable["slice"] != train_slice)].copy()
        train, validation = split_train_validation(train_pool, seed)
        split_frames = {
            "validation_train_red_plus_benign": validation.sort_values("global_window_id"),
            "test_other_red_days": test.sort_values("global_window_id"),
        }
        results.extend(
            fit_and_score(
                train,
                split_frames,
                feature_columns,
                seed,
                {
                    "protocol": "pairwise_red_host",
                    "train_slice": train_slice + "_plus_benign",
                    "test_slice": "other_red_days",
                    "heldout_host": "multiple",
                },
            )
        )
        assignments.extend(
            [
                train.assign(protocol=f"pairwise_red_host_{train_slice}", split="train"),
                validation.assign(
                    protocol=f"pairwise_red_host_{train_slice}",
                    split="validation_train_red_plus_benign",
                ),
                test.assign(protocol=f"pairwise_red_host_{train_slice}", split="test_other_red_days"),
            ]
        )
    return results, pd.concat(assignments, ignore_index=True)


def evaluate_pooled_random(
    usable: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    strata = usable["slice"].astype(str) + ":" + usable["target"].astype(str)
    train, holdout = train_test_split(
        usable,
        test_size=0.4,
        random_state=seed,
        stratify=strata,
    )
    holdout_strata = holdout["slice"].astype(str) + ":" + holdout["target"].astype(str)
    validation, test = train_test_split(
        holdout,
        test_size=0.5,
        random_state=seed,
        stratify=holdout_strata,
    )
    split_frames = {"validation": validation, "test": test}
    results = fit_and_score(
        train,
        split_frames,
        feature_columns,
        seed,
        {
            "protocol": "pooled_stratified_random",
            "train_slice": "pooled",
            "test_slice": "pooled",
            "heldout_host": "none",
        },
    )
    assignments = pd.concat(
        [
            train.assign(protocol="pooled_stratified_random", split="train"),
            validation.assign(protocol="pooled_stratified_random", split="validation"),
            test.assign(protocol="pooled_stratified_random", split="test"),
        ],
        ignore_index=True,
    )
    return results, assignments


def build_label_support(frame: pd.DataFrame) -> dict[str, Any]:
    by_slice: dict[str, dict[str, Any]] = {}
    for slice_name, group in frame.groupby("slice"):
        by_slice[slice_name] = {
            "host": str(group["host"].iloc[0]),
            "day": str(group["day"].iloc[0]),
            "slice_kind": str(group["slice_kind"].iloc[0]),
            "attack": int((group["label"] == "attack").sum()),
            "background": int((group["label"] == "background").sum()),
            "gray_buffer": int((group["label"] == "gray_buffer").sum()),
            "total": int(len(group)),
        }
    red_ready = all(
        counts["attack"] >= 20 and counts["background"] >= 20
        for counts in by_slice.values()
        if counts["slice_kind"] == "red_team"
    )
    benign_ready = all(
        counts["background"] >= 50 and counts["attack"] == 0
        for counts in by_slice.values()
        if counts["slice_kind"] == "benign_baseline"
    )
    return {
        "by_slice": by_slice,
        "red_slice_support_ready": bool(red_ready),
        "benign_baseline_support_ready": bool(benign_ready),
        "support_ready": bool(red_ready and benign_ready),
    }


def detector_floor_passes(
    results: list[dict[str, Any]],
    protocol: str,
    feature_mode: str,
    red_slice_count: int,
    min_macro_floor: float = 0.65,
    min_background_floor: float = 0.50,
    min_attack_floor: float = 0.70,
) -> list[tuple[str, float, float, float]]:
    heldout_rows = [
        row
        for row in results
        if row["feature_mode"] == feature_mode
        and row["protocol"] == protocol
        and row["split"] == "test_red_day"
    ]
    detector_scores: dict[str, list[dict[str, Any]]] = {}
    for row in heldout_rows:
        detector_scores.setdefault(row["detector"], []).append(row)

    passes = []
    for detector, rows in detector_scores.items():
        if len(rows) < red_slice_count:
            continue
        min_macro = min(row["macro_f1"] for row in rows)
        min_background = min(row["background_recall"] for row in rows)
        min_attack = min(row["attack_recall"] for row in rows)
        if (
            min_macro >= min_macro_floor
            and min_background >= min_background_floor
            and min_attack >= min_attack_floor
        ):
            passes.append((detector, min_macro, min_background, min_attack))
    return sorted(passes, key=lambda item: item[1], reverse=True)


def decide(results: list[dict[str, Any]], label_support: dict[str, Any]) -> tuple[str, str]:
    if not label_support["support_ready"]:
        return (
            "LABEL SUPPORT BLOCKED",
            "The expanded OpTC slices still do not provide the required red-team and benign baseline support. "
            "Do not train or claim a provenance detector yet.",
        )

    red_slice_count = sum(
        1 for counts in label_support["by_slice"].values() if counts["slice_kind"] == "red_team"
    )
    event_passes = detector_floor_passes(
        results,
        protocol="red_day_holdout_with_host_baseline",
        feature_mode="event_aggregate",
        red_slice_count=red_slice_count,
    )
    behavior_passes = detector_floor_passes(
        results,
        protocol="red_day_holdout_with_host_baseline",
        feature_mode="all_behavior",
        red_slice_count=red_slice_count,
    )
    strict_event_passes = detector_floor_passes(
        results,
        protocol="strict_host_holdout",
        feature_mode="event_aggregate",
        red_slice_count=red_slice_count,
    )

    if event_passes:
        best = event_passes[0]
        strict_note = (
            "Strict host holdout also clears the event-aggregate floor."
            if strict_event_passes
            else "Strict host holdout remains a separate generalization caveat."
        )
        return (
            "PRAXIS-READY HOST-BASELINED FEASIBILITY PASS",
            f"The OpTC expansion clears label support across three red-team host/day slices and three clean "
            f"benign host baselines. In the host-baselined red-day holdout, `{best[0]}` clears the conservative "
            f"event-aggregate floor with minimum Macro-F1 {best[1]:.4f}, background recall {best[2]:.4f}, "
            f"and attack recall {best[3]:.4f}. {strict_note} This supports a narrow host-baselined "
            "provenance-window detector feasibility claim, not a broad cross-host production detector claim.",
        )

    if behavior_passes:
        best = behavior_passes[0]
        return (
            "LABEL-READY; DETECTOR FEASIBILITY IS FEATURE-DEPENDENT",
            f"The expanded labels are Praxis-ready as a data artifact. The host-baselined detector gate only "
            f"clears when `exec__*` behavior columns are included: `{best[0]}` minimum Macro-F1 {best[1]:.4f}, "
            f"background recall {best[2]:.4f}, attack recall {best[3]:.4f}. Treat this as a promising but "
            "feature-dependent detector lead, not the final provenance detector claim.",
        )

    return (
        "LABEL-READY, DETECTOR NOT PROMOTED",
        "The OpTC expansion clears label support across red-team and benign baseline slices, but the detector "
        "does not clear the conservative host-baselined holdout floor. Use this as a strong label/data unlock "
        "and keep detector claims blocked.",
    )


def metric_text(value: float) -> str:
    if pd.isna(value):
        return "nan"
    return f"{value:.4f}"


def render_result_rows(
    lines: list[str],
    results: list[dict[str, Any]],
    protocol: str,
    split: str,
    include_train: bool = False,
) -> None:
    for row in results:
        if row["protocol"] != protocol or row["split"] != split:
            continue
        train = f"| `{row['train_slice']}` " if include_train else ""
        lines.append(
            f"{train}| `{row['feature_mode']}` | `{row['test_slice']}` | `{row['detector']}` | "
            f"{metric_text(row['accuracy'])} | {metric_text(row['macro_f1'])} | "
            f"{metric_text(row['roc_auc'])} | {metric_text(row['average_precision'])} | "
            f"{metric_text(row['attack_recall'])} | {metric_text(row['background_recall'])} |"
        )


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# OpTC Expanded Provenance Gate",
        "",
        "Generated: 2026-05-15",
        "",
        f"Status: **{summary['decision']}**",
        "",
        "## Scope",
        "",
        "This gate tests whether OpTC interval labels plus targeted eCAR host/day shards are strong enough for a narrow provenance-window detector feasibility claim.",
        "",
        "- Red-team slices: `sysclient0201` day 1 / `23Sep19-red`, `sysclient0501` day 2 / `24Sep19`, and `sysclient0051` day 3 / `25Sept`",
        "- Benign baselines: `sysclient0201`, `sysclient0501`, and `sysclient0051` from `benign/20-23Sep19`",
        "- Target: `attack` vs `background` windows",
        "- Excluded: `gray_buffer` windows",
        "- Primary detector split: hold out one red-team host/day and train on the other red-team slices plus benign baselines, including the held-out host's clean baseline",
        "- Strict generalization split: hold out the entire host, including its red-team and benign windows",
        "- Pairwise stress split: train on one red-team host/day plus all benign baselines, then test on the other red-team host/days",
        "- Sanity split: pooled stratified random split across all non-gray windows",
        "- Conservative feature view: event counts plus aggregate window statistics; `exec__*` columns excluded",
        "- Full feature view: event, exec, and aggregate behavior columns",
        "- Time columns and label-derived columns excluded from all detector features",
        "",
        "## Label Support",
        "",
        "| Slice | Kind | Host | Day | Attack | Background | Gray buffer | Total |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for slice_name, counts in summary["label_support"]["by_slice"].items():
        lines.append(
            f"| `{slice_name}` | `{counts['slice_kind']}` | `{counts['host']}` | `{counts['day']}` | "
            f"`{counts['attack']}` | `{counts['background']}` | `{counts['gray_buffer']}` | `{counts['total']}` |"
        )
    lines.extend(
        [
            "",
            "## Host-Baselined Red-Day Holdout",
            "",
            "| Feature mode | Held-out red slice | Detector | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    render_result_rows(
        lines,
        summary["results"],
        protocol="red_day_holdout_with_host_baseline",
        split="test_red_day",
    )
    lines.extend(
        [
            "",
            "## Strict Host Holdout",
            "",
            "| Feature mode | Held-out red slice | Detector | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    render_result_rows(
        lines,
        summary["results"],
        protocol="strict_host_holdout",
        split="test_red_day",
    )
    lines.extend(
        [
            "",
            "## Pairwise Red-Host Stress",
            "",
            "| Train slice | Feature mode | Test red slices | Detector | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    render_result_rows(
        lines,
        summary["results"],
        protocol="pairwise_red_host",
        split="test_other_red_days",
        include_train=True,
    )
    lines.extend(
        [
            "",
            "## Pooled Random Sanity Results",
            "",
            "| Feature mode | Detector | Split | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["results"]:
        if row["protocol"] != "pooled_stratified_random":
            continue
        lines.append(
            f"| `{row['feature_mode']}` | `{row['detector']}` | `{row['split']}` | "
            f"{metric_text(row['accuracy'])} | {metric_text(row['macro_f1'])} | "
            f"{metric_text(row['roc_auc'])} | {metric_text(row['average_precision'])} | "
            f"{metric_text(row['attack_recall'])} | {metric_text(row['background_recall'])} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            summary["interpretation"],
            "",
            "## Artifacts",
            "",
            "| Artifact | Path |",
            "|---|---|",
            f"| Summary JSON | `{summary['summary_path']}` |",
            f"| Metrics CSV | `{summary['metrics_path']}` |",
            f"| Split assignments | `{summary['split_path']}` |",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("runs/optc-cross-host-gate-20260515"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/OPTC_CROSS_HOST_GATE_20260515.md"),
    )
    parser.add_argument("--seed", type=int, default=20260515)
    args = parser.parse_args()

    frames = [load_slice(*slice_args) for slice_args in DEFAULT_SLICES]
    frame = pd.concat(frames, ignore_index=True, sort=False)
    label_support = build_label_support(frame)
    usable = frame[frame["label"].isin(["attack", "background"])].copy()
    usable["target"] = (usable["label"] == "attack").astype(int)

    all_results: list[dict[str, Any]] = []
    all_assignments: list[pd.DataFrame] = []
    feature_counts: dict[str, int] = {}
    for feature_mode in ["event_aggregate", "all_behavior"]:
        feature_columns = select_features(usable, feature_mode)
        feature_counts[feature_mode] = len(feature_columns)
        host_results, host_assignments = evaluate_red_holdout(
            usable,
            feature_columns,
            args.seed,
            include_heldout_host_benign=True,
        )
        strict_results, strict_assignments = evaluate_red_holdout(
            usable,
            feature_columns,
            args.seed,
            include_heldout_host_benign=False,
        )
        pairwise_results, pairwise_assignments = evaluate_pairwise_red_host(
            usable,
            feature_columns,
            args.seed,
        )
        pooled_results, pooled_assignments = evaluate_pooled_random(usable, feature_columns, args.seed)
        for row in host_results + strict_results + pairwise_results + pooled_results:
            row["feature_mode"] = feature_mode
            all_results.append(row)
        all_assignments.extend(
            [
                host_assignments.assign(feature_mode=feature_mode),
                strict_assignments.assign(feature_mode=feature_mode),
                pairwise_assignments.assign(feature_mode=feature_mode),
                pooled_assignments.assign(feature_mode=feature_mode),
            ]
        )

    decision, interpretation = decide(all_results, label_support)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.out_dir / "metrics.csv"
    split_path = args.out_dir / "split_assignments.csv"
    summary_path = args.out_dir / "summary.json"
    pd.DataFrame(all_results).to_csv(metrics_path, index=False)
    pd.concat(all_assignments, ignore_index=True)[
        [
            "feature_mode",
            "protocol",
            "split",
            "slice",
            "host",
            "day",
            "slice_kind",
            "global_window_id",
            "label",
            "target",
        ]
    ].to_csv(split_path, index=False)

    summary = {
        "decision": decision,
        "interpretation": interpretation,
        "feature_counts": feature_counts,
        "label_support": label_support,
        "usable_windows": int(len(usable)),
        "excluded_gray_buffer_windows": int((frame["label"] == "gray_buffer").sum()),
        "results": all_results,
        "summary_path": str(summary_path),
        "metrics_path": str(metrics_path),
        "split_path": str(split_path),
        "report": str(args.report),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), **summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
