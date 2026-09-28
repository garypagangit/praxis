"""Recompute reported outcomes from saved held-out probabilities and actions."""
import hashlib,json
from pathlib import Path
import numpy as np
import joblib

ROOT=Path(__file__).resolve().parent
WORK=Path('C:/w/campaign_validation_20260928')
checks=[]
def check(name,passed):
    checks.append({'name':name,'passed':bool(passed)})
    if not passed: raise AssertionError(name)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b): return np.isclose(a,b,atol=1e-8,rtol=1e-7)

freeze=json.loads((ROOT/'FREEZE.json').read_text())
results=json.loads((ROOT/'RESULTS.json').read_text())
check('frozen code unchanged',digest(ROOT/'validate.py')==freeze['code_sha256'])
check('frozen protocol unchanged',digest(ROOT/'PROTOCOL.md')==freeze['protocol_sha256'])
check('preparation unchanged',digest(ROOT/'PREPARATION.json')==freeze['preparation_sha256'])
check('disjoint execution split',not(set(freeze['train_executions']) & set(freeze['test_executions'])))
preparation=json.loads((ROOT/'PREPARATION.json').read_text())
by_name={s['execution']:s for s in preparation}
for s in preparation:
    check(s['execution']+' row conservation',s['raw_rows']==sum(s[k] for k in ['eligible_rows','unknown_label_rows','invalid_numeric_rows','duplicate_rows_removed','conflicting_identity_rows']))
    check(s['execution']+' class count conservation',sum(s['class_counts'].values())==s['eligible_rows'])
check('final calendar separation',max(by_name[n]['max_end_ms'] for n in freeze['train_executions'])<min(by_name[n]['min_start_ms'] for n in freeze['test_executions']))
train_keys=np.concatenate([np.load(WORK/'prepared'/f'{n}.npz')['key'] for n in freeze['train_executions']])
for n in freeze['test_executions']:
    check(n+' no train identity hash intersection',not np.isin(np.load(WORK/'prepared'/f'{n}.npz')['key'],train_keys).any())
fit_log=json.loads((ROOT/'FIT_LOG.json').read_text())
check('36 classifier fit records',len(fit_log)==36)
for f in fit_log:
    label=f"fit {f['seed']} {f['fold']} {f['state']}"
    check(label+' held-out execution exclusion',not(set(f['train']) & set(freeze['test_executions'])))
    check(label+' all eligible fitting rows',f['train_rows']==sum(by_name[n]['eligible_rows'] for n in f['train']))
    if f['fold']!='final':
        check(label+' forward development membership',f['train']==freeze['train_executions'][:f['fold']] and f['validation']==freeze['train_executions'][f['fold']])
    else:
        check(label+' all six final training executions',f['train']==freeze['train_executions'])
for name,h in freeze['prepared_files'].items():
    check(name+' prepared hash',digest(WORK/'prepared'/f'{name}.npz')==h)
    d=np.load(WORK/'prepared'/f'{name}.npz')
    has=d['history_count']>0
    check(name+' all history strictly earlier',np.all(d['history_last_end'][has]<d['start'][has]))
    check(name+' all history inside one hour',np.all(d['history_last_end'][has]>=d['start'][has]-3600))
    check(name+' empty histories zero',np.all(d['history'][~has]==0))
    check(name+' no current/history nonfinite',np.isfinite(d['current']).all() and np.isfinite(d['history']).all())
    check(name+' class support',set(d['y'])=={0,1,2})
