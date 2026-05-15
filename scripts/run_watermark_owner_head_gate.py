from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for candidate in (SRC_ROOT, REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03

from scripts.run_tta_streaming_apt_pilot import (
    instantiate_mlp,
    load_settings,
    predict_probs,
)


def entropy(probs: np.ndarray) -> np.ndarray:
    clipped = np.clip(probs, 1e-12, 1.0)
    return -(clipped * np.log(clipped)).sum(axis=1)


def classification_metrics(y_true: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    pred = probs.argmax(axis=1)
    labels = list(range(len(v02.STAGE_NAMES)))
    per_class = f1_score(y_true, pred, labels=labels, average=None, zero_division=0)
    y_bin = label_binarize(y_true, classes=labels)
    try:
        pr_auc = average_precision_score(y_bin, probs, average="macro")
    except ValueError:
        pr_auc = float("nan")
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "macro_f1": float(f1_score(y_true, pred, average="macro", zero_division=0)),
        "pr_auc": float(pr_auc),
        "recon_f1": float(per_class[v02.STAGE_NAMES.index("Reconnaissance")]),
        "de_f1": float(per_class[v02.STAGE_NAMES.index("Data Exfiltration")]),
    }


def sidecar_features(probs: np.ndarray) -> np.ndarray:
    sorted_probs = np.sort(probs, axis=1)
    confidence = sorted_probs[:, -1]
    margin = sorted_probs[:, -1] - sorted_probs[:, -2]
    ent = entropy(probs)
    pred = probs.argmax(axis=1)
    pred_onehot = np.eye(probs.shape[1], dtype=np.float32)[pred]
    return np.column_stack([probs, confidence, margin, ent, pred_onehot]).astype(np.float32)


def split_indices(indices: np.ndarray, rng: np.random.Generator) -> dict[str, np.ndarray]:
    shuffled = np.array(indices, dtype=int)
    rng.shuffle(shuffled)
    n = len(shuffled)
    train_end = max(1, int(round(n * 0.50)))
    cal_end = max(train_end + 1, int(round(n * 0.75)))
    cal_end = min(cal_end, n - 1)
    return {
        "train": shuffled[:train_end],
        "calibration": shuffled[train_end:cal_end],
        "eval": shuffled[cal_end:],
    }


def build_trigger_control_table(
    y_val: np.ndarray,
    probs_val: np.ndarray,
    trigger_indices: np.ndarray,
    controls_per_trigger: int,
) -> pd.DataFrame:
    conf = probs_val.max(axis=1)
    ent = entropy(probs_val)
    sorted_probs = np.sort(probs_val, axis=1)
    margin = sorted_probs[:, -1] - sorted_probs[:, -2]
    trigger_set = set(int(idx) for idx in trigger_indices)

    rows: list[dict[str, Any]] = []
    used_controls: set[int] = set()
    candidates = pd.DataFrame(
        {
            "row_id": np.arange(len(y_val), dtype=int),
            "true_label": y_val.astype(int),
            "confidence": conf,
            "entropy": ent,
            "margin": margin,
        }
    )
    nontriggers = candidates[~candidates["row_id"].isin(trigger_set)].copy()
    for trigger_id in trigger_indices:
        trigger_id = int(trigger_id)
        t = candidates.loc[candidates["row_id"] == trigger_id].iloc[0]
        same_stage = nontriggers[nontriggers["true_label"] == int(t.true_label)].copy()
        if same_stage.empty:
            same_stage = nontriggers.copy()
        same_stage["distance"] = (
            (same_stage["confidence"] - float(t.confidence)).abs()
            + (same_stage["entropy"] - float(t.entropy)).abs()
            + (same_stage["margin"] - float(t.margin)).abs()
        )
        selected: list[int] = []
        for candidate_id in same_stage.sort_values("distance")["row_id"].astype(int):
            if candidate_id in used_controls:
                continue
            selected.append(int(candidate_id))
            used_controls.add(int(candidate_id))
            if len(selected) >= controls_per_trigger:
                break
        rows.append({"row_id": trigger_id, "is_trigger": 1, "paired_trigger_id": trigger_id})
        for control_id in selected:
            rows.append(
                {"row_id": control_id, "is_trigger": 0, "paired_trigger_id": trigger_id}
            )
    return pd.DataFrame(rows)


def choose_threshold(
    scores: np.ndarray,
    labels: np.ndarray,
    max_false_rate: float,
) -> tuple[float, dict[str, float]]:
    candidates = np.unique(np.concatenate(([0.0, 1.0], scores)))
    best_threshold = 1.0
    best_tpr = -1.0
    best_fpr = 1.0
    for threshold in candidates:
        pred = scores >= threshold
        positives = labels == 1
        negatives = labels == 0
        tpr = float(pred[positives].mean()) if positives.any() else 0.0
        fpr = float(pred[negatives].mean()) if negatives.any() else 1.0
        if fpr <= max_false_rate and (tpr > best_tpr or (tpr == best_tpr and fpr < best_fpr)):
            best_threshold = float(threshold)
            best_tpr = tpr
            best_fpr = fpr
    return best_threshold, {"calibration_tpr": best_tpr, "calibration_fpr": best_fpr}


def binary_metrics(scores: np.ndarray, labels: np.ndarray, threshold: float) -> dict[str, float]:
    pred = scores >= threshold
    positives = labels == 1
    negatives = labels == 0
    try:
        auc = roc_auc_score(labels, scores)
    except ValueError:
        auc = float("nan")
    try:
        ap = average_precision_score(labels, scores)
    except ValueError:
        ap = float("nan")
    return {
        "roc_auc": float(auc),
        "average_precision": float(ap),
        "trigger_detection_rate": float(pred[positives].mean()) if positives.any() else 0.0,
        "false_watermark_rate": float(pred[negatives].mean()) if negatives.any() else 0.0,
        "accuracy": float(accuracy_score(labels, pred.astype(int))),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# APT Detector Watermark Owner-Head Gate",
        "",
        "Generated: 2026-05-14",
        "",
        "## Decision",
        "",
        f"Gate result: `{summary['decision']}`",
        "",
        summary["rationale"],
        "",
        "This is a redesign gate for a frozen-detector owner-verification sidecar. It is not a claim that the watermark transfers to a stolen surrogate.",
        "",
        "## Detector Utility",
        "",
        "| Metric | Source detector | Sidecar detector | Delta |",
        "|---|---:|---:|---:|",
    ]
    for metric in ["accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]:
        before = summary["source_test_metrics"][metric]
        after = summary["sidecar_test_metrics"][metric]
        lines.append(f"| {metric} | {before:.4f} | {after:.4f} | {after - before:+.4f} |")
    lines.extend(
        [
            "",
            "## Owner-Verification Head",
            "",
            "| Metric | Value | Gate |",
            "|---|---:|---:|",
            f"| Validation-only trigger rows | {summary['trigger_count']} | >= 20 |",
            f"| Eval trigger detection rate | {summary['eval_metrics']['trigger_detection_rate']:.4f} | >= 0.9500 |",
            f"| Eval false watermark rate | {summary['eval_metrics']['false_watermark_rate']:.4f} | <= 0.0500 |",
            f"| Background false watermark rate | {summary['background_false_watermark_rate']:.4f} | <= 0.0500 |",
            f"| Eval ROC-AUC | {summary['eval_metrics']['roc_auc']:.4f} | diagnostic |",
            f"| Eval AP | {summary['eval_metrics']['average_precision']:.4f} | diagnostic |",
            f"| Selected threshold | {summary['threshold']:.6f} | calibration only |",
            "",
            "## Split Counts",
            "",
            "| Split | Trigger rows | Control rows |",
            "|---|---:|---:|",
        ]
    )
    for split in ["train", "calibration", "eval"]:
        counts = summary["split_counts"][split]
        lines.append(f"| {split} | {counts['triggers']} | {counts['controls']} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "## Next Gate",
            "",
            summary["next_gate"],
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the redesigned owner-verification-head gate for APT detector watermarking."
    )
    parser.add_argument(
        "--source-run-dir", default="runs/mlp-support-floor-3seed-ablation-20260423"
    )
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--trigger-csv",
        type=Path,
        default=Path("runs/watermark-trigger-candidates-20260509/trigger_candidates.csv"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("runs/watermark-owner-head-gate-20260514"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/apt_detector_watermarking/WATERMARK_OWNER_HEAD_GATE_20260514.md"),
    )
    parser.add_argument("--controls-per-trigger", type=int, default=2)
    parser.add_argument("--max-false-rate", type=float, default=0.05)
    parser.add_argument("--background-sample", type=int, default=5000)
    args = parser.parse_args()

    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    source_summary = json.loads(
        (source_run_dir / "summary.json").read_text(encoding="utf-8")
    )
    config_path = Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    args.run_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(int(args.seed))
    v02.set_random_seed(int(args.seed))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    _train_df, val_df, test_df, feature_cols, preprocess_summary = (
        v03.prepare_features_and_splits_v03(
            df=df,
            settings=settings,
            gml=gml,
            run_dir=args.run_dir,
        )
    )
    x_val, y_val = v02.build_row_arrays(val_df, feature_cols)
    x_test, y_test = v02.build_row_arrays(test_df, feature_cols)

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")
    model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params)
    state_path = (
        source_run_dir
        / "seed_runs"
        / str(args.variant)
        / f"seed_{args.seed}"
        / "mlp_state_dict.pt"
    )
    model.load_state_dict(torch.load(state_path, map_location=torch.device("cpu")))
    model.eval()

    source_val_probs = predict_probs(model, x_val, 4096, torch.device("cpu"))
    source_test_probs = predict_probs(model, x_test, 4096, torch.device("cpu"))
    source_test_metrics = classification_metrics(y_test, source_test_probs)

    triggers = pd.read_csv(args.trigger_csv)
    val_triggers = triggers[triggers["split"] == "val"].copy()
    if len(val_triggers) < 20:
        raise SystemExit("Owner-head gate requires at least 20 validation trigger rows.")
    trigger_indices = val_triggers["row_id"].astype(int).to_numpy()
    split_by_trigger = split_indices(trigger_indices, rng)

    pair_table = build_trigger_control_table(
        y_val=y_val,
        probs_val=source_val_probs,
        trigger_indices=trigger_indices,
        controls_per_trigger=int(args.controls_per_trigger),
    )
    split_lookup = {}
    for split, ids in split_by_trigger.items():
        for trigger_id in ids:
            split_lookup[int(trigger_id)] = split
    pair_table["split"] = pair_table["paired_trigger_id"].astype(int).map(split_lookup)
    pair_table = pair_table.dropna(subset=["split"]).copy()

    features_val = sidecar_features(source_val_probs)
    data = features_val[pair_table["row_id"].astype(int).to_numpy()]
    labels = pair_table["is_trigger"].astype(int).to_numpy()
    splits = pair_table["split"].astype(str).to_numpy()

    train_mask = splits == "train"
    cal_mask = splits == "calibration"
    eval_mask = splits == "eval"
    head = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        random_state=int(args.seed),
    )
    head.fit(data[train_mask], labels[train_mask])
    cal_scores = head.predict_proba(data[cal_mask])[:, 1]
    threshold, threshold_diag = choose_threshold(
        cal_scores,
        labels[cal_mask],
        max_false_rate=float(args.max_false_rate),
    )
    eval_scores = head.predict_proba(data[eval_mask])[:, 1]
    eval_metrics = binary_metrics(eval_scores, labels[eval_mask], threshold)

    all_nontrigger_mask = np.ones(len(x_val), dtype=bool)
    all_nontrigger_mask[trigger_indices] = False
    background_indices = np.flatnonzero(all_nontrigger_mask)
    if len(background_indices) > int(args.background_sample):
        background_indices = rng.choice(
            background_indices, size=int(args.background_sample), replace=False
        )
    background_scores = head.predict_proba(features_val[background_indices])[:, 1]
    background_false_rate = float((background_scores >= threshold).mean())

    split_counts: dict[str, dict[str, int]] = {}
    for split in ["train", "calibration", "eval"]:
        split_frame = pair_table[pair_table["split"] == split]
        split_counts[split] = {
            "triggers": int(split_frame["is_trigger"].sum()),
            "controls": int((split_frame["is_trigger"] == 0).sum()),
        }

    utility_pass = True
    signature_pass = eval_metrics["trigger_detection_rate"] >= 0.95
    eval_fpr_pass = eval_metrics["false_watermark_rate"] <= float(args.max_false_rate)
    background_fpr_pass = background_false_rate <= float(args.max_false_rate)
    proceed = utility_pass and signature_pass and eval_fpr_pass and background_fpr_pass
    decision = (
        "PROCEED - SIDECAR OWNER-VERIFICATION GATE PASSED"
        if proceed
        else "STOP - SIDECAR OWNER-VERIFICATION GATE FAILED"
    )
    rationale = (
        "The frozen detector preserved ordinary utility by construction, and the sidecar head separated held-out trigger rows from matched controls within the false-ownership gate."
        if proceed
        else "The frozen-detector sidecar did not separate held-out trigger rows from matched controls strongly enough to justify escalation."
    )
    interpretation = (
        "This is a narrow positive for service-level owner verification, not a transferred neural watermark. The primary detector weights are unchanged, so normal APT detection metrics are unchanged; the claim would be that a deployed service can answer private ownership queries with a separate head."
        if proceed
        else "This closes the current watermarking redesign as negative for this detector lineage. The direct fine-tuning watermark already failed utility/signature, and the sidecar head also fails the strict held-out trigger/control gate."
    )
    next_gate = (
        "If this line continues, define it as sidecar owner verification and evaluate independent false-ownership against other detector checkpoints. Do not run surrogate-retention as a watermark-transfer claim."
        if proceed
        else "Archive detector watermarking for now and revisit only after a stronger detector suite exists."
    )

    summary = {
        "decision": decision,
        "rationale": rationale,
        "interpretation": interpretation,
        "next_gate": next_gate,
        "source_run_dir": str(source_run_dir),
        "variant": args.variant,
        "seed": int(args.seed),
        "trigger_count": int(len(trigger_indices)),
        "controls_per_trigger": int(args.controls_per_trigger),
        "threshold": float(threshold),
        "threshold_diagnostics": threshold_diag,
        "source_test_metrics": source_test_metrics,
        "sidecar_test_metrics": source_test_metrics,
        "eval_metrics": eval_metrics,
        "background_false_watermark_rate": background_false_rate,
        "split_counts": split_counts,
        "preprocess_summary": preprocess_summary,
    }
    pair_table.to_csv(args.run_dir / "owner_head_pairs.csv", index=False)
    (args.run_dir / "summary.json").write_text(
        json.dumps(v02.coerce_json(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(
        json.dumps(
            {
                "decision": decision,
                "report": str(args.report),
                "eval_trigger_detection_rate": eval_metrics["trigger_detection_rate"],
                "eval_false_watermark_rate": eval_metrics["false_watermark_rate"],
                "background_false_watermark_rate": background_false_rate,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
