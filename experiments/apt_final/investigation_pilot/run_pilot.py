"""Score frozen factual retrieval questions; no LLM or attack detector runs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time

from methods import build_index, retrieve


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def evaluate_prediction(question, gold, prediction, events, budget):
    assert prediction["status"] in ("ANSWER", "INSUFFICIENT_EVIDENCE", "AMBIGUOUS")
    refs = prediction["evidence_refs"]
    assert len(refs) <= budget and len(set(refs)) == len(refs)
    assert question["anchor_ref"] in refs and all(ref in events for ref in refs)
    answered = prediction["status"] == "ANSWER"
    if answered:
        assert prediction["answer_ref"] in refs
        assert events[prediction["answer_ref"]]["kind"] == "creation"
    else:
        assert prediction["answer_ref"] is None
    supported = gold["status"] == "ANSWER"
    correct = answered and supported and prediction["answer_ref"] in gold["acceptable_refs"]
    return {
        "question_id": question["question_id"], "stratum": question["stratum"],
        "gold_status": gold["status"], "prediction_status": prediction["status"],
        "available_answer": supported, "answered": answered,
        "correct_supported_answer": correct, "incorrect_or_unsupported_answer": answered and not correct,
        "correct_abstention": not supported and not answered,
        "wrong_abstention": supported and not answered,
        "correct_reason": prediction["status"] == gold["status"],
        **{key: prediction[key] for key in ("answer_ref", "evidence_refs", "inspected_records", "lookup_calls", "serialized_bytes")},
        "evidence_records": len(refs),
        "additional_creation_records": sum(events[ref]["kind"] == "creation" and ref != question["anchor_ref"] for ref in refs),
    }


def summarize(rows):
    counts = {key: sum(row[key] for row in rows) for key in (
        "available_answer", "answered", "correct_supported_answer", "incorrect_or_unsupported_answer",
        "correct_abstention", "wrong_abstention", "correct_reason")}
    n = len(rows)
    return {"questions": n, **counts,
            "answered_coverage": counts["answered"] / n,
            "supported_recovery": counts["correct_supported_answer"] / counts["available_answer"] if counts["available_answer"] else None,
            "wrong_answer_fraction": counts["incorrect_or_unsupported_answer"] / counts["answered"] if counts["answered"] else None,
            **{"mean_" + key: statistics.mean(row[key] for row in rows) for key in
               ("evidence_records", "additional_creation_records", "inspected_records", "lookup_calls", "serialized_bytes")}}


def run(workspace, destination):
    root = Path(__file__).parent
    protocol = json.loads((root / "PROTOCOL.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "CASE_MANIFEST.json").read_text(encoding="utf-8"))
    assert sha(root / "PROTOCOL.json") == manifest["protocol_sha256"]
    assert sha(root / "prepare.py") == manifest["preparation_code_sha256"]
    for name, expected in manifest["files"].items():
        assert sha(workspace / name) == expected["sha256"]
        assert (workspace / name).stat().st_size == expected["bytes"]
    records = load_jsonl(workspace / "records.jsonl")
    questions = load_jsonl(workspace / "questions.jsonl")
    gold = {g["question_id"]: g for g in load_jsonl(workspace / "gold.jsonl")}
    assert questions == manifest["questions"]
    assert len(gold) == len(questions) == 60
    assert not destination.exists(), "Keep attempts immutable; use a new output directory"
    destination.mkdir(parents=True)
    run_receipt = {"status": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat(),
                   "protocol_sha256": sha(root / "PROTOCOL.json"), "case_manifest_sha256": sha(root / "CASE_MANIFEST.json"),
                   "code_sha256": {name: sha(root / name) for name in ("prepare.py", "methods.py", "run_pilot.py")},
                   "python": sys.version, "platform": platform.platform(),
                   "llm_run": False, "gpu_used": False, "new_detector_trained": False}
    receipt_path = destination / "RUN_RECEIPT.json"
    receipt_path.write_text(json.dumps(run_receipt, indent=2) + "\n", encoding="utf-8")
    events = {r["ref"]: r for r in records}
    creations = [r for r in records if r["kind"] == "creation"]
    index_start = time.perf_counter()
    index = build_index(creations)
    index_seconds = time.perf_counter() - index_start
    predictions = {}
    rows = []
    configs = [(method, budget) for budget in protocol["evidence_record_budgets"] for method in protocol["methods"]]
    for method, budget in configs:
        outputs = [retrieve(method, q, events, index, budget) for q in questions]
        predictions[method, budget] = outputs
        for question, prediction in zip(questions, outputs):
            row = evaluate_prediction(question, gold[question["question_id"]], prediction, events, budget)
            row.update(method=method, budget=budget)
            rows.append(row)
    latencies = {config: [] for config in configs}
    for repeat in range(protocol["latency_repetitions"]):
        rotated = configs[repeat % len(configs):] + configs[:repeat % len(configs)]
        for method, budget in rotated:
            started = time.perf_counter()
            outputs = [retrieve(method, q, events, index, budget) for q in questions]
            latencies[method, budget].append(time.perf_counter() - started)
            assert outputs == predictions[method, budget], "Nondeterministic retrieval output"
    summaries = []
    for method, budget in configs:
        selected = [r for r in rows if r["method"] == method and r["budget"] == budget]
        summaries.append({"method": method, "budget": budget, "pooled": summarize(selected),
                          "strata": {c["name"]: summarize([r for r in selected if r["stratum"] == c["name"]]) for c in protocol["cohorts"]},
                          "latency_batch_seconds": {"repetitions": len(latencies[method, budget]),
                                                    "median": statistics.median(latencies[method, budget]),
                                                    "min": min(latencies[method, budget]), "max": max(latencies[method, budget])}})
    ceiling = []
    for item in summaries:
        score = item["pooled"]
        if item["method"] in protocol["strong_baselines"] and (
            score["correct_supported_answer"] == score["available_answer"] and
            score["incorrect_or_unsupported_answer"] == 0 and
            score["correct_abstention"] == score["questions"] - score["available_answer"] and
            score["correct_reason"] == score["questions"]):
            ceiling.append({"method": item["method"], "budget": item["budget"]})
    result = {
        "decision": "NO_GO_NO_HEADROOM" if ceiling else "NATURAL_FAILURE_REQUIRES_DIAGNOSIS",
        "stage": "RECORDED_IDENTITY_BASELINE_SCREEN_COMPLETE",
        "unique_questions": len(questions), "cohort_sizes": dict(Counter(q["stratum"] for q in questions)),
        "gold_status_counts": dict(Counter(g["status"] for g in gold.values())),
        "distinct_target_identities": len({g["target_identity_digest"] for g in gold.values()}),
        "evaluated_method_budget_cells": len(configs), "prediction_records": len(rows),
        "strong_baselines_reaching_ceiling": ceiling, "index_build_seconds": index_seconds,
        "shared_index_creation_records": len(creations), "summaries": summaries,
        "not_measured": ["LLM errors", "attack detection", "malicious intent", "actor attribution", "human time saved", "independent campaign generalization"],
        "interpretation": "Exact-ID lookup success measures recorded-fact retrieval, not novel APT intelligence. Name-only errors do not establish that an LLM makes those errors. The selected difficult stratum prevents treating pooled rates as natural prevalence.",
    }
    (destination / "RESULTS.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (destination / "PREDICTIONS.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    run_receipt.update(status="COMPLETE", finished_utc=datetime.now(timezone.utc).isoformat(),
                       results_sha256=sha(destination / "RESULTS.json"), predictions_sha256=sha(destination / "PREDICTIONS.jsonl"))
    receipt_path.write_text(json.dumps(run_receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "summaries"}, indent=2))
    for item in summaries:
        print(json.dumps({"method": item["method"], "budget": item["budget"], **item["pooled"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.workspace, args.output)
