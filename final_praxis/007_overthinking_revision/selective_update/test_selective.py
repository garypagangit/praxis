"""Offline selective-update protocol tests; no boto3 import, AWS client, or inference.
Set SELECTIVE_RUNNER to test a copied candidate runner.
Run: python -m unittest discover -s reports/praxis_20260912_stage2_staging/007_runner_review -p test_selective.py -v
"""
import ast, collections, contextlib, copy, hashlib, importlib.util, itertools, json, os
from pathlib import Path
import re, sys, tempfile, types, unittest
from unittest import mock
DEFAULT_RUNNER=Path(__file__).resolve().parent/"run_selective.py"
if not DEFAULT_RUNNER.exists(): DEFAULT_RUNNER=Path("C:/w/fp007/final_praxis/007_overthinking_revision/selective_update/run_selective.py")
RUNNER=Path(os.environ.get("SELECTIVE_RUNNER",str(DEFAULT_RUNNER)))
spec=importlib.util.spec_from_file_location("reviewed_selective",RUNNER)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def labels(**updates):
    out={k:"TRUE" for k in r.CHECKS};out.update(updates);return out
def item(i, split="cal",gold="TRUE"):
    return {"id":str(i),"question":"Unique factual claim number "+str(i), "release_split":split,
            "gold":gold,"evidence":"Distinct reference explanation number "+str(i),
            "hidden_audit_gold_secret":"NEVER_SERIALIZE_GOLD_METADATA"}
def cells(y0="TRUE",answer="TRUE"):
    out={"initial":{"score":{"answer":y0}}}
    out.update({c+"__"+k:{"score":{"answer":answer}} for c in r.CONDITIONS for k in r.CHECKS})
    for cell in out.values():cell['result']={'input_tokens':100,'output_tokens':5,'accounted_usd_estimate':.001}
    return out

class Decisions(unittest.TestCase):
    def test_gate_truth_table_and_invalid_veto(self):
        for y0 in ("TRUE","FALSE",None):
            for b,t,f in itertools.product(("TRUE","FALSE",None),repeat=3):
                got=r.decisions(y0,labels(blind0=b,peer_true=t,peer_false=f))["label_gate"]
                want=b if b is not None and b==t==f else y0
                self.assertEqual(got,want,(y0,b,t,f))
    def test_repeat_majority_differs_from_unanimity(self):
        result=r.decisions("FALSE",labels(blind0="TRUE",blind1="TRUE",blind2="FALSE"))
        self.assertEqual(result["repeat_majority"],"TRUE")
        self.assertEqual(result["repeat_unanimity"],"FALSE")
        result=r.decisions("FALSE",labels(blind0="TRUE",blind1="TRUE",blind2=None))
        self.assertEqual(result["repeat_majority"],"FALSE")
    def test_veto_cannot_improve_blind_recovery(self):
        for gold in ("TRUE","FALSE"):
            y0="FALSE" if gold=="TRUE" else "TRUE"
            for b,t,f in itertools.product(("TRUE","FALSE",None),repeat=3):
                result=r.decisions(y0,labels(blind0=b,peer_true=t,peer_false=f))
                self.assertLessEqual(result["label_gate"]==gold,result["blind"]==gold)

