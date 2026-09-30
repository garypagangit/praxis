"""Post-run independent aggregate audit and lossless publication of all arms."""
import csv,gzip,json,hashlib
from collections import defaultdict
import numpy as np
from common import HERE,OUT,verify,identities,STAGES

verify()
dest=HERE/'results';dest.mkdir(exist_ok=True)
checks=0;matrices=0
def check(ok):
    global checks
    assert ok
    checks+=1
def near(a,b):check(a is None if b is None else a is not None and abs(a-b)<1e-10)
def metric(m):
    global matrices
    c=np.array(m['confusion']);s=c.sum(1);p=c.sum(0);matrices+=1
    check(c.shape==(4,4) and (c>=0).all());check(int(c.sum())==m['n'])
    near(m['macro_f1'],sum(2*c[k,k]/(s[k]+p[k]) if s[k]+p[k] else 0 for k in range(4))/4)
    check(m['false_alerts']==int(c[0,1:].sum()))
    near(m['benign_fpr'],float(c[0,1:].sum()/s[0]) if s[0] else None)
    near(m['warnings_per_100k'],float(p[1:].sum()/c.sum()*100000))
    for k,n in enumerate(STAGES[1:],1):
        a=m[n];check(a['support']==s[k]);check(a['missed']==c[k,0])
        near(a['warning_recall'],float((s[k]-c[k,0])/s[k]) if s[k] else None)
        near(a['exact_recall'],float(c[k,k]/s[k]) if s[k] else None)
        near(a['miss_rate'],float(c[k,0]/s[k]) if s[k] else None)
    return c

ci,ti=identities();meta={k:np.concatenate([ci[k],ti[k]]) for k in ['y','capture','start','end']}
first=float(ti['start'].min());manifest={};allrows=[];data={}
for exp,nrows in [('PX088',126),('PX089',1620),('PX090',24)]:
    raw=(OUT/(exp+'.json')).read_bytes();d=json.loads(raw);data[exp]=d;check(len(d['rows'])==nrows)
    (dest/(exp+'.json.gz')).write_bytes(gzip.compress(raw,mtime=0))
    manifest[exp]={'rows':nrows,'sha256_decompressed':hashlib.sha256(raw).hexdigest(),'seconds':d['seconds']}
    for r in d['rows']:
        m=r.get('automatic_metrics',r);c=metric(m)
        if exp=='PX088':
            check(r['review_requests']==r['review_served']+r['review_unresolved'])
            check(m['n']+r['review_requests']==len(ti['y']))
            check(r['warning_plus_review_requests']==int(c[:,1:].sum())+r['review_requests'])
            for q in r['capacity_by_capture']:
                check(q['capacity']==q['rows']*r['budget_per_100k']//100000)
                check(q['served']==min(q['requests'],q['capacity']))
                check(q['requests']==q['served']+q['unresolved'])
            for field in ['requests','served','unresolved']:check(r['review_'+field]==sum(q[field] for q in r['capacity_by_capture']))
            for k,n in enumerate(STAGES[1:],1):
                q=r['stage_disposition'][n]
                check(q['total']==int((ti['y']==k).sum()))
                check(q['automatic']+q['review_requested']==q['total'])
                check(q['review_served']+q['review_unresolved']==q['review_requested'])
                check(q['automatic']==m[n]['support'] and q['automatic_misses']==m[n]['missed'])
        elif exp=='PX089':
            boundary=float(meta['start'][meta['capture']==r['capture']].min())
            available=meta['end']+r['delay_hours']*3600000
            mask=(meta['capture']<r['capture'])&(available<(first if r['mode']=='frozen' else boundary))
            if r['mode']=='frozen':mask &=meta['capture']==5
            if r['mode']=='recent' and mask.any():mask &=meta['capture']==max(meta['capture'][mask])
            check(r['threshold_frozen_at']==boundary)
            check(r['calibration_counts']==np.bincount(meta['y'][mask],minlength=4).tolist())
            check(r['calibration_captures']==np.unique(meta['capture'][mask]).tolist())
            near(r['max_calibration_label_available'],float(max(available[mask])) if mask.any() else None)
            check(np.all(available[mask]<boundary))
        else:
            check(np.array_equal(sum((metric(v) for v in r['per_capture'].values())),c))
            if r['arm']=='monotone_union_veto':check(r['union_warnings_demoted']==0)
        flat={'experiment':exp,**{k:v for k,v in r.items() if not isinstance(v,(dict,list))}}
        flat.update({k:m[k] for k in ['n','macro_f1','false_alerts','benign_fpr']})
        for n in STAGES[1:]:flat.update({n+'_'+k:v for k,v in m[n].items()})
        if exp=='PX088':
            for n,q in r['stage_disposition'].items():flat.update({n+'_disposition_'+k:v for k,v in q.items()})
        allrows.append(flat)
check(len(data['PX090']['fits'])==6)
for f in data['PX090']['fits']:
    if f['model']=='monotone':check(f['grid_monotonicity_violations']==0)
with (dest/'ALL_ARMS.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=sorted(set().union(*(r.keys() for r in allrows))));writer.writeheader();writer.writerows(allrows)
(HERE/'AUDIT.json').write_text(json.dumps({'status':'PASS','independent_aggregate_checks':checks,'matrices_checked_including_capture_views':matrices,'input_and_code_hashes_verified':True,'new_fits':6,'new_cloud_allocation':False,'outputs':manifest,'scope':'Aggregate arithmetic, queue accounting and independently reconstructed label availability. Does not establish external validity or analyst effectiveness.'},indent=2)+'\n')
print('PASS',checks,'checks',matrices,'matrices')
for exp in data:print(exp,manifest[exp])
