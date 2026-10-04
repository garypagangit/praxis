import csv, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from sklearn.metrics import f1_score

H=Path(__file__).resolve().parent
ROOT=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
SEEDS=[8101,8102,8103]
CONDS=['clean','delayed_unavailable','wrong_host_history']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def paths():
    return [H/'run.py',H/'PROTOCOL.md',ROOT/'evaluation_identity.npz']+[ROOT/f'seed_{s}/{c}_b{b}_{pol}.npz' for s in SEEDS for c in CONDS for b in [1,2,3] for pol in ['entropy','harm']]
if sys.argv[1]=='freeze':
    assert not (H/'FREEZE.json').exists()
    save(H/'FREEZE.json',{'utc':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_BEFORE_CALCULATION_ON_EXPOSED_DATA','files':{str(p):sha(p) for p in paths()}})
    print('Frozen');sys.exit()
for p,h in json.loads((H/'FREEZE.json').read_text())['files'].items(): assert sha(Path(p))==h,p
assert not (H/'RESULTS.json').exists()
with np.load(ROOT/'evaluation_identity.npz') as d: y=d['y']
rows=[];flat=[]
for s in SEEDS:
    for c in CONDS:
        for b in [1,2,3]:
            pred=[]
            for pol in ['entropy','harm']:
                with np.load(ROOT/f'seed_{s}/{c}_b{b}_{pol}.npz') as d: pred.append(d['probabilities'].argmax(1))
            old,new=pred
            r={'seed':s,'condition':c,'budget':b,'rows':len(y),'f1_old':float(f1_score(y,old,labels=range(4),average='macro')),'f1_new':float(f1_score(y,new,labels=range(4),average='macro')),'benign_support':int((y==0).sum()),'false_alerts_old':int(((y==0)&(old>0)).sum()),'false_alerts_new':int(((y==0)&(new>0)).sum()),'stages':[]}
            for k in [1,2,3]:
                m=y==k;t=np.bincount(4*old[m]+new[m],minlength=16).reshape(4,4)
                loss=int(t[1:,0].sum());exact=int(t[k,0]);gain=int(t[0,1:].sum());a=int((old[m]>0).sum());z=int((new[m]>0).sum())
                assert gain-loss==z-a
                stage={'stage':k,'support':int(m.sum()),'transition':t.tolist(),'warning_old':a,'warning_new':z,'losses':loss,'exact_to_benign':exact,'wrong_attack_to_benign':loss-exact,'gains':gain,'exact_negative_flips':int(t[k].sum()-t[k,k]),'warning_delta_pp':100*(z-a)/int(m.sum())}
                r['stages'].append(stage)
                flat.append({**{v:r[v] for v in ['seed','condition','budget']},**{v:val for v,val in stage.items() if v!='transition'}})
            r['f1_delta']=r['f1_new']-r['f1_old'];r['fpr_delta_pp']=100*(r['false_alerts_new']-r['false_alerts_old'])/r['benign_support']
            r['descriptive_review_pass']=r['f1_delta']>0 and min(t['warning_delta_pp'] for t in r['stages'])>=-1 and r['fpr_delta_pp']<=.1
            rows.append(r)
out={'experiment':'PX-106','pairs':rows,'new_fits':0,'independent_campaigns':1,'note':'Repeated predictions on exposed test data, not prospective model updates or independent samples.'}
save(H/'RESULTS.json',out)
with (H/'RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
print(json.dumps({'pairs':len(rows),'primary':[{'seed':r['seed'],**r['stages'][2]} for r in rows if r['condition']=='clean' and r['budget']==3],'review_passes':sum(r['descriptive_review_pass'] for r in rows)},indent=2))
