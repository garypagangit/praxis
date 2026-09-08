"""Separate policy/counter implementation: imports neither production policy nor analysis."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta

ROOT=Path(__file__).resolve().parents[1]

def independent_selection(case, trace, arm):
    prior=None;ever_review=False;decisions=[]
    for index,item in enumerate(trace):
        r=index+1;value=item["disposition"]
        risks=[]
        if arm=="A4" and r>=2:
            if case["protected_high_impact"]:risks.append("protected_high_impact")
            if r<case["minimum_review_round"]:risks.append("low_evidence_completeness")
            if prior!=value:risks.append("latest_disposition_flip")
            if value=="abstain":risks.append("abstention")
        stable=r>=2 and prior==value and value!="abstain"
        stop=(arm=="A0" and r==2) or (arm=="A1" and r==8) or (arm in ("A2","A4") and (stable or r==8))
        action="REVIEW" if risks else "STOP" if stop else "CONTINUE"
        decisions.append({"round":r,"action":action,"reasons":risks})
        ever_review=ever_review or action=="REVIEW"
        if action=="STOP" or r==8:
            final="abstain" if action=="REVIEW" else value
            return {"round":r,"disposition":final,"reviewed":ever_review,"abstained":final=="abstain",
                    "decisions":decisions,"token_count":sum(row["token_count"] for row in trace[:r])}
        prior=value

def verify_data(cases,traces,analysis):
    assert len(cases)==len({case["case_id"] for case in cases})
    assert set(traces)=={case["case_id"] for case in cases}
    result_by_id={row["case_id"]:row for row in analysis["case_results"]}
    assert len(result_by_id)==len(cases)==len(analysis["case_results"])
    totals={arm:{"correct":0,"harm":0,"prevented":0,"review":0,"abstain":0,"tokens":0,"rounds":0} for arm in ("A0","A1","A2","A4")}
    events=0;degraded=0;vectors={arm:[] for arm in totals}
    for case in cases:
        cid=case["case_id"];trace=traces[cid]
        assert len(trace)==8
        truth=[]
        for r,row in enumerate(trace,1):
            assert row["case_id"]==cid and row["round"]==r
            assert row["evidence_ids"]==[e["evidence_id"] for e in case["evidence"][:r]]
            try:
                parsed=json.loads(row["raw_response"].strip()).get("disposition","").strip().lower()
                answer=parsed if parsed in ("benign","malicious","abstain") else "abstain"
            except (ValueError,TypeError,AttributeError):answer="abstain"
            assert row["disposition"]==answer
            assert row["correct"]==(answer==case["label"])
            assert type(row["token_count"]) is int and row["token_count"]>0
            truth.append(answer==case["label"])
        count=sum(truth[i] and not truth[i+1] for i in range(7))
        events+=count;degraded+=bool(count)
        for arm in totals:
            chosen=independent_selection(case,trace,arm)
            recorded=result_by_id[cid]["arms"][arm]
            for key,value in chosen.items():assert recorded[key]==value,(cid,arm,key)
            correct=chosen["disposition"]==case["label"]
            vectors[arm].append({**chosen,"correct":int(correct)})
            harm=not correct and any(truth[chosen["round"]:])
            prevented=bool(count) and correct and any(not value for value in truth[chosen["round"]:])
            assert recorded["correct"]==correct and recorded["harm"]==harm and recorded["prevented"]==prevented
            for key,value in {"correct":correct,"harm":harm,"prevented":prevented,"review":chosen["reviewed"],
                              "abstain":chosen["abstained"],"tokens":chosen["token_count"],"rounds":chosen["round"]}.items():
                totals[arm][key]+=value
    assert analysis["degradation_events"]==events and analysis["degradation_cases"]==degraded
    n=len(cases)
    for arm,counts in totals.items():
        s=analysis["arms"][arm];k=counts["harm"]
        upper=1.0 if k==n else float(beta.ppf(.95,k+1,n-k))
        expected={"n":n,"correct":counts["correct"],"accuracy":counts["correct"]/n,"harm_cases":k,
            "harm_rate":k/n,"harm_upper_95":upper,"harm_gate":k/n<=.02 and upper<=.04,
            "prevented_cases":counts["prevented"],"prevention_rate":counts["prevented"]/degraded if degraded else None,
            "review_rate":counts["review"]/n,"abstain_rate":counts["abstain"]/n,"mean_rounds":counts["rounds"]/n,
            "total_tokens":counts["tokens"],"round_saving":1-counts["rounds"]/n/8,
            "token_saving":1-counts["tokens"]/totals["A1"]["tokens"]}
        for key,value in expected.items():assert s[key]==value,(arm,key,s[key],value)
    # Independently regenerate paired resamples and mandatory decisions; never trust a desired label.
    index=np.random.default_rng(20260908).integers(0,n,size=(10000,n))
    accurate={arm:np.array([v["correct"] for v in vals]) for arm,vals in vectors.items()}
    ni={}
    for baseline in ("A0","A1"):
        diff=accurate["A4"]-accurate[baseline]
        ni[baseline]={"difference":float(diff.mean()),"lower_97_5":float(np.quantile(diff[index].mean(axis=1),.025))}
    assert ni==analysis["noninferiority"]
    a4=analysis["arms"]["A4"];a2=analysis["arms"]["A2"]
    equivalent=abs(a4["accuracy"]-a2["accuracy"])<=.01 and abs(a4["token_saving"]-a2["token_saving"])<=.05 \
        and abs(a4["round_saving"]-a2["round_saving"])<=.05 and a4["harm_gate"]==a2["harm_gate"]
    expected_gates={"sample_400":n==400,"H1_noninferiority":all(value["lower_97_5"]>=-.02 for value in ni.values()),
        "H2_cost_reduction":a4["round_saving"]>=.20 and a4["token_saving"]>=.20,
        "H3_prevention":degraded>0 and a4["prevention_rate"]>=.25,"H4_harm":a4["harm_gate"],
        "review_rate":a4["review_rate"]<=.20,"phenomenon_20":events>=20,"A4_not_equivalent_to_A2":not equivalent}
    assert expected_gates==analysis["gates"]
    label="Bounded Positive" if all(expected_gates.values()) else "Mixed" if equivalent and all(v for k,v in expected_gates.items() if k!="A4_not_equivalent_to_A2") else "Negative"
    if not analysis["scientific"]:label="FIXTURE_ONLY"
    elif n!=400:label="Protocol Invalid"
    if analysis.get("run_kind")=="infrastructure_pilot":label="INFRASTRUCTURE_PILOT_ONLY"
    assert label==analysis["classification"]
    rt=np.array([v["round"] for v in vectors["A4"]]);t4=np.array([v["token_count"] for v in vectors["A4"]]);t1=np.array([v["token_count"] for v in vectors["A1"]])
    assert np.quantile(1-rt[index].mean(axis=1)/8,[.025,.975]).tolist()==analysis["round_saving_ci_95"]
    assert np.quantile(1-t4[index].sum(axis=1)/t1[index].sum(axis=1),[.025,.975]).tolist()==analysis["token_saving_ci_95"]
    return {"status":"PASS","verified_cases":n,"verified_rounds":n*8,"degradation_events":events,
            "policy_and_counter_implementation":"independent","fixture_only":not analysis["scientific"]}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);args=p.parse_args()
    frozen=json.loads((ROOT/"FROZEN_PROTOCOL.json").read_text())
    for rel,expected in frozen["files"].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==expected,f"Frozen file changed: {rel}"
    raw=args.run_dir/"raw.jsonl"
    complete=json.loads((args.run_dir/"RUN_COMPLETE.json").read_text())
    pilot=complete.get("run_kind")=="infrastructure_pilot"
    cases=[json.loads(line) for line in (ROOT/("configs/pilot_cases.jsonl" if pilot else "configs/cases.jsonl")).read_text().splitlines()]
    traces={case["case_id"]:[] for case in cases}
    assert complete["evidence_kind"]=="real_model_inference" and complete["completed_rounds"]==len(cases)*8
    assert len(cases)==(2 if pilot else 400)
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==complete["raw_sha256"]
    protocol_hash=hashlib.sha256((ROOT/"FROZEN_PROTOCOL.json").read_bytes()).hexdigest()
    assert complete["protocol_sha256"]==protocol_hash
    config=json.loads((ROOT/"configs/experiment.json").read_text())
    identities=set()
    for line in raw.read_text().splitlines():
        row=json.loads(line)
        assert row["evidence_kind"]=="real_model_inference"
        assert row["model_id"]==config["model_id"] and row["revision"]==config["revision"]
        assert row["protocol_sha256"]==protocol_hash
        assert row["token_count"]==row["prompt_tokens"]+row["completion_tokens"]
        encoded=(json.dumps(row["messages"],sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
        assert hashlib.sha256(encoded).hexdigest()==row["messages_sha256"]
        assert row["runtime"]["dtype"]=="bfloat16" and row["runtime"]["quantization"] is None
        assert row["runtime"]["seed"]==config["seed"]
        assert row["request_id"] not in identities;identities.add(row["request_id"])
        traces[row["case_id"]].append(row)
    for case in cases:
        trace=traces[case["case_id"]];trace.sort(key=lambda row:row["round"])
        for r,row in enumerate(trace,1):
            visible=json.loads(row["messages"][1]["content"])
            assert set(visible)=={"round","maximum_rounds","evidence","previous_dispositions"}
            assert visible["round"]==r and visible["maximum_rounds"]==8
            assert visible["evidence"]==[{"id":hashlib.sha256(("fp003-display-id-v1/"+e["evidence_id"]).encode()).hexdigest()[:16],
                "text":e["text"]} for e in case["evidence"][:r]]
            assert visible["previous_dispositions"]==[prior["disposition"] for prior in trace[:r-1]]
            for arm in ("A0","A1","A2","A4"):
                expected=independent_selection(case,trace[:r],arm)
                # Nonterminated prefix selections have no endpoint yet; inspect all emitted decisions.
                if expected is not None:
                    assert row["policy_decisions"][arm]==expected["decisions"][-1]
    analysis=json.loads((args.run_dir/"analysis.json").read_text())
    result=verify_data(cases,traces,analysis)
    result["raw_sha256"]=complete["raw_sha256"]
    result["protocol_sha256"]=protocol_hash
    result["classification"]=analysis["classification"]
    result["fixture_only"]=False
    result["infrastructure_pilot_only"]=pilot
    path=args.run_dir/"INDEPENDENT_VERIFICATION.json"
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    (args.run_dir/"FINAL_DETERMINATION.md").write_text(
        "# Final Praxis 003 determination\n\n"+analysis["classification"]+"\n\n"
        +f"Independent raw-record and policy audit: PASS. Corpus: {len(cases)} generated inert cases; one real model; eight rounds. "
        +"This supports only this fixed evidence benchmark, not SOC deployment safety.\n\n"
        +"Frozen gates:\n\n"+"\n".join(f"- {key}: {'PASS' if value else 'FAIL'}" for key,value in analysis["gates"].items())+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
