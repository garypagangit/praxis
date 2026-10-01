import argparse,hashlib,importlib.util,json,sys,heapq
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px094_soc_workload_20261001');PREV=HERE.parent/'heterogeneous_gate_20260930';AIT=Path('C:/w/campaign_validation_20260928');AE=HERE.parent/'campaign_validation_20260928/evidence';DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
ARMS={'base_mean':('base3','MEAN'),'base_OR':('base3','OR'),'plus_current_OR':('plus_current','OR'),'full_OR':('A6_full','OR')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(p,obj):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def selected():
    import gzip
    rows=json.loads(gzip.decompress((PREV/'RESULTS.json.gz').read_bytes()))
    return {ex:{a:next(r for r in rows if r['execution']==ex and r['condition']=='clean' and r['budget']==2 and r['set']==s and r['aggregator']==agg) for a,(s,agg) in ARMS.items()} for ex in ['UNRAVELED','wilson','harrison']}
def freeze():
    assert not (HERE/'FREEZE.json').exists();paths=[DATA,PREV/'RESULTS.json.gz',PREV/'AUDIT.json',AE/'validate.py',AE/'acquire_qualify.py',AE/'label_info.txt',AE/'ZENODO_RECORD.json',AE/'FREEZE.json',AE/'ACQUISITION.json']
    for ex,arms in selected().items():
        for a,r in arms.items():p=Path(r['decision_file']);assert sha(p)==r['decision_sha256'];paths.append(p)
    acq={r['file']:r['sha256'] for r in json.loads((AE/'ACQUISITION.json').read_text())};af=json.loads((AE/'FREEZE.json').read_text())
    for ex in ['wilson','harrison']:
        p=AIT/f'ait/{ex}_netflows.zip';assert sha(p)==acq[p.name];paths.append(p)
        p=AIT/f'prepared/{ex}.npz';assert sha(p)==af['prepared_files'][ex];paths.append(p)
    paths+=list(HERE.glob('*.py'))+list(HERE.glob('*.md'));from datetime import datetime,timezone
    save(HERE/'FREEZE.json',{'experiment':'PX-094','utc':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_BEFORE_REPLAY','files':{str(p):sha(p) for p in dict.fromkeys(paths)},'arms':ARMS,'windows_minutes':[5,15,60],'episode_gaps_minutes':[30,60,120],'groupings':['pair','source'],'staff':[1,2,4],'minutes_per_case':[5,15,30],'reference_staff':1,'reference_minutes':15,'measured_analyst_times':False,'qualified_incident_ids':False});OUT.mkdir(exist_ok=True)
def verify():
    for p,h in json.loads((HERE/'FREEZE.json').read_text())['files'].items():assert sha(p)==h,p
def prepare(ex):
    if ex=='UNRAVELED':
        d=dict(np.load(DATA));m=d['split']==2
        meta={'y':d['y'][m],'key':d['group_sha256'][m],'start':d['start'][m]/1000,'end':d['end'][m]/1000,'src':d['src'][m],'dst':d['dst'][m],'block':d['capture'][m].astype(str)};nchecks=3
    else:
        d=dict(np.load(AIT/f'prepared/{ex}.npz'));sys.path.insert(0,str(AE));spec=importlib.util.spec_from_file_location('ait_source_reader',AE/'validate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        raw=mod.read_execution(AIT/f'ait/{ex}_netflows.zip').set_index(['member','source_row'],verify_integrity=True)
        target=pd.MultiIndex.from_arrays([d['member'],d['source_row']]);r=raw.loc[target].reset_index();cols=['udp','cli','srv','cport','sport','start','end','cp','sp','cb','sb']
        keys=pd.util.hash_pandas_object(r[cols],index=False).to_numpy(np.uint64);assert np.array_equal(keys,d['key']);assert np.array_equal(r['label'].map(mod.labels()).to_numpy(),d['y']);assert np.array_equal(r['start'].to_numpy()/1000,d['start']);assert np.array_equal(r['end'].to_numpy()/1000,d['end'])
        meta={'y':d['y'],'key':d['key'],'start':d['start'],'end':d['end'],'src':r['cli'].astype(str).to_numpy(str),'dst':r['srv'].astype(str).to_numpy(str),'block':np.full(len(r),ex)};nchecks=4
    arms=selected()[ex];warn={}
    for a,r in arms.items():
        assert ah(meta['y'])==r['label_hash'] and ah(meta['key'])==r['identity_hash'];warn[a]=np.load(r['decision_file'])[r['aggregator']]>0
    assert np.isfinite(meta['start']).all() and np.isfinite(meta['end']).all() and np.all(meta['end']>=meta['start']);assert not any(pd.isna(meta[k]).any() for k in ['src','dst'])
    path=OUT/f'{ex}_meta.npz';assert not path.exists();np.savez_compressed(path,**meta,**warn)
    return meta,warn,{'execution':ex,'rows':len(meta['y']),'metadata_path':str(path),'metadata_sha256':sha(path),'identity_hash':ah(meta['key']),'label_hash':ah(meta['y']),'source_mapping_checks':nchecks,'incident_ids_available':False}
def episodes(meta,gap):
    y=meta['y'];ids=np.flatnonzero(y==y.max());f=pd.DataFrame({k:meta[k][ids] for k in ['block','src','start','end']});f['row']=ids;f=f.sort_values(['block','src','start','end','row'],kind='stable')
    new=(f['block']!=f['block'].shift())|(f['src']!=f['src'].shift())|(f['start'].diff()>gap*60);ep=new.cumsum().to_numpy()-1;out=np.full(len(y),-1,int);out[f['row'].to_numpy()]=ep
    starts=np.full(int(ep.max())+1,np.inf);ends=starts.copy();np.minimum.at(starts,ep,f['start']);np.minimum.at(ends,ep,f['end']);return out,starts,ends
def groups(meta,window,grouping):
    n=len(meta['y']);bins=np.floor(meta['end']/(window*60)).astype(np.int64);frame=pd.DataFrame({'block':meta['block'],'src':meta['src'],'dst':meta['dst'] if grouping=='pair' else np.full(n,''),'bin':bins})
    uid,unique=pd.factorize(pd.MultiIndex.from_frame(frame),sort=True);release=np.array([(x[-1]+1)*window*60 for x in unique],float);return uid,release
def next_start(t,minutes):
    day=np.floor(t/86400)*86400;op=day+9*3600;close=day+17*3600;t=max(t,op)
    if t+minutes*60>close:t=day+86400+9*3600
    return t
def queue(release,staff,minutes):
    order=np.lexsort((np.arange(len(release)),release));heap=[(-np.inf,i) for i in range(staff)];heapq.heapify(heap);start=np.zeros(len(release));finish=start.copy();worker=np.zeros(len(release),int)
    for i in order:
        free,w=heapq.heappop(heap);s=next_start(max(release[i],free),minutes);start[i]=s;finish[i]=s+minutes*60;worker[i]=w;heapq.heappush(heap,(finish[i],w))
    return start,finish,worker
def first_by_episode(ep,mask,t,n):
    r=np.full(n,np.inf);ids=np.flatnonzero(mask&(ep>=0));np.minimum.at(r,ep[ids],t[ids]);return r
def main():
    verify();assert not (HERE/'RESULTS.json').exists();results=[];qrows=[];prep=[]
    for ex in ['UNRAVELED','wilson','harrison']:
        m,arms,receipt=prepare(ex);prep.append(receipt);y=m['y'];epinfo={g:episodes(m,g) for g in [30,60,120]}
        epbase={g:first_by_episode(v[0],arms['base_OR'],m['end'],len(v[1])) for g,v in epinfo.items()}
        for window in [5,15,60]:
            for grouping in ['pair','source']:
                uid,release=groups(m,window,grouping);ng=len(release);horizon=float(release.max());baseids=np.unique(uid[arms['base_OR']])
                for arm,w in arms.items():
                    count=np.bincount(uid[w],minlength=ng);attack=np.bincount(uid[w&(y>0)],minlength=ng);exfil=np.bincount(uid[w&(y==y.max())],minlength=ng);all_exfil=np.bincount(uid[y==y.max()],minlength=ng);ci=np.flatnonzero(count);mapping=np.full(ng,-1,int);mapping[ci]=np.arange(len(ci));rowcase=np.where(w,mapping[uid],-1)
                    if arm in ['plus_current_OR','full_OR']:assert np.all(w[arms['base_OR']]) and set(baseids)<=set(ci)
                    cell=f'{ex}_{window}_{grouping}_{arm}';path=OUT/(cell+'_cases.npz');np.savez_compressed(path,uid=uid,rowcase=rowcase,case_ids=ci,release=release[ci],warning_count=count[ci],attack_warning_count=attack[ci],exfil_warning_count=exfil[ci])
                    stats={'cell':cell,'execution':ex,'window_minutes':window,'grouping':grouping,'arm':arm,'warning_flows':int(w.sum()),'benign_warning_flows':int((w&(y==0)).sum()),'attack_warning_flows':int((w&(y>0)).sum()),'cases':len(ci),'benign_only_warning_cases':int((attack[ci]==0).sum()),'attack_warning_cases':int((attack[ci]>0).sum()),'exfil_warning_cases':int((exfil[ci]>0).sum()),'benign_warning_cases_with_unwarned_exfil':int(((attack[ci]==0)&(all_exfil[ci]>0)).sum()),'additional_cases_vs_base':len(ci)-len(baseids),'horizon':horizon,'cases_file':str(path),'cases_sha256':sha(path)}
                    for gap,(ep,starts,ends) in epinfo.items():
                        first=first_by_episode(ep,w,m['end'],len(starts));base=epbase[gap];caught=np.isfinite(first);both=caught&np.isfinite(base);new=int((caught&~np.isfinite(base)).sum());lost=int((~caught&np.isfinite(base)).sum());delay=first[caught]-ends[caught]
                        if arm in ['plus_current_OR','full_OR']:assert lost==0
                        blocks=np.unique(m['block'][y==y.max()]);caughtblocks=sum(bool(np.any(w&(y==y.max())&(m['block']==b))) for b in blocks)
                        results.append({**stats,'episode_gap_minutes':gap,'episodes':len(starts),'episodes_warned':int(caught.sum()),'episode_warning_recall':float(caught.mean()) if len(caught) else None,'new_episodes_vs_base':new,'lost_episodes_vs_base':lost,'earlier_episodes_vs_base':int((first[both]<base[both]).sum()),'warning_delay_from_earliest_completed_flow_median_min':float(np.median(delay)/60) if len(delay) else None,'additional_cases_per_new_episode':stats['additional_cases_vs_base']/new if new else None,'exfil_blocks':len(blocks),'exfil_blocks_warned':caughtblocks})
                    for staff in [1,2,4]:
                        for minutes in [5,15,30]:
                            start,finish,worker=queue(release[ci],staff,minutes);qp=OUT/(cell+f'_a{staff}_m{minutes}.npz');np.savez_compressed(qp,start=start,finish=finish,worker=worker);wait=start-release[ci];bygap={}
                            for gap,(ep,starts,ends) in epinfo.items():
                                times=np.full(len(y),np.inf);times[w]=finish[rowcase[w]];served=first_by_episode(ep,w,times,len(starts));bygap[str(gap)]={'episodes':len(starts),'served_by_horizon':int((served<=horizon).sum()),'served_within_60min':int((served-ends<=3600).sum()),'served_within_240min':int((served-ends<=14400).sum())}
                            qrows.append({**stats,'staff':staff,'minutes_per_case':minutes,'analyst_hours':len(ci)*minutes/60,'served_by_horizon':int((finish<=horizon).sum()),'unresolved_by_horizon':int((finish>horizon).sum()),'wait_median_hours':float(np.median(wait)/3600) if len(wait) else None,'wait_p95_hours':float(np.quantile(wait,.95)/3600) if len(wait) else None,'clearance_after_horizon_hours':float(max(0,finish.max()-horizon)/3600) if len(finish) else 0,'episode_review_slots':bygap,'queue_file':str(qp),'queue_sha256':sha(qp)})
                    print('DONE',cell,flush=True)
        print('SOURCE COMPLETE',ex,flush=True)
    save(HERE/'PREPARATION.json',prep);save(HERE/'RESULTS.json',results);save(HERE/'QUEUE_RESULTS.json',qrows);print('COMPLETE',len(results),len(qrows),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);a=p.parse_args().action
    if a=='freeze':freeze()
    else:main()
