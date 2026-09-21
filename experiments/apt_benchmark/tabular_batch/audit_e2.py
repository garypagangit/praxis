"""Read-only independent audit of the E2 CPU latency necessary-condition pilot.

Reconstructs hashes/rosters, median arithmetic and saved probability contracts.
It does not rerun fitting, inference or timing and makes no quality claim.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np

from .audit_e3 import compare, digest, require


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def timer_source_check(path, protocol):
    """Inspect the bound source for actual predict/transform calls inside timers."""
    module = ast.parse(Path(path).read_text(encoding="utf-8"))
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "paired_predictions")
    require([arg.arg for arg in function.args.args] == ["stage_model", "screen_model", "imputer", "query"], "Timer accepts unexpected inputs")
    direct_predict_calls = []
    for parent in ast.walk(function):
        body = getattr(parent, "body", None)
        if not isinstance(body, list):
            continue
        for position, statement in enumerate(body):
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name) or statement.targets[0].id != "values":
                continue
            calls = [node for node in ast.walk(statement.value) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "predict_proba"]
            require(len(calls) == 1, "Recorded values do not call predict_proba")
            prediction = calls[0]
            require(len(prediction.args) == 1 and isinstance(prediction.args[0], ast.Call), "Prediction has no timed transform")
            transformed = prediction.args[0]
            require(ast.unparse(transformed) == "imputer.transform(query)", "Prediction transforms an unexpected batch")
            require(position > 0 and position + 1 < len(body), "Incomplete timer block")
            require(ast.unparse(body[position - 1]) == "started = clock()", "Prediction is not preceded by timer start")
            require(ast.unparse(body[position + 1]) == "elapsed = clock() - started", "Prediction is not followed by timer end")
            direct_predict_calls.append(statement.lineno)
    require(len(direct_predict_calls) == 2, "Expected separate warmup and measured prediction blocks")
    order_assignments = [node for node in ast.walk(function) if isinstance(node, ast.Assign) and
                         any(isinstance(target, ast.Name) and target.id == "orders" for target in node.targets)]
    require(len(order_assignments) == 1, "Missing fixed timing order")
    compare(ast.literal_eval(order_assignments[0].value), protocol["measured_pair_order"], "source_timing_order")
    return {"status": "PASS", "function": "paired_predictions", "prediction_call_lines": direct_predict_calls,
            "includes": ["fitted imputer.transform(query)", "actual model.predict_proba call"],
            "excludes": ["model/preprocessor fitting", "constructor/checkpoint setup", "query-label scoring"],
            "limitation": "Static bound-source review; wall-clock execution was not independently replayed."}


def audit(prepared, run_root, protocol_path, e1_protocol_path):
    prepared, run_root = Path(prepared), Path(run_root)
    protocol_path, e1_protocol_path = Path(protocol_path), Path(e1_protocol_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    e1 = json.loads(e1_protocol_path.read_text(encoding="utf-8"))
    prefit = json.loads((run_root / "PREFIT_RECEIPT.json").read_text(encoding="utf-8"))
    fit = json.loads((run_root / "FIT_RECEIPT.json").read_text(encoding="utf-8"))
    aggregate = json.loads((run_root / "AGGREGATE.json").read_text(encoding="utf-8"))
    complete = json.loads((run_root / "COMPLETE.json").read_text(encoding="utf-8"))
    binding = prefit["binding"]
    require(canonical(binding) == prefit["binding_sha256"] == complete["binding_sha256"], "Pre-fit binding mismatch")
    require(prefit["fitting_started_at_receipt"] is False and prefit["heldout_outcomes_evaluated"] is False, "Invalid pre-fit scope")
    require(digest(protocol_path) == binding["protocol_sha256"] == aggregate["protocol_sha256"], "E2 protocol hash mismatch")
    require(digest(e1_protocol_path) == protocol["e1_protocol_sha256"] == binding["e1_protocol_sha256"], "Linked E1 protocol hash mismatch")
    source = Path(__file__).resolve().parent
    expected_sources = {"run_e2_latency.py", "run_e1.py", "model_backend.py", "requirementsfoundation.txt", "requirements_baselines.txt"}
    require(set(binding["code_sha256"]) == expected_sources, "Source hash roster differs")
    for name, claimed in binding["code_sha256"].items():
        require(digest(source / name) == claimed, f"Source changed after freeze: {name}")
    expected_artifacts = {"PREFIT_RECEIPT.json", "FIT_RECEIPT.json", "PREDICTIONS_PRIVATE.npz", "AGGREGATE.json"}
    require(set(complete["artifact_sha256"]) == expected_artifacts, "Completion artifact roster differs")
    for name, claimed in complete["artifact_sha256"].items():
        require(digest(run_root / name) == claimed, f"Artifact checksum differs: {name}")
    for field, name in (("prefit_receipt_sha256", "PREFIT_RECEIPT.json"), ("fit_receipt_sha256", "FIT_RECEIPT.json"), ("private_predictions_sha256", "PREDICTIONS_PRIVATE.npz")):
        require(aggregate[field] == digest(run_root / name), f"Aggregate receipt mismatch: {field}")
    data_path = prepared / "DATA.npz"
    manifest_path = prepared / "MANIFEST.json"
    data_hash, manifest_hash = digest(data_path), digest(manifest_path)
    require(all(item["data_npz_sha256"] == data_hash and item["manifest_sha256"] == manifest_hash for item in (protocol, e1, binding)), "Prepared input hash mismatch")
    require(aggregate["input_sha256"] == data_hash, "Aggregate input mismatch")
    with np.load(data_path, allow_pickle=False) as archive:
        X, y, split, groups, classes = (archive[key] for key in ("X", "y", "split", "group_sha256", "classes"))
    require(len(set(groups.tolist())) == len(groups), "Repeated prepared feature group")
    generator = np.random.default_rng(protocol["seed"])
    fit_indices = []
    for label in range(len(classes)):
        eligible = np.flatnonzero((split == 0) & (y == label))
        eligible = eligible[np.argsort(groups[eligible], kind="stable")]
        fit_indices.extend(generator.choice(eligible, size=protocol["samples_per_class"], replace=False).tolist())
    fit_indices = np.asarray(fit_indices, dtype=np.int64)
    # Label-blind query selection uses only the frozen test code and fingerprint.
    candidates = np.flatnonzero(split == 2)
    query_indices = np.asarray(sorted(candidates.tolist(), key=lambda index: hashlib.sha256(
        f"{protocol['seed']}|{groups[index]}".encode("ascii")).digest())[:protocol["query_rows"]], dtype=np.int64)
    require(not set(fit_indices).intersection(query_indices), "Fit and timing queries overlap")
    compare(binding["selected_fit_indices"], fit_indices.tolist(), "prefit_fit_indices")
    compare(binding["selected_fit_fingerprints"], groups[fit_indices].tolist(), "prefit_fit_fingerprints")
    compare(binding["query_indices"], query_indices.tolist(), "prefit_query_indices")
    compare(binding["query_fingerprints"], groups[query_indices].tolist(), "prefit_query_fingerprints")
    normal = classes.tolist().index(protocol["negative_class"])
    binary_counts = [int(np.count_nonzero(y[fit_indices] == normal)), int(np.count_nonzero(y[fit_indices] != normal))]
    compare(fit["training_binary_counts"], binary_counts, "binary_training_counts")
    require(aggregate["selected_fit_rows"] == len(fit_indices) and aggregate["query_rows"] == len(query_indices), "Aggregate row count differs")
    cv_winners = {}
    for model in ("xgboost", "lightgbm"):
        recorded = fit["tree_selection"][model]
        grid = e1["model_grids"][model]
        require(len(recorded["candidates"]) == len(grid), "CV candidate count differs")
        means = []
        for candidate, params in zip(recorded["candidates"], grid):
            compare(candidate["parameters"], params, "CV_parameters")
            scores = candidate["fold_macro_f1"]
            require(len(scores) == e1["n_splits"] and all(np.isfinite(value) and 0 <= value <= 1 for value in scores), "Invalid inner-CV scores")
            mean = sum(scores) / len(scores)
            compare(candidate["mean_macro_f1"], mean, "CV_mean")
            means.append(mean)
        index = max(range(len(means)), key=lambda index: means[index])
        require(recorded["selected_candidate_index"] == index, "Inner-CV candidate winner differs")
        compare(recorded["selected_parameters"], grid[index], "selected_parameters")
        compare(recorded["selected_mean_macro_f1"], means[index], "selected_CV_mean")
        require(recorded["selection_data"] == "selected fit support only", "CV scope differs")
        cv_winners[model] = means[index]
    winner = max(("xgboost", "lightgbm"), key=lambda model: cv_winners[model])
    require(fit["selected_gbdt"] == aggregate["selected_gbdt"] == winner, "GBDT winner differs")
    compare(aggregate["selected_gbdt_parameters"], fit["tree_selection"][winner]["selected_parameters"], "aggregate_GBDT_parameters")
    backend = fit["screen_backend"]
    require(backend["model_id"] == protocol["screen_model"] == aggregate["screen_model"], "Screen model differs")
    require(backend["checkpoint_verified"] is True and backend["fitted"] is True, "Screen checkpoint/fit receipt invalid")
    require(backend["constructor_settings"]["n_estimators"] == protocol["screen_n_estimators"], "Screen ensemble differs")
    checkpoint = Path(backend["constructor_settings"]["model_path"])
    require(checkpoint.stat().st_size == backend["checkpoint"]["size_bytes"] and digest(checkpoint) == backend["checkpoint"]["sha256"], "Cached checkpoint differs from receipt")
    require(binding["device"] == aggregate["device"] == backend["device"]["selected_device"] == "cpu", "CPU device bindings differ")
    require(binding["cpu_threads"] == aggregate["cpu_threads"] == protocol["cpu_threads"], "CPU thread binding differs")
    require(aggregate["torch_interop_threads"] == protocol["torch_interop_threads"], "Interop thread binding differs")
    compare(aggregate["versions"], binding["versions"], "version_receipt")
    with np.load(run_root / "PREDICTIONS_PRIVATE.npz", allow_pickle=False) as archive:
        predictions = {key: archive[key] for key in archive.files}
    for name, expected in (("query_indices", query_indices), ("query_fingerprints", groups[query_indices]),
                           ("selected_fit_indices", fit_indices), ("selected_fit_fingerprints", groups[fit_indices]),
                           ("stage_classes", np.arange(len(classes))), ("screen_classes", np.arange(2))):
        require(np.array_equal(predictions[name], expected), f"Prediction archive alignment differs: {name}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        imputation = np.nanmedian(X[fit_indices], axis=0)
    imputation[np.isnan(imputation)] = 0
    require(np.allclose(predictions["imputer_statistics"], imputation, rtol=0, atol=0), "Imputer medians differ from selected fit rows")
    probability_checks = {}
    for name, columns in (("full_stage_probabilities", len(classes)), ("screen_probabilities", 2)):
        values = predictions[name]
        require(values.shape == (protocol["measured_repeats"], protocol["query_rows"], columns), f"Measured probability shape differs: {name}")
        require(np.isfinite(values).all() and np.all((values >= 0) & (values <= 1)) and np.allclose(values.sum(axis=2), 1, atol=1e-5), f"Malformed measured probabilities: {name}")
        probability_checks[name] = {"shape": list(values.shape), "maximum_repeat_absolute_difference": float(np.max(np.abs(values - values[0])))}
    timing = aggregate["timing"]
    compare(timing["measured_order"], protocol["measured_pair_order"], "timing_order")
    medians = {}
    for name in ("full_stage", "screen_alone"):
        values = timing["measured_seconds"][name]
        require(len(values) == 3 and all(np.isfinite(value) and value > 0 for value in values), "Invalid measured durations")
        require(np.isfinite(timing["warmup_seconds"][name]) and timing["warmup_seconds"][name] > 0, "Invalid warmup duration")
        medians[name] = sorted(values)[1]
    target = medians["full_stage"] / protocol["required_speedup"]
    passed = medians["screen_alone"] <= target
    decision = {"full_stage_median_seconds": medians["full_stage"], "screen_alone_median_seconds": medians["screen_alone"],
                "required_screen_max_seconds": target, "required_speedup": protocol["required_speedup"],
                "observed_optimistic_serial_cascade_speedup_ceiling": medians["full_stage"] / medians["screen_alone"],
                "necessary_speed_condition_passed": passed,
                "status": "NECESSARY_CONDITION_PASS_ONLY" if passed else "CPU_CANDIDATE_FAILS_NECESSARY_SPEED_CONDITION",
                "interpretation": "Measured CPU configuration only; not a full cascade, quality frontier, statistical timing guarantee, or GPU result."}
    compare(aggregate["decision"], decision, "latency_decision")
    for flag in ("heldout_classification_outcomes_evaluated", "full_cascade_evaluated", "gpu_evaluated"):
        require(aggregate[flag] is False, f"Unsupported scope claim: {flag}")
    return {"schema_version": 1, "audit_status": "PASS", "run_status": "COMPLETE", "experiment": protocol["experiment"],
            "fit_rows": len(fit_indices), "query_rows": len(query_indices), "training_binary_counts": binary_counts,
            "selected_gbdt": winner, "decision": decision, "probability_checks": probability_checks,
            "timer_source_review": timer_source_check(source / "run_e2_latency.py", protocol),
            "screen_to_stage_median_runtime_ratio": medians["screen_alone"] / medians["full_stage"],
            "artifact_hashes": complete["artifact_sha256"],
            "verified": ["Pre-fit binding, source/input/protocol/checkpoint/artifact hashes", "Fit support and label-blind timing query reconstruction",
                         "Binary training counts and inner-CV arithmetic/selection", "Training-only imputation medians",
                         "Three measured probability matrices per model", "Alternating timing order, medians and necessary-speed arithmetic"],
            "limitations": ["No fitting, model-inference replay, timing replay or query-label quality evaluation was performed by this auditor.",
                            "Source inspection establishes timer placement, not an independent measurement of elapsed time.",
                            "Result applies only to this warm CPU configuration; no GPU or full cascade claim."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol_e2_latency.json"))
    parser.add_argument("--e1-protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a new audit output file")
    result = audit(args.prepared, args.run, args.protocol, args.e1_protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"audit_status": result["audit_status"], "decision": result["decision"], "output": str(args.output)}, indent=2))
