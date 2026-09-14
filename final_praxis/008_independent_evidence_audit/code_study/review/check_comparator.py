"""Independent synthetic checks; imports a side-effect-free comparator only."""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import json


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"__float__"}:
            return float(value["__float__"])
        return {key: decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    controls_path = Path(__file__).resolve().parent / "comparator_controls.json"
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    module_spec = importlib.util.spec_from_file_location("independent_compare_target", args.worker)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    results = []
    for control in controls["comparison_cases"]:
        try:
            actual = module.compare_output(control["entry_point"], decode(control["input"]),
                                           decode(control["output"]), decode(control["expected"]), control["atol"])
            passed = type(actual) is bool and actual is control["should_pass"]
            results.append({"id": control["id"], "expected": control["should_pass"], "actual": bool(actual),
                            "actual_type": type(actual).__name__, "passed": passed})
        except Exception as exc:
            results.append({"id": control["id"], "expected": control["should_pass"], "passed": False,
                            "exception": type(exc).__name__, "detail": str(exc)})
    report = {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "worker_sha256": hashlib.sha256(args.worker.read_bytes()).hexdigest(),
              "controls_sha256": hashlib.sha256(controls_path.read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "comparison_controls": len(results), "passed": sum(r["passed"] for r in results),
              "bookkeeping_controls_executed": False,
              "scope": "Synthetic comparator calls only; no benchmark candidate execution, cloud calls or model inference. Bookkeeping controls require the isolated study runner separately.",
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("comparison_controls", "passed", "bookkeeping_controls_executed")}))
    return 0 if report["passed"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
