"""Exploratory human/AI classification using defender-visible telemetry."""

import argparse
from bisect import bisect_right
import csv
from datetime import datetime
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
HOSTS = ("dc01", "dc03", "srv02", "srv03")
SECURITY_IDS = (4624, 4625, 4634, 4648, 4672, 4688, 4689, 4768, 4769, 5140, 5145, 5156, 5158)
SYSMON_IDS = (1, 3, 7, 10, 11, 12, 13, 22)
FEATURES = {
    "security": tuple(f"security_{i}" for i in SECURITY_IDS) + ("security_other",),
    "sysmon": tuple(f"sysmon_{i}" for i in SYSMON_IDS) + ("sysmon_other",),
    "flow": ("flow_records", "flow_packets", "flow_bytes", "flow_tcp", "flow_udp",
             "flow_other_protocol", "flow_accept", "flow_reject"),
}
FEATURES["combined"] = FEATURES["security"] + FEATURES["sysmon"] + FEATURES["flow"]
EVENT_ID = re.compile(r"<(?:\w+:)?EventID(?:\s[^>]*)?>\s*(\d+)\s*</(?:\w+:)?EventID\s*>", re.I)
WINDOW_SECONDS = 30


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class FrozenInputs:
    def __init__(self, source):
        self.root = source.resolve()
        path = self.root / "reports" / "FREEZE_1.json"
        self.freeze_hash = sha256(path)
        self.files = json.loads(path.read_text(encoding="utf-8"))["files"]
        self.verified = {}

    def get(self, rel):
        metadata = self.files.get(rel)
        if metadata is None:
            raise ValueError(f"Input missing from Freeze 1: {rel}")
        path = self.root.joinpath(*rel.split("/"))
        actual = sha256(path)
        if actual != metadata["sha256"]:
            raise ValueError(f"Frozen input hash mismatch: {rel}")
        self.verified[rel] = actual
        return path


def timestamp(text):
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Login start has no timezone")
    return value.timestamp()


