"""Audit saved retrieval predictions without invoking methods or their scorer.

Reuses only the independent reference auditor. Source data are read as data;
no training, inference, retrieval execution, or timing rerun is performed.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess

import audit_reference as reference


require = reference.require
file_hash = reference.file_hash


def frozen_bytes(repository, commit, path):
    relative = path.resolve().relative_to(repository).as_posix()
    return subprocess.run(["git", "show", commit + ":" + relative], cwd=repository,
                          check=True, capture_output=True).stdout


def evidence_size(records, compact):
    """Independently reconstruct the registered reversible evidence encoding."""
    if not compact:
        payload = {"evidence": records}
    else:
        identifiers = set()
        for record in records:
            identifiers.update(record[k] for k in ("guid", "parent_guid") if record[k])
        aliases = {value: "P" + str(number) for number, value in enumerate(sorted(identifiers), 1)}
        converted = []
        for record in records:
            converted.append({key: aliases.get(value, value) if key in ("guid", "parent_guid") else value
                              for key, value in record.items()})
        payload = {"evidence": converted, "guid_aliases": {alias: value for value, alias in aliases.items()}}
    return len(json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8"))


def verified_row(saved, question, gold, events, creation_groups, name_groups):
    require(saved["question_id"] == question["question_id"], "Question identity mismatch")
    require(saved["stratum"] == question["stratum"], "Cohort mismatch")
    require(saved["gold_status"] == gold["status"], "Saved gold class mismatch")
    status = saved["prediction_status"]
    require(status in {"ANSWER", "INSUFFICIENT_EVIDENCE", "AMBIGUOUS"}, "Invalid prediction status")
    refs = saved["evidence_refs"]
    require(isinstance(refs, list) and len(refs) == len(set(refs)), "Repeated/invalid evidence refs")
    require(1 <= len(refs) <= saved["budget"], "Evidence budget exceeded")
    require(question["anchor_ref"] in refs and all(ref in events for ref in refs), "Missing/unknown evidence ref")
    require(all(ref == question["anchor_ref"] or events[ref]["kind"] == "creation" for ref in refs),
            "Non-creation additional evidence")
    answered = status == "ANSWER"
    answer_ref = saved["answer_ref"]
    if answered:
        require(answer_ref in refs and events[answer_ref]["kind"] == "creation", "Unsupported answer reference")
    else:
        require(answer_ref is None, "Abstention contains an answer reference")
    available = gold["status"] == "ANSWER"
    correct = answered and available and answer_ref in gold["acceptable_refs"]
    truth = {
        "available_answer": available, "answered": answered,
        "correct_supported_answer": correct,
        "incorrect_or_unsupported_answer": answered and not correct,
        "correct_abstention": not answered and not available,
        "wrong_abstention": not answered and available,
        # Existing output terminology: this means status-label agreement only.
        "correct_reason": status == gold["status"],
        "evidence_records": len(refs),
        "additional_creation_records": sum(ref != question["anchor_ref"] for ref in refs),
        "serialized_bytes": evidence_size([events[ref] for ref in refs], saved["method"] == "compact_guid_join"),
    }
    for key, value in truth.items():
        require(saved[key] == value and (not isinstance(value, bool) or type(saved[key]) is bool),
                f"Prediction metric mismatch: {key}")
    anchor = events[question["anchor_ref"]]
    if saved["method"] in ("exact_guid_join", "compact_guid_join"):
        target = anchor["parent_guid"] if question["kind"] == "parent_creation" else anchor["guid"]
        expected_inspections = len(creation_groups[(anchor["host"], target)])
        expected_lookups = 1 if target else 0
    else:
        image = anchor["parent_image"] if question["kind"] == "parent_creation" else anchor["image"]
        expected_inspections = len(name_groups[(anchor["host"], reference.basename(image))])
        expected_lookups = 1
        if answered:
            selected = events[answer_ref]
            expected_inspections += len(creation_groups[(anchor["host"], selected["guid"])])
            expected_lookups += 1
    require(saved["inspected_records"] == expected_inspections, "Logical inspected-record accounting mismatch")
    require(saved["lookup_calls"] == expected_lookups, "Logical lookup accounting mismatch")
    truth.update(inspected_records=expected_inspections, lookup_calls=expected_lookups)
    return truth


def aggregate(rows):
    total = len(rows)
    require(total > 0, "Empty evaluation cell")
    count_fields = ("available_answer", "answered", "correct_supported_answer", "incorrect_or_unsupported_answer",
                    "correct_abstention", "wrong_abstention", "correct_reason")
    output = {"questions": total}
    output.update({key: sum(int(row[key]) for row in rows) for key in count_fields})
    output["answered_coverage"] = output["answered"] / total
    output["supported_recovery"] = (output["correct_supported_answer"] / output["available_answer"]
                                      if output["available_answer"] else None)
    output["wrong_answer_fraction"] = (output["incorrect_or_unsupported_answer"] / output["answered"]
                                        if output["answered"] else None)
    for field in ("evidence_records", "additional_creation_records", "inspected_records", "lookup_calls", "serialized_bytes"):
        output["mean_" + field] = sum(row[field] for row in rows) / total
    return output


def audit(archive, workspace, result_dir, source_commit="f114185"):
    root = Path(__file__).resolve().parent
    repository = root.parents[2]
    protocol_path = root / "PROTOCOL.json"
    manifest_path = root / "CASE_MANIFEST.json"
    reference_path = root / "REFERENCE_AUDIT.json"
    previous_reference = json.loads(reference_path.read_text(encoding="utf-8"))
    require(previous_reference["reference_audit_passed"] is True, "Reference audit is not successful")
    require(previous_reference["auditor_sha256"] == file_hash(root / "audit_reference.py"), "Reference auditor changed")
    renewed_reference = reference.audit(archive, workspace, manifest_path, protocol_path,
                                        previous_reference["frozen_protocol_commit"])
    for key in ("input_hashes", "independent_source_counts", "eligible_population_sizes", "question_count",
                "cohort_counts", "reference_answer_classes_by_cohort", "checks"):
        require(renewed_reference[key] == previous_reference[key], f"Reference revalidation mismatch: {key}")
    full_commit = subprocess.run(["git", "rev-parse", source_commit + "^{commit}"], cwd=repository,
                                 check=True, capture_output=True, text=True).stdout.strip()
    source_names = ("prepare.py", "methods.py", "run_pilot.py")
    for name in (*source_names, "PROTOCOL.json", "CASE_MANIFEST.json", "REFERENCE_AUDIT.json", "audit_reference.py"):
        require((root / name).read_bytes() == frozen_bytes(repository, full_commit, root / name),
                f"Current input/code differs from source freeze: {name}")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    receipt_path = result_dir / "RUN_RECEIPT.json"
    results_path = result_dir / "RESULTS.json"
    predictions_path = result_dir / "PREDICTIONS.jsonl"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    require(receipt["status"] == "COMPLETE", "Run is not complete")
    require(receipt["protocol_sha256"] == file_hash(protocol_path), "Run protocol hash mismatch")
    require(receipt["case_manifest_sha256"] == file_hash(manifest_path), "Run manifest hash mismatch")
    require(receipt["code_sha256"] == {name: file_hash(root / name) for name in source_names}, "Run code hash mismatch")
    require(receipt["results_sha256"] == file_hash(results_path), "Results hash mismatch")
    require(receipt["predictions_sha256"] == file_hash(predictions_path), "Predictions hash mismatch")
    require(all(receipt[key] is False for key in ("llm_run", "gpu_used", "new_detector_trained")),
            "Unexpected execution scope")
    started = datetime.fromisoformat(receipt["started_utc"])
    finished = datetime.fromisoformat(receipt["finished_utc"])
    require(started.tzinfo is not None and finished >= started, "Invalid run timestamps")
    records = reference.read_jsonl(workspace / "records.jsonl")
    questions = reference.read_jsonl(workspace / "questions.jsonl")
    gold_rows = reference.read_jsonl(workspace / "gold.jsonl")
    predictions = reference.read_jsonl(predictions_path)
    events = {r["ref"]: r for r in records}
    question_map = {q["question_id"]: q for q in questions}
    gold = {r["question_id"]: r for r in gold_rows}
    creation_groups, name_groups = defaultdict(list), defaultdict(list)
    for record in records:
        if record["kind"] == "creation":
            creation_groups[(record["host"], record["guid"])].append(record)
            name_groups[(record["host"], reference.basename(record["image"]))].append(record)
    configs = [(method, budget) for budget in protocol["evidence_record_budgets"] for method in protocol["methods"]]
    expected_keys = {(method, budget, qid) for method, budget in configs for qid in question_map}
    by_key = {}
    for prediction in predictions:
        key = (prediction["method"], prediction["budget"], prediction["question_id"])
        require(key in expected_keys and key not in by_key, "Unexpected or duplicate method/budget/question")
        by_key[key] = prediction
    require(set(by_key) == expected_keys and len(predictions) == 480, "Missing prediction cells")
    independent_rows = {}
    for key, saved in by_key.items():
        qid = key[2]
        independent_rows[key] = verified_row(saved, question_map[qid], gold[qid], events,
                                             creation_groups, name_groups)
    summaries = []
    ceiling = []
    status_tables = []
    require(len(results["summaries"]) == len(configs) == 8, "Wrong summary count")
    for (method, budget), reported in zip(configs, results["summaries"]):
        require((reported["method"], reported["budget"]) == (method, budget), "Summary cell order mismatch")
        pool = [independent_rows[(method, budget, q["question_id"])] for q in questions]
        pooled = aggregate(pool)
        strata = {c["name"]: aggregate([independent_rows[(method, budget, q["question_id"])]
                                        for q in questions if q["stratum"] == c["name"]])
                  for c in protocol["cohorts"]}
        require(reported["pooled"] == pooled and reported["strata"] == strata, "Aggregate metric mismatch")
        summaries.append({"method": method, "budget": budget, "pooled": pooled, "strata": strata})
        timing = reported["latency_batch_seconds"]
        require(timing["repetitions"] == protocol["latency_repetitions"], "Unexpected reported latency repetitions")
        require(all(isinstance(timing[key], (int, float)) and math.isfinite(timing[key]) for key in ("min", "median", "max")),
                "Invalid reported timing values")
        require(0 <= timing["min"] <= timing["median"] <= timing["max"], "Inconsistent timing summary")
        cell = [by_key[(method, budget, q["question_id"])] for q in questions]
        classes = Counter((gold[p["question_id"]]["status"], p["prediction_status"]) for p in cell)
        status_tables.append({"method": method, "budget": budget,
                              "gold_vs_prediction_status": [{"gold": g, "prediction": p, "count": n}
                                                            for (g, p), n in sorted(classes.items())],
                              "strict_case_correct": sum(p["correct_supported_answer"] or
                                                          (not p["answered"] and p["correct_reason"]) for p in cell)})
        is_complete_correct = all(r["correct_supported_answer"] or
                                  (r["correct_abstention"] and r["correct_reason"]) for r in pool)
        if method in protocol["strong_baselines"] and is_complete_correct:
            ceiling.append({"method": method, "budget": budget})
    budget_equality = {}
    budgets = protocol["evidence_record_budgets"]
    require(budgets == [2, 4], "Unexpected registered budgets")
    for method in protocol["methods"]:
        for qid in question_map:
            first = {k: v for k, v in by_key[(method, 2, qid)].items() if k != "budget"}
            second = {k: v for k, v in by_key[(method, 4, qid)].items() if k != "budget"}
            require(first == second, "Unexpected prediction/cost difference across non-binding budgets")
        budget_equality[method] = True
    decision = "NO_GO_NO_HEADROOM" if ceiling else "NATURAL_FAILURE_REQUIRES_DIAGNOSIS"
    required_totals = {
        "decision": decision, "stage": "RECORDED_IDENTITY_BASELINE_SCREEN_COMPLETE",
        "unique_questions": len(questions), "cohort_sizes": dict(Counter(q["stratum"] for q in questions)),
        "gold_status_counts": dict(Counter(g["status"] for g in gold_rows)),
        "distinct_target_identities": len({g["target_identity_digest"] for g in gold_rows}),
        "evaluated_method_budget_cells": len(configs), "prediction_records": len(predictions),
        "strong_baselines_reaching_ceiling": ceiling,
        "shared_index_creation_records": sum(r["kind"] == "creation" for r in records),
    }
    for key, value in required_totals.items():
        require(results[key] == value, f"Top-level result mismatch: {key}")
    require(math.isfinite(results["index_build_seconds"]) and results["index_build_seconds"] >= 0,
            "Invalid index timing")
    return {
        "status": "VERIFIED_SAVED_PREDICTIONS_AND_REGISTERED_DECISION",
        "created_utc": datetime.now(timezone.utc).isoformat(), "result_audit_passed": True,
        "scientific_screen_complete": True, "independent_decision": decision,
        "source_freeze_commit": full_commit,
        "input_hashes": {
            "run_receipt_sha256": file_hash(receipt_path), "results_sha256": file_hash(results_path),
            "predictions_sha256": file_hash(predictions_path), "reference_audit_sha256": file_hash(reference_path),
            "protocol_sha256": file_hash(protocol_path), "case_manifest_sha256": file_hash(manifest_path),
            "source_code": {name: file_hash(root / name) for name in source_names},
            "reference_inputs": renewed_reference["input_hashes"],
        },
        "auditor_sha256": file_hash(Path(__file__)), "reference_auditor_sha256": file_hash(root / "audit_reference.py"),
        "verified_totals": required_totals, "independent_summaries": summaries,
        "status_label_diagnostics": status_tables,
        "prediction_and_cost_equality_across_budgets": budget_equality,
        "checks": {"all_480_predictions_recomputed_from_source_verified_gold": True,
                   "all_8_cells_contain_each_of_60_questions_once": True,
                   "evidence_refs_budgets_and_creation_types_verified": True,
                   "serialized_utf8_bytes_include_compact_alias_map": True,
                   "logical_lookup_and_inspection_accounting_verified": True,
                   "all_pooled_and_stratified_metrics_match": True,
                   "run_receipt_and_current_code_hashes_match_source_freeze": True,
                   "registered_stopping_decision_matches": True,
                   "latency_summary_internal_consistency_only": True,
                   "raw_latency_samples_independently_verified": False},
        "evaluated_methods_or_scorer_imported": False, "methods_rerun": False, "model_run": False,
        "interpretation_limits": [
            "There are 60 selected factual questions and 480 repeated method/budget evaluations, not 480 attacks or independent cases.",
            "The 38 distinct target identities include answerable and unavailable targets; they are not 38 independent campaigns.",
            "The fixed recorded-identity task has no measured headroom over exact joins; this does not close every investigation task.",
            "The 22 unavailable answers have no matching creation in the qualified 447-row Sysmon EventID 1 table; other channels such as Security 4688 were not qualified for this endpoint.",
            "correct_reason denotes status-label agreement, which can also occur for an incorrect identity answer.",
            "correct_abstention denotes withholding an answer; an AMBIGUOUS response can still misstate an INSUFFICIENT_EVIDENCE reason.",
            "Logical work counts are source-consistent counters, not an independent instrumented CPU-operation trace.",
            "Only latency min/median/max and repetition counts were retained; raw timings and repeat equality cannot be independently reconstructed here.",
            "No LLM performance, attack detection, human time savings, or independent-campaign generalization was measured.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--source-commit", default="f114185")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    destination = args.output or args.result_dir / "RESULTS_AUDIT.json"
    require(not destination.exists(), "Do not overwrite a results audit receipt")
    result = audit(args.archive, args.workspace, args.result_dir, args.source_commit)
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "decision": result["independent_decision"],
                      "questions": result["verified_totals"]["unique_questions"],
                      "predictions": result["verified_totals"]["prediction_records"]}))
