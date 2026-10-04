"""Independent replay checks; does not refit or select thresholds."""
import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import beta
HERE=Path(__file__).resolve().parent
OUT=Path('C:/w/assurance_batch_20261004')
checks=[]
def check(name,condition):
    checks.append({'check':name,'pass':bool(condition)})
    assert condition,name
freeze=json.loads((HERE/'FREEZE.json').read_text())
check('protocol hash',hashlib.sha256((HERE/'PROTOCOL.txt').read_bytes()).hexdigest()==freeze['protocol_sha256'])
for f,h in freeze['data_sha256'].items(): check('data hash '+f,hashlib.sha256((OUT/f).read_bytes()).hexdigest()==h)
meta=json.loads((OUT/'credit_preprocess.json').read_text())
sets=[set(meta[k]) for k in ['train','calibration','evaluation']]
check('credit splits disjoint',all(not sets[i]&sets[j] for i in range(3) for j in range(i)))
check('credit splits cover 1000',len(set.union(*sets))==1000)
data=pd.read_csv(OUT/'credit_full_inputs.csv').drop(columns='kredit')
for col in meta['categorical']: data[col]=pd.Categorical(data[col],categories=meta['levels'][col])
model=lgb.Booster(model_file=str(OUT/'credit_model.txt'))
evidence=np.load(OUT/'credit_evidence.npz')
replay=model.predict(data.iloc[meta['evaluation']],pred_contrib=True,num_threads=2)
check('saved model exactly replays contributions',np.array_equal(replay,evidence['phi']))
check('contributions add to margin',np.allclose(replay.sum(1),model.predict(data.iloc[meta['evaluation']],raw_score=True,num_threads=2)))
r112=json.loads((HERE/'PX112_RESULTS.json').read_text())
check('all lazy replay comparisons exact',all(r['max_replay_difference']==0 for r in r112['lazy']))
check('zero-failure binomial bounds',all(abs(float(v)-(1-.05**(1/int(n))))<1e-12 for n,v in r112['sampling_zero_failure_bounds'].items()))
for c in json.loads((HERE/'PX113_RESULTS.json').read_text())['cycles']:
    ev=np.load(OUT/f'electricity_cycle_{c["cycle"]}.npz')
    for split in ['cal','eval']:
        yy=ev[split+'_y']; b=ev[split+'_base']>=.5; p=ev[split+'_candidate']>=.5
        check(f'cycle {c["cycle"]} {split} paired counts',len(yy)==len(b)==len(p)==2000)
        check(f'cycle {c["cycle"]} {split} accuracies',np.mean(b==yy)==c[split]['base_accuracy'] and np.mean(p==yy)==c[split]['candidate_accuracy'])
        check(f'cycle {c["cycle"]} {split} demotions',int(np.sum((yy==1)&b&~p))==c[split]['positive_demotions'])
        check(f'cycle {c["cycle"]} {split} recoveries',int(np.sum((yy==1)&~b&p))==c[split]['positive_recoveries'])
    check(f'cycle {c["cycle"]} frozen gates',c['gate_P']==(c['cal']['candidate_accuracy']>=c['cal']['base_accuracy']) and c['gate_E']==(c['cal']['top3_overlap']>=2/3) and c['gate_PE']==(c['gate_P'] and c['gate_E']))
    check(f'cycle {c["cycle"]} harm definition',c['harmful']==(c['eval_change_pp'] < -1))
result={'status':'PASS','checks':checks,'scope':'PX112/113 artifact replay and metric checks; not independent dataset replication.'}
(HERE/'NUMERIC_AUDIT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(f'{len(checks)} numeric audit checks passed')
