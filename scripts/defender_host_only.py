"""Re-evaluate defender host logs without requiring network-flow coverage."""

import argparse
import csv
import itertools
import json
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded
import defender_sequence_tuning as sequence
import defender_flow_ablation as ablation


HOST_COLUMNS = (
    base.FEATURES["security"] + base.FEATURES["sysmon"] + expanded.EXTRA_FEATURES
    + tuple(f"{channel}_{feature}" for channel in ("security", "sysmon", "extra")
            for feature in ("active_fraction", "peak_fraction", "variation"))
    + ("security_sysmon_coactive", "windows_extra_coactive")
)
COMPARE_COLUMNS = (
    base.FEATURES["security"] + base.FEATURES["sysmon"] + expanded.EXTRA_FEATURES
    + tuple(f"bin_{channel}_{i}" for channel in ("security", "sysmon", "extra") for i in range(6))
)


def check_previous(row, previous):
    if row["label"] != previous["label"]:
        raise ValueError("Host and prior window labels differ")
    for column in COMPARE_COLUMNS:
        if int(row[column]) != int(previous[column]):
            raise ValueError(f"Host feature differs from previous extraction: {column}")


def extract(source, experiment, output):
    source, experiment = source.resolve(), experiment.resolve()
    output = expanded.safe_output(output, source, experiment)
    own_hash = base.sha256(Path(__file__).resolve())
    _, _, _, _, _, provenance = sequence.prepare(experiment)
    prior = base.rows(experiment / "windows30.csv")
    previous = {(r["session"], r["window"]): r for r in prior}
    if len(previous) != len(prior):
        raise ValueError("Duplicate prior feature windows")
    expanded_manifest = json.loads((experiment / "extraction.json").read_text(encoding="utf-8"))
    inp = base.FrozenInputs(source)
    if inp.freeze_hash != expanded_manifest["freeze1_sha256"]:
        raise ValueError("Study freeze does not match previous extraction")
    by_session = base.make_windows(inp)
    required = {f"{host}/{channel}" for host in base.HOSTS for channel in ("security", "sysmon")}
    retained = []
    coverage = {}
    found = set()
    for participant, windows in by_session.items():
        session, label = windows[0]["session"], windows[0]["label"]
        for w in windows:
            w["extra"] = {name: 0 for name in expanded.EXTRA_FEATURES + expanded.BIN_COLUMNS}
        for host in base.HOSTS:
            for channel in ("security", "sysmon"):
                path = inp.get(f"set_aside/{participant}/{host}/{channel}.jsonl.gz")
                base.windows_stream(path, windows, host, channel)
                expanded.timing_stream(path, windows, channel)
        for stream_name, kind in expanded.EXTRA.items():
            path = inp.get(f"set_aside/{participant}/{stream_name}.jsonl.gz")
            expanded.timing_stream(path, windows, "extra", extra_channel=kind)
        eligible = [w for w in windows if required <= w["covered"]]
        if not eligible:
            raise ValueError("A session has no eligible host windows")
        for w in eligible:
            row = {"session": session, "label": label, "window": w["window"],
                   **w["values"], **w["extra"]}
            key = (session, w["window"])
            if key in previous:
                check_previous(row, previous[key])
                found.add(key)
            retained.append(row)
        coverage[session] = {"class": label, "candidate_windows": len(windows),
                             "eligible_host_windows": len(eligible),
                             "outside_host_extents": len(windows) - len(eligible)}
        print(f"Processed host logs for {session}", flush=True)
    if found != set(previous):
        raise ValueError("Some prior common-coverage windows were not recovered")
    if base.sha256(Path(__file__).resolve()) != own_hash:
        raise ValueError("Host-only code changed during extraction")
    aggregates = expanded.aggregate(retained, 30)
    output.mkdir(parents=True)
    path = output / "host_features.csv"
    columns = ["session", "label", "window"] + list(HOST_COLUMNS)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(aggregates)
    manifest = {
        "version": 1, "script_sha256": own_hash, "freeze1_sha256": inp.freeze_hash,
        "provenance": provenance, "inputs_sha256": inp.verified,
        "host_features_sha256": base.sha256(path), "host_columns": HOST_COLUMNS,
        "coverage_by_session": coverage, "total_candidate_windows": sum(x["candidate_windows"] for x in coverage.values()),
        "host_eligible_windows": len(aggregates), "matched_windows": len(found),
    }
    (output / "extraction.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Extracted {len(aggregates)} host-covered windows; {len(found)} match prior sample.", flush=True)


