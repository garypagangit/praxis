"""Bounded calibration and confirmation; defaults to validation without model load."""
import argparse,hashlib,importlib.util,json,os,time
from pathlib import Path
from intervention import Containment
THRESHOLDS=(0.5,1.0,1.5,2.0)
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def data(x):return (json.dumps(x,sort_keys=True,indent=2)+"\n").encode()
def freeze(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);raw=data(x)
    if p.exists():
        if p.read_bytes()!=raw:raise ValueError("Frozen artifact differs: "+str(p))
    else:
        with p.open("xb") as f:f.write(raw)
def main():
    p=argparse.ArgumentParser()
    for name in ("data","arc-runner","qualification","previous-out","out"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--execute",action="store_true");a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    fixture=read(a.data/"fixture.json");lock=read(a.data/"data_lock.json")
    if sha((a.data/"fixture.json").read_bytes())!=lock["fixture_sha256"]:raise ValueError("Fixture hash differs")
    if len(fixture["calibration"])!=16 or len(fixture["confirmation"])!=32:raise ValueError("Unexpected cohort")
    if {r["id"] for r in fixture["confirmation"]}&set(lock["excluded_previous_test_ids"]):raise ValueError("Exposed test overlap")
    prereg=Path(os.environ["PRAXIS_PREREG_PATH"]);prereg_sha=sha(prereg.read_bytes())
    if prereg_sha!=os.environ["PRAXIS_PREREG_SHA256"]:raise ValueError("Preregistration differs")
    manifest={"protocol":"006-stage2-v1","prereg_sha256":prereg_sha,"data_lock":lock,
        "script_sha256":sha(Path(__file__).read_bytes()),"intervention_sha256":sha(Path(__file__).with_name("intervention.py").read_bytes()),
        "arc_runner_sha256":sha(a.arc_runner.read_bytes()),"thresholds":THRESHOLDS,
        "checkpoint_settings":read(a.qualification/"settings.json"),
        "source_receipts_sha256":sha((a.qualification/"source_receipts.json").read_bytes()),
        "calibration_corruptions":["clean","negate"],"confirmation_corruptions":["clean","negate","permute"],
        "permutation_shift":17,"max_candidate_forwards":3000,"wall_seconds":7200,
        "threshold_selection":"max corrupted calibration correct subject to no clean accuracy loss; ties clean accuracy then fewer interventions then larger threshold",
        "primary_metric":"unnormalized ARC full-choice continuation likelihood","novelty_claim":False}
    freeze(a.out/"manifest.json",manifest);manifest_sha=sha(data(manifest))
    if not a.execute:print("Validated; no model loaded.");return
    if (a.out/"summary.json").exists():
        complete=read(a.out/"summary.json")
        if complete["manifest_sha256"]!=manifest_sha:raise ValueError("Completed result manifest differs")
        print(json.dumps(complete));return
    spec=importlib.util.spec_from_file_location("qualified_arc",a.arc_runner)
    arc=importlib.util.module_from_spec(spec);spec.loader.exec_module(arc)
    model,tokenizer,environment=arc.load_qualified_model(a.qualification,a.previous_out)
    freeze(a.out/"environment.json",environment)
    started=time.monotonic();counter=0
    def raw_score(row,choice,ablation):
        nonlocal counter
        counter+=1
        if counter>3000 or time.monotonic()-started>7200:raise RuntimeError("Bound exceeded")
        return arc.score_candidate(model,tokenizer,row["question"],choice,ablation)
    first=fixture["calibration"][0];choice=first["choices"]["text"][0]
    naked=raw_score(first,choice,[])["log_likelihood"]
    control=Containment(model)
    try:
        control.configure("none","clean",2,0,"sanity")
        sham=raw_score(first,choice,[])["log_likelihood"]
        control.configure("always","clean",2,0,"sanity")
        always=raw_score(first,choice,[])["log_likelihood"]
        control.configure("permanent","clean",2,0,"sanity")
        permanent=raw_score(first,choice,["social"])["log_likelihood"]
        sanity={"sham_abs_delta":abs(naked-sham),"always_vs_permanent_abs_delta":abs(always-permanent)}
        freeze(a.out/"sanity.json",sanity)
        if sanity["sham_abs_delta"]>1e-6 or sanity["always_vs_permanent_abs_delta"]>1e-4:
            raise RuntimeError("Hook identity or constant-ablation equivalence failed")
        def cell(split,row,corruption,policy,threshold=2.0,rate=0.0):
            ident=[manifest_sha,split,row["id"],corruption,policy,threshold,rate]
            path=a.out/"cells"/(sha(data(ident))+".json")
            if path.exists():
                prior=read(path)
                if prior["identity"]!=ident:raise ValueError("Cell identity differs")
                return prior
            cell_started=time.monotonic();scores=[];eligible=interventions=0
            for label,text in zip(row["choices"]["label"],row["choices"]["text"]):
                # No corruption flag in random seed; no gold in any gate argument.
                control.configure(policy,corruption,threshold,rate,f"{row['id']}:{label}")
                score=raw_score(row,text,["social"] if policy=="permanent" else [])
                score["monitor"]=dict(control.stats);scores.append(score)
                eligible+=control.stats["eligible"];interventions+=control.stats["interventions"]
            ll=[s["log_likelihood"] for s in scores]
            predicted=row["choices"]["label"][arc.winner(ll)]
            record={"identity":ident,"split":split,"id":row["id"],"corruption":corruption,"policy":policy,
                "threshold":threshold,"random_rate":rate,"scores":scores,"prediction":predicted,"gold":row["answerKey"],
                "correct":predicted==row["answerKey"],"eligible":eligible,"interventions":interventions,"seconds":time.monotonic()-cell_started}
            freeze(path,record);return record
        cal={}
        for corruption in ("clean","negate"):
            for policy,threshold in [("none",2.0),("permanent",2.0)]+[("conditional",t) for t in THRESHOLDS]:
                rows=[cell("calibration",r,corruption,policy,threshold) for r in fixture["calibration"]]
                cal[(corruption,policy,threshold)]=rows
        clean_base=sum(r["correct"] for r in cal[("clean","none",2.0)])
        candidates=[]
        for threshold in THRESHOLDS:
            clean=cal[("clean","conditional",threshold)];corrupt=cal[("negate","conditional",threshold)]
            candidates.append({"threshold":threshold,"clean_correct":sum(r["correct"] for r in clean),
                "corrupt_correct":sum(r["correct"] for r in corrupt),
                "interventions":sum(r["interventions"] for r in clean+corrupt),
                "eligible":sum(r["eligible"] for r in clean+corrupt)})
        admissible=[x for x in candidates if x["clean_correct"]>=clean_base]
        if not admissible:raise RuntimeError("Even disabled gate failed clean retention")
        best=max(admissible,key=lambda x:(x["corrupt_correct"],x["clean_correct"],-x["interventions"],x["threshold"]))
        threshold=best["threshold"];rate=best["interventions"]/best["eligible"] if best["eligible"] else 0
        calibration={"manifest_sha256":manifest_sha,"candidates":candidates,"selected":best,
                     "random_rate":rate,"clean_baseline_correct":clean_base,"selection_uses_confirmation":False}
        freeze(a.out/"calibration_frozen.json",calibration)
        confirmation=[]
        for row in fixture["confirmation"]:
            for corruption in ("clean","negate","permute"):
                for policy in ("none","permanent","conditional","random"):
                    confirmation.append(cell("confirmation",row,corruption,policy,threshold,rate))
            print(json.dumps({"completed_confirmation_questions":1+fixture["confirmation"].index(row),"forward_calls":counter}),flush=True)
        report={"status":"COMPLETED_MECHANISTIC_FEASIBILITY","manifest_sha256":manifest_sha,
            "calibration":calibration,"candidate_forwards_this_execution":counter,"elapsed_seconds":time.monotonic()-started,"n":32,"metrics":{},
            "corruption":"synthetic norm-preserving residual actuator; not naturally incorrect reasoning",
            "novel_method_established":False}
        for corruption in ("clean","negate","permute"):
            for policy in ("none","permanent","conditional","random"):
                rows=[r for r in confirmation if r["corruption"]==corruption and r["policy"]==policy]
                report["metrics"][corruption+"/"+policy]={"correct":sum(r["correct"] for r in rows),
                    "accuracy":sum(r["correct"] for r in rows)/32,"interventions":sum(r["interventions"] for r in rows),
                    "eligible":sum(r["eligible"] for r in rows)}
        pairs={r["id"]:{(c["corruption"],c["policy"]):c for c in confirmation if c["id"]==r["id"]} for r in fixture["confirmation"]}
        report["clean_permanent_harms"]=sum(x[("clean","none")]["correct"] and not x[("clean","permanent")]["correct"] for x in pairs.values())
        report["negation_damages_clean_correct"]=sum(x[("clean","none")]["correct"] and not x[("negate","none")]["correct"] for x in pairs.values())
        report["conditional_recovers_negation_damage"]=sum(x[("clean","none")]["correct"] and not x[("negate","none")]["correct"] and x[("negate","conditional")]["correct"] for x in pairs.values())
        report["conditional_clean_losses"]=sum(x[("clean","none")]["correct"] and not x[("clean","conditional")]["correct"] for x in pairs.values())
        report["requires_further_confirmation"]=True
        freeze(a.out/"summary.json",report);print(json.dumps(report))
    finally:control.close()
if __name__=="__main__":main()


