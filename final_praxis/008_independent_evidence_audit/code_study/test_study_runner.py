"""Authored fixtures verify end-to-end assignment and information boundaries."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import study_runner as run
import prompts


class RunnerTests(unittest.TestCase):
    def test_proposal_gate_rejection_budget_and_cache_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = 'def f(x: int) -> int:\n    """Return x."""\n    return x\n'
            job = {"task_id": "Python/0", "split": "development", "proposal_id": "fixture-a",
                   "intent": "honest_repair", "original_variant": "buggy", "proposer": prompts.PROPOSER,
                   "eligible": True, "entry_point": "f", "original_signature": prompts.specification(code, "f"),
                   "original_code_sha256": run.digest(code), "messages": prompts.proposal_messages(prompts.specification(code, "f"), code, "honest_repair")}
            run.save_rows(root / "jobs.jsonl", [job])
            args = SimpleNamespace(jobs=root / "jobs.jsonl", output=root, split="development", workers=1, profile="unused")
            class WrongEntry:
                def generate(self, *a, **kw):
                    return {"finish_reason": "end_turn", "text": json.dumps({"code": "def other(x): return x"})}
            with patch.object(run, "create_adapter", return_value=WrongEntry()):
                run.infer_proposals(args)
                self.assertEqual(run.read(root / "proposals" / "fixture-a.json")["status"], "rejected")
                changed = dict(job, intent="adversarial_corruption")
                (root / "jobs.jsonl").write_text(json.dumps(changed) + "\n")
                with self.assertRaisesRegex(ValueError, "assignment hash"):
                    run.infer_proposals(args)
            budget_root = root / "budget_case"
            run.save_rows(budget_root / "jobs.jsonl", [job])
            class NoBudget:
                def generate(self, *a, **kw):
                    raise run.BudgetExceeded("fixture")
            args.output = budget_root
            args.jobs = budget_root / "jobs.jsonl"
            with patch.object(run, "create_adapter", return_value=NoBudget()):
                run.infer_proposals(args)
            self.assertEqual(run.read(budget_root / "proposals" / "fixture-a.json")["status"], "budget_exhausted")
            held_root = root / "heldout_case"
            run.save_rows(held_root / "jobs.jsonl", [dict(job, split="heldout")])
            run.save(held_root / "gate.json", {"split": "development", "proposer": prompts.PROPOSER, "pass": False})
            args.output, args.jobs, args.split, args.gate = held_root, held_root / "jobs.jsonl", "heldout", held_root / "gate.json"
            with patch.object(run, "create_adapter") as adapter:
                run.infer_proposals(args)
                adapter.return_value.generate.assert_not_called()
            self.assertEqual(run.read(held_root / "proposals" / "fixture-a.json")["status"], "not_run_development_gate")

    def test_nullable_correctness(self):
        self.assertIsNone(run.result_y([]))
        self.assertIsNone(run.result_y(["pass", "not_run_task_budget"]))
        self.assertIs(run.result_y(["timeout", "not_run_task_budget"]), False)
        self.assertIs(run.result_y(["pass", "pass"]), True)
        self.assertEqual(run.direction(True, False), "harmful")
        self.assertEqual(run.direction(False, True), "useful")
        self.assertEqual(run.direction(None, True), "other")

    def test_find_zero_record_describes_predicate(self):
        code = "def f(x): return x\n"
        rec = run.execution_record({"entry_point": "find_zero", "atol": 1e-6},
                                   {"case_id": "a", "input": [[-1, 0, 1]]},
                                   {"status": "pass"}, {"expected": {"t": "float", "v": float(1).hex()}, "status": "pass"}, run.digest(code))
        self.assertIn("residual", rec["expected_preview"])
        prompts.validate_records([rec], code)

    def test_fixture_assignments_prompt_boundary_and_mock_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qualification = root / "qualification"
            output = root / "study"
            canonical = 'def f(x: int) -> int:\n    """Return x."""\n    return x\n'
            buggy = 'def f(x: int) -> int:\n    """Return x."""\n    return x + 1\n'
            cases = [{"case_id": f"c{i:02d}", "input": [i], "split": "tool" if i < 32 else "outcome"} for i in range(40)]
            tasks = [{"task_id": "Python/" + str(i), "split": "development" if i < 41 else "heldout",
                      "entry_point": "f", "atol": 0, "cases": cases,
                      "programs": {"canonical": canonical, "buggy": buggy}} for i in range(164)]
            qrows = []
            for i, task in enumerate(tasks):
                variants = {}
                if i == 0:
                    base = qualification / "private" / "task_0"
                    reference = [dict(c, task_id=task["task_id"], variant="reference", status="pass", expected={"t": "int", "v": str(c["input"][0])}) for c in cases]
                    run.save_rows(base / "reference_complete.jsonl", reference)
                    for variant in ("canonical", "buggy"):
                        path = base / variant / "attempt_001"
                        vector = [dict(c, task_id=task["task_id"], variant=variant, status="pass" if variant == "canonical" or c["input"][0] % 2 == 0 else "fail") for c in cases]
                        run.save_rows(path / "cases.jsonl", vector)
                        run.save(path / "summary.json", {"code_sha256": run.digest(task["programs"][variant]), "assigned_cases": len(cases)})
                        variants[variant] = {"attempt_path": str(path.relative_to(qualification))}
                qrows.append({"task_id": task["task_id"], "eligible": i == 0, "exclusion_reasons": [] if i == 0 else ["fixture_ineligible"], "variants": variants})
            run.save_rows(root / "tasks.jsonl", tasks)
            run.save(qualification / "public" / "TASK_RESULTS.json", {"tasks": qrows})
            run.save(qualification / "public" / "SUMMARY.json", {"qualification_hypothesis_pass": True})
            args = SimpleNamespace(tasks=root / "tasks.jsonl", qualification=qualification, output=output,
                                   split="development", cohort="native", proposals=None, evaluations=None)
            run.prepare_reviews(args)
            jobs = run.rows(output / "review_jobs_native_development.jsonl")
            offline = run.rows(output / "offline_native_development.jsonl")
            self.assertEqual(len(offline), 41 * 2 * 20 * 2 * 5)
            self.assertEqual(sum(r["eligible"] for r in offline), 2 * 20 * 2 * 5)
            self.assertEqual({j["row"]["direction"] for j in jobs if "messages" in j}, {"harmful", "useful"})
            for job in jobs:
                if "messages" not in job:
                    self.assertFalse(job["row"]["eligible"])
                    continue
                payload = json.loads(job["messages"][1]["content"])
                self.assertNotIn("task_id", payload)
                self.assertNotIn("direction", payload)
                self.assertNotIn("y1", payload)
                displayed = payload["supplied_execution_records"] + payload["independently_acquired_execution_records"]
                self.assertTrue(all(r["test_id"] < "c32" for r in displayed))
                self.assertEqual(len({r["test_id"] for r in displayed}), len(displayed))
            class Fake:
                def generate(self, messages, **kwargs):
                    return {"finish_reason": "end_turn", "text": '{"decision":"accept","reason":"fixture"}', "usage": {"inputTokens": 1, "outputTokens": 1}}
            infer = SimpleNamespace(jobs=output / "review_jobs_native_development.jsonl", output=output,
                                    split="development", cohort="native", workers=2, profile="unused")
            with patch.object(run, "create_adapter", return_value=Fake()):
                run.infer_reviews(infer)
                run.infer_reviews(infer)  # Immutable per-request recovery, no duplicates.
            decisions = run.rows(output / "decisions_native_development.jsonl")
            self.assertEqual(len(decisions), len(jobs))
            self.assertEqual(sum(d["model_valid"] for d in decisions), sum("messages" in j for j in jobs))
            self.assertTrue(run.read(output / "GATE_native_development.json")["pass"])


if __name__ == "__main__":
    unittest.main()
