"""Frozen adapted AIT campaign validation. No row sampling, tuning, or role inputs."""
import argparse, hashlib, json, platform, time, zipfile
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from acquire_qualify import labels, DATA, ROOT

WORK = DATA.parent
PREP = WORK/'prepared'
MODELS = WORK/'models'
PRED = WORK/'predictions'
CLASSES = ['benign', 'other_attack', 'exfiltration']
SEEDS = [8101,8102,8103]
CURRENT = ['udp','log_duration_s','log_client_packets','log_server_packets',
           'log_client_bytes','log_server_bytes','client_byte_fraction','client_packet_fraction',
           'log_client_bytes_per_packet','log_server_bytes_per_packet']
HISTORY = ['log_count','log_bytes','log_packets','log_mean_bytes','log_mean_packets',
           'mean_log_duration_s','udp_fraction','log_seconds_since_last_end']

def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def read_execution(p):
    parts = []
    with zipfile.ZipFile(p) as z:
        for name in sorted(z.namelist()):
            if not name.endswith('.csv'): continue
            udp = 'udp' in name
            mapping = ({'#c_ip:1':'cli','s_ip:10':'srv','c_port:2':'cport','s_port:11':'sport',
                        'c_first_abs:3':'start','c_durat:4':'cdur','s_first_abs:12':'sstart',
                        's_durat:13':'sdur','c_bytes_all:5':'cb','s_bytes_all:14':'sb',
                        'c_pkts_all:6':'cp','s_pkts_all:15':'sp','label':'label'} if udp else
                       {'#15#c_ip:1':'cli','s_ip:15':'srv','c_port:2':'cport','s_port:16':'sport',
                        'first:29':'start','last:30':'end','c_bytes_all:9':'cb','s_bytes_all:23':'sb',
                        'c_pkts_all:3':'cp','s_pkts_all:17':'sp','label':'label'})
            with z.open(name) as r:
                d = pd.read_csv(r, usecols=list(mapping), low_memory=False).rename(columns=mapping)
            for col in set(d.columns)-{'cli','srv','label'}:
                d[col] = pd.to_numeric(d[col], errors='coerce')
            if udp:
                cs = d['start'].to_numpy().copy()
                ss = d['sstart'].to_numpy()
                # Missing peer observations have zero start; do not make an epoch-zero flow.
                d['end'] = np.maximum(cs+d['cdur'].to_numpy(), np.where(ss>0, ss+d['sdur'].to_numpy(), cs))
                d['start'] = np.minimum(cs, np.where(ss>0, ss, cs))
                d = d.drop(columns=['sstart','cdur','sdur'])
            d['udp'] = int(udp)
            d['member'] = name
            d['source_row'] = np.arange(len(d), dtype=np.int64)
            parts.append(d)
    return pd.concat(parts, ignore_index=True)

