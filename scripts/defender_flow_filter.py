"""Rebuild flow features after removing selected UDP port traffic."""

import argparse
from collections import Counter
import csv
import gzip
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


FLOW_COLUMNS = base.FEATURES["flow"] + tuple(f"bin_flow_{i}" for i in range(6))


def add_flow(values, fields, index):
    packets, byte_count = int(fields[8]), int(fields[9])
    if packets < 0 or byte_count < 0 or fields[12] not in ("ACCEPT", "REJECT"):
        raise ValueError("Invalid VPC flow record")
    values["flow_records"] += 1
    values["flow_packets"] += packets
    values["flow_bytes"] += byte_count
    proto = {"6": "tcp", "17": "udp"}.get(fields[7], "other_protocol")
    values["flow_" + proto] += 1
    values["flow_" + fields[12].lower()] += 1
    values[f"bin_flow_{index}"] += 1


def excluded(fields):
    if fields[7] != "17":
        return False
    source, destination = int(fields[5]), int(fields[6])
    if not 0 <= source <= 65535 or not 0 <= destination <= 65535:
        raise ValueError("Invalid UDP flow port")
    return source in (41641, 3478) or destination in (41641, 3478)


def extract(source, experiment, output):
    source, experiment = source.resolve(), experiment.resolve()
    output = expanded.safe_output(output, source, experiment)
    own_hash = base.sha256(Path(__file__).resolve())
    _, _, _, _, _, provenance = sequence.prepare(experiment)
    manifest = json.loads((experiment / "extraction.json").read_text(encoding="utf-8"))
    inp = base.FrozenInputs(source)
    if inp.freeze_hash != manifest["freeze1_sha256"]:
        raise ValueError("Study freeze does not match the previous experiment")
    original_rows = base.rows(experiment / "windows30.csv")
    prior = {(r["session"], r["window"]): r for r in original_rows}
    if len(prior) != len(original_rows):
        raise ValueError("Duplicate prior feature windows")
    found = set()
    rows = []
    counts = {}
    for participant, all_windows in base.make_windows(inp).items():
        windows = [w for w in all_windows if (w["session"], w["window"]) in prior]
        if not windows:
            raise ValueError("A session has no prior windows")
        session, label = windows[0]["session"], windows[0]["label"]
        starts = [w["start"] for w in windows]
        for w in windows:
            w["original_flow"] = {name: 0 for name in FLOW_COLUMNS}
            w["filtered_flow"] = {name: 0 for name in FLOW_COLUMNS}
        stats = Counter()
        path = inp.get(f"set_aside/{participant}/vpc-flow/eni-all.jsonl.gz")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                fields = json.loads(line)["message"].split()
                if len(fields) != 14 or fields[0] != "2":
                    raise ValueError("Unexpected VPC flow record")
                if fields[13] != "OK":
                    if fields[13] not in ("NODATA", "SKIPDATA"):
                        raise ValueError("Unexpected flow status")
                    continue
                moment = int(fields[11])
                w = base.locate(windows, starts, moment)
                if w is None:
                    continue
                index = int((moment - w["start"]) // 5)
                add_flow(w["original_flow"], fields, index)
                stats["original_records"] += 1
                if excluded(fields):
                    stats["excluded_records"] += 1
                    if fields[12] == "REJECT":
                        stats["excluded_rejected_records"] += 1
                else:
                    add_flow(w["filtered_flow"], fields, index)
        for w in windows:
            key = (session, w["window"])
            row = dict(prior[key])
            if row["label"] != label:
                raise ValueError("Prior labels differ")
            for column in FLOW_COLUMNS:
                if int(row[column]) != w["original_flow"][column]:
                    raise ValueError(f"Original flow feature mismatch: {column}")
                row[column] = w["filtered_flow"][column]
            rows.append(row)
            found.add(key)
        counts[session] = {"class": label, **stats}
        print(f"Filtered flow records for {session}", flush=True)
    if found != set(prior):
        raise ValueError("Prior windows do not match frozen login metadata")
    if base.sha256(Path(__file__).resolve()) != own_hash:
        raise ValueError("Flow-filter code changed during extraction")
    output.mkdir(parents=True)
    path = output / "filtered_windows30.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(original_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    document = {
        "version": 1, "script_sha256": own_hash, "freeze1_sha256": inp.freeze_hash,
        "provenance": provenance, "inputs_sha256": inp.verified,
        "filtered_features_sha256": base.sha256(path), "port_filter": [41641, 3478],
        "counts_by_session": counts,
    }
    (output / "extraction.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rebuilt {len(rows)} windows after port-based filtering.", flush=True)


