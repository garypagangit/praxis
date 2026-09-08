"""Infrastructure-only tests. Test stubs never enter scientific runs."""
import copy
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from .scientific_protocol import (allocation, instantiate, controlled_state, changed_value,
    parse_decision, execute_actions, write_new, digest, ROOT, visible_receipt, public_record, judge_messages)
from .task_registry import all_tasks
from .validate_fixtures import validate
from .verifier import verify, set_path
from .verify_scientific import truth, parse, bootstrap, exact_mcnemar

class ScientificInfrastructureTests(unittest.TestCase):
    def test_original_140_fixture_replay(self):
        self.assertEqual(validate(ROOT / "artifacts/fixtures/fixtures.jsonl"), [])

    def test_balanced_400_allocation(self):
        rows = allocation()
        self.assertEqual(len({row["instance_id"] for row in rows}), 400)
        self.assertEqual(set(Counter(row["task_id"] for row in rows).values()), {20})
        self.assertEqual(Counter(row["condition"] for row in rows), {"clean_success": 100, "alternate_valid": 100,
            "incomplete_completion": 50, "false_success_claim": 50, "partial_success": 50, "collateral_damage": 50})
        self.assertEqual(rows, allocation())

    def test_pilot_coverage_and_separation(self):
        rows = allocation("pilot")
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({(r["task_id"], r["condition"]) for r in rows}), 16)
        self.assertEqual(len({r["condition"] for r in rows}), 6)
        self.assertFalse({r["instance_id"] for r in rows} & {r["instance_id"] for r in allocation()})

    def test_all_400_controlled_states_independent_truth(self):
        for unit in allocation():
            spec = instantiate(unit["task_id"], unit["instance_id"])
            state, _, _ = controlled_state(spec, unit["condition"])
            expected = unit["condition"] in ("clean_success", "alternate_valid")
            self.assertEqual(verify(spec, state).success, expected)
            self.assertEqual(truth(asdict(spec), state)["success"], expected)

    def test_every_predicate_and_invariant_negative(self):
        for original in all_tasks():
            spec = instantiate(original.task_id, "fixture-0123")
            valid, _, _ = controlled_state(spec, "clean_success")
            for condition in spec.goal_conditions + spec.invariant_conditions:
                state = copy.deepcopy(valid)
                set_path(state, condition.path, changed_value(condition.expected))
                self.assertFalse(verify(spec, state).success, condition.path)
                self.assertFalse(truth(asdict(spec), state)["success"], condition.path)

    def test_alternate_path_and_set_equivalence(self):
        for task in ("F01", "F04", "D02", "C03", "W03"):
            spec = instantiate(task, "fixture-0123")
            clean, ca, _ = controlled_state(spec, "clean_success")
            alternate, aa, _ = controlled_state(spec, "alternate_valid")
            self.assertTrue(verify(spec, alternate).success)
            self.assertNotEqual(ca, aa)

    def test_missing_field_and_boolean_type_reject(self):
        spec = instantiate("F01", "fixture-0123")
        valid, _, _ = controlled_state(spec, "clean_success")
        del valid["files"]["summary"]["owner"]
        self.assertFalse(verify(spec, valid).success)
        valid, _, _ = controlled_state(spec, "clean_success")
        valid["files"]["summary"]["exists"] = 1
        self.assertFalse(verify(spec, valid).success)

    def test_mixed_type_set_rejects_without_crash(self):
        spec = instantiate("F04", "fixture-0123")
        valid, _, _ = controlled_state(spec, "clean_success")
        valid["allow"]["output"] = [1, "y", "z"]
        self.assertFalse(verify(spec, valid).success)
        self.assertFalse(truth(asdict(spec), valid)["success"])

    def test_malformed_output_is_outcome(self):
        for value in ("oops", '{"success":"true"}', '{"success":true,"reason":"ok","confidence":2}', "{}"):
            parsed, error = parse_decision(value)
            self.assertFalse(parsed["success"])
            self.assertIsNotNone(error)
            self.assertEqual(parse(value), (False, True))

    def test_fenced_json_parity(self):
        value = '```json\n{"success":true,"confidence":0.9,"reason":"observed"}\n```'
        self.assertTrue(parse_decision(value)[0]["success"])
        self.assertEqual(parse(value), (True, False))

    def test_action_execution_and_natural_state_separation(self):
        spec = instantiate("D01", "fixture-0123")
        action = {"actions": [{"path": c.path, "value": c.expected} for c in spec.goal_conditions]}
        state, actions, receipts, error = execute_actions(spec, json.dumps(action))
        self.assertTrue(verify(spec, state).success)
        controlled, _, _ = controlled_state(spec, "collateral_damage")
        self.assertFalse(verify(spec, controlled).success)
        self.assertTrue(verify(spec, state).success)
        self.assertIsNone(error)
        self.assertEqual(len(receipts), 1)

    def test_unauthorized_path_inert(self):
        spec = instantiate("D01", "fixture-0123")
        state, _, receipts, error = execute_actions(spec, '{"actions":[{"path":"external.shell","value":"anything"}]}')
        self.assertEqual(state, spec.initial_state)
        self.assertEqual(receipts[0]["status"], "unknown_path")

    def test_immutable_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            write_new(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                write_new(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text()), {"a": 1})

    def test_statistics_known_paired_case(self):
        rows = [{"task_id": str(i//10), "truth": False, "judge": i % 2 == 0, "det": False} for i in range(200)]
        ci = bootstrap(rows, replicates=1000)
        self.assertLess(ci[0], .5)
        self.assertGreater(ci[1], .5)
        result = exact_mcnemar(rows)
        self.assertEqual(result["judge_only_false_accepts"], 100)
        self.assertAlmostEqual(result["two_sided_p"], 2**-99)

if __name__ == "__main__":
    unittest.main()
