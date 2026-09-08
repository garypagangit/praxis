from __future__ import annotations
import json
from .common import ROOT, ARMS, file_hash, load_json, write_json
from .generate_fixtures import generate_all, fixture_record
from .scenario_registry import build_scenarios, expected_handoff
from .gates import handoff_errors
from .independent_verify import verify_record


def validate():
    cases = {case["case_id"]: case for case in build_scenarios()}
    records = load_json(ROOT / "artifacts" / "fixtures" / "fixtures.json")
    errors = []
    expected = {(case["case_id"], arm) for case in cases.values() if case["index"] < 3 for arm in ARMS}
    actual = [(record["case_id"], record["arm"]) for record in records]
    if set(actual) != expected or len(actual) != 144: errors.append("coverage_or_duplicate")
    if records != generate_all(): errors.append("deterministic_regeneration")
    for record in records:
        case = cases[record["case_id"]]
        issues, row = verify_record(record, case)
        errors.extend(issues)
        if case["condition"] == "clean" and not row["success"]: errors.append("clean_utility:" + case["case_id"])
        if case["condition"] == "injected":
            if record["arm"] in ("A2", "A3") and (not row["blocked"] or row["depth"] != 0): errors.append("handoff_containment")
            if record["arm"] in ("A0", "A1") and row["depth"] != 2: errors.append("propagation_attribution")
    # Independent verifier must detect altered raw evidence/summary fields.
    import copy
    tampered = copy.deepcopy(records[0]); tampered["outcome"]["task_success"] = False
    if not verify_record(tampered, cases[tampered["case_id"]])[0]: errors.append("tamper_detection")
    case = next(c for c in cases.values() if c["condition"] == "injected")
    corrected = fixture_record(case, "A0", behavior="correct")
    if corrected["propagation_depth"] != 0 or not corrected["outcome"]["task_success"]: errors.append("model_correction_path")
    malformed = [None, {}, {**expected_handoff(case), "confidence": True}, {**expected_handoff(case), "evidence_ids": [{}]}, {**expected_handoff(case), "claims": []}]
    if any(not handoff_errors(obj, case) for obj in malformed): errors.append("malformed_output_handling")
    result = {"status": "PASS" if not errors else "FAIL", "fixture_count": 144, "additional_checks": 7, "errors": errors,
              "fixture_sha256": file_hash(ROOT / "artifacts" / "fixtures" / "fixtures.json"), "evidence_kind": "synthetic_fixture_only"}
    write_json(ROOT / "artifacts" / "fixtures" / "FIXTURE_GATE.json", result)
    (ROOT / "FIXTURE_GATE.md").write_text("# Final Praxis 002 fixture gate\n\nStatus: **" + result["status"] + "**\n\n144 workflow fixtures: 6 error families × 3 base scenarios × 2 matched conditions × 4 arms. Seven additional malformed-output, correction and tamper checks. Deterministic regeneration and independent raw reconstruction checked.\n\nSHA-256: `" + result["fixture_sha256"] + "`\n\nThis is infrastructure evidence only. No scientific model inference or final scientific classification.\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, indent=2)); raise SystemExit(0 if result["status"] == "PASS" else 1)
