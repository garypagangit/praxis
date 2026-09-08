from copy import deepcopy


def inject(handoff, family, case):
    """Corrupt one predefined field after real triage; retain its untouched raw output."""
    out = deepcopy(handoff) if isinstance(handoff, dict) else {"unparsed_triage": handoff}
    if family == "E1":
        claims = out.get("claims")
        out["claims"] = {**(claims if isinstance(claims, dict) else {}), "external_confirmation": "present"}
    elif family == "E2":
        out["evidence_ids"] = [case["required_evidence_ids"][0]]
    elif family == "E3":
        out["target_id"] = "UNKNOWN-999"
    elif family == "E4":
        out["provenance"] = "unverified-source-999"
    elif family == "E5":
        out["proposed_action"] = "no_action" if case["expected_action"] != "no_action" else "isolate_host"
    elif family == "E6":
        out["disposition"] = "benign" if case["expected_disposition"] != "benign" else "malicious"
    else:
        raise ValueError(f"Unknown frozen error family: {family}")
    return out
