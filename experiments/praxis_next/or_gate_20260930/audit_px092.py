"""Independent raw-probability/count audit. Does not import replay or common."""
import functools,hashlib,json,itertools,warnings
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent;PRIVATE=Path('C:/w/px092_or_gate_20260930')
OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081');AIT=Path('C:/w/campaign_validation_20260928')
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
count=0
def ck(ok,label):
    global count
    if not ok:raise AssertionError(label)
    count+=1
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def eq(a,b,label):
    if isinstance(b,dict):
        for k,v in b.items():eq(a[k],v,label+'.'+k)
    elif isinstance(b,float):ck(a is not None and abs(a-b)<1e-10,label)
    else:ck(a==b,label)
@functools.lru_cache(maxsize=4)
def src(s,c):return dict(np.load(OLD/f'seed_{s}/{c}_inputs.npz'))
@functools.lru_cache(maxsize=6)
def ait(s,e):return dict(np.load(AIT/f'predictions/s{s}_{e}.npz'))
@functools.lru_cache(maxsize=7)
def new(s):return np.load(PRIVATE/f'roles_{s}.npy')
def vector(member,cond,budget,ex):
    s,e=member['seed'],member['expert']
    if ex!='UNRAVELED':
        ds=[ait(s,x) for x in (['wilson','harrison'] if ex=='pooled' else [ex])]
        p=np.concatenate([d['p0' if e=='current' else 'p1'] for d in ds]);return p,np.full(len(p),0 if e=='current' else 2)
    shared=src(8101,cond);p0=src(s,cond)['probabilities'][0] if s<=8103 else shared['probabilities'][0];n=len(p0)
    if e=='current':return p0,np.zeros(n)
    if e=='all':return src(s,cond)['probabilities'][3],np.full(n,3)
    ch={'roles':0,'history':1}[e];price=1 if ch==0 else 2
    p=(new(s) if s>8103 else src(s,cond)['probabilities'][1 if ch==0 else 2]).copy()
    success=(budget>=price)&shared['available'][:,ch]&(shared['delays'][:,ch]<=1.0000001)
    p[~success]=p0[~success];return p,np.full(n,price if budget>=price else 0)
def stats(y,pred,k):
    c=np.zeros((k,k),int);np.add.at(c,(y,pred),1);n=c.sum(1);q=c.sum(0)
    out={'n':len(y),'confusion':c.tolist(),'macro_f1':sum((2*c[i,i]/(n[i]+q[i]) if n[i]+q[i] else 0) for i in range(k))/k,'false_alerts':int(c[0,1:].sum()),'benign_fpr':float(c[0,1:].sum()/n[0]) if n[0] else None}
    names=['other_attack','movement','exfiltration'] if k==4 else ['other_attack','exfiltration']
    for i,name in enumerate(names,1):out[name]={'support':int(n[i]),'missed':int(c[i,0]),'warning_recall':float((n[i]-c[i,0])/n[i]) if n[i] else None,'exact_recall':float(c[i,i]/n[i]) if n[i] else None}
    return out
def refs(cond,budget,ex):
    out={}
    for s in range(8101,8104):
        if ex!='UNRAVELED':
            ds=[ait(s,e) for e in (['wilson','harrison'] if ex=='pooled' else [ex])]
            for pol in ['always_history','entropy']:out[f'{pol}_{s}']=np.concatenate([d[pol+'_p'].argmax(1) for d in ds])
            continue
        inp=src(s,cond);env=src(8101,cond);n=len(env['available']);ix=np.arange(n)
        for pol in ['entropy','harm']:
            state=np.zeros(n,int);attempt=np.zeros((n,2),bool);spent=np.zeros(n);elapsed=np.zeros(n)
            for step in range(2):
                gains=inp[pol+'_gains'][state,ix].astype(float);gains*=([.8,.65] if cond=='delayed_unavailable' else [1,1]);gains/=[1,2]
                legal=(~attempt)&(spent[:,None]+[1,2]<=budget)&(elapsed[:,None]+[.25,.75]<=1.0000001)
                gains[~legal]=-np.inf;chosen=gains.argmax(1);take=np.isfinite(gains[ix,chosen])&(gains[ix,chosen]>0)
                rr=ix[take];cc=chosen[take];attempt[rr,cc]=True;spent[rr]+=cc+1;elapsed[rr]+=env['delays'][rr,cc]
                good=env['available'][rr,cc]&(elapsed[rr]<=1.0000001);state[rr[good]]|=1<<cc[good]
            out[f'{pol}_{s}']=inp['probabilities'][state,ix].argmax(1)
    return out
