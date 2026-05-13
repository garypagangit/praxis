from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from praxis.praxis04.data_loader import load_preprocessed_split, split_to_matrices
from scripts.run_mia_apt_detector_pilot import align_proba, entropy, score_attack


def choose_indices(
    n: int, size: int, rng: np.random.Generator, exclude: set[int] | None = None
) -> np.ndarray:
    candidates = np.array(
        [idx for idx in range(n) if exclude is None or idx not in exclude], dtype=int
    )
    if len(candidates) < size:
        size = len(candidates)
    return rng.choice(candidates, size=size, replace=False)


def attack_features(probs: np.ndarray, y: np.ndarray) -> np.ndarray:
    pred = probs.argmax(axis=1)
    true_prob = probs[np.arange(len(y)), y]
    return np.column_stack(
        [
            probs.max(axis=1),
            -entropy(probs),
            true_prob,
            (pred == y).astype(float),
        ]
    )


def fit_rf(
    x: np.ndarray, y: np.ndarray, seed: int, n_estimators: int
) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=seed,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    model.fit(x, y)
    return model


def model_features(
    model: RandomForestClassifier,
    x: np.ndarray,
    y: np.ndarray,
    n_classes: int,
) -> np.ndarray:
    probs = align_proba(model.predict_proba(x), model.classes_, n_classes)
    return attack_features(probs, y)


def evaluate_attack(
    member_scores: np.ndarray, nonmember_scores: np.ndarray
) -> dict[str, float]:
    y_true = np.concatenate(
        [
            np.ones(len(member_scores), dtype=int),
            np.zeros(len(nonmember_scores), dtype=int),
        ]
    )
    scores = np.concatenate([member_scores, nonmember_scores])
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "average_precision": float(average_precision_score(y_true, scores)),
        "member_mean": float(np.mean(member_scores)),
        "nonmember_mean": float(np.mean(nonmember_scores)),
    }


def run_seed(args: argparse.Namespace, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    split = load_preprocessed_split(
        args.data_dir,
        sample_rows_per_file=args.sample_rows_per_file,
        sample_seed=seed,
        sample_strategy="uniform",
        holdout_day_pattern="02-03-2018",
        val_fraction_of_train_days=0.2,
    )
    matrices = split_to_matrices(split)
    n_classes = len(matrices.label_names)

    train_n = len(matrices.x_train)
    member_idx = choose_indices(train_n, args.member_limit, rng)
    member_set = set(member_idx.tolist())
    same_nonmember_idx = choose_indices(
        train_n, args.nonmember_limit, rng, exclude=member_set
    )
    temporal_nonmember_idx = choose_indices(
        len(matrices.x_test), args.nonmember_limit, rng
    )

    target = fit_rf(
        matrices.x_train[member_idx],
        matrices.y_train[member_idx],
        seed=seed,
        n_estimators=args.n_estimators,
    )
    target_member_feat = model_features(
        target, matrices.x_train[member_idx], matrices.y_train[member_idx], n_classes
    )
    target_same_feat = model_features(
        target,
        matrices.x_train[same_nonmember_idx],
        matrices.y_train[same_nonmember_idx],
        n_classes,
    )
    target_temporal_feat = model_features(
        target,
        matrices.x_test[temporal_nonmember_idx],
        matrices.y_test[temporal_nonmember_idx],
        n_classes,
    )

    shadow_x: list[np.ndarray] = []
    shadow_y: list[np.ndarray] = []
    for shadow_id in range(args.shadow_models):
        shadow_rng = np.random.default_rng(seed * 1000 + shadow_id)
        shadow_member_idx = choose_indices(
            train_n, args.shadow_member_limit, shadow_rng
        )
        shadow_member_set = set(shadow_member_idx.tolist())
        shadow_nonmember_idx = choose_indices(
            train_n,
            args.shadow_member_limit,
            shadow_rng,
            exclude=shadow_member_set,
        )
        shadow = fit_rf(
            matrices.x_train[shadow_member_idx],
            matrices.y_train[shadow_member_idx],
            seed=seed * 1000 + shadow_id,
            n_estimators=args.shadow_estimators,
        )
        member_feat = model_features(
            shadow,
            matrices.x_train[shadow_member_idx],
            matrices.y_train[shadow_member_idx],
            n_classes,
        )
        nonmember_feat = model_features(
            shadow,
            matrices.x_train[shadow_nonmember_idx],
            matrices.y_train[shadow_nonmember_idx],
            n_classes,
        )
        shadow_x.append(np.vstack([member_feat, nonmember_feat]))
        shadow_y.append(
            np.concatenate(
                [
                    np.ones(len(member_feat), dtype=int),
                    np.zeros(len(nonmember_feat), dtype=int),
                ]
            )
        )

    attack_train_x = np.vstack(shadow_x)
    attack_train_y = np.concatenate(shadow_y)
    attack_model = LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=seed
    )
    attack_model.fit(attack_train_x, attack_train_y)

    member_attack_score = attack_model.predict_proba(target_member_feat)[:, 1]
    same_attack_score = attack_model.predict_proba(target_same_feat)[:, 1]
    temporal_attack_score = attack_model.predict_proba(target_temporal_feat)[:, 1]

    direct_names = [
        "max_confidence",
        "negative_entropy",
        "true_class_probability",
        "correctness",
    ]
    direct_same = {
        name: score_attack(target_member_feat[:, idx], target_same_feat[:, idx])
        for idx, name in enumerate(direct_names)
    }
    direct_temporal = {
        name: score_attack(target_member_feat[:, idx], target_temporal_feat[:, idx])
        for idx, name in enumerate(direct_names)
    }

    return {
        "seed": seed,
        "member_rows": int(len(member_idx)),
        "same_distribution_nonmember_rows": int(len(same_nonmember_idx)),
        "temporal_nonmember_rows": int(len(temporal_nonmember_idx)),
        "shadow_attack_same_distribution": evaluate_attack(
            member_attack_score, same_attack_score
        ),
        "shadow_attack_temporal": evaluate_attack(
            member_attack_score, temporal_attack_score
        ),
        "best_direct_same_distribution": max(
            direct_same.items(), key=lambda item: item[1]["roc_auc"]
        ),
        "best_direct_temporal": max(
            direct_temporal.items(), key=lambda item: item[1]["roc_auc"]
        ),
        "all_direct_same_distribution": direct_same,
        "all_direct_temporal": direct_temporal,
    }


