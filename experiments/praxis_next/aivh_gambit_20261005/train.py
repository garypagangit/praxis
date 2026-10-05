"""Frozen group-separated development comparisons; no shell execution."""
import collections,concurrent.futures,hashlib,json,time
from pathlib import Path
import joblib,numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,confusion_matrix
from common import inputs

OUT=Path('outputs');OUT.mkdir(exist_ok=True)
DATA=json.loads(Path('records.json').read_text());ROWS=DATA['rows'];SEED=11703

def dedup(partitions):
    seen=set();result=[];drops=[]
    for group in partitions:
        local=set();kept=[]
        for r in group:
            key=(r['fingerprint'],r['label'])
            if r['fingerprint'] in seen or key in local:continue
            local.add(key);kept.append(r)
        drops.append(len(group)-len(kept));result.append(kept)
        seen.update(r['fingerprint'] for r in kept)
    return result,drops

def split():
    rng=np.random.default_rng(SEED);parts=[[],[],[]]
    groups=sorted({r['group'] for r in ROWS if r['label']==0});rng.shuffle(groups)
    a=int(.6*len(groups));b=int(.8*len(groups))
    for dest,gs in zip(parts,[groups[:a],groups[a:b],groups[b:]]):
        dest.extend(r for r in ROWS if r['label']==0 and r['group'] in gs)
    for family in sorted({r['family'] for r in ROWS if r['label']==1}):
        rows=[r for r in ROWS if r['family']==family];ix=rng.permutation(len(rows))
        a=int(.6*len(rows));b=int(.8*len(rows))
        for dest,indices in zip(parts,[ix[:a],ix[a:b],ix[b:]]):dest.extend(rows[i] for i in indices)
    return dedup(parts)

def weights(rows,labels):
    counts=collections.Counter((int(y),r['group']) for r,y in zip(rows,labels))
    groups=collections.Counter(y for y,g in counts)
    return np.array([len(rows)/(2*groups[int(y)]*counts[int(y),r['group']]) for r,y in zip(rows,labels)])

def make_model(kind):
    lr=LogisticRegression(C=1,max_iter=2000,random_state=SEED)
    if kind=='length':return make_pipeline(StandardScaler(),lr)
    return make_pipeline(TfidfVectorizer(ngram_range=(1,3) if kind=='verbs' else (1,2),
                         min_df=1,max_features=20000,sublinear_tf=True),lr)

def metrics(rows,scores,threshold):
    y=np.array([r['label'] for r in rows]);scores=np.array(scores);pred=(scores>=threshold).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    hs=collections.defaultdict(list)
    for r,p in zip(rows,pred):
        if r['label']==0:hs[r['group']].append(int(p))
    rates=np.array([np.mean(v) for v in hs.values()]);rng=np.random.default_rng(SEED)
    ci=np.quantile(np.mean(rng.choice(rates,(2000,len(rates)),replace=True),axis=1),[.025,.975]) if len(rates) else [None,None]
    return {'auroc':float(roc_auc_score(y,scores)) if len(set(y))==2 else None,
            'tp':int(tp),'fn':int(fn),'fp':int(fp),'tn':int(tn),
            'agent_recall':float(tp/(tp+fn)) if tp+fn else None,
            'human_window_fpr':float(fp/(fp+tn)) if fp+tn else None,
            'human_group_mean_fpr':float(np.mean(rates)) if len(rates) else None,
            'human_groups_with_any_false_alert':sum(any(v) for v in hs.values()),
            'human_groups':len(hs),'human_group_fpr_bootstrap_ci':[float(v) if v is not None else None for v in ci]}

