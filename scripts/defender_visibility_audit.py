"""Compare process-free and flow-only telemetry and outside-login flow controls."""

import argparse
from collections import Counter
import csv
import gzip
import itertools
import json
import math
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded
import defender_sequence_tuning as sequence
import defender_flow_ablation as ablation
import defender_flow_investigation as investigation


PROCESS_IDS = {"security": 4688, "sysmon": 1}
PROCESS_COLUMNS = ("security_4688", "sysmon_1")
PROCESS_FREE_COLUMNS = tuple(c for c in sequence.BASE_COLUMNS if c not in PROCESS_COLUMNS)
FLOW_COLUMNS = base.FEATURES["flow"] + tuple(
    f"flow_{name}" for name in ("active_fraction", "peak_fraction", "variation")
)


def subtract_process_events(row, channel, counts):
    column = f"{channel}_{PROCESS_IDS[channel]}"
    if len(counts) != 6 or any(n < 0 for n in counts):
        raise ValueError("Invalid process-event bin counts")
    if sum(counts) != int(row[column]):
        raise ValueError(f"Process-event count differs from prior {column}")
    updated = dict(row)
    updated[column] = 0
    for i, count in enumerate(counts):
        key = f"bin_{channel}_{i}"
        remainder = int(row[key]) - count
        if remainder < 0:
            raise ValueError(f"Process count exceeds original {key}")
        updated[key] = remainder
    return updated


