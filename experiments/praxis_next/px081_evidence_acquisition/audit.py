"""Independent receipt/trace/confusion audit; does not import experiment code."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score

HERE=Path(__file__).resolve().parent
NAMES=('benign','other_attack','movement','exfiltration')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def near(a,b): assert abs(float(a)-float(b))<2e-6,(a,b)

def check_table(row,y,p,trace):
    pred=p.argmax(1); cm=np.zeros((4,4),dtype=int);np.add.at(cm,(y,pred),1)
    assert cm.tolist()==row['confusion']
    assert len(y)==row['n']
    support=cm.sum(1); predicted=cm.sum(0); tp=cm.diagonal()
    pr=np.divide(tp,predicted,out=np.zeros(4),where=predicted>0)
    rc=np.divide(tp,support,out=np.zeros(4),where=support>0)
    f1=np.divide(2*pr*rc,pr+rc,out=np.zeros(4),where=(pr+rc)>0)
    near(row['macro_f1'],f1.mean());near(row['weighted_error_total'],((support-tp)*[1,1,4,4]).sum())
    assert row['errors']==len(y)-tp.sum()
    assert row['benign_false_alerts']==cm[0,1:].sum()
    assert row['movement_missed']==support[2]-tp[2]
    assert row['exfiltration_missed']==support[3]-tp[3]
    assert row['movement_as_exfiltration']==cm[2,3]
    for c,name in enumerate(NAMES):
        r=row[name]; assert r['support']==support[c]
        near(r['precision'],pr[c]);near(r['recall'],rc[c]);near(r['f1'],f1[c])
        if 0<support[c]<len(y):
            near(r['ap'],average_precision_score(y==c,p[:,c]));near(r['roc_auc'],roc_auc_score(y==c,p[:,c]))
        else: assert r['ap'] is None and r['roc_auc'] is None
    for k in ('spent','elapsed'):near(row['mean_'+('spend' if k=='spent' else k)],trace[k].mean())
    near(row['query_rate'],(trace['attempted']>0).mean())
    near(row['mean_queries'],(trace['actions']>=0).sum(1).mean())
    near(row['mean_delivered'],((trace['state']&1)>0).mean()+((trace['state']&2)>0).mean())

def audit(root):
    receipt=json.loads((root/'RUN_RECEIPT.json').read_text()); frozen=json.loads((HERE/'FREEZE.json').read_text())
    assert sha(HERE/'FREEZE.json')==receipt['freeze_sha256']
    for name,digest in frozen['source_sha256'].items():assert sha(HERE/name)==digest,name
    for name,digest in receipt['public_hashes'].items():assert sha(HERE/name)==digest,name
    identities=np.load(root/'evaluation_identity.npz');y=identities['y'];caps=identities['capture']
    rows=json.loads((HERE/'RESULTS.json').read_text());strata=json.loads((HERE/'CAPTURE_RESULTS.json').read_text())
    stratum_lookup={(r['seed'],r['condition'],r['budget'],r['policy'],r['capture']):r for r in strata}
    checked=0; trace_checks=0; inputs=None; previous=None
    for row in rows:
        seed,condition,budget,policy=[row[k] for k in ('seed','condition','budget','policy')]
        seedpath=root/f'seed_{seed}'
        if (seed,condition)!=previous:
            inputs=dict(np.load(seedpath/f'{condition}_inputs.npz')); previous=(seed,condition)
        n=len(y)
        if row['reference_only']:
            tr=dict(state=np.full(n,3),attempted=np.full(n,3),spent=np.full(n,3.),elapsed=np.zeros(n),actions=np.broadcast_to([0,1],(n,2)))
            check_table(row,y,inputs['probabilities'][3],tr);checked+=1;continue
        tr=dict(np.load(seedpath/f'{condition}_b{budget}_{policy}.npz')); p=tr.pop('probabilities')
        state=np.zeros(n,int);attempted=np.zeros(n,int);spent=np.zeros(n);elapsed=np.zeros(n)
        for step in range(2):
            chosen=tr['actions'][:,step]; ids=np.flatnonzero(chosen>=0);g=chosen[ids]
            assert np.all((attempted[ids]&(1<<g))==0)
            assert np.all(spent[ids]+np.array([1.,2.])[g]<=budget)
            assert np.all(elapsed[ids]+np.array([.25,.75])[g]<=1.+1e-7)
            attempted[ids]|=1<<g;spent[ids]+=np.array([1.,2.])[g]
            elapsed[ids]+=inputs['delays'][ids,g]
            delivered=inputs['available'][ids,g]&(elapsed[ids]<=1.+1e-7)
            state[ids[delivered]]|=1<<g[delivered]
        for key,actual in [('state',state),('attempted',attempted),('spent',spent),('elapsed',elapsed)]:np.testing.assert_array_equal(actual,tr[key])
        np.testing.assert_array_equal(p,inputs['probabilities'][state,np.arange(n)])
        check_table(row,y,p,tr);checked+=1;trace_checks+=1
        for c in np.unique(caps):
            mask=caps==c
            check_table(stratum_lookup[seed,condition,budget,policy,int(c)],y[mask],p[mask],{k:v[mask] for k,v in tr.items()});checked+=1
    fits=json.loads((root/'FIT_LOG.json').read_text())
    for f in fits:assert max(f['fit_captures'])<f['evaluation_capture']
    private_hashes={str(p.relative_to(root)):sha(p) for p in root.rglob('*.npz')}
    manifest=root/'ARTIFACT_HASHES.json';manifest.write_text(json.dumps(private_hashes,indent=2)+'\n')
    result={'status':'PASS','independent_metric_tables_checked':checked,'sequential_query_traces_checked':trace_checks,
        'forward_folds_checked':len(fits),'private_npz_hashed':len(private_hashes),'artifact_manifest_sha256':sha(manifest),
        'checks':['frozen code/input receipt linkage','all confusion and ranking metrics','all capture-stratum metrics',
            'budget charged for failed and late queries','no duplicate channel queries','quoted delay eligibility',
            'delivered state exactly matches hidden schedule','predictions use precisely delivered subset','forward fold ordering'],
        'scope':'Recomputability audit, not independent campaign validation or live availability measurement'}
    (HERE/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,default=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081'))
    audit(a.parse_args().output)
