"""Calibrate on old fold 0, then report exposed SecEval diagnostics without retuning."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import semantic_checker as checker

ROOT = Path(__file__).resolve().parent
EXTERNAL = ROOT.parent / "cti_external_validation_20260918"
MODELS = ["llama", "qwen"]
SUPPORTS = [0, .25, .5, .75, .9]
MARGINS = [0, .1, .25, .5]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return checker.sha(path)


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def map_unique(records):
    mapped = {r["id"]: r for r in records}
    require(len(mapped) == len(records), "Duplicate ID")
    return mapped


def verify_scores(name, score_path, receipt_path, qualification_path):
    """Bind exact scores to safe rows, frozen bridge, model and input audit."""
    audit = load(ROOT / "INPUT_AUDIT.json")
    require(audit["status"] == "PASS", "Input preparation did not pass")
    inputs_path = ROOT / f"{name}_inputs.jsonl"
    evaluation_path = ROOT / f"{name}_evaluation.jsonl"
    counts = audit["counts"][name]
    require(sha(inputs_path) == counts["safe_input_sha256"], "Safe inputs changed")
    require(sha(evaluation_path) == counts["evaluation_sha256"], "Evaluation records changed")
    require(sha(ROOT / "prepare_inputs.py") == audit["code_sha256"], "Preparation code changed")
    receipt = load(receipt_path)
    require(receipt["status"] == "COMPLETE", "NLI run incomplete")
    require(receipt["input_sha256"] == sha(inputs_path), "Receipt input mismatch")
    require(receipt["output_sha256"] == sha(score_path), "Receipt output mismatch")
    require(receipt["qualification_sha256"] == sha(qualification_path), "Qualification hash mismatch")
    require(receipt["code_sha256"] == sha(ROOT / "semantic_checker.py"), "Scorer code changed")
    require(receipt["model_id"] == checker.MODEL_ID and receipt["revision"] == checker.REVISION,
            "Wrong verifier/model revision")
    require(receipt["template"] == checker.TEMPLATE and receipt["labels"] == checker.LABELS,
            "Wrong hypothesis/label mapping")
    require(receipt["method"] == checker.METHOD and receipt["max_length"] == 512
            and receipt["truncation"] == "longest_first" and receipt["device"] == "cpu"
            and receipt["dtype"] == "float32", "Scoring method changed")
    original = load(ROOT / "NLI_QUALIFICATION_RECEIPT.json")
    require(receipt["model_files_sha256"] == original["model_files_sha256"], "Model bytes changed")
    # Schema-only engineering amendments may change code after the first smoke
    # qualification; this run's own qualification and later policy freeze bind
    # the exact current scorer bytes. Published model bytes must stay identical.
    qualification = load(qualification_path)
    cases = checker.qualification_cases()
    require(qualification["status"] == "PASS" and qualification["correct"] == 8
            and qualification["required_correct"] == 8, "Qualification failed")
    require(qualification["cases_sha256"] == checker.object_sha(cases), "Qualification cases changed")
    require(qualification["model_id"] == checker.MODEL_ID and qualification["revision"] == checker.REVISION
            and qualification["template"] == checker.TEMPLATE, "Qualification method changed")
    require(len(qualification["cases"]) == 8, "Qualification inventory mismatch")
    for reference, actual in zip(cases, qualification["cases"]):
        require(all(actual[k] == v for k, v in reference.items()) and actual["passed"] is True
                and actual["prediction"] == reference["expected"], "Qualification case mismatch")
    inputs = checker.validate_inputs(inputs_path)
    evaluations = read(evaluation_path)
    scores = read(score_path)
    by_input, by_eval, by_score = map_unique(inputs), map_unique(evaluations), map_unique(scores)
    expected_n = 500 if name == "calibration" else 1247
    require(len(evaluations) == expected_n == counts["all_questions"], "Wrong full evaluation inventory")
    require(set(by_score) == set(by_input) and len(scores) == counts["disagreement_union_questions"],
            "Score inventory differs from projected disagreement inventory")
    expected_required = {}
    for r in evaluations:
        require(set(r["models"]) == set(MODELS), "Incomplete generators")
        required = set()
        for m in MODELS:
            pair = r["models"][m]
            require(set(pair) == {"vanilla", "evidence"}, "Incomplete paired outputs")
            for entry in pair.values():
                valid = isinstance(entry["answer"], str) and len(entry["answer"]) == 1 and entry["answer"] in "ABCD"
                require(entry["valid"] is valid and type(entry["correct"]) is bool,
                        "Malformed answer validity/correctness")
                require(valid or not entry["correct"], "Invalid answer cannot be correct")
            if pair["vanilla"]["answer"] != pair["evidence"]["answer"]:
                required.update(x["answer"] for x in pair.values() if x["valid"])
        if required:
            expected_required[r["id"]] = required
    require(set(expected_required) == set(by_input), "Question selection is not exact answer-disagreement union")
    total_pairs = truncated = 0
    for i, inp in by_input.items():
        r = by_score[i]
        require(set(inp["required_options"]) == expected_required[i], "Required options mismatch")
        require(r["input_sha256"] == checker.object_sha(inp), "Per-row safe-input hash mismatch")
        options = set(inp["required_options"])
        require(set(r["options"]) == options and set(r["hypotheses"]) == options, "Scored option inventory mismatch")
        expected_facts = [{"index": j, "text_sha256": hashlib.sha256(fact["text"].encode()).hexdigest()}
                          for j, fact in enumerate(inp["evidence"])]
        require(r["facts"] == expected_facts, "Evidence index/text hash mismatch")
        for key, summary in r["options"].items():
            require(r["hypotheses"][key] == checker.TEMPLATE.format(question=inp["question"], option=inp["options"][key]),
                    "Wrong question/option hypothesis")
            facts = summary["per_fact"]
            require([v["fact_index"] for v in facts] == list(range(len(inp["evidence"]))), "Per-fact inventory mismatch")
            for v in facts:
                values = [v[k] for k in checker.LABELS]
                require(all(isinstance(x, (int, float)) and math.isfinite(x) and 0 <= x <= 1 for x in values)
                        and abs(sum(values)-1) < 1e-5, "Invalid NLI probabilities")
                require(v["prediction"] == checker.LABELS[max(range(3), key=lambda j: values[j])], "NLI argmax mismatch")
                require(type(v["input_tokens_before_truncation"]) is int and v["input_tokens_before_truncation"] > 0
                        and v["truncated"] is (v["input_tokens_before_truncation"] > 512), "Truncation metadata mismatch")
            best = max(range(len(facts)), key=lambda j: (facts[j]["entailment"], -j))
            require(summary["strongest_support_fact"] == best
                    and summary["max_entailment"] == facts[best]["entailment"]
                    and summary["max_contradiction"] == max(v["contradiction"] for v in facts)
                    and summary["contradiction_at_strongest_support"] == facts[best]["contradiction"],
                    "Support summary is not reproducible from actual facts")
            total_pairs += len(facts)
            truncated += sum(v["truncated"] for v in facts)
    require(total_pairs == counts["nli_pairs"] == receipt["scored_pairs"], "Scored pair count mismatch")
    require(truncated == receipt["truncated_pairs"] and receipt["dataset_rows_read"] == len(scores),
            "Run count/truncation receipt mismatch")
    return evaluations, by_score, receipt


def choose(evaluations, scores, policy):
    decisions = np.zeros((len(evaluations), 2), dtype=bool)
    if policy["always_baseline"]:
        return decisions
    for i, r in enumerate(evaluations):
        for j, model in enumerate(MODELS):
            base, ev = (r["models"][model][k] for k in ("vanilla", "evidence"))
            if not ev["valid"] or ev["answer"] == base["answer"]:
                continue
            option_scores = scores[r["id"]]["options"]
            new_support = option_scores[ev["answer"]]["max_entailment"]
            old_support = option_scores[base["answer"]]["max_entailment"] if base["valid"] else 0.0
            decisions[i, j] = new_support >= policy["support"] and new_support-old_support > policy["margin"]
    return decisions


def outcomes(evaluations):
    return tuple(np.asarray([[r["models"][m][condition]["correct"] for m in MODELS]
                             for r in evaluations], dtype=bool) for condition in ("vanilla", "evidence"))


def calibration_summary(base, evidence, decisions):
    selected = np.where(decisions, evidence, base)
    recovered = int((decisions & ~base & evidence).sum())
    harms = int((decisions & base & ~evidence).sum())
    return {"pooled_net_corrections": recovered-harms, "pooled_recoveries": recovered,
            "pooled_induced_errors": harms, "pooled_accepted_changes": int(decisions.sum()),
            "mean_gain_pp": float((selected.astype(float)-base).mean()*100),
            "models": {m: {"correct": int(selected[:, j].sum()), "accuracy_pct": float(selected[:, j].mean()*100),
                "recovered": int((decisions[:, j] & ~base[:, j] & evidence[:, j]).sum()),
                "induced_errors": int((decisions[:, j] & base[:, j] & ~evidence[:, j]).sum()),
                "accepted_changes": int(decisions[:, j].sum())} for j, m in enumerate(MODELS)}}


def rank_calibration(candidate):
    p, s = candidate["policy"], candidate["metrics"]
    return (s["pooled_net_corrections"], -s["pooled_induced_errors"], -s["pooled_accepted_changes"],
            math.inf if p["always_baseline"] else p["support"],
            math.inf if p["always_baseline"] else p["margin"])


def select_calibration(evaluations, scores):
    base, evidence = outcomes(evaluations)
    policies = [{"always_baseline": False, "support": s, "margin": m} for s in SUPPORTS for m in MARGINS]
    policies.append({"always_baseline": True, "support": None, "margin": None})
    candidates = [{"policy": p, "metrics": calibration_summary(base, evidence, choose(evaluations, scores, p))}
                  for p in policies]
    return max(candidates, key=rank_calibration), candidates


def calibrate(args):
    target = ROOT / "POLICY_FREEZE.json"
    require(not target.exists(), "Refusing to overwrite frozen policy")
    evaluations, scores, receipt = verify_scores("calibration", args.scores, args.receipt, args.qualification)
    winner, candidates = select_calibration(evaluations, scores)
    bound = [ROOT / "PROTOCOL.md", ROOT / "semantic_checker.py", Path(__file__), ROOT / "INPUT_AUDIT.json",
             ROOT / "prepare_inputs.py", ROOT / "calibration_inputs.jsonl", ROOT / "calibration_evaluation.jsonl",
             args.scores, args.receipt, args.qualification, ROOT / "NLI_QUALIFICATION_RECEIPT.json"]
    amendment = ROOT / "ENGINEERING_AMENDMENT.md"
    if amendment.exists():
        bound.append(amendment)
    require(all(p.parent.resolve() == ROOT.resolve() for p in bound), "Bound artifacts must reside in revision directory")
    freeze = {"status": "FROZEN_ON_OLD_CALIBRATION_ONLY", "created_utc": datetime.now(timezone.utc).isoformat(),
        "policy": winner["policy"], "selected_calibration_metrics": winner["metrics"], "all_candidates": candidates,
        "n_calibration": 500, "support_grid": SUPPORTS, "margin_grid": MARGINS,
        "selection_rule": "maximum pooled net corrections; ties fewer harms, fewer changes, higher support, higher margin; always-baseline has infinite thresholds",
        "policy_equation": "valid different evidence answer and new_support >= support and new_support - old_support > margin; invalid baseline support=0",
        "thresholds_shared_between_generators": True, "contradiction_is_not_a_primary_policy_threshold": True,
        "external_score_outputs_opened": False, "external_data_already_exposed_to_researchers": True,
        "calibration_artifacts": {"scores": args.scores.name, "receipt": args.receipt.name,
                                  "qualification": args.qualification.name},
        "files_sha256": {p.name: sha(p) for p in bound}, "calibration_receipt": receipt}
    checker.write_new(target, freeze)
    print(json.dumps({"status": freeze["status"], "policy": freeze["policy"], "calibration_metrics": winner["metrics"]}))


def bootstrap_weights(groups, replicates=5000, seed=20260918):
    groups = np.asarray(groups)
    rng = np.random.default_rng(seed)
    weights = np.zeros((replicates, len(groups)), dtype=np.float64)
    for group in sorted(set(groups)):
        indices = np.flatnonzero(groups == group)
        weights[:, indices] = rng.multinomial(len(indices), np.full(len(indices), 1/len(indices)), size=replicates)
    return weights/len(groups)


def interval(draws):
    return [float(v) for v in np.percentile(draws, [2.5, 97.5])]


def summarize(base, evidence, decisions, changed, weights):
    chosen = np.where(decisions, evidence, base)
    delta = chosen.astype(float)-base
    draws = weights @ delta * 100
    return {"models": {m: {"correct": int(chosen[:, j].sum()), "accuracy_pct": float(chosen[:, j].mean()*100),
        "delta_vs_baseline_pp": float(delta[:, j].mean()*100), "delta_ci95_pp": interval(draws[:, j]),
        "evidence_routes": int(decisions[:, j].sum()), "accepted_answer_changes": int((decisions[:, j] & changed[:, j]).sum()),
        "recoveries": int((decisions[:, j] & ~base[:, j] & evidence[:, j]).sum()),
        "induced_errors": int((decisions[:, j] & base[:, j] & ~evidence[:, j]).sum()),
        "rejected_useful_corrections": int((~decisions[:, j] & ~base[:, j] & evidence[:, j]).sum()),
        "prevented_errors": int((~decisions[:, j] & base[:, j] & ~evidence[:, j]).sum())} for j, m in enumerate(MODELS)},
        "mean_accuracy_pct": float(chosen.mean()*100), "mean_delta_vs_baseline_pp": float(delta.mean()*100),
        "mean_delta_ci95_pp": interval(draws.mean(axis=1))}


def evaluate(args):
    for filename in ("RESULTS.json", "revision_decisions.jsonl"):
        require(not (ROOT/filename).exists(), "Refusing to overwrite revision results")
    freeze = load(ROOT / "POLICY_FREEZE.json")
    require(freeze["status"] == "FROZEN_ON_OLD_CALIBRATION_ONLY", "Policy not frozen")
    for name, digest in freeze["files_sha256"].items():
        require(sha(ROOT/name) == digest, "Calibration/frozen code changed: " + name)
    evaluations, scores, receipt = verify_scores("external_diagnostic", args.scores, args.receipt, args.qualification)
    cal_files = freeze["calibration_artifacts"]
    cal, cal_scores, _ = verify_scores("calibration", ROOT/cal_files["scores"],
        ROOT/cal_files["receipt"], ROOT/cal_files["qualification"])
    expected, _ = select_calibration(cal, cal_scores)
    require(expected["policy"] == freeze["policy"] and expected["metrics"] == freeze["selected_calibration_metrics"],
            "Frozen calibration selection cannot be reproduced")
    ext_freeze = load(EXTERNAL/"SCIENTIFIC_FREEZE.json")
    require(sha(EXTERNAL/"policy_predictions.jsonl") == ext_freeze["files"]["policy_predictions.jsonl"], "Old comparison policies changed")
    old_policies = map_unique(read(EXTERNAL/"policy_predictions.jsonl"))
    ids = [r["id"] for r in evaluations]
    require(set(old_policies) == set(ids), "Old policy inventory mismatch")
    base, evidence = outcomes(evaluations)
    changed = np.asarray([[r["models"][m]["vanilla"]["answer"] != r["models"][m]["evidence"]["answer"]
                           for m in MODELS] for r in evaluations])
    decisions = {"baseline": np.zeros_like(base), "always_evidence": np.ones_like(base),
        "previous_utility": np.repeat(np.asarray([old_policies[i]["use_evidence"]["evidence_utility"] for i in ids])[:, None], 2, axis=1),
        "previous_relevance": np.repeat(np.asarray([old_policies[i]["use_evidence"]["relevance"] for i in ids])[:, None], 2, axis=1),
        "answer_change_nli": choose(evaluations, scores, freeze["policy"])}
    groups = np.asarray([r["source_group"] for r in evaluations])
    masks = {"all": np.ones(len(ids), dtype=bool), "attack_source": groups == "attck", "other_source": groups != "attck"}
    require(int(masks["attack_source"].sum()) == 287, "Source inventory mismatch")
    metrics, comparisons = {}, {}
    for subset, mask in masks.items():
        weights = bootstrap_weights(groups[mask])
        metrics[subset] = {"n": int(mask.sum()), "arms": {name: summarize(base[mask], evidence[mask], use[mask], changed[mask], weights)
                                                        for name, use in decisions.items()}}
        if subset == "all":
            revised = np.where(decisions["answer_change_nli"], evidence, base)
            for name, use in decisions.items():
                if name == "answer_change_nli":
                    continue
                diff = revised.astype(float)-np.where(use, evidence, base)
                draws = weights @ diff * 100
                comparisons[name] = {"model_difference_pp": {m: float(diff[:, j].mean()*100) for j, m in enumerate(MODELS)},
                    "model_ci95_pp": {m: interval(draws[:, j]) for j, m in enumerate(MODELS)},
                    "mean_difference_pp": float(diff.mean()*100), "mean_ci95_pp": interval(draws.mean(axis=1))}
    gains = [metrics["all"]["arms"]["answer_change_nli"]["models"][m]["delta_vs_baseline_pp"] for m in MODELS]
    status = ("EXPOSED_DIAGNOSTIC_POSITIVE_BOTH_MODELS" if min(gains) > 0 else
              "EXPOSED_DIAGNOSTIC_MIXED_OR_NO_GAIN" if max(gains) > 0 else "EXPOSED_DIAGNOSTIC_NO_POSITIVE_GAIN")
    result = {"status": status, "n": len(ids), "completed_utc": datetime.now(timezone.utc).isoformat(),
        "policy": freeze["policy"], "metrics": metrics, "revised_minus_comparator": comparisons,
        "bootstrap": {"replicates": 5000, "seed": 20260918,
            "method": "paired questions within fixed coarse-source counts, preserving both model outcomes; not source-cluster inference"},
        "scope": "EXPOSED_DEVELOPMENT_DIAGNOSTIC_ONLY", "independent_confirmation": False,
        "novelty_established": False, "human_review_complete": False,
        "disagreements_per_model": {m: int(changed[:, j].sum()) for j, m in enumerate(MODELS)},
        "verifier_cost": {k: receipt[k] for k in ("scored_pairs", "dataset_rows_read", "truncated_pairs", "inference_seconds", "total_seconds", "device")},
        "generator_cost_note": "Reuses archived answers from two generation conditions; this is not an equal-cost pre-generation gate comparison.",
        "policy_freeze_sha256": sha(ROOT/"POLICY_FREEZE.json"),
        "files_sha256": {p.name: sha(p) for p in (args.scores, args.receipt, args.qualification, ROOT/"external_diagnostic_evaluation.jsonl")},
        "claim_boundary": "Development results against released labels, unvalidated question-to-NLI adaptation, unchanged retrieval corpus, and no prospective novelty/efficacy claim."}
    checker.write_new(ROOT/"RESULTS.json", result)
    with (ROOT/"revision_decisions.jsonl").open("x", encoding="utf-8") as f:
        for i, r in enumerate(evaluations):
            f.write(json.dumps({"id": r["id"], "source_group": r["source_group"],
                "use_evidence": {arm: {m: bool(use[i,j]) for j,m in enumerate(MODELS)} for arm,use in decisions.items()},
                "models": r["models"]}) + "\n")
    print(json.dumps({"status": status, "policy": freeze["policy"], "results": metrics["all"]["arms"]["answer_change_nli"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["calibrate", "evaluate"])
    parser.add_argument("--scores", type=resolve, required=True)
    parser.add_argument("--receipt", type=resolve, required=True)
    parser.add_argument("--qualification", type=resolve, required=True)
    args = parser.parse_args()
    (calibrate if args.command == "calibrate" else evaluate)(args)


if __name__ == "__main__":
    main()