def process_bins(path, windows, channel):
    starts = [w["start"] for w in windows]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            moment = float(record["timestamp"]) / 1000
            if not math.isfinite(moment):
                raise ValueError("Non-finite Windows event timestamp")
            window = base.locate(windows, starts, moment)
            if window is None:
                continue
            match = base.EVENT_ID.search(record["message"])
            if not match:
                raise ValueError("Cannot parse in-window Windows EventID")
            if int(match.group(1)) == PROCESS_IDS[channel]:
                index = int((moment - window["start"]) // 5)
                window["process_bins"][channel][index] += 1


def source_hashes():
    return {Path(module.__file__).name: base.sha256(Path(module.__file__).resolve())
            for module in (base, expanded, sequence, ablation, investigation)}


def extract(source, experiment, prior_investigation, output):
    source, experiment, prior_investigation = (
        source.resolve(), experiment.resolve(), prior_investigation.resolve()
    )
    output = expanded.safe_output(output, source, experiment)
    if prior_investigation == output or output in prior_investigation.parents:
        raise ValueError("Output must not contain prior investigation")
    code = source_hashes()
    own_hash = base.sha256(Path(__file__).resolve())
    _, _, _, _, _, provenance = sequence.prepare(experiment)
    manifest = json.loads((experiment / "extraction.json").read_text(encoding="utf-8"))
    previous_path = prior_investigation / "investigation.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    if previous["script_sha256"] != code[Path(investigation.__file__).name]:
        raise ValueError("Prior investigation code changed")
    inp = base.FrozenInputs(source)
    if inp.freeze_hash != manifest["freeze1_sha256"] or inp.freeze_hash != previous["freeze1_sha256"]:
        raise ValueError("Source freeze differs from prior experiments")
    original_rows = base.rows(experiment / "windows30.csv")
    original = {(r["session"], r["window"]): r for r in original_rows}
    if len(original) != len(original_rows):
        raise ValueError("Duplicate prior feature windows")
    included = {r["login_key"] for r in base.rows(inp.get("data/labels/logins.csv"))
                if r["included"] == "1"}
    changed_rows, context_rows = [], []
    found = set()
    coverage = {}
    for participant, candidates in base.make_windows(inp).items():
        windows = [w for w in candidates if (w["session"], w["window"]) in original]
        if not windows:
            raise ValueError("A session has no previous windows")
        session, label = windows[0]["session"], windows[0]["label"]
        for w in windows:
            w["process_bins"] = {channel: [0] * 6 for channel in PROCESS_IDS}
        for host in base.HOSTS:
            for channel in PROCESS_IDS:
                rel = f"set_aside/{participant}/{host}/{channel}.jsonl.gz"
                process_bins(inp.get(rel), windows, channel)
        for w in windows:
            key = (session, w["window"])
            row = original[key]
            if row["label"] != label:
                raise ValueError("Prior label differs")
            for channel in PROCESS_IDS:
                row = subtract_process_events(row, channel, w["process_bins"][channel])
            changed_rows.append(row)
            found.add(key)

        first, last = investigation.login_extent(inp, participant, included)
        context = investigation.context_windows(session, label, first, last)
        for w in context:
            w["extra"] = {name: 0 for name in expanded.EXTRA_FEATURES + expanded.BIN_COLUMNS}
        path = inp.get(f"set_aside/{participant}/vpc-flow/eni-all.jsonl.gz")
        base.flow_stream(path, context)
        expanded.timing_stream(path, context, "flow", flow=True)
        eligible = [w for w in context if "flow" in w["covered"] and not w["skipped_flow"]]
        counts = {}
        for phase in ("before", "after"):
            group = [w for w in eligible if w["phase"] == phase]
            actual = {
                "windows": len(group),
                "records": sum(w["values"]["flow_records"] for w in group),
                "rejected": sum(w["values"]["flow_reject"] for w in group),
                "other_protocol": sum(w["values"]["flow_other_protocol"] for w in group),
            }
            old = previous["sessions"][session]["periods"].get(phase, {})
            if any(actual[k] != old.get(k, 0) for k in actual):
                raise ValueError(f"Context flow counts differ from earlier investigation: {phase}")
            counts[phase] = len(group)
        for w in eligible:
            flow_total = sum(w["extra"][f"bin_flow_{i}"] for i in range(6))
            if flow_total != w["values"]["flow_records"]:
                raise ValueError("Context flow bins do not match flow counts")
            context_rows.append({"session": session, "label": label, "window": w["window"],
                                 **w["values"], **w["extra"]})
        coverage[session] = {"class": label, **counts}
        print(f"Extracted stricter and outside-login features for {session}", flush=True)
    if found != set(original):
        raise ValueError("Prior windows do not match the frozen study")
    if base.sha256(Path(__file__).resolve()) != own_hash or source_hashes() != code:
        raise ValueError("Audit code changed during extraction")
    output.mkdir(parents=True)
    paths = (output / "process_free.csv", output / "outside_login.csv")
    for path, rows, columns in (
        (paths[0], changed_rows, list(original_rows[0])),
        (paths[1], context_rows,
         ["session", "label", "window"] + list(base.FEATURES["combined"])
         + list(expanded.EXTRA_FEATURES + expanded.BIN_COLUMNS)),
    ):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    document = {
        "version": 1, "script_sha256": own_hash, "helper_sha256": code,
        "freeze1_sha256": inp.freeze_hash, "provenance": provenance,
        "prior_investigation_sha256": base.sha256(previous_path),
        "inputs_sha256": inp.verified, "coverage_by_session": coverage,
        "process_free_sha256": base.sha256(paths[0]),
        "outside_login_sha256": base.sha256(paths[1]),
    }
    (output / "extraction.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Extracted {len(changed_rows)} matched and {len(context_rows)} outside-login windows.", flush=True)


def evaluate_one(data, columns):
    groups = np.array([r["session"] for r in data])
    labels = np.array([int(r["label"] == "ai") for r in data])
    sessions = sorted(set(groups))
    if any(len(set(labels[groups == s])) != 1 for s in sessions):
        raise ValueError("Inconsistent labels within a session")
    true_ai = tuple(s for s in sessions if labels[groups == s][0] == 1)
    if min(len(true_ai), len(sessions) - len(true_ai)) < 2:
        raise ValueError("Need at least two sessions of each class")
    score, predictions, probabilities = expanded.model_score(data, columns, true_ai, "xgboost", False)
    result = sequence.summarize(labels, groups, sessions, probabilities)
    assignments = list(itertools.combinations(sessions, len(true_ai)))
    scores = [expanded.model_score(data, columns, assignment, "xgboost", False)[0]
              for assignment in assignments]
    if abs(scores[assignments.index(true_ai)] - score) > 1e-12:
        raise ValueError("Observed label assignment differs")
    result.update({
        "raw_p": sum(x >= score - 1e-12 for x in scores) / len(scores),
        "permutations": len(scores), "windows": len(data), "sessions": len(sessions),
        "class_windows": {c: sum(r["label"] == c for r in data) for c in ("human", "ai")},
        "class_sessions": {"ai": len(true_ai), "human": len(sessions) - len(true_ai)},
        "predictions": predictions.tolist(),
        "session_positive_rates": {
            s: float(np.mean(predictions[groups == s])) for s in sessions
        },
    })
    return result, labels, groups, sessions


def evaluate(experiment, output):
    experiment, output = experiment.resolve(), output.resolve()
    result_path = output / "results.json"
    if result_path.exists() or (output / "RESULTS.md").exists():
        raise ValueError("Refusing to overwrite previous results")
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    own_hash = base.sha256(Path(__file__).resolve())
    _, baseline_groups, baseline_labels, baseline_sessions, baseline, provenance = sequence.prepare(experiment)
    if (manifest["script_sha256"] != own_hash or manifest["helper_sha256"] != source_hashes()
            or manifest["provenance"] != provenance
            or manifest["process_free_sha256"] != base.sha256(output / "process_free.csv")
            or manifest["outside_login_sha256"] != base.sha256(output / "outside_login.csv")):
        raise ValueError("Experiment inputs or code changed after extraction")
    original = expanded.aggregate(base.rows(experiment / "windows30.csv"), 30)
    process_free = expanded.aggregate(base.rows(output / "process_free.csv"), 30)
    context = expanded.aggregate(base.rows(output / "outside_login.csv"), 30)
    key = lambda rows: [(r["session"], r["window"], r["label"]) for r in rows]
    if key(original) != key(process_free):
        raise ValueError("Process-free and baseline windows misaligned")
    studies = [
        ("process_free", process_free, PROCESS_FREE_COLUMNS),
        ("attack_flow_only", original, FLOW_COLUMNS),
        ("outside_before", [r for r in context if r["window"].startswith("before_")], FLOW_COLUMNS),
        ("outside_after", [r for r in context if r["window"].startswith("after_")], FLOW_COLUMNS),
        ("outside_combined", context, FLOW_COLUMNS),
    ]
    results = {}
    for name, data, columns in studies:
        result, labels, groups, sessions = evaluate_one(data, columns)
        if name in ("process_free", "attack_flow_only"):
            if (labels.tolist() != baseline_labels.tolist() or groups.tolist() != baseline_groups.tolist()
                    or sessions != baseline_sessions):
                raise ValueError("Matched baseline predictions are not aligned")
            result["delta_from_combined_baseline"] = result["macro_f1"] - baseline["macro_f1"]
            result["paired_interval"] = ablation.paired_interval(
                labels, groups, sessions, np.array(baseline["predictions"]), np.array(result["predictions"])
            )
        results[name] = result
        print(f"{name}: F1 {result['macro_f1']:.3f}, raw p {result['raw_p']:.4f}, "
              f"{result['windows']} windows in {result['sessions']} sessions", flush=True)
    for name, value in zip(results, base.holm([v["raw_p"] for v in results.values()])):
        results[name]["holm_p_five_test_family"] = value
    if base.sha256(Path(__file__).resolve()) != own_hash or source_hashes() != manifest["helper_sha256"]:
        raise ValueError("Audit code changed during evaluation")
    result_path.write_text(json.dumps({"exploratory": True, "provenance": provenance, "results": results},
                                      indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Defender visibility and outside-login audit", "",
             "**Exploratory; outside-login activity is not known to be benign.**", "",
             "| Model | Windows (human / AI) | Sessions (human / AI) | Macro-F1 | AI-labeled recall | Human-labeled positive rate | Session accuracy | Raw p | Holm p |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, r in results.items():
        w, s = r["class_windows"], r["class_sessions"]
        lines.append(f"| {name} | {w['human']} / {w['ai']} | {s['human']} / {s['ai']} | "
                     f"{r['macro_f1']:.3f} | {r['ai_recall']:.3f} | "
                     f"{r['human_attack_window_fpr']:.3f} | {r['session_accuracy']:.3f} | "
                     f"{r['raw_p']:.4f} | {r['holm_p_five_test_family']:.4f} |")
    lines += ["", "The outside-login label describes the session, not the operator active in a window. "
              "Neither the before nor after periods are known benign; after periods may contain attack effects.",
              "The p-values test label association, not the difference between models, and Holm correction "
              "covers these five exploratory analyses only. Group-label exchangeability may not hold.",
              "Paired intervals resample fixed predictions by session without model refitting or selection uncertainty.",
              "Process-free removes Windows Security 4688 and Sysmon 1 records and recomputes affected bins; "
              "other process-related events and correlated signals remain."]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved audit results to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--experiment", type=Path, required=True)
    p.add_argument("--prior-investigation", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("evaluate")
    p.add_argument("--experiment", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "extract":
        extract(args.source, args.experiment, args.prior_investigation, args.output)
    else:
        evaluate(args.experiment, args.output)