def prepare():
    PREP.mkdir(parents=True, exist_ok=True)
    stats = []
    for p in sorted(DATA.glob('*_netflows.zip')):
        name = p.stem.replace('_netflows','')
        d = read_execution(p)
        s = {'execution':name,'raw_rows':len(d)}
        raw_min_start = float(d['start'].min())
        y = d['label'].map(labels())
        valid_label = y.notna()
        valid_numeric = (np.isfinite(d[['start','end','cp','sp','cb','sb','cport','sport']]).all(axis=1)
                         & (d['start']>0) & (d['end']>=d['start'])
                         & (d[['cp','sp','cb','sb','cport','sport']]>=0).all(axis=1))
        s['unknown_label_rows'] = int((~valid_label).sum())
        s['invalid_numeric_rows'] = int((valid_label & ~valid_numeric).sum())
        d = d[valid_label & valid_numeric].copy()
        d['y'] = y[valid_label & valid_numeric].astype(np.int8)
        identity = ['udp','cli','srv','cport','sport','start','end','cp','sp','cb','sb']
        # Native-label conflicts are excluded even if both map to the same broad class.
        conflicts = d.groupby(identity, dropna=False, sort=False)['label'].transform('nunique').gt(1)
        s['conflicting_identity_rows'] = int(conflicts.sum())
        d = d[~conflicts].copy()
        dupe = d.duplicated(identity, keep='first')
        s['duplicate_rows_removed'] = int(dupe.sum())
        d = d[~dupe].sort_values(['start','end','member','source_row'], kind='stable').reset_index(drop=True)
        keys = pd.util.hash_pandas_object(d[identity],index=False).to_numpy(np.uint64)
        t = d['start'].to_numpy(np.float64)/1000
        end = d['end'].to_numpy(np.float64)/1000
        cp,sp,cb,sb = [d[c].to_numpy(np.float64) for c in ['cp','sp','cb','sb']]
        udp = d['udp'].to_numpy(np.float64)
        duration = end-t
        total_b,total_p = cb+sb,cp+sp
        cur = np.column_stack([udp,np.log1p(duration),np.log1p(cp),np.log1p(sp),
                              np.log1p(cb),np.log1p(sb),cb/np.maximum(total_b,1),
                              cp/np.maximum(total_p,1),np.log1p(cb/np.maximum(cp,1)),
                              np.log1p(sb/np.maximum(sp,1))]).astype(np.float32)
        history = np.zeros((len(d),len(HISTORY)),np.float32)
        latest = np.full(len(d),-1.0,np.float64)
        history_count = np.zeros(len(d),np.int64)
        audit_samples = []
        for _, idx in d.groupby('cli',sort=False).indices.items():
            by_end = idx[np.argsort(end[idx],kind='stable')]
            e = end[by_end]
            lo = np.searchsorted(e,t[idx]-3600,side='left')
            hi = np.searchsorted(e,t[idx],side='left')
            count = hi-lo
            vals = np.column_stack([total_b[by_end],total_p[by_end],np.log1p(duration[by_end]),udp[by_end]])
            pref = np.vstack([np.zeros((1,4)),np.cumsum(vals,axis=0)])
            sums = pref[hi]-pref[lo]
            denom = np.maximum(count,1)
            b,pkt,ld,u = sums.T
            has = count>0
            last = np.where(has,e[np.maximum(hi-1,0)],-1)
            latest[idx] = last
            history_count[idx] = count
            age = np.where(has,t[idx]-last,0)
            history[idx] = np.column_stack([np.log1p(count),np.log1p(b),np.log1p(pkt),
                                           np.log1p(b/denom),np.log1p(pkt/denom),ld/denom,
                                           u/denom,np.log1p(age)])
            assert np.all(last[has]<t[idx][has])
            assert np.all(last[has]>=t[idx][has]-3600)
            # Brute-force samples use direct Boolean membership, independently of searchsorted.
            for q in idx[np.linspace(0,len(idx)-1,min(3,len(idx)),dtype=int)]:
                prior = idx[(end[idx]<t[q]) & (end[idx]>=t[q]-3600)]
                assert len(prior)==history_count[q]
                assert np.isclose(np.expm1(history[q,1]),total_b[prior].sum(),rtol=2e-6,atol=.01)
                audit_samples.append(int(q))
        assert np.isfinite(cur).all() and np.isfinite(history).all()
        s.update(eligible_rows=len(d),raw_min_start_ms=raw_min_start,
                 min_start_ms=float(d['start'].min()),max_end_ms=float(d['end'].max()),
                 class_counts={c:int((d.y==i).sum()) for i,c in enumerate(CLASSES)},
                 history_rows=int((history_count>0).sum()),history_sample_checks=len(audit_samples),
                 strict_history_time_passed=True)
        np.savez_compressed(PREP/f'{name}.npz',current=cur,history=history,y=d.y.to_numpy(np.int8),
                            key=keys,start=t,end=end,history_last_end=latest,history_count=history_count,
                            member=d.member.to_numpy(str),source_row=d.source_row.to_numpy(np.int64))
        s['prepared_sha256']=sha(PREP/f'{name}.npz')
        stats.append(s)
        print('PREPARED',name,len(d),s['class_counts'],flush=True)
    ordered = sorted(stats,key=lambda s:(s['raw_min_start_ms'],s['execution']))
    train = [s['execution'] for s in ordered[:6]]
    test = [s['execution'] for s in ordered[6:]]
    train_keys = np.concatenate([np.load(PREP/f'{name}.npz')['key'] for name in train])
    cross = {}
    for name in test:
        data = dict(np.load(PREP/f'{name}.npz'))
        mask = ~np.isin(data['key'],train_keys)
        cross[name] = int((~mask).sum())
        # A nonzero hash intersection needs original-field equality review before fitting.
        # Abort rather than silently call a hash collision an exact duplicate.
        assert mask.all(), 'Cross-execution identity overlap: review full source fields before fitting.'
    save(ROOT/'PREPARATION.json',stats)
    freeze = {'created_utc':pd.Timestamp.now(tz='UTC').isoformat(), 'train_executions':train,
              'test_executions':test,'current_features':CURRENT,'history_features':HISTORY,
              'seeds':SEEDS,'cross_execution_identity_hash_overlaps':cross,
              'strict_calendar_train_before_test':max(s['max_end_ms'] for s in ordered[:6])<min(s['min_start_ms'] for s in ordered[6:]),
              'protocol_sha256':sha(ROOT/'PROTOCOL.md'),'code_sha256':sha(Path(__file__)),
              'preparation_sha256':sha(ROOT/'PREPARATION.json'),
              'prepared_files':{s['execution']:s['prepared_sha256'] for s in stats},
              'software':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'lightgbm':lgb.__version__}}
    save(ROOT/'FREEZE.json',freeze)
    print('FROZEN',json.dumps(freeze),flush=True)