def evaluate(experiment, output):
    experiment, output = experiment.resolve(), output.resolve()
    result_path = output / "results.json"
    if result_path.exists() or (output / "RESULTS.md").exists():
        raise ValueError("Refusing to overwrite results")
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    path = output / "filtered_windows30.csv"
    _, groups, labels, sessions, baseline, provenance = sequence.prepare(experiment)
    if (manifest["script_sha256"] != base.sha256(Path(__file__).resolve())
            or manifest["filtered_features_sha256"] != base.sha256(path)
            or manifest["provenance"] != provenance):
        raise ValueError("Filtered input, script, or prior experiment changed")
    data = expanded.aggregate(base.rows(path), 30)
    if labels.tolist() != [int(r["label"] == "ai") for r in data] or groups.tolist() != [r["session"] for r in data]:
        raise ValueError("Filtered and baseline windows are misaligned")
    true_ai = tuple(s for s in sessions if labels[groups == s][0] == 1)
    observed, predicted, probabilities = expanded.model_score(data, sequence.BASE_COLUMNS, true_ai, "xgboost", False)
    result = sequence.summarize(labels, groups, sessions, probabilities)
    import itertools
    assignments = list(itertools.combinations(sessions, 4))
    chance = [expanded.model_score(data, sequence.BASE_COLUMNS, a, "xgboost", False)[0]
              for a in assignments]
    if abs(chance[assignments.index(true_ai)] - observed) > 1e-12:
        raise ValueError("True permutation does not match the observed score")
    result["permutation_p"] = sum(x >= observed - 1e-12 for x in chance) / len(chance)
    result["permutations"] = len(chance)
    result["delta_from_combined_baseline"] = observed - baseline["macro_f1"]
    result["paired_interval"] = ablation.paired_interval(
        labels, groups, sessions, np.array(baseline["predictions"]), predicted
    )
    result["predictions"] = predicted.tolist()
    if base.sha256(Path(__file__).resolve()) != manifest["script_sha256"]:
        raise ValueError("Flow-filter code changed during evaluation")
    result_path.write_text(json.dumps({"exploratory": True, "result": result, "provenance": provenance},
                                      indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lo, hi = result["paired_interval"]
    lines = [
        "# Port-filtered flow sensitivity", "",
        "**Exploratory; no benign-traffic evaluation or independent validation.**",
        "Recomputed all flow features after removing UDP records with source or destination "
        "port 41641 or 3478. Port numbers do not establish application identity.",
        f"Same {len(data)} eligible 30-second windows and nine sessions as the baseline.",
        "", "| Model | Macro-F1 | AI recall | Human attack FPR | Session accuracy | Raw p |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Port-filtered XGBoost | {result['macro_f1']:.3f} | {result['ai_recall']:.3f} | "
        f"{result['human_attack_window_fpr']:.3f} | {result['session_accuracy']:.3f} | "
        f"{result['permutation_p']:.4f} |",
        "", f"Change from combined baseline: {result['delta_from_combined_baseline']:+.3f} "
        f"(paired fixed-prediction session interval {lo:+.3f} to {hi:+.3f}).",
        "The 126 session-label permutations test association, not improvement; the p-value is "
        "unadjusted and the filter was chosen after inspecting the data.",
        "Filtering ports may remove unrelated traffic and can leave other infrastructure signals "
        "in ICMP, traffic volume, and host features. It cannot establish the traffic's process or "
        "prove whether remaining signal is operator behavior.",
        "",
    ]
    (output / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Port-filtered F1 {result['macro_f1']:.3f}; saved results to {output}", flush=True)


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
