from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    roc_auc_score,
)

from praxis.praxis04.data_loader import load_preprocessed_split, split_to_matrices


def entropy(probs: np.ndarray) -> np.ndarray:
    clipped = np.clip(probs, 1e-12, 1.0)
    return -(clipped * np.log(clipped)).sum(axis=1)


def align_proba(probs: np.ndarray, classes: np.ndarray, n_classes: int) -> np.ndarray:
    aligned = np.zeros((len(probs), n_classes), dtype=np.float32)
    for source_idx, class_id in enumerate(classes.astype(int)):
        if 0 <= class_id < n_classes:
            aligned[:, class_id] = probs[:, source_idx]
    return aligned


def score_attack(member_scores: np.ndarray, nonmember_scores: np.ndarray) -> dict:
    y_true = np.concatenate(
        [
            np.ones(len(member_scores), dtype=np.int8),
            np.zeros(len(nonmember_scores), dtype=np.int8),
        ]
    )
    scores = np.concatenate([member_scores, nonmember_scores])
    threshold = float(np.median(scores))
    y_pred = (scores >= threshold).astype(np.int8)
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "average_precision": float(average_precision_score(y_true, scores)),
        "balanced_accuracy_at_median_threshold": float(
            balanced_accuracy_score(y_true, y_pred)
        ),
        "threshold_median": threshold,
        "member_mean": float(np.mean(member_scores)),
        "nonmember_mean": float(np.mean(nonmember_scores)),
        "member_p95": float(np.quantile(member_scores, 0.95)),
        "nonmember_p95": float(np.quantile(nonmember_scores, 0.95)),
    }


def subsample(
    x: np.ndarray, y: np.ndarray, limit: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    if limit <= 0 or len(x) <= limit:
        return x, y
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(x), size=limit, replace=False)
    return x[idx], y[idx]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a cheap confidence-based membership inference pilot against an APT detector."
    )
    parser.add_argument("--data-dir", default="data/cic-ids-2018")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--sample-rows-per-file", type=int, default=5000)
    parser.add_argument("--member-limit", type=int, default=20000)
    parser.add_argument("--nonmember-limit", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--n-estimators", type=int, default=120)
    parser.add_argument("--max-depth", type=int, default=None)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    split = load_preprocessed_split(
        args.data_dir,
        sample_rows_per_file=args.sample_rows_per_file,
        sample_seed=args.seed,
        sample_strategy="uniform",
        holdout_day_pattern="02-03-2018",
        val_fraction_of_train_days=0.2,
    )
    matrices = split_to_matrices(split)

    train_x, train_y = subsample(
        matrices.x_train, matrices.y_train, args.member_limit, args.seed
    )
    test_x, test_y = subsample(
        matrices.x_test, matrices.y_test, args.nonmember_limit, args.seed + 1
    )

    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.seed,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    model.fit(train_x, train_y)

    n_classes = len(matrices.label_names)
    member_probs = align_proba(model.predict_proba(train_x), model.classes_, n_classes)
    nonmember_probs = align_proba(
        model.predict_proba(test_x), model.classes_, n_classes
    )

    member_pred = member_probs.argmax(axis=1)
    nonmember_pred = nonmember_probs.argmax(axis=1)
    member_correct = (member_pred == train_y).astype(float)
    nonmember_correct = (nonmember_pred == test_y).astype(float)

    member_true_prob = member_probs[np.arange(len(train_y)), train_y]
    nonmember_true_prob = nonmember_probs[np.arange(len(test_y)), test_y]

    attacks = {
        "max_confidence": score_attack(
            member_probs.max(axis=1), nonmember_probs.max(axis=1)
        ),
        "negative_entropy": score_attack(
            -entropy(member_probs), -entropy(nonmember_probs)
        ),
        "true_class_probability": score_attack(member_true_prob, nonmember_true_prob),
        "correctness": score_attack(member_correct, nonmember_correct),
    }

    payload = {
        "seed": args.seed,
        "sample_rows_per_file": args.sample_rows_per_file,
        "member_rows": int(len(train_x)),
        "nonmember_rows": int(len(test_x)),
        "label_names": matrices.label_names,
        "stage_names": matrices.stage_names,
        "data_summary": matrices.summary,
        "attacks": attacks,
        "target_train_accuracy": float(member_correct.mean()),
        "target_nonmember_accuracy": float(nonmember_correct.mean()),
        "gate_decision": {
            "data_and_target_detector": "pass",
            "mia_signal": (
                "positive"
                if max(v["roc_auc"] for v in attacks.values()) >= 0.6
                else "weak"
            ),
            "shadow_model_protocol": "not_run",
        },
    }

    (out_dir / "summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    best_name, best = max(attacks.items(), key=lambda item: item[1]["roc_auc"])
    report = [
        "# Membership Inference - APT Detector Pilot",
        "",
        "## Result",
        "",
        f"- Target detector: `RandomForestClassifier`",
        f"- Member rows: `{len(train_x)}`",
        f"- Nonmember rows: `{len(test_x)}`",
        f"- Target train accuracy: `{payload['target_train_accuracy']:.4f}`",
        f"- Target nonmember accuracy: `{payload['target_nonmember_accuracy']:.4f}`",
        f"- Best attack score: `{best_name}`",
        f"- Best attack ROC-AUC: `{best['roc_auc']:.4f}`",
        f"- Best attack AP: `{best['average_precision']:.4f}`",
        "",
        "## Attack Table",
        "",
        "| Attack score | ROC-AUC | AP | Balanced acc @ median | Member mean | Nonmember mean |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, row in attacks.items():
        report.append(
            f"| {name} | {row['roc_auc']:.4f} | {row['average_precision']:.4f} | "
            f"{row['balanced_accuracy_at_median_threshold']:.4f} | "
            f"{row['member_mean']:.4f} | {row['nonmember_mean']:.4f} |"
        )
    report.extend(
        [
            "",
            "## Decision",
            "",
            "This is a cheap first-pass privacy signal, not the final paper protocol. "
            "A publishable result still needs shadow models, multiple target families, "
            "attack-trace membership splits, and calibration against temporal distribution shift.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(payload["gate_decision"], indent=2))


if __name__ == "__main__":
    main()
