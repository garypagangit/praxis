"""Offline import/replay custody tests. No boto3 import or inference.
Imports sibling run_selective.py when copied; INLINE_RUNNER overrides explicitly.
"""
import contextlib, copy, hashlib, importlib.util, io, json, os, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock
DEFAULT=Path(__file__).resolve().parent/"run_selective.py"
if not DEFAULT.exists():DEFAULT=Path("C:/w/fp007/final_praxis/007_overthinking_revision/selective_update_inline/run_selective.py")
RUNNER=Path(os.environ.get("INLINE_RUNNER",str(DEFAULT)))
sys.path.insert(0,str(RUNNER.parent))
spec=importlib.util.spec_from_file_location("inline_import_review",RUNNER)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
OLD_RUNNER_SHA="ce23b5a698f9d580a4a780cb2b0a9558d0825c394fe507a1bbc4a07aa7e77379"
OLD_PREREG_SHA="1f7b8637b8cb8e7c248c78506a2a2d91e8c498dcda3bc7d7209326f09273d0fe"

def row(i,split="cal"):
    return {"id":str(i),"release_split":split,"question":"Unique question "+str(i),
            "evidence":"Distinct passage "+str(i),"gold":"TRUE"}
def old_score(response,limit):
    base=r.original.score(response,["TRUE","FALSE"],limit)
    normalized,changes=r.formatting.normalize(response["text"])
    base.update(answer=r.original.parse(normalized,["TRUE","FALSE"],base["truncated"]),
                normalized_text=normalized,normalization=changes)
    return base

