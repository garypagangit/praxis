"""Frozen development follow-up, preserving the previous split and examples."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import joblib
import numpy as np
from lightgbm import LGBMClassifier
from threadpoolctl import threadpool_limits

from ..host_history_exfil.run import CLASSES, PARAMS, SEEDS, metrics, sha, utc, write
from .features import build
from .policy import evaluate

ARMS = ["current_availability", "context_availability", "current_auth", "context_auth", "context_wrong_auth", "auth_availability_only", "availability_only"]
REPLAY_ARMS = ["current", "current_roles", "current_history", "current_roles_history", "current_roles_wrong_host_history", "roles_only"]


def read_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def fresh(path):
    if path.exists() and any(path.iterdir()):
        raise ValueError("Fresh output required")
    path.mkdir(parents=True, exist_ok=True)


def verify(protocol_path):
    spec = json.loads(protocol_path.read_text(encoding="utf-8"))
    for item in spec["bindings"]:
        if sha(item["path"]) != item["sha256"]:
            raise ValueError("Frozen source/artifact changed: " + item["path"])
    return spec


def views(d, a):
    current, context = d["current"], np.column_stack([d["current"], d["roles"], d["history"]])
    available, auth, wrong = a["availability"], a["auth"], a["wrong_auth"]
    return {"current_availability": np.column_stack([current, available]),
            "context_availability": np.column_stack([context, available]),
            "current_auth": np.column_stack([current, available, auth]),
            "context_auth": np.column_stack([context, available, auth]),
            "context_wrong_auth": np.column_stack([context, available, wrong]),
            "auth_availability_only": np.column_stack([available, auth]), "availability_only": available}


def prepare(protocol_path, output):
    spec = verify(protocol_path); fresh(output)
    d = read_npz(Path(spec["base_prepared"]) / "DATA.npz")
    events = read_npz(Path(spec["events"]) / "EVENTS.npz")
    observed = read_npz(Path(spec["events"]) / "OBSERVED.npz")
    a = build(d["start"], d["src"], events, observed)
    np.savez_compressed(output / "AUTH.npz", **a)
    counts = {}
    for k, name in enumerate(["fit", "calibration", "test"]):
        counts[name] = {}
        for c, label in enumerate(CLASSES):
            mask = (d["split"] == k) & (d["y"] == c)
            counts[name][label] = {"rows": int(mask.sum()), "source_observed_prior": int(np.sum(mask & (a["availability"][:, 0] > 0))),
                                  "any_auth_in_30m": int(np.sum(mask & np.any(a["auth"] > 0, axis=1))),
                                  "eligible_donor": int(np.sum(mask & (a["availability"][:, 6] > 0)))}
    write(output / "PREPARATION.json", {"created_utc": utc(), "protocol_sha256": sha(protocol_path), "auth_sha256": sha(output / "AUTH.npz"),
          "feature_names": a["feature_names"].tolist(), "availability_names": a["availability_names"].tolist(), "counts": counts,
          "latest_auth_before_flow_start": bool(np.all(a["latest_auth"] < d["start"])), "latest_wrong_auth_before_flow_start": bool(np.all(a["latest_wrong_auth"] < d["start"]))})
    print(json.dumps(counts), flush=True)


def arm_result(d, indices, y_cal, pc, pt, base, cal):
    y = d["y"][indices]
    roles = d["src_role"] * 4 + d["dst_role"]
    result = {"stage": metrics(y, pt), "decisions": evaluate(y_cal, pc[:, 3], roles[cal], y, pt[:, 3], roles[indices], base),
              "by_source_host": {}, "by_capture": {}, "role_strata": {}}
    # Source identity is used only for diagnostic reporting, never as a feature.
    for host in np.unique(d["src"][indices]):
        mask = d["src"][indices] == host
        if np.any(np.isin(y[mask], [2, 3])):
            result["by_source_host"][str(host)] = metrics(y[mask], pt[mask])
    for capture in np.unique(d["capture"][indices]):
        mask = d["capture"][indices] == capture
        result["by_capture"][str(capture)] = metrics(y[mask], pt[mask])
    for role in np.unique(roles[indices]):
        mask = roles[indices] == role
        result["role_strata"][str(role)] = metrics(y[mask], pt[mask])
    return result


def run(protocol_path, prepared, output, replay_only=False):
    spec = verify(protocol_path); fresh(output)
    d = read_npz(Path(spec["base_prepared"]) / "DATA.npz")
    a = None
    if not replay_only:
        receipt = json.loads((prepared / "PREPARATION.json").read_text(encoding="utf-8"))
        if receipt["protocol_sha256"] != sha(protocol_path) or receipt["auth_sha256"] != sha(prepared / "AUTH.npz"):
            raise ValueError("Auth preparation binding mismatch")
        a = read_npz(prepared / "AUTH.npz")
        matrices = views(d, a)
    receipt = {"started_utc": utc(), "protocol_sha256": sha(protocol_path), "mode": "prediction_replay" if replay_only else "auth_fits_and_replay", "cloud_compute_started": False}
    if a is not None:
        receipt["auth_preparation_sha256"] = sha(prepared / "PREPARATION.json")
        receipt["auth_data_sha256"] = sha(prepared / "AUTH.npz")
    write(output / "STARTED.json", receipt)
    results = []; clock = time.perf_counter()
    for seed in SEEDS:
        directory = output / str(seed); directory.mkdir()
        prior = read_npz(Path(spec["base_run"]) / str(seed) / "PREDICTIONS.npz")
        fit, cal, test = [prior[key] for key in ["fit_indices", "cal_indices", "test_indices"]]
        if not (np.all(d["split"][fit] == 0) and np.all(d["split"][cal] == 1) and np.all(d["split"][test] == 2)):
            raise ValueError("Prior split binding mismatch")
        if not np.array_equal(prior["cal_y"], d["y"][cal]) or not np.array_equal(prior["test_y"], d["y"][test]):
            raise ValueError("Prior labels differ")
        base = prior["current__test"].argmax(axis=1)
        saved = {"fit_indices": fit, "cal_indices": cal, "test_indices": test, "cal_y": d["y"][cal], "test_y": d["y"][test]}
        arms = {}
        for name in REPLAY_ARMS:
            pc, pt = prior[name + "__cal"], prior[name + "__test"]
            arms["prior_" + name] = arm_result(d, test, d["y"][cal], pc, pt, base, cal)
        if a is not None:
            for name in ARMS:
                print(f"FIT {seed} {name} {len(fit)}", flush=True)
                model = LGBMClassifier(**PARAMS, random_state=seed, n_jobs=4, deterministic=True, force_col_wise=True, verbosity=-1)
                model.fit(matrices[name][fit], d["y"][fit])
                if not np.array_equal(model.classes_, np.arange(4)):
                    raise ValueError("Missing fit class")
                pc, pt = model.predict_proba(matrices[name][cal]), model.predict_proba(matrices[name][test])
                arms[name] = arm_result(d, test, d["y"][cal], pc, pt, base, cal)
                saved[name + "__cal"], saved[name + "__test"] = pc, pt
                joblib.dump(model, directory / (name + ".joblib"), compress=3)
        np.savez_compressed(directory / "PREDICTIONS.npz", **saved)
        item = {"seed": seed, "fit_counts": np.bincount(d["y"][fit], minlength=4).tolist(), "arms": arms}
        write(directory / "METRICS.json", item)
        write(directory / "COMPLETE.json", {"files": {p.name: sha(p) for p in directory.iterdir() if p.is_file()}})
        results.append(item)
        print(f"SEED_COMPLETE {seed}", flush=True)
    receipt.update({"completed_utc": utc(), "elapsed_seconds": time.perf_counter() - clock, "models_fitted": 0 if replay_only else len(ARMS) * len(SEEDS), "saved_prediction_arms_replayed": len(REPLAY_ARMS) * len(SEEDS)})
    write(output / "SUMMARY.json", {"receipt": receipt, "seeds": results})
    write(output / "COMPLETE.json", {"summary_sha256": sha(output / "SUMMARY.json"), "started_sha256": sha(output / "STARTED.json")})
    print(json.dumps(receipt), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=["prepare", "fit", "replay"])
    parser.add_argument("--protocol", type=Path, required=True); parser.add_argument("--prepared", type=Path); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=4):
        if args.mode == "prepare": prepare(args.protocol, args.output)
        else: run(args.protocol, args.prepared, args.output, args.mode == "replay")


if __name__ == "__main__": main()
