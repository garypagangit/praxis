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
from .verify_scientific import (truth, parse, bootstrap, exact_mcnemar, verify_manifest_binding,
    check_inference_binding, independent_projection, independently_public_record)

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

    def test_manifest_threshold_and_model_tamper_rejected(self):
        config = {"promotion_gates": {"judge_fsar_nontrivial_floor": .10}, "agent": {"revision": "original"}}
        freeze = {"artifact_hashes": {"config.json": "abc"}}
        manifest = {"experiment_id": "Final Praxis 001", "stage": "discovery", "config": config,
                    "frozen_artifacts": freeze["artifact_hashes"]}
        verify_manifest_binding(manifest, freeze, config)
        for field in ("threshold", "model", "stage"):
            altered = copy.deepcopy(manifest)
            if field == "threshold": altered["config"]["promotion_gates"]["judge_fsar_nontrivial_floor"] = 0
            elif field == "model": altered["config"]["agent"]["revision"] = "different"
            else: altered["stage"] = "unregistered"
            with self.assertRaises(ValueError): verify_manifest_binding(altered, freeze, config)

    def test_manifest_input_ledger_tamper_rejected(self):
        config, freeze = {"frozen": True}, {"artifact_hashes": {"source.py": "abc"}}
        manifest = {"experiment_id": "Final Praxis 001", "stage": "pilot", "config": config,
                    "frozen_artifacts": {"source.py": "altered"}}
        with self.assertRaisesRegex(ValueError, "frozen_artifacts"):
            verify_manifest_binding(manifest, freeze, config)

    def test_independent_state_projection_and_public_receipts(self):
        for unit in allocation("pilot"):
            spec = instantiate(unit["task_id"], unit["instance_id"])
            state, actions, mutations = controlled_state(spec, unit["condition"])
            self.assertEqual(independent_projection(asdict(spec), unit["condition"]), (state, actions, mutations))
            text = json.dumps({"actions": actions})
            expected = public_record(spec, unit, actions, visible_receipt(state, actions))
            self.assertEqual(independently_public_record(spec, unit, text, state), expected)

    def test_inference_prompt_and_runtime_tamper_rejected(self):
        # Isolated temporary test fixture only; never a scientific adapter or output.
        model = {"model_id": "FIXTURE_ONLY", "revision": "fixture"}
        config = {"infrastructure_retry_max": 2, "runtime_target": {"attention": "sdpa"},
                  "dtype": "bfloat16", "quantization": None, "seed": 20260908}
        messages = [{"role": "user", "content": "isolated infrastructure fixture"}]
        payload = {"messages": messages, "model": model, "max_new_tokens": 10, "temperature": 0.0}
        response = {**model, "text": "fixture", "request_id": "fixture-only", "timestamp_utc": "fixture-only",
            "prompt_sha256": "0" * 64, "prompt_tokens": 4, "completion_tokens": 1,
            "runtime": {**model, "attention": "sdpa", "dtype": "bfloat16", "quantization": None, "seed": 20260908}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "raw/inference" / digest(payload)
            write_new(path / "request.json", payload)
            write_new(path / "response.json", response)
            write_new(path / "attempt_00.json", {"attempt": 0, "lineage_id": digest(payload), "request_sha256": digest(payload)})
            self.assertEqual(check_inference_binding(root, messages, response, model, 10, config), digest(payload))
            altered = copy.deepcopy(response)
            altered["runtime"]["quantization"] = "4bit"
            (path / "response.json").write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "runtime"):
                check_inference_binding(root, messages, altered, model, 10, config)
            (path / "request.json").write_text(json.dumps({**payload, "messages": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "request"):
                check_inference_binding(root, messages, altered, model, 10, config)

if __name__ == "__main__":
    unittest.main()
