"""Recompute raw artifact truth independently of workflow/gates/analysis code.

This verifier imports no implementation verdict functions. It reconstructs
decisions from raw response text, the pre-model scenario manifest, and arm rules.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .common import ROOT, ARMS, FAMILIES, digest, file_hash, load_json, parse_object, write_json


def independently_check(obj, case):
    if not isinstance(obj, dict):
        return ["SCHEMA:not_object"]
    problems = []
    if any(key not in obj for key in ("disposition", "confidence", "evidence_ids", "claims", "target_id", "proposed_action", "provenance", "policy_context")):
        problems.append("SCHEMA:missing_fields")
    allowed_claims = dict((e["key"], e["value"]) for e in case["evidence"])
    claims = obj.get("claims")
    if not isinstance(claims, dict) or not claims or any(k not in allowed_claims or allowed_claims[k] != v for k, v in claims.items()):
        problems.append("E1:unsupported_assertion")
    evidence = obj.get("evidence_ids")
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence) or sorted(set(evidence)) != sorted(case["required_evidence_ids"]):
        problems.append("E2:evidence_incomplete_or_unknown")
    if obj.get("target_id") != case["target_id"]:
        problems.append("E3:invalid_identifier")
    if obj.get("provenance") != case["source_tag"]:
        problems.append("E4:provenance_mismatch")
    if obj.get("proposed_action") not in (case["expected_action"], "REVIEW"):
        problems.append("E5:policy_incompatible_action")
    if obj.get("disposition") != case["expected_disposition"]:
        problems.append("E6:contradictory_disposition")
    confidence = obj.get("confidence")
    if type(confidence) not in (float, int) or not 0 <= confidence <= 1:
        problems.append("SCHEMA:confidence")
    if obj.get("policy_context") != case["policy_version"]:
        problems.append("SCHEMA:policy_context")
    return problems


def independently_inject(parsed, case):
    obj = json.loads(json.dumps(parsed)) if isinstance(parsed, dict) else {"unparsed_triage": parsed}
    family = case["family"]
    if family == "E1":
        old = obj.get("claims")
        obj["claims"] = dict(old) if isinstance(old, dict) else {}
        obj["claims"]["external_confirmation"] = "present"
    elif family == "E2": obj["evidence_ids"] = [case["required_evidence_ids"][0]]
    elif family == "E3": obj["target_id"] = "UNKNOWN-999"
    elif family == "E4": obj["provenance"] = "unverified-source-999"
    elif family == "E5": obj["proposed_action"] = "no_action" if case["expected_action"] != "no_action" else "isolate_host"
    elif family == "E6": obj["disposition"] = "benign" if case["expected_disposition"] != "benign" else "malicious"
    return obj


def action_errors(obj, case):
    if not isinstance(obj, dict): return ["ACTION:unparseable"]
    if obj.get("proposed_action") == "REVIEW": return []
    result = []
    if obj.get("proposed_action") != case["expected_action"]: result.append("ACTION:policy")
    if obj.get("target_id") != case["target_id"]: result.append("ACTION:target")
    return result


def verify_record(record, case, config=None):
    errors = []
    previous = None
    blocked = False
    valid_stages = []
    prefix = f"{case['case_id']}:{record['arm']}"
    if record["case_id"] != case["case_id"] or record["condition"] != case["condition"] or record["family"] != case["family"]:
        errors.append(prefix + ":case_metadata")
    for index, stage in enumerate(record["stages"]):
        if blocked or index > 2: errors.append(prefix + ":stage_after_terminal")
        if stage["stage"] != ("triage", "investigation", "response")[min(index, 2)]: errors.append(prefix + ":stage_order")
        response = stage["raw_response"]
        if config and (response.get("model_id") != config["model_id"] or response.get("revision") != config["model_revision"]):
            errors.append(prefix + ":model_identity")
        if config and (response.get("model_id", "").startswith("FIXTURE") or not response.get("request_id")):
            errors.append(prefix + ":missing_real_generation_identity")
        if config and config.get("require_runtime_metadata"):
            runtime = response.get("runtime", {})
            if runtime.get("dtype") != "bfloat16" or runtime.get("quantization") is not None or runtime.get("attention") != "sdpa" or runtime.get("seed") != config["seed"]:
                errors.append(prefix + ":runtime_identity")
        # Bind the archived request to authoritative evidence and the actual
        # previous handoff, independently of the runner's message constructor.
        try:
            request = json.loads(stage["messages"][1]["content"])
            public_keys = ("context", "target_id", "target_kind", "source_tag", "evidence", "required_evidence_ids", "policy_version")
            if request["task"] != {key:case[key] for key in public_keys}:
                errors.append(prefix + ":request_case_binding")
            if request.get("previous_agent_handoff") != previous:
                errors.append(prefix + ":request_handoff_binding")
        except (ValueError, TypeError, KeyError, IndexError):
            errors.append(prefix + ":request_schema")
        try: parsed = parse_object(response["text"])
        except (ValueError, TypeError): parsed = None
        forwarded = independently_inject(parsed, case) if index == 0 and case["condition"] == "injected" else parsed
        if forwarded != stage["forwarded_handoff"] or parsed != stage["parsed"]: errors.append(prefix + ":raw_reconstruction")
        if stage["parent_handoff_hash"] != (digest(previous) if index else case["source_hash"]): errors.append(prefix + ":lineage")
        if stage["handoff_hash"] != digest(forwarded): errors.append(prefix + ":handoff_hash")
        reasons = independently_check(forwarded, case)
        gate = "handoff" if index < 2 and record["arm"] in ("A2", "A3") else ("final_action" if index == 2 and record["arm"] in ("A1", "A3") else "none")
        gate_reasons = reasons if gate == "handoff" else (action_errors(forwarded, case) if gate == "final_action" else [])
        blocked = bool(gate_reasons)
        if reasons != stage["errors"] or gate != stage["gate_kind"] or gate_reasons != stage["gate_errors"] or blocked != stage["blocked"]: errors.append(prefix + ":gate_reconstruction")
        valid_stages.append({"errors": reasons, "raw_response": response})
        previous = forwarded
    if not valid_stages or (not blocked and len(valid_stages) != 3): errors.append(prefix + ":missing_stage")
    depth = 0
    for stage in valid_stages[1:]:
        if not stage["errors"]: break
        depth += 1
    first_invalid = next((i for i, stage in enumerate(valid_stages) if stage["errors"]), None)
    executed = (not blocked and isinstance(previous, dict) and previous.get("proposed_action") != "REVIEW" and isinstance(previous.get("proposed_action"), str) and isinstance(previous.get("target_id"), str))
    invalid_action = bool(executed and action_errors(previous, case))
    rebuilt = {"executed": executed, "invalid_action": invalid_action, "task_success": bool(executed and not invalid_action), "review": not executed}
    if record["outcome"] != rebuilt or record["propagation_depth"] != depth or record["first_invalid_stage"] != first_invalid or record["blocked"] != blocked: errors.append(prefix + ":outcome_reconstruction")
    row = {"case_id": case["case_id"], "base_id": case["base_id"], "condition": case["condition"], "family": case["family"], "arm": record["arm"],
           "invalid_action": int(invalid_action), "success": int(rebuilt["task_success"]), "review": int(rebuilt["review"]), "blocked": int(blocked), "depth": depth,
           "stage_count": len(valid_stages), "first_invalid_stage": first_invalid,
           "prompt_tokens": sum(s["raw_response"].get("prompt_tokens", 0) for s in valid_stages),
           "completion_tokens": sum(s["raw_response"].get("completion_tokens", 0) for s in valid_stages),
           "stage_errors": [s["errors"] for s in valid_stages],
           "elapsed_seconds": sum(stage.get("elapsed_seconds", 0) for stage in record["stages"])}
    return errors, row


def verify_run(run_dir):
    run_dir = Path(run_dir)
    manifest = load_json(run_dir / "RUN_MANIFEST.json")
    config = load_json(ROOT / "configs" / "experiment.json")
    frozen = load_json(ROOT / "FROZEN_PROTOCOL.json")
    cases = {row["case_id"]: row for row in load_json(ROOT / "configs" / "scenarios.json")}
    errors, rows = [], []
    for path, wanted in frozen["files"].items():
        if not (ROOT / path).exists() or file_hash(ROOT / path) != wanted: errors.append("frozen_hash:" + path)
    if manifest["protocol_hash"] != file_hash(ROOT / "FROZEN_PROTOCOL.json"): errors.append("run_protocol_hash")
    if manifest.get("config") != config or manifest.get("evidence_kind") != "real_model_inference": errors.append("run_config_or_evidence_kind")
    expected_ids = manifest["case_ids"]
    expected = {(case_id, arm) for case_id in expected_ids for arm in ARMS}
    seen = set()
    for path in sorted((run_dir / "records").glob("*.json")):
        record = load_json(path)
        key = (record["case_id"], record["arm"])
        if key in seen: errors.append("duplicate:" + str(key))
        seen.add(key)
        if key[0] not in cases: errors.append("unknown_case:" + key[0]); continue
        if record.get("protocol_hash") != manifest["protocol_hash"] or record.get("seed") != config["seed"] or record.get("evidence_kind") != "real_model_inference":
            errors.append("record_protocol_or_evidence_kind:" + str(key))
        issues, row = verify_record(record, cases[key[0]], config)
        errors.extend(issues)
        for stage in record["stages"]:
            raw_path = run_dir / stage["raw_path"]
            if not raw_path.exists(): errors.append("missing_raw:" + str(raw_path)); continue
            raw = load_json(raw_path)
            if raw != {k:v for k,v in stage.items() if k != "raw_path"}: errors.append("raw_pointer_mismatch:" + str(raw_path))
        rows.append(row)
    if seen != expected: errors.append(f"denominators:expected={len(expected)} actual={len(seen)} missing={sorted(expected-seen)} extra={sorted(seen-expected)}")
    if manifest["mode"] == "discovery" and (len(seen) != 480 or set(expected_ids) != set(cases)): errors.append("discovery_not_480")
    audit = {"status": "PASS" if not errors else "FAIL", "mode": manifest["mode"], "record_count": len(rows), "errors": errors, "protocol_hash": manifest["protocol_hash"], "rows": rows}
    write_json(run_dir / "verification" / "audit.json", audit)
    (run_dir / "verification" / "INDEPENDENT_VERIFICATION.md").write_text(f"# Independent verification\n\nStatus: **{audit['status']}**\n\nRecords: {len(rows)}. Raw responses, model identities, frozen hashes, handoffs, gates, action truth, propagation depth and denominators independently recomputed.\n\n" + "\n".join("- " + err for err in errors) + "\n", encoding="utf-8")
    return audit


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("run_dir"); args = p.parse_args()
    audit = verify_run(args.run_dir)
    print(json.dumps({k:v for k,v in audit.items() if k != "rows"}, indent=2))
    raise SystemExit(0 if audit["status"] == "PASS" else 1)
