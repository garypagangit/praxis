"""Exploratory follow-on experiments using frozen defender telemetry."""

import argparse
from bisect import bisect_right
import csv
import gzip
import itertools
import json
import math
import os
from pathlib import Path
import sys

import defender_telemetry_experiment as base


ROOT = Path(__file__).resolve().parent.parent
SIZES = (30, 60, 120, 300)
EXTRA = {
    "dc01/system": "system",
    "dc01/microsoft-windows-taskscheduler-operational": "tasks",
    "dc03/microsoft-windows-taskscheduler-operational": "tasks",
    "srv02/application": "application",
    "srv02/system": "system",
    "srv02/microsoft-windows-taskscheduler-operational": "tasks",
    "srv02/iis-access": "iis",
    "srv03/application": "application",
    "srv03/microsoft-windows-taskscheduler-operational": "tasks",
}
EXTRA_IDS = {
    "system": (1074, 6005, 6006, 6008, 7036, 7040, 7045),
    "tasks": (100, 102, 106, 129, 140, 141, 200, 201),
    "application": (1000, 1001, 1002, 1004, 1026, 11707),
}
EXTRA_FEATURES = tuple(
    f"{channel}_{event}" for channel, events in EXTRA_IDS.items()
    for event in (*events, "other")
) + ("iis_records",)
BIN_CHANNELS = ("security", "sysmon", "flow", "extra")
BIN_COLUMNS = tuple(f"bin_{channel}_{i}" for channel in BIN_CHANNELS for i in range(6))
BEHAVIOR_FEATURES = tuple(
    f"{channel}_{feature}" for channel in BIN_CHANNELS
    for feature in ("active_fraction", "peak_fraction", "variation")
) + ("security_sysmon_coactive", "windows_extra_coactive")


def safe_output(output, source, prior):
    output = output.resolve()
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    for root in (ROOT, source.resolve(), prior.resolve()):
        if output == root or root in output.parents or output in root.parents:
            raise ValueError("Output must be outside the repository, study, and prior output")
    return output