def evaluate(experiment, output):
    experiment, output = experiment.resolve(), output.resolve()
    result_path = output / "results.json"
    if result_path.exists() or (output / "RESULTS.md").exists():
        raise ValueError("Refusing to overwrite host-only results")
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    path = output / "host_features.csv"
    _, _, _, _, saved, provenance = sequence.prepare(experiment)
    if (manifest["script_sha256"] != base.sha256(Path(__file__).resolve())
            or manifest["host_features_sha256"] != base.sha256(path)
            or manifest["host_columns"] != list(HOST_COLUMNS)
            or manifest["provenance"] != provenance):
        raise ValueError("Host input, code or prior experiment changed")
    data_all = base.rows(path)
    prior = base.rows(experiment / "windows30.csv")
    keys = {(r["session"], r["window"]) for r in prior}
    data_matched = [r for r in data_all if (r["session"], r["window"]) in keys]
    if len(data_matched) != len(keys) or len(data_all) != manifest["host_eligible_windows"]:
        raise ValueError("Unexpected host dataset size")
    sessions = sorted({r["session"] for r in data_all})
    if len(sessions) != 9:
        raise ValueError("Expected nine sessions")
    classes = {s: next(r["label"] for r in data_all if r["session"] == s) for s in sessions}
    if any(r["label"] != classes[r["session"]] for r in data_all):
        raise ValueError("Inconsistent session labels")
    true_ai = tuple(s for s in sessions if classes[s] == "ai")
    if len(true_ai) != 4:
        raise ValueError("Expected four AI sessions")
    assignments = list(itertools.combinations(sessions, 4))
    results = {}
    for name, data in (("matched", data_matched), ("all_host_covered", data_all)):
        groups = np.array([r["session"] for r in data])
        labels = np.array([int(r["label"] == "ai") for r in data])
        if set(groups) != set(sessions):
            raise ValueError(f"Missing sessions in {name}")
        observed, predicted, probabilities = expanded.model_score(data, HOST_COLUMNS, true_ai, "xgboost", False)
        result = sequence.summarize(labels, groups, sessions, probabilities)
        chance = [expanded.model_score(data, HOST_COLUMNS, a, "xgboost", False)[0]
                  for a in assignments]
        if abs(chance[assignments.index(true_ai)] - observed) > 1e-12:
            raise ValueError("True permutation differs from observed score")
        result["permutation_p"] = sum(x >= observed - 1e-12 for x in chance) / len(chance)
        result["permutations"] = len(chance)
        result["windows"] = len(data)
        result["windows_by_class"] = {label: sum(r["label"] == label for r in data)
                                      for label in ("human", "ai")}
        result["predictions"] = predicted.tolist()
        if name == "matched":
            if labels.tolist() != saved["labels"]:
                raise ValueError("Matched windows are not aligned with baseline predictions")
            old = np.array(saved["predictions"])
            result["delta_from_combined_baseline"] = observed - saved["macro_f1"]
            result["paired_interval"] = ablation.paired_interval(labels, groups, sessions, old, predicted)
        results[name] = result
        print(f"{name}: {len(data)} windows, F1 {observed:.3f}, raw p {result['permutation_p']:.4f}", flush=True)
    for name, p in zip(results, base.holm([e["permutation_p"] for e in results.values()])):
        results[name]["holm_p"] = p
    if base.sha256(Path(__file__).resolve()) != manifest["script_sha256"]:
        raise ValueError("Host-only code changed during evaluation")
    result_path.write_text(json.dumps({"exploratory": True, "results": results, "provenance": provenance},
                                      indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# SOC host-only telemetry results", "",
             "**Exploratory; no benign-traffic evaluation or independent validation.**",
             "| Sample | Windows (human / AI) | Macro-F1 | 95% session interval | AI recall | Human attack FPR | Session accuracy | Raw p | Holm p |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, r in results.items():
        lo, hi = r["bootstrap_interval"]
        counts = r["windows_by_class"]
        lines.append(f"| {name} | {r['windows']} ({counts['human']} / {counts['ai']}) | "
                     f"{r['macro_f1']:.3f} | {lo:.3f}-{hi:.3f} | {r['ai_recall']:.3f} | "
                     f"{r['human_attack_window_fpr']:.3f} | {r['session_accuracy']:.3f} | "
                     f"{r['permutation_p']:.4f} | {r['holm_p']:.4f} |")
    e = results["matched"]
    lo, hi = e["paired_interval"]
    lines += ["", f"Matched host-only minus combined baseline macro-F1: {e['delta_from_combined_baseline']:+.3f} "
              f"(paired fixed-prediction session interval {lo:+.3f} to {hi:+.3f}).",
              "The larger host-covered sample is not a matched comparison with the combined model.",
              "Host features include common Security, Sysmon and additional event channels and their "
              "five-second activity; no network-flow features or command content are used.",
              "The first/last timestamp extent is only a coarse coverage proxy; additional sparse "
              "channels may be incomplete. Each method uses 126 session-label permutations. Holm "
              "correction covers only these two exploratory tests, not earlier analyses.",
              "Intervals resample fixed predictions by session; p-values assess label association, "
              "not the difference from baseline. Known attack periods and small, potentially "
              "confounded sessions limit generalization. Human FPR is for attacks, not benign traffic.", ""]
    (output / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved host-only results to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--experiment", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("evaluate")
    p.add_argument("--experiment", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "extract":
        extract(args.source, args.experiment, args.output)
    else:
        evaluate(args.experiment, args.output)
