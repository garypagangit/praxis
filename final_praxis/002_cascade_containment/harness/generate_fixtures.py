"""Synthetic fixtures only; these never substitute for scientific model responses."""
from __future__ import annotations
import json
from copy import deepcopy
from .common import ARMS, ROOT, write_json, file_hash
from .scenario_registry import build_scenarios, expected_handoff, POLICY
from .inject_errors import inject
from .workflow import run_one


def fixture_record(case, arm, behavior="propagate"):
    config = {"model_id": "FIXTURE_ONLY", "model_revision": "synthetic-v1", "temperature": 0, "max_new_tokens": 256}
    count = 0
    def generate(messages, **kwargs):
        nonlocal count
        obj = expected_handoff(case)
        if count > 0 and case["condition"] == "injected" and behavior == "propagate":
            obj = inject(obj, case["family"], case)
        count += 1
        return {"text": json.dumps(obj), "model_id": "FIXTURE_ONLY", "revision": "synthetic-v1", "prompt_tokens": 0, "completion_tokens": 0, "request_id": f"fixture-{count}"}
    result = run_one(case, arm, generate, POLICY, config)
    result["evidence_kind"] = "synthetic_fixture"
    # Wall time/timestamp are deliberately absent from the deterministic digest.
    for stage in result["stages"]:
        stage["timestamp"] = "FIXTURE"
        stage["elapsed_seconds"] = 0.0
    return result


def generate_all():
    cases = [case for case in build_scenarios() if case["index"] < 3]
    return [fixture_record(case, arm) for case in cases for arm in ARMS]


if __name__ == "__main__":
    path = ROOT / "artifacts" / "fixtures" / "fixtures.json"
    write_json(path, generate_all())
    print(json.dumps({"fixtures": 144, "sha256": file_hash(path)}))
