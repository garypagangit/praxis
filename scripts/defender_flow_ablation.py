"""Re-evaluate the SOC XGBoost model after removing selected flow features."""

import argparse
import itertools
import json
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
from sklearn.metrics import f1_score

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded
import defender_sequence_tuning as sequence


VARIANTS = {
    "baseline": (),
    "without_reject": ("flow_reject",),
    "without_other_protocol": ("flow_other_protocol",),
    "without_both": ("flow_reject", "flow_other_protocol"),
}


def paired_interval(labels, groups, sessions, baseline, changed):
    humans = [s for s in sessions if labels[groups == s][0] == 0]
    ai = [s for s in sessions if labels[groups == s][0] == 1]
    rng = np.random.default_rng(42)
    scores = []
    for _ in range(2000):
        chosen = list(rng.choice(humans, len(humans), replace=True))
        chosen += list(rng.choice(ai, len(ai), replace=True))
        indices = np.concatenate([np.flatnonzero(groups == s) for s in chosen])
        old = f1_score(labels[indices], baseline[indices], average="macro", zero_division=0)
        new = f1_score(labels[indices], changed[indices], average="macro", zero_division=0)
        scores.append(new - old)
    return [float(x) for x in np.percentile(scores, [2.5, 97.5])]


def run(experiment, output):
    experiment = experiment.resolve()
    output = expanded.safe_output(output, experiment, experiment)
    own_hash = base.sha256(Path(__file__).resolve())
    sequence_hash = base.sha256(Path(sequence.__file__).resolve())
    _, groups, labels, sessions, baseline, provenance = sequence.prepare(experiment)
    data = expanded.aggregate(base.rows(experiment / "windows30.csv"), 30)
    true_ai = tuple(s for s in sessions if labels[groups == s][0] == 1)
    assignments = list(itertools.combinations(sessions, 4))
    results = {}
    predictions = {}
    for variant, removed in VARIANTS.items():
        columns = tuple(c for c in sequence.BASE_COLUMNS if c not in removed)
        observed, predicted, probabilities = expanded.model_score(data, columns, true_ai, "xgboost", False)
        if variant == "baseline":
            if predicted.tolist() != baseline["predictions"] or abs(observed - baseline["macro_f1"]) > 1e-12:
                raise ValueError("Prior baseline predictions do not match")
        entry = sequence.summarize(labels, groups, sessions, probabilities)
        permutation_scores = [expanded.model_score(data, columns, a, "xgboost", False)[0]
                              for a in assignments]
        if abs(permutation_scores[assignments.index(true_ai)] - observed) > 1e-12:
            raise ValueError("True permutation differs from observed score")
        entry["permutation_p"] = sum(x >= observed - 1e-12 for x in permutation_scores) / len(assignments)
        entry["permutations"] = len(assignments)
        entry["removed_features"] = list(removed)
        entry["predictions"] = predicted.tolist()
        predictions[variant] = predicted
        results[variant] = entry
        print(f"{variant}: F1 {observed:.3f}, raw p {entry['permutation_p']:.4f}", flush=True)
    for variant, p in zip(VARIANTS, base.holm([results[v]["permutation_p"] for v in VARIANTS])):
        results[variant]["holm_p"] = p
        results[variant]["delta_macro_f1"] = results[variant]["macro_f1"] - results["baseline"]["macro_f1"]
        results[variant]["paired_interval"] = paired_interval(
            labels, groups, sessions, predictions["baseline"], predictions[variant]
        )
    if (base.sha256(Path(__file__).resolve()) != own_hash
            or base.sha256(Path(sequence.__file__).resolve()) != sequence_hash):
        raise ValueError("Ablation or helper code changed during evaluation")
    output.mkdir(parents=True)
    result = {"exploratory": True, "script_sha256": own_hash, "sequence_sha256": sequence_hash, "provenance": provenance,
              "results": results, "windows": len(data), "sessions": len(sessions)}
    (output / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# SOC flow feature ablation", "",
             "**Exploratory; no independent or benign-traffic evaluation.**",
             f"{len(data)} common 30-second windows from {len(sessions)} sessions.",
             "", "| Variant | Macro-F1 | Change vs baseline | Paired session interval | AI recall | Human attack FPR | Session accuracy | Raw p | Holm p |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for variant, e in results.items():
        low, high = e["paired_interval"]
        lines.append(f"| {variant} | {e['macro_f1']:.3f} | {e['delta_macro_f1']:+.3f} | "
                     f"{low:+.3f} to {high:+.3f} | {e['ai_recall']:.3f} | "
                     f"{e['human_attack_window_fpr']:.3f} | {e['session_accuracy']:.3f} | "
                     f"{e['permutation_p']:.4f} | {e['holm_p']:.4f} |")
    lines += ["", "Each method refits for all 126 session-label assignments. Holm correction covers "
              "these four exploratory tests only; p-values assess label association, not the "
              "difference from baseline. Paired intervals resample fixed predictions by session "
              "without refitting and do not account for earlier selection.",
              "Removing columns does not remove all related information: for example, non-TCP/UDP "
              "flow count can be reconstructed from total, TCP and UDP counts."]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved results to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.experiment, args.output)
