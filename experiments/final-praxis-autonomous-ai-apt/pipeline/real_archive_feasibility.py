"""Real-archive feasibility screen. Publishes aggregates only; never executes commands."""
import argparse,collections,json,re,zipfile,platform
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import balanced_accuracy_score,f1_score
from grounded_synthetic import digest,command_stats,entropy

N=10
STRUCT=['length_mean','length_cv','flag_fraction','pipe_fraction','chain_fraction','redirect_fraction','unique_command_fraction']
ALL=['executable_diversity','transition_entropy','immediate_repeat','discovery_vocabulary','tool_vocabulary']+STRUCT

def clean(cs):
    return [str(c).strip() for c in cs if str(c).strip().lower() not in {'','na','none','nan'}]

def extract(cs):
    cs=clean(cs)
    if len(cs)<N:return None
    cs=cs[:N]; lens=np.array([len(c) for c in cs]); base=command_stats(cs)
    if base is None:return None
    return base+[float(lens.mean()),float(lens.std()/lens.mean()),sum(bool(re.search(r'(?:^|\s)--?\w',c)) for c in cs)/N,sum('|' in c for c in cs)/N,sum('&&' in c or ';' in c for c in cs)/N,sum('>' in c for c in cs)/N,len(set(cs))/N]

def weights(df):
    w=1/df.groupby(['label','group'])['label'].transform('size').to_numpy(float)
    for label in [0,1]:w[df.label.to_numpy()==label]/=w[df.label.to_numpy()==label].sum()
    return w*len(df)/2

def evaluate(df,pred):
    w=weights(df); y=df.label.to_numpy();return {'group_balanced_accuracy':float(balanced_accuracy_score(y,pred,sample_weight=w)), 'group_weighted_macro_f1':float(f1_score(y,pred,average='macro',sample_weight=w)), 'human_or_source0_false_positive':float(np.average(pred[y==0],weights=w[y==0])), 'ai_or_source1_recall':float(np.average(pred[y==1],weights=w[y==1]))}

