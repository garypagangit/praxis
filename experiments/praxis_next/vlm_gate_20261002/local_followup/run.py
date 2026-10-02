"""Four frozen local fits on chart-equivalent aggregates, with common-unit evaluation."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='2'
import argparse,hashlib,json,time,platform
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
HERE=Path(__file__).resolve().parent
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
META=Path('C:/w/px094_soc_workload_20261001/UNRAVELED_meta.npz')
OUT=Path('C:/w/px098_local_followup_20261002')
METRICS=['bytes_out','bytes_in','flows','dns_flows','peers']
VIEWS=['host_hour','host_5min','peer_service_hour','peer_service_5min']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def freeze():
    assert not (HERE/'FREEZE.json').exists()
    save(HERE/'FREEZE.json',{'status':'FROZEN_BEFORE_FITS','files':{str(p):sha(p) for p in [DATA,META,HERE/'PROTOCOL.json',Path(__file__)]},
        'python':platform.python_version(),'numpy':np.__version__,'lightgbm':lgb.__version__,'fit_limit':4})
def build():
    d=dict(np.load(DATA));n=len(d['y']);names=list(d['feature_names']);x=d['current']
    get=lambda name:x[:,names.index(name)]
    flags=np.column_stack([get('dst_dns_service'),get('dst_web_service'),get('dst_remote_admin_service')])
    assert (flags.sum(1)<=1).all()
    service=(flags*np.array([1,2,3])).sum(1).astype(int)
    base=np.zeros(n,bool);full=np.zeros(n,bool);test=d['split']==2;m=dict(np.load(META))
    assert np.array_equal(m['key'],d['group_sha256'][test]) and np.array_equal(m['y'],d['y'][test])
    base[test]=m['base_OR'];full[test]=m['full_OR']
    frames=[]
    for reverse in [False,True]:
        frames.append(pd.DataFrame({'part':d['split'],'capture':d['capture'],'host':d['dst' if reverse else 'src'],
            'peer':d['src' if reverse else 'dst'],'service':service,'protocol':get('protocol').astype(int),
            'bin':np.floor(d['end']/300000).astype(np.int64),'bytes_out':get('dst2src_bytes' if reverse else 'src2dst_bytes'),
            'bytes_in':get('src2dst_bytes' if reverse else 'dst2src_bytes'),'flows':1,'dns_flows':get('dst_dns_service'),
            'exfil':(d['y']==3)&(not reverse),'benign':d['y']==0,'base':base&(not reverse),'full':full&(not reverse)}))
    e=pd.concat(frames,ignore_index=True)
    e=e.drop(index=np.flatnonzero(d['src']==d['dst'])+n).reset_index(drop=True)
    e['hour']=e['bin']//12
    e['pid']=e.groupby(['part','capture','host','hour'],sort=True).ngroup()
    parent=e.groupby('pid',sort=True).agg(part=('part','first'),capture=('capture','first'),host=('host','first'),hour=('hour','first'),
        exfil=('exfil','max'),benign=('benign','min'),base=('base','max'),full=('full','max'))
    assert np.array_equal(parent.index,np.arange(len(parent)))
    prior=json.loads(Path('C:/w/vlm_pilots_20261002/private_truth.json').read_text())
    for r in parent[parent.part==2].itertuples():
        ident=hashlib.sha256(f'PX098:{r.capture}:{r.host}:{r.hour}'.encode()).hexdigest();v=prior[ident]
        assert all(bool(getattr(r,k))==v[k] for k in ['exfil','benign','base','full'])
    assert int((parent.part==2).sum())==len(prior)
    return d,e,parent,base,full
def aggregate(e,view):
    fine=view.endswith('5min');peer=view.startswith('peer')
    cols=['pid']+(['bin'] if fine else [])+(['peer','service','protocol'] if peer else [])
    gid=e.groupby(cols,sort=True).ngroup().to_numpy();g=e.assign(gid=gid,pos=0 if fine else e['bin']%12)
    labels=g.groupby('gid',sort=True).agg(pid=('pid','first'),exfil=('exfil','max'),benign=('benign','min'),bin=('bin','first'))
    a=g.groupby(['gid','pos'],sort=True).agg(bytes_out=('bytes_out','sum'),bytes_in=('bytes_in','sum'),flows=('flows','sum'),dns_flows=('dns_flows','sum'),peers=('peer','nunique'))
    raw=np.zeros((len(labels),1 if fine else 12,5),dtype=np.float64)
    raw[a.index.get_level_values(0),a.index.get_level_values(1),:]=a[METRICS].to_numpy()
    assert np.isfinite(raw).all() and (raw>=0).all()
    end=(labels['bin'].to_numpy()+1)*300000 if fine else (labels['bin'].to_numpy()//12+1)*3600000
    return raw,labels,gid,end
def max_parent(scores,pid,n):
    result=np.full(n,-np.inf);np.maximum.at(result,pid,scores);return result
def threshold(scores,benign):
    v=np.sort(scores[benign])[::-1];assert len(v)>0 and np.isfinite(v).all()
    allowed=int(np.floor(.01*len(v)))
    cut=float(np.nextafter(v[allowed],np.inf));assert int((v>=cut).sum())<=allowed
    return cut,allowed
def main():
    f=json.loads((HERE/'FREEZE.json').read_text())
    for p,h in f['files'].items():assert sha(p)==h,p
    assert lgb.__version__==f['lightgbm'] and not (HERE/'RESULTS.json').exists()
    OUT.mkdir(exist_ok=False);started=time.monotonic();d,e,parent,base,full=build();parent.to_pickle(OUT/'parents.pkl')
    results=[];diagnostics=[];np.savez_compressed(OUT/'flow_identity.npz',key=d['group_sha256'],split=d['split'])
    for view in VIEWS:
        t=time.monotonic();raw,labels,gid,end=aggregate(e,view);pid=labels.pid.to_numpy();part=parent.part.to_numpy()[pid]
        positive=labels.exfil.to_numpy(dtype=bool);benign=labels.benign.to_numpy(dtype=bool)
        train=(part==0)&(positive|benign);assert positive[train].any() and benign[train].any()
        x=np.log1p(raw.reshape(len(raw),-1));weights=1/np.bincount(pid)[pid]
        model=lgb.LGBMClassifier(n_estimators=150,learning_rate=.05,num_leaves=15,max_depth=5,min_child_samples=20,
            class_weight='balanced',random_state=9802,n_jobs=2,verbosity=-1,deterministic=True,force_col_wise=True)
        model.fit(x[train],positive[train].astype(int),sample_weight=weights[train])
        model.booster_.save_model(str(OUT/(view+'.txt')))
        scores=model.predict_proba(x)[:,1];parent_scores=max_parent(scores,pid,len(parent))
        cal=(parent.part.to_numpy()==1)&parent.benign.to_numpy(dtype=bool);cut,allowed=threshold(parent_scores,cal)
        warn=scores>=cut;pw=parent_scores>=cut;test=parent.part.to_numpy()==2
        ex=test&parent.exfil.to_numpy(dtype=bool);bn=test&parent.benign.to_numpy(dtype=bool)
        row={'view':view,'groups':len(raw),'features':x.shape[1],'train_groups':int(train.sum()),'train_exfil_groups':int(positive[train].sum()),
            'calibration_exfil_host_hours':int(((parent.part==1)&parent.exfil).sum()),'calibration_benign_host_hours':int(cal.sum()),
            'calibration_allowed_false_alerts':allowed,'calibration_false_alerts':int((pw&cal).sum()),'threshold':cut,
            'test_host_hours':int(test.sum()),'test_exfil_host_hours':int(ex.sum()),'test_benign_host_hours':int(bn.sum()),
            'model_exfil_host_hours_warned':int((pw&ex).sum()),'model_benign_alerts':int((pw&bn).sum()),'model_benign_fpr':float((pw&bn).sum()/bn.sum())}
        for gate in ['base','full']:
            old=parent[gate].to_numpy(dtype=bool);combined=old|pw
            assert ((combined&test)|( ~test) | (~old)).all()
            addex=int((ex&pw&~old).sum());addben=int((bn&pw&~old).sum())
            row[gate]={'exfil_before':int((ex&old).sum()),'exfil_after':int((ex&combined).sum()),'added_exfil':addex,
                'benign_before':int((bn&old).sum()),'added_benign':addben,'added_benign_fpr':float(addben/bn.sum()),
                'added_all_cases':int((test&pw&~old).sum()),'passes_exploratory_screen':bool(addex>0 and addben/bn.sum()<=.01)}
        flowgid=gid[:len(d['y'])];miss=np.flatnonzero((d['split']==2)&(d['y']==3)&~full)
        all_miss=(d['split']==2)&(d['y']==3)&~full
        misses_per_group=np.bincount(flowgid[all_miss],weights=d['current'][all_miss,list(d['feature_names']).index('src2dst_bytes')],minlength=len(raw))
        shares=[];delays=[]
        for i in miss:
            j=flowgid[i];total=raw[j,:,0].sum();share=float(misses_per_group[j]/total) if total>0 else None
            if share is not None:shares.append(share)
            recovered=bool(warn[j]);delay=float((end[j]-d['end'][i])/1000);assert delay>0
            if recovered:delays.append(delay)
            diagnostics.append({'view':view,'flow_index':int(i),'group':int(j),'missed_flow_byte_share':share,'group_warned':recovered,'delay_from_flow_end_seconds':delay})
        row['full_gate_missed_flows']=len(miss);row['missed_flows_warned_by_own_group']=len(delays)
        row['recovered_flow_delay_median_seconds']=float(np.median(delays)) if delays else None
        row['missed_byte_share_median']=float(np.median(shares)) if shares else None
        # Exact duplicate feature vectors with opposing labels in test groups.
        look={}
        for i in np.flatnonzero((part==2)&(positive|benign)):
            key=hashlib.sha256(raw[i].tobytes()).hexdigest();look.setdefault(key,[0,0])[int(positive[i])]+=1
        conflicts=[v for v in look.values() if all(v)]
        row['test_exact_feature_conflicting_patterns']=len(conflicts)
        row['test_exfil_groups_sharing_exact_features_with_benign']=sum(v[1] for v in conflicts)
        row['seconds']=time.monotonic()-t
        np.savez_compressed(OUT/(view+'.npz'),raw=raw,pid=pid,positive=positive,benign=benign,part=part,scores=scores,
            group_end=end,flowgid=flowgid,parent_scores=parent_scores,threshold=cut)
        results.append(row);print(json.dumps(row),flush=True)
    save(HERE/'RESULTS.json',{'experiment':'PX-098','phase':'local_followup','fits':4,'aws_calls':0,'seconds':time.monotonic()-started,'rows':results})
    save(HERE/'FLOW_DIAGNOSTICS.json',diagnostics)
    save(HERE/'ARTIFACTS.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file()})
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run']);a=ap.parse_args()
    freeze() if a.action=='freeze' else main()
