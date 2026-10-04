"""Frozen PX-112/113 feasibility runs; public data retained outside git."""
import io, json, time, zipfile, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import beta
from sklearn.model_selection import train_test_split

OUT = Path('C:/w/assurance_batch_20261004')
HERE = Path(__file__).resolve().parent
def save(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')
def fit(x,y,seed):
    return lgb.LGBMClassifier(n_estimators=100,num_leaves=9,random_state=seed,
        n_jobs=2,verbosity=-1).fit(x,y)
def phi(m,x):
    return m.booster_.predict(x,pred_contrib=True,num_threads=2)
def reasons(v):
    return [{'feature':f'F{i}','direction':'increase' if v[i]>0 else 'decrease'}
            for i in np.argsort(-np.abs(v),kind='stable')[:3]]

def main():
    z=zipfile.ZipFile(OUT/'south_german.zip')
    d=pd.read_csv(io.BytesIO(z.read('SouthGermanCredit.asc')),sep=r'\s+')
    assert len(d)==1000 and d.kredit.value_counts().to_dict()=={1:700,0:300}
    x=d.drop(columns='kredit').copy(); y=1-d.kredit # positive = bad credit
    # Ordinal codes retained in order; unordered factors native categorical.
    numeric={'laufzeit','hoehe','alter','rate','wohnzeit','bishkred'}
    cats=[c for c in x if c not in numeric]
    for c in cats: x[c]=x[c].astype('category')
    tr,rest=train_test_split(np.arange(len(d)),train_size=600,stratify=y,random_state=11201)
    ca,te=train_test_split(rest,test_size=200,stratify=y.iloc[rest],random_state=11202)
    m=fit(x.iloc[tr],y.iloc[tr],11201); m.booster_.save_model(str(OUT/'credit_model.txt'))
    save(OUT/'credit_preprocess.json',{'columns':list(x.columns),'categorical':cats,
         'levels':{c:x[c].cat.categories.tolist() for c in cats},'positive':'bad credit',
         'train':tr.tolist(),'calibration':ca.tolist(),'evaluation':te.tolist()})
    d.to_csv(OUT/'credit_full_inputs.csv',index=False)
    phi(m,x.iloc[te[:1]]) # warmup
    t=time.perf_counter(); p=phi(m,x.iloc[te]); eager=time.perf_counter()-t
    np.savez(OUT/'credit_evidence.npz',phi=p,eval_ids=te,prob=m.predict_proba(x.iloc[te])[:,1])
    assert np.allclose(p.sum(axis=1),m.booster_.predict(x.iloc[te],raw_score=True),atol=1e-10)
    costs=[]
    for frac in [.01,.1,.5,1.]:
        n=round(len(te)*frac); t=time.perf_counter()
        q=np.vstack([phi(m,x.iloc[[i]]) for i in te[:n]])
        elapsed=time.perf_counter()-t
        costs.append({'request_fraction':frac,'requests':n,'seconds':elapsed,
                      'max_replay_difference':float(np.max(np.abs(q-p[:n])))})
    t=time.perf_counter(); templates=[reasons(v[:-1]) for v in p]; render=time.perf_counter()-t
    base=[{'id':int(i),'input':d.iloc[i,:-1].tolist(),'probability':float(v)}
          for i,v in zip(te,m.predict_proba(x.iloc[te])[:,1])]
    augmented=[dict(r,contributions=v.tolist()) for r,v in zip(base,p)]
    r112={'id':'PX-112','rows':1000,'split':[600,200,200],'eager_seconds':eager,
          'lazy':costs,'template_render_seconds':render,
          'base_records_bytes':len(json.dumps(base).encode()),
          'records_with_phi_bytes':len(json.dumps(augmented).encode()),
          'sampling_zero_failure_bounds':{str(n):float(beta.ppf(.95,1,n)) for n in [30,100,299,300,1000]},
          'sampling_example_3_of_300_upper':float(beta.ppf(.95,4,297)),
          'evaluation_accuracy':float(np.mean(m.predict(x.iloc[te])==y.iloc[te])),
          'scope':'One warm-process timing per condition; hypothetical request rates, not cost estimates.'}
    save(HERE/'PX112_RESULTS.json',r112)
    payload=[{'row_id':int(te[i]),'probability_bad':float(m.predict_proba(x.iloc[[te[i]]])[0,1]),
              'phi':{f'F{j}':float(v) for j,v in enumerate(p[i,:-1])},'expected':templates[i]}
             for i in range(32)]
    save(OUT/'narrative_inputs.json',payload)
    arff=(OUT/'electricity.arff').read_bytes()
    assert hashlib.md5(arff).hexdigest()=='8ca97867d960ae029ae3a9ac2c923d34'
    e=pd.read_csv(io.StringIO(arff.decode().split('@data')[1]),header=None,
                  names=['date','day','period','nswprice','nswdemand','vicprice','vicdemand','transfer','class'])
    assert len(e)==45312
    e=e.sort_values(['date','period'],kind='stable').reset_index(drop=True)
    ex=e.drop(columns=['date','class']); ey=(e['class']=='UP').astype(int)
    ex['day']=ex.day.astype('category')
    bm=fit(ex.iloc[:10000],ey.iloc[:10000],11301)
    bm.booster_.save_model(str(OUT/'electricity_base.txt'))
    cycles=[]
    for j in range(3):
        end=15000+5000*j; cm=fit(ex.iloc[:end],ey.iloc[:end],11301)
        cm.booster_.save_model(str(OUT/f'electricity_candidate_{j}.txt'))
        r={'cycle':j,'train_end':end}
        evidence={}
        for name,a,b in [('cal',end,end+2000),('eval',end+2000,end+4000)]:
            xx=ex.iloc[a:b]; yy=ey.iloc[a:b].to_numpy()
            bp=bm.predict_proba(xx)[:,1]; cp=cm.predict_proba(xx)[:,1]
            bb=bp>=.5; cb=cp>=.5
            ps=phi(bm,xx)[:,:-1]; qs=phi(cm,xx)[:,:-1]
            tops=np.argsort(-np.abs(ps),axis=1,kind='stable')[:,:3]
            topc=np.argsort(-np.abs(qs),axis=1,kind='stable')[:,:3]
            overlap=float(np.mean([len(set(a)&set(b))/3 for a,b in zip(tops,topc)]))
            r[name]={'base_accuracy':float(np.mean(bb==yy)), 'candidate_accuracy':float(np.mean(cb==yy)),
                'top3_overlap':overlap,'base_positive_recall':float(bb[yy==1].mean()),
                'candidate_positive_recall':float(cb[yy==1].mean()),
                'positive_demotions':int(np.sum((yy==1)&bb&~cb)),
                'positive_recoveries':int(np.sum((yy==1)&~bb&cb))}
            evidence.update({name+'_y':yy,name+'_base':bp,name+'_candidate':cp,
                             name+'_base_phi':ps,name+'_candidate_phi':qs})
        np.savez(OUT/f'electricity_cycle_{j}.npz',**evidence)
        r['gate_P']=r['cal']['candidate_accuracy']>=r['cal']['base_accuracy']
        r['gate_E']=r['cal']['top3_overlap']>=2/3
        r['gate_PE']=r['gate_P'] and r['gate_E']
        r['eval_change_pp']=100*(r['eval']['candidate_accuracy']-r['eval']['base_accuracy'])
        r['harmful']=r['eval_change_pp'] < -1
        cycles.append(r)
    save(HERE/'PX113_RESULTS.json',{'id':'PX-113','rows':len(e),'cycles':cycles,
         'scope':'Three dependent chronological release cycles; market direction, not attack warnings.'})
    print(json.dumps({'112':r112,'113':cycles},indent=2))

if __name__=='__main__': main()