def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    rows=[]; fingerprints=set();audit=collections.Counter();manifest=[]
    def file(p):manifest.append({'file':p.name,'sha256':digest(p),'bytes':p.stat().st_size})
    def add(cs,source,group):
        cs=clean(cs);v=extract(cs)
        if v is None:audit[source+'_too_short']+=1;return
        # Global exact first-window deduplication BEFORE splitting. Never perturb duplicates.
        import hashlib
        fp=hashlib.sha256(json.dumps(cs[:N]).encode()).hexdigest()
        if fp in fingerprints:audit[source+'_duplicate_window']+=1;return
        fingerprints.add(fp);rows.append(dict(source=source,group=source+':'+group,label=int(source!='gambit'),**dict(zip(ALL,v))))
    p=Path(args.human);file(p);hg=collections.defaultdict(list)
    for e in json.loads(p.read_text()):
        if not clean([e['command']]):audit['human_placeholder']+=1;continue
        if pd.isna(pd.to_datetime(e['timestamp'],errors='coerce',utc=True)):audit['human_invalid_time']+=1;continue
        hg[(e['participant'],e['timestamp'][:10])].append(e)
    for (person,day),es in sorted(hg.items()):add([e['command'] for e in sorted(es,key=lambda e:e['timestamp'])],'gambit',person)
    p=Path(args.honey);file(p)
    with zipfile.ZipFile(p) as z:
        ns=sorted(n for n in z.namelist() if n.endswith('.json'));rng=np.random.default_rng(20261020)
        for i in sorted(rng.choice(len(ns),min(1800,len(ns)),replace=False)):
            ts=json.loads(z.read(ns[i]));cs=[t[2][1] for t in ts[1:] if isinstance(t,list) and len(t)>2 and isinstance(t[2],list) and len(t[2])>1 and t[2][0]=='raw_command']
            add(cs,'honey',ns[i].split('/')[-2])
    for p in sorted(Path(args.cochise).glob('*.json')):
        file(p);cs=[];model=None
        for l in p.read_text().splitlines():
            if not l.strip():continue
            e=json.loads(l)
            if e.get('event')=='configuration':model=e.get('model')
            if e.get('event')=='tool_call' and e.get('tool_name')=='execute_command':cs.append(e.get('params',{}).get('command',''))
        if not model:audit['cochise_missing_model']+=1;continue
        add(cs,'cochise',model)
    df=pd.DataFrame(rows);results=[];split_audit=[]
    for seed in [19,29,39,49,59]:
        rng=np.random.default_rng(seed);trainparts={};testparts={}
        for source in ['gambit','honey','cochise']:
            sub=df[df.source==source];gs=np.array(sorted(sub.group.unique()));rng.shuffle(gs);cut=max(2,int(.7*len(gs)));trainparts[source]=sub[sub.group.isin(gs[:cut])];testparts[source]=sub[~sub.group.isin(gs[:cut])]
            assert set(trainparts[source].group).isdisjoint(testparts[source].group)
        tasks=[]
        for source,other in [('honey','cochise'),('cochise','honey')]:
            tr=pd.concat([trainparts['gambit'],trainparts[source]])
            tasks.extend([(source+'_within',tr,pd.concat([testparts['gambit'],testparts[source]])),(source+'_to_'+other,tr,pd.concat([testparts['gambit'],df[df.source==other]]))])
        # Same origin (AI), different archives: source recognition is a confounding diagnostic.
        tr=pd.concat([trainparts['honey'].assign(label=0),trainparts['cochise'].assign(label=1)])
        te=pd.concat([testparts['honey'].assign(label=0),testparts['cochise'].assign(label=1)])
        tasks.append(('ai_source_probe',tr,te))
        for task,tr,te in tasks:
            assert set(tr.group).isdisjoint(te.group)
            split_audit.append({'seed':seed,'task':task,'train_rows':len(tr),'test_rows':len(te),'train_groups':tr.group.nunique(),'test_groups':te.group.nunique()})
            for rep,cols in [('all',ALL),('structural',STRUCT)]:
                for name,clf in [('logistic',LogisticRegression(C=1,max_iter=1000)),('random_forest',RandomForestClassifier(n_estimators=150,max_depth=4,min_samples_leaf=3,random_state=seed)),('svm',SVC(C=1,kernel='rbf'))]:
                    model=make_pipeline(StandardScaler(),clf);kw={list(model.named_steps)[-1]+'__sample_weight':weights(tr)}
                    model.fit(tr[cols],tr.label,**kw);pred=model.predict(te[cols]);r=evaluate(te,pred);results.append(dict(seed=seed,task=task,representation=rep,model=name,**r))
                # Group-level shuffled training labels, evaluated against untouched test labels.
                groups=tr[['group','label']].drop_duplicates(); labels=groups.label.to_numpy().copy();rng.shuffle(labels);mapping=dict(zip(groups.group,labels));null=tr.copy();null['label']=null.group.map(mapping)
                model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000));model.fit(null[cols],null.label,logisticregression__sample_weight=weights(null));results.append(dict(seed=seed,task=task,representation=rep,model='null_logistic',**evaluate(te,model.predict(te[cols]))))
    r=pd.DataFrame(results);r.to_csv(out/'scores.csv',index=False)
    summary=r.groupby(['task','representation','model']).agg(ba_mean=('group_balanced_accuracy','mean'),ba_min=('group_balanced_accuracy','min'),ba_max=('group_balanced_accuracy','max'),f1_mean=('group_weighted_macro_f1','mean'),false_positive_mean=('human_or_source0_false_positive','mean'),recall_mean=('ai_or_source1_recall','mean')).reset_index();summary.to_csv(out/'summary.csv',index=False)
    meta={'window_commands':N,'features':ALL,'structural_features':STRUCT,'exclusions':dict(audit),'counts':df.groupby('source').size().to_dict(),'groups':df.groupby('source').group.nunique().to_dict(),'inputs':manifest,'script_sha256':digest(__file__),'helper_sha256':digest(Path(__file__).with_name('grounded_synthetic.py')),'python':platform.python_version(),'seeds':[19,29,39,49,59],'split_audit':split_audit}
    (out/'audit.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:meta[k] for k in ['counts','groups','exclusions']}));print(summary.to_string(index=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--human',required=True);p.add_argument('--honey',required=True);p.add_argument('--cochise',required=True);p.add_argument('--output',required=True);run(p.parse_args())
