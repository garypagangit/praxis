"""Reproduce the 30-second XGBoost model and plot held-out feature reliance."""

import argparse
import json
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded


def describe(name):
    event_names = {
        "security_4624": "Security 4624: successful logon",
        "security_4625": "Security 4625: failed logon",
        "security_4634": "Security 4634: logoff",
        "security_4648": "Security 4648: explicit credentials",
        "security_4672": "Security 4672: special privileges",
        "security_4688": "Security 4688: process creation",
        "security_4689": "Security 4689: process termination",
        "security_4768": "Security 4768: Kerberos TGT request",
        "security_4769": "Security 4769: Kerberos service ticket",
        "security_5140": "Security 5140: network share access",
        "security_5145": "Security 5145: network share check",
        "security_5156": "Security 5156: allowed connection",
        "security_5158": "Security 5158: allowed port bind",
        "sysmon_1": "Sysmon 1: process creation",
        "sysmon_3": "Sysmon 3: network connection",
        "sysmon_7": "Sysmon 7: image load",
        "sysmon_10": "Sysmon 10: process access",
        "sysmon_11": "Sysmon 11: file creation",
        "sysmon_12": "Sysmon 12: registry object",
        "sysmon_13": "Sysmon 13: registry value",
        "sysmon_22": "Sysmon 22: DNS query",
        "flow_reject": "Rejected network flow records",
        "flow_other_protocol": "Non-TCP/UDP flow records",
        "flow_packets": "Network packet count",
        "flow_records": "Network flow record count",
        "flow_tcp": "TCP flow records",
        "flow_bytes": "Network byte count",
        "flow_variation": "Flow record timing variation",
        "security_variation": "Security event timing variation",
    }
    if name in event_names:
        return event_names[name]
    return name.replace("_", " ")


def calculate(output, repeats=30):
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    phase = json.loads((output / "behavior.json").read_text(encoding="utf-8"))
    features_file = output / "windows30.csv"
    if (manifest["script_sha256"] != base.sha256(Path(expanded.__file__).resolve())
            or manifest["original_script_sha256"] != base.sha256(Path(base.__file__).resolve())
            or manifest["windows30_sha256"] != base.sha256(features_file)
            or phase["script_sha256"] != manifest["script_sha256"]):
        raise ValueError("Experiment inputs or scripts differ from the saved evaluation")
    columns = base.FEATURES["combined"] + expanded.EXTRA_FEATURES + expanded.BEHAVIOR_FEATURES
    if phase["phase"] != "behavior" or phase["features"] != list(columns) or phase["smote"]:
        raise ValueError("Saved evaluation is not the expected non-SMOTE feature configuration")
    data = expanded.aggregate(base.rows(features_file), 30)
    groups = np.array([r["session"] for r in data])
    labels = np.array([int(r["label"] == "ai") for r in data])
    sessions = sorted(set(groups))
    if len(sessions) != 9 or sum(labels[groups == s][0] for s in sessions) != 4:
        raise ValueError("Expected five human and four AI sessions")
    X = np.log1p(np.array([[float(r[c]) for c in columns] for r in data]))
    if not np.isfinite(X).all():
        raise ValueError("Non-finite input features")
    saved = phase["results"]["30"]
    predictions = np.zeros(len(data), dtype=int)
    folds = []
    rng = np.random.default_rng(42)
    for held in sessions:
        train, test = groups != held, groups == held
        train_groups = groups[train]
        train_y = labels[train]
        weights = np.zeros(len(train_y), dtype=float)
        for cls in (0, 1):
            members = [s for s in sessions if s != held and labels[groups == s][0] == cls]
            for s in members:
                mask = train_groups == s
                weights[mask] = 0.5 / len(members) / mask.sum()
        weights *= len(weights) / weights.sum()
        scaler = StandardScaler().fit(X[train])
        model = XGBClassifier(
            n_estimators=80, max_depth=3, learning_rate=0.1, subsample=1,
            colsample_bytree=1, n_jobs=1, random_state=42, eval_metric="logloss",
        )
        model.fit(scaler.transform(X[train]), train_y, sample_weight=weights)
        held_x = scaler.transform(X[test])
        predictions[test] = (model.predict_proba(held_x)[:, 1] >= 0.5).astype(int)
        permutations = [rng.permutation(len(held_x)) for _ in range(repeats)]
        folds.append((test, held_x, model, permutations))
    observed = float(f1_score(labels, predictions, average="macro", zero_division=0))
    if (predictions.tolist() != saved["predictions"]
            or labels.tolist() != saved["labels"]
            or abs(observed - saved["macro_f1"]) > 1e-12):
        raise ValueError("Refitted models do not reproduce the saved held-out predictions")
    importance = []
    for index, name in enumerate(columns):
        scores = []
        for repeat in range(repeats):
            shuffled_predictions = np.zeros(len(data), dtype=int)
            for test, held_x, model, permutations in folds:
                shuffled = held_x.copy()
                shuffled[:, index] = held_x[permutations[repeat], index]
                shuffled_predictions[test] = (model.predict_proba(shuffled)[:, 1] >= 0.5).astype(int)
            scores.append(f1_score(labels, shuffled_predictions, average="macro", zero_division=0))
        importance.append((name, observed - float(np.mean(scores))))
    return sorted(importance, key=lambda x: (-x[1], x[0]))


def plot(importance, output, overwrite=False):
    if output.exists() and not overwrite:
        raise ValueError("Refusing to overwrite an existing figure")
    top = importance[:10][::-1]
    fig, ax = plt.subplots(figsize=(11, 6.4), layout="constrained")
    values = [value * 100 for _, value in top]
    bars = ax.barh([describe(name) for name, _ in top], values, color="#176b87")
    ax.axvline(0, color="#444444", linewidth=0.8)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
    ax.set_xlabel("Mean decrease in held-out macro-F1 (percentage points)")
    ax.set_title("SOC telemetry: top non-command features\n"
                 "Within-session held-out permutation, 30 repeats; exploratory, not causal",
                 loc="left", fontweight="bold", fontsize=12)
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    ax.margins(x=0.16)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    importance = calculate(args.experiment.resolve())
    plot(importance, args.output.resolve(), args.overwrite)
    for name, value in importance[:10]:
        print(f"{name}: {value * 100:.3f} macro-F1 percentage points")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
