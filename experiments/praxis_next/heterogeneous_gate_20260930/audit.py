"""Independent PX-093 raw probability/count audit. No runner import."""
import functools,hashlib,json,warnings
from pathlib import Path
import numpy as np,joblib
from threadpoolctl import threadpool_limits
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px093_heterogeneous_20260930');AIT=Path('C:/w/campaign_validation_20260928');OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081');DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
checks=0
def ck(x,msg):
    global checks
    assert x,msg
    checks+=1
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def eq(a,b,msg):
    if isinstance(b,dict):
        for k,v in b.items():eq(a[k],v,msg+'.'+k)
    elif isinstance(b,float):ck(a is not None and abs(a-b)<1e-10,msg)
    else:ck(a==b,msg)
@functools.lru_cache(maxsize=9)
def un(s,c):return dict(np.load(OLD/f'seed_{s}/{c}_inputs.npz'))
@functools.lru_cache(maxsize=6)
def ai(s,e):return dict(np.load(AIT/f'predictions/s{s}_{e}.npz'))
@functools.lru_cache(maxsize=3)
def lr(e):return dict(np.load(OUT/f'lr_{e}.npz'))
def raw(ex,cond,b):
    if ex=='pooled':
        a=raw('wilson',cond,b);z=raw('harrison',cond,b);return {k:np.concatenate([a[0][k],z[0][k]]) for k in a[0]},np.concatenate([a[1],z[1]]),np.concatenate([a[2],z[2]])
    l=lr(ex);y,key=l['y'],l['key'];v={'lr':l['p'].copy()}
    if ex=='UNRAVELED':
        env=un(8101,cond);yes=(b>=1)&env['available'][:,0]&(env['delays'][:,0]<=1.0000001)
        for s in range(8101,8104):
            p=un(s,cond)['probabilities'];a=p[0].copy();a[yes]=p[1,yes];v['b'+str(s)]=a
        v['current']=env['probabilities'][0];v['lr'][~yes]=v['current'][~yes]
    else:
        for s in range(8101,8104):v['b'+str(s)]=ai(s,ex)['p1']
        v['current']=ai(8101,ex)['p0']
    return v,y,key
def metric(y,p,k):
    c=np.zeros((k,k),int);np.add.at(c,(y,p),1);s=c.sum(1);q=c.sum(0);m={'n':len(y),'confusion':c.tolist(),'macro_f1':sum(2*c[i,i]/(s[i]+q[i]) if s[i]+q[i] else 0 for i in range(k))/k,'false_alerts':int(c[0,1:].sum()),'benign_fpr':float(c[0,1:].sum()/s[0])}
    for i,n in enumerate(['other_attack','movement','exfiltration'] if k==4 else ['other_attack','exfiltration'],1):m[n]={'support':int(s[i]),'missed':int(c[i,0]),'warning_recall':float((s[i]-c[i,0])/s[i]) if s[i] else None,'exact_recall':float(c[i,i]/s[i]) if s[i] else None}
    return m