def fit_eval(kind,name,parts,shuffle=False):
    fit,cal,test=parts
    if any(len({r['label'] for r in p})<2 for p in parts):return {'model':kind,'condition':name,'status':'SKIP_MISSING_CLASS'}
    assert not ({r['group'] for r in fit}&{r['group'] for r in cal+test})
    assert not ({r['group'] for r in cal}&{r['group'] for r in test})
    assert not ({r['fingerprint'] for r in fit}&{r['fingerprint'] for r in cal+test})
    assert not ({r['fingerprint'] for r in cal}&{r['fingerprint'] for r in test})
    human=[r for r in fit if r['label']==0];agents=[r for r in fit if r['label']==1]
    rng=np.random.default_rng(SEED)
    if len(agents)>4*len(human):agents=[agents[i] for i in rng.choice(len(agents),4*len(human),replace=False)]
    fit=human+agents;y=np.array([r['label'] for r in fit]);wy=y.copy()
    if shuffle:
        gs=sorted({r['group'] for r in fit});orig={r['group']:r['label'] for r in fit}
        perm=dict(zip(gs,rng.permutation([orig[g] for g in gs])))
        wy=np.array([perm[r['group']] for r in fit])
    model=make_model(kind);model.fit(inputs(fit,kind),wy,logisticregression__sample_weight=weights(fit,wy))
    pc=model.predict_proba(inputs(cal,kind))[:,1];pt=model.predict_proba(inputs(test,kind))[:,1]
    yc=np.array([r['label'] for r in cal]);wc=weights(cal,yc);hc=yc==0
    thresholds=np.unique(np.r_[0,pc[hc],np.nextafter(pc[hc],np.inf),np.nextafter(1.,np.inf)])
    threshold=next(float(t) for t in thresholds if np.average(pc[hc]>=t,weights=wc[hc])<=.05)
    result={'model':kind,'condition':name,'status':'COMPLETE_DESCRIPTIVE_ONLY','fit_n':len(fit),'cal_n':len(cal),'test_n':len(test),
            'threshold':threshold,'calibration_auroc':float(roc_auc_score(yc,pc)),
            'calibration_group_mean_fpr':float(np.average(pc[hc]>=threshold,weights=wc[hc])),**metrics(test,pt,threshold)}
    result['meets_numerical_target']=bool(result['agent_recall']>=(.7 if name.startswith('family_') else .8) and result['human_group_mean_fpr']<=.05)
    evidence={'fit':[{'id':r['id'],'label_used':int(v)} for r,v in zip(fit,wy)],
              'calibration':[{'id':r['id'],'score':float(s)} for r,s in zip(cal,pc)],
              'test':[{'id':r['id'],'score':float(s)} for r,s in zip(test,pt)]}
    if name=='participant_holdout':
        artifact={'model':model,'kind':kind,'threshold':threshold,'scope':'GAMBiT/Honey common-command development prototype; unassisted-human and APT attribution unverified.'}
        joblib.dump(artifact,OUT/(kind+'.joblib'))
        seen={r['fingerprint'] for r in fit+cal};external=[];used=set()
        for r in DATA['external']:
            if r['fingerprint'] not in seen and r['fingerprint'] not in used:
                external.append(r);used.add(r['fingerprint'])
        if external:
            pe=model.predict_proba(inputs(external,kind))[:,1]
            result['external_kypo']=metrics(external,pe,threshold)
            evidence['external']=[{'id':r['id'],'score':float(s)} for r,s in zip(external,pe)]
    (OUT/(kind+'_'+name+'_predictions.json')).write_text(json.dumps(evidence,indent=2))
    return result

def run(kind,parts):
    results=[fit_eval(kind,'participant_holdout',parts)]
    for family in sorted({r['family'] for r in ROWS if r['label']==1}):
        held=[r for r in parts[2] if r['label']==0]+[r for p in parts for r in p if r['family']==family]
        hfp={r['fingerprint'] for r in held}
        f=[r for r in parts[0] if r['family']!=family and r['fingerprint'] not in hfp]
        c=[r for r in parts[1] if r['family']!=family and r['fingerprint'] not in hfp]
        results.append(fit_eval(kind,'family_'+family,[f,c,held]))
    results.append(fit_eval(kind,'shuffled_fit_labels',parts,True))
    return results

def main():
    start=time.monotonic();parts,drops=split()
    (OUT/'split_manifest.json').write_text(json.dumps({'partitions':[[r['id'] for r in p] for p in parts],'dedup_drops':drops},indent=2))
    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        result=list(pool.map(lambda k:run(k,parts),['length','lexical','verbs']))
    flat=[r for group in result for r in group]
    base=[r for r in flat if r['condition']=='participant_holdout' and r['status']=='COMPLETE_DESCRIPTIVE_ONLY']
    selected=sorted(base,key=lambda r:(-r['calibration_auroc'],r['model']))[0]['model'] if base else None
    (OUT/'RESULTS.json').write_text(json.dumps({'experiment':'PX-117C','seed':SEED,'records_sha256':hashlib.sha256(Path('records.json').read_bytes()).hexdigest(),
        'selected_model':selected,'seconds':time.monotonic()-start,'results':flat},indent=2))
    print(json.dumps({'conditions':len(flat),'selected_model':selected,'seconds':time.monotonic()-start}),flush=True)

if __name__=='__main__':main()
