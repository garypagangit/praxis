"""Independent manual adversarial controls; never loads main-study artifacts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import audit_results as checker


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding="utf-8")


def raw_fixture(root, *, corrupt_cost=False, corrupt_decision=False, response_text=None,
                heldout=False, gate_pass=False, no_ledger=False):
    rid="review-synthetic"
    job=dict(job_id=rid,row=dict(eligible=True,reviewer=checker.REVIEWERS[0],split="heldout" if heldout else "dev",cohort="native"),
             messages=[dict(role="system",content="synthetic instruction"),dict(role="user",content="synthetic input")])
    body=checker.request_body(job,rid)
    content_hash=checker.sha_text(checker.canonical({k:v for k,v in body.items() if k!="requestMetadata"}))
    prompt_hash=checker.sha_text(checker.canonical(body))
    request=dict(request_id=rid,attempt=1,request=body,prompt_sha256=prompt_hash,
                 inference_input_sha256=content_hash,timestamp_utc="2026-09-14T01:00:00+00:00")
    attempt=rid+".attempt-1"
    write(root/"raw_inference"/(attempt+".request.json"),request)
    usage=dict(inputTokens=10,outputTokens=20)
    entry=dict(model_id=checker.REVIEWERS[0],accounted_usd=.01 if corrupt_cost else .000029,
               reserved_usd=.0001,status="SUCCESS",usage=usage)
    if no_ledger:
        write(root/"budget.json",dict(limit_usd=30,entries={}))
        decisions={rid:dict(model_status="budget_exhausted")}
    else:
        write(root/"budget.json",dict(limit_usd=30,entries={attempt:entry}))
        text=response_text or '{"decision":"accept","reason":"synthetic"}'
        response=dict(usage=usage,stopReason="end_turn",output=dict(message=dict(content=[dict(text=text)])))
        write(root/"raw_inference"/(attempt+".response.json"),response)
        result=dict(text=text,finish_reason="end_turn",usage=usage,request_id=rid,
                    request_receipt="/remote/"+attempt+".request.json",response_receipt="/remote/"+attempt+".response.json",
                    prompt_sha256=prompt_hash,inference_input_sha256=content_hash,
                    preregistration_sha256=checker.PROTOCOL_SHA256,model_id=checker.REVIEWERS[0])
        write(root/"raw_inference"/(rid+".result.json"),result)
        decisions={rid:dict(checker.parse_review(result),model_status="complete")}
        if corrupt_decision: decisions[rid]["decision"]="keep"
    gates=dict(native_development=dict(models={checker.REVIEWERS[0]:{"pass":gate_pass}}))
    audit=checker.Audit()
    checker.audit_raw(audit,root,{rid:(job,False)},decisions,{},gates,"2026-09-14T00:53:00+00:00")
    return audit


class ArtifactControls(unittest.TestCase):
    def test_known_and_unknown_outcomes(self):
        self.assertIsNone(checker.outcome([]))
        self.assertIsNone(checker.outcome(["pass","not_run_worker_incomplete"]))
        self.assertIs(checker.outcome(["pass","pass"]),True)
        self.assertIs(checker.outcome(["timeout","not_run_worker_incomplete"]),False)

    def test_null_direction_not_other(self):
        self.assertEqual(checker.direction(True,None),"unknown")
        self.assertEqual(checker.direction(True,False),"harmful")
        self.assertEqual(checker.direction(False,True),"useful")

    def test_terminal_parse_normalizes_decision(self):
        value=checker.parse_review(dict(finish_reason="end_turn",text='{"decision":" AcCePt ","reason":"  retained  "}'))
        self.assertEqual(value,dict(decision="accept",model_valid=True,reason="  retained  "))

    def test_duplicate_json_key_is_invalid(self):
        value=checker.parse_review(dict(finish_reason="end_turn",text='{"decision":"accept","decision":"keep","reason":"x"}'))
        self.assertFalse(value["model_valid"])

    def test_truncated_valid_json_still_abstains(self):
        value=checker.parse_review(dict(finish_reason="max_tokens",text='{"decision":"accept","reason":"x"}'))
        self.assertEqual(value["reason"],"nonterminal_or_truncated_response")
        self.assertEqual(value["decision"],"abstain")

    def test_one_complete_json_fence_only(self):
        good='```json\n{"decision":"keep","reason":"x"}\n```'
        self.assertTrue(checker.parse_review(dict(finish_reason="end_turn",text=good))["model_valid"])
        self.assertFalse(checker.parse_review(dict(finish_reason="end_turn",text="explanation\n"+good))["model_valid"])

    def test_preserve_dictionary_pairs_and_boolean_values(self):
        value={"t":"dict","v":[[{"t":"bool","v":True},{"t":"int","v":"2"}]]}
        self.assertEqual(checker.public_value(value),{"dictionary_pairs":[[True,2]]})

    def test_expected_preview_residual_not_canonical_root(self):
        record=checker.display_record(dict(entry_point="find_zero",atol=1e-6),dict(case_id="x",input=[[1,2]]),"pass",
                                      dict(status="pass",expected={"t":"int","v":"999"}),"a"*64)
        self.assertIn("polynomial residual",record["expected_preview"])
        self.assertNotIn("999",record["expected_preview"])

    def test_preview_truncation_hashes_full_payload(self):
        record=checker.display_record(dict(entry_point="f"),dict(case_id="x",input=["z"*500]),"reference_unavailable",{},"a"*64)
        self.assertTrue(record["truncated"])
        self.assertEqual(len(record["input_preview"]),350)
        self.assertEqual(record["input_sha256"],checker.sha_text(checker.canonical(["z"*500])))
        self.assertEqual(record["status"],"unknown")

    def test_exact9456_universe(self):
        tasks={f"Python/{i}":dict(split="development" if i<41 else "heldout") for i in range(164)}
        universe=checker.expected_universe(tasks)
        self.assertEqual(len(universe),9456)
        self.assertEqual(sum(r["cohort"]=="native" for r in universe.values()),5516)
        self.assertEqual(len({r["task_id"] for r in universe.values() if r["replicate"]==1}),33)

    def test_safe_child_rejects_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): checker.safe_child(Path(tmp),"../elsewhere")

    def test_authentic_raw_receipts_and_hand_calculated_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit=raw_fixture(Path(tmp))
            self.assertEqual(audit.passed,audit.total,audit.failures)
            self.assertEqual(audit.counts["accounted_api_usd_estimate"],.000029)

    def test_price_corruption_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit=raw_fixture(Path(tmp),corrupt_cost=True)
            self.assertIn("ledger:response_usage_cost",{f["check"] for f in audit.failures})

    def test_saved_decision_disagrees_with_raw_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit=raw_fixture(Path(tmp),corrupt_decision=True)
            self.assertIn("decision:independent_raw_parse",{f["check"] for f in audit.failures})

    def test_heldout_call_after_failed_gate_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit=raw_fixture(Path(tmp),heldout=True,gate_pass=False)
            self.assertIn("raw:heldout_gate_passed",{f["check"] for f in audit.failures})

    def test_budget_prevention_request_is_not_unrecorded_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit=raw_fixture(Path(tmp),no_ledger=True)
            self.assertEqual(audit.passed,audit.total,audit.failures)
            self.assertEqual(audit.counts["prevented_unledgered_budget_requests"],1)


if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ArtifactControls))
    report=dict(scope="Authorship-independent manually specified synthetic artifact controls; no main-study outputs loaded",
                tests_run=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors),
                failures=[str(t) for t,_ in result.failures],errors=[str(t) for t,_ in result.errors],
                auditor_sha256=checker.sha_file(Path(checker.__file__)),control_sha256=checker.sha_file(Path(__file__)))
    Path(__file__).with_name("SYNTHETIC_AUDIT_REVIEW.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
