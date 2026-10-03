"""Separate checks of attribution statistics and conservative evidence verification."""
import json,itertools
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def check_claim(members,claim):
    if members is None or len(members)!=3 or any(p is None for p in members):return 'ABSTAIN'
    if any(not np.isfinite(p).all() for p in members):return 'ABSTAIN'
    return 'VERIFIED' if any(int(np.argmax(p))!=0 for p in members)==claim else 'REJECTED'
pool=json.loads(Path('C:/w/explanation_trials_20261003/review_case_pool.json').read_text());counts={'valid':0,'flipped':0,'missing':0}
for c in pool:
    p=c['member_probabilities'];v=c['OR_warns']
    assert check_claim(p,v)=='VERIFIED';counts['valid']+=1
    assert check_claim(p,not v)=='REJECTED';counts['flipped']+=1
    for i in range(3):
        z=p.copy();z[i]=None;assert check_claim(z,v)=='ABSTAIN';counts['missing']+=1
d=dict(np.load('C:/w/explanation_trials_20261003/attributions.npz'));r=json.loads((HERE/'PX101_RESULTS.json').read_text());checks=0
for cell in r['stability']:
    i,j=[s-8101 for s in cell['seeds']];mask=d['cohort']==cell['cohort']
    if cell['stratum']!='all':mask&=(d['warnings'][i]==d['warnings'][j]) if cell['stratum']=='same_warning' else (d['warnings'][i]!=d['warnings'][j])
    values=[]
    for k in np.flatnonzero(mask):
        sets=[set(sorted(range(70),key=lambda f:(-abs(d['attrs'][s,k,f]),f))[:5]) for s in [i,j]]
        values.append(len(sets[0].intersection(sets[1]))/len(sets[0].union(sets[1])))
    assert len(values)==cell['n']
    if values:assert abs(sum(values)/len(values)-cell['mean_top5_jaccard'])<1e-12
    checks+=1
(HERE/'AUDIT.json').write_text(json.dumps({'status':'PASS','evidence_challenges':counts,'independent_stability_cells':checks,'scope':'Specified output flips and missing-member faults only; not adversarial tamper security.'},indent=2)+'\n')
print('PASS',counts,checks)