class SourceFixture:
    def __init__(self,base):
        self.source=base/"old"/"outputs";self.out=base/"new"/"outputs"
        self.source.mkdir(parents=True);self.out.mkdir(parents=True)
        self.items=[row(0),row(1),row(2,"test"),row(3,"test")]
        self.manifest={"fixture_sha256":r.FIXTURE_SHA,"runner_sha256":OLD_RUNNER_SHA,
                       "prereg_sha256":OLD_PREREG_SHA,"models":list(r.MODELS)}
        r.write(self.source/"manifest.json",self.manifest)
        r.write(self.source.parent/"cloud_status.json",{"state":"COMPLETED","returncode":0,"run_id":"fp007-selective-20260912-1c47aca"})
        mapping=r.evidence_map(self.items)
        for model in r.MODELS:
            for item in self.items[:2]:
                initial_text="One sentence. FINAL: TRUE"
                for name in sorted(r.EXPECTED_CELLS):
                    initial=name=="initial";limit=64 if initial else 256;temperature=0 if initial else .3
                    if initial:messages=r.initial(item["question"])
                    else:
                        condition,kind=name.split("__")
                        messages=r.check_messages(item["question"],initial_text,mapping[item["id"]][condition],kind)
                    request={"manifest":self.manifest,"model":model,"id":item["id"],"cell":name,
                             "messages":messages,"max_tokens":limit,"temperature":temperature}
                    digest=r.sha(r.encode(request))
                    response={"text":initial_text,"finish_reason":"end_turn","output_tokens":41,"input_tokens":100,
                              "request_id":"fp007s2-"+digest[:32],"preregistration_sha256":OLD_PREREG_SHA,
                              "cost_usd_estimate":0}
                    cell={"model":model,"id":item["id"],"split":"cal","cell":name,"messages":messages,
                          "request_sha256":digest,"result":response,"score":old_score(response,limit),"seconds":.01}
                    r.write(r.cell_dir(self.source,model,item)/(name+".json"),cell)
    def first(self):
        return r.cell_dir(self.source,r.MODELS[0],self.items[0])/"initial.json"
    def mutate_first(self,fn):
        p=self.first();v=json.loads(p.read_text(encoding="utf-8"));fn(v);r.write(p,v)
    def run(self):return r.import_calibration(self.source,self.out,self.items)

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="007-import-offline-")
        self.addCleanup(self.temp.cleanup);self.f=SourceFixture(Path(self.temp.name))
    def test_import_replay_keeps_raw_results_old_identity_and_source_bytes(self):
        snapshots={str(p.relative_to(self.f.source)):p.read_bytes() for p in self.f.source.rglob("*.json")}
        self.assertEqual(self.f.run(),[])
        receipt=json.loads((self.f.out/"calibration_import.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["imported_cells"],2*2*22)
        self.assertEqual(receipt["model_calls_for_calibration"],0)
        for model in r.MODELS:
            for item in self.f.items[:2]:
                old=r.read_cells(self.f.source,model,item);new=r.read_cells(self.f.out,model,item)
                for name,cell in old.items():
                    replay=new[name]
                    self.assertEqual(replay["result"],cell["result"])
                    self.assertEqual(replay["messages"],cell["messages"])
                    self.assertEqual(replay["request_sha256"],cell["request_sha256"])
                    self.assertEqual(replay["original_score"],cell["score"])
                    self.assertIsNone(cell["score"]["answer"]);self.assertEqual(replay["score"]["answer"],"TRUE")
                    raw=(r.cell_dir(self.f.source,model,item)/(name+".json")).read_bytes()
                    self.assertEqual(replay["replayed_calibration"]["raw_cell_sha256"],r.sha(raw))
                    self.assertTrue(replay["replayed_calibration"]["no_new_model_call"])
        self.assertEqual(snapshots,{str(p.relative_to(self.f.source)):p.read_bytes() for p in self.f.source.rglob("*.json")})
        # Resume should be a byte-identical import, with no provider interaction.
        before={str(p.relative_to(self.f.out)):p.read_bytes() for p in self.f.out.rglob("*.json")}
        self.f.run()
        self.assertEqual(before,{str(p.relative_to(self.f.out)):p.read_bytes() for p in self.f.out.rglob("*.json")})
    def test_manifest_runner_hash_tamper_fails(self):
        v=copy.deepcopy(self.f.manifest);v["runner_sha256"]="0"*64
        r.write(self.f.source/"manifest.json",v)
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_manifest_prereg_hash_tamper_fails(self):
        v=copy.deepcopy(self.f.manifest);v["prereg_sha256"]="0"*64
        r.write(self.f.source/"manifest.json",v)
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_request_hash_tamper_fails(self):
        self.f.mutate_first(lambda cell:cell.update(request_sha256="0"*64))
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_tampered_saved_strict_score_fails(self):
        self.f.mutate_first(lambda cell:cell["score"].update(answer="FALSE"))
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_tampered_raw_result_without_score_change_fails(self):
        self.f.mutate_first(lambda cell:cell["result"].update(text="FINAL: FALSE"))
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_incomplete_source_status_fails(self):
        r.write(self.f.source.parent/"cloud_status.json",{"state":"RUNNING","returncode":None,"run_id":"offline"})
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_failed_source_status_fails(self):
        r.write(self.f.source.parent/"cloud_status.json",{"state":"COMPLETED","returncode":1,"run_id":"offline"})
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_missing_planned_cell_fails(self):
        self.f.first().unlink()
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_cell_identity_tamper_fails(self):
        self.f.mutate_first(lambda cell:cell.update(split="test"))
        with self.assertRaises((AssertionError,ValueError)):self.f.run()
    def test_any_test_cell_marks_only_its_model_exposed_and_is_not_copied(self):
        model=r.MODELS[0];test=self.f.items[2]
        r.write(r.cell_dir(self.f.source,model,test)/"initial.json",{"exposed":True})
        self.assertEqual(self.f.run(),[model])
        self.assertFalse(r.cell_dir(self.f.out,model,test).exists())
    def test_rehashed_altered_prompt_is_rejected(self):
        def tamper(cell):
            cell["messages"]=[{"role":"user","content":"Different unregistered prompt"}]
            request={"manifest":self.f.manifest,"model":cell["model"],"id":cell["id"],"cell":cell["cell"],
                     "messages":cell["messages"],"max_tokens":64,"temperature":0}
            cell["request_sha256"]=r.sha(r.encode(request))
        self.f.mutate_first(tamper)
        with self.assertRaises((AssertionError,ValueError)):self.f.run()

class NoGenerationForExposedModel(unittest.TestCase):
    def test_exposed_model_skips_fresh_test_even_if_amended_gate_passes(self):
        class FailAdapter:
            def __init__(self,*args,**kwargs):raise AssertionError("Adapter must never be created for exposed model")
        adapter=types.ModuleType("final_praxis.shared_20260912.bedrock_adapter")
        adapter.BedrockAdapter=FailAdapter;adapter.BudgetLedger=lambda *a,**k:None
        lock=types.ModuleType("filelock");lock.FileLock=lambda *a,**k:contextlib.nullcontext()
        modules={"final_praxis":types.ModuleType("final_praxis"),
                 "final_praxis.shared_20260912":types.ModuleType("final_praxis.shared_20260912"),
                 "final_praxis.shared_20260912.bedrock_adapter":adapter,"filelock":lock}
        with tempfile.TemporaryDirectory(prefix="007-exposure-skip-") as directory:
            base=Path(directory);here=base/"study";(here/"data").mkdir(parents=True)
            items=[row(i,"cal" if i<64 else "test") for i in range(192)]
            fixture=r.encode({"items":items});(here/"data/fixtures.json").write_bytes(fixture)
            prereg=b"offline-only";(here/"PREREGISTRATION.md").write_bytes(prereg)
            (here/"inline_parser.py").write_text("# offline parser receipt placeholder",encoding="utf-8")
            out=base/"out"
            with mock.patch.object(r,"HERE",here),mock.patch.object(r,"FIXTURE_SHA",r.sha(fixture)),\
                 mock.patch.object(r,"MODELS",("exposed-model",)),mock.patch.dict(sys.modules,modules),\
                 mock.patch.dict(os.environ,{"PRAXIS_PREREG_SHA256":r.sha(prereg)}),\
                 mock.patch.object(r,"import_calibration",return_value=["exposed-model"]),\
                 mock.patch.object(r,"summarize",return_value={"technical_gate_passed":True}),\
                 mock.patch.object(sys,"argv",["run","--out",str(out),"--source-out",str(base/"source"),"--execute"]),\
                 contextlib.redirect_stdout(io.StringIO()):
                r.main()
            status=json.loads((out/"exposed-model__test_not_started.json").read_text(encoding="utf-8"))
            self.assertEqual(status["reason"],"original_source_has_test_exposure")
            self.assertFalse((out/"cells").exists())

if __name__=="__main__":unittest.main()