class PromptAndParser(unittest.TestCase):
    def test_gold_mutation_leaves_public_mapping_and_prompts_identical(self):
        rows=[item(i,"cal" if i<2 else "test") for i in range(4)]
        flipped=copy.deepcopy(rows)
        for row in flipped:
            row["gold"]="FALSE";row["gold_original_bool"]=False
        self.assertEqual(r.evidence_map(rows),r.evidence_map(flipped))
        for before,after in zip(rows,flipped):
            self.assertEqual(r.public(before),r.public(after))
            self.assertNotIn("gold",r.public(before))
            for kind in r.CHECKS:
                a=r.check_messages(before["question"],"FINAL: FALSE",before["evidence"],kind)
                b=r.check_messages(after["question"],"FINAL: FALSE",after["evidence"],kind)
                self.assertEqual(a,b)
                self.assertNotIn("NEVER_SERIALIZE",json.dumps(a))
    def test_blind_prompts_identical_and_peer_labels_only_literal_change(self):
        args=("Claim","FINAL: FALSE","Reference")
        messages=[r.check_messages(*args,k) for k in ("blind0","blind1","blind2")]
        self.assertEqual(messages[0],messages[1]);self.assertEqual(messages[1],messages[2])
        true=r.check_messages(*args,"peer_true");false=r.check_messages(*args,"peer_false")
        self.assertEqual(true[:2],false[:2]);self.assertEqual(true[1]["content"],"FINAL: FALSE")
        self.assertEqual(true[2]["content"].replace("asserts TRUE","asserts FALSE"),false[2]["content"])
    def test_parser_normalization_ambiguity_and_truncation(self):
        for text in ("FINAL: TRUE","**FINAL: TRUE**",json.dumps("FINAL: TRUE")):
            result=r.score({"text":text,"finish_reason":"end_turn","output_tokens":9},256)
            self.assertEqual(result["answer"],"TRUE")
        for text in ("FINAL: TRUE\nFINAL: FALSE","FINAL: TRUE followed by words","TRUE"):
            self.assertIsNone(r.score({"text":text,"finish_reason":"end_turn","output_tokens":9},256)["answer"])
        for stop in ("max_tokens","length","max_output_tokens","MAX_TOKENS"):
            result=r.score({"text":"FINAL: TRUE","finish_reason":stop,"output_tokens":256},256)
            self.assertTrue(result["truncated"]);self.assertIsNone(result["answer"])
    def test_donors_are_same_split_independent_of_order_and_not_self(self):
        rows=[item(i,"cal" if i<2 else "test") for i in range(4)]
        result=r.evidence_map(rows);self.assertEqual(result,r.evidence_map(list(reversed(rows))))
        byid={i["id"]:i for i in rows}
        for qid,assignment in result.items():
            self.assertNotEqual(qid,assignment["donor_id"])
            self.assertEqual(byid[qid]["release_split"],byid[assignment["donor_id"]]["release_split"])

class Analysis(unittest.TestCase):
    def test_denominators_keep_invalid_initial_out_of_conditional_rates(self):
        rows=[{"initial":a,"gold":g,"decisions":{"p":b}} for a,g,b in
              [("TRUE","TRUE",None),("FALSE","TRUE","TRUE"),(None,"TRUE","TRUE"),("TRUE","TRUE","FALSE")]]
        m=r.measure(rows,"p")
        self.assertEqual((m["n"],m["initial_correct"],m["initial_wrong"],m["initial_invalid"]),(4,2,1,1))
        self.assertEqual((m["harm"],m["c_to_w"],m["c_to_invalid"],m["recovery"]),(2,1,1,1))
        self.assertEqual(m["harm_rate"],1);self.assertEqual(m["recovery_rate"],1)
        self.assertEqual(m["accuracy"],.5)
    def test_empty_denominators_are_none(self):
        m=r.measure([],"p")
        for key in ("harm_rate","recovery_rate","accuracy","harmful_update_risk"):
            self.assertIsNone(m[key])
    def test_bootstrap_resamples_questions_not_condition_cells(self):
        rows=[]
        for qid in ("a","b"):
            for condition in r.CONDITIONS:
                rows.append({"id":qid,"condition":condition,"initial":"TRUE","gold":"TRUE",
                             "decisions":{"label_gate":"TRUE","repeat_majority":"FALSE"}})
        result=r.bootstrap_difference(rows,"repeat_majority","harm_rate")
        self.assertEqual(result["question_n"],2);self.assertEqual(result["difference"],-1)
        self.assertEqual(result["ci95"],[-1,-1])
    def test_missing_check_with_stray_file_cannot_pass_calibration(self):
        rows=[item(i,gold="TRUE" if i<32 else "FALSE") for i in range(64)]
        def read(out,model,row):
            got=cells()
            if row["id"]=="0":
                got.pop("reference__peer_false")
                got["stray"]={"score":{"answer":"TRUE"}}
            return got
        with mock.patch.object(r,"read_cells",side_effect=read):
            try:
                summary=r.summarize(rows,Path("."),"offline","cal")
            except ValueError as error:
                self.assertIn("cell",str(error).lower())
                return
        self.assertFalse(summary["technical_gate_passed"],
                         "Completeness must check all expected names, not file count22")
    def test_accepted_stable_wrong_excludes_unchanged_wrong_answer(self):
        rows=[item(0,gold="FALSE")]
        with mock.patch.object(r,"read_cells",return_value=cells(y0="TRUE",answer="TRUE")):
            summary=r.summarize(rows,Path("."),"offline","cal")
        # If separately named accepted field is provided, use it; old field claimed this metric.
        metrics=summary.get("stable_wrong_updates",summary.get("stable_wrong_accepted_updates",summary["stable_wrong"]))
        self.assertEqual(metrics["none"],0,"Unchanged initial error is not an accepted update")
    def test_wrong_label_diagnostics_are_present_after_scoring(self):
        rows=[item(0,gold="TRUE"),item(1,gold="FALSE")]
        with mock.patch.object(r,"read_cells",return_value=cells()):
            summary=r.summarize(rows,Path("."),"offline","cal")
        for condition in r.CONDITIONS:
            self.assertIn("wrong_peer",summary["metrics"][condition])
            self.assertIn("wrong_sway",summary["metrics"][condition])

