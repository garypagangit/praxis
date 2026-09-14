"""Aggregate every frozen assignment after all phases; do not choose favorable arms."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import analysis
import offline_analysis
import policies
import prompts
from study_runner import save, save_rows

HERE = Path(__file__).resolve().parent
IDENTITY = ("task_id", "split", "cohort", "proposal_id", "intent", "proposer", "reviewer", "arm", "replicate")
JOB_ID_FIELDS = ("task_id", "proposal_id", "cohort", "reviewer", "arm", "replicate")
PROPOSAL_FIELDS = ("task_id", "split", "proposal_id", "intent", "original_variant", "proposer")


def digest(value):
    return hashlib.sha256(policies.canonical(value).encode()).hexdigest()


def frozen_universe(split_manifest):
    tasks = {"Python/" + str(i) for i in range(164)}
    dev, heldout = split_manifest["development_ids"], split_manifest["heldout_ids"]
    if (len(dev) != 41 or len(heldout) != 123 or len(set(dev)) != 41 or len(set(heldout)) != 123
            or set(dev) & set(heldout) or set(dev) | set(heldout) != tasks):
        raise ValueError("Invalid frozen 41/123 source-task split")
    repeated = set(sorted(tasks, key=lambda task: policies.derived_seed("stability", task))[:33])
    jobs, proposals = {}, {}
    for task in sorted(tasks):
        split = "dev" if task in dev else "heldout"
        for cohort, intents, arms in (
            ("native", ("canonical_to_buggy", "buggy_to_canonical"), prompts.NATIVE_ARMS),
            ("generated", ("honest_repair", "adversarial_corruption"), prompts.GENERATED_ARMS),
        ):
            for intent in intents:
                pid = "t" + task.split("/")[1] + "-" + intent
                base = dict(task_id=task, split=split, cohort=cohort, proposal_id=pid,
                            intent="native_" + intent if cohort == "native" else intent,
                            proposer=None if cohort == "native" else prompts.PROPOSER)
                if cohort == "generated":
                    proposals[pid] = dict(task_id=task, split="development" if split == "dev" else split,
                                          proposal_id=pid, intent=intent, proposer=prompts.PROPOSER,
                                          original_variant="buggy" if intent == "honest_repair" else "canonical")
                for reviewer in prompts.REVIEWERS:
                    for arm in arms:
                        for replicate in ((0, 1) if task in repeated else (0,)):
                            row = dict(base, reviewer=reviewer, arm=arm, replicate=replicate)
                            jobid = "review-" + digest({k: row[k] for k in JOB_ID_FIELDS})[:32]
                            if jobid in jobs:
                                raise ValueError("Frozen job identity collision")
                            jobs[jobid] = row
    if len(jobs) != 9456 or len(proposals) != 328:
        raise ValueError("Frozen seven/five-arm, two-reviewer assignment universe changed")
    return jobs, proposals


def validate_review_jobs(jobs, universe):
    actual = {}
    for job in jobs:
        jobid = job.get("job_id")
        if jobid not in universe or jobid in actual:
            raise ValueError("Unknown or duplicate review job ID")
        row = job["row"]
        if any(row.get(key) != universe[jobid][key] for key in IDENTITY):
            raise ValueError("Review job contradicts frozen identity/direction")
        if type(row.get("eligible")) is not bool or ("messages" in job) != row["eligible"]:
            raise ValueError("Review eligibility and assigned prompt disagree")
        actual[jobid] = job
    if set(actual) != set(universe):
        raise ValueError("Frozen review assignments missing: " + str(len(set(universe) - set(actual))))
    return actual


def validate_decisions(decisions, jobs):
    seen = set()
    for row in decisions:
        jobid = row.get("job_id")
        if jobid not in jobs or jobid in seen:
            raise ValueError("Unknown or duplicate decision job ID")
        seen.add(jobid)
        job = jobs[jobid]
        if row.get("assignment_sha256") != digest(job):
            raise ValueError("Decision assignment hash mismatch")
        if any(row.get(key) != job["row"][key] for key in IDENTITY):
            raise ValueError("Decision identity disagrees with assigned job")
    return set(jobs) - seen


def validate_proposals(proposals, jobs, universe):
    assigned = {}
    for job in jobs:
        pid = job.get("proposal_id")
        if pid not in universe or pid in assigned:
            raise ValueError("Unknown or duplicate proposal assignment")
        if any(job.get(key) != universe[pid][key] for key in PROPOSAL_FIELDS):
            raise ValueError("Proposal assignment contradicts frozen direction/split")
        assigned[pid] = job
    if set(assigned) != set(universe):
        raise ValueError("Frozen generated proposal assignments missing")
    seen = set()
    for row in proposals:
        pid = row.get("proposal_id")
        if pid not in assigned or pid in seen:
            raise ValueError("Unknown or duplicate generated proposal record")
        seen.add(pid)
        if row.get("assignment_sha256") != digest(assigned[pid]):
            raise ValueError("Generated proposal assignment hash mismatch")
        if any(row.get(key) != universe[pid][key] for key in PROPOSAL_FIELDS):
            raise ValueError("Generated proposal record identity mismatch")
        if row.get("status") == "admitted":
            if not isinstance(row.get("code"), str) or hashlib.sha256(row["code"].encode()).hexdigest() != row.get("code_sha256"):
                raise ValueError("Admitted generated source hash mismatch")
    if seen != set(universe):
        raise ValueError("Generated proposal record placeholders missing")


def validate_budget(budget):
    if type(budget.get("limit_usd")) not in (int, float) or budget["limit_usd"] != 30:
        raise ValueError("Frozen API ledger limit must equal $30")
    if not isinstance(budget.get("entries"), dict):
        raise ValueError("API ledger entries must be an object")
    entries = list(budget["entries"].values())
    for row in entries:
        amount = row.get("accounted_usd")
        if type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
            raise ValueError("Invalid nonfinite/negative API accounted amount")
        if row.get("model_id") not in prompts.REVIEWERS:
            raise ValueError("API ledger contains an unfrozen model")
        if not isinstance(row.get("status"), str) or not row["status"]:
            raise ValueError("API ledger attempt status is missing")
        for name in ("inputTokens", "outputTokens"):
            value = (row.get("usage") or {}).get(name, 0)
            if type(value) is not int or value < 0:
                raise ValueError("Invalid API token usage")
    total = math.fsum(row["accounted_usd"] for row in entries)
    if total > 30 + 1e-9:
        raise ValueError("Accounted API estimate exceeds frozen $30 limit")
    return entries, total


def validate_gate(gate, decisions, jobs):
    if type(gate.get("all_assignments_accounted")) is not bool or gate["all_assignments_accounted"] != (len(decisions) == len(jobs)):
        raise ValueError("Technical gate assignment accounting mismatch")
    expected_pass = []
    for reviewer in prompts.REVIEWERS:
        selected = [row for row in decisions if row["reviewer"] == reviewer and row["eligible"]]
        valid = sum(row["model_valid"] for row in selected)
        expected = dict(assigned=len(selected), valid=valid,
                        valid_rate=valid / len(selected) if selected else None,
                        **{"pass": bool(selected) and valid / len(selected) >= .95})
        actual = gate["models"][reviewer]
        if any(actual.get(key) != value for key, value in expected.items()) or type(actual.get("pass")) is not bool:
            raise ValueError("Technical gate disagrees with observed reviewer counts")
        expected_pass.append(expected["pass"])
    if type(gate.get("pass")) is not bool or gate["pass"] != (all(expected_pass) and len(decisions) == len(jobs)):
        raise ValueError("Technical gate aggregate decision mismatch")


def capture(path, provenance, name=None, jsonl=False):
    data = path.read_bytes()
    provenance[name or path.name] = hashlib.sha256(data).hexdigest()
    return analysis.load_jsonl_bytes(data, str(path)) if jsonl else json.loads(data.decode("utf-8-sig"))


def save_text(path, text):
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() != data:
        raise ValueError("Refusing to change existing report: " + str(path))
    path.write_bytes(data)


def finalize(root, protocol, protocol_hash):
    if hashlib.sha256(protocol.read_bytes()).hexdigest() != protocol_hash:
        raise ValueError("Frozen protocol hash mismatch")
    decisions, expected, offline, gates, provenance, all_jobs = [], [], [], {}, {}, []
    source_freeze = capture(HERE / "MODEL_SOURCE_FREEZE.json", provenance)
    for relative, wanted in source_freeze["files"].items():
        path = (HERE / relative).resolve()
        if not path.is_relative_to(HERE.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
            raise ValueError("Finalization source freeze mismatch: " + relative)
    split_manifest = capture(HERE / "qualification/SPLIT_MANIFEST.json", provenance, "qualification/SPLIT_MANIFEST.json")
    capture(root / "REFERENCE_MANIFEST.json", provenance)
    universe, proposal_universe = frozen_universe(split_manifest)
    for cohort in ("native", "generated"):
        for split in ("development", "heldout"):
            suffix = cohort + "_" + split
            local_decisions = capture(root / ("decisions_" + suffix + ".jsonl"), provenance, jsonl=True)
            jobs = capture(root / ("review_jobs_" + suffix + ".jsonl"), provenance, jsonl=True)
            local_offline = capture(root / ("offline_" + suffix + ".jsonl"), provenance, jsonl=True)
            label = "dev" if split == "development" else split
            if any(row["cohort"] != cohort or row["split"] != label for row in local_decisions + local_offline):
                raise ValueError("Result file cohort/split mismatch")
            if any(job["row"]["cohort"] != cohort or job["row"]["split"] != label for job in jobs):
                raise ValueError("Job file cohort/split mismatch")
            decisions.extend(local_decisions)
            all_jobs.extend(jobs)
            expected.extend(job["row"] for job in jobs)
            offline.extend(local_offline)
            gate = capture(root / ("GATE_" + suffix + ".json"), provenance)
            if gate.get("split") != split or gate.get("cohort") != cohort or set(gate.get("models", {})) != set(prompts.REVIEWERS):
                raise ValueError("Technical gate identity mismatch")
            validate_gate(gate, local_decisions, jobs)
            gates[suffix] = gate
    proposer_gate = capture(root / "PROPOSER_DEVELOPMENT_GATE.json", provenance)
    required_checks = {cohort: gates[cohort + "_development"]["models"][prompts.PROPOSER]["pass"] for cohort in ("native", "generated")}
    if (proposer_gate.get("split") != "development" or proposer_gate.get("proposer") != prompts.PROPOSER
            or proposer_gate.get("checks") != required_checks or type(proposer_gate.get("pass")) is not bool
            or proposer_gate["pass"] != all(required_checks.values())):
        raise ValueError("Proposer gate disagrees with both development reviewer gates")
    jobs_by_id = validate_review_jobs(all_jobs, universe)
    missing_decisions = validate_decisions(decisions, jobs_by_id)
    proposal_jobs, proposals = [], []
    for split in ("development", "heldout"):
        proposal_jobs.extend(capture(root / ("proposal_jobs_" + split + ".jsonl"), provenance, jsonl=True))
        proposals.extend(capture(root / ("proposals_" + split + ".jsonl"), provenance, jsonl=True))
    validate_proposals(proposals, proposal_jobs, proposal_universe)
    budget = capture(root / "budget.json", provenance)
    entries, total_cost = validate_budget(budget)
    unique = {}
    for row in expected:
        key = (row["task_id"], row["cohort"], row["proposal_id"])
        unique.setdefault(key, row)
    if len(unique) != 656:
        raise ValueError("Frozen656-direction assignment universe changed")
    offline_expected = []
    for row in unique.values():
        base = {key: row[key] for key in ("task_id", "split", "cohort", "proposal_id", "direction", "eligible", "eligibility_reasons", "proposer", "intent")}
        for replicate in range(20):
            for budget_value in (4, 8):
                for policy in policies.POLICIES:
                    offline_expected.append(dict(base, policy=policy, budget=budget_value, replicate=replicate))
    model = analysis.analyze(decisions, reviewers=prompts.REVIEWERS, expected_assignments=expected)
    acquisition = offline_analysis.analyze(offline, expected_assignments=offline_expected)
    common = {"protocol_sha256": protocol_hash, "source_inputs_sha256": provenance,
              "finalizer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    model["provenance"] = dict(common, analysis_source_sha256=hashlib.sha256(Path(analysis.__file__).read_bytes()).hexdigest())
    acquisition["provenance"] = dict(common, analysis_source_sha256=hashlib.sha256(Path(offline_analysis.__file__).read_bytes()).hexdigest())
    usage = {model: {"input_tokens": sum((r.get("usage") or {}).get("inputTokens", 0) for r in entries if r["model_id"] == model),
                     "output_tokens": sum((r.get("usage") or {}).get("outputTokens", 0) for r in entries if r["model_id"] == model),
                     "accounted_usd_estimate": sum(r["accounted_usd"] for r in entries if r["model_id"] == model)} for model in prompts.REVIEWERS}
    flow = {"source_tasks": 164, "proposal_directions_assigned": len(unique), "review_assignments": len(expected),
            "review_records": len(decisions), "missing_review_record_ids": sorted(missing_decisions),
            "model_status_counts": dict(Counter(r["model_status"] for r in decisions)),
            "generated_proposals": len(proposals), "generated_status_counts": dict(Counter(r["status"] for r in proposals)),
            "offline_assigned_rows": len(offline_expected), "offline_rows": len(offline),
            "cohort_flow": {cohort: dict(Counter(("eligible_" if row["eligible"] else "ineligible_") + row["direction"] for row in unique.values() if row["cohort"] == cohort)) for cohort in ("native", "generated")},
            "technical_gates": gates, "api_budget_limit_usd": budget["limit_usd"], "api_usage": usage,
            "accounted_api_usd_estimate": total_cost, "within_frozen_api_ledger": True, "invoice_claimed": False,
            "api_attempt_status_counts": dict(Counter(r["status"] for r in entries)),
            "experiment_processing_accounted": not missing_decisions and len(offline) == len(offline_expected),
            "eligible_review_assignments": sum(row["eligible"] for row in expected),
            "eligible_review_calls_completed": sum(row["eligible"] and row.get("model_status") == "complete" for row in decisions),
            "eligible_reviews_all_completed": not missing_decisions and all(row.get("model_status") == "complete" for row in decisions if row["eligible"]),
            "accounting_interpretation": "Every assigned record can be accounted for while calls are gated, budget-exhausted, invalid, or otherwise incomplete; accounting does not establish a positive result.",
            "paper_development_readiness": "Await independent automated artifact review; completion is not a positive method result."}
    output = root / "public_results"
    for name, values in (("DECISIONS", decisions), ("EXPECTED_DECISIONS", expected), ("OFFLINE", offline), ("EXPECTED_OFFLINE", offline_expected)):
        save_rows(output / (name + ".jsonl"), values)
    save(output / "MODEL_RESULTS.json", model)
    save(output / "ACQUISITION_RESULTS.json", acquisition)
    save_text(output / "MODEL_RESULTS.md", analysis.render_markdown(model))
    save_text(output / "ACQUISITION_RESULTS.md", offline_analysis.render_markdown(acquisition))
    save(output / "FLOW_AND_COSTS.json", flow)
    save(output / "RESULTS_RECEIPT.json", {**common, "artifacts_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file() and p.name != "RESULTS_RECEIPT.json"}})
    print(json.dumps(flow, indent=2), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study-root", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--protocol-sha256", required=True)
    args = p.parse_args()
    finalize(args.study_root, args.protocol, args.protocol_sha256)