def make_windows(inp):
    report = json.loads(inp.get("reports/05_windows_report.json").read_text(encoding="utf-8"))
    labels = {row["session_key"]: row["class"] for row in rows(inp.get("data/labels/sessions.csv"))
              if row["included"] == "1"}
    logins = {row["login_key"] for row in rows(inp.get("data/labels/logins.csv"))
              if row["included"] == "1"}
    if sorted(labels.values()) != ["ai"] * 4 + ["human"] * 5:
        raise ValueError("Expected five human and four AI sessions")
    windows_by_session = {}
    seen_logins = set()
    for participant, info in sorted(report["sessions"].items()):
        session = info["session_key"]
        if session not in labels:
            raise ValueError("Window report contains a session absent from labels")
        windows = []
        for login in info["logins"].values():
            key = login["login_key"]
            if key not in logins:
                continue
            if key in seen_logins:
                raise ValueError("Duplicate included login")
            seen_logins.add(key)
            rel = f"data/cleaned/{session}/{key}.recorder.jsonl"
            with inp.get(rel).open(encoding="utf-8") as stream:
                start = json.loads(json.loads(next(stream))["message"])
            if start["kind"] != "start":
                raise ValueError(f"First recorder record is not a login start: {rel}")
            t0 = timestamp(start["time"])
            duration = float(login["w30"]["duration_s"])
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Invalid login duration")
            for index in range(int(duration // WINDOW_SECONDS)):
                a = t0 + index * WINDOW_SECONDS
                windows.append({
                    "session": session, "label": labels[session],
                    "window": f"{key}_{index}", "start": a, "end": a + WINDOW_SECONDS,
                    "values": {name: 0 for name in FEATURES["combined"]},
                    "covered": set(), "skipped_flow": False,
                })
        windows.sort(key=lambda w: w["start"])
        if any(a["end"] > b["start"] for a, b in zip(windows, windows[1:])):
            raise ValueError(f"Overlapping included login windows for {participant}")
        if not windows:
            raise ValueError(f"No full windows for {participant}")
        windows_by_session[participant] = windows
    if seen_logins != logins or len(windows_by_session) != len(labels):
        raise ValueError("Included logins or sessions do not match the window report")
    return windows_by_session


def locate(windows, starts, moment):
    index = bisect_right(starts, moment) - 1
    if index >= 0 and moment < windows[index]["end"]:
        return windows[index]
    return None


def mark_coverage(windows, source, first, last):
    if first is None or last is None:
        raise ValueError(f"No usable timestamps for {source}")
    for window in windows:
        if first <= window["start"] and last >= window["end"]:
            window["covered"].add(source)


def windows_stream(path, windows, host, channel):
    starts = [w["start"] for w in windows]
    first = last = None
    count = matched = 0
    ids = SECURITY_IDS if channel == "security" else SYSMON_IDS
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            moment = float(record["timestamp"]) / 1000
            if not math.isfinite(moment):
                raise ValueError(f"Invalid event timestamp: {path}")
            first = moment if first is None else min(first, moment)
            last = moment if last is None else max(last, moment)
            count += 1
            window = locate(windows, starts, moment)
            if window is None:
                continue
            match = EVENT_ID.search(record["message"])
            if not match:
                raise ValueError(f"Cannot parse an in-window Windows EventID in {path}")
            event_id = int(match.group(1))
            key = f"{channel}_{event_id}" if event_id in ids else f"{channel}_other"
            window["values"][key] += 1
            matched += 1
    source = f"{host}/{channel}"
    mark_coverage(windows, source, first, last)
    return {"records": count, "in_window": matched}


def flow_stream(path, windows):
    starts = [w["start"] for w in windows]
    ends = [w["end"] for w in windows]
    first = last = None
    count = matched = skipped = zero_duration_skipped = 0
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            fields = record["message"].split()
            if len(fields) != 14 or fields[0] != "2":
                raise ValueError(f"Unexpected VPC flow format: {path}")
            start, end = int(fields[10]), int(fields[11])
            if end < start:
                raise ValueError(f"Invalid VPC flow interval: {path}")
            first = start if first is None else min(first, start)
            last = end if last is None else max(last, end)
            count += 1
            status = fields[13]
            if status == "SKIPDATA":
                skipped += 1
                if start == end:
                    zero_duration_skipped += 1
                    window = locate(windows, starts, start)
                    if window is not None:
                        window["skipped_flow"] = True
                    continue
                i = bisect_right(ends, start)
                while i < len(windows) and windows[i]["start"] < end:
                    windows[i]["skipped_flow"] = True
                    i += 1
                continue
            if status == "NODATA":
                continue
            if status != "OK":
                raise ValueError(f"Unexpected VPC flow status {status!r}: {path}")
            window = locate(windows, starts, end)
            if window is None:
                continue
            packets, byte_count = int(fields[8]), int(fields[9])
            if packets < 0 or byte_count < 0 or fields[12] not in ("ACCEPT", "REJECT"):
                raise ValueError(f"Invalid VPC flow record: {path}")
            values = window["values"]
            values["flow_records"] += 1
            values["flow_packets"] += packets
            values["flow_bytes"] += byte_count
            protocol = {"6": "tcp", "17": "udp"}.get(fields[7], "other_protocol")
            values["flow_" + protocol] += 1
            values["flow_" + fields[12].lower()] += 1
            matched += 1
    mark_coverage(windows, "flow", first, last)
    return {"records": count, "in_window": matched, "skipdata_records": skipped,
            "zero_duration_skipdata_records": zero_duration_skipped}


def extract(source, output):
    source, output = source.resolve(), output.resolve()
    script_hash = sha256(Path(__file__).resolve())
    if output == source or source in output.parents or output in source.parents or output == ROOT or ROOT in output.parents:
        raise ValueError("Output must be outside the study folder and Git repository")
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    inp = FrozenInputs(source)
    by_session = make_windows(inp)
    streams = {}
    required = {f"{host}/{channel}" for host in HOSTS for channel in ("security", "sysmon")} | {"flow"}
    for participant, windows in by_session.items():
        session = windows[0]["session"]
        streams[session] = {}
        for host in HOSTS:
            for channel in ("security", "sysmon"):
                path = inp.get(f"set_aside/{participant}/{host}/{channel}.jsonl.gz")
                streams[session][f"{host}/{channel}"] = windows_stream(path, windows, host, channel)
        path = inp.get(f"set_aside/{participant}/vpc-flow/eni-all.jsonl.gz")
        streams[session]["flow"] = flow_stream(path, windows)
        print(f"Processed defender logs for {session}", flush=True)
    all_windows = [window for windows in by_session.values() for window in windows]
    kept = [w for w in all_windows if required <= w["covered"] and not w["skipped_flow"]]
    if {w["session"] for w in kept} != {w["session"] for w in all_windows}:
        raise ValueError("At least one session has no common-coverage windows")
    if sha256(Path(__file__).resolve()) != script_hash:
        raise ValueError("Experiment code changed during extraction")
    output.mkdir(parents=True)
    path = output / "features.csv"
    columns = ["session", "label", "window"] + list(FEATURES["combined"])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for w in kept:
            writer.writerow({"session": w["session"], "label": w["label"],
                             "window": w["window"], **w["values"]})
    counts = {label: sum(w["label"] == label for w in kept) for label in ("human", "ai")}
    coverage = {}
    for windows in by_session.values():
        session = windows[0]["session"]
        coverage[session] = {
            "class": windows[0]["label"],
            "candidate_windows": len(windows),
            "eligible_windows": sum(required <= w["covered"] and not w["skipped_flow"] for w in windows),
            "excluded_missing_coverage": sum(not required <= w["covered"] for w in windows),
            "excluded_skipdata": sum(w["skipped_flow"] for w in windows),
        }
    manifest = {
        "version": 1, "window_seconds": WINDOW_SECONDS, "freeze1_sha256": inp.freeze_hash,
        "script_sha256": script_hash,
        "inputs_sha256": inp.verified, "features_sha256": sha256(path),
        "total_full_windows": len(all_windows), "eligible_windows": len(kept),
        "excluded_missing_coverage": sum(not required <= w["covered"] for w in all_windows),
        "excluded_skipdata": sum(w["skipped_flow"] for w in all_windows),
        "eligible_by_class": counts, "coverage_by_session": coverage,
        "streams": streams, "feature_sets": FEATURES,
    }
    (output / "extraction.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Extraction complete: {len(kept)}/{len(all_windows)} common-coverage windows.")


def holm(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    previous = 0.0
    for rank, i in enumerate(order):
        previous = max(previous, min(1.0, (len(values) - rank) * values[i]))
        out[i] = previous
    return out


def evaluate(output, permutations):
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.preprocessing import StandardScaler

    output = output.resolve()
    output_file = output / ("results.json" if permutations else "smoke-results.json")
    report_file = output / ("RESULTS.md" if permutations else "SMOKE_RESULTS.md")
    if output_file.exists() or report_file.exists():
        raise ValueError("Refusing to overwrite an existing results file")
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    path = output / "features.csv"
    if (sha256(path) != manifest["features_sha256"]
            or sha256(Path(__file__).resolve()) != manifest["script_sha256"]
            or manifest["feature_sets"] != {k: list(v) for k, v in FEATURES.items()}):
        raise ValueError("Feature file or feature schema changed after extraction")
    data = rows(path)
    sessions = sorted({r["session"] for r in data})
    classes = {}
    for row in data:
        s, label = row["session"], row["label"]
        if label not in ("human", "ai") or (s in classes and classes[s] != label):
            raise ValueError("Invalid or inconsistent session label")
        classes[s] = label
    if len(sessions) != 9 or sum(v == "ai" for v in classes.values()) != 4:
        raise ValueError("Expected nine sessions and four AI sessions")
    groups = np.array([r["session"] for r in data])
    y = np.array([int(r["label"] == "ai") for r in data])
    true_ai = tuple(s for s in sessions if classes[s] == "ai")
    assignments = list(itertools.combinations(sessions, 4))

    def score(X, assignment):
        actual = np.isin(groups, assignment).astype(int)
        predicted = np.zeros(len(data), dtype=int)
        probs = np.zeros(len(data), dtype=float)
        for held in sessions:
            train, test = groups != held, groups == held
            training_sessions = [s for s in sessions if s != held]
            weights = np.empty(int(train.sum()), dtype=float)
            train_groups = groups[train]
            for cls in (0, 1):
                members = [s for s in training_sessions if int(s in assignment) == cls]
                for s in members:
                    mask = train_groups == s
                    weights[mask] = 0.5 / len(members) / mask.sum()
            weights *= len(weights) / weights.sum()
            scaler = StandardScaler().fit(X[train])
            model = LogisticRegression(solver="liblinear", random_state=42, max_iter=1000)
            model.fit(scaler.transform(X[train]), actual[train], sample_weight=weights)
            probs[test] = model.predict_proba(scaler.transform(X[test]))[:, 1]
            predicted[test] = (probs[test] >= 0.5).astype(int)
        return float(f1_score(actual, predicted, average="macro", zero_division=0)), predicted, probs

    results = {}
    for name, columns in FEATURES.items():
        X = np.log1p(np.array([[float(r[c]) for c in columns] for r in data], dtype=float))
        if not np.isfinite(X).all():
            raise ValueError(f"Invalid values in {name} features")
        metric, predictions, probabilities = score(X, true_ai)
        session_calls = {s: int(probabilities[groups == s].mean() >= 0.5) for s in sessions}
        entry = {
            "macro_f1": metric, "windows": len(data),
            "session_accuracy": sum(session_calls[s] == int(s in true_ai) for s in sessions) / len(sessions),
            "ai_recall": float(np.mean(predictions[y == 1] == 1)),
            "human_false_positive_rate": float(np.mean(predictions[y == 0] == 1)),
            "true_labels": y.tolist(), "predictions": predictions.tolist(),
            "session_calls": session_calls,
        }
        counts = {}
        for s in sessions:
            mask = groups == s
            counts[s] = np.array([
                np.sum((y[mask] == 1) & (predictions[mask] == 1)),
                np.sum((y[mask] == 0) & (predictions[mask] == 1)),
                np.sum((y[mask] == 1) & (predictions[mask] == 0)),
                np.sum((y[mask] == 0) & (predictions[mask] == 0)),
            ])
        humans = [s for s in sessions if s not in true_ai]
        rng = np.random.default_rng(42)
        boot = []
        for _ in range(2000):
            chosen = list(rng.choice(humans, len(humans), replace=True))
            chosen += list(rng.choice(true_ai, len(true_ai), replace=True))
            tp, fp, fn, tn = np.sum([counts[s] for s in chosen], axis=0)
            f_ai = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
            f_human = 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 0
            boot.append((f_ai + f_human) / 2)
        entry["session_bootstrap_95_interval"] = [float(v) for v in np.percentile(boot, [2.5, 97.5])]
        if permutations:
            chance = [score(X, combo)[0] for combo in assignments]
            if abs(chance[assignments.index(true_ai)] - metric) > 1e-12:
                raise ValueError("True permutation does not match the original score")
            entry["permutation_p"] = sum(v >= metric - 1e-12 for v in chance) / len(chance)
            entry["permutations"] = len(chance)
            entry["permutation_median"] = float(np.median(chance))
        results[name] = entry
        print(f"Evaluated {name}: macro-F1 {metric:.3f}", flush=True)
    if permutations:
        adjusted = holm([results[name]["permutation_p"] for name in FEATURES])
        for name, value in zip(FEATURES, adjusted):
            results[name]["holm_p"] = value
    document = {
        "exploratory": True, "estimator": "logistic_regression_liblinear",
        "threshold": 0.5, "seed": 42, "unit_of_split": "session",
        "feature_file_sha256": manifest["features_sha256"],
        "python": sys.version.split()[0], "numpy": np.__version__,
        "scikit_learn": __import__("sklearn").__version__, "results": results,
    }
    output_file.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "# Defender telemetry experiment",
        "",
        "**Exploratory; not an independent replication or a benign-traffic detector.**",
        f"30-second candidate windows: {manifest['total_full_windows']}; "
        f"common-coverage windows: {manifest['eligible_windows']} "
        f"({manifest['eligible_by_class']['human']} human, {manifest['eligible_by_class']['ai']} AI).",
        f"Windows overlapping network SKIPDATA: {manifest['excluded_skipdata']}; "
        f"windows outside observed source extents: {manifest['excluded_missing_coverage']} "
        "(exclusion categories may overlap).",
        "",
        "| Features | Macro-F1 | 95% session interval | AI recall | Human attack-window FPR | Session accuracy | Permutation p | Holm p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in FEATURES:
        entry = results[name]
        low, high = entry["session_bootstrap_95_interval"]
        p = f"{entry['permutation_p']:.4f}" if permutations else "not run"
        adjusted = f"{entry['holm_p']:.4f}" if permutations else "not run"
        report.append(
            f"| {name} | {entry['macro_f1']:.3f} | {low:.3f}-{high:.3f} | "
            f"{entry['ai_recall']:.3f} | {entry['human_false_positive_rate']:.3f} | "
            f"{entry['session_accuracy']:.3f} | {p} | {adjusted} |"
        )
    report += [
        "",
        "Permutations relabel whole sessions; interpretation assumes exchangeable sessions. "
        "Confidence intervals resample sessions within each class.",
        "Matched login boundaries are supplied by the prior study. Flow records are assigned "
        "to the window containing their end time, not necessarily when traffic occurred.",
        "Sensor coverage and exclusion rates may differ by session; see extraction.json. "
        "No causal or production-performance conclusion follows from this analysis.",
        "",
    ]
    report_file.write_text("\n".join(report), encoding="utf-8")
    print(f"Saved {'full permutation results' if permutations else 'smoke results'} to {output_file}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    extraction = commands.add_parser("extract")
    extraction.add_argument("--source", type=Path, required=True)
    extraction.add_argument("--output", type=Path, required=True)
    scoring = commands.add_parser("evaluate")
    scoring.add_argument("--output", type=Path, required=True)
    scoring.add_argument("--smoke", action="store_true", help="skip permutations; not hypothesis evidence")
    args = parser.parse_args()
    try:
        if args.command == "extract":
            extract(args.source, args.output)
        else:
            evaluate(args.output, not args.smoke)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
