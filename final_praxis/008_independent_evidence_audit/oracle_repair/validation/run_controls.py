"""Run independently frozen synthetic controls against the local repaired scorer.

This adapter maps public interface names; it never calculates expected answers.
Unsupported controls are visible and do not count as passes.
"""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import importlib.util
import inspect
import json

ROOT = Path(__file__).resolve().parent


def decode_fixture(value):
    if isinstance(value, dict):
        if set(value) == {"__fixture_float__"}:
            return float(value["__fixture_float__"])
        return {key: decode_fixture(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode_fixture(item) for item in value]
    return value


def adapt_spec(contract):
    result = {"numeric_mode": "exact", "list_mode": contract.get("list_mode", "ordered")}
    for fixture_key, scorer_key in (("numeric_abs_tol", "abs_tol"), ("numeric_rel_tol", "rel_tol")):
        if fixture_key in contract:
            result[scorer_key] = contract[fixture_key]
            if contract[fixture_key]:
                result["numeric_mode"] = "tolerant"
    for key in ("columnar_mode", "path_modes", "allow_null"):
        if key in contract:
            result[key] = contract[key]
    return result


def decision_agrees(expected, actual):
    # Input-invalidity categories retain failure semantics through API status/reason.
    expected_status = {
        "invalid_prediction": "incorrect",
        "invalid_reference_identity": "invalid_reference",
        "invalid_prediction_identity": "incorrect",
    }.get(expected, expected)
    expected_correct = True if expected_status == "correct" else None if expected_status == "invalid_reference" else False
    if actual.get("status") != expected_status or actual.get("correct") is not expected_correct:
        return False
    if expected == "invalid_prediction":
        return "nonfinite" in actual.get("reason", "")
    if expected.endswith("_identity"):
        return any(word in actual.get("reason", "") for word in ("identity", "record IDs", "schema"))
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorer", type=Path, default=ROOT.parent / "scorer.py")
    parser.add_argument("--controls", type=Path, default=ROOT / "controls.json")
    parser.add_argument("--freeze", type=Path, default=ROOT / "CONTROL_FREEZE.json")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    control_raw = args.controls.read_bytes()
    frozen = json.loads(args.freeze.read_text(encoding="utf-8"))
    if hashlib.sha256(control_raw).hexdigest() != frozen["sha256"]:
        raise RuntimeError("Independent control freeze mismatch")
    controls = json.loads(control_raw)
    module_spec = importlib.util.spec_from_file_location("independently_validated_scorer", args.scorer)
    scorer = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(scorer)
    results = []
    for category in ("answer", "table"):
        for fixture in controls[category + "_controls"]:
            result = {"id": fixture["id"], "category": category, "expected": fixture["expected"]}
            reference = decode_fixture(fixture["reference"])
            prediction = decode_fixture(fixture.get("prediction"))
            state = {"missing": "missing_output"}.get(fixture.get("prediction_status"), fixture.get("prediction_status", "ok"))
            contract = dict(controls["default_" + category + "_contract"])
            contract.update(fixture.get("contract", {}))
            try:
                if category == "answer":
                    actual = scorer.score_answer(reference, prediction, spec=adapt_spec(contract), prediction_status=state)
                else:
                    table_args = {"id_columns": contract["key_columns"], "required_columns": contract["columns"]}
                    if state != "ok":
                        if "prediction_status" not in inspect.signature(scorer.score_table).parameters:
                            result.update(verdict="not_implemented", detail="score_table has no prediction_status input")
                            results.append(result)
                            continue
                        table_args["prediction_status"] = state
                    actual = scorer.score_table(reference, prediction, **table_args)
                result.update(actual=actual, verdict="pass" if decision_agrees(fixture["expected"], actual) else "fail")
            except Exception as exc:
                result.update(verdict="fail", exception=type(exc).__name__, detail=str(exc))
            results.append(result)
    counts = dict(collections.Counter(result["verdict"] for result in results))
    receipt = {
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scorer_sha256": hashlib.sha256(args.scorer.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "controls_sha256": hashlib.sha256(control_raw).hexdigest(),
        "control_freeze": frozen,
        "scorer_version": scorer.VERSION,
        "counts": counts,
        "all_controls_pass": all(result["verdict"] == "pass" for result in results),
        "scope": "Synthetic agreement and record-restoration controls only; does not establish benchmark purpose success or model capability",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"counts": counts, "all_controls_pass": receipt["all_controls_pass"], "output": str(args.output)}))
    return 0 if receipt["all_controls_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
