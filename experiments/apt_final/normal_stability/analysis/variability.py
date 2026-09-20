"""Describe crossed encoder/bank ranges without changing the frozen experiment."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
import math
from pathlib import Path
from statistics import fmean


STATUS = "POSTHOC_DESCRIPTIVE_NO_THRESHOLD_CHANGES"
FIELDS = ("dataset", "fold", "strategy", "representation", "condition")
PHASE_METRICS = {
    "normal": ("false_positive_rate",),
    "attack": ("recall", "false_positive_rate", "f1"),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _axis(values, name):
    values = list(values)
    if not values or len(set(values)) != len(values):
        raise ValueError(f"Empty or duplicated configuration axis: {name}")
    return values


def _rate(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 <= value <= 1):
        raise ValueError("Metrics must be finite rates between zero and one")
    return float(value)


def _spread(values):
    return {"mean": fmean(values), "minimum": min(values), "maximum": max(values),
            "range": max(values) - min(values)}


def summarize(result, config):
    """Require the full crossed grid and describe each factor conditionally.

    The two mean ranges are not an additive variance decomposition. Encoder
    ranges hold the bank seed fixed; bank ranges hold the encoder seed fixed.
    Folds, strategies, representations and conditions are never mixed inside
    an individual range. Local-feature encoder copies are checked then excluded
    from case counts and bank-range averaging.
    """
    if result.get("status") != "COMPLETE_FIXED_FAMILY_DEVELOPMENT":
        raise ValueError("A complete fixed-family result is required")
    axes = [
        _axis(config["datasets"], "datasets"),
        _axis([fold["name"] for fold in config["folds"]], "folds"),
        _axis(config["strategies"], "strategies"),
        _axis(config["representations"], "representations"),
        _axis(config["conditions"], "conditions"),
    ]
    encoders = _axis(config["encoder_seeds"], "encoder_seeds")
    banks = _axis(config["bank_seeds"], "bank_seeds")
    expected = set(product(*axes, encoders, banks))
    groups, summaries = [], []
    phase_counts = {}
    for phase, metrics in PHASE_METRICS.items():
        lookup = {}
        for record in result[phase + "_records"]:
            index = tuple(record[name] for name in FIELDS) + (record["encoder_seed"], record["bank_seed"])
            if index in lookup:
                raise ValueError("Duplicate experiment identity")
            lookup[index] = record
        if set(lookup) != expected:
            raise ValueError("Result does not contain exactly the configured crossed grid")
        unique_cases = 0
        for fixed in product(*axes):
            local = fixed[3] == "local_knn"
            reference_encoder = encoders[0]
            for bank in banks:
                original = lookup[fixed + (reference_encoder, bank)]
                for encoder in encoders:
                    record = lookup[fixed + (encoder, bank)]
                    expected_duplicate = reference_encoder if local and encoder != reference_encoder else None
                    if record.get("duplicate_of_encoder_seed") != expected_duplicate:
                        raise ValueError("Incorrect local-feature duplicate marker")
                    if local and record["metrics"] != original["metrics"]:
                        raise ValueError("Local-feature encoder copy has changed metrics")
            effective_encoders = [reference_encoder] if local else encoders
            group_unique = len(effective_encoders) * len(banks)
            unique_cases += group_unique
            for metric in metrics:
                values = {(e, b): _rate(lookup[fixed + (e, b)]["metrics"][metric])
                          for e in encoders for b in banks}
                encoder_ranges = [
                    {"bank_seed": b, **_spread([values[e, b] for e in encoders])}
                    for b in banks
                ]
                bank_ranges = [
                    {"encoder_seed": e, **_spread([values[e, b] for b in banks])}
                    for e in effective_encoders
                ]
                unique_values = [values[e, b] for e in effective_encoders for b in banks]
                groups.append({
                    "phase": phase, **dict(zip(FIELDS, fixed)), "metric": metric,
                    "encoder_seeds": encoders, "bank_seeds": banks,
                    "effective_encoder_seeds": effective_encoders,
                    "encoder_variation_structurally_absent": local,
                    "raw_cases": len(encoders) * len(banks), "unique_cases": group_unique,
                    "duplicate_local_copies_excluded": len(encoders) * len(banks) - group_unique,
                    "metric_summary": _spread(unique_values),
                    "encoder_ranges_at_fixed_bank": encoder_ranges,
                    "bank_ranges_at_fixed_encoder": bank_ranges,
                    "mean_encoder_range": fmean(r["range"] for r in encoder_ranges),
                    "mean_bank_range": fmean(r["range"] for r in bank_ranges),
                })
        phase_counts[phase] = {"raw_records": len(lookup), "unique_records": unique_cases,
                               "duplicate_local_copies_excluded": len(lookup) - unique_cases}

    summary_fields = ("phase", "dataset", "strategy", "representation", "condition", "metric")
    grouped = {}
    for group in groups:
        grouped.setdefault(tuple(group[f] for f in summary_fields), []).append(group)
    for key, selected in sorted(grouped.items()):
        summaries.append({
            **dict(zip(summary_fields, key)),
            "folds": [r["fold"] for r in selected],
            "unique_cases": sum(r["unique_cases"] for r in selected),
            "duplicate_local_copies_excluded": sum(r["duplicate_local_copies_excluded"] for r in selected),
            "mean_encoder_range": fmean(r["mean_encoder_range"] for r in selected),
            "mean_bank_range": fmean(r["mean_bank_range"] for r in selected),
            "largest_fixed_bank_encoder_range": max(v["range"] for r in selected for v in r["encoder_ranges_at_fixed_bank"]),
            "largest_fixed_encoder_bank_range": max(v["range"] for r in selected for v in r["bank_ranges_at_fixed_encoder"]),
            "equal_fold_metric_mean": fmean(r["metric_summary"]["mean"] for r in selected),
            "metric_minimum": min(r["metric_summary"]["minimum"] for r in selected),
            "metric_maximum": max(r["metric_summary"]["maximum"] for r in selected),
        })
    return {
        "status": STATUS,
        "scope": "DESCRIPTIVE_FIXED_DEVELOPMENT_FAMILY",
        "units": "Rates and ranges are proportions; multiply by 100 for percentage points.",
        "methods": {
            "encoder": "Within each fixed fold/strategy/representation/condition/bank, maximum minus minimum over encoder seeds; then equal mean over banks and folds.",
            "bank": "Within each fixed fold/strategy/representation/condition/encoder, maximum minus minimum over bank seeds; then equal mean over distinct encoders and folds.",
            "local_features": "Copies must match exactly across encoder seeds. Encoder range is zero by construction; bank ranges and case counts use one encoder copy.",
        },
        "interpretation_limits": [
            "Ranges describe this crossed seed grid; they are not causal variance fractions and cannot be added to partition total variation.",
            "An encoder-seed association includes all training randomness controlled by that seed, not an isolated architecture effect.",
            "A bank-seed association includes sampled reference rows and, for pooled reference banks, their seeded clean/masked view assignments.",
            "Folds overlap, and attack metrics reuse the same exposed test graph; seed and fold repeats are not independent attack campaigns.",
            "Normal FPR measures held-out normal graph alerts. Attack FPR uses benchmark-negative entities, not independently verified benign labels.",
            "Zero observed range does not establish robustness beyond the tested settings. No tests, p-values, thresholds, selections or retraining are introduced.",
        ],
        "phase_counts": phase_counts, "conditional_groups": groups, "fold_summaries": summaries,
        "thresholds_changed": False, "models_refit": False,
        "independent_campaign_inference": False, "causal_attribution": False,
    }


def markdown(summary):
    lines = ["# Encoder and reference-bank variability", "", f"Status: `{summary['status']}`.", "",
             "Each cell shows **encoder range / bank range**, in percentage points. A range compares seeds while the other seed, fold, strategy and condition are fixed; the table averages these ranges equally over the fixed settings and folds.", "",
             "These are descriptive seed associations, not causes or percentages of explained variation. The two ranges are not additive. Folds overlap and attack results reuse exposed test data, so these repeats are not independent campaigns.", "",
             "Local-feature encoder range is zero by construction. Its duplicate encoder copies are excluded from bank summaries and case counts. Bank seed also controls view assignment when the reference mixes clean and masked views.", "",
             "| Dataset | Strategy | Representation | Condition | Unique cases per phase | Normal FPR | Attack FPR | Attack recall | Attack F1 |",
             "|---|---|---|---|---:|---:|---:|---:|---:|"]
    fixed_fields = ("dataset", "strategy", "representation", "condition")
    rows = {}
    for row in summary["fold_summaries"]:
        rows.setdefault(tuple(row[f] for f in fixed_fields), {})[(row["phase"], row["metric"])] = row
    ordered_metrics = (("normal", "false_positive_rate"), ("attack", "false_positive_rate"),
                       ("attack", "recall"), ("attack", "f1"))
    for fixed, values in sorted(rows.items()):
        cells = [f"{100 * values[k]['mean_encoder_range']:.2f} / {100 * values[k]['mean_bank_range']:.2f}"
                 for k in ordered_metrics]
        counts = {row["unique_cases"] for row in values.values()}
        if len(counts) != 1:
            raise ValueError("Phase case counts disagree")
        lines.append("| " + " | ".join([*fixed, str(counts.pop()), *cells]) + " |")
    lines.extend(["", "Normal FPR is the alert fraction in held-out normal graphs; attack FPR uses benchmark-negative entities. Exact per-fold ranges, maxima and input hashes are in `FACTOR_VARIABILITY.json`. No model, calibration threshold or decision was changed."])
    if "provenance" in summary:
        p = summary["provenance"]
        lines.extend(["", f"Input RESULTS SHA256: `{p['results_sha256']}`.",
                      f"Input config SHA256: `{p['config_sha256']}`.",
                      f"Analysis script SHA256: `{p['script_sha256']}`."])
    return "\n".join(lines) + "\n"


def write_report(results_path, config_path, output_dir):
    results_path, config_path, output_dir = map(Path, (results_path, config_path, output_dir))
    raw_results, raw_config = results_path.read_bytes(), config_path.read_bytes()
    results, config = json.loads(raw_results), json.loads(raw_config)
    config_sha = hashlib.sha256(raw_config).hexdigest()
    if results.get("config_sha256") != config_sha:
        raise ValueError("Configuration hash does not match RESULTS")
    report = summarize(results, config)
    report["created_utc"] = datetime.now(timezone.utc).isoformat()
    report["provenance"] = {
        "results_filename": results_path.name, "results_sha256": hashlib.sha256(raw_results).hexdigest(),
        "config_filename": config_path.name, "config_sha256": config_sha,
        "script_sha256": digest(__file__), "source_commit": results.get("source_commit"),
        "registration_sha256": results.get("registration_sha256"),
        "normal_freeze_sha256": results.get("normal_freeze_sha256"),
        "validation_scope": "Binds and validates aggregate RESULTS/config only; does not re-audit private scores or source registration.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = output_dir / "FACTOR_VARIABILITY.json", output_dir / "FACTOR_VARIABILITY.md"
    if json_path.exists() or md_path.exists():
        raise FileExistsError("Variability outputs already exist; choose a new output directory")
    json_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = write_report(args.results, args.config, args.output_dir)
    print(json.dumps({"status": report["status"], "conditional_groups": len(report["conditional_groups"]),
                      "fold_summaries": len(report["fold_summaries"]), "phase_counts": report["phase_counts"]}))
