"""Independent generated-execution outcome/signature controls; no code execution."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generated_execution as execution
import study_runner as runner


class GeneratedControls(unittest.TestCase):
    def test_reserved_full_pass(self):
        self.assertIs(execution.outcome_label([dict(split="outcome", status="pass")] * 2), True)
        self.assertIs(runner.result_y(["pass", "pass"]), True)

    def test_demonstrated_failure_survives_incompleteness(self):
        for status in ("fail", "exception", "timeout", "program_load_error"):
            rows = [dict(split="outcome", status=status), dict(split="outcome", status="not_run_worker_incomplete")]
            self.assertIs(execution.outcome_label(rows), False)
            self.assertIs(runner.result_y([r["status"] for r in rows]), False)

    def test_infrastructure_or_absence_is_unknown(self):
        for statuses in ([], ["not_run_worker_incomplete"], ["pass", "not_run_worker_incomplete"], ["not_executed_rejected"]):
            self.assertIsNone(execution.outcome_label([dict(split="outcome", status=s) for s in statuses]))
            self.assertIsNone(runner.result_y(statuses))

    def test_tool_failure_does_not_define_reserved_direction(self):
        rows = [dict(split="tool", status="fail"), dict(split="outcome", status="pass")]
        self.assertIs(execution.outcome_label(rows), True)
        self.assertIsNone(execution.outcome_label(rows[:1]))

    def test_signature_checks_defaults_names_and_return_annotation(self):
        baseline = "def f(x: int, y=1) -> int:\n    return x + y\n"
        same = "def f(x: int, y=1) -> int:\n    return x - y\n"
        self.assertEqual(execution.signature(baseline, "f"), execution.signature(same, "f"))
        for altered in (same.replace("y=1", "y=2"), same.replace("x: int", "z: int"), same.replace("-> int", "-> float")):
            self.assertNotEqual(execution.signature(baseline, "f"), execution.signature(altered, "f"))

    def test_repeated_or_missing_entry_rejected_without_executing(self):
        for source in ("def other(x):\n    return x\n", "def f(x):\n    return x\ndef f(x):\n    return 2*x\n"):
            with self.assertRaises(ValueError):
                execution.signature(source, "f")

    def test_display_records_preserve_unknown_and_residual_predicate(self):
        task = dict(entry_point="find_zero", atol=1e-6)
        row = runner.execution_record(task, dict(case_id="case", input=[[1, 2]]),
                                      dict(status="not_run_worker_incomplete"),
                                      dict(status="pass", expected=dict(t="int", v="999")), "a" * 64)
        self.assertEqual(row["status"], "unknown")
        self.assertIn("polynomial residual", row["expected_preview"])
        self.assertNotIn("999", row["expected_preview"])
        self.assertEqual(row["expected_sha256"], hashlib.sha256(row["expected_preview"].encode()).hexdigest())


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeneratedControls))
    receipt = dict(scope="Independent pure metadata/AST controls; no candidate or downloaded benchmark program executed",
                   tests_run=result.testsRun, passed=result.testsRun-len(result.failures)-len(result.errors),
                   failures=[str(t) for t, _ in result.failures], errors=[str(t) for t, _ in result.errors],
                   source_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                  for name in ("generated_execution.py", "study_runner.py", "qualification/worker.py")},
                   control_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    Path(__file__).with_name("GENERATED_METADATA_REVIEW.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
