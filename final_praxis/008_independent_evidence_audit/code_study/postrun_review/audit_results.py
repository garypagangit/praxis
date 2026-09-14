"""Read-only postrun evidence audit. Never executes candidate code or calls models.

Run only after the coordinator supplies the completed artifact archive. The main
study source/protocol is immutable; this auditor writes only its requested report.
"""
import argparse
import ast
from collections import Counter, defaultdict
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import sys

PROTOCOL_SHA256 = "11b620786e74a374158c93181024e1bfec216fc8edfa3c4178bbd12bd234610a"
FROZEN_COMMIT = "162d2ab"
REVIEWERS = ("qwen.qwen3-coder-next", "mistral.devstral-2-123b")
RATES = {REVIEWERS[0]: (.5, 1.2), REVIEWERS[1]: (.4, 2.)}
FAILURES = {"fail", "exception", "timeout", "program_load_error"}
ARMS = {"native": ("no_witness", "uniform_w", "selected_w", "uniform_a", "edit", "complement", "hybrid"),
        "generated": ("uniform_w", "selected_w", "uniform_a", "edit", "hybrid")}
REVIEW_SCHEMA = {"type":"object", "properties":{"decision":{"type":"string","enum":["accept","keep"]},
                  "reason":{"type":"string"}}, "required":["decision","reason"], "additionalProperties":False}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode_json(text):
    return json.loads(text, object_pairs_hook=strict_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON token")))


def read_json(path):
    return decode_json(path.read_text(encoding="utf-8-sig"))


def read_rows(path):
    return [decode_json(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def derived_seed(*parts):
    return int.from_bytes(hashlib.sha256("|".join(map(str, ("praxis008-code-study-v1", *parts))).encode()).digest()[:16], "big")


def outcome(statuses):
    statuses = list(statuses)
    if statuses and all(status == "pass" for status in statuses):
        return True
    if any(status in FAILURES for status in statuses):
        return False
    return None


def direction(y0, y1):
    if y0 is None or y1 is None:
        return "unknown"
    return "harmful" if y0 and not y1 else "useful" if not y0 and y1 else "other"


def terminal_object(result):
    if result.get("finish_reason") not in ("end_turn", "stop_sequence"):
        return None, "nonterminal_or_truncated_response"
    try:
        text = result["text"].strip()
        if text.startswith("```"):
            match = re.fullmatch(r"```(?:json)?\s*\n([\s\S]*?)\n```", text, flags=re.IGNORECASE)
            if not match:
                raise ValueError("Invalid fence")
            text = match[1].strip()
        value = decode_json(text)
        if type(value) is not dict:
            raise ValueError("Object required")
        return value, None
    except (ValueError, TypeError, KeyError):
        return None, "invalid_review_format"


def parse_review(result):
    value, error = terminal_object(result)
    if error:
        return dict(decision="abstain", model_valid=False, reason=error)
    if set(value) != {"decision", "reason"} or type(value["decision"]) is not str or type(value["reason"]) is not str or value["decision"].strip().lower() not in ("accept", "keep"):
        return dict(decision="abstain", model_valid=False, reason="invalid_review_format")
    return dict(decision=value["decision"].strip().lower(), model_valid=True, reason=value["reason"])


def public_value(value):
    tag = value["t"]
    if tag == "none": return None
    if tag in ("bool", "str"): return value["v"]
    if tag == "int": return int(value["v"])
    if tag == "float":
        number = float.fromhex(value["v"])
        return number if math.isfinite(number) else {"nonfinite_float": value["v"]}
    if tag in ("list", "tuple"): return [public_value(item) for item in value["v"]]
    if tag == "dict": return {"dictionary_pairs": [[public_value(k), public_value(v)] for k, v in value["v"]]}
    raise ValueError("Unsupported reference encoding")


def display_record(task, case, status, reference, code_hash):
    inputs = canonical(case["input"])
    if task["entry_point"] == "find_zero":
        expected = canonical({"predicate": "finite polynomial residual with absolute value <= tolerance", "tolerance": task["atol"]})
    elif reference.get("status") == "pass" and "expected" in reference:
        expected = canonical(public_value(reference["expected"]))
    else:
        expected = canonical({"oracle": "unavailable"})
    return dict(test_id=case["case_id"], input_preview=inputs[:350], input_sha256=sha_text(inputs),
                expected_preview=expected[:150], expected_sha256=sha_text(expected),
                status=status if status in FAILURES | {"pass"} else "unknown", code_sha256=code_hash,
                truncated=len(inputs) > 350 or len(expected) > 150)


def specification(task):
    function=next(node for node in ast.parse(task["programs"]["canonical"]).body
                  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==task["entry_point"])
    return dict(entry_point=task["entry_point"],signature=ast.unparse(function.args),
                returns=ast.unparse(function.returns) if function.returns is not None else None,
                description=ast.get_docstring(function,clean=False) or "")


def safe_child(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes its declared root")
    return path


def load_frozen_module(code, filename, name):
    spec = importlib.util.spec_from_file_location(name, code / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Audit:
    def __init__(self):
        self.total = self.passed = 0
        self.failures = []
        self.warnings = []
        self.counts = {}

    def check(self, condition, name, detail=None):
        self.total += 1
        if condition:
            self.passed += 1
        elif len(self.failures) < 1000:
            self.failures.append(dict(check=name, detail=detail))
        return bool(condition)

    def finish(self):
        return dict(checks_total=self.total, checks_passed=self.passed,
                    checks_failed=self.total-self.passed, failures=self.failures,
                    warnings=self.warnings, counters=self.counts)


def expected_universe(tasks):
    repeated = set(sorted(tasks, key=lambda task: derived_seed("stability", task))[:33])
    result = {}
    for task_id, task in tasks.items():
        for cohort, intents in (("native", ("canonical_to_buggy", "buggy_to_canonical")),
                                ("generated", ("honest_repair", "adversarial_corruption"))):
            for intent in intents:
                for reviewer in REVIEWERS:
                    for arm in ARMS[cohort]:
                        for replicate in ((0, 1) if task_id in repeated else (0,)):
                            row = dict(task_id=task_id, proposal_id="t"+task_id.split("/")[1]+"-"+intent,
                                       cohort=cohort, reviewer=reviewer, arm=arm, replicate=replicate)
                            job_id = "review-" + sha_text(canonical(row))[:32]
                            result[job_id] = dict(row, split="dev" if task["split"] == "development" else task["split"],
                                                 intent="native_"+intent if cohort == "native" else intent,
                                                 proposer=None if cohort == "native" else REVIEWERS[0])
    return result


def request_body(job, request_id, proposer=False, *, protocol_hash=PROTOCOL_SHA256, structured_reviews=False):
    messages = job["messages"]
    model = REVIEWERS[0] if proposer else job["row"]["reviewer"]
    body = dict(modelId=model, messages=[], inferenceConfig=dict(maxTokens=2048 if proposer else 1024, temperature=0),
                requestMetadata=dict(experiment="final-praxis-008-code-20260914", request_id=request_id,
                                     preregistration_sha256=protocol_hash))
    system = []
    for message in messages:
        if message["role"] == "system": system.append({"text": message["content"]})
        else: body["messages"].append(dict(role=message["role"], content=[{"text": message["content"]}]))
    if system: body["system"] = system
    if structured_reviews and not proposer and model==REVIEWERS[0]:
        body["outputConfig"]={"textFormat":{"type":"json_schema","structure":{"jsonSchema":{
            "name":"experiment_response","schema":canonical(REVIEW_SCHEMA)}}}}
    return body


def audit_raw(audit, study, assignments, decisions, proposals, gates, freeze_time, *, protocol_hash=PROTOCOL_SHA256, structured_reviews=False):
    raw = study / "raw_inference"
    ledger = read_json(study / "budget.json")
    entries = ledger["entries"]
    audit.check(type(ledger["limit_usd"]) in (int, float) and ledger["limit_usd"] == 30, "ledger:frozen_limit30")
    all_requests = {path.name.removesuffix(".request.json"): path for path in raw.glob("*.request.json")}
    audit.counts["raw_request_attempts"] = len(all_requests)
    audit.counts["ledger_attempts"] = len(entries)
    unledgered = unresolved = 0
    for attempt_id, path in all_requests.items():
        record = read_json(path)
        request_id = record["request_id"]
        assigned = assignments.get(request_id)
        if not audit.check(assigned is not None, "raw:assigned_request", attempt_id): continue
        job, proposer = assigned
        eligible = job["eligible"] if proposer else job["row"]["eligible"]
        audit.check(eligible and "messages" in job, "raw:eligible_assignment", attempt_id)
        audit.check(type(record["attempt"]) is int and 1 <= record["attempt"] <= 2 and attempt_id == request_id+".attempt-"+str(record["attempt"]), "raw:attempt_identity", attempt_id)
        body = request_body(job, request_id, proposer, protocol_hash=protocol_hash, structured_reviews=structured_reviews)
        audit.check(record["request"] == body, "raw:exact_frozen_request", attempt_id)
        audit.check(record["prompt_sha256"] == sha_text(canonical(body)), "raw:request_hash", attempt_id)
        content_hash = sha_text(canonical({k:v for k,v in body.items() if k != "requestMetadata"}))
        audit.check(record["inference_input_sha256"] == content_hash, "raw:content_hash", attempt_id)
        audit.check(record["timestamp_utc"] >= freeze_time, "raw:after_source_freeze", attempt_id)
        split = job["split"] if proposer else job["row"]["split"]
        if split == "heldout":
            permitted = gates["proposer"]["pass"] if proposer else gates[job["row"]["cohort"]+"_development"]["models"][body["modelId"]]["pass"]
            audit.check(permitted is True, "raw:heldout_gate_passed", attempt_id)
        response_path, error_path = raw/(attempt_id+".response.json"), raw/(attempt_id+".error.json")
        entry = entries.get(attempt_id)
        if entry is None:
            unledgered += 1
            final = proposals.get(request_id.removeprefix("proposal-")) if proposer else decisions.get(request_id)
            state = final.get("status") if proposer else final.get("model_status")
            audit.check(state == "budget_exhausted" and not response_path.exists() and not error_path.exists(), "raw:unledgered_only_budget_prevention", attempt_id)
            continue
        amount = entry["accounted_usd"]
        audit.check(type(amount) in (int,float) and math.isfinite(amount) and amount >= 0, "ledger:finite_nonnegative_amount", attempt_id)
        audit.check(entry["model_id"] == body["modelId"], "ledger:request_model", attempt_id)
        audit.check(not (response_path.exists() and error_path.exists()), "raw:single_attempt_outcome", attempt_id)
        if response_path.exists():
            response = read_json(response_path)
            usage = response.get("usage", {})
            known = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("inputTokens", "outputTokens"))
            if known:
                price = RATES[body["modelId"]]
                expected_cost = (usage["inputTokens"]*price[0]+usage["outputTokens"]*price[1])/1e6
                audit.check(math.isclose(amount, expected_cost, abs_tol=1e-10) and entry["usage"] == usage and entry["status"]=="SUCCESS", "ledger:response_usage_cost", attempt_id)
            else:
                audit.check(entry["status"] == "MISSING_USAGE", "ledger:missing_usage_accounted", attempt_id)
        elif error_path.exists():
            error = read_json(error_path)
            rejected = error["error_type"] in {"AccessDeniedException", "ValidationException", "ResourceNotFoundException", "ThrottlingException"}
            audit.check(entry["status"] == "ERROR_"+error["error_type"], "ledger:error_status", attempt_id)
            audit.check(math.isclose(amount, 0 if rejected else entry["reserved_usd"], abs_tol=1e-10), "ledger:error_cost", attempt_id)
        else:
            unresolved += 1
            audit.check(entry["status"] == "RESERVED" and amount == entry["reserved_usd"], "ledger:unresolved_attempt_reserved", attempt_id)
    audit.check(set(entries) <= set(all_requests), "ledger:every_attempt_has_request")
    for path in raw.glob("*.result.json"):
        result = read_json(path)
        request_id = result["request_id"]
        assigned = assignments.get(request_id)
        if not audit.check(assigned is not None, "result:assigned_identity", request_id): continue
        job, proposer = assigned
        response_name = str(result["response_receipt"]).replace("\\", "/").split("/")[-1]
        request_name = str(result["request_receipt"]).replace("\\", "/").split("/")[-1]
        response, request = read_json(raw/response_name), read_json(raw/request_name)
        text = "".join(block["text"] for block in response.get("output",{}).get("message",{}).get("content",[]) if "text" in block)
        audit.check(result["text"] == text and result["finish_reason"] == response.get("stopReason") and result["usage"] == response.get("usage"), "result:raw_response_binding", request_id)
        audit.check(result["model_id"]==request["request"]["modelId"], "result:reported_model_identity", request_id)
        audit.check(result["prompt_sha256"] == request["prompt_sha256"] and result["inference_input_sha256"] == request["inference_input_sha256"] and result["preregistration_sha256"] == protocol_hash, "result:request_protocol_binding", request_id)
        if structured_reviews and not proposer and result["model_id"]==REVIEWERS[0]:
            audit.check(result.get("runtime",{}).get("structured_output") is True,"result:structured_qwen_runtime",request_id)
        if proposer:
            record = proposals[request_id.removeprefix("proposal-")]
            value, error = terminal_object(result)
            if record["status"] in ("admitted", "rejected"):
                audit.check(error is None and set(value) == {"code"} and type(value["code"]) is str, "proposal:raw_schema", request_id)
                code = value["code"].strip()+"\n"
                audit.check(record["code"] == code and record["code_sha256"] == sha_text(code), "proposal:raw_code_binding", request_id)
        else:
            record = decisions[request_id]
            parsed = parse_review(result)
            audit.check(all(record.get(key) == value for key,value in parsed.items()), "decision:independent_raw_parse", request_id)
    audit.check(all((raw/(request_id+".result.json")).exists() for request_id,row in decisions.items() if row["model_status"] == "complete"), "decision:every_complete_call_has_raw_result")
    total = math.fsum(entry["accounted_usd"] for entry in entries.values())
    audit.check(total <= 30+1e-9, "ledger:total_within30")
    audit.counts.update(accounted_api_usd_estimate=total, prevented_unledgered_budget_requests=unledgered,
                        unresolved_reserved_attempts=unresolved)
    if unresolved: audit.warnings.append("Some transport attempts lack terminal receipts; their estimated reservations remain charged and are not treated as successful generations.")
    return ledger


def audit_evidence(audit, args, tasks, jobs, proposals, offline, frozen_policies, frozen_prompts):
    study, full = args.study, args.qualification
    qualification = {row["task_id"]: row for row in read_json(full/"public/TASK_RESULTS.json")["tasks"]}
    reference_manifest = read_json(study/"REFERENCE_MANIFEST.json")
    audit.check(reference_manifest["tasks_sha256"] == sha_file(args.tasks), "evidence:task_file_hash")
    ref_meta = {row["task_id"]: row for row in reference_manifest["records"]}
    evaluations = {}
    for split in ("development", "heldout"):
        directory = args.campaign / ("generated_v2_heldout" if getattr(args,"extension",False) and split=="heldout" else "generated_"+split)
        for row in read_rows(directory/"public/PROPOSAL_RESULTS.jsonl"):
            key = row["proposal_id"]
            audit.check(key not in evaluations, "generated:unique_execution_identity", key)
            evaluations[key] = (directory, row)
    by_proposal = defaultdict(list)
    for job in jobs.values():
        row = job["row"]
        by_proposal[row["task_id"],row["cohort"],row["proposal_id"]].append(job)
    offline_by = {}
    for row in offline:
        key = (row["proposal_id"],row["replicate"],row["budget"],row["policy"])
        audit.check(key not in offline_by, "offline:unique_assigned_policy", str(key))
        offline_by[key] = row
    commitments_expected = set()
    for task_index,(task_id, task) in enumerate(sorted(tasks.items())):
        if task_index % 25 == 0:
            print(json.dumps(dict(audit_stage="evidence",source_tasks_completed=task_index,total_source_tasks=len(tasks))),flush=True)
        cases = {case["case_id"]: case for case in task["cases"]}
        audit.check(len(cases) == len(task["cases"]), "pools:unique_case_ids", task_id)
        tools = [dict(id=case["case_id"],args=case["input"]) for case in task["cases"] if case["split"] == "tool"]
        ordered = sorted(tools,key=lambda row:derived_seed("WA",task_id,row["id"]))
        W,A = ordered[:len(ordered)//2],ordered[len(ordered)//2:]
        H = [case for case in task["cases"] if case["split"] == "outcome"]
        wf = {sha_text(canonical(row["args"])) for row in W}
        af = {sha_text(canonical(row["args"])) for row in A}
        hf = {sha_text(canonical(row["input"])) for row in H}
        audit.check(not(wf&af or wf&hf or af&hf) and len(wf)==len(W) and len(af)==len(A) and len(hf)==len(H), "pools:W_A_H_input_disjoint", task_id)
        qrow = qualification[task_id]
        native, reference = {}, {}
        if qrow["eligible"]:
            for variant in ("canonical","buggy"):
                path = safe_child(full,qrow["variants"][variant]["attempt_path"])/"cases.jsonl"
                native[variant] = {row["case_id"]:row for row in read_rows(path)}
            ref_path = safe_child(full/"private",ref_meta[task_id]["path"])
            audit.check(sha_file(ref_path)==ref_meta[task_id]["sha256"], "evidence:reference_hash", task_id)
            reference = {row["case_id"]:row for row in read_rows(ref_path)}
        groups = [(key,group) for key,group in by_proposal.items() if key[0]==task_id]
        audit.check(len(groups)==4, "evidence:four_directions_per_source", task_id)
        for (_,cohort,pid), group in groups:
            original_variant = ("canonical" if pid.endswith("canonical_to_buggy") else "buggy") if cohort=="native" else proposals[pid]["original_variant"]
            original = task["programs"][original_variant]
            y0 = outcome(native[original_variant].get(c["case_id"],{}).get("status","unknown") for c in H) if qrow["eligible"] else None
            vector, proposed, y1 = {}, None, None
            if cohort=="native":
                variant = "buggy" if original_variant=="canonical" else "canonical"
                proposed = task["programs"][variant]
                if qrow["eligible"]: vector = native[variant]
            else:
                proposed = proposals[pid].get("code")
                directory,evaluation = evaluations[pid]
                audit.check(evaluation["task_id"]==task_id and evaluation["proposal_id"]==pid, "generated:execution_identity", pid)
                if qrow["eligible"] and proposals[pid]["status"]=="admitted" and evaluation.get("cases_path"):
                    path = safe_child(directory,evaluation["cases_path"])
                    audit.check(sha_file(path)==evaluation["normalized_cases_sha256"] and evaluation["code_sha256"]==sha_text(proposed), "generated:code_case_hashes", pid)
                    values = read_rows(path)
                    vector = {row["case_id"]:row for row in values}
                    audit.check(len(vector)==len(values) and set(vector)==set(cases), "generated:complete_case_identity", pid)
                    audit.check(all(row["task_id"]==task_id and row["proposal_id"]==pid and row["split"]==cases[row["case_id"]]["split"] for row in values), "generated:case_row_labels", pid)
            if vector: y1 = outcome(vector.get(c["case_id"],{}).get("status","unknown") for c in H)
            if cohort=="generated": audit.check(evaluation["y1"] is y1,"generated:reserved_outcome_label",pid)
            eligible = bool(qrow["eligible"] and y0 is not None and y1 is not None and (cohort=="native" or proposals[pid]["status"]=="admitted"))
            label = direction(y0,y1)
            code_hash = sha_text(proposed) if proposed is not None else None
            selections0 = {}
            for replicate in range(20):
                if eligible:
                    acquired = random.Random(derived_seed("supplier",task_id,replicate)).sample(sorted(W,key=lambda row:row["id"]),min(16,len(W)))
                    path = study/"commitments"/pid/("supplier_"+str(replicate)+".json")
                    commitments_expected.add(path.resolve())
                    commitment = read_json(path)
                    audit.check(commitment==dict(ids=[row["id"] for row in acquired],code_sha256=code_hash), "supplier:committed_uniform_acquisition", pid+":"+str(replicate))
                    passed = {row["id"]:vector.get(row["id"],{}).get("status")=="pass" for row in acquired}
                    # Static frozen policy replay is an artifact consistency check,
                    # not an independent implementation of the selection algorithm.
                    uniform = frozen_policies.testimony(acquired,passed,"uniform",task_id,replicate)
                    selected = frozen_policies.testimony(acquired,passed,"selected",task_id,replicate)
                    witness_args = [cases[i]["input"] for i in selected["ids"]]
                    if replicate==0:
                        selections0.update(uniform_w=uniform["ids"],selected_w=selected["ids"],
                                           supplier_count=len(acquired),supplier_feasible=selected["fully_feasible"])
                for budget in (4,8):
                    for policy in ("fixed","uniform","edit","complement","hybrid"):
                        row = offline_by.get((pid,replicate,budget,policy))
                        if not audit.check(row is not None, "offline:assigned_row_present", pid): continue
                        audit.check(row["task_id"]==task_id and row["eligible"] is eligible and row["direction"] in ({"unknown","other"} if label=="unknown" else {label}), "offline:reserved_label", pid)
                        if not eligible:
                            audit.check(row["detected"] is None and row["logical_supplier_executions"]==0 and row["logical_independent_executions"]==0, "offline:ineligible_placeholder", pid)
                            continue
                        path = study/"commitments"/pid/f"{policy}_{budget}_{replicate}.json"
                        commitments_expected.add(path.resolve())
                        selection = read_json(path)
                        ids = selection["ids"]
                        audit.check(len(ids)==len(set(ids))==min(budget,len(A)) and set(ids)<={r["id"] for r in A}, "selection:only_disjoint_A_and_budget", pid)
                        audit.check(selection["selection_commitment"]==sha_text(canonical(ids)), "selection:commitment_hash", pid)
                        if not args.skip_policy_replay:
                            replay = frozen_policies.select(A,original,proposed,witness_args,policy,task_id,replicate,budget)
                            audit.check(replay==selection, "selection:frozen_static_replay", pid+":"+policy)
                        statuses=[vector.get(i,{}).get("status","unknown") for i in ids]
                        detected=True if any(s in FAILURES for s in statuses) else False if all(s=="pass" for s in statuses) else None
                        audit.check(row["detected"] is detected and row["logical_supplier_executions"]==len(acquired) and row["logical_independent_executions"]==len(ids) and row["supplier_feasible"] is selected["fully_feasible"], "offline:measured_detection_and_budget", pid)
                        if replicate==0 and budget==8: selections0[policy]=ids
            for job in group:
                row = job["row"]
                audit.check(row["y0"] is y0 and row["y1"] is y1 and row["eligible"] is eligible, "assignment:reserved_transition", job["job_id"])
                if not eligible:
                    audit.check("messages" not in job and row["authenticated_failure"] is False, "assignment:ineligible_no_model_prompt", job["job_id"])
                    continue
                payload = decode_json(job["messages"][1]["content"])
                audit.check(set(payload)=={"task","current_implementation","proposed_implementation","specialist_recommendation","supplied_execution_records","independently_acquired_execution_records","execution_record_notice"}, "prompt:no_extra_outcome_fields", job["job_id"])
                audit.check(payload["current_implementation"]==original and payload["proposed_implementation"]==proposed, "prompt:source_code_identity", job["job_id"])
                audit.check(payload["task"]==specification(task), "prompt:public_specification_only", job["job_id"])
                arm=row["arm"]
                supplied=[] if arm=="no_witness" else selections0["uniform_w" if arm=="uniform_w" else "selected_w"]
                policy="uniform" if arm=="uniform_a" else arm
                independent=selections0[policy] if policy in ("uniform","edit","complement","hybrid") else []
                expected_records=[[display_record(task,cases[i],vector.get(i,{}).get("status","unknown"),reference.get(i,{}),code_hash) for i in ids] for ids in (supplied,independent)]
                audit.check(payload["supplied_execution_records"]==expected_records[0] and payload["independently_acquired_execution_records"]==expected_records[1], "prompt:authenticated_record_truth", job["job_id"])
                audit.check(job["messages"]==frozen_prompts.review_messages(specification(task),original,proposed,*expected_records), "prompt:exact_frozen_review_construction", job["job_id"])
                failed=any(record["status"] in FAILURES for records in expected_records for record in records)
                audit.check(row["authenticated_failure"] is failed, "enforcement:authenticated_failure_flag", job["job_id"])
                audit.check(row["logical_supplier_executions"]==(0 if arm=="no_witness" else selections0["supplier_count"]) and row["logical_independent_executions"]==len(independent), "assignment:logical_costs", job["job_id"])
    actual_commitments={path.resolve() for path in (study/"commitments").rglob("*.json")}
    audit.check(actual_commitments==commitments_expected, "selection:no_missing_or_extra_commitments")
    audit.counts["commitments_checked"]=len(commitments_expected)
    if args.skip_policy_replay:
        audit.warnings.append("Static selection replay was skipped; allowed IDs/budgets/hashes and measured evidence were checked, but exact frozen selections were not rederived.")


def audit_gates(audit, decisions, jobs, gates, *, extension=False):
    for cohort in ("native","generated"):
        for split in ("development","heldout"):
            key=cohort+"_"+split
            gate=gates[key]
            label="dev" if split=="development" else split
            observed=[row for row in decisions.values() if row["cohort"]==cohort and row["split"]==label]
            assigned=[job for job in jobs.values() if job["row"]["cohort"]==cohort and job["row"]["split"]==label]
            passed=[]
            audit.check(gate["split"]==split and gate["cohort"]==cohort, "gate:cohort_identity", key)
            for reviewer in REVIEWERS:
                rows=[row for row in observed if row["reviewer"]==reviewer and row["eligible"]]
                valid=sum(row["model_valid"] for row in rows)
                expected=dict(assigned=len(rows),valid=valid,valid_rate=valid/len(rows) if rows else None,
                              **{"pass":bool(rows) and valid/len(rows)>=.95})
                audit.check(gate["models"][reviewer]==expected, "gate:independent_counts", key+":"+reviewer)
                passed.append(expected["pass"])
            complete=len(observed)==len(assigned)
            audit.check(gate["all_assignments_accounted"] is complete and gate["pass"] is (all(passed) and complete), "gate:aggregate_arithmetic", key)
    checks={cohort:gates[cohort+"_development"]["models"][REVIEWERS[0]]["pass"] for cohort in ("native","generated")}
    expected=dict(split="development",proposer=REVIEWERS[0],checks=checks,**{"pass":all(checks.values())})
    audit.check(all(gates["proposer"].get(k)==v for k,v in expected.items()) if extension else gates["proposer"]==expected, "gate:proposer_both_development_checks")


def audit_artifacts(args, audit=None):
    audit=Audit() if audit is None else audit
    code,study=args.code,args.study
    if not audit.check(sha_file(code/"MODEL_STUDY_PREREG.md")==PROTOCOL_SHA256, "freeze:original_protocol_hash"):
        raise ValueError("This auditor targets original162d2ab; amendments require a separately identified audit configuration")
    freeze=read_json(code/"MODEL_SOURCE_FREEZE.json")
    audit.check(freeze["main_study_model_calls_before_freeze"]==0 and freeze["main_policy_results_inspected_before_freeze"] is False, "freeze:declared_preexecution_freeze")
    frozen_ok=True
    for relative,wanted in freeze["files"].items():
        frozen_ok=audit.check(sha_file(safe_child(code,relative))==wanted, "freeze:source_hash", relative) and frozen_ok
    if not frozen_ok: raise ValueError("Frozen source mismatch; do not mix results with changed source")
    print(json.dumps(dict(audit_stage="source_verified")),flush=True)
    extension=getattr(args,"extension",False)
    protocol_hash=PROTOCOL_SHA256
    if extension:
        from extension_checks import verify_extension_source
        protocol_hash=verify_extension_source(audit,args)
    frozen_policies=load_frozen_module(code,"policies.py","audited_frozen_policies")
    frozen_prompts=load_frozen_module(code,"prompts.py","audited_frozen_prompts")
    tasks_list=read_rows(args.tasks)
    tasks={task["task_id"]:task for task in tasks_list}
    audit.check(len(tasks_list)==len(tasks)==164 and set(tasks)=={"Python/"+str(i) for i in range(164)}, "assignment:all164_task_inputs")
    universe=expected_universe(tasks)
    audit.check(len(universe)==9456,"assignment:independent9456_universe")
    public=study/"public_results"
    receipt=read_json(public/"RESULTS_RECEIPT.json")
    audit.check(receipt["protocol_sha256"]==protocol_hash,"receipt:protocol")
    for name,wanted in receipt["artifacts_sha256"].items():
        audit.check(sha_file(safe_child(public,name))==wanted,"receipt:public_artifact_hash",name)
    for name,wanted in receipt["source_inputs_sha256"].items():
        root=code if name=="MODEL_SOURCE_FREEZE.json" or name.startswith("qualification/") else study
        audit.check(sha_file(safe_child(root,name))==wanted,"receipt:source_input_hash",name)
    audit.check(receipt["finalizer_sha256"]==sha_file(code/"finalize_results.py"),"receipt:finalizer_source")
    jobs,decisions,proposals,assignments,gates={}, {}, {}, {}, {}
    phase_decisions,phase_offline=[],[]
    for cohort in ("native","generated"):
        for split in ("development","heldout"):
            suffix=cohort+"_"+split
            for job in read_rows(study/("review_jobs_"+suffix+".jsonl")):
                job_id=job["job_id"]
                audit.check(job_id not in jobs,"assignment:unique_job",job_id)
                jobs[job_id]=job
                assignments[job_id]=(job,False)
            phase_decisions.extend(read_rows(study/("decisions_"+suffix+".jsonl")))
            phase_offline.extend(read_rows(study/("offline_"+suffix+".jsonl")))
            gates[suffix]=read_json(study/("GATE_"+suffix+".json"))
    audit.check(set(jobs)==set(universe),"assignment:exact_frozen_job_set")
    for job_id,job in jobs.items():
        expected=universe.get(job_id)
        audit.check(expected is not None and all(job["row"].get(key)==value for key,value in expected.items()),"assignment:exact_identity_fields",job_id)
    for row in phase_decisions:
        job_id=row["job_id"]
        audit.check(job_id not in decisions and job_id in jobs,"decision:unique_assigned_identity",job_id)
        decisions[job_id]=row
        job=jobs[job_id]
        audit.check(row["assignment_sha256"]==sha_text(canonical(job)),"decision:assignment_hash",job_id)
        audit.check(all(row.get(key)==value for key,value in job["row"].items()),"decision:assigned_metadata_unchanged",job_id)
        audit.check(type(row["model_valid"]) is bool and type(row["authenticated_failure"]) is bool,"decision:literal_boolean_flags",job_id)
        if not row["model_valid"]: audit.check(row["decision"]=="abstain","decision:invalid_output_abstains",job_id)
    for split in ("development","heldout"):
        proposal_jobs={job["proposal_id"]:job for job in read_rows(study/("proposal_jobs_"+split+".jsonl"))}
        for pid,job in proposal_jobs.items():
            assignments["proposal-"+pid]=(job,True)
            if job["eligible"]:
                task=tasks[job["task_id"]]
                wanted=frozen_prompts.proposal_messages(specification(task),task["programs"][job["original_variant"]],job["intent"])
                audit.check(job["messages"]==wanted,"prompt:exact_frozen_proposal_construction",pid)
        for row in read_rows(study/("proposals_"+split+".jsonl")):
            pid=row["proposal_id"]
            audit.check(pid not in proposals and pid in proposal_jobs,"proposal:unique_assigned_identity",pid)
            proposals[pid]=row
            audit.check(row["assignment_sha256"]==sha_text(canonical(proposal_jobs[pid])),"proposal:assignment_hash",pid)
    expected_pids={"t"+task.split("/")[1]+"-"+intent for task in tasks for intent in ("honest_repair","adversarial_corruption")}
    audit.check(set(proposals)==expected_pids and len(proposals)==328,"proposal:exact328_universe")
    gates["proposer"]=read_json(study/"PROPOSER_DEVELOPMENT_GATE.json")
    published_decisions=read_rows(public/"DECISIONS.jsonl")
    published_expected=read_rows(public/"EXPECTED_DECISIONS.jsonl")
    published_offline=read_rows(public/"OFFLINE.jsonl")
    offline_expected=read_rows(public/"EXPECTED_OFFLINE.jsonl")
    audit.check(published_decisions==phase_decisions,"receipt:decision_concatenation")
    audit.check(published_expected==[job["row"] for job in jobs.values()],"receipt:expected_job_concatenation")
    audit.check(published_offline==phase_offline,"receipt:offline_concatenation")
    audit.check(len(offline_expected)==131200,"assignment:offline131200_expected")
    audit_gates(audit,decisions,jobs,gates,extension=extension)
    print(json.dumps(dict(audit_stage="assignments_and_public_hashes_verified",checks_failed=audit.total-audit.passed)),flush=True)
    if extension:
        from extension_checks import audit_extension_lineage_and_raw
        ledger=audit_extension_lineage_and_raw(audit,args,assignments,decisions,proposals,gates,frozen_prompts)
    else:
        ledger=audit_raw(audit,study,assignments,decisions,proposals,gates,freeze["created_utc"])
    print(json.dumps(dict(audit_stage="raw_calls_checked",checks_failed=audit.total-audit.passed)),flush=True)
    audit_evidence(audit,args,tasks,jobs,proposals,published_offline,frozen_policies,frozen_prompts)
    model,acquisition=read_json(public/"MODEL_RESULTS.json"),read_json(public/"ACQUISITION_RESULTS.json")
    for name,report in (("model",model),("acquisition",acquisition)):
        audit.check(report["provenance"]["protocol_sha256"]==protocol_hash and report["provenance"]["source_inputs_sha256"]==receipt["source_inputs_sha256"],"report:provenance_consistency",name)
    flow=read_json(public/"FLOW_AND_COSTS.json")
    audit.check(flow["review_assignments"]==9456 and flow["review_records"]==len(decisions) and flow["generated_proposals"]==328 and flow["offline_assigned_rows"]==131200 and flow["offline_rows"]==len(published_offline),"flow:assignment_counts")
    audit.check(flow["model_status_counts"]==dict(Counter(row["model_status"] for row in decisions.values())),"flow:model_status_counts")
    audit.check(flow["generated_status_counts"]==dict(Counter(row["status"] for row in proposals.values())),"flow:proposal_status_counts")
    audit.check(math.isclose(flow["accounted_api_usd_estimate"],audit.counts["accounted_api_usd_estimate"],abs_tol=1e-9),"flow:ledger_cost_total")
    audit.check(flow["api_attempt_status_counts"]==dict(Counter(row["status"] for row in ledger["entries"].values())),"flow:attempt_status_counts")
    from statistical_checks import audit_statistics
    print(json.dumps(dict(audit_stage="evidence_checked_statistics_next",checks_failed=audit.total-audit.passed)),flush=True)
    for check in audit_statistics(published_decisions,published_expected,published_offline,offline_expected,model,acquisition):
        audit.check(check["passed"],"statistics:"+check["check"],check.get("detail"))
        if check.get("warning"):
            audit.warnings.append(check["warning"])
    audit.counts.update(source_tasks=len(tasks),review_jobs=len(jobs),review_records=len(decisions),generated_proposals=len(proposals),offline_rows=len(published_offline),results_receipt_sha256=sha_file(public/"RESULTS_RECEIPT.json"),protocol_sha256=protocol_hash)
    audit.warnings.append("Statistical checker independently recomputes arithmetic but is authored by the original-analysis author; authorship-independent controls/review are separate. Published bootstrap intervals are numerical inputs, not independently regenerated here.")
    audit.warnings.append("Conclusions remain conditional on135 qualified tasks; helper-namespace compatibility exclusions32/38/50 and public/pretraining exposure remain limitations. No arbitrary hostile-harness protection is established.")
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--campaign",type=Path,required=True,help="Extracted campaign root containing generated_development and generated_heldout")
    p.add_argument("--study",type=Path)
    p.add_argument("--qualification",type=Path)
    p.add_argument("--code",type=Path)
    p.add_argument("--tasks",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--skip-policy-replay",action="store_true")
    p.add_argument("--extension",action="store_true",help="Audit separately frozen V2 assembled evidence; requires --original-audit and explicit extension hash")
    p.add_argument("--original-audit",type=Path)
    p.add_argument("--extension-code",type=Path)
    p.add_argument("--extension-protocol-sha256")
    args=p.parse_args()
    args.study=args.study or args.campaign/("study_v2" if args.extension else "study")
    args.qualification=args.qualification or args.campaign/"full"
    args.code=args.code or args.campaign/"model_code"
    args.tasks=args.tasks or args.campaign/"bundle/data/tasks.jsonl"
    args.extension_code=args.extension_code or args.code/"technical_extension"
    started=datetime.datetime.now(datetime.timezone.utc)
    source_at_start=sha_file(Path(__file__))
    audit=Audit()
    complete=False
    try:
        audit_artifacts(args,audit)
        complete=True
    except Exception as error:
        audit.check(False,"audit_could_not_complete",type(error).__name__+": "+str(error))
    report=audit.finish()
    report.update(started_utc=started.isoformat(),completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  protocol_sha256=args.extension_protocol_sha256 if args.extension else PROTOCOL_SHA256,reported_frozen_commit=FROZEN_COMMIT,
                  configuration="extension_v2_with_explicit_v1_reuse" if args.extension else "original_v1",
                  auditor_sha256=source_at_start,auditor_file_unchanged_during_run=source_at_start==sha_file(Path(__file__)),mode="read_only_no_candidate_execution_or_model_calls",
                  audit_complete=complete,
                  integrity_pass=complete and report["checks_failed"]==0,
                  positive_method_claimed=False,paper_ready_claimed=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({key:report[key] for key in ("audit_complete","integrity_pass","checks_total","checks_failed","counters")}))
    return 0 if report["integrity_pass"] else 2


if __name__=="__main__":
    raise SystemExit(main())
