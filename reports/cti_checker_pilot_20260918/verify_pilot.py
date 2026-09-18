"""Independent audit of frozen CTI routing pilot; never trains or selects a model.

Only calls implementation feature/threshold/top-k helpers for adversarial checks.
Routing reconstruction, source isolation, metrics, bootstrap checks and verdict
are independently implemented here. Writes REVIEW.json, not frozen artifacts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import traceback

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
MODELS = ("llama", "qwen")
ARMS = ("relevance", "relevance_options", "source_classifier", "question_utility", "evidence_utility")
COMPARATORS = ARMS[:-1]
CHECKS = Counter()


def require(value, description):
    if not value:
        raise AssertionError(description)
    CHECKS[description.split(":", 1)[0]] += 1


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def records(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def same(actual, expected, label):
    if isinstance(actual, (float, np.floating)):
        require(math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-9), label)
    else:
        require(actual == expected, label)


def pre_checks(review):
    frozen = load("FREEZE.json")
    for name, digest in frozen["sha256"].items():
        require(sha(ROOT / name) == digest, "frozen_hash:" + name)
    review["freeze_sha256"] = sha(ROOT / "FREEZE.json")
    review["freeze_created_utc"] = frozen["created_utc"]
    spec = importlib.util.spec_from_file_location("cti_pilot_audit_target", ROOT / "run_pilot.py")
    implementation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(implementation)
    data = records("data.jsonl")
    splits = load("SPLITS.json")
    require(len(data) == 2500 and len({r["id"] for r in data}) == 2500, "question_inventory")
    require([r["id"] for r in data] == [r["id"] for r in splits], "split_id_join")
    seen = set()
    groups_by_fold = {i: set() for i in range(5)}
    fold_counts = Counter()
    for row, split in zip(data, splits):
        require(row["source_group"] == split["source_group"], "split_source_group_join")
        require(split["fold"] in groups_by_fold, "valid_fold")
        fold_counts[split["fold"]] += 1
        groups_by_fold[split["fold"]].add(row["source_group"])
        question = re.sub(r"\s+", " ", row["question"].strip().casefold())
        options = tuple(sorted(re.sub(r"\s+", " ", s.strip().casefold()) for s in row["options"].values()))
        signature = (question, options)
        require(signature not in seen, "no_exact_question_options_duplicate")
        seen.add(signature)
        fake_logits = list(np.linspace(-1, 1, len(row["evidence"])))
        original = implementation.features(row, fake_logits)
        changed = copy.deepcopy(row)
        changed.update(id="TRAP", source_group="TRAP", eligible=not row["eligible"],
                       previously_exposed=not row["previously_exposed"], outcomes={"TRAP": 999},
                       source_url="TRAP", expected_output="TRAP", technique_id="TRAP",
                       option_support_scores={"A": 999}, source_pointer_relationship_evidence="TRAP",
                       dataset_stratum="TRAP", raw_output="TRAP", parsed_answer="TRAP")
        require(implementation.question_text(changed) == implementation.question_text(row), "forbidden_metadata_text_invariance")
        require(implementation.features(changed, fake_logits) == original, "forbidden_metadata_feature_invariance")
        require(bool(np.isfinite(list(original.values())).all()), "finite_numeric_features")
    for f in range(5):
        require(fold_counts[f] == 500, "outer_test_inventory")
        train = set().union(*(groups_by_fold[j] for j in range(5) if j not in {f, (f + 1) % 5}))
        validation, test = groups_by_fold[(f + 1) % 5], groups_by_fold[f]
        require(not (train & validation or train & test or validation & test), "train_validation_test_group_isolation")
    # Handconstructed contracts: lower coverage breaks equal-utility ties;
    # equal scores cannot make an allowed 15%-85% selection; mismatched harm
    # invalidates a gate; top-k resolves equal scores by ID, independently of outcomes.
    scores = np.array([3., 2., 1., 0.])
    target = np.array([[1., 1.], [0., 0.], [0., 0.], [0., 0.]])
    eligible = np.array([True, True, False, False])
    threshold, details = implementation.threshold(scores, target, eligible)
    require(threshold == 3 and details["feasible"] and details["evidence_use"] == .25, "threshold_lower_coverage_tie")
    threshold, details = implementation.threshold(np.ones(4), target, eligible)
    require(math.isinf(threshold) and not details["feasible"], "threshold_constant_score_fallback")
    target = np.array([[-1., -1.], [1., 1.], [0., 0.], [0., 0.]])
    threshold, details = implementation.threshold(scores, target, np.array([False, True, True, True]))
    require(math.isinf(threshold) and not details["feasible"], "threshold_mismatch_harm_fallback")
    require(implementation.top_k([.5, .5, .2], ["b", "a", "c"], 1).tolist() == [False, True, False], "top_k_deterministic_id_tie")
    require(not implementation.top_k([.5, .5, .2], ["b", "a", "c"], 0).any(), "top_k_zero")
    require(implementation.top_k([.5, .5, .2], ["b", "a", "c"], 3).all(), "top_k_all")
    review["pre_fit_checks"] = {"status": "PASS", "rows": len(data), "source_groups": len(set(r["source_group"] for r in data)),
                                "fold_sizes": dict(fold_counts), "numerical_features": len(original),
                                "exact_question_options_duplicates": 0, "fits_performed_by_auditor": 0}
    return data, splits


def post_checks(review, data, splits):
    predictions = records("predictions.jsonl")
    result, receipt = load("RESULTS.json"), load("FIT_RECEIPT.json")
    require([r["id"] for r in predictions] == [r["id"] for r in data], "prediction_id_join")
    require(receipt["predictions_sha256"] == sha(ROOT / "predictions.jsonl"), "prediction_hash")
    require(receipt["freeze_sha256"] == sha(ROOT / "FREEZE.json"), "receipt_freeze_hash")
    require(receipt["finished_utc"] > review["freeze_created_utc"], "fit_finished_after_freeze")
    for name in ("relevance_scores", "relevance_options_scores"):
        require(receipt[name + "_sha256"] == sha(ROOT / (name + ".jsonl")), "receipt_scorer_hash:" + name)
    require(len(receipt["folds"]) == 5, "fit_fold_count")
    fits = {r["fold"]: r for r in receipt["folds"]}
    for row, split in zip(predictions, splits):
        require(row["fold"] == split["fold"], "prediction_fold_join")
        require(set(row["scores"]) == set(ARMS), "score_arm_inventory")
        for arm in ARMS:
            cal = fits[row["fold"]]["calibration"][arm]
            expected = row["scores"][arm] >= cal["threshold"] if cal["feasible"] else False
            require(row["use_evidence"][arm] == expected, "routing_uses_frozen_calibration_threshold")
    for f in range(5):
        held = [p for p in predictions if p["fold"] == f]
        count = sum(p["use_evidence"]["evidence_utility"] for p in held)
        for arm in COMPARATORS:
            ranked = sorted(held, key=lambda p: (-p["scores"][arm], p["id"]))
            selected = {p["id"] for p in ranked[:count]}
            require(sum(p["use_evidence"][arm + "_matched"] for p in held) == count, "matched_fold_evidence_count")
            require(all(p["use_evidence"][arm + "_matched"] == (p["id"] in selected) for p in held), "matched_routing_outcome_free_rank")
    n = len(data)
    baseline = np.array([[r["outcomes"][m]["vanilla"] for m in MODELS] for r in data], dtype=float)
    evidence = np.array([[r["outcomes"][m]["evidence"] for m in MODELS] for r in data], dtype=float)
    delta = evidence - baseline
    eligibility = np.array([r["eligible"] for r in data])
    masks = {"all": np.ones(n, dtype=bool), "eligible": eligibility, "mismatch": ~eligibility,
             "excluding_prior_500": np.array([not r["previously_exposed"] for r in data])}
    controls = {"llama": {"all": (1618, 1767), "eligible": (970, 1257), "mismatch": (648, 510)},
                "qwen": {"all": (1571, 1629), "eligible": (970, 1189), "mismatch": (601, 440)}}
    for j, model in enumerate(MODELS):
        for cohort, pair in controls[model].items():
            same(int(baseline[masks[cohort], j].sum()), pair[0], "published_vanilla_count")
            same(int(evidence[masks[cohort], j].sum()), pair[1], "published_evidence_count")
    policies = {"always_vanilla": np.zeros(n, dtype=bool), "always_evidence": np.ones(n, dtype=bool)}
    policies.update({a: np.array([p["use_evidence"][a] for p in predictions]) for a in predictions[0]["use_evidence"]})
    require(set(policies) == set(result["metrics"]), "reported_policy_inventory")
    reconstructed = {}
    for arm, use in policies.items():
        answer = np.where(use[:, None], evidence, baseline)
        reconstructed[arm] = answer
        for cohort, mask in masks.items():
            metric = result["metrics"][arm][cohort]
            same(int(use[mask].sum()), metric["evidence_used_n"], "policy_evidence_count")
            same(float(use[mask].mean() * 100), metric["evidence_use_pct"], "policy_evidence_rate")
            for j, model in enumerate(MODELS):
                measured = {"n": int(mask.sum()), "correct": int(answer[mask, j].sum()),
                    "accuracy_pct": float(answer[mask, j].mean() * 100),
                    "delta_vs_vanilla_pp": float((answer - baseline)[mask, j].mean() * 100),
                    "recovered_wrong_answers": int((mask & use & (delta[:, j] > 0)).sum()),
                    "induced_mistakes": int((mask & use & (delta[:, j] < 0)).sum()),
                    "prevented_mistakes": int((mask & ~use & (delta[:, j] < 0)).sum()),
                    "lost_improvements": int((mask & ~use & (delta[:, j] > 0)).sum())}
                for field, actual in measured.items():
                    same(actual, metric[model][field], "reconstructed_policy_metric:" + field)
    # Independent aggregation via bincount, not the analysis program's sparse
    # matrix. Regenerate all intervals that enter the final decision.
    groups, inverse = np.unique([r["source_group"] for r in data], return_inverse=True)
    rng = np.random.default_rng(20260918)
    weights = rng.multinomial(len(groups), np.repeat(1 / len(groups), len(groups)), size=5000)
    def interval(values, mask):
        numerator = weights @ np.bincount(inverse, weights=values * mask, minlength=len(groups))
        denominator = weights @ np.bincount(inverse, weights=mask.astype(float), minlength=len(groups))
        return np.quantile(numerator / denominator * 100, [.025, .975]).tolist()
    candidate = reconstructed["evidence_utility"]
    core = {}
    for j, model in enumerate(MODELS):
        effect = candidate[:, j] - baseline[:, j]
        mismatch_interval = interval(effect, masks["mismatch"])
        reported = result["metrics"]["evidence_utility"]["mismatch"][model]["delta_ci95_pp"]
        require(np.allclose(mismatch_interval, reported, rtol=1e-10, atol=1e-9), "independent_mismatch_decision_bootstrap")
        core[model] = {
            "overall_gain_at_least_3pp": effect.mean() * 100 >= 3 - 1e-9,
            "retains_half_eligible_benefit": effect[eligibility].mean() >= .5 * delta[eligibility, j].mean() - 1e-11,
            "mismatch_loss_no_worse_than_2pp": effect[~eligibility].mean() * 100 >= -2 - 1e-9,
            "mismatch_ci_lower_above_minus5pp": mismatch_interval[0] > -5}
    added = {}
    for arm in COMPARATORS:
        for suffix in ("", "_matched"):
            differences = candidate - reconstructed[arm + suffix]
            reported = result["candidate_vs_comparator"][arm + suffix]
            for j, model in enumerate(MODELS):
                same(float(differences[:, j].mean() * 100), reported[model]["difference_pp"], "comparator_point_difference")
            same(float(differences.mean() * 100), reported["paired_model_average"]["difference_pp"], "comparator_average_difference")
        differences = candidate - reconstructed[arm + "_matched"]
        ci = interval(differences.mean(axis=1), masks["all"])
        require(np.allclose(ci, result["candidate_vs_comparator"][arm + "_matched"]["paired_model_average"]["ci95_pp"], rtol=1e-10, atol=1e-9), "independent_added_value_decision_bootstrap")
        added[arm] = {**{model + "_gain_at_least_1pp": differences[:, j].mean() * 100 >= 1 - 1e-9 for j, model in enumerate(MODELS)},
                      "paired_average_ci_positive": ci[0] > 0}
    core = {m: {k: bool(v) for k, v in checks.items()} for m, checks in core.items()}
    added = {m: {k: bool(v) for k, v in checks.items()} for m, checks in added.items()}
    require(core == result["core_checks"], "independent_core_gate_reconstruction")
    require(added == result["added_value_checks"], "independent_added_value_gate_reconstruction")
    core_pass = all(all(c.values()) for c in core.values())
    added_pass = all(all(c.values()) for c in added.values())
    expected = "METHOD_SPECIFIC_PILOT_SIGNAL" if core_pass and added_pass else "USEFUL_SELECTION_SIGNAL_ADDED_VALUE_UNPROVEN" if core_pass else "PILOT_CRITERIA_NOT_MET"
    require((core_pass, added_pass, expected) == (result["core_signal_pass"], result["added_value_pass"], result["status"]), "independent_final_decision")
    review["post_fit_checks"] = {"status": "PASS", "policies": len(policies), "reported_cohorts": list(masks),
        "decision_intervals_independently_regenerated": 2 + len(COMPARATORS), "method_status": expected,
        "predictions_sha256": sha(ROOT / "predictions.jsonl"), "results_sha256": sha(ROOT / "RESULTS.json"),
        "no_refitting_or_method_selection": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-post", action="store_true")
    args = parser.parse_args()
    review = {"reviewed_utc": datetime.now(timezone.utc).isoformat(),
              "auditor": "independent data/audit agent; independent reconstruction without refitting",
              "audit_script_sha256": sha(__file__),
              "limits": "Audit validates implementation and recorded arithmetic; it does not establish fresh-data generalization, novelty, stronger-checker superiority, or academic acceptance."}
    try:
        data, splits = pre_checks(review)
        available = all((ROOT / name).exists() for name in ("predictions.jsonl", "RESULTS.json", "FIT_RECEIPT.json"))
        if available:
            post_checks(review, data, splits)
            review["status"] = "PASS_PRE_AND_POST_FIT_AUDIT"
        else:
            require(not args.require_post, "post_fit_outputs_required")
            review["status"] = "PASS_PRE_FIT_AUDIT_POST_FIT_PENDING"
            review["post_fit_checks"] = {"status": "PENDING", "reason": "Final predictions, analysis, and fit receipt are not all available."}
    except Exception:
        review["status"] = "FAIL_AUDIT"
        review["error"] = traceback.format_exc()
    review["check_counts"] = dict(CHECKS)
    (ROOT / "REVIEW.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(review, indent=2))
    if review["status"] == "FAIL_AUDIT":
        raise SystemExit(1)


if __name__ == "__main__":
    with threadpool_limits(limits=4):
        main()
