"""Reconstruct transitions using independent loops and confusion-count arithmetic."""
import hashlib,json
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
data=json.loads((H/'RESULTS.json').read_text());y=np.load(R/'evaluation_identity.npz')['y'];checks=0
for r in data['pairs']:
    preds=[]
    for pol in ['entropy','harm']:
        f=R/f"seed_{r['seed']}/{r['condition']}_b{r['budget']}_{pol}.npz"
        preds.append(np.argmax(np.load(f)['probabilities'],axis=1))
    old,new=preds
    for pol,p in zip(['old','new'],preds):
        conf=np.array([[np.sum((y==a)&(p==b)) for b in range(4)] for a in range(4)])
        macro=np.mean([2*conf[k,k]/(conf[k].sum()+conf[:,k].sum()) for k in range(4)])
        assert abs(macro-r['f1_'+pol])<1e-12
        assert int(conf[0,1:].sum())==r['false_alerts_'+pol];checks+=2
    for st in r['stages']:
        k=st['stage'];m=y==k
        matrix=[[int(np.sum(m&(old==a)&(new==b))) for b in range(4)] for a in range(4)]
        assert matrix==st['transition'];assert sum(map(sum,matrix))==st['support'];checks+=2
        direct={'warning_old':np.sum(m&(old!=0)),'warning_new':np.sum(m&(new!=0)),
          'losses':np.sum(m&(old!=0)&(new==0)),'exact_to_benign':np.sum(m&(old==k)&(new==0)),
          'wrong_attack_to_benign':np.sum(m&(old!=0)&(old!=k)&(new==0)),
          'gains':np.sum(m&(old==0)&(new!=0)), 'exact_negative_flips':np.sum(m&(old==k)&(new!=k))}
        for key,val in direct.items(): assert st[key]==val;checks+=1
        assert st['gains']-st['losses']==st['warning_new']-st['warning_old'];checks+=1
    passing=(r['f1_new']>r['f1_old'] and all(t['warning_delta_pp']>=-1 for t in r['stages']) and 100*(r['false_alerts_new']-r['false_alerts_old'])/np.sum(y==0)<=.1)
    assert r['descriptive_review_pass']==passing;checks+=1
receipt={'status':'PASS','pairs':len(data['pairs']),'checks':checks,'result_sha256':hashlib.sha256((H/'RESULTS.json').read_bytes()).hexdigest(),'new_fits':0}
(H/'AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(receipt)
