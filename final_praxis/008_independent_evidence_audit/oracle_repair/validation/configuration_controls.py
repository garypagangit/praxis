"""Additional source-review checks for exact count precision and bad configurations."""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorer", type=Path, default=Path(__file__).resolve().parent.parent / "scorer.py")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("precision_validated_scorer", args.scorer)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    # Each expected result is written explicitly; none derives from scorer output.
    decisions = [
        ("count_above_float_precision_identity", lambda: scorer.score_answer(9007199254740993, 9007199254740993), "correct", True),
        ("count_above_float_precision_off_by_one", lambda: scorer.score_answer(9007199254740993, 9007199254740992), "incorrect", False),
        ("count_above_float_precision_lossy_float", lambda: scorer.score_answer(9007199254740993, 9007199254740992.0), "incorrect", False),
        ("null_forbidden_reference", lambda: scorer.score_answer(None, None, spec={"allow_null": False}), "invalid_reference", None),
        ("null_forbidden_prediction", lambda: scorer.score_answer(1, None, spec={"allow_null": False}), "incorrect", False),
        ("nonstring_reference_mapping_key", lambda: scorer.score_answer({1: "a"}, {1: "a"}), "invalid_reference", None),
        ("nonstring_prediction_mapping_key", lambda: scorer.score_answer({"1": "a"}, {1: "a"}), "incorrect", False),
        ("invalid_reference_precedes_missing_prediction", lambda: scorer.score_answer(float("nan"), prediction_status="missing_output"), "invalid_reference", None),
    ]
    rejected_configurations = [
        ("unknown_numeric_mode", lambda: scorer.score_answer(1, 1, spec={"numeric_mode": "approximate"})),
        ("unknown_list_mode", lambda: scorer.score_answer([], [], spec={"list_mode": "unordered"})),
        ("unknown_path_mode", lambda: scorer.score_answer([], [], spec={"path_modes": {"": "unordered"}})),
        ("unknown_columnar_mode", lambda: scorer.score_answer({}, {}, spec={"columnar_mode": "set"})),
        ("negative_absolute_tolerance", lambda: scorer.score_answer(1, 1, spec={"abs_tol": -1})),
        ("infinite_relative_tolerance", lambda: scorer.score_answer(1, 1, spec={"rel_tol": float("inf")})),
        ("nan_absolute_tolerance", lambda: scorer.score_answer(1, 1, spec={"abs_tol": float("nan")})),
        ("boolean_tolerance", lambda: scorer.score_answer(1, 1, spec={"abs_tol": True})),
        ("unknown_prediction_status", lambda: scorer.score_answer(1, 1, prediction_status="unknown")),
    ]
    results = []
    for name, action, status, correct in decisions:
        try:
            actual = action()
            results.append({"id": name, "expected_status": status, "expected_correct": correct, "actual": actual,
                            "pass": actual.get("status") == status and actual.get("correct") is correct})
        except Exception as exc:
            results.append({"id": name, "pass": False, "exception": type(exc).__name__, "detail": str(exc)})
    for name, action in rejected_configurations:
        try:
            actual = action()
            results.append({"id": name, "expected_exception": "ValueError", "actual": actual, "pass": False})
        except Exception as exc:
            results.append({"id": name, "expected_exception": "ValueError", "exception": type(exc).__name__, "pass": type(exc) is ValueError})
    report = {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "provenance": "Manually specified supplementary source-review controls, not blinded pre-implementation controls",
              "scorer_sha256": hashlib.sha256(args.scorer.read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "total": len(results), "passed": sum(x["pass"] for x in results), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "scorer_sha256")}))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