def classifier(seed):
    return lgb.LGBMClassifier(n_estimators=150,num_leaves=15,learning_rate=.05,
                             min_child_samples=10,reg_lambda=1,n_jobs=4,verbosity=-1,
                             random_state=seed,deterministic=True,force_col_wise=True)

def regressor(seed):
    return lgb.LGBMRegressor(n_estimators=100,num_leaves=9,learning_rate=.05,
                            min_child_samples=20,reg_lambda=1,n_jobs=4,verbosity=-1,
                            random_state=seed,deterministic=True,force_col_wise=True)

def fit_model(x,y,seed):
    if len(np.unique(y))==1: return int(y[0])
    return classifier(seed).fit(x,y)

def predict(model,x):
    p = np.zeros((len(x),3),np.float32)
    if isinstance(model,int): p[:,model]=1
    else: p[:,model.classes_.astype(int)]=model.predict_proba(x)
    return p

def entropy(p): return -(p*np.log(np.maximum(p,1e-15))).sum(axis=1)

def metrics(y,p,action):
    pred = p.argmax(axis=1)
    cm = confusion_matrix(y,pred,labels=[0,1,2])
    pr,re,f1,_ = precision_recall_fscore_support(y,pred,labels=[0,1,2],zero_division=0)
    ex = y==2
    ben = y==0
    return {'rows':len(y),'confusion_matrix':cm.tolist(),'macro_f1':float(f1.mean()),
            'per_class':{c:{'precision':float(pr[i]),'recall':float(re[i]),'f1':float(f1[i]),'support':int((y==i).sum())} for i,c in enumerate(CLASSES)},
            'exfil_warning_recall':float((pred[ex]!=0).mean()) if ex.any() else None,
            'exfil_warning_missed':int((pred[ex]==0).sum()),'exfil_exact_recall':float(re[2]),
            'benign_false_alerts':int((pred[ben]!=0).sum()),
            'benign_false_alert_rate':float((pred[ben]!=0).mean()) if ben.any() else None,
            'error_rate':float((pred!=y).mean()),
            'weighted_error':float((np.array([1,1,4])[y]*(pred!=y)).mean()),
            'acquired_count':int(action.sum()),'acquired_fraction':float(action.mean()),
            'mean_spend':float(2*action.mean())}

