import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='2'
import argparse,functools,hashlib,importlib.util,json,time,warnings,platform
from pathlib import Path
import numpy as np,joblib,sklearn
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px093_heterogeneous_20260930')
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
OLD=DATA.parents[2]/'praxis_next/px081';AIT=Path('C:/w/campaign_validation_20260928');AE=HERE.parent/'campaign_validation_20260928/evidence'
SIZES=['benign','other_attack','movement','exfiltration'];CONDITIONS=['clean','delayed_unavailable','wrong_host_history']
SETS={'base3':['b8101','b8102','b8103'],'plus_current':['b8101','b8102','b8103','current'],'plus_lr':['b8101','b8102','b8103','lr'],'A6_full':['b8101','b8102','b8103','current','lr'],'heterogeneous3':['b8101','current','lr'],'duplicate_control':['b8101','b8102','b8103','b8101'],'lr_only':['lr'],'current_only':['current']}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,obj):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def capped(data):
    rng=np.random.default_rng(8101);indices=[]
    for k,cap in enumerate([12000,4000,4000,4000]):
        pool=np.flatnonzero((data['split']==0)&(data['y']==k));indices.extend(rng.choice(pool,min(cap,len(pool)),replace=False))
    return np.sort(np.array(indices,dtype=np.int64))
