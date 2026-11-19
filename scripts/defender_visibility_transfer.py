"""Apply held-out attack-trained flow models to outside-login windows."""

import argparse
import json
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded
import defender_sequence_tuning as sequence
import defender_visibility_audit as audit


def transfer(attack, outside):
    rows = attack + outside
    groups = np.array([r["session"] for r in rows])
    labels = np.array([int(r["label"] == "ai") for r in rows])
    sessions = sorted({r["session"] for r in attack})
    if set(groups) != set(sessions) or len(audit.FLOW_COLUMNS) > len(sequence.BASE_COLUMNS):
        raise ValueError("Unexpected session set or flow feature count")
    if any(len(set(labels[groups == s])) != 1 for s in sessions):
        raise ValueError("Inconsistent labels within a session")
    features = np.log1p(np.array([[float(r[c]) for c in audit.FLOW_COLUMNS] for r in rows]))
    if not np.isfinite(features).all():
        raise ValueError("Non-finite flow features")
    in_attack = np.arange(len(rows)) < len(attack)
    probabilities = np.zeros(len(rows))
    for session in sessions:
        train = in_attack & (groups != session)
        test = groups == session
        probabilities[test] = sequence.fit_predict(
            features, groups, labels, train, test, sequence.CANDIDATES[0]
        )
    return labels, groups, probabilities


def run(experiment, audit_output, output):
    experiment, audit_output = experiment.resolve(), audit_output.resolve()
    output = expanded.safe_output(output, experiment, audit_output)
    own_hash = base.sha256(Path(__file__).resolve())
    _, _, _, _, _, provenance = sequence.prepare(experiment)
    manifest_path = audit_output / "extraction.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prior_path = audit_output / "results.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    context_path = audit_output / "outside_login.csv"
    if (manifest["script_sha256"] != base.sha256(Path(audit.__file__).resolve())
            or manifest["helper_sha256"] != audit.source_hashes()
            or manifest["provenance"] != provenance or prior["provenance"] != provenance
            or manifest["outside_login_sha256"] != base.sha256(context_path)):
        raise ValueError("Source experiments or audit code changed")
    attack = expanded.aggregate(base.rows(experiment / "windows30.csv"), 30)
    context = expanded.aggregate(base.rows(context_path), 30)
    labels, groups, probabilities = transfer(attack, context)
    attack_predictions = (probabilities[:len(attack)] >= 0.5).astype(int).tolist()
    if attack_predictions != prior["results"]["attack_flow_only"]["predictions"]:
        raise ValueError("Attack-trained models do not reproduce the prior held-out predictions")
    results = {}
    for name in ("before", "after", "combined"):
        indices = [i for i, row in enumerate(context, start=len(attack))
                   if name == "combined" or row["window"].startswith(name + "_")]
        subgroup = groups[indices]
        sessions = sorted(set(subgroup))
        value = sequence.summarize(labels[indices], subgroup, sessions, probabilities[indices])
        value["windows"] = len(indices)
        value["class_windows"] = {
            "human": int(np.sum(labels[indices] == 0)), "ai": int(np.sum(labels[indices] == 1))
        }
        value["class_sessions"] = {
            "human": sum(int(labels[groups == s][0] == 0) for s in sessions),
            "ai": sum(int(labels[groups == s][0] == 1) for s in sessions),
        }
        results[name] = value
    if base.sha256(Path(__file__).resolve()) != own_hash or manifest["helper_sha256"] != audit.source_hashes():
        raise ValueError("Code changed during transfer evaluation")
    output.mkdir(parents=True)
    doc = {"exploratory": True, "script_sha256": own_hash, "provenance": provenance,
           "audit_results_sha256": base.sha256(prior_path), "results": results}
    (output / "results.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Attack-trained flow models applied outside logins", "",
             "Each model was trained only on attack windows from other sessions and applied to "
             "the held-out session. Results are descriptive, not a significance test.", "",
             "| Period | Windows (human / AI) | Sessions (human / AI) | Macro-F1 | AI-labeled positive rate | Human-labeled positive rate |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        w, s = result["class_windows"], result["class_sessions"]
        lines.append(f"| {name} | {w['human']} / {w['ai']} | {s['human']} / {s['ai']} | "
                     f"{result['macro_f1']:.3f} | {result['ai_recall']:.3f} | "
                     f"{result['human_attack_window_fpr']:.3f} |")
    lines += ["", "Outside-login windows are not known to be benign; session labels do not establish "
              "who or what was active. Training and evaluation cover different periods, with uneven "
              "coverage and potentially different activities. This check cannot prove the absence "
              "of environment confounding."]
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved descriptive transfer results to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.experiment, args.audit_output, args.output)
