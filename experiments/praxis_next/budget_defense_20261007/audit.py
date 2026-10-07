"""Public arithmetic checks and independent small-case tie enumeration."""
import itertools,json,pathlib
import numpy as np
from run import measure,policies,sha,HERE
r=json.loads((HERE/'RESULTS.json').read_text()); assert len(r['rows'])==600
assert r['code_sha256']==sha(HERE/'run.py')
assert r['protocol_sha256']==sha(HERE/'PROTOCOL.txt')
checks=0
for x in r['rows']:
    b=x['budget']; a=x['above_tp']; t=x['tie_tp']; n=x['ties']; k=x['needed']
    assert b==int(np.ceil(x['n']*x['budget_fraction'])) and x['above']+k==b
    expected=a+k*t/n
    assert np.isclose(x['expected_tp'],expected)
    assert np.isclose(x['precision'],expected/b) and np.isclose(x['recall'],expected/x['positives'])
    assert x['min_tp']==a+max(0,k-(n-t)) and x['max_tp']==a+min(k,t)
    assert 0<=x['min_tp']<=expected<=x['max_tp']<=min(b,x['positives'])
    checks+=6
# Exhaustively enumerate all selections for every binary label vector of 5 tied nodes.
for labels in itertools.product([0,1],repeat=5):
    if not sum(labels): continue
    for k in range(1,6):
        vals=[sum(labels[i] for i in pick) for pick in itertools.combinations(range(5),k)]
        x=measure(np.ones(5),np.array(labels),k/5)
        assert np.isclose(x['expected_tp'],np.mean(vals)) and x['min_tp']==min(vals) and x['max_tp']==max(vals)
        checks+=1
# Permutation equivariance prevents node ID being used as score information.
rng=np.random.default_rng(42); a=[rng.integers(0,8,50) for _ in range(3)]; ix=rng.permutation(50)
for name,s in policies(a).items():
    assert np.allclose(s[ix],policies([v[ix] for v in a])[name]); checks+=1
s=json.loads((HERE/'SUMMARY.json').read_text()); passed=[]
for policy in ['mean','minimum','maximum','median','local_mlp','gin_local','gin_mlp']:
    ok=True
    for ds in ['cadets','theia']:
        p=next(x for x in s if x['dataset']==ds and x['policy']==policy); g=next(x for x in s if x['dataset']==ds and x['policy']=='gin')
        ok &= p['loss']>g['loss'] and p['clean']>=g['clean']-.05
    if ok: passed.append(policy)
out=dict(status='PASS',checks=checks,comparisons=600,policies_meeting_primary_criterion=passed,scope='Arithmetic, tie enumeration and label-free ranking invariance; does not independently validate source labels')
(HERE/'AUDIT.json').write_text(json.dumps(out,indent=2)); print(out)
