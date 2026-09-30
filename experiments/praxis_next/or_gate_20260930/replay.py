"""Fixed warning OR/mean replay. Per-row decision artifacts remain private."""
import argparse,functools,itertools
import numpy as np
from common import *

@functools.lru_cache(maxsize=3)
def old(seed,condition):return dict(np.load(OLD/f'seed_{seed}/{condition}_inputs.npz'))
@functools.lru_cache(maxsize=6)
def ait(seed,execution):return dict(np.load(AIT/f'predictions/s{seed}_{execution}.npz'))
@functools.lru_cache(maxsize=10)
def roles(seed):return np.load(PRIVATE/f'roles_{seed}.npy')
@functools.lru_cache(maxsize=1)
def unr_identity():return dict(np.load(OLD/'evaluation_identity.npz'))

def identity(domain,execution):
    if domain=='UNRAVELED':
        d=unr_identity();return d['y'],d['event_hash']
    ds=[ait(8101,e) for e in (['wilson','harrison'] if execution=='pooled' else [execution])]
    return np.concatenate([d['y'] for d in ds]),np.concatenate([d['key'] for d in ds])

def single(spec,condition,budget,execution):
    seed=spec['seed'];expert=spec['expert']
    if execution!='UNRAVELED':
        if execution=='pooled':
            vals=[single(spec,condition,budget,e) for e in ['wilson','harrison']]
            return tuple(np.concatenate([v[i] for v in vals]) for i in range(3))
        d=ait(seed,execution);n=len(d['y']);p=d['p0' if expert=='current' else 'p1']
        return p,np.full(n,0 if expert=='current' else 2,np.float32),np.full(n,0 if expert=='current' else 2,np.uint8)
    shared=old(8101,condition);n=shared['probabilities'].shape[1]
    if seed<=8103:d=old(seed,condition);base=d['probabilities'][0]
    else:base=shared['probabilities'][0]
    if expert=='all':return d['probabilities'][3],np.full(n,3,np.float32),np.full(n,3,np.uint8)
    if expert=='current':return base,np.zeros(n,np.float32),np.zeros(n,np.uint8)
    channel=0 if expert=='roles' else 1;cost=channel+1;state=1<<channel
    attempted=budget>=cost
    arrived=shared['available'][:,channel]&(shared['delays'][:,channel]<=1+1e-7)&attempted
    p=roles(seed) if seed>8103 else d['probabilities'][state]
    return np.where(arrived[:,None],p,base),np.full(n,cost if attempted else 0,np.float32),np.where(arrived,state,0).astype(np.uint8)

def references(condition,budget,execution):
    refs={}
    if execution!='UNRAVELED':
        for s in SEEDS[:3]:
            for pol in ['always_history','entropy']:
                ds=[ait(s,e) for e in (['wilson','harrison'] if execution=='pooled' else [execution])]
                refs[f'{pol}_{s}']=np.concatenate([d[pol+'_p'].argmax(1) for d in ds])
        return refs
    shared=old(8101,condition);px=pxmodule()
    for s in SEEDS[:3]:
        d=old(s,condition);g={p:d[p+'_gains'] for p in ['entropy','harm']}
        for pol in g:
            tr=px.replay(pol,g,shared['available'],shared['delays'],shared['random_order'],budget,condition)
            refs[f'{pol}_{s}']=d['probabilities'][tr['state'],np.arange(len(tr['state']))].argmax(1)
    return refs

