"""Real eight-round inference with immutable inputs, append-only records and resume."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import sys
import threading
import time
from pathlib import Path
try:
    from .cases import ROOT,canonical,digest
    from .trace_schema import disposition
    from .policies import select,ARMS
except ImportError:
    from cases import ROOT,canonical,digest
    from trace_schema import disposition
    from policies import select,ARMS

REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO))
SYSTEM=("You classify inert security triage cases from staged evidence. The benchmark defines malicious as "
        "an actually executed action that lacks approval matching its actor, asset and inclusive time interval; "
        "benign requires all three approval conditions to match and no other out-of-scope activity. "
        "A signed authoritative audit takes precedence over provisional tickets, unverified notes and weak alerts. "
        "Using only evidence shown so far, output exactly one JSON object with the single field disposition, "
        "whose value is benign, malicious, or abstain. Choose abstain if evidence does not support a disposition. "
        "Do not browse or invent evidence. Do not include reasoning or Markdown.")

def messages_for(case,round_number,prior):
    # Explicit projection: hidden labels and private ground-truth records never leave the runner.
    visible={"round":round_number,"maximum_rounds":8,
             "evidence":[{"id":e["evidence_id"],"text":e["text"]} for e in case["evidence"][:round_number]],
             "previous_dispositions":[row["disposition"] for row in prior]}
    return [{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps(visible,sort_keys=True)}]

def preflight():
    frozen=json.loads((ROOT/"FROZEN_PROTOCOL.json").read_text())
    for rel,expected in frozen["files"].items():
        if digest(ROOT/rel)!=expected:raise ValueError(f"Frozen hash mismatch: {rel}")
    marker=json.loads((ROOT/"FIXTURE_GATE.json").read_text())
    if marker["status"]!="PASS" or marker["traces"]<80:raise ValueError("Fixture gate missing")
    for rel,expected in marker["harness_sha256"].items():
        if digest(ROOT/rel)!=expected:raise ValueError(f"Fixture-tested code changed: {rel}")
    manifest=json.loads((ROOT/"configs/case_manifest.json").read_text())
    if manifest["count"]!=400 or manifest["rounds"]!=8 or digest(ROOT/"configs/cases.jsonl")!=manifest["case_sha256"]:
        raise ValueError("Missing frozen 400-case evidence manifest")
    cases=[json.loads(line) for line in (ROOT/"configs/cases.jsonl").read_text().splitlines()]
    if len(cases)!=400 or [case["case_id"] for case in cases]!=manifest["case_ids"]:
        raise ValueError("Corpus identity mismatch")
    for case in cases:
        truth=case["hidden_ground_truth"]
        benign=(truth["event_actor"]==truth["allowed_actor"] and truth["event_asset"]==truth["allowed_asset"]
                and truth["allowed_start"]<=truth["minute"]<=truth["allowed_end"])
        if case["label"]!=("benign" if benign else "malicious"):raise ValueError("Label provenance mismatch")
    return json.loads((ROOT/"configs/experiment.json").read_text()),cases,digest(ROOT/"FROZEN_PROTOCOL.json")

def main():
    p=argparse.ArgumentParser();p.add_argument("--run-dir",type=Path);p.add_argument("--base-url")
    p.add_argument("--resume",action="store_true");p.add_argument("--preflight-only",action="store_true")
    p.add_argument("--pilot",action="store_true",help="Run only the two frozen infrastructure cases; never discovery evidence")
    p.add_argument("--pilot-verification",type=Path,default=ROOT/"artifacts/pilot/qwen_20260908/INDEPENDENT_VERIFICATION.json")
    args=p.parse_args();config,cases,protocol_hash=preflight()
    case_path=ROOT/("configs/pilot_cases.jsonl" if args.pilot else "configs/cases.jsonl")
    if args.pilot:cases=[json.loads(line) for line in case_path.read_text().splitlines()]
    expected_rounds=len(cases)*8
    if args.preflight_only:
        print(json.dumps({"status":"PASS","cases":len(cases),"rounds":expected_rounds,"protocol_sha256":protocol_hash}));return
    if not args.run_dir:raise ValueError("--run-dir required")
    if not args.pilot:
        pilot_receipt=json.loads(args.pilot_verification.read_text())
        if pilot_receipt.get("status")!="PASS" or pilot_receipt.get("classification")!="INFRASTRUCTURE_PILOT_ONLY" \
                or pilot_receipt.get("verified_rounds")!=16 or pilot_receipt.get("protocol_sha256")!=protocol_hash:
            raise ValueError("Matching independent infrastructure pilot verification is required.")
    run_dir=args.run_dir.resolve()
    if run_dir.exists() and not args.resume:raise FileExistsError("Use a new run directory.")
    run_dir.mkdir(parents=True,exist_ok=True)
    if (run_dir/"RUN_COMPLETE.json").exists():raise ValueError("Completed discovery cannot be rerun.")
    if len(list(run_dir.glob("INFRA_FAILURE_*.json")))>config["maximum_infrastructure_retries"]:
        raise ValueError("Frozen infrastructure retry allowance exhausted.")
    contract={"evidence_kind":"real_model_inference","model_id":config["model_id"],"revision":config["revision"],
              "run_kind":"infrastructure_pilot" if args.pilot else "discovery",
              "seed":config["seed"],"protocol_sha256":protocol_hash,"case_sha256":digest(case_path),
              "concurrency":config["concurrency"],"max_new_tokens":config["max_new_tokens"]}
    start_path=run_dir/"RUN_START.json"
    if start_path.exists():
        if json.loads(start_path.read_text())!=contract:raise ValueError("Resume contract differs")
    else:start_path.write_bytes(canonical(contract))
    raw=run_dir/"raw.jsonl";existing={case["case_id"]:[] for case in cases}
    if raw.exists():
        for line in raw.read_text().splitlines():
            row=json.loads(line)
            if row["protocol_sha256"]!=protocol_hash or row["model_id"]!=config["model_id"] or row["revision"]!=config["revision"]:
                raise ValueError("Stored row identity differs")
            existing[row["case_id"]].append(row)
    for cid,trace in existing.items():
        trace.sort(key=lambda row:row["round"])
        if [row["round"] for row in trace]!=list(range(1,len(trace)+1)):raise ValueError(f"Non-prefix resume: {cid}")
    from final_praxis.shared.model_adapter import HTTPAdapter,TransformersAdapter
    adapter=HTTPAdapter(args.base_url,config["model_id"],config["revision"]) if args.base_url else \
        TransformersAdapter(config["model_id"],config["revision"],seed=config["seed"])
    lock=threading.Lock();completed=[sum(len(trace) for trace in existing.values())]
    def collect(case):
        trace=existing[case["case_id"]]
        for r in range(len(trace)+1,9):
            messages=messages_for(case,r,trace)
            begun=time.monotonic()
            result=adapter.generate(messages,max_new_tokens=config["max_new_tokens"],temperature=0)
            if result["model_id"]!=config["model_id"] or result["revision"]!=config["revision"]:
                raise ValueError("Model adapter identity mismatch")
            for field in ("prompt_tokens","completion_tokens"):
                if type(result[field]) is not int or result[field]<0:raise ValueError("Invalid measured token usage")
            answer=disposition(result["text"])
            row={**contract,"case_id":case["case_id"],"round":r,"evidence_ids":[e["evidence_id"] for e in case["evidence"][:r]],
                 "raw_response":result["text"],"disposition":answer,"correct":answer==case["label"],
                 "prompt_tokens":result["prompt_tokens"],"completion_tokens":result["completion_tokens"],
                 "token_count":result["prompt_tokens"]+result["completion_tokens"],"request_id":result["request_id"],
                 "runtime":result["runtime"],"messages":messages,
                 "messages_sha256":hashlib.sha256(canonical(messages)).hexdigest(),
                 "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "elapsed_seconds":time.monotonic()-begun}
            trace.append(row)
            # Full-trace collection continues even when a policy would stop; no arm changes evidence.
            row["policy_decisions"]={arm:select(case,trace,arm)["decisions"][-1] for arm in ARMS}
            with lock:
                with raw.open("ab") as out:out.write(canonical(row));out.flush()
                completed[0]+=1
                if completed[0]%80==0:print(json.dumps({"completed_rounds":completed[0],"total":expected_rounds}),flush=True)
        return case["case_id"]
    failures=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=config["concurrency"] if args.base_url else 1) as pool:
        jobs={pool.submit(collect,case):case["case_id"] for case in cases}
        for future in concurrent.futures.as_completed(jobs):
            try:future.result()
            except Exception as exc:
                failures.append({"case_id":jobs[future],"error":f"{type(exc).__name__}: {exc}"})
    if failures:
        path=run_dir/f"INFRA_FAILURE_{time.time_ns()}.json";path.write_bytes(canonical(failures))
        raise RuntimeError(f"{len(failures)} incomplete cases; preserved raw outputs. Resume only after infrastructure correction.")
    if completed[0]!=expected_rounds:raise ValueError("Incomplete run")
    receipt={**contract,"completed_rounds":expected_rounds,"completed_cases":len(cases),"raw_sha256":digest(raw),
             "completed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (run_dir/"RUN_COMPLETE.json").write_bytes(canonical(receipt));print(json.dumps(receipt,indent=2))

if __name__=="__main__":main()
