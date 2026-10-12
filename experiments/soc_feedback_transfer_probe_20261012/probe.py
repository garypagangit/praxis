"""Fixed exploratory task-transfer comparison; source commands remain inert."""
import collections
import hashlib
import json
from pathlib import Path
import re
import shlex
import warnings
import numpy as np
from scipy.sparse import csr_matrix,hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score,roc_auc_score,confusion_matrix
from sklearn.preprocessing import StandardScaler
from loader import load_data,entities,WRAPPER,SETUP_LITERALS,save

HERE=Path(__file__).resolve().parent
ERROR=re.compile(r'(?i)(?:error|not found|permission denied|failed|unsupported|invalid|traceback)')


def words(command):
    try:return shlex.split(command)
    except ValueError:return command.split()


def local_use(commands,outputs,adjacent):
    supported=hits=used=available=0
    for i in range(len(commands)-1):
        if not adjacent[i] or outputs[i] is None:continue
        available+=1
        new=entities(outputs[i])-entities(commands[i])-SETUP_LITERALS
        found=new & entities(commands[i+1])
        supported+=bool(new);hits+=bool(found);used+=len(found)
    return [hits/available if available else 0,
            hits/supported if supported else 0,
            used/available if available else 0],supported,available


def features(bb,loaded):
    cc=[loaded[b['id'],b['index']][0] for b in bb]
    rr=[loaded[b['id'],b['index']][1] for b in bb]
    rr=[r if b['qualified'] and r is not None and not WRAPPER.search(r) else None for b,r in zip(bb,rr)]
    adjacent=[b['index']==a['index']+1 and (a['log']==b['log'] if a['origin']=='H' else a['reply_message']<b['call_message']) for a,b in zip(bb,bb[1:])]
    tokens=[words(c) for c in cc]
    verbs=[t[0] if t else '' for t in tokens]
    c=[np.mean([len(x) for x in cc]),np.mean([x.count('\n')+1 for x in cc]),
       np.mean([len(x) for x in tokens]),len(set(verbs))/5,
       sum(a==b for a,b in zip(cc,cc[1:]))/4,
       sum(b['px125_syntax']=='single' for b in bb)/5]
    f,supported,available=local_use(cc,rr,adjacent)
    complete=[r for r in rr if r is not None]
    err=[i for i in range(4) if adjacent[i] and rr[i] is not None and ERROR.search(rr[i])]
    o=[len(complete)/5,np.mean([len(r) for r in complete]) if complete else 0,
       np.mean([len(entities(r)) for r in complete]) if complete else 0,
       available/4,supported/available if available else 0,
       sum(bool(ERROR.search(r)) for r in complete)/len(complete) if complete else 0,
       len(err)/4,
       np.mean([cc[i]==cc[i+1] for i in err]) if err else 0,
       np.mean([verbs[i]==verbs[i+1] for i in err]) if err else 0,
       np.mean([abs(len(tokens[i])-len(tokens[i+1])) for i in err]) if err else 0]
    rotated=np.mean([local_use(cc,rr[k:]+rr[:k],adjacent)[0] for k in range(1,5)],axis=0).tolist()
    return {'command_text':'\n'.join(cc),'command_hash':hashlib.sha256(json.dumps(cc).encode()).hexdigest(),
            'C':c,'O':c+o,'F':c+o+f,'R':c+o+rotated,
            'source_diagnostic':[c[1],c[5],o[0],o[1]],
            'opportunity_only':o[:5], 'available_transitions':available,'supported_transitions':supported}


def metrics(y,p):
    pred=np.array(p)>=.5
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
            'auroc':float(roc_auc_score(y,p)),
            'human_false_flags':int(fp),'human_sessions':int(tn+fp),
            'ai_detected':int(tp),'ai_sessions':int(tp+fn)}


