import json
from pathlib import Path
import numpy as np
from sklearn.metrics import balanced_accuracy_score,roc_auc_score

ROOT=Path(__file__).resolve().parent/'results'
load=lambda n:json.loads((ROOT/(n+'.json')).read_bytes())
summary=load('SUMMARY');rows=load('PREDICTIONS');features=load('FEATURES');folds=load('FOLDS')
assert len(rows)==len(features)==summary['sessions']==73
byid={r['id']:r for r in features}
assert len(byid)==73
seen=[]
for fold in folds:
    train,test=set(fold['train_ids']),set(fold['test_ids'])
    assert not train & test
    assert not {byid[i]['command_hash'] for i in train} & {byid[i]['command_hash'] for i in test}
    testtasks={(byid[i]['benchmark'],byid[i]['task']) for i in test}
    assert len(testtasks)==1
    assert not testtasks & {(byid[i]['benchmark'],byid[i]['task']) for i in train}
    seen.extend(test)
assert sorted(seen)==sorted(byid)
y=np.array([r['origin']=='A' for r in rows])
for name,m in summary['metrics'].items():
    p=np.array([r['probabilities'][name] for r in rows])
    assert abs(balanced_accuracy_score(y,p>=.5)-m['balanced_accuracy'])<1e-12
    assert abs(roc_auc_score(y,p)-m['auroc'])<1e-12
    assert sum((p>=.5)&~y)==m['human_false_flags']
    assert sum((p>=.5)&y)==m['ai_detected']
assert all('command_text' not in r for r in features)
assert all(len(r['F'])==len(r['O'])+3 for r in features)
print('PASS: held-task folds, exact-duplicate purge, predictions, metrics and export boundary')