def run():
    freeze=json.loads((ROOT/'FREEZE.json').read_text())
    assert freeze['code_sha256']==sha(Path(__file__))
    assert freeze['protocol_sha256']==sha(ROOT/'PROTOCOL.md')
    all_data={}
    for name,h in freeze['prepared_files'].items():
        assert sha(PREP/f'{name}.npz')==h
        all_data[name]=dict(np.load(PREP/f'{name}.npz'))
    MODELS.mkdir(parents=True,exist_ok=True)
    PRED.mkdir(parents=True,exist_ok=True)
    train_names=freeze['train_executions']
    results=[]
    fit_log=[]
    def combine(names,key): return np.concatenate([all_data[n][key] for n in names])
    for seed in SEEDS:
        fold_x=[]; fold_p0=[]; fold_p1=[]; fold_y=[]
        for k in range(1,len(train_names)):
            fit_names=train_names[:k]; val_name=train_names[k]
            cur=combine(fit_names,'current'); hist=combine(fit_names,'history'); y=combine(fit_names,'y')
            val=all_data[val_name]
            ps=[]
            for state in [0,1]:
                tick=time.monotonic()
                x=np.column_stack([cur,hist]) if state else cur
                vx=np.column_stack([val['current'],val['history']]) if state else val['current']
                model=fit_model(x,y,seed)
                joblib.dump(model,MODELS/f's{seed}_fold{k}_state{state}.joblib',compress=3)
                ps.append(predict(model,vx))
                fit_log.append({'seed':seed,'fold':k,'state':state,'train':fit_names,'validation':val_name,'train_rows':len(y),'seconds':time.monotonic()-tick})
                save(ROOT/'FIT_LOG.json',fit_log)
                print('FIT',seed,k,state,len(y),round(fit_log[-1]['seconds'],1),flush=True)
            fold_x.append(val['current']); fold_p0.append(ps[0]); fold_p1.append(ps[1]); fold_y.append(val['y'])
        oof_x=np.concatenate(fold_x); p0=np.concatenate(fold_p0); p1=np.concatenate(fold_p1); oy=np.concatenate(fold_y)
        sx=np.column_stack([oof_x,p0])
        targets={'entropy':entropy(p0)-entropy(p1),
                 'harm':np.array([1,1,4])[oy]*((p0.argmax(axis=1)!=oy).astype(float)-(p1.argmax(axis=1)!=oy))}
        selectors={}
        for policy,target in targets.items():
            selectors[policy]=regressor(seed).fit(sx,target)
            joblib.dump(selectors[policy],MODELS/f's{seed}_{policy}.joblib',compress=3)
        np.savez_compressed(PRED/f's{seed}_development_oof.npz',y=oy,p0=p0,p1=p1,
                            entropy_target=targets['entropy'],harm_target=targets['harm'])
        cur=combine(train_names,'current'); hist=combine(train_names,'history'); y=combine(train_names,'y')
        final_models=[]
        for state in [0,1]:
            tick=time.monotonic()
            model=fit_model(np.column_stack([cur,hist]) if state else cur,y,seed)
            final_models.append(model)
            joblib.dump(model,MODELS/f's{seed}_final_state{state}.joblib',compress=3)
            fit_log.append({'seed':seed,'fold':'final','state':state,'train':train_names,'train_rows':len(y),'seconds':time.monotonic()-tick})
            save(ROOT/'FIT_LOG.json',fit_log)
            print('FINAL FIT',seed,state,len(y),round(fit_log[-1]['seconds'],1),flush=True)
        pooled={policy:[] for policy in ['none','always_history','entropy','harm']}
        for name in freeze['test_executions']:
            d=all_data[name]; ey=d['y']
            ep0=predict(final_models[0],d['current'])
            ep1=predict(final_models[1],np.column_stack([d['current'],d['history']]))
            selector_x=np.column_stack([d['current'],ep0])
            gains={pol:sel.predict(selector_x) for pol,sel in selectors.items()}
            output={'y':ey,'p0':ep0,'p1':ep1,'key':d['key'],'entropy_gain':gains['entropy'],'harm_gain':gains['harm']}
            for policy in pooled:
                action=(np.zeros(len(ey),bool) if policy=='none' else np.ones(len(ey),bool) if policy=='always_history' else gains[policy]>0)
                prob=np.where(action[:,None],ep1,ep0)
                output[policy+'_action']=action
                output[policy+'_p']=prob
                results.append({'seed':seed,'execution':name,'policy':policy,**metrics(ey,prob,action)})
                pooled[policy].append((ey,prob,action))
            np.savez_compressed(PRED/f's{seed}_{name}.npz',**output)
        for policy,sets in pooled.items():
            results.append({'seed':seed,'execution':'pooled','policy':policy,**metrics(*[np.concatenate([v[i] for v in sets]) for i in range(3)])})
        save(ROOT/'RESULTS.json',results)
        print('SEED COMPLETE',seed,flush=True)
    files=[p for folder in (MODELS,PRED) for p in folder.glob('*')]
    save(ROOT/'ARTIFACTS.json',[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files])
    flat=[{k:v for k,v in r.items() if k not in ['per_class','confusion_matrix']} for r in results]
    pd.DataFrame(flat).to_csv(ROOT/'RESULTS.csv',index=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['prepare','run'])
    action=parser.parse_args().action
    prepare() if action=='prepare' else run()
