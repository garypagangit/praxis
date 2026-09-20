"""Post-hoc description of frozen clean-graph predictions; never fits or retunes.

Usage:
  python diagnose_failure.py --outputs-root /collected/outputs \
    --audit /INDEPENDENT_RESULT_AUDIT.json --output /POSTHOC_DIAGNOSTIC.json

This script examines annotated malicious entities, not independent attacks or
campaigns. Exact ties describe saved numeric scores; their causal explanation
is not established by this analysis.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def score_distribution(values):
    values = np.asarray(values)
    if values.ndim != 1 or len(values) == 0 or not np.all(np.isfinite(values)):
        raise ValueError("score distribution requires nonempty finite one-dimensional values")
    distinct, counts = np.unique(values, return_counts=True)
    index = int(np.argmax(counts))
    quantiles = [0.0, 0.25, 0.5, 0.9, 0.95, 0.99, 1.0]
    return {
        "n_entities": len(values),
        "n_distinct_saved_scores": len(distinct),
        "largest_exact_tie_count": int(counts[index]),
        "largest_exact_tie_fraction": float(counts[index] / len(values)),
        "largest_exact_tie_score": float(distinct[index]),
        "largest_tie_definition": "exact equality at saved NumPy dtype precision; no rounding",
        "quantiles": {str(q): float(v) for q, v in zip(quantiles, np.quantile(values, quantiles))},
    }


def diagnose(outputs_root, audit_path, output_path):
    outputs_root, audit_path, output_path = map(Path, (outputs_root, audit_path, output_path))
    if output_path.exists():
        raise FileExistsError("diagnostic output already exists; preserve prior evidence")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS_SAVED_EVIDENCE_AUDIT":
        raise ValueError("independent saved-evidence audit has not passed")
    records, inputs = [], []
    for dataset in ("cadets", "theia"):
        audit_matches = [item for item in audit["datasets"] if item["dataset"] == dataset]
        if len(audit_matches) != 1:
            raise ValueError("dataset missing or duplicated in independent audit")
        dataset_audit = audit_matches[0]
        result_path = outputs_root / dataset / "RESULTS.json"
        result_hash = sha256(result_path)
        if result_hash != dataset_audit["results_sha256"]:
            raise ValueError(f"{dataset}: RESULTS.json changed since independent audit")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") != "COMPLETE_DEVELOPMENT_ONLY":
            raise ValueError("source result is incomplete or outside development scope")
        inputs.append({"relative_path": f"{dataset}/RESULTS.json", "sha256": result_hash})
        clean_records = [item for item in result["records"] if item["drop_rate"] == 0]
        seeds = [item["seed"] for item in clean_records]
        if len(seeds) != len(set(seeds)) or not seeds:
            raise ValueError("clean scenario must occur exactly once per seed")
        for clean in clean_records:
            seed = clean["seed"]
            prediction_name = f"predictions_{seed}_clean.npz"
            prediction_path = outputs_root / dataset / "private" / prediction_name
            prediction_hash = sha256(prediction_path)
            if prediction_hash != result["private_artifact_sha256"][prediction_name]:
                raise ValueError(f"{dataset}/{prediction_name}: frozen prediction hash mismatch")
            inputs.append({"relative_path": f"{dataset}/private/{prediction_name}", "sha256": prediction_hash})
            with np.load(prediction_path, allow_pickle=False) as saved:
                y = saved["y"]
                if y.ndim != 1 or set(np.unique(y)) != {0, 1}:
                    raise ValueError("binary annotation vector must contain both labels")
                malicious, benign = y == 1, y == 0
                mlp = saved["margin_mlp"] >= 0
                gin = saved["margin_gin"] >= 0
                if mlp.shape != y.shape or gin.shape != y.shape:
                    raise ValueError("predictions and annotations are not aligned")
                union = mlp | gin
                mlp_tp = int(np.sum(malicious & mlp))
                gin_tp = int(np.sum(malicious & gin))
                if mlp_tp != clean["metrics"]["mlp"]["tp"] or gin_tp != clean["metrics"]["gin"]["tp"]:
                    raise ValueError("saved true-positive counts disagree with audited metrics")
                n_malicious = int(malicious.sum())
                distributions = {}
                for arm in ("mlp", "gin", "isolation_forest", "type_rarity"):
                    scores = saved[f"score_{arm}"]
                    if scores.shape != y.shape:
                        raise ValueError("scores and annotations are not aligned")
                    distributions[arm] = {
                        "annotated_malicious_entities": score_distribution(scores[malicious]),
                        "annotated_benign_entities": score_distribution(scores[benign]),
                    }
                records.append({
                    "dataset": dataset, "seed": seed, "scenario": "clean",
                    "n_entities": len(y), "n_annotated_malicious_entities": n_malicious,
                    "annotated_malicious_prevalence": float(malicious.mean()),
                    "frozen_mlp_true_positive_entities": mlp_tp,
                    "frozen_gin_true_positive_entities": gin_tp,
                    "frozen_mlp_gin_union_true_positive_entities": int(np.sum(malicious & union)),
                    "union_recall_upper_bound_for_fixed_binary_selector": float(np.sum(malicious & union) / n_malicious),
                    "mlp_additional_true_positive_entities_over_gin": int(np.sum(malicious & mlp & ~gin)),
                    "gin_additional_true_positive_entities_over_mlp": int(np.sum(malicious & gin & ~mlp)),
                    "shared_true_positive_entities": int(np.sum(malicious & mlp & gin)),
                    "malicious_entities_missed_by_both": int(np.sum(malicious & ~union)),
                    "all_entity_prediction_disagreements": int(np.sum(mlp != gin)),
                    "score_distributions": distributions,
                })
    report = {
        "status": "POSTHOC_EXPLORATORY_NO_THRESHOLD_CHANGES",
        "scope": "DEVELOPMENT_ONLY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_script_sha256": sha256(__file__),
        "numpy_version": np.__version__,
        "input_independent_audit_sha256": sha256(audit_path),
        "source_registration_sha256": audit["registration_sha256"],
        "source_commit": audit["source_commit"],
        "input_files": inputs,
        "selection": "All three frozen seeds for each dataset, clean graph only, selected after seeing the pilot results.",
        "model_fitting_performed": False,
        "threshold_changes_performed": False,
        "frozen_results_modified": False,
        "prediction_rule": "Reuse each saved calibrated margin >= 0; no rescoring or threshold optimization.",
        "interpretation_limits": [
            "Union recall bounds selection between these fixed binary decisions only; it does not bound retrained detectors or new scores.",
            "Exact score ties and distributions describe a possible representation/scoring limitation, not an established causal mechanism.",
            "Counts concern annotated malicious entities, not independent attacks or campaigns.",
            "Benign score quantiles use test annotations post hoc for diagnosis only; no thresholds are selected from them.",
            "This diagnostic does not establish dataset failure, general impossibility of routing, or positive deployment performance."
        ],
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-root", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = diagnose(args.outputs_root, args.audit, args.output)
    print(json.dumps({"status": report["status"], "records": len(report["records"]),
                      "output": str(Path(args.output).resolve())}))


if __name__ == "__main__":
    main()
