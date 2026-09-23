"""Recalculate published outputs and saved inference; no fitting or tuning."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits
from .run import (ROOT,SEEDS,CONDITIONS,ARMS,CLASSES,COST,DATA_SHA,binding,sha,write,utc,observe,selector_features,gate_target,choose)

def metric(y,p):
    """Independent confusion/count formulas; ranking uses standard sklearn metrics."""
    pred=np.argmax(p,axis=1);cm=np.zeros((4,4),dtype=np.int64);np.add.at(cm,(y,pred),1)
    support=cm.sum(1);called=cm.sum(0);tp=cm.diagonal()
    precision=np.divide(tp,called,out=np.zeros(4),where=called>0)
    recall=np.divide(tp,support,out=np.zeros(4),where=support>0)
    f1=np.divide(2*tp,support+called,out=np.zeros(4),where=(support+called)>0)
    return {'rows':len(y),'macro_f1':float(f1.mean()),'stage_weighted_error':float(np.dot(COST,support-tp)/len(y)),
        'normal_false_attacks':int(support[0]-tp[0]),'movement_any_attack_recall':float((support[2]-cm[2,0])/support[2]) if support[2] else None,
        'confusion':cm.tolist(),'classes':{name:{'support':int(support[k]),'precision':float(precision[k]),'recall':float(recall[k]),'f1':float(f1[k]),
            'ap':float(average_precision_score(y==k,p[:,k])) if support[k] else None,
            'roc_auc':float(roc_auc_score(y==k,p[:,k])) if 0<support[k]<len(y) else None} for k,name in enumerate(CLASSES)}}

def same(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:same(a[k],b[k])
    elif isinstance(a,float):assert np.isclose(a,b,rtol=1e-12,atol=1e-12),(a,b)
    else:assert a==b,(a,b)

def audit(data, run, output):
    if sha(data)!=DATA_SHA:raise AssertionError("Source changed")
    d=dict(np.load(data,allow_pickle=False));st=np.load(run/"STALE.npz",allow_pickle=False)
    assert np.all(st["latest"]<d["start"]-300000)
    assert json.loads((run/"STARTED.json").read_text())["binding"]==binding()
    recorded=json.loads((run/"METRICS.json").read_text());lookup={(r['seed'],r['condition'],r['arm']):r for r in recorded}
    tables=0;model_arrays=0;target_rows=0;fold_checks=0
    for seed in SEEDS:
        sd=run/str(seed);rows=np.load(sd/"ROWS.npz",allow_pickle=False);fit,test=rows['fit'],rows['test']
        assert np.all(d['split'][fit]==0) and np.all(d['split'][test]==2)
        np.testing.assert_array_equal(test,np.flatnonzero(d['split']==2));np.testing.assert_array_equal(rows['y'],d['y'][test])
        for capture in range(1,5):
            z=np.load(sd/f'fold{capture}_rows.npz',allow_pickle=False);tr,va=z['fit'],z['validation']
            assert not np.intersect1d(tr,va).size and np.all(d['capture'][tr]<capture) and np.all(d['capture'][va]==capture)
            assert d['end'][tr].max()<d['start'][va].min();fold_checks+=1
        oof=np.load(sd/'OOF.npz',allow_pickle=False);yr=d['y'][oof['rows']]
        assert np.all(d['split'][oof['rows']]==0)
        np.testing.assert_array_equal(oof['target'],gate_target(yr,oof['current_p'],oof['context_p'],COST))
        np.testing.assert_array_equal(oof['ordinary_target'],gate_target(yr,oof['current_p'],oof['context_p'],np.ones(4)))
        for ci,condition in enumerate(['clean','missing_half','stale_5min']):
            mask=oof['conditions']==ci;_,status=observe(d,oof['rows'][mask],condition,st['history'],st['latest'])
            np.testing.assert_array_equal(oof['features'][mask],selector_features(oof['current_p'][mask],oof['context_p'][mask],status))
        for capture in range(1,5):
            a=joblib.load(sd/f'fold{capture}_current.joblib');b=joblib.load(sd/f'fold{capture}_context.joblib')
            for ci,condition in enumerate(['clean','missing_half','stale_5min']):
                mask=(d['capture'][oof['rows']]==capture)&(oof['conditions']==ci);ix=oof['rows'][mask]
                x=np.column_stack([d['current'][ix],d['roles'][ix]]);h,_=observe(d,ix,condition,st['history'],st['latest'])
                np.testing.assert_array_equal(oof['current_p'][mask],a.predict_proba(x))
                np.testing.assert_array_equal(oof['context_p'][mask],b.predict_proba(np.column_stack([x,h])))
        target_rows+=len(yr)
        models={n:joblib.load(sd/(n+'.joblib')) for n in ['current','context','context_dropout','ordinary_gate','stage_harm_gate']}
        x=np.column_stack([d['current'][test],d['roles'][test]]);pc=models['current'].predict_proba(x);y=d['y'][test]
        for condition in CONDITIONS:
            p=np.load(sd/(condition+'.npz'),allow_pickle=False);h,status=observe(d,test,condition,st['history'],st['latest'])
            ph=models['context'].predict_proba(np.column_stack([x,h]));s=selector_features(pc,ph,status)
            os=models['ordinary_gate'].predict(s);ss=models['stage_harm_gate'].predict(s)
            expected={'current_roles':pc,'context':ph,'fixed_fusion':(pc+ph)/2,'confidence_gate':choose(pc,ph,ph.max(1)>pc.max(1)),
                'ordinary_gate':choose(pc,ph,os<0),'stage_harm_gate':choose(pc,ph,ss<0),'context_dropout':models['context_dropout'].predict_proba(np.column_stack([x,h]))}
            for name in ARMS:
                np.testing.assert_array_equal(p[name],expected[name]);model_arrays+=1
                assert np.isfinite(p[name]).all() and np.allclose(p[name].sum(1),1)
                r=lookup[(seed,condition,name)];m=metric(y,p[name])
                for k,v in m.items():same(r[k],v)
                for capture in np.unique(d['capture'][test]):
                    ix=d['capture'][test]==capture
                    same(r['by_capture'][str(capture)],metric(y[ix],p[name][ix]));tables+=1
                ix=(d['src_role'][test]==1)&(d['dst_role'][test]==3)
                same(r['department_to_private_services'],metric(y[ix],p[name][ix]));tables+=2
            np.testing.assert_array_equal(p['ordinary_score'],os);np.testing.assert_array_equal(p['stage_harm_score'],ss)
            np.testing.assert_array_equal(p['status'],status)
            print(f'AUDIT {seed} {condition}',flush=True)
    result={'utc':utc(),'status':'PASS','forward_folds_checked':fold_checks,'selector_targets_checked':target_rows,
        'metric_tables_recomputed':tables,'saved_probability_arrays_replayed_exactly':model_arrays,
        'scope':'Calculation, source bindings, partition chronology, target construction and inference integrity; not independent attack-label verification or independent scientific confirmation.',
        'source_hashes':{str(ROOT/'audit.py'):sha(ROOT/'audit.py')},'input_sha256':DATA_SHA}
    write(output,result)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    with threadpool_limits(limits=4):audit(a.data,a.run,a.output)
