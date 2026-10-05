"""Frozen descriptive source-transfer experiment; no logged commands execute."""
import concurrent.futures,hashlib,json,os,platform,time,subprocess,sys
from pathlib import Path
import joblib,numpy as np,sklearn
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score,confusion_matrix

OUT=Path('outputs'); OUT.mkdir(exist_ok=True)
ROWS=json.loads(Path('records.json').read_text())
SEED=11701
FEATURES=sorted(ROWS[0]['features'])

def split():
    rng=np.random.default_rng(SEED); groups=[[],[],[]]
    for label in [0,1]:
        rows=[r for r in ROWS if r['label']==label]
        order=rng.permutation(len(rows)); a=int(.6*len(rows));b=int(.8*len(rows))
        for dest,indices in zip(groups,[order[:a],order[a:b],order[b:]]):dest.extend(rows[i] for i in indices)
    seen=set(); clean=[]; removed=[]
    for group in groups:
        kept=[];drop=0;local=set()
        for r in group:
            key=(r['fingerprint'],r['label'])
            if r['fingerprint'] in seen or key in local:drop+=1;continue
            local.add(key);kept.append(r)
        seen.update(r['fingerprint'] for r in kept)
        clean.append(kept);removed.append(drop)
    return clean,removed

def input_for(rows,kind):
    if kind=='ngrams':return [r['text'] for r in rows]
    if kind=='length':return np.array([[r['n_commands']] for r in rows])
    return np.array([[r['features'][k] for k in FEATURES] for r in rows])

def model_for(kind):
    if kind=='ngrams':return make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=20000,sublinear_tf=True),LogisticRegression(C=1,class_weight='balanced',max_iter=1500,random_state=SEED))
    if kind=='length':return LogisticRegression(C=1,class_weight='balanced',max_iter=1000,random_state=SEED)
    return HistGradientBoostingClassifier(max_iter=150,max_depth=3,l2_regularization=1,class_weight='balanced',random_state=SEED)

def evaluate(kind,fit,cal,test,name):
    before=time.monotonic()
    if any(len({r['label'] for r in group})!=2 for group in [fit,cal,test]):
        return {'name':name,'model':kind,'status':'SKIPPED_MISSING_CLASS'},None
    rng=np.random.default_rng(SEED)
    human=[r for r in fit if r['label']==0]; agents=[r for r in fit if r['label']==1]
    if len(agents)>4*len(human):agents=[agents[i] for i in rng.choice(len(agents),4*len(human),replace=False)]
    fit=human+agents
    assert not ({r['fingerprint'] for r in fit}&{r['fingerprint'] for r in cal+test})
    assert not ({r['fingerprint'] for r in cal}&{r['fingerprint'] for r in test})
    model=model_for(kind);model.fit(input_for(fit,kind),[r['label'] for r in fit])
    pc=model.predict_proba(input_for(cal,kind))[:,list(model.classes_).index(1)]
    pt=model.predict_proba(input_for(test,kind))[:,list(model.classes_).index(1)]
    yc=np.array([r['label'] for r in cal]);yt=np.array([r['label'] for r in test])
    thresholds=np.unique(np.r_[0,pc[yc==0],np.nextafter(pc[yc==0],np.inf),np.nextafter(1.,np.inf)])
    threshold=next(float(t) for t in thresholds if np.mean(pc[yc==0]>=t)<=.05)
    pred=(pt>=threshold).astype(int);tn,fp,fn,tp=confusion_matrix(yt,pred,labels=[0,1]).ravel()
    result={'name':name,'model':kind,'status':'COMPLETE_DESCRIPTIVE_ONLY','fit_n':len(fit),'cal_n':len(cal),'test_n':len(test),
        'calibration_auroc':float(roc_auc_score(yc,pc)),'threshold':threshold,
        'calibration_human_fpr':float(np.mean(pc[yc==0]>=threshold)),
        'test_auroc':float(roc_auc_score(yt,pt)),'agent_recall':float(tp/(tp+fn)),
        'human_fpr':float(fp/(fp+tn)),'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp),
        'seconds':time.monotonic()-before}
    (OUT/(name+'_'+kind+'_predictions.json')).write_text(json.dumps({'fit_ids':[r['id'] for r in fit],
        'calibration':[{'id':r['id'],'label':r['label'],'score':float(s)} for r,s in zip(cal,pc)],
        'test':[{'id':r['id'],'label':r['label'],'score':float(s)} for r,s in zip(test,pt)]},indent=2))
    return result,{'model':model,'kind':kind,'threshold':threshold,'feature_names':FEATURES,
        'scope':'Exploratory source-confounded prototype. Not validated for autonomous-AI attribution or APT detection.'}

