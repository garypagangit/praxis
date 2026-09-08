from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import json, sys
from .task_registry import all_tasks
from .verifier import verify

EXPECTED={"clean_success":True,"alternate_valid":True,"incomplete_completion":False,
"false_success_claim":False,"partial_success":False,"collateral_damage":False,"admitted_failure":False}

def validate(path):
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    errors=[]
    if len(rows)!=140: errors.append(f"COUNT:{len(rows)}")
    c=Counter((r["task_id"],r["fixture_family"]) for r in rows)
    for spec in all_tasks():
        for fam in EXPECTED:
            if c[(spec.task_id,fam)]!=1:
                errors.append(f"COVERAGE:{spec.task_id}:{fam}:{c[(spec.task_id,fam)]}")
    toggles=defaultdict(lambda:{"T":0,"F":0})
    for r in rows:
        spec=next(x for x in all_tasks() if x.task_id==r["task_id"])
        v=verify(spec,r["final_state"])
        if v.success != EXPECTED[r["fixture_family"]]:
            errors.append(f"VERDICT:{r['task_id']}:{r['fixture_family']}:{v.success}")
        if v.success != r["verifier_success"]:
            errors.append(f"REPLAY:{r['task_id']}:{r['fixture_family']}")
        for k,val in v.goal_predicates.items(): toggles[(r["task_id"],"g",k)]["T" if val else "F"]+=1
        for k,val in v.protected_invariants.items(): toggles[(r["task_id"],"i",k)]["T" if val else "F"]+=1
    for spec in all_tasks():
        for cnd in spec.goal_conditions:
            if toggles[(spec.task_id,"g",cnd.path)]["T"]==0:
                errors.append(f"GOAL_NEVER_TRUE:{spec.task_id}:{cnd.path}")
        first=spec.goal_conditions[0].path
        if toggles[(spec.task_id,"g",first)]["F"]==0:
            errors.append(f"GOAL_NO_NEGATIVE:{spec.task_id}:{first}")
        for cnd in spec.invariant_conditions:
            if toggles[(spec.task_id,"i",cnd.path)]["T"]==0:
                errors.append(f"INV_NEVER_TRUE:{spec.task_id}:{cnd.path}")
        firsti=spec.invariant_conditions[0].path
        if toggles[(spec.task_id,"i",firsti)]["F"]==0:
            errors.append(f"INV_NO_NEGATIVE:{spec.task_id}:{firsti}")
    return errors

if __name__=="__main__":
    path=Path(__file__).parents[1]/"artifacts"/"fixtures"/"fixtures.jsonl"
    errors=validate(path)
    if errors:
        print("FAIL",len(errors)); print("\n".join(errors[:50])); sys.exit(1)
    print("PASS 140/140 fixture coverage and deterministic replay")
