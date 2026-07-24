from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


def safe_spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 3 or np.std(left) == 0 or np.std(right) == 0:
        return 0.0
    value = spearmanr(left, right).statistic
    return 0.0 if not np.isfinite(value) else float(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    raw = json.loads(args.results.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary = raw["summary"]
    methods = list(config["explanations"]["methods"])
    seeds = [int(seed) for seed in config["model"]["seeds"]]
    holdouts = list(config["dataset"]["holdout_patterns"])

    expected_seed_reference = len(methods) * len(seeds)
    # Raw results intentionally include the reference-validation domain in
    # addition to the five outcome-bearing holdouts.
    expected_domains = len(methods) * len(seeds) * (len(holdouts) + 1)
    eligible = [int(seed) for seed in summary["accuracy_matched_seeds"]]
    replay_values = [
        float(row["identical_replay_rank_spearman"])
        for row in raw["seed_reference"]
    ]

    completeness = {
        "archive_size_matches_historical_release": (
            int(manifest["archive_size_bytes"]) == 235_102_953
        ),
        "archive_sha256_matches_pinned_mirror": (
            manifest["archive_sha256"]
            == "c3f26274b36c837ccf28ffd2dbf4582941c30b3ee70a635c6e5b2f87c4727928"
        ),
        "eight_csv_files": len(manifest["files"]) == 8,
        "all_seed_method_references": (
            len(raw["seed_reference"]) == expected_seed_reference
        ),
        "all_seed_method_holdouts": len(raw["domains"]) == expected_domains,
        "at_least_two_accuracy_matched_seeds": len(eligible) >= 2,
        "deterministic_replay": bool(replay_values)
        and min(replay_values) >= 0.99,
        "label_shuffle_control_present": any(
            row.get("control") == "label_shuffle" for row in raw["controls"]
        ),
    }

    method_checks = {}
    corrected_method_metrics = {}
    for method in methods:
        runner_metrics = summary["methods"][method]
        method_rows = [
            row for row in raw["domains"]
            if row["method"] == method and row["domain"] in holdouts
        ]
        holdout_aggregates = []
        for holdout in holdouts:
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
                "seed_repetitions": len(repeated),
            })
        drift_failure_spearman = safe_spearman(
            [row["explanation_drift"] for row in holdout_aggregates],
            [row["balanced_error"] for row in holdout_aggregates],
        )
        corrected_method_metrics[method] = {
            "mean_top_k_seed_stability": runner_metrics[
                "mean_top_k_seed_stability"
            ],
            "mean_rank_seed_stability": runner_metrics[
                "mean_rank_seed_stability"
            ],
            "drift_failure_spearman": drift_failure_spearman,
            "confidence_drift_failure_spearman": safe_spearman(
                [row["confidence_drift"] for row in holdout_aggregates],
                [row["balanced_error"] for row in holdout_aggregates],
            ),
            "feature_drift_failure_spearman": safe_spearman(
                [row["feature_mean_drift"] for row in holdout_aggregates],
                [row["balanced_error"] for row in holdout_aggregates],
            ),
            "n_independent_holdouts": len(holdout_aggregates),
            "accuracy_matched_seeds": runner_metrics[
                "accuracy_matched_seeds"
            ],
            "holdout_aggregates": holdout_aggregates,
        }
        method_checks[method] = {
            "five_independent_holdouts": (
                len(holdout_aggregates) == len(holdouts)
                and all(
                    row["seed_repetitions"] == len(seeds)
                    for row in holdout_aggregates
                )
            ),
            "accuracy_subset_matches_summary": (
                [int(seed) for seed in runner_metrics["accuracy_matched_seeds"]]
                == eligible
            ),
            "H1_seed_stability": (
                float(runner_metrics["mean_top_k_seed_stability"])
                >= float(config["gates"]["minimum_mean_stability"])
            ),
            "H2_drift_warning": (
                drift_failure_spearman
                >= float(config["gates"]["minimum_drift_failure_spearman"])
            ),
        }

    h1_consensus = all(
        checks["H1_seed_stability"] for checks in method_checks.values()
    )
    h2_consensus = all(
        checks["H2_drift_warning"] for checks in method_checks.values()
    )
    valid = all(completeness.values()) and all(
        checks["five_independent_holdouts"]
        and checks["accuracy_subset_matches_summary"]
        for checks in method_checks.values()
    )
    if not valid:
        status = "INVALID_INCOMPLETE"
    elif h1_consensus and h2_consensus:
        status = "PASS_METHOD_CONSENSUS"
    else:
        status = "FAIL_METHOD_CONSENSUS"

    result = {
        "experiment_id": "PX-058",
        "stage": "gate2_confirmatory_corrected",
        "status": status,
        "valid": valid,
        "H1_method_consensus": h1_consensus,
        "H2_method_consensus": h2_consensus,
        "accuracy_matched_seeds": eligible,
        "completeness_checks": completeness,
        "method_checks": method_checks,
        "method_metrics": corrected_method_metrics,
        "dataset_provenance": {
            "distribution": manifest["distribution"],
            "publisher_page": manifest["publisher_page"],
            "retrieval_url": manifest["retrieval_url"],
            "archive_size_bytes": manifest["archive_size_bytes"],
            "archive_sha256": manifest["archive_sha256"],
            "archive_md5": manifest["archive_md5"],
        },
        "claim_boundary": (
            "H1 concerns top-k global-feature stability among accuracy-matched "
            "random-forest seeds. H2 concerns association across five CICIDS2017 "
            "holdouts after aggregating repeated seeds. Neither establishes "
            "causal explanation correctness, human usefulness, transportability, "
            "or H3 incremental warning."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
