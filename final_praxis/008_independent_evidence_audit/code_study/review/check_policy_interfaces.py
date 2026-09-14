"""Independent acquisition-policy controls using synthetic inputs, no outcomes."""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import math


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--policies',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('policy_review_target',args.policies);policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
    pool=[{'id':f'case-{i:02d}','args':[i-8]} for i in range(16)];original='def f(x): return x > 0';proposal='def f(x): return x >= 1';results=[]
    def check(name,action):
        try:results.append({'id':name,'passed':bool(action())})
        except Exception as exc:results.append({'id':name,'passed':False,'exception':type(exc).__name__,'detail':str(exc)})
    def rejected(action):
        try:action()
        except ValueError:return True
        return False
    before=copy.deepcopy(pool)
    for name in policy.POLICIES:
        chosen=policy.select(pool,original,proposal,[[1]],name,'synthetic',budget=8)
        check(name+'_unique_exact_budget',lambda chosen=chosen:len(chosen['ids'])==len(set(chosen['ids']))==chosen['actual_budget']==8)
        check(name+'_order_invariant_determinism',lambda chosen=chosen,name=name:chosen==policy.select(list(reversed(pool)),original,proposal,[[1]],name,'synthetic',budget=8))
        check(name+'_budget_above_pool',lambda name=name:policy.select(pool,original,proposal,[],name,'synthetic',budget=100)['actual_budget']==16)
        check(name+'_zero_budget',lambda name=name:policy.select(pool,original,proposal,[],name,'synthetic',budget=0)['ids']==[])
        if name in ('edit','complement','hybrid'):
            check(name+'_uniform_probability_floor',lambda chosen=chosen:all(policy.EPSILON/r['remaining']<=r['probability']<=1 for r in chosen['draws']))
    check('pool_unmodified',lambda:pool==before)
    bad=copy.deepcopy(pool);bad[0]['hidden_outcome']=True
    check('forbidden_pool_outcome_field',lambda:rejected(lambda:policy.select(bad,original,proposal,[],'uniform','s')))
    duplicate_id=copy.deepcopy(pool);duplicate_id[1]['id']=duplicate_id[0]['id']
    check('duplicate_test_id',lambda:rejected(lambda:policy.validate_pool(duplicate_id)))
    duplicate_input=copy.deepcopy(pool);duplicate_input[1]['args']=duplicate_input[0]['args']
    check('duplicate_test_arguments',lambda:rejected(lambda:policy.validate_pool(duplicate_input)))
    check('code_is_parsed_not_executed',lambda:policy.select(pool,"raise RuntimeError('must not execute')",proposal,[],'hybrid','s',budget=1)['actual_budget']==1)
    check('invalid_source_static_fallback',lambda:policy.select(pool,'def broken(',proposal,[],'hybrid','s',budget=1)['static_support']=='unparseable_static_fallback')
    w,a=policy.partition_tool_pool(pool,'s')
    check('supplier_independent_disjoint_exhaustive',lambda:({r['id'] for r in w}.isdisjoint({r['id'] for r in a}) and len(w)+len(a)==len(pool)))
    acquired=policy.supplier_acquisition(w,'s',budget=5);passed={r['id']:i<3 for i,r in enumerate(acquired)}
    testimony=policy.testimony(acquired,passed,'selected','s')
    check('selected_witnesses_genuinely_pass',lambda:len(testimony['ids'])==2 and all(passed[i] is True for i in testimony['ids']) and testimony['acquired']==5)
    bad_passed=dict(passed);bad_passed[acquired[0]['id']]='true'
    check('supplier_boolean_outcomes_required',lambda:rejected(lambda:policy.testimony(acquired,bad_passed,'selected','s')))
    all_fail={r['id']:False for r in acquired};infeasible=policy.testimony(acquired,all_fail,'selected','s')
    check('infeasible_attack_no_resampling',lambda:infeasible['ids']==[] and not infeasible['fully_feasible'] and infeasible['acquired']==5)
    check('boolean_is_not_numeric_feature',lambda:not policy.finite_number(True) and policy.features([True])!=policy.features([1]))
    check('impossible_miss_probability_zero',lambda:policy.miss_bound(4,3,2)==0)
    check('empty_sampling_probability_one',lambda:policy.miss_bound(4,3,0)==1)
    check('no_failures_probability_one',lambda:policy.miss_bound(4,0,4)==1)
    check('uniform_bound_matches_hypergeometric',lambda:math.isclose(policy.miss_bound(10,3,4,epsilon=1),math.comb(7,4)/math.comb(10,4)))
    check('invalid_bound_parameters',lambda:rejected(lambda:policy.miss_bound(4,5,1)))
    report={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Outcome-free synthetic input/source controls only; no program execution, real outcome data or model calls.','controls':len(results),'passed':sum(r['passed'] for r in results),'results':results,'policies_sha256':hashlib.sha256(args.policies.read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'controls':report['controls'],'passed':report['passed']}));return 0 if report['controls']==report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