def run_kind(kind,groups):
    fit,cal,test=groups
    result,artifact=evaluate(kind,fit,cal,test,'record_holdout')
    if artifact:joblib.dump(artifact,OUT/(kind+'.joblib'))
    all_results=[result]
    for family in sorted({r['family'] for r in ROWS if r['label']==1}):
        held=[r for r in test if r['label']==0]+[r for r in ROWS if r['label']==1 and r['family']==family]
        # Global dedup priority prevents reintroducing earlier aliases in held-out probes.
        held=list({(r['fingerprint'],r['label']):r for r in held}.values())
        hfp={r['fingerprint'] for r in held}
        f=[r for r in fit if r['family']!=family and r['fingerprint'] not in hfp]
        c=[r for r in cal if r['family']!=family and r['fingerprint'] not in hfp]
        all_results.append(evaluate(kind,f,c,held,'family_'+family)[0])
    for task in sorted({r['task'] for r in ROWS if r['label']==0}):
        held=[r for r in test if r['label']==1]+[r for r in ROWS if r['label']==0 and r['task']==task]
        held=list({(r['fingerprint'],r['label']):r for r in held}.values()); hfp={r['fingerprint'] for r in held}
        f=[r for r in fit if r['task']!=task and r['fingerprint'] not in hfp]
        c=[r for r in cal if r['task']!=task and r['fingerprint'] not in hfp]
        all_results.append(evaluate(kind,f,c,held,'human_task_'+task.replace(' ','_'))[0])
    (OUT/(kind+'_results.json')).write_text(json.dumps(all_results,indent=2))
    print(kind+' completed',flush=True)
    return all_results

def main():
    groups,removed=split()
    (OUT/'split_manifest.json').write_text(json.dumps({'seed':SEED,'duplicate_removals':removed,
        'partitions':[[r['id'] for r in g] for g in groups]},indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        all_results=list(pool.map(lambda kind:run_kind(kind,groups),['length','ngrams','tree']))
    candidates=[r[0] for r in all_results if r[0]['status']=='COMPLETE_DESCRIPTIVE_ONLY']
    best=max(candidates,key=lambda r:(r['calibration_auroc'],r['model']))
    export_checks=[]
    artifact=joblib.load(OUT/(best['model']+'.joblib'))
    for label in [0,1]:
        row=next(r for r in groups[2] if r['label']==label)
        path=OUT/('example_'+str(label)+'.json');path.write_text(json.dumps(row['commands']))
        cli=subprocess.run([sys.executable,'predict.py','--model',str(OUT/(best['model']+'.joblib')),'--commands',str(path)],capture_output=True,text=True,check=True)
        decoded=json.loads(cli.stdout)
        expected=float(artifact['model'].predict_proba(input_for([row],best['model']))[0,1])
        assert abs(decoded['ai_score']-expected)<1e-10
        export_checks.append({'id':row['id'],'prediction_matches_saved_model':True,'output':decoded})
    (OUT/'EXPORT_CHECKS.json').write_text(json.dumps(export_checks,indent=2))
    result={'stage':'DEVELOPMENT_ONLY_NOT_APT_VALIDATION','results':[r for arm in all_results for r in arm],
        'selected_model':best['model'],'selection_rule':'highest calibration AUROC, alphabetical model tie-break',
        'scope':'Source and class are perfectly associated. These scores do not establish AI-versus-human detection in matched conditions.',
        'source_identity_rule_accuracy_by_construction':1.,'python':platform.python_version(),'sklearn':sklearn.__version__,
        'numpy':np.__version__,'records_sha256':hashlib.sha256(Path('records.json').read_bytes()).hexdigest()}
    (OUT/'RESULTS.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'selected_model':best['model'],'comparisons':len(result['results'])}),flush=True)

if __name__=='__main__':main()
