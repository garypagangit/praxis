import hashlib,json,sys,time,importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
META=Path('C:/w/px094_soc_workload_20261001')
OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
AIT=Path('C:/w/campaign_validation_20260928')
OUT=Path('C:/w/px103_warning_budget_20261003')
EXS=['UNRAVELED','wilson','harrison'];BUDGETS=[1,5,20]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def load(p):return dict(np.load(p,allow_pickle=False))
def freeze():
    assert not (HERE/'FREEZE.json').exists()
    paths=[HERE/'run.py',HERE/'PROTOCOL.md',HERE.parent/'soc_workload_20261001/run.py']
    for ex in EXS:
        paths.append(META/f'{ex}_meta.npz')
        paths.extend([OLD/f'seed_{s}/clean_inputs.npz' if ex=='UNRAVELED' else AIT/f'predictions/s{s}_{ex}.npz' for s in [8101,8102,8103]])
    save(HERE/'FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':{str(p):sha(p) for p in paths},'budgets':BUDGETS,'random_seeds':list(range(10300,10310))})
def prepare(m,p):
    # This function and select receive no ground-truth labels.
    votes=p.argmax(2)>0;base=p.mean(0).argmax(1)>0;orw=votes.any(0);candidate=orw&~base
    margin=(p[:,:,1:].max(2)-p[:,:,0]).max(0)
    frame=pd.DataFrame({k:m[k] for k in ['block','src','dst']});frame['bin']=np.floor(m['end']/900).astype(np.int64)
    gid,unique=pd.factorize(pd.MultiIndex.from_frame(frame),sort=True);ng=len(unique)
    basecase=np.bincount(gid[base],minlength=ng)>0;cc=np.bincount(gid[candidate],minlength=ng)>0
    scores=np.full(ng,-np.inf);np.maximum.at(scores,gid[candidate],margin[candidate])
    first=np.full(ng,np.inf);np.minimum.at(first,gid[candidate],m['end'][candidate])
    cases=pd.DataFrame(list(unique),columns=['block','src','dst','bin']);cases['base']=basecase;cases['candidate']=cc;cases['score']=scores;cases['first']=first;cases['gid']=np.arange(ng)
    return gid,base,orw,candidate,cases
def select(cases,method,budget,seed=10300):
    chosen=set();log=[];last={};rng=np.random.default_rng(seed)
    for (block,binid),batch in cases.groupby(['block','bin'],sort=True):
        release=(int(binid)+1)*900
        for row in batch[batch['base']].itertuples():last[(block,row.src)]=release
        pool=list(batch[batch['candidate']&~batch['base']].itertuples())
        if method=='random':rng.shuffle(pool)
        for _ in range(min(budget,len(pool))):
            def fresh(r):return release-last.get((block,r.src),-np.inf)>3600
            if method=='coverage':pool.sort(key=lambda r:(-int(fresh(r)),-r.score,r.gid))
            elif method=='confidence':pool.sort(key=lambda r:(-r.score,r.gid))
            elif method=='earliest':pool.sort(key=lambda r:(r.first,r.gid))
            r=pool.pop(0);novel=fresh(r);chosen.add(r.gid);last[(block,r.src)]=release
            log.append({'case_id':int(r.gid),'block':str(block),'bin':int(binid),'source':str(r.src),'no_warning_preceding_60min':bool(novel),'margin':float(r.score),'release':release,'reason':'No warning for this source in preceding 60 minutes; then member margin' if method=='coverage' and novel else method+' ordering'})
    return np.array(sorted(chosen),dtype=int),log