def main():
    frozen=json.loads((HERE/'FREEZE.json').read_text())
    for p,h in frozen['files'].items():ck(sha(p)==h,'frozen '+p)
    fits={dom:json.loads((HERE/f'FIT_{dom}.json').read_text()) for dom in ['UNRAVELED','AIT']};ck(len(list(OUT.glob('*_lr.joblib')))==2,'two fits')
    for dom,fit in fits.items():
        model=joblib.load(OUT/f'{dom}_lr.joblib');ck(sha(OUT/f'{dom}_lr.joblib')==fit['model_sha256'],'model hash');ck(model[-1].C==1 and model[-1].max_iter==500 and model[-1].solver=='lbfgs','LR params')
        if dom=='UNRAVELED':
            data=dict(np.load(DATA));rng=np.random.default_rng(8101);sel=[]
            for cls,cap in enumerate([12000,4000,4000,4000]):
                pool=np.flatnonzero((data['split']==0)&(data['y']==cls));sel.extend(rng.choice(pool,min(cap,len(pool)),replace=False))
            ids=np.sort(np.array(sel,dtype=np.int64));key=data['group_sha256'][ids];y=data['y'][ids];evals=['UNRAVELED']
            ck(np.max(data['end'][ids])<np.min(data['start'][data['split']==1]),'UNR train before cal')
        else:
            ds=[dict(np.load(AIT/f'prepared/{e}.npz')) for e in frozen['training_executions']];key=np.concatenate([d['key'] for d in ds]);y=np.concatenate([d['y'] for d in ds]);ids=np.arange(len(y));evals=['wilson','harrison'];maxend=max(float(d['end'].max()) for d in ds);del ds
        ck(ah(key)==fit['training_identity_hash'],'training identities');ck(ah(y)==fit['training_label_hash'],'training labels');ck(ah(ids)==fit['selected_indices_hash'],'training row indices');ck(np.array_equal(ids,np.load(OUT/f'{dom}_training_indices.npy')),'saved indices');ck(len(y)==fit['training_rows'],'training count');ck(np.bincount(y).tolist()==fit['class_counts'],'class counts')
        for ex in evals:
            if ex=='UNRAVELED':
                mask=data['split']==2;x=np.column_stack([data['current'][mask],data['roles'][mask]]);ey=data['y'][mask];ek=data['group_sha256'][mask];oldid=dict(np.load(OLD/'evaluation_identity.npz'));ck(np.array_equal(oldid['y'],ey) and np.array_equal(oldid['event_hash'],ek),'PX081 identity alignment')
            else:
                d=dict(np.load(AIT/f'prepared/{ex}.npz'));x=np.column_stack([d['current'],d['history']]);ey,ek=d['y'],d['key'];ck(maxend<d['start'].min(),'AIT chronological split')
                for s in range(8101,8104):ck(np.array_equal(ai(s,ex)['y'],ey) and np.array_equal(ai(s,ex)['key'],ek),'AIT native identity alignment')
            ck(not np.intersect1d(key,ek).size,'train test identity disjoint')
            with threadpool_limits(limits=2),warnings.catch_warnings():warnings.simplefilter('ignore');p=model.predict_proba(x).astype(np.float32)
            d=lr(ex);ck(np.array_equal(p,d['p']),'full LR reprediction');ck(np.array_equal(ey,d['y']) and np.array_equal(ek,d['key']),'LR identity');entry=next(o for o in fit['outputs'] if o['execution']==ex);ck(sha(OUT/f'lr_{ex}.npz')==entry['sha256'],'LR output hash')
        print('AUDIT MODEL',dom,flush=True)
    rows=json.loads((HERE/'RESULTS.json').read_text());ck(len(rows)==288,'result count');groups={}
    for r in rows:groups.setdefault(r['cell'],[]).append(r)
    ck(len(groups)==96,'cell count')
    for num,(cell,rs) in enumerate(groups.items(),1):
        r=rs[0];ex,c,b=r['execution'],r['condition'],r['budget'];v,y,key=raw(ex,c,b);members=frozen['sets'][r['set']];ps=[v[n].astype(float) for n in members];singles=[p.argmax(1) for p in ps];warn=np.logical_or.reduce([s>0 for s in singles]);stage=np.zeros((len(y),ps[0].shape[1]-1))
        for p,s in zip(ps,singles):stage[s>0]+=p[s>0,1:]
        op=np.zeros(len(y),np.int8);op[warn]=stage[warn].argmax(1)+1;mp=(sum(ps)/len(ps)).argmax(1);k=ps[0].shape[1];sm=[metric(y,p,k) for p in singles];best=min(range(len(sm)),key=lambda i:(sm[i]['exfiltration']['missed'],sm[i]['false_alerts'],i));preds={'OR':op,'MEAN':mp,'best_single':singles[best]};om=metric(y,op,k);sumfa=sum(m['false_alerts'] for m in sm)
        base_warn=np.logical_or.reduce([v['b'+str(s)].argmax(1)>0 for s in range(8101,8104)]);base_fa=int(((y==0)&base_warn).sum());fixed=sum(int(((y==0)&(v['b'+str(s)].argmax(1)>0)).sum()) for s in range(8101,8104))/3
        if r['set']=='duplicate_control':ck(np.array_equal(op>0,base_warn),'duplicate unchanged warnings')
        saved=dict(np.load(r['decision_file']));ck(sha(r['decision_file'])==r['decision_sha256'],'decision hash');cost=0 if members==['current'] else 1 if ex=='UNRAVELED' else 2;ck(np.all(saved['spent']==cost) and cost<=b,'per-row evidence cost')
        for m in sm:
            for name in ['other_attack','exfiltration']+(['movement'] if k==4 else []):ck(om[name]['missed']<=m[name]['missed'],'H1 recall')
        ck(om['false_alerts']<=sumfa,'H1 false alerts')
        unique=int(((y==k-1)&(op>0)&~base_warn).sum());delta=om['false_alerts']-base_fa;lost=(y>0)&(op>0)&(mp==0);allwarn=np.logical_and.reduce([s>0 for s in singles])
        for r in rs:
            ck(r['members']==members and r['model_count']==len(members),'membership');ck(r['identity_hash']==ah(key) and r['label_hash']==ah(y),'cell identity');ck(np.array_equal(saved[r['aggregator']],preds[r['aggregator']]),'raw decision equality');eq(r,metric(y,preds[r['aggregator']],k),'metrics')
            for x,z in zip(r['single_metrics'],sm):eq(x,z,'single metrics')
            eq(r['overlap_ratio'],om['false_alerts']/sumfa if sumfa else None,'overlap');eq(r['fixed_base_mean_false_alerts'],fixed,'fixed workload denominator');eq(r['best_single_warning_recall'],sm[best]['exfiltration']['warning_recall'],'best recall')
            eq(r['OR_marginal_exfil_warnings'],unique,'exfil recovery');eq(r['OR_marginal_false_alerts'],delta,'marginal FA');eq(r['OR_added_false_alerts_per_exfil_recovery'],delta/unique if unique else None,'exchange rate');eq(r['OR_marginal_attack_warnings'],int(((y>0)&(op>0)&~base_warn).sum()),'attack recovery');eq(r['OR_unrecoverable_attacks'],int(((y>0)&(op==0)).sum()),'unrecoverable')
            eq(r['mean_lost_OR_attack_warnings'],int(lost.sum()),'mean loss');eq(r['mean_lost_all_members_warn'],int((lost&allwarn).sum()),'vote split');eq(r['mean_lost_some_members_benign'],int((lost&~allwarn).sum()),'benign member loss')
        if num%16==0:print('AUDIT',num,checks,flush=True)
    def get(ex):return next(r for r in rows if r['set']=='A6_full' and r['aggregator']=='OR' and r['execution']==ex and r['condition']=='clean' and r['budget']==2)
    r=get('UNRAVELED');h2={'strict_gain_over_base':r['OR_marginal_exfil_warnings']>0,'recall_at_least_95':r['exfiltration']['warning_recall']>=.95,'fixed_FA_bound':r['false_alerts']<=2*r['fixed_base_mean_false_alerts']};h3=[]
    for ex in ['wilson','harrison','pooled']:
        r=get(ex);h3.append({'execution':ex,'strict_gain_over_best':r['exfiltration']['warning_recall']>r['best_single_warning_recall'],'overlap_below_075':r['overlap_ratio'] is not None and r['overlap_ratio']<.75,'fixed_FA_bound':r['false_alerts']<=2*r['fixed_base_mean_false_alerts']})
    ok=all(f['converged'] for f in fits.values());status={'H1':'SUPPORTED_BY_CONSTRUCTION','H2':'SUPPORTED' if all(h2.values()) and ok else 'NOT_SUPPORTED','H3':'SUPPORTED' if all(x['strict_gain_over_best'] for x in h3) and all(x['overlap_below_075'] and x['fixed_FA_bound'] for x in h3[:2]) and ok else 'NOT_SUPPORTED'}
    result={'status':'PASS','checks':checks,'cells':96,'result_rows':288,'new_models_repredicted':2,'failures':[],'hypotheses':status,'H2_components':h2,'H3_components':h3,'fits_converged':ok,'original_PX092_H3':'NOT_SUPPORTED_UNCHANGED'};(HERE/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    try:main()
    except Exception as e:(HERE/'AUDIT_FAILURE.json').write_text(json.dumps({'checks':checks,'error':repr(e)},indent=2));raise
