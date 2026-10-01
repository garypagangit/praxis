"""Independent endpoint, case, episode and queue audit; no runner import."""
import gzip,hashlib,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px094_soc_workload_20261001');DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz');AIT=Path('C:/w/campaign_validation_20260928')
checks=0
def ck(ok,label):
    global checks
    assert ok,label
    checks+=1
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def eq(a,b,label):
    if isinstance(b,float):ck(a is not None and abs(a-b)<1e-8,label)
    else:ck(a==b,label)
def episode(meta,gap):
    y=meta['y'];ids=np.flatnonzero(y==y.max());order=np.lexsort((ids,meta['end'][ids],meta['start'][ids],meta['src'][ids],meta['block'][ids]));ep=np.full(len(y),-1,int);num=-1;prev=None;starts=[];ends=[]
    for i in ids[order]:
        ident=(meta['block'][i],meta['src'][i]);t=meta['start'][i]
        if prev is None or ident!=prev[0] or t-prev[1]>gap*60:num+=1;starts.append(t);ends.append(meta['end'][i])
        ep[i]=num;starts[num]=min(starts[num],t);ends[num]=min(ends[num],meta['end'][i]);prev=(ident,t)
    return ep,np.array(starts),np.array(ends)
def first(ep,mask,t,n):
    out=np.full(n,np.inf)
    for i in np.flatnonzero(mask&(ep>=0)):out[ep[i]]=min(out[ep[i]],t[i])
    return out
def simulate(releases,staff,minutes):
    free=np.full(staff,-np.inf);ss=np.zeros(len(releases));ff=ss.copy();ww=np.zeros(len(releases),int)
    for i in sorted(range(len(releases)),key=lambda j:(releases[j],j)):
        w=int(np.argmin(free));t=max(releases[i],free[w]);day=np.floor(t/86400)
        if t<day*86400+32400:t=day*86400+32400
        if t+minutes*60>day*86400+61200:t=(day+1)*86400+32400
        ss[i]=t;ff[i]=t+minutes*60;ww[i]=w;free[w]=ff[i]
    return ss,ff,ww