def freeze():
    assert not (HERE/'FREEZE.json').exists();f=json.loads((AE/'FREEZE.json').read_text());paths=[DATA,OLD/'evaluation_identity.npz',OLD/'ARTIFACT_HASHES.json',AE/'FREEZE.json',AE/'ARTIFACTS.json',HERE.parent/'or_gate_20260930/HYPOTHESES.json']
    px=json.loads((HERE.parent/'px081_evidence_acquisition/FREEZE.json').read_text());assert sha(DATA)==px['input_sha256']
    om=json.loads((OLD/'ARTIFACT_HASHES.json').read_text())
    for s in [8101,8102,8103]:
        for c in CONDITIONS:
            p=OLD/f'seed_{s}/{c}_inputs.npz';assert sha(p)==om[str(p.relative_to(OLD))];paths.append(p)
    am={Path(r['path']):r['sha256'] for r in json.loads((AE/'ARTIFACTS.json').read_text())}
    for ex,h in f['prepared_files'].items():
        p=AIT/f'prepared/{ex}.npz';assert sha(p)==h;paths.append(p)
    for ex in f['test_executions']:
        for s in [8101,8102,8103]:
            p=AIT/f'predictions/s{s}_{ex}.npz';assert sha(p)==am[p];paths.append(p)
    paths+=list(HERE.glob('*.py'))+list(HERE.glob('*.md'));from datetime import datetime,timezone
    save(HERE/'FREEZE.json',{'experiment':'PX-093','utc':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_BEFORE_FITS','sklearn':sklearn.__version__,'numpy':np.__version__,'python':platform.python_version(),'sets':SETS,'training_executions':f['train_executions'],'files':{str(p):sha(p) for p in paths},'new_fit_limit':2});OUT.mkdir(exist_ok=True)
def verify():
    f=json.loads((HERE/'FREEZE.json').read_text());assert sklearn.__version__==f['sklearn']
    for p,h in f['files'].items():assert sha(p)==h,p
    return f
def training(domain):
    if domain=='UNRAVELED':
        d=dict(np.load(DATA));ix=capped(d);x=np.column_stack([d['current'][ix],d['roles'][ix]]);return x,d['y'][ix],d['group_sha256'][ix],ix
    f=json.loads((AE/'FREEZE.json').read_text());ds=[dict(np.load(AIT/f'prepared/{e}.npz')) for e in f['train_executions']]
    return np.concatenate([np.column_stack([d['current'],d['history']]) for d in ds]),np.concatenate([d['y'] for d in ds]),np.concatenate([d['key'] for d in ds]),np.arange(sum(len(d['y']) for d in ds))
def evaluation(domain,ex):
    if domain=='UNRAVELED':
        d=dict(np.load(DATA));i=d['split']==2;return np.column_stack([d['current'][i],d['roles'][i]]),d['y'][i],d['group_sha256'][i]
    d=dict(np.load(AIT/f'prepared/{ex}.npz'));return np.column_stack([d['current'],d['history']]),d['y'],d['key']
def fit(domain):
    verify();path=OUT/f'{domain}_lr.joblib';assert not path.exists();t=time.monotonic();x,y,key,indices=training(domain)
    assert not np.isinf(x).any();model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(C=1.,solver='lbfgs',max_iter=500,tol=1e-4,class_weight=None,random_state=8101))
    with threadpool_limits(limits=2),warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');model.fit(x,y)
    fit_seconds=time.monotonic()-t;joblib.dump(model,path);np.save(OUT/f'{domain}_training_indices.npy',indices)
    converged=not any(issubclass(w.category,ConvergenceWarning) for w in caught);record={'domain':domain,'training_rows':len(y),'class_counts':np.bincount(y).tolist(),'training_identity_hash':ah(key),'training_label_hash':ah(y),'selected_indices_hash':ah(indices),'fit_seconds':fit_seconds,'iterations':model[-1].n_iter_.tolist(),'converged':converged,'warnings':[str(w.message) for w in caught],'model_sha256':sha(path),'outputs':[]}
    del x
    for ex in (['UNRAVELED'] if domain=='UNRAVELED' else ['wilson','harrison']):
        xx,yy,kk=evaluation(domain,ex);assert not np.intersect1d(key,kk).size
        with threadpool_limits(limits=2):p=model.predict_proba(xx).astype(np.float32)
        dest=OUT/f'lr_{ex}.npz';np.savez_compressed(dest,p=p,y=yy,key=kk);record['outputs'].append({'execution':ex,'path':str(dest),'sha256':sha(dest),'rows':len(yy),'identity_hash':ah(kk),'label_hash':ah(yy)})
    save(HERE/f'FIT_{domain}.json',record);print('FIT',domain,len(y),fit_seconds,'converged',converged,flush=True)
@functools.lru_cache(maxsize=9)
def old(s,c):return dict(np.load(OLD/f'seed_{s}/{c}_inputs.npz'))
@functools.lru_cache(maxsize=6)
def ait(s,e):return dict(np.load(AIT/f'predictions/s{s}_{e}.npz'))
@functools.lru_cache(maxsize=3)
def lr(e):return dict(np.load(OUT/f'lr_{e}.npz'))
def inputs(ex,cond,b):
    if ex=='pooled':
        aa=inputs('wilson',cond,b);bb=inputs('harrison',cond,b);return ({k:np.concatenate([aa[0][k],bb[0][k]]) for k in aa[0]},np.concatenate([aa[1],bb[1]]),np.concatenate([aa[2],bb[2]]))
    l=lr(ex);vectors={'lr':l['p']};y,key=l['y'],l['key']
    if ex=='UNRAVELED':
        env=old(8101,cond);ok=env['available'][:,0]&(env['delays'][:,0]<=1.0000001)&(b>=1)
        for s in [8101,8102,8103]:
            p=old(s,cond)['probabilities'];vectors[f'b{s}']=np.where(ok[:,None],p[1],p[0])
        vectors['current']=env['probabilities'][0];vectors['lr']=np.where(ok[:,None],l['p'],vectors['current'])
    else:
        for s in [8101,8102,8103]:
            d=ait(s,ex);assert np.array_equal(d['y'],y) and np.array_equal(d['key'],key);vectors[f'b{s}']=d['p1']
        vectors['current']=ait(8101,ex)['p0']
    return vectors,y,key
def gate(ps):
    p=np.array(ps,dtype=np.float64);singles=p.argmax(2);w=singles>0;stage=1+(p[:,:,1:]*w[:,:,None]).sum(0).argmax(1)
    return np.where(w.any(0),stage,0).astype(np.int8),p.mean(0).argmax(1).astype(np.int8),singles
def metrics(y,p,k):
    c=np.bincount(y.astype(int)*k+p,minlength=k*k).reshape(k,k);s=c.sum(1);d=s+c.sum(0);out={'n':len(y),'confusion':c.tolist(),'macro_f1':float(np.divide(2*c.diagonal(),d,out=np.zeros(k),where=d>0).mean()),'false_alerts':int(c[0,1:].sum()),'benign_fpr':float(c[0,1:].sum()/s[0])}
    for i,n in enumerate((SIZES if k==4 else ['benign','other_attack','exfiltration'])[1:],1):out[n]={'support':int(s[i]),'missed':int(c[i,0]),'warning_recall':float(1-c[i,0]/s[i]) if s[i] else None,'exact_recall':float(c[i,i]/s[i]) if s[i] else None}
    return out
def replay():
    verify();assert not (HERE/'RESULTS.json').exists();rows=[];cells=[('UNRAVELED',c,b) for c in CONDITIONS for b in [1,2,3]]+[(e,'clean',2) for e in ['wilson','harrison','pooled']]
    for ex,cond,b in cells:
        v,y,key=inputs(ex,cond,b);k=len(v['lr'][0]);base=gate([v[n] for n in SETS['base3']])[0];bm=metrics(y,base,k);fixed_fa=sum(metrics(y,v[n].argmax(1),k)['false_alerts'] for n in SETS['base3'])/3
        for name,members in SETS.items():
            ps=[v[n] for n in members];op,mp,sp=gate(ps);sm=[metrics(y,p,k) for p in sp];best=min(range(len(sm)),key=lambda i:(sm[i]['exfiltration']['missed'],sm[i]['false_alerts'],i));fa_sum=sum(m['false_alerts'] for m in sm);om=metrics(y,op,k)
            for m in sm:
                for st in ['other_attack','exfiltration']+(['movement'] if k==4 else []):assert om[st]['missed']<=m[st]['missed']
            assert om['false_alerts']<=fa_sum
            if name=='duplicate_control':assert np.array_equal(op>0,base>0)
            cost=0 if all(n=='current' for n in members) else 1 if ex=='UNRAVELED' else 2
            cell=f'{ex}_{cond}_b{b}_{name}';dest=OUT/(cell+'.npz');assert not dest.exists();np.savez_compressed(dest,OR=op,MEAN=mp,best_single=sp[best],spent=np.full(len(y),cost,np.int8))
            lost=(y>0)&(op>0)&(mp==0);allwarn=(sp>0).all(0);unique_ex=int(((y==k-1)&(op>0)&(base==0)).sum());delta=om['false_alerts']-bm['false_alerts']
            for agg,pred in [('OR',op),('MEAN',mp),('best_single',sp[best])]:rows.append({'cell':cell,'execution':ex,'condition':cond,'budget':b,'set':name,'members':members,'aggregator':agg,'model_count':len(members),'evidence_cost':cost,'identity_hash':ah(key),'label_hash':ah(y),'decision_file':str(dest),'decision_sha256':sha(dest),'single_metrics':sm,'best_single_member':members[best],'best_single_warning_recall':sm[best]['exfiltration']['warning_recall'],'overlap_ratio':om['false_alerts']/fa_sum if fa_sum else None,'sum_single_false_alerts':fa_sum,'fixed_base_mean_false_alerts':fixed_fa,'base_OR_metrics':bm,'OR_marginal_attack_warnings':int(((y>0)&(op>0)&(base==0)).sum()),'OR_marginal_exfil_warnings':unique_ex,'OR_marginal_false_alerts':delta,'OR_added_false_alerts_per_exfil_recovery':delta/unique_ex if unique_ex else None,'OR_unrecoverable_attacks':int(((y>0)&(op==0)).sum()),'mean_lost_OR_attack_warnings':int(lost.sum()),'mean_lost_all_members_warn':int((lost&allwarn).sum()),'mean_lost_some_members_benign':int((lost&~allwarn).sum()),**metrics(y,pred,k)})
        print('REPLAY',ex,cond,b,flush=True)
    save(HERE/'RESULTS.json',rows);print('COMPLETE',len(rows),'rows',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','fit-unr','fit-ait','replay']);a=ap.parse_args().action
    if a=='freeze':freeze()
    elif a.startswith('fit'):fit('UNRAVELED' if a=='fit-unr' else 'AIT')
    else:replay()
