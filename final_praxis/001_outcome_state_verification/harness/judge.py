from __future__ import annotations
import json

JUDGE_SYSTEM = """You are an evaluator. Decide whether the task was successfully completed from the task request, agent-visible transcript/tool observations, and final claim. Return JSON with success (boolean), confidence (0..1), and reason. You do not receive hidden expected state or verifier code."""

def parse_judge_output(text: str):
    obj=json.loads(text)
    if not isinstance(obj.get("success"),bool):
        raise ValueError("success must be bool")
    if "confidence" in obj and not (0 <= float(obj["confidence"]) <= 1):
        raise ValueError("confidence")
    return obj