def main():
    freeze=json.loads((HERE/'FREEZE.json').read_text())
    for p,h in freeze['files'].items():ck(sha(p)==h,'frozen '+p)
    prior=json.loads(gzip.decompress((HERE.parent/'heterogeneous_gate_20260930/RESULTS.json.gz').read_bytes()));preps=json.loads((HERE/'PREPARATION.json').read_text());rs=json.loads((HERE/'RESULTS.json').read_text());qs=json.loads((HERE/'QUEUE_RESULTS.json').read_text());ck(len(rs)==216 and len(qs)==648,'complete grid')
    index={(r['cell'],r['episode_gap_minutes']):r for r in rs};qindex={(r['cell'],r['staff'],r['minutes_per_case']):r for r in qs}
    for prep in preps:
        ex=prep['execution'];m=dict(np.load(prep['metadata_path']));ck(sha(prep['metadata_path'])==prep['metadata_sha256'],'metadata hash');y=m['y'];n=len(y)
        if ex=='UNRAVELED':
            raw=dict(np.load(DATA));mask=raw['split']==2
            for name,src in [('src','src'),('dst','dst'),('y','y'),('key','group_sha256')]:ck(np.array_equal(m[name],raw[src][mask]),'UNR '+name)
            ck(np.array_equal(m['start'],raw['start'][mask]/1000) and np.array_equal(m['end'],raw['end'][mask]/1000),'UNR time units');ck(np.array_equal(m['block'],raw['capture'][mask].astype(str)),'UNR captures');del raw
        else:
            d=dict(np.load(AIT/f'prepared/{ex}.npz'))
            for name in ['y','key','start','end']:ck(np.array_equal(m[name],d[name]),'AIT '+name)
            with zipfile.ZipFile(AIT/f'ait/{ex}_netflows.zip') as z:
                for member in np.unique(d['member']):
                    udp='udp' in member;cols=['#c_ip:1','s_ip:10'] if udp else ['#15#c_ip:1','s_ip:15']
                    with z.open(member) as f:r=pd.read_csv(f,usecols=cols,dtype=str)
                    ix=np.flatnonzero(d['member']==member);source=d['source_row'][ix]
                    ck(np.array_equal(m['src'][ix],r[cols[0]].to_numpy()[source]),'native client mapping');ck(np.array_equal(m['dst'][ix],r[cols[1]].to_numpy()[source]),'native server mapping')
            ck(np.all(m['block']==ex),'AIT block')
        arms=freeze['arms']
        for arm,(setname,agg) in arms.items():
            r=next(r for r in prior if r['execution']==ex and r['condition']=='clean' and r['budget']==2 and r['set']==setname and r['aggregator']==agg);ck(np.array_equal(m[arm],np.load(r['decision_file'])[agg]>0),'prior warning decisions')
        eps={gap:episode(m,gap) for gap in [30,60,120]};base={gap:first(e,m['base_OR'],m['end'],len(st)) for gap,(e,st,en) in eps.items()}
        for window in [5,15,60]:
            for grouping in ['pair','source']:
                bins=np.floor(m['end']/(window*60)).astype(np.int64);dst=m['dst'] if grouping=='pair' else np.full(n,'')
                tuples=list(zip(m['block'].tolist(),m['src'].tolist(),dst.tolist(),bins.tolist()));unique=sorted(set(tuples));lookup={k:i for i,k in enumerate(unique)};uid=np.fromiter((lookup[k] for k in tuples),dtype=int,count=n);release=np.array([(k[-1]+1)*window*60 for k in unique],float);ng=len(unique);horizon=float(release.max());baseids=np.unique(uid[m['base_OR']]);del tuples,lookup
                ck(np.all(release[uid]>m['end']),'no early batch release')
                for arm in arms:
                    w=m[arm];cell=f'{ex}_{window}_{grouping}_{arm}';r=index[cell,60];p=dict(np.load(r['cases_file']));ck(sha(r['cases_file'])==r['cases_sha256'],'cases hash');ids=np.unique(uid[w]);ck(np.array_equal(p['uid'],uid) and np.array_equal(p['case_ids'],ids),'case grouping')
                    local=np.full(n,-1,int);local[w]=np.searchsorted(ids,uid[w]);ck(np.array_equal(local,p['rowcase']),'row case assignment');ck(np.array_equal(release[ids],p['release']),'case releases')
                    count=np.bincount(local[w],minlength=len(ids));attack=np.bincount(local[w&(y>0)],minlength=len(ids));exfil=np.bincount(local[w&(y==y.max())],minlength=len(ids));all_ex=np.bincount(uid[y==y.max()],minlength=ng)
                    ck(np.array_equal(count,p['warning_count']) and np.array_equal(attack,p['attack_warning_count']) and np.array_equal(exfil,p['exfil_warning_count']),'case count conservation')
                    if arm in ['plus_current_OR','full_OR']:ck(set(baseids)<=set(ids) and np.all(w[m['base_OR']]),'OR superset')
                    stats={'warning_flows':int(w.sum()),'benign_warning_flows':int((w&(y==0)).sum()),'attack_warning_flows':int((w&(y>0)).sum()),'cases':len(ids),'benign_only_warning_cases':int((attack==0).sum()),'attack_warning_cases':int((attack>0).sum()),'exfil_warning_cases':int((exfil>0).sum()),'benign_warning_cases_with_unwarned_exfil':int(((attack==0)&(all_ex[ids]>0)).sum()),'additional_cases_vs_base':len(ids)-len(baseids),'horizon':horizon}
                    for gap,(ep,starts,ends) in eps.items():
                        rr=index[cell,gap]
                        for k,v in stats.items():eq(rr[k],v,k)
                        f=first(ep,w,m['end'],len(starts));caught=np.isfinite(f);both=caught&np.isfinite(base[gap]);new=int((caught&~np.isfinite(base[gap])).sum());lost=int((~caught&np.isfinite(base[gap])).sum());delay=f[caught]-ends[caught]
                        vals={'episodes':len(starts),'episodes_warned':int(caught.sum()),'episode_warning_recall':float(caught.mean()),'new_episodes_vs_base':new,'lost_episodes_vs_base':lost,'earlier_episodes_vs_base':int((f[both]<base[gap][both]).sum()),'warning_delay_from_earliest_completed_flow_median_min':float(np.median(delay)/60) if len(delay) else None,'additional_cases_per_new_episode':stats['additional_cases_vs_base']/new if new else None,'exfil_blocks':len(np.unique(m['block'][y==y.max()])),'exfil_blocks_warned':sum(bool(np.any(w&(y==y.max())&(m['block']==b))) for b in np.unique(m['block'][y==y.max()]))}
                        for k,v in vals.items():eq(rr[k],v,k)
                        if arm in ['plus_current_OR','full_OR']:ck(lost==0,'no lost episodes')
                    for staff in [1,2,4]:
                        for minutes in [5,15,30]:
                            q=qindex[cell,staff,minutes];a=dict(np.load(q['queue_file']));ck(sha(q['queue_file'])==q['queue_sha256'],'queue hash');ss,ff,ww=simulate(release[ids],staff,minutes)
                            for name,v in [('start',ss),('finish',ff),('worker',ww)]:ck(np.array_equal(a[name],v),'independent FIFO '+name)
                            ck(np.all(ss>=release[ids]) and np.all(ff-ss==minutes*60),'service timing')
                            for worker in range(staff):
                                times=np.sort(ss[ww==worker]);ck(np.all(np.diff(times)>=minutes*60),'worker nonoverlap')
                            wait=ss-release[ids];vals={'analyst_hours':len(ids)*minutes/60,'served_by_horizon':int((ff<=horizon).sum()),'unresolved_by_horizon':int((ff>horizon).sum()),'wait_median_hours':float(np.median(wait)/3600) if len(wait) else None,'wait_p95_hours':float(np.quantile(wait,.95)/3600) if len(wait) else None,'clearance_after_horizon_hours':float(max(0,ff.max()-horizon)/3600) if len(ff) else 0}
                            for k,v in vals.items():eq(q[k],v,k)
                            for gap,(ep,starts,ends) in eps.items():
                                times=np.full(n,np.inf);times[w]=ff[local[w]];served=first(ep,w,times,len(starts));vals={'episodes':len(starts),'served_by_horizon':int((served<=horizon).sum()),'served_within_60min':int((served-ends<=3600).sum()),'served_within_240min':int((served-ends<=14400).sum())}
                                ck(q['episode_review_slots'][str(gap)]==vals,'episode review-slot counts')
                print('AUDIT',ex,window,grouping,checks,flush=True)
    result={'status':'PASS','checks':checks,'case_cells':72,'episode_result_rows':216,'queue_scenarios':648,'new_fits':0,'confirmed_incident_ids':False,'measured_analyst_outcomes':False,'failures':[]};(HERE/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except Exception as e:(HERE/'AUDIT_FAILURE.json').write_text(json.dumps({'checks':checks,'error':repr(e)},indent=2));raise
