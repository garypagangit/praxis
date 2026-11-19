"""Explore 30-second SOC activity sequences with nested session-held-out tuning."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
import os
from pathlib import Path
import sys

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded


BASE_COLUMNS = base.FEATURES["combined"] + expanded.EXTRA_FEATURES + expanded.BEHAVIOR_FEATURES
SEQUENCE_COLUMNS = tuple(
    f"next_bin_{first}_to_{second}"
    for first in expanded.BIN_CHANNELS for second in expanded.BIN_CHANNELS
)
# Fixed before evaluating this follow-on. Ties favor the earlier candidate.
CANDIDATES = (
    ("enhanced_depth3", False, 3),
    ("sequence_depth3", True, 3),
    ("sequence_depth2", True, 2),
    ("sequence_depth4", True, 4),
)


def sequence_features(row):
    active = {
        channel: [int(row[f"bin_{channel}_{i}"]) > 0 for i in range(6)]
        for channel in expanded.BIN_CHANNELS
    }
    return {
        f"next_bin_{first}_to_{second}": sum(
            active[first][i] and active[second][i + 1] for i in range(5)
        )
        for first in expanded.BIN_CHANNELS for second in expanded.BIN_CHANNELS
    }


def prepare(experiment):
    manifest_path = experiment / "extraction.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    phase_path = experiment / "behavior.json"
    phase = json.loads(phase_path.read_text(encoding="utf-8"))
    source = experiment / "windows30.csv"
    if (manifest["script_sha256"] != base.sha256(Path(expanded.__file__).resolve())
            or manifest["original_script_sha256"] != base.sha256(Path(base.__file__).resolve())
            or manifest["windows30_sha256"] != base.sha256(source)
            or phase["script_sha256"] != manifest["script_sha256"]
            or phase["features"] != list(BASE_COLUMNS) or phase["smote"]):
        raise ValueError("Original experiment code, features or results changed")
    raw = base.rows(source)
    original = {(row["session"], row["window"]): row for row in raw}
    if len(original) != len(raw):
        raise ValueError("Duplicate windows")
    data = expanded.aggregate(raw, 30)
    for row in data:
        row.update(sequence_features(original[(row["session"], row["window"])]))
    groups = np.array([row["session"] for row in data])
    labels = np.array([int(row["label"] == "ai") for row in data])
    sessions = sorted(set(groups))
    if len(sessions) != 9 or any(len(set(labels[groups == s])) != 1 for s in sessions):
        raise ValueError("Expected nine consistently labeled sessions")
    if sum(labels[groups == s][0] for s in sessions) != 4:
        raise ValueError("Expected four AI and five human sessions")
    X = np.log1p(np.array([[float(row[c]) for c in BASE_COLUMNS + SEQUENCE_COLUMNS]
                           for row in data], dtype=float))
    if not np.isfinite(X).all():
        raise ValueError("Non-finite features")
    saved = phase["results"]["30"]
    if saved["labels"] != labels.tolist() or saved["windows"] != len(data):
        raise ValueError("Baseline result does not match the candidate windows")
    return X, groups, labels, sessions, saved, {
        "extraction_sha256": base.sha256(manifest_path),
        "baseline_sha256": base.sha256(phase_path),
        "windows30_sha256": manifest["windows30_sha256"],
        "base_script_sha256": manifest["original_script_sha256"],
        "expanded_script_sha256": manifest["script_sha256"],
    }


def fit_predict(X, groups, labels, train, test, candidate):
    if set(groups[train]) & set(groups[test]):
        raise ValueError("Training and validation sessions overlap")
    train_groups = groups[train]
    train_y = labels[train]
    weights = np.zeros(len(train_y), dtype=float)
    for cls in (0, 1):
        members = sorted(set(train_groups[train_y == cls]))
        if not members:
            raise ValueError("Training fold is missing a class")
        for session in members:
            mask = train_groups == session
            weights[mask] = 0.5 / len(members) / mask.sum()
    weights *= len(weights) / weights.sum()
    columns = len(BASE_COLUMNS) + (len(SEQUENCE_COLUMNS) if candidate[1] else 0)
    scaler = StandardScaler().fit(X[train, :columns])
    model = XGBClassifier(n_estimators=80, max_depth=candidate[2], learning_rate=0.1,
                          subsample=1, colsample_bytree=1, n_jobs=1,
                          random_state=42, eval_metric="logloss")
    model.fit(scaler.transform(X[train, :columns]), train_y, sample_weight=weights)
    return model.predict_proba(scaler.transform(X[test, :columns]))[:, 1]


def nested_predictions(X, groups, labels, sessions):
    fixed = np.zeros(len(labels))
    tuned = np.zeros(len(labels))
    selected = {}
    for outer in sessions:
        outer_train = groups != outer
        outer_test = groups == outer
        scores = []
        for candidate in CANDIDATES:
            inner_predictions = np.zeros(len(labels), dtype=int)
            for inner in sessions:
                if inner == outer:
                    continue
                train = outer_train & (groups != inner)
                test = outer_train & (groups == inner)
                p = fit_predict(X, groups, labels, train, test, candidate)
                inner_predictions[test] = p >= 0.5
            scores.append(float(f1_score(labels[outer_train], inner_predictions[outer_train],
                                         average="macro", zero_division=0)))
        chosen = int(np.argmax(scores))
        tuned[outer_test] = fit_predict(X, groups, labels, outer_train, outer_test, CANDIDATES[chosen])
        if chosen == 1:
            fixed[outer_test] = tuned[outer_test]
        else:
            fixed[outer_test] = fit_predict(X, groups, labels, outer_train, outer_test, CANDIDATES[1])
        selected[outer] = {"candidate": CANDIDATES[chosen][0], "inner_macro_f1": scores}
    return fixed, tuned, selected


_DATA = None


def initialize_worker(X, groups, sessions):
    global _DATA
    _DATA = X, groups, sessions


def run_assignment(assignment):
    X, groups, sessions = _DATA
    labels = np.isin(groups, assignment).astype(int)
    fixed, tuned, selected = nested_predictions(X, groups, labels, sessions)
    return {
        "assignment": list(assignment),
        "fixed_score": float(f1_score(labels, fixed >= 0.5, average="macro", zero_division=0)),
        "nested_score": float(f1_score(labels, tuned >= 0.5, average="macro", zero_division=0)),
        "fixed_probabilities": fixed.tolist(), "nested_probabilities": tuned.tolist(),
        "selected": selected,
    }


def summarize(labels, groups, sessions, probabilities):
    predictions = probabilities >= 0.5
    calls = {s: int(probabilities[groups == s].mean() >= 0.5) for s in sessions}
    session_labels = {s: int(labels[groups == s][0]) for s in sessions}
    counts = {}
    for s in sessions:
        mask = groups == s
        counts[s] = np.array([
            np.sum((labels[mask] == 1) & predictions[mask]),
            np.sum((labels[mask] == 0) & predictions[mask]),
            np.sum((labels[mask] == 1) & ~predictions[mask]),
            np.sum((labels[mask] == 0) & ~predictions[mask]),
        ])
    humans = [s for s in sessions if not session_labels[s]]
    ai = [s for s in sessions if session_labels[s]]
    rng = np.random.default_rng(42)
    bootstrap = []
    for _ in range(2000):
        chosen = list(rng.choice(humans, len(humans), replace=True))
        chosen += list(rng.choice(ai, len(ai), replace=True))
        tp, fp, fn, tn = np.sum([counts[s] for s in chosen], axis=0)
        f_ai = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
        f_human = 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 0
        bootstrap.append((f_ai + f_human) / 2)
    return {
        "macro_f1": float(f1_score(labels, predictions, average="macro", zero_division=0)),
        "ai_recall": float(np.mean(predictions[labels == 1])),
        "human_attack_window_fpr": float(np.mean(predictions[labels == 0])),
        "session_accuracy": sum(calls[s] == session_labels[s] for s in sessions) / len(sessions),
        "bootstrap_interval": [float(x) for x in np.percentile(bootstrap, [2.5, 97.5])],
        "session_calls": calls,
    }


def run(experiment, output, workers):
    experiment = experiment.resolve()
    output = expanded.safe_output(output, experiment, experiment)
    if workers < 1:
        raise ValueError("Workers must be positive")
    script_hash = base.sha256(Path(__file__).resolve())
    X, groups, labels, sessions, baseline, provenance = prepare(experiment)
    assignment = tuple(s for s in sessions if labels[groups == s][0] == 1)
    baseline_score, baseline_predictions, _ = expanded.model_score(
        expanded.aggregate(base.rows(experiment / "windows30.csv"), 30),
        BASE_COLUMNS, assignment, "xgboost", False,
    )
    if (baseline_predictions.tolist() != baseline["predictions"]
            or abs(baseline_score - baseline["macro_f1"]) > 1e-12):
        raise ValueError("Original 30-second baseline did not reproduce")
    assignments = list(itertools.combinations(sessions, 4))
    assignments.remove(assignment)
    assignments.insert(0, assignment)
    output.mkdir(parents=True)
    metadata = {
        **provenance, "script_sha256": script_hash, "candidates": CANDIDATES,
        "base_columns": list(BASE_COLUMNS), "sequence_columns": list(SEQUENCE_COLUMNS),
        "session_count": 9, "windows": len(labels), "permutations": len(assignments),
    }
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    completed = []
    with (output / "permutations.jsonl").open("x", encoding="utf-8") as stream:
        with ProcessPoolExecutor(max_workers=workers, initializer=initialize_worker,
                                 initargs=(X, groups, sessions)) as pool:
            for result in pool.map(run_assignment, assignments):
                completed.append(result)
                stream.write(json.dumps(result, separators=(",", ":")) + "\n")
                stream.flush()
                count = len(completed)
                if count == 1:
                    print(f"Observed fixed-sequence F1 {result['fixed_score']:.3f}; "
                          f"nested-tuned F1 {result['nested_score']:.3f}", flush=True)
                if count % 10 == 0 or count == len(assignments):
                    print(f"Completed {count}/{len(assignments)} full nested permutations", flush=True)
    if base.sha256(Path(__file__).resolve()) != script_hash:
        raise ValueError("Experiment code changed during evaluation")
    observed = completed[0]
    results = {}
    for name in ("fixed", "nested"):
        probabilities = np.array(observed[f"{name}_probabilities"])
        entry = summarize(labels, groups, sessions, probabilities)
        key = f"{name}_score"
        if abs(entry["macro_f1"] - observed[key]) > 1e-12:
            raise ValueError("Observed predictions and permutation score differ")
        entry["permutation_p"] = sum(x[key] >= observed[key] - 1e-12 for x in completed) / len(completed)
        results[name] = entry
    for name, p in zip(("fixed", "nested"), base.holm([results["fixed"]["permutation_p"],
                                                      results["nested"]["permutation_p"]])):
        results[name]["holm_p"] = p
    result = {"exploratory": True, "baseline_macro_f1": baseline["macro_f1"],
              "selected_by_outer_fold": observed["selected"], "results": results,
              "permutations": len(completed), "provenance": metadata}
    (output / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# SOC sequence and nested-tuning results", "",
        "**Exploratory; no independent external validation or benign-traffic evaluation.**",
        f"Nine sessions; {len(labels)} retained 30-second windows. Baseline XGBoost macro-F1: {baseline['macro_f1']:.3f}.",
        "", "| Model | Macro-F1 | 95% session interval | AI recall | Human attack FPR | Session accuracy | Raw p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("fixed", "nested"):
        e = results[name]
        low, high = e["bootstrap_interval"]
        lines.append(f"| {name} | {e['macro_f1']:.3f} | {low:.3f}-{high:.3f} | "
                     f"{e['ai_recall']:.3f} | {e['human_attack_window_fpr']:.3f} | "
                     f"{e['session_accuracy']:.3f} | {e['permutation_p']:.4f} | {e['holm_p']:.4f} |")
    lines += [
        "", "Fixed = sequence features with depth 3; nested = four-candidate feature/depth selection "
        "inside each outer training fold. Both use 126 whole-session permutations; nested selection "
        "is rerun for every permutation. Holm correction covers these two exploratory analyses only.",
        "The bootstrap resamples sessions using fixed out-of-fold predictions, not refits or selection.",
        "Five-second channel transitions are coarse bin-level associations; flow bins use record end "
        "times and do not establish event ordering or real-time availability.",
        "Known attack boundaries, collection gaps, prior experimentation, session dependence and "
        "possible environment confounding limit interpretation. These p-values do not establish "
        "independent confirmation or prove an improvement over the earlier baseline.", "",
    ]
    (output / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved results to {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    run(args.experiment, args.output, args.workers)


if __name__ == "__main__":
    main()
