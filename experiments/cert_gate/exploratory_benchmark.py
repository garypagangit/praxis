"""Fixed, offline score-only benchmark; no operational risk certificate is issued."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import time
import warnings

import joblib
import numpy as np

try:
    from .calibration import calibrate, apply_certificate
    from .feature_grouping import GROUPING_VERSION, feature_group_sha, exact_feature_sha
    from .scorers import LinearSVMScorer, serialize_features
except ImportError:  # Direct script invocation from the repository root.
    from calibration import calibrate, apply_certificate
    from feature_grouping import GROUPING_VERSION, feature_group_sha, exact_feature_sha
    from scorers import LinearSVMScorer, serialize_features


EXPECTED_SOURCE_SHA256 = "33f95305d1c42f8e615e4f94066119570859dee7eb086dff7c2273536c932ea3"
RELEASE = "RELEASED_EXPLORATORY_SCORE_ONLY"
GROUPING = "ipv4_normalized_feature_groups_v1"
ROLES = ("fit", "selection", "calibration", "test")
FRACTIONS = dict(zip(ROLES, (.4, .1, .3, .2)))
ARMS = ("KEEP_ALL", "ZERO_MARGIN", "PAC_SCORE_ONLY", "MARGINAL_CRC_FORMULA")
LABELS = {"Attack": 1, "Non-Attack": 0}
SOURCE_FILES = ("exploratory_benchmark.py", "feature_grouping.py", "scorers.py", "calibration.py")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def committed_inputs(protocol_path):
    """Require the operative files and prospective protocol to be committed."""
    root = Path(__file__).resolve().parents[2]
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    hashes = {}
    for path in [Path(__file__).with_name(name) for name in SOURCE_FILES] + [protocol_path]:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError("The prospective protocol must be inside the repository")
        relative = path.relative_to(root).as_posix()
        committed = subprocess.check_output(["git", "-C", str(root), "show", f"{head}:{relative}"])
        if committed != path.read_bytes():
            raise ValueError(f"Uncommitted operative bytes: {relative}")
        hashes[relative] = sha_bytes(committed)
    return {"git_commit": head, "committed_file_sha256": hashes}


def split_role(group_sha, seed):
    """Label-independent assignment using integer SHA256 cut points."""
    value = int(hashlib.sha256(f"{seed}|{group_sha}".encode("ascii")).hexdigest(), 16)
    size = 2 ** 256
    for role, numerator in (("fit", 4), ("selection", 5), ("calibration", 8)):
        if value < numerator * size // 10:
            return role
    return "test"


def build_splits(rows, held_ordinals, seed):
    """Exclude entire held-review and mixed-label groups before assignment."""
    grouped = defaultdict(list)
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("Label") not in LABELS:
            raise ValueError("Every row needs the original binary dataset label")
        grouped[feature_group_sha(row)].append(ordinal)
    held = set(held_ordinals)
    if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(rows) for i in held):
        raise ValueError("Invalid held-review source ordinal")
    records, excluded = [], []
    for group_sha, indices in grouped.items():
        labels = {LABELS[rows[i]["Label"]] for i in indices}
        reasons = []
        if len(labels) != 1:
            reasons.append("mixed_labels")
        if held.intersection(indices):
            reasons.append("held_human_review")
        record = {
            "group_sha256": group_sha, "source_ordinals": indices,
            "representative_ordinal": min(indices),
            "exact_feature_sha256": sorted({exact_feature_sha(rows[i]) for i in indices}),
        }
        if reasons:
            excluded.append({**record, "reasons": reasons})
        else:
            records.append({**record, "attack_label": labels.pop(), "role": split_role(group_sha, seed)})
    records.sort(key=lambda item: item["representative_ordinal"])
    excluded.sort(key=lambda item: item["representative_ordinal"])
    parts = {role: [g for g in records if g["role"] == role] for role in ROLES}
    if set(g["attack_label"] for g in parts["fit"]) != {0, 1}:
        raise ValueError("The fixed fitting split needs both classes; no seed search is allowed")
    if not parts["test"]:
        raise ValueError("The fixed test split is empty; no seed search is allowed")
    summary = {
        "source_rows": len(rows), "normalized_feature_groups": len(grouped),
        "exact_feature_groups": len({exact_feature_sha(row) for row in rows}),
        "held_review_rows": len(held), "excluded_groups_union": len(excluded),
        "excluded_rows_union": sum(len(g["source_ordinals"]) for g in excluded),
        "exclusion_reason_counts": {
            reason: {"groups": sum(reason in g["reasons"] for g in excluded),
                     "rows": sum(len(g["source_ordinals"]) for g in excluded if reason in g["reasons"])}
            for reason in ("mixed_labels", "held_human_review")
        },
        "retained_groups": len(records), "retained_rows": sum(len(g["source_ordinals"]) for g in records),
        "grouping_is_not_incident_or_campaign_independence": True,
        "splits": {},
    }
    for role, groups in parts.items():
        summary["splits"][role] = {
            "groups": len(groups), "rows": sum(len(g["source_ordinals"]) for g in groups),
            "attack_groups": sum(g["attack_label"] for g in groups),
            "nonattack_groups": sum(1 - g["attack_label"] for g in groups),
            "attack_rows": sum(len(g["source_ordinals"]) * g["attack_label"] for g in groups),
            "nonattack_rows": sum(len(g["source_ordinals"]) * (1 - g["attack_label"]) for g in groups),
        }
    return parts, {"retained_groups": records, "excluded_groups": excluded}, summary


def marginal_calibrate(attack_scores, alpha):
    """Existing marginal formula: expectation, without a 1-delta guarantee."""
    scores = np.asarray(attack_scores, dtype=float)
    if scores.ndim != 1 or not np.isfinite(scores).all() or not 0 < alpha < 1:
        raise ValueError("Invalid marginal calibration inputs")
    n = len(scores)
    k = math.floor(alpha * (n + 1))
    while k > 0 and k / (n + 1) > alpha:
        k -= 1
    if k == 0:
        return {"mode": "KEEP_ALL", "threshold": {"kind": "positive_infinity", "value": None},
                "n_attack": n, "alpha": alpha, "expectation_bound_under_assumptions": 0.0}
    threshold = float(np.partition(scores, n - k)[n - k])
    return {"mode": "MARGINAL_EXPECTATION_ONLY", "threshold": {"kind": "finite", "value": threshold},
            "n_attack": n, "alpha": alpha, "order_rank": n - k + 1,
            "expectation_bound_under_assumptions": k / (n + 1)}


def predictions(scores, pac, marginal):
    values = np.asarray(scores, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("Scorer returned invalid values")
    threshold = marginal["threshold"]["value"]
    return {
        "KEEP_ALL": np.zeros(len(values), dtype=bool),
        "ZERO_MARGIN": values > 0,
        "PAC_SCORE_ONLY": apply_certificate(pac, values, np.ones(len(values), dtype=bool)),
        "MARGINAL_CRC_FORMULA": np.zeros(len(values), dtype=bool) if marginal["mode"] == "KEEP_ALL" else values > threshold,
    }


def fraction(numerator, denominator):
    return None if denominator == 0 else float(numerator / denominator)


def classifier_metrics(labels, scores):
    y, predicted = np.asarray(labels, dtype=int), np.asarray(scores) < 0
    tp, fp = int(np.sum((y == 1) & predicted)), int(np.sum((y == 0) & predicted))
    fn, tn = int(np.sum((y == 1) & ~predicted)), int(np.sum((y == 0) & ~predicted))
    return {"n": len(y), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "F1": fraction(2 * tp, 2 * tp + fp + fn), "TPR": fraction(tp, tp + fn),
            "FPR": fraction(fp, fp + tn), "precision": fraction(tp, tp + fp),
            "decision": "attack iff benignness score < 0; zero margin is classifier non-attack"}


def suppression_metrics(labels, suppress):
    y, s = np.asarray(labels, dtype=int), np.asarray(suppress, dtype=bool)
    n_attack, n_benign = int(np.sum(y == 1)), int(np.sum(y == 0))
    attack_missed, benign_removed = int(np.sum(s & (y == 1))), int(np.sum(s & (y == 0)))
    return {"n": len(y), "attack_alerts": n_attack, "nonattack_alerts": n_benign,
            "attack_alerts_suppressed": attack_missed, "nonattack_alerts_suppressed": benign_removed,
            "attack_suppression_fraction": fraction(attack_missed, n_attack),
            "nonattack_suppression_fraction": fraction(benign_removed, n_benign),
            "all_alert_suppression_fraction": fraction(int(s.sum()), len(y))}


def bootstrap_rates(group_labels, representative_predictions, row_counts, row_suppressed, repetitions, seed):
    """Resample empirical feature groups; these are not population-risk CIs."""
    y, weights = np.asarray(group_labels, dtype=int), np.asarray(row_counts, dtype=int)
    n = len(y)
    if n == 0 or weights.shape != y.shape or np.any(weights < 1) or repetitions < 1:
        raise ValueError("Invalid empirical group resampling inputs")
    rng = np.random.default_rng(seed)
    draws = {f"{unit}__{arm}__{metric}": np.full(repetitions, np.nan)
             for unit in ("primary_unique_groups", "secondary_all_rows") for arm in ARMS
             for metric in ("attack_suppression_fraction", "nonattack_suppression_fraction")}
    for offset in range(0, repetitions, 100):
        count = min(100, repetitions - offset)
        selected = rng.integers(0, n, size=(count, n))
        selected_y = y[selected]
        for unit in ("primary_unique_groups", "secondary_all_rows"):
            mass = np.ones(n, dtype=int) if unit == "primary_unique_groups" else weights
            for arm in ARMS:
                removed = np.asarray(representative_predictions[arm], dtype=int) if unit == "primary_unique_groups" else np.asarray(row_suppressed[arm], dtype=int)
                if removed.shape != y.shape or np.any(removed < 0) or np.any(removed > mass):
                    raise ValueError("Invalid per-group suppression counts")
                for label, metric in ((1, "attack_suppression_fraction"), (0, "nonattack_suppression_fraction")):
                    selected_class = selected_y == label
                    denominator = np.sum(mass[selected] * selected_class, axis=1)
                    numerator = np.sum(removed[selected] * selected_class, axis=1)
                    out = np.full(count, np.nan)
                    np.divide(numerator, denominator, out=out, where=denominator > 0)
                    draws[f"{unit}__{arm}__{metric}"][offset:offset + count] = out
    summary = {"method": "percentile resampling of the finite empirical normalized-feature-group distribution",
               "interpretation": "Descriptive resampling variability only; not an incident/population confidence interval or an operational risk certificate. Zero observed errors can give a zero-width empirical band.",
               "repetitions": repetitions, "seed": seed, "groups": n, "bands": {}}
    for key, values in draws.items():
        finite = values[np.isfinite(values)]
        summary["bands"][key] = {"percentiles_2_5_and_97_5": None if len(finite) == 0 else np.quantile(finite, [.025, .975]).tolist(),
                                 "defined_resamples": len(finite), "undefined_resamples": repetitions - len(finite)}
    return summary, draws


def peak_memory():
    """OS-reported process-lifetime peak, including native allocations."""
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counter = Counters()
        counter.cb = ctypes.sizeof(counter)
        kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counter), counter.cb):
            raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
        return {"bytes": counter.PeakWorkingSetSize, "method": "Windows process-lifetime PeakWorkingSetSize"}
    import resource
    amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"bytes": int(amount if platform.system() == "Darwin" else amount * 1024), "method": "process-lifetime ru_maxrss"}


def validate_inputs(source_path, protocol_path, audit_path):
    protocol_raw, source_raw, audit_raw = protocol_path.read_bytes(), source_path.read_bytes(), audit_path.read_bytes()
    protocol, audit = json.loads(protocol_raw), json.loads(audit_raw)
    required = {"release_status", "seed", "split_fractions", "alpha", "delta", "bootstrap_repetitions", "expected_source_sha256", "expected_audit_sha256", "scorer_config_sha256", "grouping"}
    if not required.issubset(protocol) or protocol["release_status"] != RELEASE:
        raise ValueError("The exploratory score-only protocol is not released")
    if protocol["split_fractions"] != FRACTIONS or protocol["grouping"] != GROUPING:
        raise ValueError("Unexpected frozen split or grouping specification")
    if protocol["alpha"] != .01 or protocol["delta"] != .05 or protocol["bootstrap_repetitions"] != 10000:
        raise ValueError("Unexpected frozen risk/resampling settings")
    if isinstance(protocol["seed"], bool) or not isinstance(protocol["seed"], int) or not 0 <= protocol["seed"] <= 2 ** 32 - 1:
        raise ValueError("Invalid frozen seed")
    source_hash, audit_hash = sha_bytes(source_raw), sha_bytes(audit_raw)
    if source_hash != EXPECTED_SOURCE_SHA256 or source_hash != protocol["expected_source_sha256"]:
        raise ValueError("Source bytes do not match the frozen dataset")
    if audit_hash != protocol["expected_audit_sha256"] or audit.get("source_sha256") != source_hash:
        raise ValueError("Audit bytes/source binding do not match the protocol")
    rows = json.loads(source_raw)
    if not isinstance(rows, list) or not all(isinstance(row, dict) and row.get("Label") in LABELS for row in rows):
        raise ValueError("Invalid source dataset schema")
    sample = audit.get("sample", [])
    if len(sample) != 50 or audit.get("human_review", {}).get("cases") != 50:
        raise ValueError("Expected the frozen 50-case human-review holdout")
    held = []
    for case in sample:
        i = case["source_row_zero_based"]
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(rows):
            raise ValueError("Invalid review source ordinal")
        content = sha_bytes(canonical({k: v for k, v in rows[i].items() if k != "Label"}))
        if case["input_content_sha256"] != content or case["case_id"] != sha_bytes(f"{i}|{content}".encode()):
            raise ValueError("Review case does not bind to source content")
        held.append(i)
    if len(set(held)) != 50:
        raise ValueError("Review source ordinals are not unique")
    scorer = LinearSVMScorer(seed=protocol["seed"])
    if scorer.metadata()["config_sha256"] != protocol["scorer_config_sha256"]:
        raise ValueError("Scorer recipe differs from the frozen protocol")
    return rows, held, protocol, scorer, {"source_sha256": source_hash, "audit_sha256": audit_hash, "protocol_sha256": sha_bytes(protocol_raw)}


def run(source, protocol, audit, private_output, output):
    paths = [Path(p).resolve() for p in (source, protocol, audit, private_output, output)]
    source_path, protocol_path, audit_path, private, public = paths
    if private.exists() or public.exists():
        raise ValueError("Output directories must be new; preserve prior attempts")
    repo = Path(__file__).resolve().parents[2]
    if private.is_relative_to(repo) or private.is_relative_to(public) or public.is_relative_to(private):
        raise ValueError("Private artifacts must stay outside the repository and public output tree")
    rows, held, spec, scorer, bindings = validate_inputs(source_path, protocol_path, audit_path)
    source_freeze = committed_inputs(protocol_path)
    started, memory_start = time.perf_counter(), peak_memory()
    parts, split_manifest, split_summary = build_splits(rows, held, spec["seed"])
    private.mkdir(parents=True)
    public.mkdir(parents=True)
    write_json(private / "SPLIT_MANIFEST.json", split_manifest)
    fit_groups = parts["fit"]
    fit_started = time.perf_counter()
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        scorer.fit([rows[g["representative_ordinal"]] for g in fit_groups], [g["attack_label"] for g in fit_groups], split_role="fit")
    fit_warnings = [{"category": item.category.__name__, "message": str(item.message)} for item in captured_warnings]
    fit_seconds = time.perf_counter() - fit_started
    joblib.dump(scorer, private / "MODEL.joblib")
    scoring_times, scored = {}, {}

    def score_ordinals(role, ordinals):
        scores, latencies = [], []
        role_started = time.perf_counter()
        for i in ordinals:
            before = time.perf_counter()
            score = float(scorer.score([rows[i]])[0])
            latencies.append(time.perf_counter() - before)
            if not np.isfinite(score):
                raise ValueError("Nonfinite model output; no threshold or test result is valid")
            scores.append(score)
        scoring_times[role] = {"rows_actually_scored": len(ordinals), "elapsed_seconds": time.perf_counter() - role_started,
                               "per_row_latency_seconds": None if not latencies else {"mean": float(np.mean(latencies)), "median": float(np.median(latencies)), "p95": float(np.quantile(latencies, .95)), "min": float(min(latencies)), "max": float(max(latencies))}}
        np.savez_compressed(private / f"SCORES_{role}.npz", source_ordinals=np.asarray(ordinals, dtype=np.int64),
                            scores=np.asarray(scores), latency_seconds=np.asarray(latencies), labels=np.asarray([LABELS[rows[i]["Label"]] for i in ordinals], dtype=np.int8))
        return np.asarray(scores, dtype=float)

    for role in ("fit", "selection", "calibration"):
        scored[role] = score_ordinals(role, [g["representative_ordinal"] for g in parts[role]])
    cal_labels = np.asarray([g["attack_label"] for g in parts["calibration"]], dtype=int)
    attack_scores = scored["calibration"][cal_labels == 1]
    metadata = {**bindings, "purpose": "EXPLORATORY_SCORE_ONLY_NOT_OPERATIONAL_CERTIFICATION", "scorer_fit_sha256": scorer.metadata()["fit_sha256"], "calibration_scores_sha256": sha_bytes((private / "SCORES_calibration.npz").read_bytes()), "eligibility": "ALL_TRUE_SCORE_ONLY; full operational predicates are not applied"}
    pac = calibrate(attack_scores, alpha=spec["alpha"], delta=spec["delta"], metadata=metadata)
    marginal = marginal_calibrate(attack_scores, spec["alpha"])
    freeze = {"status": "FROZEN_BEFORE_TEST_SCORING", "created_utc": datetime.now(timezone.utc).isoformat(),
              **bindings, **source_freeze, "scorer": scorer.metadata(),
              "scorer_execution": "FITTED_FIXED_RECIPE_ON_FIT_REPRESENTATIVES", "fit_warnings": fit_warnings,
              "model_artifact_sha256": sha_bytes((private / "MODEL.joblib").read_bytes()),
              "split_manifest_sha256": sha_bytes((private / "SPLIT_MANIFEST.json").read_bytes()),
              "pac_formula": pac.to_dict(), "marginal_formula": marginal,
              "selection_used_for_tuning": False, "operational_certification": False}
    write_json(public / "CALIBRATION_FREEZE.json", freeze)
    # No test scores or test performance have been computed before this freeze.
    test_groups = parts["test"]
    test_ordinals = [i for g in test_groups for i in g["source_ordinals"]]
    test_scores = score_ordinals("test_all_rows", test_ordinals)
    test_labels = np.asarray([LABELS[rows[i]["Label"]] for i in test_ordinals], dtype=int)
    offsets = np.cumsum([0] + [len(g["source_ordinals"]) for g in test_groups])
    rep_positions = offsets[:-1]
    group_labels = np.asarray([g["attack_label"] for g in test_groups], dtype=int)
    primary_scores = test_scores[rep_positions]
    all_predictions = predictions(test_scores, pac, marginal)
    representative_predictions = {arm: values[rep_positions] for arm, values in all_predictions.items()}
    row_suppressed = {arm: np.asarray([int(values[a:b].sum()) for a, b in zip(offsets[:-1], offsets[1:])]) for arm, values in all_predictions.items()}
    group_counts = np.diff(offsets)
    bootstrap, bootstrap_draws = bootstrap_rates(group_labels, representative_predictions, group_counts,
                                                 row_suppressed, spec["bootstrap_repetitions"], spec["seed"])
    np.savez_compressed(private / "BOOTSTRAP_DRAWS.npz", **bootstrap_draws)
    np.savez_compressed(private / "TEST_PREDICTIONS.npz", source_ordinals=np.asarray(test_ordinals, dtype=np.int64),
                        group_index=np.repeat(np.arange(len(test_groups)), group_counts), representative_positions=rep_positions,
                        labels=test_labels, benignness_scores=test_scores, **{arm: values for arm, values in all_predictions.items()})
    results = {
        "status": "EXPLORATORY_SCORE_ONLY_COMPLETE_NO_OPERATIONAL_CERTIFICATION",
        "created_utc": datetime.now(timezone.utc).isoformat(), **bindings, **source_freeze,
        "operational_certification": False, "full_g0_satisfied": False,
        "human_review_completed": False, "published_model_reproduction": False, "novelty_claim": False,
        "interpretation": "Observed benchmark separability and suppression fractions only. Unknown dependence and label validity prevent a deployment risk certificate. Full provenance/severity/incident predicates remain unsupported; all-true eligibility here is an explicitly different score-only experiment.",
        "grouping": GROUPING, "grouping_implementation_version": GROUPING_VERSION,
        "split_summary": split_summary, "scorer": scorer.metadata(),
        "scorer_execution": "FITTED_FIXED_RECIPE_ON_FIT_REPRESENTATIVES", "fit_warnings": fit_warnings,
        "selection_used_for_tuning": False,
        "classifier": {
            **{role: classifier_metrics([g["attack_label"] for g in parts[role]], scored[role]) for role in ("fit", "selection", "calibration")},
            "test_primary_unique_groups": classifier_metrics(group_labels, primary_scores),
            "test_secondary_all_rows": classifier_metrics(test_labels, test_scores),
        },
        "suppression": {
            "primary_unique_groups": {arm: suppression_metrics(group_labels, representative_predictions[arm]) for arm in ARMS},
            "secondary_all_rows": {arm: suppression_metrics(test_labels, all_predictions[arm]) for arm in ARMS},
        },
        "pac_formula": pac.to_dict(), "marginal_formula": marginal, "bootstrap": bootstrap,
        "timing": {"fit_seconds": fit_seconds, "scoring": scoring_times,
                   "elapsed_seconds": time.perf_counter() - started, "meaning": "Descriptive single-run CPU timing including per-row scoring calls; no speed superiority claim"},
        "memory": {"before_fit_process_peak": memory_start, "final_process_peak": peak_memory(), "meaning": "Process-lifetime OS peak, includes imports/data and may include earlier work if called inside a long-lived process"},
        "platform": platform.platform(),
        "public_freeze_sha256": sha_bytes((public / "CALIBRATION_FREEZE.json").read_bytes()),
        "private_artifacts": {p.name: {"sha256": sha_bytes(p.read_bytes()), "bytes": p.stat().st_size} for p in sorted(private.iterdir()) if p.is_file()},
        "limitations": ["Dataset labels are unreviewed; 50 human-review cases and their groups were excluded, not adjudicated.",
                        "Normalized duplicate groups are not independent incidents or campaigns.",
                        "Mixed-label groups were excluded by a fixed pre-fit rule; this changes the evaluated population.",
                        "Lowest-ordinal group representatives define primary metrics; all retained test rows are a separate secondary denominator.",
                        "The selection split is scored for transparency but never selects a model, threshold, seed or feature recipe.",
                        "Study terms and full G0 requirements remain unresolved; exploratory access is not a claim of permission for redistribution or deployment.",
                        "Both calibration formulas are named by their mathematical assumptions; those assumptions have not been established for this dataset."],
    }
    write_json(public / "RESULTS.json", results)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "protocol", "audit", "private-output", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.protocol, args.audit, args.private_output, args.output)
    print(json.dumps({"status": result["status"], "operational_certification": False, "split_summary": result["split_summary"]}, indent=2))
