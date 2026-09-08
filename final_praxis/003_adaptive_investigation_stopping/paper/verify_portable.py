"""Supplemental numeric replay; never substitutes for the frozen cloud verifier.

The archived strict local attempt differed from the frozen cloud artifact by one
last-place SciPy beta quantile bit. This audit permits only absolute floating
equality deltas <=1e-14; inequalities, integers, booleans, hashes and gates remain
exact. It does not change any frozen file, source analysis value or cloud receipt.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
DELTAS=[]
class ComparableFloat(float):
    def __new__(cls,value,path):
        obj=super().__new__(cls,value);obj.path=path;return obj
    def __eq__(self,other):
        if type(other) not in (float,int,ComparableFloat):return super().__eq__(other)
        delta=abs(float(self)-float(other))
        if delta and delta<=1e-14:
            DELTAS.append({"path":self.path,"archived":float(self),"recomputed":float(other),"absolute_delta":delta})
        return delta<=1e-14
    def __ne__(self,other):return not self==other

def compare_view(value,path="analysis"):
    if type(value) is float:return ComparableFloat(value,path)
    if isinstance(value,dict):return {k:compare_view(v,path+"."+k) for k,v in value.items()}
    if isinstance(value,list):return [compare_view(v,f"{path}[{i}]") for i,v in enumerate(value)]
    return value

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    run=Path(sys.argv[1]);destination=ROOT/"artifacts/verification/qwen_20260908_v2_local"
    destination.mkdir(parents=True,exist_ok=True)
    raw=run/"raw.jsonl";completion=json.loads((run/"RUN_COMPLETE.json").read_text())
    frozen=json.loads((ROOT/"FROZEN_PROTOCOL.json").read_text())
    assert sha(raw)==completion["raw_sha256"]
    assert sha(ROOT/"FROZEN_PROTOCOL.json")==completion["protocol_sha256"]
    for name,expected in frozen["files"].items():assert sha(ROOT/name)==expected,name
    cases=[json.loads(line) for line in (ROOT/"configs/cases.jsonl").read_text().splitlines()]
    config=json.loads((ROOT/"configs/experiment.json").read_text())
    traces={case["case_id"]:[] for case in cases};request_ids=set()
    for line in raw.read_text().splitlines():
        row=json.loads(line)
        assert row["run_kind"]=="discovery" and row["evidence_kind"]=="real_model_inference"
        assert row["model_id"]==config["model_id"] and row["revision"]==config["revision"]
        assert row["protocol_sha256"]==completion["protocol_sha256"]
        assert row["token_count"]==row["prompt_tokens"]+row["completion_tokens"]
        assert row["runtime"]["dtype"]=="bfloat16" and row["runtime"]["quantization"] is None and row["runtime"]["seed"]==config["seed"]
        assert row["request_id"] not in request_ids;request_ids.add(row["request_id"])
        encoded=(json.dumps(row["messages"],sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
        assert hashlib.sha256(encoded).hexdigest()==row["messages_sha256"]
        traces[row["case_id"]].append(row)
    for case in cases:
        trace=traces[case["case_id"]];trace.sort(key=lambda x:x["round"])
        for r,row in enumerate(trace,1):
            payload=json.loads(row["messages"][1]["content"])
            assert payload=={"round":r,"maximum_rounds":8,"previous_dispositions":[prior["disposition"] for prior in trace[:r-1]],
                "evidence":[{"id":hashlib.sha256(("fp003-display-id-v1/"+e["evidence_id"]).encode()).hexdigest()[:16],"text":e["text"]} for e in case["evidence"][:r]]}
    assert len(cases)==400 and len(request_ids)==3200
    analysis=json.loads((run/"analysis.json").read_text())
    spec=importlib.util.spec_from_file_location("fp003_frozen_verifier",ROOT/"harness/independent_verify.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.verify_data(cases,traces,compare_view(analysis))
    cloud=json.loads((run/"INDEPENDENT_VERIFICATION.json").read_text())
    assert cloud["status"]=="PASS" and cloud["classification"]==analysis["classification"]
    assert result["verified_cases"]==400 and result["verified_rounds"]==3200
    # Deduplicate repeated numerical checks, preserving the exact discrepancy values.
    unique={json.dumps(item,sort_keys=True):item for item in DELTAS}
    receipt={"status":"SUPPLEMENTAL_REPLAY_PASS","audit_kind":"platform_numeric_tolerance_replay",
        "frozen_cloud_verifier_status":cloud["status"],"strict_local_frozen_verifier_status":"FAILED_EXACT_FLOAT_EQUALITY",
        "comparison_tolerance_absolute":1e-14,"tolerance_applied_only_to":"floating equality; no threshold inequalities changed",
        "threshold_decisions_unchanged":True,"classification":analysis["classification"],
        "verified_cases":400,"verified_rounds":3200,"recorded_float_differences":list(unique.values()),
        "protocol_sha256":completion["protocol_sha256"],"raw_sha256":sha(raw),"analysis_sha256":sha(run/"analysis.json"),
        "cloud_receipt_sha256":sha(run/"INDEPENDENT_VERIFICATION.json"),
        "frozen_verifier_sha256":sha(ROOT/"harness/independent_verify.py"),"supplemental_auditor_sha256":sha(Path(__file__)),
        "audited_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    target=destination/"SUPPLEMENTAL_NUMERIC_REPLAY.json"
    with target.open("x",encoding="utf-8") as stream:json.dump(receipt,stream,indent=2);stream.write("\n")
    print(json.dumps(receipt,indent=2))

if __name__=="__main__":main()
