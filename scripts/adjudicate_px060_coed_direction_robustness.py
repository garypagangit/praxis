from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np


def mean(values):
    return float(np.mean(values)) if values else None


def at_least(value, threshold):
    return value is not None and np.isfinite(value) and value >= threshold


def at_most(value, threshold):
    return value is not None and np.isfinite(value) and value <= threshold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    raw = json.loads(args.results.read_text())
    rows = raw["rows"]
    expected_matrix = {
        (str(item["kind"]), int(seed), learned)
        for item in cfg["perturbations"]
        for seed in cfg["seeds"]
        for learned in (True, False)
    }
    observed_matrix = {
        (str(row["perturbation"]), int(row["seed"]), bool(row["learn_theta"]))
        for row in rows
    }
    repo_commit = subprocess.check_output(
        ["git", "-C", str(args.repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    dataset_path = args.repo / "datasets" / cfg["dataset"]
    dataset_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    def select(kind, learned):
        return [
            row for row in rows
            if row["perturbation"] == kind and row["learn_theta"] is learned
        ]

    clean_learned = select("clean", True)
    clean_fixed = select("clean", False)
    fixed_by_seed = {r["seed"]: r for r in clean_fixed}
    improvements = [
        (fixed_by_seed[r["seed"]]["test_mse"] - r["test_mse"])
        / fixed_by_seed[r["seed"]]["test_mse"]
        for r in clean_learned
    ]
    clean_by_seed = {r["seed"]: r for r in clean_learned}
    perturb_summary = {}
    for kind in ("reverse", "delete"):
        learned = select(kind, True)
        degradation = [
            (r["test_mse"] - clean_by_seed[r["seed"]]["test_mse"])
            / clean_by_seed[r["seed"]]["test_mse"]
            for r in learned
        ]
        perturb_summary[kind] = {
            "mean_test_mse": mean([r["test_mse"] for r in learned]),
            "mean_theta_spearman": mean([r["theta_spearman"] for r in learned]),
            "mean_relative_mse_degradation": mean(degradation),
            "per_seed_relative_mse_degradation": degradation,
        }

    gates = cfg["primary_gates"]
    metrics = {
        "clean_mean_learned_mse": mean([r["test_mse"] for r in clean_learned]),
        "clean_mean_fixed_mse": mean([r["test_mse"] for r in clean_fixed]),
        "clean_mean_learned_improvement": mean(improvements),
        "clean_mean_theta_spearman": mean([r["theta_spearman"] for r in clean_learned]),
        "perturbations": perturb_summary,
    }
    checks = {
        "clean_mse_improvement": at_least(
            metrics["clean_mean_learned_improvement"],
            gates["clean_learned_mse_improvement_over_fixed_min"],
        ),
        "clean_direction_recovery": at_least(
            metrics["clean_mean_theta_spearman"],
            gates["clean_theta_spearman_min"],
        ),
        "reverse_direction_recovery": at_least(
            perturb_summary["reverse"]["mean_theta_spearman"],
            gates["perturbed_theta_spearman_min"],
        ),
        "delete_direction_recovery": at_least(
            perturb_summary["delete"]["mean_theta_spearman"],
            gates["perturbed_theta_spearman_min"],
        ),
        "reverse_mse_robustness": at_most(
            perturb_summary["reverse"]["mean_relative_mse_degradation"],
            gates["perturbed_relative_mse_degradation_max"],
        ),
        "delete_mse_robustness": at_most(
            perturb_summary["delete"]["mean_relative_mse_degradation"],
            gates["perturbed_relative_mse_degradation_max"],
        ),
    }
    completeness = {
        "experiment_id_matches": raw["experiment_id"] == cfg["experiment_id"],
        "not_smoke": raw.get("smoke") is False,
        "complete_unique_condition_matrix": (
            len(rows) == len(expected_matrix)
            and len(observed_matrix) == len(expected_matrix)
            and observed_matrix == expected_matrix
        ),
        "repository_commit_matches": repo_commit == cfg["source"]["commit"],
        "dataset_sha256_matches": dataset_sha256 == cfg["dataset_sha256"],
        "learned_theta_values_finite": all(
            np.isfinite(float(row["theta_spearman"]))
            for row in rows
            if row["learn_theta"]
        ),
        "mse_values_finite": all(
            np.isfinite(float(row["test_mse"])) for row in rows
        ),
    }
    valid = all(completeness.values())
    result = {
        "experiment_id": "PX-060",
        "status": (
            "PASS" if valid and all(checks.values())
            else "FAIL" if valid
            else "INVALID_INCOMPLETE"
        ),
        "valid": valid,
        "completeness_checks": completeness,
        "repository_commit": repo_commit,
        "dataset_sha256": dataset_sha256,
        "metrics": metrics,
        "checks": checks,
        "claim_boundary": cfg["claim_boundary"],
        "rows": rows,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
