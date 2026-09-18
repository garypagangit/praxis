"""Independent standard-library audit of the answer-change checker diagnostic.

Does not import the scorer or analyzer, call a model, or repeat bootstrap draws.
Reconstructs all decisions from per-fact probabilities, all calibration choices,
and all point metrics. Run only after POLICY_FREEZE.json and RESULTS.json exist.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

MODELS = ("llama", "qwen")
LABELS = ("contradiction", "entailment", "neutral")
SUPPORTS = (0, .25, .5, .75, .9)
MARGINS = (0, .1, .25, .5)
MODEL = "cross-encoder/nli-deberta-v3-xsmall"
REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"
TEMPLATE = 'The answer to the question "{question}" is "{option}".'
METHOD = "question_answer_template_individual_fact_nli_v1"
ARMS = ("baseline", "always_evidence", "previous_utility", "previous_relevance", "answer_change_nli")
CHECKS = Counter()


def demand(ok, message):
    CHECKS["assertions"] += 1
    if not ok:
        raise AssertionError(message)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def index(records):
    out = {}
    for record in records:
        demand(isinstance(record["id"], str) and record["id"] not in out, "Missing or repeated ID")
        out[record["id"]] = record
    return out


def close(actual, expected, label):
    if isinstance(expected, bool):
        demand(actual is expected, label)
    elif isinstance(expected, int):
        demand(type(actual) is int and actual == expected, label)
    elif isinstance(expected, float):
        demand(isinstance(actual, (float, int)) and not isinstance(actual, bool)
               and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10), label)
    elif isinstance(expected, dict):
        demand(set(actual) == set(expected), label + " keys")
        for key, value in expected.items():
            close(actual[key], value, label + "/" + key)
    else:
        demand(actual == expected, label)


def interval(value, label):
    demand(isinstance(value, list) and len(value) == 2 and
           all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in value)
           and -100 <= value[0] <= value[1] <= 100, label)
    CHECKS["intervals_structure_only"] += 1


def local_file(root, name):
    path = root / name
    demand(path.parent.resolve() == root.resolve(), "Unexpected nested/absolute result artifact: " + name)
    return path


def source_file(root, original, expected_sha256):
    """Prefer a byte-identical checkout copy; retain the historical path as fallback.

    The immutable preparation receipt records absolute paths from its execution
    machine. A matching repository-relative copy is sufficient for this audit;
    its exact expected SHA-256 is still mandatory. Existing wrong-byte copies
    fail immediately rather than silently using a different location.
    """
    repo = root.parents[1]
    normalized = original.replace("\\", "/")
    filename = Path(normalized).name
    archives = {f"full2500_{model}_query_only.jsonl.gz" for model in MODELS}
    candidates = [root / "source_archives" / filename] if filename in archives else []
    for marker in ("/reports/",):
        if marker in normalized:
            relative = normalized.split(marker, 1)[1]
            candidate = repo / marker.strip("/") / relative
            demand(candidate.resolve().is_relative_to(repo.resolve()), "Source fallback escapes checkout")
            candidates.append(candidate)
            break
    if filename in archives:
        candidates.append(Path(normalized))
    else:
        demand(bool(candidates), "Nonarchive source has no repository-relative location: " + original)
    for path in candidates:
        if path.is_file():
            demand(digest(path) == expected_sha256, "Source byte mismatch: " + str(path))
            return path
    raise FileNotFoundError("Required source unavailable in checkout or original location: " + original)


def qualification_cases():
    values = [
        ("ordinary_entailment_1", "A man is eating pizza.", "A man eats something.", "entailment"),
        ("ordinary_contradiction_1", "A man is eating pizza.", "No person is eating anything.", "contradiction"),
        ("ordinary_entailment_2", "The only operating system installed on this server is Linux.", "Linux is installed on this server.", "entailment"),
        ("ordinary_contradiction_2", "The only operating system installed on this server is Linux.", "Linux is not installed on this server.", "contradiction"),
    ]
    bridges = [
        ("template_entailment_1", "The operating system installed on this server is Linux, not Windows.", "Which operating system is installed on this server?", "Linux", "entailment"),
        ("template_contradiction_1", "The operating system installed on this server is Linux, not Windows.", "Which operating system is installed on this server?", "Windows", "contradiction"),
        ("template_entailment_2", "The server accepts connections on port 443 and does not accept connections on port 80.", "Which port accepts connections on the server?", "Port 443", "entailment"),
        ("template_contradiction_2", "The server accepts connections on port 443 and does not accept connections on port 80.", "Which port accepts connections on the server?", "Port 80", "contradiction"),
    ]
    values += [(i, p, TEMPLATE.format(question=q, option=o), e) for i, p, q, o, e in bridges]
    return [dict(id=i, premise=p, hypothesis=h, expected=e) for i, p, h, e in values]


def qualify(path):
    q = load(path)
    expected = qualification_cases()
    demand(q["status"] == "PASS" and q["correct"] == q["required_correct"] == 8, "Qualification did not pass eight cases")
    demand(q["cases_sha256"] == object_digest(expected), "Qualification cases changed")
    demand(q["model_id"] == MODEL and q["revision"] == REVISION and q["template"] == TEMPLATE, "Qualification model/template changed")
    demand(len(q["cases"]) == 8, "Qualification count changed")
    for source, scored in zip(expected, q["cases"]):
        demand(all(scored[k] == v for k, v in source.items()), "Qualification content changed")
        demand(scored["passed"] is True and scored["prediction"] == source["expected"], "Qualification prediction failed")


def verify_phase(root, phase, score_name, receipt_name, qualification_name, input_audit):
    inputs_file = root / (phase + "_inputs.jsonl")
    eval_file = root / (phase + "_evaluation.jsonl")
    score_file = local_file(root, score_name)
    receipt_file = local_file(root, receipt_name)
    qualification_file = local_file(root, qualification_name)
    counts = input_audit["counts"][phase]
    demand(digest(inputs_file) == counts["safe_input_sha256"], "Safe input digest changed")
    demand(digest(eval_file) == counts["evaluation_sha256"], "Evaluation digest changed")
    receipt = load(receipt_file)
    initial = load(root / "NLI_QUALIFICATION_RECEIPT.json")
    for k, v in {"status": "COMPLETE", "model_id": MODEL, "revision": REVISION, "template": TEMPLATE,
                 "method": METHOD, "max_length": 512, "truncation": "longest_first", "device": "cpu", "dtype": "float32"}.items():
        demand(receipt[k] == v, "Receipt contract mismatch: " + k)
    demand(receipt["labels"] == list(LABELS), "NLI labels changed")
    demand(receipt["model_files_sha256"] == initial["model_files_sha256"], "Published model bytes changed")
    for key, path in (("input_sha256", inputs_file), ("output_sha256", score_file),
                      ("qualification_sha256", qualification_file), ("code_sha256", root / "semantic_checker.py")):
        demand(receipt[key] == digest(path), "Scorer receipt digest mismatch: " + key)
    qualify(qualification_file)
    evaluations = rows(eval_file)
    inputs = index(rows(inputs_file))
    scores = index(rows(score_file))
    by_eval = index(evaluations)
    expected_n = 500 if phase == "calibration" else 1247
    demand(len(evaluations) == expected_n == counts["all_questions"], "Full question count incorrect")
    demand(set(inputs) == set(scores), "NLI input/output ID mismatch")
    expected_options, disagreements = {}, Counter()
    for row in evaluations:
        demand(set(row["models"]) == set(MODELS), "Generator inventory incomplete")
        required = set()
        for model in MODELS:
            pair = row["models"][model]
            demand(set(pair) == {"vanilla", "evidence"}, "Paired outcome inventory incomplete")
            for x in pair.values():
                valid = isinstance(x["answer"], str) and len(x["answer"]) == 1 and x["answer"] in "ABCD"
                demand(x["valid"] is valid and type(x["correct"]) is bool, "Invalid answer flags")
                demand(valid or not x["correct"], "Invalid answer marked correct")
            if pair["vanilla"]["answer"] != pair["evidence"]["answer"]:
                disagreements[model] += 1
                required.update(x["answer"] for x in pair.values() if x["valid"])
        if required:
            expected_options[row["id"]] = required
    demand(dict(disagreements) == counts["disagreements_per_model"], "Disagreement count mismatch")
    demand(set(inputs) == set(expected_options), "Inputs are not exact disagreement union")
    demand(len(inputs) == counts["disagreement_union_questions"] == receipt["dataset_rows_read"], "NLI row count mismatch")
    derived, pairs, truncated = {}, 0, 0
    for qid, inp in inputs.items():
        demand(set(inp) == {"id", "question", "options", "evidence", "required_options"}, "Unapproved scorer input fields")
        demand(set(inp["options"]) == set("ABCD"), "Options are not ABCD")
        demand(len(inp["required_options"]) == len(set(inp["required_options"])) and
               set(inp["required_options"]) == expected_options[qid], "Required option mismatch")
        demand(isinstance(inp["question"], str) and inp["question"].strip(), "Empty question")
        demand(bool(inp["evidence"]), "Empty evidence")
        scored = scores[qid]
        demand(scored["input_sha256"] == object_digest(inp), "Per-question input digest mismatch")
        demand(set(scored["options"]) == set(scored["hypotheses"]) == expected_options[qid], "Scored options incomplete")
        fact_refs = []
        for j, fact in enumerate(inp["evidence"]):
            demand(not(set(fact) - {"text", "kind", "score"}) and isinstance(fact["text"], str) and bool(fact["text"].strip()), "Unsafe or empty fact")
            fact_refs.append({"index": j, "text_sha256": hashlib.sha256(fact["text"].encode()).hexdigest()})
        demand(scored["facts"] == fact_refs, "Fact identities changed")
        derived[qid] = {}
        for option in inp["required_options"]:
            demand(isinstance(inp["options"][option], str) and inp["options"][option].strip(), "Required option empty")
            demand(scored["hypotheses"][option] == TEMPLATE.format(question=inp["question"], option=inp["options"][option]), "Question/option hypothesis changed")
            summary = scored["options"][option]
            facts = summary["per_fact"]
            demand([v["fact_index"] for v in facts] == list(range(len(inp["evidence"]))), "Fact-score inventory mismatch")
            for fact in facts:
                probs = [fact[k] for k in LABELS]
                demand(all(type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1 for v in probs)
                       and abs(sum(probs) - 1) < 1e-5, "Malformed NLI probability")
                demand(fact["prediction"] == LABELS[max(range(3), key=lambda k: probs[k])], "Probability argmax mismatch")
                demand(type(fact["input_tokens_before_truncation"]) is int and fact["input_tokens_before_truncation"] > 0, "Token count invalid")
                demand(fact["truncated"] is (fact["input_tokens_before_truncation"] > 512), "Truncation flag invalid")
                truncated += int(fact["truncated"])
            best = max(range(len(facts)), key=lambda k: facts[k]["entailment"])
            maximum = facts[best]["entailment"]
            demand(summary["max_entailment"] == maximum and summary["strongest_support_fact"] == best, "Option support not reproducible")
            demand(summary["max_contradiction"] == max(v["contradiction"] for v in facts)
                   and summary["contradiction_at_strongest_support"] == facts[best]["contradiction"], "Contradiction summary mismatch")
            derived[qid][option] = maximum
            pairs += len(facts)
    demand(pairs == counts["nli_pairs"] == receipt["scored_pairs"], "NLI pair count mismatch")
    demand(truncated == receipt["truncated_pairs"], "Total truncation mismatch")
    return evaluations, derived, receipt, inputs, {"questions": expected_n, "scored_questions": len(inputs), "pairs": pairs, "truncated": truncated}


def policy_decision(row, model, support, policy):
    old, new = (row["models"][model][c] for c in ("vanilla", "evidence"))
    if policy["always_baseline"] or not new["valid"] or old["answer"] == new["answer"]:
        return False
    new_score = support[row["id"]][new["answer"]]
    old_score = support[row["id"]][old["answer"]] if old["valid"] else 0.0
    return new_score >= policy["support"] and (new_score - old_score) > policy["margin"]


def cal_metrics(evaluations, supports, policy):
    per_model = {}
    for m in MODELS:
        c = Counter(correct=0, recovered=0, induced_errors=0, accepted_changes=0)
        for row in evaluations:
            b, e = (row["models"][m][v]["correct"] for v in ("vanilla", "evidence"))
            use = policy_decision(row, m, supports, policy)
            c["correct"] += int(e if use else b)
            c["recovered"] += int(use and not b and e)
            c["induced_errors"] += int(use and b and not e)
            c["accepted_changes"] += int(use)
        per_model[m] = {**dict(c), "accuracy_pct": c["correct"] / len(evaluations) * 100}
    recovery = sum(v["recovered"] for v in per_model.values())
    harm = sum(v["induced_errors"] for v in per_model.values())
    return {"pooled_net_corrections": recovery-harm, "pooled_recoveries": recovery,
            "pooled_induced_errors": harm, "pooled_accepted_changes": sum(v["accepted_changes"] for v in per_model.values()),
            "mean_gain_pp": (recovery-harm)/(len(evaluations)*2)*100, "models": per_model}


def rank(candidate):
    p, v = candidate["policy"], candidate["metrics"]
    return (v["pooled_net_corrections"], -v["pooled_induced_errors"], -v["pooled_accepted_changes"],
            math.inf if p["always_baseline"] else p["support"], math.inf if p["always_baseline"] else p["margin"])


def point_metrics(evaluations, decisions, arm):
    n = len(evaluations)
    models = {}
    for m in MODELS:
        counter = Counter({k: 0 for k in ("correct", "evidence_routes", "accepted_answer_changes", "recoveries", "induced_errors", "rejected_useful_corrections", "prevented_errors")})
        base_correct = 0
        for row in evaluations:
            old, new = (row["models"][m][v] for v in ("vanilla", "evidence"))
            b, e = old["correct"], new["correct"]
            use = decisions[row["id"]][arm][m]
            base_correct += b
            counter["correct"] += int(e if use else b)
            counter["evidence_routes"] += int(use)
            counter["accepted_answer_changes"] += int(use and old["answer"] != new["answer"])
            counter["recoveries"] += int(use and not b and e)
            counter["induced_errors"] += int(use and b and not e)
            counter["rejected_useful_corrections"] += int(not use and not b and e)
            counter["prevented_errors"] += int(not use and b and not e)
        models[m] = {**dict(counter), "accuracy_pct": counter["correct"]/n*100,
                     "delta_vs_baseline_pp": (counter["correct"]-base_correct)/n*100}
    return {"models": models, "mean_accuracy_pct": sum(x["correct"] for x in models.values())/(2*n)*100,
            "mean_delta_vs_baseline_pp": sum(x["delta_vs_baseline_pp"] for x in models.values())/2}


def audit(root):
    ext = root.parent / "cti_external_validation_20260918"
    frozen = load(root / "POLICY_FREEZE.json")
    result = load(root / "RESULTS.json")
    demand(frozen["status"] == "FROZEN_ON_OLD_CALIBRATION_ONLY", "Policy not frozen")
    for name, expected in frozen["files_sha256"].items():
        demand(digest(local_file(root, name)) == expected, "Changed frozen artifact: " + name)
    demand(result["policy_freeze_sha256"] == digest(root / "POLICY_FREEZE.json"), "Result bound to wrong policy")
    for name, expected in result["files_sha256"].items():
        demand(digest(local_file(root, name)) == expected, "Changed result input: " + name)
    input_audit = load(root / "INPUT_AUDIT.json")
    demand(input_audit["status"] == "PASS" and input_audit["scope"] == "EXPOSED_DEVELOPMENT_DATA_ONLY", "Input audit/scope failed")
    demand(digest(root / "prepare_inputs.py") == input_audit["code_sha256"], "Preparation code changed")
    resolved_sources = {original: source_file(root, original, receipt["sha256"])
                        for original, receipt in input_audit["source_files"].items()}
    demand(frozen["n_calibration"] == 500 and frozen["support_grid"] == list(SUPPORTS) and frozen["margin_grid"] == list(MARGINS), "Calibration search grid changed")
    demand(frozen["thresholds_shared_between_generators"] is True and frozen["external_score_outputs_opened"] is False
           and frozen["external_data_already_exposed_to_researchers"] is True
           and frozen["contradiction_is_not_a_primary_policy_threshold"] is True, "Declared selection boundary changed")
    cal_files = frozen["calibration_artifacts"]
    cal, cal_support, _, cal_inputs, cal_inventory = verify_phase(root, "calibration", cal_files["scores"], cal_files["receipt"], cal_files["qualification"], input_audit)
    candidates = []
    for s in SUPPORTS:
        for m in MARGINS:
            p = {"always_baseline": False, "support": s, "margin": m}
            candidates.append({"policy": p, "metrics": cal_metrics(cal, cal_support, p)})
    p = {"always_baseline": True, "support": None, "margin": None}
    candidates.append({"policy": p, "metrics": cal_metrics(cal, cal_support, p)})
    demand(len(frozen["all_candidates"]) == 21, "Expected all 20 thresholds plus baseline")
    for computed, published in zip(candidates, frozen["all_candidates"]):
        close(published, computed, "Calibration candidate")
    winning = max(candidates, key=rank)
    demand(winning["policy"] == frozen["policy"] == result["policy"], "Wrong selected calibration policy")
    close(frozen["selected_calibration_metrics"], winning["metrics"], "Selected calibration metrics")
    # Locate exact external score/receipt/qualification from hash-bound result files.
    external_receipts = []
    for name in result["files_sha256"]:
        if name.endswith(".json"):
            item = load(root / name)
            if item.get("status") == "COMPLETE" and item.get("input_sha256") == input_audit["counts"]["external_diagnostic"]["safe_input_sha256"]:
                external_receipts.append((name, item))
    demand(len(external_receipts) == 1, "Ambiguous external scorer receipt")
    receipt_name, receipt = external_receipts[0]
    frozen_time = datetime.fromisoformat(frozen["created_utc"].replace("Z", "+00:00"))
    external_time = datetime.fromisoformat(receipt["created_utc"].replace("Z", "+00:00"))
    demand(frozen_time.tzinfo is not None and external_time.tzinfo is not None
           and frozen_time < external_time, "External scoring receipt must follow the completed calibration policy freeze")
    score_names = [n for n, d in result["files_sha256"].items() if d == receipt["output_sha256"]]
    qual_names = [n for n, d in result["files_sha256"].items() if d == receipt["qualification_sha256"]]
    demand(len(score_names) == len(qual_names) == 1, "Unbound external scores/qualification")
    evaluations, supports, receipt, safe, inventory = verify_phase(root, "external_diagnostic", score_names[0], receipt_name, qual_names[0], input_audit)
    old_freeze = load(ext / "SCIENTIFIC_FREEZE.json")
    demand(digest(ext / "policy_predictions.jsonl") == old_freeze["files"]["policy_predictions.jsonl"], "Old policy file changed")
    previous = index(rows(ext / "policy_predictions.jsonl"))
    evaluation = index(evaluations)
    demand(set(previous) == set(evaluation), "Old policy IDs differ")
    # Independently bind external gold/outcomes and question/fact projection.
    gold = index(rows(ext / "sealed_labels.jsonl"))
    original_inputs = index(rows(ext / "test_inputs.jsonl"))
    demand(set(gold) == set(original_inputs) == set(evaluation), "External source inventory mismatch")
    predictions = rows(ext / "execution_outputs/predictions.jsonl")
    prediction_keys = set()
    for pred in predictions:
        condition = "evidence" if pred["condition"] == "relationship_evidence" else pred["condition"]
        key = (pred["id"], pred["model"], condition)
        demand(key not in prediction_keys, "Duplicate external generator output")
        prediction_keys.add(key)
        qid, model, condition = key
        demand(qid in evaluation and model in MODELS and condition in ("vanilla", "evidence"), "Unexpected external generator output")
        expected = {"answer": pred["parsed_answer"], "valid": pred["valid"], "correct": pred["parsed_answer"] == gold[qid]["answer"]}
        demand(evaluation[qid]["models"][model][condition] == expected, "External evaluation differs from original answer/gold")
    demand(len(prediction_keys) == 4988, "Incomplete generator inventory")
    for qid, inp in safe.items():
        original = original_inputs[qid]
        for field in ("question", "options"):
            demand(inp[field] == original[field], "Question/options projection changed")
        demand(inp["evidence"] == [{k: v for k, v in fact.items() if k in {"text", "kind", "score"}} for fact in original["evidence"]], "Evidence projection changed")
    for qid, row in evaluation.items():
        demand(row["source_group"] == gold[qid]["source"], "Source group differs from original labels")
    # Independent old-fold membership and outcome verification; safe projection is unchanged.
    pilot = root.parent / "cti_checker_pilot_20260918"
    old_data = index(rows(pilot / "data.jsonl"))
    fold = {r["id"] for r in load(pilot / "SPLITS.json") if r["fold"] == 0}
    demand(set(r["id"] for r in cal) == fold and len(fold) == 500, "Calibration no longer old fold zero")
    cal_by_id = index(cal)
    for model in MODELS:
        archives = [resolved_sources[p] for p in input_audit["source_files"] if p.replace("\\", "/").endswith(f"/full2500_{model}_query_only.jsonl.gz")]
        demand(len(archives) == 1, "Missing or ambiguous archived calibration source")
        archived = [json.loads(line) for line in gzip.decompress(archives[0].read_bytes()).decode("utf-8").splitlines() if line.strip()]
        demand(len(archived) == 5000, "Old generator archive inventory changed")
        seen = set()
        for raw in archived:
            if raw["id"] not in fold:
                continue
            condition = "evidence" if raw["condition"] == "relationship_evidence" else raw["condition"]
            key = (raw["id"], condition)
            demand(condition in ("vanilla", "evidence") and key not in seen, "Duplicate old calibration outcome")
            seen.add(key)
            answer = raw["parsed_answer"]
            expected = {"answer": answer, "valid": isinstance(answer, str) and len(answer) == 1 and answer in "ABCD",
                        "correct": answer == raw["expected_output"]}
            demand(raw["correct"] is expected["correct"] and cal_by_id[raw["id"]]["models"][model][condition] == expected,
                   "Calibration answer differs from archived generator output")
        demand(len(seen) == 1000, "Calibration archive pairing incomplete")
    for row in cal:
        original = old_data[row["id"]]
        demand(row["source_group"] == original["source_group"], "Calibration source differs")
        for m in MODELS:
            for c in ("vanilla", "evidence"):
                demand(row["models"][m][c]["correct"] == original["outcomes"][m][c], "Calibration correctness differs from old data")
        if row["id"] in cal_inputs:
            inp = cal_inputs[row["id"]]
            demand(inp["question"] == original["question"] and inp["options"] == original["options"], "Calibration projection changed")
            demand(inp["evidence"] == [{k: v for k, v in fact.items() if k in {"text", "kind", "score"}} for fact in original["evidence"]], "Calibration facts changed")
    decisions = {}
    for row in evaluations:
        qid = row["id"]
        decisions[qid] = {arm: {} for arm in ARMS}
        for m in MODELS:
            decisions[qid]["baseline"][m] = False
            decisions[qid]["always_evidence"][m] = True
            for arm, old in (("previous_utility", "evidence_utility"), ("previous_relevance", "relevance")):
                value = previous[qid]["use_evidence"][old]
                demand(type(value) is bool, "Previous routing not Boolean")
                decisions[qid][arm][m] = value
            decisions[qid]["answer_change_nli"][m] = policy_decision(row, m, supports, winning["policy"])
    saved_decisions = index(rows(root / "revision_decisions.jsonl"))
    demand(set(saved_decisions) == set(evaluation), "Decision output inventory differs")
    for qid, row in evaluation.items():
        demand(saved_decisions[qid] == {"id": qid, "source_group": row["source_group"], "use_evidence": decisions[qid], "models": row["models"]}, "Saved decision differs from independently reconstructed decision")
    cohorts = {"all": evaluations, "attack_source": [r for r in evaluations if r["source_group"] == "attck"],
               "other_source": [r for r in evaluations if r["source_group"] != "attck"]}
    demand({k: len(v) for k, v in cohorts.items()} == {"all": 1247, "attack_source": 287, "other_source": 960}, "Cohort sizes changed")
    demand(set(result["metrics"]) == set(cohorts), "Result cohort set changed")
    reproduced = {}
    for cohort, subset in cohorts.items():
        reported = result["metrics"][cohort]
        demand(reported["n"] == len(subset) and set(reported["arms"]) == set(ARMS), "Arm/cohort inventory mismatch")
        reproduced[cohort] = {}
        for arm in ARMS:
            calculated = point_metrics(subset, decisions, arm)
            shown = reported["arms"][arm]
            demand(set(shown["models"]) == set(MODELS), "Model result inventory mismatch")
            for m in MODELS:
                for key, value in calculated["models"][m].items():
                    close(shown["models"][m][key], value, f"{cohort}/{arm}/{m}/{key}")
                interval(shown["models"][m]["delta_ci95_pp"], "Model bootstrap interval")
            for key in ("mean_accuracy_pct", "mean_delta_vs_baseline_pp"):
                close(shown[key], calculated[key], f"{cohort}/{arm}/{key}")
            interval(shown["mean_delta_ci95_pp"], "Pooled bootstrap interval")
            reproduced[cohort][arm] = calculated
    comparisons = result["revised_minus_comparator"]
    demand(set(comparisons) == set(ARMS)-{"answer_change_nli"}, "Comparator set differs")
    revised = reproduced["all"]["answer_change_nli"]
    for name, item in comparisons.items():
        expected = {m: (revised["models"][m]["correct"]-reproduced["all"][name]["models"][m]["correct"])/1247*100 for m in MODELS}
        close(item["model_difference_pp"], expected, "Comparator model differences")
        close(item["mean_difference_pp"], sum(expected.values())/2, "Comparator pooled difference")
        demand(set(item["model_ci95_pp"]) == set(MODELS), "Comparator CI model set")
        for value in item["model_ci95_pp"].values():
            interval(value, "Comparator interval")
        interval(item["mean_ci95_pp"], "Mean comparator interval")
    gains = [revised["models"][m]["delta_vs_baseline_pp"] for m in MODELS]
    expected_status = "EXPOSED_DIAGNOSTIC_POSITIVE_BOTH_MODELS" if min(gains) > 0 else ("EXPOSED_DIAGNOSTIC_MIXED_OR_NO_GAIN" if max(gains) > 0 else "EXPOSED_DIAGNOSTIC_NO_POSITIVE_GAIN")
    demand(result["status"] == expected_status and result["n"] == 1247, "Final status inconsistent with point gains")
    demand(result["scope"] == "EXPOSED_DEVELOPMENT_DIAGNOSTIC_ONLY" and result["independent_confirmation"] is False
           and result["novelty_established"] is False and result["human_review_complete"] is False, "Unsupported confirmation/novelty/review assertion")
    demand(result["bootstrap"]["replicates"] == 5000 and result["bootstrap"]["seed"] == 20260918
           and "not source-cluster" in result["bootstrap"]["method"], "Bootstrap scope changed")
    expected_disagreements = {m: sum(r["models"][m]["vanilla"]["answer"] != r["models"][m]["evidence"]["answer"] for r in evaluations) for m in MODELS}
    close(result["disagreements_per_model"], expected_disagreements, "Final disagreement counts")
    for name in ("scored_pairs", "dataset_rows_read", "truncated_pairs", "inference_seconds", "total_seconds", "device"):
        demand(result["verifier_cost"][name] == receipt[name], "Verifier cost differs from receipt")
    return {"status": "PASS_INDEPENDENT_POINT_AND_POLICY_AUDIT", "completed_utc": datetime.now(timezone.utc).isoformat(),
            "auditor_sha256": digest(__file__), "policy_freeze_sha256": digest(root / "POLICY_FREEZE.json"),
            "results_sha256": digest(root / "RESULTS.json"), "decision_file_sha256": digest(root / "revision_decisions.jsonl"),
            "imports_production_analysis_or_scorer": False, "uses_standard_library_only": True,
            "fresh_model_calls": 0, "calibration_candidates": len(candidates), "selected_policy": winning["policy"],
            "calibration_inventory": cal_inventory, "external_inventory": inventory,
            "external_decision_identities": len(evaluations)*len(ARMS)*len(MODELS),
            "policy_frozen_before_external_scoring_receipt": True,
            "verified_source_locations": {name: str(path) for name, path in resolved_sources.items()},
            "all_sources_resolved_within_checkout": all(path.resolve().is_relative_to(root.parents[1].resolve()) for path in resolved_sources.values()),
            "reproduced_point_metrics": reproduced, "verified_result_status": expected_status,
            "checks": dict(CHECKS), "bootstrap_draws_independently_repeated": False,
            "ci_audit_scope": "Interval shape, finite ordered bounds, declared sampling scope, and point estimates checked; NumPy bootstrap draws and percentile endpoints not independently recomputed.",
            "limitations": ["The same exposed external questions remain development diagnostics, not confirmation.",
                            "Byte and arithmetic checks do not validate the NLI question template, released answer labels, semantic applicability, or novelty.",
                            "Raw NLI probabilities and original generator outputs are not regenerated.",
                            "Original parsed generator answers are checked against preserved predictions and gold; parser logic is not independently reimplemented."]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    target = args.output or args.root / "INDEPENDENT_AUDIT.json"
    try:
        outcome = audit(args.root.resolve())
    except Exception as exc:
        outcome = {"status": "FAIL_INDEPENDENT_REVISION_AUDIT", "error_type": type(exc).__name__, "error": str(exc), "checks": dict(CHECKS),
                   "completed_utc": datetime.now(timezone.utc).isoformat(), "auditor_sha256": digest(__file__)}
    with target.open("x", encoding="utf-8") as stream:
        json.dump(outcome, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": outcome["status"], "checks": outcome.get("checks"), "error": outcome.get("error"), "output": str(target)}))
    if outcome["status"].startswith("FAIL"):
        sys.exit(1)


if __name__ == "__main__":
    main()
