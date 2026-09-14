"""Synthetic finalization controls; no model, dataset outcomes or cloud access."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import contextlib
import io
import finalize_results as final


class FinalizerControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.splits = dict(development_ids=[f"Python/{i}" for i in range(41)],
                          heldout_ids=[f"Python/{i}" for i in range(41, 164)])
        cls.universe, cls.proposal_universe = final.frozen_universe(cls.splits)
        cls.jobs = [dict(job_id=key, row=dict(row, eligible=False)) for key, row in cls.universe.items()]
        cls.job_map = {job["job_id"]: job for job in cls.jobs}
        cls.proposal_jobs = [dict(row, eligible=False) for row in cls.proposal_universe.values()]
        cls.proposals = [dict(row, assignment_sha256=final.digest(row), status="budget_exhausted")
                         for row in cls.proposal_jobs]

    def test_full_frozen_counts_and_per_task_directions(self):
        self.assertEqual(len(self.universe), 9456)
        self.assertEqual(sum(r["cohort"] == "native" for r in self.universe.values()), 5516)
        self.assertEqual(sum(r["cohort"] == "generated" for r in self.universe.values()), 3940)
        self.assertEqual(len(self.proposal_universe), 328)
        repeated = {r["task_id"] for r in self.universe.values() if r["replicate"] == 1}
        self.assertEqual(len(repeated), 33)
        for task in self.splits["development_ids"] + self.splits["heldout_ids"]:
            pids = {r["proposal_id"] for r in self.universe.values() if r["task_id"] == task}
            self.assertEqual(len(pids), 4)

    def test_missing_arm_or_stability_assignment_rejected(self):
        for index in (0, next(i for i, job in enumerate(self.jobs) if job["row"]["replicate"] == 1)):
            with self.assertRaises(ValueError):
                final.validate_review_jobs(self.jobs[:index] + self.jobs[index+1:], self.universe)

    def test_duplicate_replacement_cannot_preserve_global_count(self):
        with self.assertRaises(ValueError):
            final.validate_review_jobs(self.jobs[:-1] + [self.jobs[0]], self.universe)

    def test_wrong_split_direction_or_reviewer_rejected(self):
        for field, value in (("split", "unknown"), ("intent", "wrong_direction"), ("reviewer", "unfrozen")):
            altered = copy.deepcopy(self.jobs[0])
            altered["row"][field] = value
            with self.assertRaises(ValueError):
                final.validate_review_jobs([altered] + self.jobs[1:], self.universe)

    def test_complete_ineligible_jobs_remain_expected(self):
        self.assertEqual(len(final.validate_review_jobs(self.jobs, self.universe)), 9456)

    def test_eligible_prompt_mismatch_rejected(self):
        altered = copy.deepcopy(self.jobs[0])
        altered["row"]["eligible"] = True
        with self.assertRaises(ValueError):
            final.validate_review_jobs([altered] + self.jobs[1:], self.universe)

    def test_bad_split_manifest_rejected(self):
        bad = copy.deepcopy(self.splits)
        bad["heldout_ids"][0] = bad["development_ids"][0]
        with self.assertRaises(ValueError):
            final.frozen_universe(bad)

    def test_missing_decisions_explicit_not_silently_complete(self):
        job = self.jobs[0]
        row = dict(job["row"], job_id=job["job_id"], assignment_sha256=final.digest(job))
        missing = final.validate_decisions([row], self.job_map)
        self.assertEqual(len(missing), 9455)

    def test_wrong_decision_assignment_hash_rejected(self):
        job = self.jobs[0]
        row = dict(job["row"], job_id=job["job_id"], assignment_sha256="0" * 64)
        with self.assertRaises(ValueError):
            final.validate_decisions([row], self.job_map)

    def test_duplicate_decision_rejected(self):
        job = self.jobs[0]
        row = dict(job["row"], job_id=job["job_id"], assignment_sha256=final.digest(job))
        with self.assertRaises(ValueError):
            final.validate_decisions([row, row], self.job_map)

    def test_complete_proposal_placeholders_valid(self):
        final.validate_proposals(self.proposals, self.proposal_jobs, self.proposal_universe)

    def test_missing_or_duplicate_proposal_rejected(self):
        for values in (self.proposals[:-1], self.proposals[:-1] + [self.proposals[0]]):
            with self.assertRaises(ValueError):
                final.validate_proposals(values, self.proposal_jobs, self.proposal_universe)

    def test_admitted_wrong_source_hash_rejected(self):
        row = dict(self.proposals[0], status="admitted", code="def f(x): return x", code_sha256="0" * 64)
        with self.assertRaises(ValueError):
            final.validate_proposals([row] + self.proposals[1:], self.proposal_jobs, self.proposal_universe)

    def test_budget_exact_limit_and_reserved_attempt_accounted(self):
        row = dict(model_id=final.prompts.PROPOSER, accounted_usd=30.0, status="RESERVED", usage=None)
        entries, total = final.validate_budget(dict(limit_usd=30, entries={"attempt": row}))
        self.assertEqual(total, 30)
        self.assertEqual(len(entries), 1)

    def test_invalid_budget_amount_and_limit_rejected(self):
        row = dict(model_id=final.prompts.PROPOSER, accounted_usd=0, status="RESERVED", usage=None)
        for amount in (-1, float("nan"), float("inf"), True, 30.01):
            with self.assertRaises(ValueError):
                final.validate_budget(dict(limit_usd=30, entries={"attempt": dict(row, accounted_usd=amount)}))
        with self.assertRaises(ValueError):
            final.validate_budget(dict(limit_usd=100, entries={}))

    def test_unfrozen_model_and_bad_usage_rejected(self):
        row = dict(model_id=final.prompts.PROPOSER, accounted_usd=0, status="SUCCESS", usage=None)
        for change in (dict(model_id="other"), dict(usage={"inputTokens": -1}), dict(usage={"outputTokens": True})):
            with self.assertRaises(ValueError):
                final.validate_budget(dict(limit_usd=30, entries={"attempt": dict(row, **change)}))

    def test_captured_hash_binds_exact_parsed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"source.json"
            data = b'\xef\xbb\xbf{"value": 3}\r\n'
            path.write_bytes(data)
            provenance = {}
            self.assertEqual(final.capture(path, provenance), {"value": 3})
            self.assertEqual(provenance[path.name], hashlib.sha256(data).hexdigest())

    def test_finalizer_flow_with_complete_placeholders_and_missing_offline(self):
        # Full frozen source-task identities, entirely synthetic observations.
        # Stub expensive statistics/row serialization only; execute finalizer
        # validation, universe construction, metadata capture and report writing.
        local_job_map = copy.deepcopy(self.job_map)
        datasets = {"MODEL_SOURCE_FREEZE.json": {"files": {}},
                    "SPLIT_MANIFEST.json": self.splits, "REFERENCE_MANIFEST.json": {},
                    "PROPOSER_DEVELOPMENT_GATE.json": dict(split="development", proposer=final.prompts.PROPOSER,
                        checks={"native": False, "generated": False}, **{"pass": False}),
                    "budget.json": {"limit_usd": 30, "entries": {}}}
        for cohort in ("native", "generated"):
            for split in ("development", "heldout"):
                label = "dev" if split == "development" else split
                jobs = [j for j in local_job_map.values() if j["row"]["cohort"] == cohort and j["row"]["split"] == label]
                suffix = cohort + "_" + split
                datasets["review_jobs_" + suffix + ".jsonl"] = jobs
                datasets["decisions_" + suffix + ".jsonl"] = [dict(j["row"], job_id=j["job_id"],
                    assignment_sha256=final.digest(j), model_status="not_assigned_ineligible", model_valid=False, direction="unknown") for j in jobs]
                datasets["offline_" + suffix + ".jsonl"] = []
                datasets["GATE_" + suffix + ".json"] = dict(split=split, cohort=cohort,
                    all_assignments_accounted=True, models={m: dict(assigned=0, valid=0, valid_rate=None, **{"pass": False})
                        for m in final.prompts.REVIEWERS}, **{"pass": False})
        # Expected rows need the label metadata used to build offline inventory.
        for jobs in [v for k,v in datasets.items() if k.startswith("review_jobs_")]:
            for job in jobs:
                job["row"].update(direction="unknown", eligibility_reasons=["synthetic"])
        for key, decisions in datasets.items():
            if key.startswith("decisions_"):
                for decision in decisions:
                    decision["assignment_sha256"] = final.digest(local_job_map[decision["job_id"]])
        for split in ("development", "heldout"):
            datasets["proposal_jobs_" + split + ".jsonl"] = [j for j in self.proposal_jobs if j["split"] == split]
            datasets["proposals_" + split + ".jsonl"] = [r for r in self.proposals if r["split"] == split]
        def captured(path, provenance, name=None, jsonl=False):
            value = datasets[path.name]
            provenance[name or path.name] = final.digest(value)
            return value
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = root/"protocol.md"
            protocol.write_text("synthetic", encoding="utf-8")
            with mock.patch.object(final, "capture", side_effect=captured), \
                 mock.patch.object(final.analysis, "analyze", return_value={}), \
                 mock.patch.object(final.offline_analysis, "analyze", return_value={}), \
                 mock.patch.object(final.analysis, "render_markdown", return_value="synthetic model"), \
                 mock.patch.object(final.offline_analysis, "render_markdown", return_value="synthetic offline"), \
                 mock.patch.object(final, "save_rows") as saved, contextlib.redirect_stdout(io.StringIO()):
                final.finalize(root, protocol, hashlib.sha256(protocol.read_bytes()).hexdigest())
            flow = json.loads((root/"public_results/FLOW_AND_COSTS.json").read_text())
            self.assertEqual(flow["review_assignments"], 9456)
            self.assertEqual(flow["review_records"], 9456)
            self.assertEqual(flow["offline_assigned_rows"], 131200)
            self.assertFalse(flow["experiment_processing_accounted"])
            self.assertEqual(flow["eligible_review_calls_completed"], 0)
            self.assertEqual(saved.call_count, 4)
            receipt = json.loads((root/"public_results/RESULTS_RECEIPT.json").read_text())
            self.assertIn("budget.json", receipt["source_inputs_sha256"])
            self.assertIn("GATE_generated_development.json", receipt["source_inputs_sha256"])
            self.assertIn("proposals_heldout.jsonl", receipt["source_inputs_sha256"])

    def test_technical_gate_recomputed_from_counts(self):
        rows = [dict(reviewer=m, eligible=True, model_valid=True) for m in final.prompts.REVIEWERS]
        gate = dict(all_assignments_accounted=True, models={m: dict(assigned=1, valid=1, valid_rate=1, **{"pass": True})
                    for m in final.prompts.REVIEWERS}, **{"pass": True})
        final.validate_gate(gate, rows, rows)
        rows[0]["model_valid"] = False
        with self.assertRaises(ValueError):
            final.validate_gate(gate, rows, rows)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FinalizerControls))
    receipt = dict(scope="Synthetic finalizer controls only; source-task IDs and statuses are constructed, no study outputs read",
                   tests_run=result.testsRun, passed=result.testsRun-len(result.failures)-len(result.errors),
                   failures=[str(t) for t, _ in result.failures], errors=[str(t) for t, _ in result.errors],
                   finalizer_sha256=hashlib.sha256(Path(final.__file__).read_bytes()).hexdigest(),
                   control_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (Path(__file__).parent/"review/FINALIZER_CONTROL_REVIEW.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