def main():
    frozen=json.loads((HERE/'FREEZE.json').read_text())
    for p,h in frozen['files'].items():assert sha(Path(p))==h,p
    assert not (HERE/'RESULTS.json').exists();OUT.mkdir(exist_ok=True)
    spec=importlib.util.spec_from_file_location('episode_defs',HERE.parent/'soc_workload_20261001/run.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    rows=[];audits=[]
    for ex in EXS:
        m=load(META/f'{ex}_meta.npz');pp=[]
        for s in [8101,8102,8103]:
            z=load(OLD/f'seed_{s}/clean_inputs.npz') if ex=='UNRAVELED' else load(AIT/f'predictions/s{s}_{ex}.npz')
            if ex!='UNRAVELED':assert np.array_equal(z['key'],m['key']) and np.array_equal(z['y'],m['y'])
            pp.append(z['probabilities'][1] if ex=='UNRAVELED' else z['p1'])
        p=np.array(pp,dtype=np.float64);features={k:m[k] for k in ['block','src','dst','end']};gid,base,orw,candidate,cases=prepare(features,p)
        assert np.array_equal(base,m['base_mean']) and np.array_equal(orw,m['base_OR'])
        y=m['y'];baseids=set(np.flatnonzero(cases['base']));release=(cases['bin'].to_numpy()+1)*900;eps={g:mod.episodes(m,g) for g in [30,60,120]}
        configs=[('mean',0,0),('OR',0,0)]+[(method,b,seed) for b in BUDGETS for method in ['coverage','confidence','earliest','random'] for seed in (range(10300,10310) if method=='random' else [0])]
        for method,b,seed in configs:
            if method=='mean':chosen=np.array([],int);w=base.copy();log=[]
            elif method=='OR':chosen=np.flatnonzero(cases['candidate']&~cases['base']);w=orw.copy();log=[]
            else:
                chosen,log=select(cases,method,b,seed)
                counts=cases.iloc[chosen].groupby(['block','bin']).size();assert not len(counts) or counts.max()<=b
                # No labels enter selection; verify a separate table copy produces identical decisions.
                c2=cases.copy();c2['unused_shuffled_label']=np.random.default_rng(1).permutation(np.arange(len(cases)))
                repeat,_=select(c2,method,b,seed);assert np.array_equal(chosen,repeat)
                w=base|(candidate&np.isin(gid,np.array(sorted(baseids|set(chosen)))))
            assert np.all(w[base]) and not np.any(w&~orw)
            name=f'{ex}_{method}_b{b}_s{seed}';np.savez_compressed(OUT/(name+'.npz'),warning=w,chosen=chosen)
            if method=='coverage':save(OUT/(name+'_explanations.json'),log)
            attack_counts=np.bincount(gid[w&(y>0)],minlength=len(cases));benigncases=int((attack_counts[chosen]==0).sum())
            for gap,(ep,starts,ends) in eps.items():
                baseline=mod.first_by_episode(ep,base,release[gid],len(starts));first=mod.first_by_episode(ep,w,release[gid],len(starts));caught=np.isfinite(first);new=caught&~np.isfinite(baseline)
                row={'execution':ex,'method':method,'budget_per_bin':b,'seed':seed,'episode_gap_min':gap,'episodes':len(starts),'covered':int(caught.sum()),'new_episodes':int(new.sum()),'additional_cases':len(chosen),'additional_benign_only_cases':benigncases,'new_episodes_per_100_benign_cases':float(100*new.sum()/benigncases) if benigncases else None,'exfil_warned':int((w&(y==y.max())).sum()),'exfil_support':int((y==y.max()).sum()),'benign_warning_flows':int((w&(y==0)).sum()),'median_first_warning_delay_seconds':float(np.median(first[caught]-ends[caught])) if caught.any() else None}
                rows.append(row)
        audits.append({'execution':ex,'rows':len(y),'candidate_flows':int(candidate.sum()),'candidate_new_cases':int((cases['candidate']&~cases['base']).sum()),'alignment':'PASS','budget_and_subset_checks':'PASS','label_independence':'selector accepts no labels; irrelevant-field invariance PASS'})
        print(ex,'complete',flush=True)
    save(HERE/'RESULTS.json',rows);save(HERE/'AUDIT.json',audits)
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else main()