class Runtime(unittest.TestCase):
    def test_current_adapter_accepts_preregistered_stochastic_temperature_without_network(self):
        # Compile only the actual generate method. The iterable interrupts before request/cache/SDK access.
        # This catches the observed shared-adapter temperature=0 incompatibility without importing boto3.
        adapter=RUNNER.parents[2]/"shared_20260912/bedrock_adapter.py"
        tree=ast.parse(adapter.read_text(encoding="utf-8-sig"))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="BedrockAdapter")
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="generate")
        module=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(module)
        namespace={"re":re}
        exec(compile(module,str(adapter),"exec"),namespace)
        class BeforeNetwork(Exception):pass
        class StopIterationBeforeNetwork:
            def __iter__(self):raise BeforeNetwork()
        fake=types.SimpleNamespace(model_id="offline",prereg_hash="hash",allowed_temperatures=(0,.3))
        with self.assertRaises(BeforeNetwork):
            namespace["generate"](fake,StopIterationBeforeNetwork(),max_new_tokens=256,
                                  temperature=.3,request_id="unit_stochastic")
    def test_mock_execution_resume_distinct_replica_ids_and_technical_gate(self):
        calls=[];seen=set()
        class FakeAdapter:
            def __init__(self,**kwargs):pass
            def generate(self,messages,**kwargs):
                self_id=kwargs["request_id"]
                if self_id in seen:raise AssertionError("Duplicate actual request on resume")
                seen.add(self_id);calls.append((messages,kwargs))
                return {"text":"FINAL: TRUE","finish_reason":"end_turn","output_tokens":4,
                        "input_tokens":20,"request_id":self_id,"cost_usd_estimate":0}
        adapter=types.ModuleType("final_praxis.shared_20260912.bedrock_adapter")
        adapter.BedrockAdapter=FakeAdapter;adapter.BudgetLedger=lambda *a,**k:None
        lock=types.ModuleType("filelock");lock.FileLock=lambda *a,**k:contextlib.nullcontext()
        modules={"final_praxis":types.ModuleType("final_praxis"),
                 "final_praxis.shared_20260912":types.ModuleType("final_praxis.shared_20260912"),
                 "final_praxis.shared_20260912.bedrock_adapter":adapter,"filelock":lock}
        with tempfile.TemporaryDirectory(prefix="007-offline-") as directory:
            root=Path(directory);here=root/"study";(here/"data").mkdir(parents=True)
            # Deliberately tiny calibration prevents paid-style advancement; untouched test remains unqueried.
            fixture={"items":[item(i,"cal" if i<2 else "test") for i in range(192)]}
            raw=r.encode(fixture);(here/"data/fixtures.json").write_bytes(raw)
            prereg=b"offline unit test";(here/"PREREGISTRATION.md").write_bytes(prereg)
            out=root/"out"
            with mock.patch.object(r,"HERE",here),mock.patch.object(r,"FIXTURE_SHA",r.sha(raw)),\
                 mock.patch.object(r,"MODELS",("offline-model",)),mock.patch.dict(sys.modules,modules),\
                 mock.patch.dict(os.environ,{"PRAXIS_PREREG_SHA256":r.sha(prereg)}),\
                 mock.patch.object(sys,"argv",["run","--out",str(out),"--execute"]),\
                 contextlib.redirect_stdout(__import__("io").StringIO()):
                r.main();r.main()
            self.assertEqual(len(calls),44);self.assertTrue((out/"offline-model__test_not_started.json").exists())
            self.assertEqual(len(list((out/"cells").glob("*/*.json"))),44)
            first=r.read_cells(out,"offline-model",item(0))
            replicas=[first["reference__"+k] for k in ("blind0","blind1","blind2")]
            self.assertEqual(len({x["request_sha256"] for x in replicas}),3)
            self.assertEqual(replicas[0]["messages"],replicas[1]["messages"])
            for messages,kwargs in calls:
                self.assertNotIn("NEVER_SERIALIZE_GOLD_METADATA",json.dumps(messages))
                self.assertIn(kwargs["temperature"],(0,.3))
                self.assertIn(kwargs["max_new_tokens"],(64,256))

if __name__=="__main__":unittest.main()