def main():
    out=HERE/'results';out.mkdir(exist_ok=True)
    by_session,loaded,sessions,sources=load_data()
    meta={s['id']:s for s in sessions}
    candidates=[]
    for sid,bb in by_session.items():
        if len(bb)<5:continue
        s=meta[sid]
        candidates.append({**{k:s[k] for k in ('id','origin','benchmark','task','family','group')},
                           **features(bb[:5],loaded)})
    shared={(s['benchmark'],s['task']) for s in candidates if s['origin']=='H'} & {
        (s['benchmark'],s['task']) for s in candidates if s['origin']=='A'}
    rows=[s for s in candidates if (s['benchmark'],s['task']) in shared]
    y=np.array([s['origin']=='A' for s in rows],dtype=int)
    keys=[s['benchmark']+':'+s['task'] for s in rows]
    groups=sorted(set(keys))
    names=['C','O','F','R','source_diagnostic','opportunity_only']
    predictions={name:np.full(len(rows),np.nan) for name in names}
    fold_records=[]
    for key in groups:
        test=np.array([i for i,k in enumerate(keys) if k==key])
        held_hashes={rows[i]['command_hash'] for i in test}
        train=np.array([i for i,k in enumerate(keys) if k!=key and rows[i]['command_hash'] not in held_hashes])
        assert set(y[train])=={0,1} and set(y[test])=={0,1}
        vectorizer=TfidfVectorizer(ngram_range=(1,2),max_features=10000)
        train_text=vectorizer.fit_transform([rows[i]['command_text'] for i in train])
        test_text=vectorizer.transform([rows[i]['command_text'] for i in test])
        for name in names:
            scaler=StandardScaler()
            a=scaler.fit_transform(np.array([rows[i][name] for i in train]))
            b=scaler.transform(np.array([rows[i][name] for i in test]))
            if name in ('C','O','F','R'):
                a=hstack([train_text,csr_matrix(a)]);b=hstack([test_text,csr_matrix(b)])
            model=LogisticRegression(C=1,class_weight='balanced',max_iter=3000,random_state=20261012)
            model.fit(a,y[train]);predictions[name][test]=model.predict_proba(b)[:,1]
        fold_records.append({'held_task':key,'train_ids':[rows[i]['id'] for i in train],
            'test_ids':[rows[i]['id'] for i in test],
            'exact_duplicate_rows_purged':len(rows)-len(train)-len(test)})
    assert all(np.isfinite(p).all() for p in predictions.values())
    task_scores=[]
    for key in groups:
        indices=np.array([i for i,k in enumerate(keys) if k==key])
        task_scores.append({'task':key,'metrics':{name:metrics(y[indices],p[indices]) for name,p in predictions.items()}})
    differences=np.array([[t['metrics']['F']['balanced_accuracy']-t['metrics'][baseline]['balanced_accuracy'] for baseline in ('O','R')] for t in task_scores])
    rng=np.random.default_rng(20261012)
    boot=np.array([differences[rng.integers(0,len(groups),len(groups))].mean(axis=0) for _ in range(5000)])
    contrasts={}
    for j,base in enumerate(('O','R')):
        contrasts['F_minus_'+base]={'task_macro_balanced_accuracy_difference':float(differences[:,j].mean()),
            'task_cluster_bootstrap_95_interval':np.quantile(boot[:,j],[.025,.975]).tolist(),
            'positive_tasks':int(sum(differences[:,j]>0)),'negative_tasks':int(sum(differences[:,j]<0)),
            'tied_tasks':int(sum(differences[:,j]==0)),
            'leave_one_task_out_difference_range':[float(np.delete(differences[:,j],i).mean()) for i in range(len(groups))]}
    # Descriptive strata reuse out-of-fold task predictions; not held-family fits.
    families={}
    for family in sorted({r['family'] for r in rows if r['origin']=='A'}):
        ix=[i for i,r in enumerate(rows) if r['origin']=='H' or r['family']==family]
        families[family]={name:metrics(y[ix],p[ix]) for name,p in predictions.items()}
    summary={'date':'2026-10-12','status':'EXPLORATORY_EXPOSED_DATA_PROBE','sessions':len(rows),
        'humans':int(sum(y==0)),'ai':int(sum(y==1)),'tasks':len(groups),
        'human_operators':len({r['group'] for r in rows if r['origin']=='H'}),
        'source_files_verified':len(sources),'model_fits':len(groups)*len(names),
        'metrics':{name:metrics(y,p) for name,p in predictions.items()},
        'task_macro_balanced_accuracy':{name:float(np.mean([t['metrics'][name]['balanced_accuracy'] for t in task_scores])) for name in names},
        'primary_contrasts':contrasts,'family_strata_not_family_holdout':families,
        'available_transition_counts_by_origin':{o:[r['available_transitions'] for r in rows if r['origin']==o] for o in ('H','A')}}
    save(out/'SUMMARY.json',summary)
    save(out/'TASK_SCORES.json',task_scores)
    save(out/'FOLDS.json',fold_records)
    save(out/'SOURCE_BINDINGS.json',sources)
    save(out/'FEATURES.json',[{k:v for k,v in r.items() if k!='command_text'} for r in rows])
    save(out/'PREDICTIONS.json',[{'id':r['id'],'origin':r['origin'],'task':keys[i],
        'probabilities':{name:float(p[i]) for name,p in predictions.items()}} for i,r in enumerate(rows)])
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        main()
