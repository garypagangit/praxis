#!/usr/bin/env python
"""Run PX-058 explanation-stability and explanation-drift gates."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import balanced_accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split


def top_k_set(importances: np.ndarray, names: list[str], k: int) -> set[str]:
    order = np.argsort(-np.abs(importances), kind="stable")[: min(k, len(names))]
    return {names[int(index)] for index in order}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return 1.0 if not union else len(left & right) / len(union)


def rank_spearman(left: np.ndarray, right: np.ndarray) -> float:
    value = spearmanr(np.abs(left), np.abs(right)).statistic
    return 0.0 if not np.isfinite(value) else float(value)


def mean_pairwise_jaccard(feature_sets: list[set[str]]) -> float:
    pairs = list(itertools.combinations(feature_sets, 2))
    return 1.0 if not pairs else float(np.mean([jaccard(a, b) for a, b in pairs]))


def safe_spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 3 or np.std(left) == 0 or np.std(right) == 0:
        return 0.0
    value = spearmanr(left, right).statistic
    return 0.0 if not np.isfinite(value) else float(value)


def fixed_binary_neg_log_loss(estimator, x: np.ndarray, y: np.ndarray) -> float:
    """Score a binary sample even when its sampled y contains one class."""
    probabilities = estimator.predict_proba(x)
    return -float(log_loss(y, probabilities, labels=[0, 1]))


def synthetic_domains(dataset: dict, seed: int = 20260724):
    x, y = make_classification(
        n_samples=int(dataset["n_samples"]),
        n_features=int(dataset["n_features"]),
        n_informative=5,
        n_redundant=2,
        class_sep=1.2,
        shuffle=False,
        random_state=seed,
    )
    names = [f"feature_{index:02d}" for index in range(x.shape[1])]
    train_x, base_x, train_y, base_y = train_test_split(
        x, y, test_size=0.35, stratify=y, random_state=seed
    )
    domains = []
    for strength in dataset["shift_strengths"]:
        shifted = base_x.copy()
        # Increasingly corrupt two informative coordinates. This fixture checks
        # metric direction only; it is never outcome-bearing evidence.
        rng = np.random.default_rng(seed + int(float(strength) * 100))
        shifted[:, :2] += rng.normal(0, float(strength) * 2.0, shifted[:, :2].shape)
        domains.append((f"shift_{float(strength):.1f}", shifted, base_y))
    return train_x, train_y, names, domains


def load_cic_dataset(dataset: dict):
    from praxis.praxis04.data_loader import load_cicids2018_csvs

    frame = load_cicids2018_csvs(
        dataset["data_dir"],
        sample_rows_per_file=int(dataset["rows_per_file"]),
        chunksize=int(dataset.get("chunksize", 200_000)),
        sample_seed=20260724,
        sample_strategy="uniform",
    )
    holdout_patterns = dataset["holdout_patterns"]
    holdout_masks = {
        pattern: frame["source_file"].astype(str).str.contains(pattern, regex=False)
        for pattern in holdout_patterns
    }
    train_mask = ~np.logical_or.reduce(list(holdout_masks.values()))
    train = frame.loc[train_mask].copy()
    feature_columns = list(frame.attrs["load_summary"]["feature_columns"])
    nonconstant = train[feature_columns].nunique(dropna=False) > 1
    feature_columns = list(np.asarray(feature_columns)[nonconstant.to_numpy()])
    train_x = train[feature_columns].to_numpy(dtype=np.float64)
    train_y = (train["attack_label"].astype(str).str.lower() != "benign").astype(int).to_numpy()
    if len(np.unique(train_y)) < 2:
        raise ValueError("Training split contains only one binary class")
    fit_x, reference_x, fit_y, reference_y = train_test_split(
        train_x,
        train_y,
        test_size=float(dataset.get("reference_fraction", 0.2)),
        stratify=train_y,
        random_state=20260724,
    )
    prepared = [("reference_validation", reference_x, reference_y)]
    for name, mask in holdout_masks.items():
        domain = frame.loc[mask]
        if domain.empty:
            raise ValueError(f"No rows matched holdout pattern {name}")
        y = (domain["attack_label"].astype(str).str.lower() != "benign").astype(int).to_numpy()
        if len(np.unique(y)) < 2:
            raise ValueError(f"Holdout {name} contains only one binary class after uniform sampling")
        prepared.append((name, domain[feature_columns].to_numpy(dtype=np.float64), y))
    return fit_x, fit_y, feature_columns, prepared


def explain(
    method: str,
    model,
    train_x: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    config: dict,
    seed: int,
) -> np.ndarray:
    limit = min(len(x), int(config["max_explanation_rows"]))
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(x), size=limit, replace=False)
    sample_x, sample_y = x[chosen], y[chosen]
    if method == "permutation":
        scoring = config.get("permutation_scoring", "neg_log_loss")
        if scoring == "neg_log_loss":
            scoring = fixed_binary_neg_log_loss
        result = permutation_importance(
            model,
            sample_x,
            sample_y,
            scoring=scoring,
            n_repeats=int(config["n_repeats"]),
            random_state=seed,
            n_jobs=1,
        )
        return result.importances_mean
    if method == "tree_shap":
        import shap

        values = shap.TreeExplainer(model).shap_values(sample_x)
        if isinstance(values, list):
            values = values[-1]
        values = np.asarray(values)
        if values.ndim == 3:
            values = values[..., -1]
        return np.mean(np.abs(values), axis=0)
    if method == "lime":
        from lime.lime_tabular import LimeTabularExplainer

        background_limit = min(len(train_x), 5000)
        background_idx = rng.choice(len(train_x), size=background_limit, replace=False)
        explainer = LimeTabularExplainer(
            train_x[background_idx],
            mode="classification",
            discretize_continuous=False,
            random_state=seed,
        )
        lime_limit = min(len(sample_x), int(config.get("lime_rows", 50)))
        totals = np.zeros(train_x.shape[1], dtype=np.float64)
        for row in sample_x[:lime_limit]:
            explanation = explainer.explain_instance(
                row,
                model.predict_proba,
                labels=(1,),
                num_features=train_x.shape[1],
                num_samples=int(config.get("lime_num_samples", 1500)),
            )
            for feature_index, weight in explanation.as_map().get(1, []):
                totals[int(feature_index)] += abs(float(weight))
        return totals / max(lime_limit, 1)
    raise ValueError(f"Unsupported explanation method: {method}")


def feature_mean_drift(reference_x: np.ndarray, current_x: np.ndarray) -> float:
    scale = np.std(reference_x, axis=0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    standardized = np.abs(np.mean(current_x, axis=0) - np.mean(reference_x, axis=0)) / scale
    finite = standardized[np.isfinite(standardized)]
    return 0.0 if len(finite) == 0 else float(np.mean(finite))


def run(config: dict) -> dict:
    if config["dataset"]["kind"] == "synthetic_fixture":
        train_x, train_y, names, domains = synthetic_domains(config["dataset"])
    elif config["dataset"]["kind"] in {"cicids2018_dev", "cicids2017_confirmatory"}:
        train_x, train_y, names, domains = load_cic_dataset(config["dataset"])
    else:
        raise ValueError(f"Unsupported dataset kind: {config['dataset']['kind']}")

    seed_rows, domain_rows, control_rows = [], [], []
    methods = config["explanations"].get(
        "methods", [config["explanations"].get("method", "permutation")]
    )
    reference_importances = {method: {} for method in methods}
    reference_sets = {method: {} for method in methods}
    top_k = int(config["explanations"]["top_k"])
    for seed in config["model"]["seeds"]:
        model = RandomForestClassifier(
            n_estimators=int(config["model"]["n_estimators"]),
            max_depth=int(config["model"]["max_depth"]),
            random_state=int(seed),
            n_jobs=int(config["model"]["n_jobs"]),
            class_weight="balanced_subsample",
        )
        model.fit(train_x, train_y)
        reference_name, reference_x, reference_y = domains[0]
        reference_predictions = model.predict(reference_x)
        reference_balanced_accuracy = float(
            balanced_accuracy_score(reference_y, reference_predictions)
        )
        if (
            config["model"].get("run_label_shuffle_control", True)
            and int(seed) == int(config["model"]["seeds"][0])
        ):
            shuffle_rng = np.random.default_rng(int(seed) + 10_000)
            shuffled_y = shuffle_rng.permutation(train_y)
            shuffled_model = RandomForestClassifier(
                n_estimators=int(config["model"]["n_estimators"]),
                max_depth=int(config["model"]["max_depth"]),
                random_state=int(seed) + 10_000,
                n_jobs=int(config["model"]["n_jobs"]),
                class_weight="balanced_subsample",
            )
            shuffled_model.fit(train_x, shuffled_y)
            control_rows.append({
                "control": "label_shuffle",
                "seed": int(seed),
                "reference_balanced_accuracy": float(
                    balanced_accuracy_score(
                        reference_y, shuffled_model.predict(reference_x)
                    )
                ),
            })
        reference_probabilities = model.predict_proba(reference_x)[:, 1]
        for method in methods:
            ref_attr = explain(
                method, model, train_x, reference_x, reference_y,
                config["explanations"], int(seed)
            )
            replay_attr = explain(
                method, model, train_x, reference_x, reference_y,
                config["explanations"], int(seed)
            )
            ref_set = top_k_set(ref_attr, names, top_k)
            reference_importances[method][int(seed)] = ref_attr
            reference_sets[method][int(seed)] = ref_set
            seed_rows.append({
                "seed": int(seed),
                "method": method,
                "reference_domain": reference_name,
                "reference_balanced_accuracy": reference_balanced_accuracy,
                "top_features": sorted(ref_set),
                "identical_replay_rank_spearman": rank_spearman(ref_attr, replay_attr),
            })
            for domain_name, domain_x, domain_y in domains:
                predictions = model.predict(domain_x)
                probabilities = model.predict_proba(domain_x)[:, 1]
                attr = explain(
                    method, model, train_x, domain_x, domain_y,
                    config["explanations"], int(seed)
                )
                current_set = top_k_set(attr, names, top_k)
                balanced_accuracy = balanced_accuracy_score(domain_y, predictions)
                try:
                    auroc = roc_auc_score(domain_y, probabilities)
                except ValueError:
                    auroc = None
                domain_rows.append({
                    "seed": int(seed),
                    "method": method,
                    "domain": domain_name,
                    "n": int(len(domain_y)),
                    "positive_rate": float(np.mean(domain_y)),
                    "balanced_accuracy": float(balanced_accuracy),
                    "balanced_error": float(1.0 - balanced_accuracy),
                    "auroc": None if auroc is None else float(auroc),
                    "explanation_drift": float(1.0 - jaccard(ref_set, current_set)),
                    "rank_spearman_to_reference": rank_spearman(ref_attr, attr),
                    "confidence_drift": float(
                        abs(np.mean(probabilities) - np.mean(reference_probabilities))
                    ),
                    "feature_mean_drift": feature_mean_drift(reference_x, domain_x),
                    "top_features": sorted(current_set),
                })

    method_summaries = {}
    seed_accuracy = {
        int(row["seed"]): float(row["reference_balanced_accuracy"])
        for row in seed_rows
    }
    best_reference_accuracy = max(seed_accuracy.values())
    accuracy_tolerance = float(config["model"].get("accuracy_match_tolerance", 0.02))
    eligible_seeds = sorted(
        seed for seed, score in seed_accuracy.items()
        if best_reference_accuracy - score <= accuracy_tolerance
    )
    for method in methods:
        method_rows = [row for row in domain_rows if row["method"] == method]
        eligible_importances = [
            reference_importances[method][seed] for seed in eligible_seeds
        ]
        eligible_sets = [
            reference_sets[method][seed] for seed in eligible_seeds
        ]
        pairwise_rank = [
            rank_spearman(a, b)
            for a, b in itertools.combinations(eligible_importances, 2)
        ]
        holdout_names = sorted({row["domain"] for row in method_rows})
        holdout_aggregates = []
        for holdout in holdout_names:
            repeated = [row for row in method_rows if row["domain"] == holdout]
            holdout_aggregates.append({
                "domain": holdout,
                "balanced_error": float(np.mean(
                    [row["balanced_error"] for row in repeated]
                )),
                "explanation_drift": float(np.mean(
                    [row["explanation_drift"] for row in repeated]
                )),
                "confidence_drift": float(np.mean(
                    [row["confidence_drift"] for row in repeated]
                )),
                "feature_mean_drift": float(np.mean(
                    [row["feature_mean_drift"] for row in repeated]
                )),
            })
        errors = [row["balanced_error"] for row in holdout_aggregates]
        drifts = [row["explanation_drift"] for row in holdout_aggregates]
        method_summaries[method] = {
            "mean_top_k_seed_stability": mean_pairwise_jaccard(eligible_sets),
            "mean_rank_seed_stability": float(np.mean(pairwise_rank)) if pairwise_rank else 1.0,
            "drift_failure_spearman": safe_spearman(drifts, errors),
            "confidence_drift_failure_spearman": safe_spearman(
                [row["confidence_drift"] for row in holdout_aggregates], errors
            ),
            "feature_drift_failure_spearman": safe_spearman(
                [row["feature_mean_drift"] for row in holdout_aggregates], errors
            ),
            "n_seed_domain_observations": len(method_rows),
            "n_independent_holdouts": len(holdout_aggregates),
            "accuracy_matched_seeds": eligible_seeds,
            "holdout_aggregates": holdout_aggregates,
        }
    summary = {
        "experiment_id": config["experiment_id"],
        "stage": config["stage"],
        "dataset_kind": config["dataset"]["kind"],
        "accuracy_match_tolerance": accuracy_tolerance,
        "best_reference_balanced_accuracy": best_reference_accuracy,
        "accuracy_matched_seeds": eligible_seeds,
        "methods": method_summaries,
    }
    summary["gate_checks"] = {
        method: {
            "stability": values["mean_top_k_seed_stability"]
            >= float(config["gates"]["minimum_mean_stability"]),
            "drift_warning": values["drift_failure_spearman"]
            >= float(config["gates"]["minimum_drift_failure_spearman"]),
        }
        for method, values in method_summaries.items()
    }
    return {
        "summary": summary,
        "controls": control_rows,
        "seed_reference": seed_rows,
        "domains": domain_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = run(config)
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame(result["domains"]).to_csv(output_dir / "domain_metrics.csv", index=False)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
