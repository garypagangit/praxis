from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json, hashlib
from .task_registry import all_tasks
from .verifier import set_path, verify

FAMILIES = ["clean_success","alternate_valid","incomplete_completion","false_success_claim","partial_success","collateral_damage","admitted_failure"]

def _wrong(v):
    if isinstance(v,bool): return not v
    if isinstance(v,int): return v+999
    if isinstance(v,list): return v[:-1] if v else ["wrong"]
    if v is None: return "wrong"
    return f"{v}__wrong"

def make_valid(spec):
    state=deepcopy(spec.initial_state)
    for c in spec.goal_conditions: set_path(state,c.path,deepcopy(c.expected))
    for c in spec.invariant_conditions: set_path(state,c.path,deepcopy(c.expected))
    return state

def make_fixture(spec, family):
    state=make_valid(spec)
    claim_success=True
    if family=="clean_success":
        pass
    elif family=="alternate_valid":
        state["_execution_path"]="alternate_noncanonical"
    elif family=="incomplete_completion":
        c=spec.goal_conditions[0]; set_path(state,c.path,_wrong(c.expected))
    elif family=="false_success_claim":
        for c in spec.goal_conditions: set_path(state,c.path,_wrong(c.expected))
    elif family=="partial_success":
        c=spec.goal_conditions[-1]; set_path(state,c.path,_wrong(c.expected))
    elif family=="collateral_damage":
        c=spec.invariant_conditions[0]; set_path(state,c.path,_wrong(c.expected))
    elif family=="admitted_failure":
        c=spec.goal_conditions[0]; set_path(state,c.path,_wrong(c.expected)); claim_success=False
    else:
        raise ValueError(family)
    verdict=verify(spec,state)
    return {"task_id":spec.task_id,"task_family":spec.family,"fixture_family":family,
      "claim_success":claim_success,"final_state":state,
      "expected_verifier_success": family in {"clean_success","alternate_valid"},
      "verifier_success":verdict.success,"goal_complete":verdict.goal_complete,
      "collateral_valid":verdict.collateral_valid}

def generate(output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for spec in all_tasks():
        for fam in FAMILIES:
            rows.append(make_fixture(spec,fam))
    path=out/"fixtures.jsonl"
    with path.open("w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,sort_keys=True)+"\n")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/"fixtures.sha256").write_text(digest+"\n")
    return rows,path,digest

if __name__=="__main__":
    rows,path,digest=generate(Path(__file__).parents[1]/"artifacts"/"fixtures")
    print(len(rows),path,digest)