for seed in freeze['seeds']:
    for policy in ('entropy','harm'):
        model=joblib.load(WORK/'models'/f's{seed}_{policy}.joblib')
        check(f'{seed} {policy} current+probability input width',model.n_features_in_==len(freeze['current_features'])+3)
    oof=np.load(WORK/'predictions'/f's{seed}_development_oof.npz')
    y=oof['y']; p=oof['p0']; q=oof['p1']
    loss0=np.where(p.argmax(1)==y,0,np.take([1,1,4],y))
    loss1=np.where(q.argmax(1)==y,0,np.take([1,1,4],y))
    check(f'{seed} OOF error target',np.array_equal(loss0-loss1,oof['harm_target']))
    e0=-np.sum(np.where(p>0,p*np.log(np.maximum(p,1e-15)),0),axis=1)
    e1=-np.sum(np.where(q>0,q*np.log(np.maximum(q,1e-15)),0),axis=1)
    check(f'{seed} OOF entropy target',np.allclose(e0-e1,oof['entropy_target']))
    for name in freeze['test_executions']:
        d=np.load(WORK/'predictions'/f's{seed}_{name}.npz')
        prep=np.load(WORK/'prepared'/f'{name}.npz')
        check(f'{seed} {name} evaluation key/label identity',np.array_equal(d['key'],prep['key']) and np.array_equal(d['y'],prep['y']))
        for policy in ['none','always_history','entropy','harm']:
            ac=d[policy+'_action']; pr=d[policy+'_p']
            expected=(np.zeros(len(ac),bool) if policy=='none' else np.ones(len(ac),bool) if policy=='always_history' else d[policy+'_gain']>0)
            check(f'{seed} {name} {policy} acquisition rule',np.array_equal(ac,expected))
            check(f'{seed} {name} {policy} selected state',np.array_equal(pr,np.where(ac[:,None],d['p1'],d['p0'])))
            check(f'{seed} {name} {policy} probabilities',np.isfinite(pr).all() and np.all(pr>=0) and np.allclose(pr.sum(1),1,atol=1e-6))
            check(f'{seed} {name} {policy} budget/deadline',np.all(ac.astype(int)*2<=2) and np.all(ac.astype(float)*.75<=1))
for r in results:
    names=freeze['test_executions'] if r['execution']=='pooled' else [r['execution']]
    arrays=[np.load(WORK/'predictions'/f"s{r['seed']}_{n}.npz") for n in names]
    truth=np.concatenate([d['y'] for d in arrays]).astype(int)
    guess=np.concatenate([d[r['policy']+'_p'].argmax(1) for d in arrays])
    action=np.concatenate([d[r['policy']+'_action'] for d in arrays])
    cm=np.bincount(3*truth+guess,minlength=9).reshape(3,3)
    tp=cm.diagonal(); support=cm.sum(axis=1); predicted=cm.sum(axis=0)
    precision=np.divide(tp,predicted,out=np.zeros(3),where=predicted!=0)
    recall=np.divide(tp,support,out=np.zeros(3),where=support!=0)
    f1=np.divide(2*tp,support+predicted,out=np.zeros(3),where=(support+predicted)!=0)
    label=f"{r['seed']} {r['execution']} {r['policy']}"
    check(label+' rows',len(truth)==r['rows'])
    check(label+' confusion matrix',np.array_equal(cm,r['confusion_matrix']))
    expected={'macro_f1':f1.mean(),'exfil_warning_recall':1-cm[2,0]/support[2],
              'exfil_warning_missed':cm[2,0],'exfil_exact_recall':recall[2],
              'benign_false_alerts':cm[0,1:].sum(),'benign_false_alert_rate':cm[0,1:].sum()/support[0],
              'error_rate':1-tp.sum()/len(truth),
              'weighted_error':np.dot(support-tp,[1,1,4])/len(truth),
              'acquired_count':action.sum(),'acquired_fraction':action.mean(),'mean_spend':2*action.mean()}
    for metric,value in expected.items(): check(label+' '+metric,close(value,r[metric]))
    for i,c in enumerate(('benign','other_attack','exfiltration')):
        for metric,value in [('precision',precision[i]),('recall',recall[i]),('f1',f1[i]),('support',support[i])]:
            check(label+' '+c+' '+metric,close(value,r['per_class'][c][metric]))
for f in json.loads((ROOT/'ARTIFACTS.json').read_text()):
    check('artifact '+Path(f['path']).name,digest(Path(f['path']))==f['sha256'])
out={'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks}
(ROOT/'AUDIT.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'passed':out['passed'],'failed':out['failed']}))
