"""Independently reconstruct reported outcomes from frozen source predictions and selected cases."""
from pathlib import Path
import json, hashlib, numpy as np, shutil
HERE=Path(__file__).parent
PRIVATE=Path('C:/w/px107_aws_pilot')
OUT=PRIVATE/'collected/outputs/results'
rows=json.loads((OUT/'RESULTS.json').read_text()); checks=0
expected_hashes=json.loads((HERE/'INPUTS.json').read_text())
for name,h in expected_hashes.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
    checks+=1
for execution in ['wilson','harrison']:
    d=np.load(PRIVATE/f'input/eval_{execution}.npz'); y=d['y']; case=d['case']; ep=d['episode']
    for seed in [8101,8102,8103]:
        pred=np.load(PRIVATE/f'input/pred_{seed}_{execution}.npz')
        saved=np.load(OUT/f'cases_{seed}_{execution}.npz')
        a=pred['p0'].argmax(1)>0; b=pred['p1'].argmax(1)>0
        base=set(case[a].tolist()); allcases=set(case.tolist()); eligible=allcases-base
        ex=set(case[y==2].tolist()); attack=set(case[y>0].tolist())
        epbase=set(ep[(ep>=0)&a].tolist())
        epfull=set(ep[(ep>=0)&(a|b)].tolist())
        for r in [r for r in rows if r['execution']==execution and r['seed']==seed]:
            order=saved['order_'+r['method']]
            assert len(set(order.tolist()))==len(order) and set(order.tolist())==eligible; checks+=2
            selected=set(order[:r['budget']].tolist()); q=np.isin(case,list(selected)); after=a|(q&b)
            newly_warned=set(case[q&b].tolist())-base
            neweps=set(ep[(ep>=0)&after].tolist())-epbase
            values={'queries':len(selected),'new_warning_cases':len(newly_warned),
                    'new_exfil_cases':len(newly_warned&ex),'new_benign_only_cases':len(newly_warned-attack),
                    'new_other_attack_cases':len((newly_warned&attack)-ex),
                    'new_exfil_warn_rows':int(np.count_nonzero(after&~a&(y==2))),
                    'episode_total':len(set(ep[ep>=0].tolist())),'baseline_episode_coverage':len(epbase),
                    'episode_coverage':len(epbase)+len(neweps),'episodes_recovered':len(neweps),
                    'full_history_episode_coverage':len(epfull),'eligible_cases':len(eligible),
                    'baseline_exfil_warn_rows':int(np.count_nonzero(a&(y==2))),
                    'total_exfil_rows':int(np.count_nonzero(y==2))}
            for k,v in values.items():assert r[k]==v,(execution,seed,r['method'],k,r[k],v);checks+=1
            assert len(selected)<=r['budget'] and len(newly_warned)<=r['budget']; checks+=2
aud={'status':'PASS','count_checks':checks,'result_cells':len(rows),'scope':'Source hashes, eligible-case set, selection uniqueness, budgets and outcome counts. Not an independent model reimplementation or causal validation.'}
(HERE/'AUDIT.json').write_text(json.dumps(aud,indent=2))
for name in ['RESULTS.json','RESULTS.csv','CHECKS.json','ENVIRONMENT.json']:shutil.copy2(OUT/name,HERE/name)
print(json.dumps(aud))
