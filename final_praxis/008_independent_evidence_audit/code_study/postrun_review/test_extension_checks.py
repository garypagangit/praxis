"""Authorship-independent, manually specified extension artifact controls."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import audit_results as audit
import extension_checks as extension
from test_audit_results import raw_fixture, write

PIN="a"*64


def v2_raw_fixture(root, *, change_schema=False, wrong_protocol=False, original_id=False):
    raw_fixture(root)
    old="review-synthetic"
    rid=old if original_id else "v2-"+old
    folder=root/"raw_inference"
    for path in list(folder.glob("*")):
        value=audit.read_json(path)
        for key in ("request_id","request_receipt","response_receipt"):
            if key in value: value[key]=value[key].replace(old,rid)
        if path.name.endswith(".request.json"):
            value["request"]["requestMetadata"].update(request_id=rid,preregistration_sha256=audit.PROTOCOL_SHA256 if wrong_protocol else PIN)
            value["request"]["outputConfig"]={"textFormat":{"type":"json_schema","structure":{"jsonSchema":{
                "name":"experiment_response","schema":audit.canonical(audit.REVIEW_SCHEMA)}}}}
            if change_schema: value["request"].pop("outputConfig")
            value["prompt_sha256"]=audit.sha_text(audit.canonical(value["request"]))
            value["inference_input_sha256"]=audit.sha_text(audit.canonical({k:v for k,v in value["request"].items() if k!="requestMetadata"}))
            request=value
        path.unlink()
        write(folder/path.name.replace(old,rid),value)
    result_path=folder/(rid+".result.json")
    result=audit.read_json(result_path)
    result.update(prompt_sha256=request["prompt_sha256"],inference_input_sha256=request["inference_input_sha256"],preregistration_sha256=PIN,runtime=dict(structured_output=True))
    write(result_path,result)
    ledger=audit.read_json(root/"budget.json")
    ledger["entries"]={k.replace(old,rid):v for k,v in ledger["entries"].items()}
    write(root/"budget.json",ledger)
    assigned_id="v2-"+old
    job=dict(job_id=old,row=dict(eligible=True,reviewer=audit.REVIEWERS[0],split="dev",cohort="native"),
             messages=[dict(role="system",content="synthetic instruction"),dict(role="user",content="synthetic input")])
    checked=audit.Audit()
    audit.audit_raw(checked,root,{assigned_id:(job,False)},
                    {assigned_id:dict(audit.parse_review(result),model_status="complete")},{},{},
                    "2026-09-14T00:53:00+00:00",protocol_hash=PIN,structured_reviews=True)
    return checked


class ExtensionControls(unittest.TestCase):
    def test_fixed_reuse_selector_all_placeholders_included(self):
        for cohort,split,wanted in (("native","dev",True),("native","heldout",True),("generated","dev",True),("generated","heldout",False)):
            for model in audit.REVIEWERS:
                row=dict(reviewer=model,cohort=cohort,split=split,eligible=False,model_status="not_assigned_ineligible")
                self.assertEqual(extension.imported_review(row),wanted and model==audit.REVIEWERS[1])

    def test_qwen_new_namespace_devstral_unchanged(self):
        self.assertEqual(extension.new_request_id("review-s",dict(reviewer=audit.REVIEWERS[0])),"v2-review-s")
        self.assertEqual(extension.new_request_id("review-s",dict(reviewer=audit.REVIEWERS[1])),"review-s")

    def test_schema_only_on_qwen_reviews(self):
        for proposer in (False,True):
            for model in audit.REVIEWERS:
                job=dict(messages=[dict(role="system",content="fixture")],row=dict(reviewer=model))
                body=audit.request_body(job,"synthetic",proposer,protocol_hash=PIN,structured_reviews=True)
                self.assertEqual("outputConfig" in body,not proposer and model==audit.REVIEWERS[0])
                self.assertEqual(body["requestMetadata"]["preregistration_sha256"],PIN)
                self.assertEqual(body["inferenceConfig"]["maxTokens"],2048 if proposer else 1024)

    def test_new_schema_receipts_and_cost_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=v2_raw_fixture(Path(tmp))
            self.assertEqual(result.total,result.passed,result.failures)
            self.assertEqual(result.counts["accounted_api_usd_estimate"],.000029)

    def test_qwen_missing_schema_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=v2_raw_fixture(Path(tmp),change_schema=True)
            self.assertIn("raw:exact_frozen_request",{r["check"] for r in result.failures})

    def test_qwen_original_protocol_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=v2_raw_fixture(Path(tmp),wrong_protocol=True)
            self.assertIn("raw:exact_frozen_request",{r["check"] for r in result.failures})

    def test_old_qwen_raw_namespace_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=v2_raw_fixture(Path(tmp),original_id=True)
            self.assertIn("raw:assigned_request",{r["check"] for r in result.failures})

    def test_byte_exact_import_includes_invalid_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); study=root/"study_v2"
            args=SimpleNamespace(campaign=root,study=study)
            record=dict(status="invalid",code=None)
            write(root/"study/proposals/s.json",record)
            write(study/"proposals/s.json",record)
            item=dict(source="study/proposals/s.json",destination="proposals/s.json",sha256=audit.sha_file(root/"study/proposals/s.json"))
            checked=audit.Audit()
            self.assertTrue(extension.exact_import(checked,args,item,item["source"],item["destination"],record))
            write(study/"proposals/s.json",dict(status="admitted",code="new"))
            self.assertFalse(extension.exact_import(checked,args,item,item["source"],item["destination"],record))

    def test_effective_gate_manual_truth_table_and_tamper(self):
        for native,generated in ((False,False),(False,True),(True,False),(True,True)):
            with self.subTest(native=native,generated=generated),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                args=SimpleNamespace(study=root,extension_protocol_sha256=PIN)
                gates={}
                for cohort,passed in (("native",native),("generated",generated)):
                    gate=dict(cohort=cohort,split="development",all_assignments_accounted=True,
                              models={audit.REVIEWERS[0]:{"pass":passed},audit.REVIEWERS[1]:{"pass":True}},**{"pass":passed})
                    gates[cohort+"_development"]=gate
                    write(root/("GATE_"+cohort+"_development.json"),gate)
                hashes={c:audit.sha_file(root/("GATE_"+c+"_development.json")) for c in ("native","generated")}
                checks=dict(native=native,generated=generated)
                joint=native and generated
                annotation=dict(checks=checks,**{"pass":joint},measured_gate_sha256=hashes,protocol_sha256=PIN)
                gates["proposer"]=dict(split="development",proposer=audit.REVIEWERS[0],**annotation)
                for cohort,passed in (("native",native),("generated",generated)):
                    effective=copy.deepcopy(gates[cohort+"_development"])
                    effective["models"][audit.REVIEWERS[0]].update(measured_pass=passed,**{"pass":joint})
                    effective.update(effective_qwen_joint_gate=annotation,**{"pass":joint})
                    write(root/("EFFECTIVE_GATE_"+cohort+"_development.json"),effective)
                checked=audit.Audit()
                effective,_,_=extension.effective_gates(checked,args,gates)
                self.assertEqual(checked.total,checked.passed,checked.failures)
                self.assertIs(effective["native_development"]["models"][audit.REVIEWERS[0]]["pass"],joint)
                bad=root/"EFFECTIVE_GATE_native_development.json"
                changed=audit.read_json(bad);changed["models"][audit.REVIEWERS[0]]["pass"]=not joint;write(bad,changed)
                extension.effective_gates(checked,args,gates)
                self.assertIn("v2:effective_heldout_gate_exact",{r["check"] for r in checked.failures})


if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExtensionControls))
    report=dict(scope="Authorship-independent manually specified V2 lineage/schema/gate synthetic controls only",
                tests_run=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors),
                failures=[str(t) for t,_ in result.failures],errors=[str(t) for t,_ in result.errors],
                auditor_sha256=audit.sha_file(Path(audit.__file__)),extension_checker_sha256=audit.sha_file(Path(extension.__file__)),
                control_sha256=audit.sha_file(Path(__file__)),model_calls=0)
    Path(__file__).with_name("EXTENSION_SYNTHETIC_REVIEW.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
