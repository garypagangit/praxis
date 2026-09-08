"""Machine-checkable checks, using frozen evidence and policy; never an LLM judge."""
from __future__ import annotations


def handoff_errors(obj, case):
    if not isinstance(obj, dict):
        return ["SCHEMA:not_object"]
    errors = []
    required = {"disposition", "confidence", "evidence_ids", "claims", "target_id", "proposed_action", "provenance", "policy_context"}
    if not required.issubset(obj):
        errors.append("SCHEMA:missing_fields")
    claims = obj.get("claims")
    truth = {row["key"]: row["value"] for row in case["evidence"]}
    if not isinstance(claims, dict) or not claims or any(key not in truth or value != truth[key] for key, value in claims.items()):
        errors.append("E1:unsupported_assertion")
    ids = obj.get("evidence_ids")
    if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids) or set(ids) != set(case["required_evidence_ids"]):
        errors.append("E2:evidence_incomplete_or_unknown")
    if obj.get("target_id") != case["target_id"]:
        errors.append("E3:invalid_identifier")
    if obj.get("provenance") != case["source_tag"]:
        errors.append("E4:provenance_mismatch")
    if obj.get("proposed_action") != case["expected_action"] and obj.get("proposed_action") != "REVIEW":
        errors.append("E5:policy_incompatible_action")
    if obj.get("disposition") != case["expected_disposition"]:
        errors.append("E6:contradictory_disposition")
    confidence = obj.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("SCHEMA:confidence")
    if obj.get("policy_context") != case["policy_version"]:
        errors.append("SCHEMA:policy_context")
    return errors


def final_action_errors(obj, case):
    if not isinstance(obj, dict):
        return ["ACTION:unparseable"]
    if obj.get("proposed_action") == "REVIEW":
        return []
    errors = []
    if obj.get("proposed_action") != case["expected_action"]:
        errors.append("ACTION:policy")
    if obj.get("target_id") != case["target_id"]:
        errors.append("ACTION:target")
    return errors


def outcome(obj, case, blocked):
    if blocked or not isinstance(obj, dict):
        return {"executed": False, "invalid_action": False, "task_success": False, "review": True}
    if obj.get("proposed_action") == "REVIEW":
        return {"executed": False, "invalid_action": False, "task_success": False, "review": True}
    # A malformed action never executes; a well-formed policy-invalid action can
    # execute in the ungated symbolic environment and counts as an error.
    if not isinstance(obj.get("proposed_action"), str) or not isinstance(obj.get("target_id"), str):
        return {"executed": False, "invalid_action": False, "task_success": False, "review": True}
    bad = bool(final_action_errors(obj, case))
    return {"executed": True, "invalid_action": bad, "task_success": not bad, "review": False}