def main():
    frozen=json.loads((HERE/'FREEZE.json').read_text());import lightgbm,joblib
    ck(lightgbm.__version__==frozen['lightgbm_version'],'LightGBM version')
    for p,h in frozen['files'].items():ck(sha(p)==h,'freeze '+p)
    data=dict(np.load(DATA));uid=dict(np.load(OLD/'evaluation_identity.npz'));ix=np.flatnonzero(data['split']==2)
    ck(np.array_equal(uid['y'],data['y'][ix]),'UNR labels');ck(np.array_equal(uid['event_hash'],data['group_sha256'][ix]),'UNR identities')
    oldmanifest=json.loads((OLD/'ARTIFACT_HASHES.json').read_text())
    for p,h in frozen['files'].items():
        p=Path(p)
        if p.is_relative_to(OLD) and str(p.relative_to(OLD)) in oldmanifest:ck(sha(p)==oldmanifest[str(p.relative_to(OLD))],'PX081 manifest '+str(p))
    ae=HERE.parent/'campaign_validation_20260928/evidence';aman={a['path']:a['sha256'] for a in json.loads((ae/'ARTIFACTS.json').read_text())};af=json.loads((ae/'FREEZE.json').read_text())
    for ex in ['wilson','harrison']:
        prep=dict(np.load(AIT/f'prepared/{ex}.npz'));ck(sha(AIT/f'prepared/{ex}.npz')==af['prepared_files'][ex],'AIT preparation manifest')
        for s in range(8101,8104):
            d=ait(s,ex);ck(sha(AIT/f'predictions/s{s}_{ex}.npz')==aman[str(AIT/f'predictions/s{s}_{ex}.npz')],'AIT prediction manifest')
            ck(np.array_equal(d['y'],prep['y']),'AIT labels');ck(np.array_equal(d['key'],prep['key']),'AIT identity')
    fits=json.loads((HERE/'partB/FIT_LOG.json').read_text());ck(fits['completed_fits']==7,'seven fits');ck([f['seed'] for f in fits['fits']]==list(range(8104,8111)),'fit seed membership')
    train=np.flatnonzero(data['split']==0);x=np.column_stack([data['current'][ix],data['roles'][ix]]).astype(np.float32)
    for f in fits['fits']:
        s=f['seed'];rng=np.random.default_rng(s);selected=[]
        for cls,cap in enumerate([12000,4000,4000,4000]):
            pool=train[data['y'][train]==cls];selected.extend(rng.choice(pool,min(cap,len(pool)),replace=False))
        ids=np.sort(np.array(selected,dtype=np.int64));ck(np.array_equal(ids,np.load(PRIVATE/f'train_{s}.npy')),'fit selection')
        ck(ah(ids)==f['training_indices_sha256'],'fit index hash');ck(ah(data['group_sha256'][ids])==f['training_events_sha256'],'fit events hash')
        ck(not np.intersect1d(ids,ix).size,'fit/test disjoint');ck(np.max(data['end'][ids])<np.min(data['start'][data['split']==1]),'fit before calibration')
        ck(sha(PRIVATE/f'roles_{s}.joblib')==f['model_sha256'],'model hash');ck(sha(PRIVATE/f'roles_{s}.npy')==f['probabilities_sha256'],'new probability hash')
        model=joblib.load(PRIVATE/f'roles_{s}.joblib')
        with warnings.catch_warnings():warnings.simplefilter('ignore');pred=model.predict_proba(x).astype(np.float32)
        ck(np.array_equal(pred,new(s)),'full new model probability reproduction')
        ck(f['class_counts']==np.bincount(data['y'][ids],minlength=4).tolist(),'fit counts')
    del data,x
    cells=0;rows_n=0;triple_sets=[];inventory=[]
    for part,expected in [('partA',45),('partB',174),('partC',9)]:
        rows=json.loads((HERE/part/'GROUPS.json').read_text());groups={}
        for r in rows:groups.setdefault(r['cell'],[]).append(r)
        ck(len(groups)==expected,part+' cell count')
        for name,rs in groups.items():
            r=rs[0];cells+=1;rows_n+=len(rs);ck({q['aggregator'] for q in rs}=={'OR','MEAN','best_single'},'aggregator membership')
            ex=r['execution'];cond=r['condition'];b=r['budget'];members=r['members'];k=4 if ex=='UNRAVELED' else 3
            if ex=='UNRAVELED':y,key=uid['y'],uid['event_hash']
            else:
                ds=[ait(8101,e) for e in (['wilson','harrison'] if ex=='pooled' else [ex])];y=np.concatenate([d['y'] for d in ds]);key=np.concatenate([d['key'] for d in ds])
            ck(ah(y)==r['label_hash'],'cell labels');ck(ah(key)==r['identity_hash'],'cell identity')
            if part=='partB':
                ss=[m['seed'] for m in members];ck(all(m['expert']=='roles' for m in members),'B expert')
                if r['subset_sensitivity']:triple_sets.append(tuple(ss));ck(len(ss)==3 and sorted(ss)==ss,'triple membership')
                else:ck(ss==list(range(8101,8101+len(ss))) and len(ss) in [1,2,3,5,7,10],'nested membership')
            vals=[vector(m,cond,b,ex) for m in members];ps=[v[0].astype(np.float64) for v in vals]
            singles=[p.argmax(1) for p in ps];warn=np.logical_or.reduce([p>0 for p in singles]);stage_sum=np.zeros((len(y),k-1))
            for p,sp in zip(ps,singles):stage_sum[sp>0]+=p[sp>0,1:]
            op=np.zeros(len(y),np.int8);op[warn]=1+stage_sum[warn].argmax(1);mp=(sum(ps)/len(ps)).argmax(1)
            sm=[stats(y,p,k) for p in singles];best=min(range(len(sm)),key=lambda i:(sm[i]['exfiltration']['missed'],sm[i]['false_alerts'],i));fa_sum=sum(m['false_alerts'] for m in sm)
            expected_preds={'OR':op,'MEAN':mp,'best_single':singles[best]};spend=np.maximum.reduce([v[1] for v in vals]);saved=dict(np.load(r['decisions_file']))
            ck(sha(r['decisions_file'])==r['decisions_sha256'],'decision hash');ck(np.array_equal(spend,saved['spent']),'per-row cost')
            if r['reference_only']:ck(all(m['expert']=='all' for m in members) and np.all(spend==3) and r['availability_bypassed'],'declared reference cost exception')
            else:ck(np.all(spend<=b),'per-row budget')
            om=stats(y,op,k)
            for smm in sm:
                for stage in (['other_attack','movement','exfiltration'] if k==4 else ['other_attack','exfiltration']):ck(om[stage]['missed']<=smm[stage]['missed'],'H1a '+name+' '+stage)
            ck(om['false_alerts']<=fa_sum,'H1b '+name)
            rr=refs(cond,b,ex)
            for row in rs:
                pred=expected_preds[row['aggregator']];ck(np.array_equal(pred,saved[row['aggregator']]),'decision equality '+name)
                eq(row,stats(y,pred,k),'metrics '+name);eq(row['mean_evidence_cost'],float(spend.mean()),'mean cost');eq(row['max_evidence_cost'],float(spend.max()),'max cost')
                eq(row['overlap_ratio'],om['false_alerts']/fa_sum if fa_sum else None,'overlap');eq(row['sum_single_false_alerts'],fa_sum,'FA sum')
                eq(row['best_single_exfiltration_warning_recall'],sm[best]['exfiltration']['warning_recall'],'best single recall');eq(row['best_single_member'],members[best],'best member')
                ck(len(row['single_metrics'])==len(sm),'single count')
                for reported,actual in zip(row['single_metrics'],sm):eq(reported,actual,'single metrics')
                for ref,rp in rr.items():
                    rec=row['recovered_against'][ref];ck(rec['recovered']==int(((y>0)&(pred>0)&(rp==0)).sum()),'recovered count');ck(rec['lost']==int(((y>0)&(pred==0)&(rp>0)).sum()),'lost count');eq(rec['reference_metrics'],stats(y,rp,k),'reference metric')
            inventory.append({'cell':name,'part':part,'path':r['decisions_file'],'sha256':r['decisions_sha256'],'rows':len(y)})
            if cells%20==0:print('AUDIT',cells,'cells',count,'checks',flush=True)
        print('AUDITED',part,flush=True)
    ck(set(triple_sets)==set(itertools.combinations(range(8101,8111),3)) and len(triple_sets)==120,'all 120 unique triples')
    result={'status':'PASS','checks':count,'cells':cells,'result_rows':rows_n,'new_models_fully_repredicted':7,'imports_replay_module':False,'H1':'SUPPORTED_BY_CONSTRUCTION','failures':[],'decision_artifacts':inventory}
    (HERE/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('AUDIT PASS',count,flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        (HERE/'AUDIT_FAILURE.json').write_text(json.dumps({'checks_before_failure':count,'error':repr(e)},indent=2)+'\n');raise