def normalize_best(row: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    name, metrics = row
    return {"score": name, **metrics}


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Membership Inference Shadow Protocol",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## Aggregate Results",
        "",
        "| Evaluation | ROC-AUC mean | AP mean | Interpretation |",
        "|---|---:|---:|---|",
    ]
    for row in summary["aggregate"]:
        lines.append(
            f"| `{row['evaluation']}` | `{row['roc_auc_mean']:.4f}` | `{row['average_precision_mean']:.4f}` | {row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Per-Seed Shadow Attack",
            "",
            "| Seed | Same-dist ROC-AUC | Temporal ROC-AUC | Same member mean | Same nonmember mean |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["seeds"]:
        same = row["shadow_attack_same_distribution"]
        temporal = row["shadow_attack_temporal"]
        lines.append(
            f"| `{row['seed']}` | `{same['roc_auc']:.4f}` | `{temporal['roc_auc']:.4f}` | `{same['member_mean']:.4f}` | `{same['nonmember_mean']:.4f}` |"
        )
    lines.extend(["", "## Recommendation", "", summary["recommendation"]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/cic-ids-2018")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "mia-shadow-protocol-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "membership_inference_apt_detectors"
        / "SHADOW_PROTOCOL_20260509.md",
    )
    parser.add_argument("--seeds", default="13,29,43")
    parser.add_argument("--sample-rows-per-file", type=int, default=1000)
    parser.add_argument("--member-limit", type=int, default=2500)
    parser.add_argument("--nonmember-limit", type=int, default=2500)
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--shadow-models", type=int, default=4)
    parser.add_argument("--shadow-member-limit", type=int, default=1500)
    parser.add_argument("--shadow-estimators", type=int, default=80)
    args = parser.parse_args()

    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    seed_rows = []
    for seed in seeds:
        print(f"Running MIA shadow protocol seed {seed}...")
        row = run_seed(args, seed)
        row["best_direct_same_distribution"] = normalize_best(
            row["best_direct_same_distribution"]
        )
        row["best_direct_temporal"] = normalize_best(row["best_direct_temporal"])
        seed_rows.append(row)

    aggregate = []
    for key, label, interpretation in [
        (
            "shadow_attack_same_distribution",
            "shadow attack / same-distribution nonmembers",
            "Controls ordinary day-shift; strongest privacy test here.",
        ),
        (
            "shadow_attack_temporal",
            "shadow attack / temporal nonmembers",
            "Includes temporal shift; useful but confounded.",
        ),
        (
            "best_direct_same_distribution",
            "best direct score / same-distribution nonmembers",
            "No shadow training; useful sanity check.",
        ),
        (
            "best_direct_temporal",
            "best direct score / temporal nonmembers",
            "Comparable to the earlier smoke setup.",
        ),
    ]:
        aggregate.append(
            {
                "evaluation": label,
                "roc_auc_mean": float(
                    np.mean([row[key]["roc_auc"] for row in seed_rows])
                ),
                "average_precision_mean": float(
                    np.mean([row[key]["average_precision"] for row in seed_rows])
                ),
                "interpretation": interpretation,
            }
        )

    same_auc = next(
        row["roc_auc_mean"]
        for row in aggregate
        if row["evaluation"] == "shadow attack / same-distribution nonmembers"
    )
    decision = (
        "CONTINUE - SAME-DISTRIBUTION PRIVACY SIGNAL"
        if same_auc >= 0.60
        else "WEAKENED - TEMPORAL SHIFT EXPLAINS MOST SIGNAL"
    )
    summary = {
        "decision": decision,
        "seeds": seed_rows,
        "aggregate": aggregate,
        "recommendation": (
            "Promote to a backup Praxis only after repeating on Unraveled or a neural target detector."
            if same_auc >= 0.60
            else "Keep as a documented diagnostic; do not promote unless a same-distribution signal appears on a stronger detector family."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    pd.DataFrame(aggregate).to_csv(args.out_dir / "aggregate.csv", index=False)
    render_report(args.report, summary)
    print(json.dumps({"decision": decision, "aggregate": aggregate}, indent=2))


if __name__ == "__main__":
    main()