def timing_stream(path, windows, channel, flow=False, extra_channel=None):
    starts = [w["start"] for w in windows]
    matched = 0
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if flow:
                fields = record["message"].split()
                if len(fields) != 14 or fields[0] != "2":
                    raise ValueError(f"Unexpected flow record in {path}")
                if fields[13] != "OK":
                    if fields[13] not in ("NODATA", "SKIPDATA"):
                        raise ValueError(f"Unexpected flow status in {path}")
                    continue
                moment = int(fields[11])
            else:
                moment = float(record["timestamp"]) / 1000
                if not math.isfinite(moment):
                    raise ValueError(f"Invalid event timestamp in {path}")
            window = base.locate(windows, starts, moment)
            if window is None:
                continue
            bin_index = int((moment - window["start"]) // 5)
            window["extra"][f"bin_{channel}_{bin_index}"] += 1
            if extra_channel == "iis":
                window["extra"]["iis_records"] += 1
            elif extra_channel:
                match = base.EVENT_ID.search(record["message"])
                if not match:
                    raise ValueError(f"Cannot parse an in-window event in {path}")
                event = int(match.group(1))
                name = str(event) if event in EXTRA_IDS[extra_channel] else "other"
                window["extra"][f"{extra_channel}_{name}"] += 1
            matched += 1
    return matched


def extract(source, prior, output):
    source, prior = source.resolve(), prior.resolve()
    output = safe_output(output, source, prior)
    script_hash = base.sha256(Path(__file__).resolve())
    base_script_hash = base.sha256(Path(base.__file__).resolve())
    manifest_path = prior / "extraction.json"
    prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prior_features = prior / "features.csv"
    if (prior_manifest["window_seconds"] != 30
            or prior_manifest["script_sha256"] != base_script_hash
            or prior_manifest["features_sha256"] != base.sha256(prior_features)):
        raise ValueError("Prior extraction, feature file, or original script changed")
    inp = base.FrozenInputs(source)
    if inp.freeze_hash != prior_manifest["freeze1_sha256"]:
        raise ValueError("The study freeze differs from the original extraction")
    by_session = base.make_windows(inp)
    existing = {(r["session"], r["window"]): r for r in base.rows(prior_features)}
    if len(existing) != prior_manifest["eligible_windows"]:
        raise ValueError("Duplicate or missing previous windows")
    streams = {}
    found = set()
    retained = []
    for participant, all_windows in by_session.items():
        windows = []
        for w in all_windows:
            key = (w["session"], w["window"])
            if key in existing:
                if w["label"] != existing[key]["label"]:
                    raise ValueError("Prior and current session labels differ")
                w["extra"] = {name: 0 for name in EXTRA_FEATURES + BIN_COLUMNS}
                windows.append(w)
                found.add(key)
        if not windows:
            raise ValueError("A session has no retained windows")
        session = windows[0]["session"]
        streams[session] = {}
        for host in base.HOSTS:
            for channel in ("security", "sysmon"):
                rel = f"set_aside/{participant}/{host}/{channel}.jsonl.gz"
                streams[session][f"{host}/{channel}"] = timing_stream(
                    inp.get(rel), windows, channel
                )
        rel = f"set_aside/{participant}/vpc-flow/eni-all.jsonl.gz"
        streams[session]["flow"] = timing_stream(inp.get(rel), windows, "flow", flow=True)
        for stream_name, kind in EXTRA.items():
            rel = f"set_aside/{participant}/{stream_name}.jsonl.gz"
            streams[session][stream_name] = timing_stream(
                inp.get(rel), windows, "extra", extra_channel=kind
            )
        for channel in ("security", "sysmon", "flow"):
            observed = sum(w["extra"][f"bin_{channel}_{i}"] for w in windows for i in range(6))
            if channel == "flow":
                expected = sum(int(existing[(session, w["window"])]["flow_records"]) for w in windows)
            else:
                expected = sum(
                    int(existing[(session, w["window"])][column])
                    for w in windows for column in base.FEATURES[channel]
                )
            if observed != expected:
                raise ValueError(f"{channel} timing records do not match previous extraction")
        for w in windows:
            row = dict(existing[(session, w["window"])])
            row.update(w["extra"])
            retained.append(row)
        print(f"Processed expanded telemetry for {session}", flush=True)
    if found != set(existing):
        raise ValueError("Prior windows do not match frozen login metadata")
    if base.sha256(Path(__file__).resolve()) != script_hash:
        raise ValueError("Expanded code changed during extraction")
    output.mkdir(parents=True)
    columns = ["session", "label", "window"] + list(base.FEATURES["combined"])
    columns += list(EXTRA_FEATURES + BIN_COLUMNS)
    path = output / "windows30.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(retained)
    document = {
        "version": 1, "window_seconds": 30, "freeze1_sha256": inp.freeze_hash,
        "original_script_sha256": base_script_hash, "script_sha256": script_hash,
        "prior_extraction_sha256": base.sha256(manifest_path),
        "prior_features_sha256": prior_manifest["features_sha256"],
        "inputs_sha256": inp.verified, "windows30_sha256": base.sha256(path),
        "extra_streams": EXTRA, "in_window_records_by_session": streams,
        "prior_coverage": prior_manifest["coverage_by_session"],
    }
    (output / "extraction.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Extracted timing and additional channels for {len(retained)} windows.", flush=True)


def aggregate(rows, size):
    if size not in SIZES:
        raise ValueError("Unsupported window size")
    factor = size // 30
    grouped = {}
    for row in rows:
        login, index = row["window"].rsplit("_", 1)
        index = int(index)
        key = (row["session"], login, index // factor)
        grouped.setdefault(key, {})[index % factor] = row
    output = []
    for (session, login, index), parts in sorted(grouped.items()):
        if set(parts) != set(range(factor)):
            continue
        ordered = [parts[i] for i in range(factor)]
        if len({r["label"] for r in ordered}) != 1:
            raise ValueError("Inconsistent labels within an aggregated window")
        values = {name: sum(int(r[name]) for r in ordered)
                  for name in base.FEATURES["combined"] + EXTRA_FEATURES}
        bins = {
            channel: [int(row[f"bin_{channel}_{i}"]) for row in ordered for i in range(6)]
            for channel in BIN_CHANNELS
        }
        for channel, counts in bins.items():
            total = sum(counts)
            mean = total / len(counts)
            variance = sum((x - mean) ** 2 for x in counts) / len(counts)
            values[f"{channel}_active_fraction"] = sum(x > 0 for x in counts) / len(counts)
            values[f"{channel}_peak_fraction"] = max(counts) / total if total else 0
            values[f"{channel}_variation"] = math.sqrt(variance) / mean if mean else 0
        values["security_sysmon_coactive"] = sum(
            a > 0 and b > 0 for a, b in zip(bins["security"], bins["sysmon"])
        ) / len(bins["security"])
        values["windows_extra_coactive"] = sum(
            (a > 0 or b > 0) and c > 0
            for a, b, c in zip(bins["security"], bins["sysmon"], bins["extra"])
        ) / len(bins["security"])
        output.append({"session": session, "label": ordered[0]["label"],
                       "window": f"{login}_{index}", **values})
    return output


def model_score(data, columns, assignment, model_kind, smote):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.preprocessing import StandardScaler
    from xgboost import XGBClassifier

    sessions = sorted({row["session"] for row in data})
    groups = np.array([r["session"] for r in data])
    actual = np.isin(groups, assignment).astype(int)
    X = np.log1p(np.array([[float(r[c]) for c in columns] for r in data]))
    if not np.isfinite(X).all():
        raise ValueError("Non-finite feature values")
    predicted = np.zeros(len(data), dtype=int)
    probabilities = np.zeros(len(data), dtype=float)
    for held in sessions:
        train, test = groups != held, groups == held
        train_groups = groups[train]
        train_y = actual[train]
        weights = np.zeros(len(train_y), dtype=float)
        for cls in (0, 1):
            members = [s for s in sessions if s != held and int(s in assignment) == cls]
            if not members:
                raise ValueError("Training fold is missing a class")
            for s in members:
                mask = train_groups == s
                weights[mask] = 0.5 / len(members) / mask.sum()
        scaler = StandardScaler().fit(X[train])
        train_x = scaler.transform(X[train])
        if smote:
            from imblearn.over_sampling import SMOTE
            class_counts = np.bincount(train_y, minlength=2)
            if class_counts.min() < 2:
                raise ValueError("SMOTE requires at least two training windows per class")
            minority = int(np.argmin(class_counts))
            sampler = SMOTE(random_state=42, k_neighbors=min(5, int(class_counts.min()) - 1))
            resampled_x, resampled_y = sampler.fit_resample(train_x, train_y)
            extra = len(resampled_y) - len(train_y)
            synthetic_weights = np.full(extra, weights[train_y == minority].mean())
            weights = np.concatenate((weights, synthetic_weights))
            train_x, train_y = resampled_x, resampled_y
            for cls in (0, 1):
                mask = train_y == cls
                weights[mask] *= 0.5 / weights[mask].sum()
        weights *= len(weights) / weights.sum()
        if model_kind == "logistic":
            model = LogisticRegression(solver="liblinear", random_state=42, max_iter=1000)
        elif model_kind == "xgboost":
            model = XGBClassifier(
                n_estimators=80, max_depth=3, learning_rate=0.1, subsample=1,
                colsample_bytree=1, n_jobs=1, random_state=42, eval_metric="logloss",
            )
        else:
            raise ValueError("Unknown estimator")
        model.fit(train_x, train_y, sample_weight=weights)
        probabilities[test] = model.predict_proba(scaler.transform(X[test]))[:, 1]
        predicted[test] = (probabilities[test] >= 0.5).astype(int)
    return float(f1_score(actual, predicted, average="macro", zero_division=0)), predicted, probabilities


def evaluate_phase(output, phase):
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    import numpy as np
    import sklearn
    import xgboost
    import imblearn

    output = output.resolve()
    path = output / f"{phase}.json"
    if path.exists():
        raise ValueError("Refusing to overwrite an existing phase result")
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    if (manifest["script_sha256"] != base.sha256(Path(__file__).resolve())
            or manifest["original_script_sha256"] != base.sha256(Path(base.__file__).resolve())
            or manifest["windows30_sha256"] != base.sha256(output / "windows30.csv")):
        raise ValueError("Code or expanded inputs changed after extraction")
    original = base.rows(output / "windows30.csv")
    all_sessions = sorted({r["session"] for r in original})
    ai = tuple(s for s in all_sessions if next(r["label"] for r in original if r["session"] == s) == "ai")
    if len(all_sessions) != 9 or len(ai) != 4:
        raise ValueError("Expected five human and four AI sessions")
    assignments = list(itertools.combinations(all_sessions, 4))
    model = "logistic" if phase == "windows" else "xgboost"
    enhanced = phase in ("behavior", "smote")
    smote = phase == "smote"
    columns = base.FEATURES["combined"] + (EXTRA_FEATURES + BEHAVIOR_FEATURES if enhanced else ())
    results = {}
    for size in SIZES:
        data = aggregate(original, size)
        groups = np.array([r["session"] for r in data])
        if set(groups) != set(all_sessions):
            results[str(size)] = {"status": "insufficient_coverage", "windows": len(data)}
            print(f"{phase} {size}s: insufficient coverage for all sessions", flush=True)
            continue
        labels = np.array([int(r["label"] == "ai") for r in data])
        metric, predictions, probabilities = model_score(data, columns, ai, model, smote)
        session_calls = {s: int(probabilities[groups == s].mean() >= 0.5) for s in all_sessions}
        counts = {}
        for s in all_sessions:
            mask = groups == s
            counts[s] = np.array([
                np.sum((labels[mask] == 1) & (predictions[mask] == 1)),
                np.sum((labels[mask] == 0) & (predictions[mask] == 1)),
                np.sum((labels[mask] == 1) & (predictions[mask] == 0)),
                np.sum((labels[mask] == 0) & (predictions[mask] == 0)),
            ])
        humans = [s for s in all_sessions if s not in ai]
        rng = np.random.default_rng(42)
        bootstrap = []
        for _ in range(2000):
            chosen = list(rng.choice(humans, len(humans), replace=True))
            chosen += list(rng.choice(ai, len(ai), replace=True))
            tp, fp, fn, tn = np.sum([counts[s] for s in chosen], axis=0)
            f_ai = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
            f_human = 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 0
            bootstrap.append((f_ai + f_human) / 2)
        chance = [model_score(data, columns, combo, model, smote)[0] for combo in assignments]
        if abs(chance[assignments.index(ai)] - metric) > 1e-12:
            raise ValueError("Observed labeling differs from its permutation")
        results[str(size)] = {
            "status": "complete", "windows": len(data),
            "windows_by_class": {k: sum(r["label"] == k for r in data) for k in ("human", "ai")},
            "windows_by_session": {s: int(np.sum(groups == s)) for s in all_sessions},
            "macro_f1": metric, "ai_recall": float(np.mean(predictions[labels == 1] == 1)),
            "human_attack_window_fpr": float(np.mean(predictions[labels == 0] == 1)),
            "session_accuracy": sum(session_calls[s] == int(s in ai) for s in all_sessions) / len(all_sessions),
            "session_calls": session_calls,
            "bootstrap_interval": [float(x) for x in np.percentile(bootstrap, [2.5, 97.5])],
            "permutations": len(chance),
            "permutation_p": sum(x >= metric - 1e-12 for x in chance) / len(chance),
            "predictions": predictions.tolist(), "labels": labels.tolist(),
        }
        print(f"{phase} {size}s: F1 {metric:.3f}, raw p {results[str(size)]['permutation_p']:.4f}", flush=True)
    document = {"phase": phase, "model": model, "features": list(columns), "smote": smote,
                "script_sha256": manifest["script_sha256"], "results": results,
                "versions": {"python": sys.version.split()[0], "numpy": np.__version__,
                             "sklearn": sklearn.__version__, "xgboost": xgboost.__version__,
                             "imblearn": imblearn.__version__}}
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("evaluate")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--phase", choices=("windows", "models", "behavior", "smote"), required=True)
    args = parser.parse_args()
    if args.command == "extract":
        extract(args.source, args.prior, args.output)
    else:
        evaluate_phase(args.output, args.phase)


if __name__ == "__main__":
    main()
