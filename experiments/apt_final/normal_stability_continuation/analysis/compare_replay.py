"""Exact private comparison of interrupted attempt 1 and a completed replay.

No cloud calls, fitting, scoring, or scientific artifact changes. Omit final
results to run an explicitly labeled self-check, not a completed replay claim.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
import math
from pathlib import Path

IDENTITY = ("dataset", "fold", "encoder_seed", "bank_seed", "strategy", "representation", "condition")
BINDINGS = ("source_commit", "registration_sha256", "config_sha256", "data_manifest_sha256", "device", "knn_device")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique)


def expected_grid(config):
    axes = [config["datasets"], [f["name"] for f in config["folds"]], config["encoder_seeds"],
            config["bank_seeds"], list(config["strategies"]), config["representations"], list(config["conditions"])]
    if any(not axis or len(set(axis)) != len(axis) for axis in axes):
        raise ValueError("Configuration axes must be nonempty and unique")
    return set(product(*axes))


def exact(left, right, path="metrics"):
    if isinstance(left, bool) or isinstance(right, bool):
        if type(left) is not type(right) or left != right:
            raise ValueError("Changed " + path)
    elif isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not math.isfinite(left) or not math.isfinite(right) or left != right:
            raise ValueError("Changed/nonfinite " + path)
    elif isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            raise ValueError("Changed metric field inventory at " + path)
        for key in sorted(left):
            exact(left[key], right[key], path + "." + key)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise ValueError("Changed list length at " + path)
        for i, (a, b) in enumerate(zip(left, right)):
            exact(a, b, path + "[" + str(i) + "]")
    elif type(left) is not type(right) or left != right:
        raise ValueError("Changed " + path)


def index_records(records, config, complete, label):
    allowed, found = expected_grid(config), {}
    for record in records:
        if set(record) != set(IDENTITY) | {"duplicate_of_encoder_seed", "metrics"}:
            raise ValueError(label + ": unexpected record fields")
        identity = tuple(record[key] for key in IDENTITY)
        if identity not in allowed:
            raise ValueError(label + ": unexpected experiment identity")
        if identity in found:
            raise ValueError(label + ": duplicate experiment identity")
        duplicate = (config["encoder_seeds"][0] if record["representation"] == "local_knn"
                     and record["encoder_seed"] != config["encoder_seeds"][0] else None)
        if record["duplicate_of_encoder_seed"] != duplicate:
            raise ValueError(label + ": incorrect local duplicate marker")
        exact(record["metrics"], record["metrics"])
        found[identity] = record
    if not found or (complete and set(found) != allowed):
        raise ValueError(label + ": missing configured identities")
    for identity, record in found.items():
        if record["duplicate_of_encoder_seed"] is not None:
            original = list(identity)
            original[2] = config["encoder_seeds"][0]
            if tuple(original) not in found:
                raise ValueError(label + ": missing original local copy")
            exact(record["metrics"], found[tuple(original)]["metrics"], label + ".local_copy")
    return found


def compare(normal, attack_partial, final, config, self_check=False):
    if normal.get("status") != "NORMAL_PHASE_COMPLETE":
        raise ValueError("Attempt 1 normal phase is not complete")
    if attack_partial.get("status") != "ATTACK_REPLAY_RUNNING":
        raise ValueError("Attempt 1 attack snapshot must identify interrupted replay")
    if not self_check and final.get("status") != "COMPLETE_FIXED_FAMILY_DEVELOPMENT":
        raise ValueError("Final candidate is not complete")
    for name in BINDINGS:
        if name not in normal or normal[name] != attack_partial.get(name):
            raise ValueError("Attempt 1 phase binding mismatch: " + name)
        if not self_check and normal[name] != final.get(name):
            raise ValueError("Final binding mismatch: " + name)
    phases = {}
    for phase, source in (("normal", normal), ("attack", attack_partial)):
        prior = index_records(source["records"], config, phase == "normal", "attempt1." + phase)
        current = index_records(source["records"] if self_check else final[phase + "_records"],
                                config, not self_check or phase == "normal", "final." + phase)
        if not set(prior) <= set(current):
            raise ValueError("Final replay is missing completed prior identities")
        for identity, record in prior.items():
            exact(record["metrics"], current[identity]["metrics"], phase + "/" + repr(identity))
            exact(record["duplicate_of_encoder_seed"], current[identity]["duplicate_of_encoder_seed"])
        phases[phase] = {"attempt1_completed_records": len(prior), "candidate_records": len(current),
                         "exactly_equal_overlapping_records": len(prior),
                         "new_final_records_without_attempt1_comparator": len(set(current) - set(prior)),
                         "duplicate_local_records_compared_not_independent": sum(r["duplicate_of_encoder_seed"] is not None for r in prior.values())}
    return {"status": "SELF_CHECK_ONLY_NO_NEW_RESULT" if self_check else "PASS_EXACT_REPLAY_OF_COMPLETED_RECORDS",
            "compared_identity_fields": list(IDENTITY), "matched_binding_fields": list(BINDINGS),
            "numeric_comparison": "Exact finite values, zero tolerance; numeric JSON spelling and int-vs-float representation ignored.",
            "metrics_compared": "Every nested metrics field, including counts, by-type rates, FPR, recall, precision, F1 and average precision where present.",
            "ignored_metadata": ["record order", "timestamps and elapsed/scoring durations", "paths and artifact inventories",
                                 "phase-specific status/label progress", "continuation-only receipts",
                                 "final decision: interrupted attempt1 has no completed decision"],
            "limits": "Aggregate equality does not re-audit scores, predictions, inference, registration or transport; those require their separate audits.",
            "independent_new_experiment": False, "phases": phases}


def run(attempt1_output, config_path, final_results=None):
    root, config_path = Path(attempt1_output), Path(config_path)
    inputs = {"attempt1_normal": root / "NORMAL_RESULTS.json", "attempt1_attack_partial": root / "ATTACK_RESULTS.partial.json",
              "config": config_path}
    if final_results is not None:
        inputs["final_results"] = Path(final_results)
    normal, attack, config = read(inputs["attempt1_normal"]), read(inputs["attempt1_attack_partial"]), read(config_path)
    if normal.get("config_sha256") != digest(config_path):
        raise ValueError("Configuration bytes differ from attempt 1")
    report = compare(normal, attack, read(final_results) if final_results else None, config, final_results is None)
    report.update(created_utc=datetime.now(timezone.utc).isoformat(), helper_sha256=digest(__file__),
                  input_sha256={label: digest(path) for label, path in inputs.items()})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt1-output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--final-results", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        raise FileExistsError("Comparison report already exists")
    try:
        report = run(args.attempt1_output, args.config, args.final_results)
    except (ValueError, KeyError, TypeError) as error:
        report = {"status": "FAIL_REPLAY_COMPARISON", "error": str(error), "helper_sha256": digest(__file__)}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    raise SystemExit(int(report["status"] == "FAIL_REPLAY_COMPARISON"))
