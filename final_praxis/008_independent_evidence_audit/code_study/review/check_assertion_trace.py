"""Independent synthetic assertion-trace checks; no downloaded programs or datasets."""
from pathlib import Path
import argparse
import contextlib
import datetime
import hashlib
import importlib.util
import json

CASES = [
    {"id": "two_passes", "body": "assert candidate(1) == 1\n    assert candidate(2) == 2", "status": "pass", "error_type": None, "events": ["pass", "pass"], "unreached": []},
    {"id": "stop_after_first_false", "body": "assert candidate(1) == 2\n    assert candidate(2) == 2", "status": "fail", "error_type": "AssertionError", "events": ["fail"], "unreached": [1]},
    {"id": "failing_expression_exception", "body": "assert 1 / 0\n    assert candidate(2) == 2", "status": "exception", "error_type": "ZeroDivisionError", "events": ["exception"], "unreached": [1]},
    {"id": "false_assertion_evaluates_message", "body": "assert False, 1 / 0\n    assert candidate(2) == 2", "status": "exception", "error_type": "ZeroDivisionError", "events": ["fail"], "unreached": [1]},
    {"id": "true_assertion_does_not_evaluate_message", "body": "assert True, 1 / 0\n    assert candidate(2) == 2", "status": "pass", "error_type": None, "events": ["pass", "pass"], "unreached": []},
    {"id": "trailing_check_runs_once", "source": "calls = 0\ndef check(candidate):\n    global calls\n    calls += 1\n    assert calls == 1\ncheck(identity)\n", "status": "pass", "error_type": None, "events": ["pass"], "unreached": []},
    {"id": "message_runs_once", "source": "def check(candidate):\n    calls = []\n    def message():\n        calls.append(1)\n        return 'synthetic'\n    try:\n        assert False, message()\n    except AssertionError:\n        assert len(calls) == 1\ncheck(identity)\n", "status": "pass", "error_type": None, "events": ["fail", "pass"], "unreached": []},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("synthetic_trace_target", args.worker)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    # Windows lacks SIGALRM. These terminating trusted synthetic controls inspect
    # tracing semantics only; cloud execution separately qualifies time/isolation.
    worker.time_limit = lambda seconds: contextlib.nullcontext()
    results = []
    for case in CASES:
        source = case.get("source") or "def check(candidate):\n    " + case["body"] + "\ncheck(identity)\n"
        synthetic = {"entry_point": "identity", "original_test": source}
        # These are validator-authored three-line trusted synthetic programs only.
        result = worker.original_check(synthetic, "def identity(x):\n    return x\n")
        actual = {"status": result["status"], "error_type": result["error_type"],
                  "events": [event["status"] for event in result["assertion_events"]],
                  "unreached": result["unreached_assertion_ids"]}
        expected = {key: case[key] for key in actual}
        results.append({"id": case["id"], "expected": expected, "actual": actual, "passed": actual == expected})
    for identifier, source in [("missing_trailing_call", "def check(candidate):\n    assert True\n"),
                               ("wrong_trailing_entrypoint", "def check(candidate):\n    assert True\ncheck(other)\n")]:
        try:
            worker.original_check({"entry_point": "identity", "original_test": source}, "def identity(x):\n    return x\n")
            results.append({"id": identifier, "passed": False, "expected_exception": "ValueError", "actual_exception": None})
        except Exception as exc:
            results.append({"id": identifier, "passed": type(exc) is ValueError, "expected_exception": "ValueError", "actual_exception": type(exc).__name__})
    report = {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "Trusted validator-authored synthetic assertion programs only; no downloaded benchmark programs, model calls or cloud actions. Time-limit context replaced with nullcontext for these terminating Windows semantic tests; this does not qualify cloud sandbox/time limits.",
              "worker_sha256": hashlib.sha256(args.worker.read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "controls": len(results), "passed": sum(result["passed"] for result in results), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("controls", "passed")}))
    return 0 if report["passed"] == report["controls"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
