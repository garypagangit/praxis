"""Strict response parsing: malformed or refused outputs count as abstentions."""
import json

def disposition(text):
    try:
        value = json.loads(text.strip())
        answer = value.get("disposition", "").lower().strip()
        return answer if answer in ("benign", "malicious", "abstain") else "abstain"
    except (ValueError, AttributeError, TypeError):
        return "abstain"

def validate_trace(case, trace):
    assert len(trace) == 8, "missing rounds"
    for r, row in enumerate(trace, 1):
        assert row["case_id"] == case["case_id"] and row["round"] == r
        assert row["evidence_ids"] == [e["evidence_id"] for e in case["evidence"][:r]]
        assert row["disposition"] == disposition(row["raw_response"])
        assert row["correct"] == (row["disposition"] == case["label"])
        assert isinstance(row["token_count"], int) and row["token_count"] > 0