def evaluate(part,cell,members,condition='clean',budget=2,execution='UNRAVELED',subset=False):
    domain='UNRAVELED' if execution=='UNRAVELED' else 'AIT';y,key=identity(domain,execution);k=4 if domain=='UNRAVELED' else 3
    vals=[single(m,condition,budget,execution) for m in members];p=np.stack([v[0] for v in vals]);op,mp,sp=decisions(p)
    # Evidence is shared across members; these sets require only one channel, or all evidence in the explicit reference.
    spent=np.max(np.stack([v[1] for v in vals]),axis=0);reference=any(m['expert']=='all' for m in members)
    if not reference:assert np.all(spent<=budget)
    mm=[metrics(y,v,k) for v in sp];fa_sum=sum(m['false_alerts'] for m in mm);ex=k-1
    best=min(range(len(mm)),key=lambda i:(mm[i]['exfiltration']['missed'],mm[i]['false_alerts'],i));preds={'OR':op,'MEAN':mp,'best_single':sp[best]}
    om=metrics(y,op,k)
    for m in mm:
        for n in (NAMES[1:] if k==4 else ['other_attack','exfiltration']):assert om[n]['missed']<=m[n]['missed']
    assert om['false_alerts']<=fa_sum
    dest=PRIVATE/part;dest.mkdir(exist_ok=True);path=dest/(cell+'.npz')
    assert not path.exists();np.savez_compressed(path,**preds,spent=spent)
    refs=references(condition,budget,execution);out=[]
    for agg,pred in preds.items():
        m=metrics(y,pred,k)
        rec={name:{'recovered':int(((y>0)&(pred>0)&(r==0)).sum()),'lost':int(((y>0)&(pred==0)&(r>0)).sum()),'reference_metrics':metrics(y,r,k)} for name,r in refs.items()}
        out.append({'part':part,'cell':cell,'aggregator':agg,'execution':execution,'condition':condition,'budget':budget,'members':members,'model_count':len(members),'subset_sensitivity':subset,'reference_only':reference,'availability_bypassed':reference,'best_single_member':members[best],'mean_evidence_cost':float(spent.mean()),'max_evidence_cost':float(spent.max()),'nominal_member_evaluations':len(members),'overlap_ratio':om['false_alerts']/fa_sum if fa_sum else None,'sum_single_false_alerts':fa_sum,'best_single_exfiltration_warning_recall':mm[best]['exfiltration']['warning_recall'],'single_metrics':mm,'recovered_against':rec,'label_hash':ah(y),'identity_hash':ah(key),'decisions_file':str(path),'decisions_sha256':sha(path),**m})
    return out

def run(part):
    verify();assert not (HERE/part/'GROUPS.json').exists();rows=[]
    if part=='partA':
        sets={'A1_roles':[(s,'roles') for s in SEEDS[:3]],'A2_current':[(s,'current') for s in SEEDS[:3]],'A3_history':[(s,'history') for s in SEEDS[:3]],'A4_all_reference':[(s,'all') for s in SEEDS[:3]],'A5_mixed':[(s,e) for s in SEEDS[:3] for e in ['current','roles']]}
        for cond in CONDS:
            for b in [1,2,3]:
                for name,ms in sets.items():rows+=evaluate(part,f'{name}_{cond}_b{b}',[{'seed':s,'expert':e} for s,e in ms],cond,b)
                print(part,cond,b,flush=True)
    elif part=='partB':
        assert json.loads((HERE/'partB/FIT_LOG.json').read_text())['completed_fits']==7
        for cond in CONDS:
            for b in [1,2,3]:
                for n in [1,2,3,5,7,10]:rows+=evaluate(part,f'B_n{n}_{cond}_b{b}',[{'seed':s,'expert':'roles'} for s in SEEDS[:n]],cond,b)
                print(part,cond,b,flush=True)
        for ss in itertools.combinations(SEEDS,3):
            rows+=evaluate(part,'B_triple_'+'_'.join(map(str,ss)),[{'seed':s,'expert':'roles'} for s in ss],subset=True)
        print('partB 120 triples complete',flush=True)
    else:
        sets={'C1_history':[(s,'history') for s in SEEDS[:3]],'C2_current':[(s,'current') for s in SEEDS[:3]],'C3_mixed':[(s,e) for s in SEEDS[:3] for e in ['current','history']]}
        for ex in ['wilson','harrison','pooled']:
            for name,ms in sets.items():rows+=evaluate(part,f'{name}_{ex}',[{'seed':s,'expert':e} for s,e in ms],execution=ex)
            print(part,ex,flush=True)
    save(HERE/part/'GROUPS.json',rows);print(part,'complete',len(rows),'rows',flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('part',choices=['partA','partB','partC']);run(ap.parse_args().part)
