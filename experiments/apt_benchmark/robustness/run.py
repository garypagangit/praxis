"""Run fixed development ablations with private models and aggregate reporting."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import time
import warnings

import joblib
import numpy as np
from scipy import sparse
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from .replay import Replay, load_events
from ..models import calibration_threshold, resolve_threshold


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def is_target(labels, target):
    return any(label == target or label.split(":", 1)[0].split(".", 1)[0] == target for label in labels)


def summarize(y, scores, observed, threshold):
    y = np.asarray(y, dtype=bool)
    scores = np.asarray(scores, dtype=float)
    observed = np.asarray(observed, dtype=bool)
    pred = (scores > threshold) & observed
    tp = int((pred & y).sum())
    fp = int((pred & ~y).sum())
    fn = int((~pred & y).sum())
    tn = int((~pred & ~y).sum())
    positive, negative = int(y.sum()), int((~y).sum())
    return {
        "n": len(y), "positive": positive, "negative": negative,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / positive if positive else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        "negative_label_flag_rate": fp / negative if negative else None,
        "roc_auc": float(roc_auc_score(y, scores)) if positive and negative else None,
        "average_precision": float(average_precision_score(y, scores)) if positive else None,
        "observed_targets": int(observed.sum()),
        "observation_coverage": float(observed.mean()) if len(y) else None,
        "unobserved_positive_targets": int((y & ~observed).sum()),
        "decision_rule": "score > threshold AND at least one target fragment observed",
    }


def report(result):
    lines = [f"# {result['dataset']} missing/delayed-log development experiments", "",
             "Fixed protocol; no new novelty claim. Event-time plus synthetic delays is not measured online latency.", "",
             "Negative means absence of this source technique label in the eligible target roster; it does not mean independently verified benign activity.", "",
             "Random conditions average three fixed perturbation seeds; other conditions are deterministic. Models and calibration thresholds stay fixed.", "",
             "## Qualification", "", f"- Context events: {result['events']:,}; eligible prediction targets: {result['eligible_targets']:,}.",
             f"- Input event SHA256: `{result['input_sha256']}`.",
             f"- Protocol SHA256: `{result['protocol_sha256']}`.",
             f"- Runtime: {result.get('runtime_seconds', 0):.2f} seconds.", ""]
    for target, value in result["targets"].items():
        lines += [f"## {target}", "", f"Status: **{value['status']}**. Support: `{json.dumps(value['support'], sort_keys=True)}`.", ""]
        if value["status"] != "COMPLETE":
            continue
        lines += ["| Condition | Model | F1 at 0.5 | Recall at frozen calibration threshold | Other-label flag rate | Observed target coverage |", "|---|---|---:|---:|---:|---:|"]
        groups = {}
        for row in value["results"]:
            groups.setdefault((row["condition"], row["arm"]), []).append(row)
        for (condition, arm), rows in groups.items():
            def mean(metric, key):
                values = [r[metric][key] for r in rows if r[metric][key] is not None]
                return f"{np.mean(values):.4f}" if values else "undefined"
            lines.append(f"| {condition} | {arm} | {mean('fixed_0_5', 'f1')} | {mean('calibrated', 'recall')} | {mean('calibrated', 'negative_label_flag_rate')} | {mean('calibrated', 'observation_coverage')} |")
        lines += ["", "Per-run confusion counts, precision, recall, F1, ROC-AUC and average precision are in RESULTS.json. Correlated source events and three corruption seeds do not provide a population confidence interval.", ""]
    lines += ["## Limits", "", "- AIT uses already-exposed development runs and author-rule labels. Grouped audit events are a new denominator; do not compare directly with the old line-level F1.",
              "- CasinoLimit uses annotated process-technique onset targets and other annotated techniques as negatives. It does not measure benign false positives or unseen campaign generalization.",
              "- Record-type deletion is not a physical sensor outage; the recent-history burst is a target-relative stress test.",
              "- No-observation targets are retained and forced to no alarm. This offline target roster does not implement a deployed trigger for invisible events.",
              "- Source timestamps stand in for native fragment availability. Later source events are excluded even when a decision waits.",
              "- Waiting at least the injected deterministic delay restores the clean view by construction; that recovery is a buffering control, not a learned-method success.",
              "- Fit/calibration/test are separated by run. Shared recipes, process-label inheritance and potential repeat players remain dependencies.",
              "- A clean-calibration 1% other-label budget can fail under corruption and run shift. Actual observed rates are reported; no guarantee is claimed."]
    return "\n".join(lines) + "\n"


def run(events_path, manifest_path, dataset, output, protocol_path, feature_cache=None):
    start = time.perf_counter()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    input_hash = sha256(events_path)
    if manifest.get("events_sha256") != input_hash:
        raise ValueError("Source manifest does not bind this event corpus")
    if feature_cache is not None:
        from .feature_cache import CachedReplay
        replay = CachedReplay(feature_cache, protocol, input_hash)
        if replay.manifest["source_manifest_sha256"] != sha256(manifest_path):
            raise ValueError("Feature cache source manifest differs from the fitted dataset manifest")
        events = replay.events
        source_event_count = replay.source_event_count
    else:
        events = load_events(events_path)
        replay = Replay(events, protocol["history"]["seconds"], protocol["history"]["max_events"])
        source_event_count = len(events)
    eligible = np.asarray([i for i, e in enumerate(events) if e.get("target_eligible", True)], dtype=int)
    indices = {split: np.asarray([i for i in eligible if events[i]["split"] == split], dtype=int)
               for split in ("fit", "development", "calibration", "test")}
    clean = protocol["conditions"][0]
    seed = protocol["classifier"]["random_state"]
    dimensions = protocol["text_features"]["hash_dimensions_per_block"]
    result = {
        "status": "RUNNING", "dataset": dataset,
        "events": source_event_count, "eligible_targets": len(eligible),
        "input_sha256": input_hash, "manifest_sha256": sha256(manifest_path),
        "protocol_sha256": sha256(protocol_path),
        "python": platform.python_version(), "sklearn": sklearn.__version__,
        "targets": {}, "no_population_guarantee": True,
        "private_manifest_status": manifest.get("status", "see private manifest"),
    }
    code_files = [Path(__file__), Path(__file__).with_name("replay.py"), Path(__file__).parents[1] / "models.py"]
    if feature_cache is not None:
        code_files.append(Path(__file__).with_name("feature_cache.py"))
        result["feature_cache_manifest_sha256"] = sha256(Path(feature_cache) / "MANIFEST.json")
    receipt = {"frozen_before_fit": True, "input_sha256": result["input_sha256"],
               "protocol": protocol, "protocol_sha256": result["protocol_sha256"],
               "code_sha256": {p.name: sha256(p) for p in code_files}}
    if feature_cache is not None:
        receipt["feature_cache_manifest_sha256"] = result["feature_cache_manifest_sha256"]
    save_json(output / "PRE_FIT_RECEIPT.json", receipt)
    save_json(output / "RESULTS.partial.json", result)
    # Matrices depend on inputs, never targets. Cache only the clean fit/cal views.
    cache = {}
    for family in ("generic_event", "semantic_event", "entity_context"):
        for split in ("fit", "calibration"):
            cache[(family, split)] = replay.matrix(indices[split], clean, seed, family, dimensions)
    train_conditions = [next(c for c in protocol["conditions"] if c["name"] == name)
                        for name in protocol["dropout_training"]["views"]]
    augmentation_seed = protocol["dropout_training"]["seed"]
    augmented = [replay.matrix(indices["fit"], c, augmentation_seed, "entity_context", dimensions)[0] for c in train_conditions]
    augmented_X = sparse.vstack(augmented, format="csr")
    del augmented
    fitted = {}
    for target in protocol["datasets"][dataset]["targets"]:
        y_all = np.asarray([is_target(e["labels"], target) for e in events], dtype=np.int8)
        support = {split: {"n": len(idx), "positive": int(y_all[idx].sum()), "negative": int(len(idx)-y_all[idx].sum())}
                   for split, idx in indices.items()}
        record = {"status": "RUNNING", "support": support, "models": {}, "results": []}
        result["targets"][target] = record
        if any(not support[s]["positive"] or not support[s]["negative"] for s in ("fit", "calibration", "test")):
            record["status"] = "UNSUPPORTED_BOTH_CLASSES_REQUIRED"
            continue
        for arm in protocol["models"]:
            family = "entity_context" if arm == "context_dropout" else arm
            X = augmented_X if arm == "context_dropout" else cache[(family, "fit")][0]
            y = np.tile(y_all[indices["fit"]], len(train_conditions)) if arm == "context_dropout" else y_all[indices["fit"]]
            params = {k: v for k, v in protocol["classifier"].items() if k != "type"}
            model = LogisticRegression(**params)
            fit_start = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                weights = np.full(len(y), 1 / len(train_conditions)) if arm == "context_dropout" else None
                model.fit(X, y, sample_weight=weights)
            if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                raise RuntimeError(f"Nonconverged fit: {dataset}/{target}/{arm}")
            Xcal, observed_cal = cache[(family, "calibration")]
            scores_cal = model.predict_proba(Xcal)[:, list(model.classes_).index(1)]
            scores_cal[~observed_cal] = 0
            threshold = calibration_threshold(y_all[indices["calibration"]], scores_cal, protocol["calibration"]["negative_label_fpr_budget"])
            model_path = output / f"{target}_{arm}.joblib"
            joblib.dump(model, model_path)
            record["models"][arm] = {"threshold": threshold, "fit_seconds": time.perf_counter()-fit_start, "model_sha256": sha256(model_path), "training_rows": len(y)}
            fitted[(target, arm)] = (model, resolve_threshold(threshold))
            print(f"fit {dataset} {target} {arm}: {len(y)} rows", flush=True)
        record["status"] = "FITTED"
    test_idx = indices["test"]
    test_runs = np.asarray([events[i]["run_id"] for i in test_idx])
    np.savez_compressed(output / "PRIVATE_TARGET_ROSTER.npz", event_ids=np.asarray([events[i]["event_id"] for i in test_idx]), run_ids=test_runs)
    for condition in protocol["conditions"]:
        seeds = protocol["seeds"] if condition["kind"] == "random" else [protocol["seeds"][0]]
        for corruption_seed in seeds:
            for family in ("generic_event", "semantic_event", "entity_context"):
                Xtest, observed = replay.matrix(test_idx, condition, corruption_seed, family, dimensions)
                arms = [family, "context_dropout"] if family == "entity_context" else [family]
                for target, record in result["targets"].items():
                    if record["status"] != "FITTED":
                        continue
                    labels = np.asarray([is_target(events[i]["labels"], target) for i in test_idx], dtype=np.int8)
                    for arm in arms:
                        model, threshold = fitted[(target, arm)]
                        scores = model.predict_proba(Xtest)[:, list(model.classes_).index(1)]
                        scores[~observed] = 0
                        row = {"condition": condition["name"], "seed": corruption_seed, "arm": arm, "deadline_seconds": condition.get("deadline", 0),
                               "fixed_0_5": summarize(labels, scores, observed, 0.5),
                               "calibrated": summarize(labels, scores, observed, threshold), "by_run": {}}
                        for run_id in sorted(set(test_runs)):
                            mask = test_runs == run_id
                            row["by_run"][run_id] = {"fixed_0_5": summarize(labels[mask], scores[mask], observed[mask], 0.5),
                                                    "calibrated": summarize(labels[mask], scores[mask], observed[mask], threshold)}
                        record["results"].append(row)
                        np.savez_compressed(output / f"PRIVATE_{target}_{arm}_{condition['name']}_{corruption_seed}.npz", y=labels, score=scores, observed=observed)
            print(f"scored {dataset} {condition['name']} seed {corruption_seed}", flush=True)
        save_json(output / "RESULTS.partial.json", result)
    for record in result["targets"].values():
        if record["status"] == "FITTED":
            record["status"] = "COMPLETE"
    result["status"] = "COMPLETE"
    result["runtime_seconds"] = time.perf_counter() - start
    save_json(output / "RESULTS.json", result)
    (output / "REPORT.md").write_text(report(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "dataset": dataset, "runtime_seconds": result["runtime_seconds"]}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset", choices=("ait", "casino"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--feature-cache", type=Path, help="Precomputed per-run causal features for corpora too large to materialize")
    args = parser.parse_args()
    run(args.events, args.manifest, args.dataset, args.output, args.protocol, args.feature_cache)
