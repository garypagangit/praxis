"""Independent count formulas and replay of the frozen score policy."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score
from .run import ROOT,SOURCE,DATASETS,ARMS,TARGET,PARAMS,qualify,binding,sha,write,utc,features,target

def metrics(y,s,t=.5):
    pred=s>t;positive=y==1;tp=int(np.sum(pred&positive));fp=int(np.sum(pred&~positive));fn=int(np.sum(~pred&positive));tn=int(np.sum(~pred&~positive))
    return {'rows':len(y),'positive':int(positive.sum()),'confusion':[[tn,fp],[fn,tp]],'precision':tp/(tp+fp) if tp+fp else 0.,
        'recall':tp/(tp+fn) if tp+fn else 0.,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
        'ap':float(average_precision_score(y,s)) if tp+fn else None,'roc_auc':float(roc_auc_score(y,s)) if tp+fn and tn+fp else None,
        'other_label_flags':fp,'other_label_flag_rate':fp/(tn+fp) if tn+fp else None,'target_cost_error':(fp+4*fn)/len(y)}

def same(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:same(a[k],b[k])
    elif isinstance(a,float):assert np.isclose(a,b,atol=1e-12,rtol=1e-12),(a,b)
    else:assert a==b,(a,b)

def audit(run,output):
    assert qualify()==json.loads((ROOT/'INPUTS.json').read_text())
    assert json.loads((run/'STARTED.json').read_text())['binding']==binding()
    models=[joblib.load(run/'ordinary.joblib'),joblib.load(run/'target_cost.joblib')]
    for m in models:
        for k,v in PARAMS.items():assert m.get_params()[k]==v
    a=np.load(SOURCE/'casino_run1'/f'PRIVATE_CAL_{TARGET}_semantic_event.npz');b=np.load(SOURCE/'casino_run1'/f'PRIVATE_CAL_{TARGET}_entity_context.npz');tr=np.load(run/'TRAIN.npz')
    np.testing.assert_array_equal(tr['X'],features(a['score'],b['score'],a['observed'],b['observed']));np.testing.assert_array_equal(tr['y'],a['y'])
    np.testing.assert_array_equal(tr['ordinary_target'],target(a['y'],a['score'],b['score'],1));np.testing.assert_array_equal(tr['cost_target'],target(a['y'],a['score'],b['score'],4))
    rows=json.loads((run/'METRICS.json').read_text());lookup={(r['dataset'],r['condition'],r['perturbation_seed'],r['arm']):r for r in rows}
    arrays=tables=0
    for dataset in DATASETS:
        source=SOURCE/(dataset+'_run1');roster=np.load(source/'PRIVATE_TARGET_ROSTER.npz')
        grid=sorted({(r['condition'],r['perturbation_seed']) for r in rows if r['dataset']==dataset});assert len(grid)==21
        for condition,seed in grid:
            sourcep={n:np.load(source/f'PRIVATE_{TARGET}_{n}_{condition}_{seed}.npz') for n in ['semantic_event','entity_context','mixed_dropout']}
            c=sourcep['semantic_event']['score'];h=sourcep['entity_context']['score'];oc=sourcep['semantic_event']['observed'];oh=sourcep['entity_context']['observed'];y=sourcep['semantic_event']['y']
            p=np.load(run/dataset/f'{condition}_{seed}.npz');np.testing.assert_array_equal(p['y'],y)
            os=models[0].predict(features(c,h,oc,oh));cs=models[1].predict(features(c,h,oc,oh))
            expected={'current':c.copy(),'context':h.copy(),'fixed_fusion':(c+h)/2,'mixed_dropout':sourcep['mixed_dropout']['score'].copy(),
                'confidence_gate':np.where(np.maximum(h,1-h)>np.maximum(c,1-c),h,c),'ordinary_gate':np.where(os<0,h,c),'target_cost_gate':np.where(cs<0,h,c)}
            for arm,e in expected.items():
                e[~(oc|oh)]=0;np.testing.assert_array_equal(e,p[arm]);arrays+=1
                row=lookup[(dataset,condition,seed,arm)]
                for k,v in metrics(y,e).items():same(row[k],v)
                tables+=1
                for rid in np.unique(roster['run_ids']):
                    ix=roster['run_ids']==rid;same(row['by_run'][str(rid)],metrics(y[ix],e[ix]));tables+=1
            np.testing.assert_array_equal(p['ordinary_gate_score'],os);np.testing.assert_array_equal(p['target_cost_gate_score'],cs)
        print('AUDIT '+dataset,flush=True)
    native=json.loads((run/'ORIGINAL_THRESHOLD_CONTROLS.json').read_text())
    for r in native:
        source=SOURCE/(r['dataset']+'_run1');z=np.load(source/f"PRIVATE_{TARGET}_{r['arm']}_{r['condition']}_{r['perturbation_seed']}.npz")
        original=json.loads((source/'RESULTS.json').read_text())['targets'][TARGET]['models'][r['arm']]['threshold']
        assert r['threshold']==original['threshold_value']
        for k,v in metrics(z['y'],z['score'],r['threshold']).items():same(r[k],v)
    write(output,{'status':'PASS','utc':utc(),'qualified_input_prediction_files':220,'selector_training_rows':len(tr['y']),
        'final_probability_arrays_replayed_exactly':arrays,'independent_metric_tables':tables,'original_threshold_control_tables':len(native),
        'auditor_sha256':sha(ROOT/'audit.py'),'scope':'Source/cache order bindings, fit split/targets, invisible-row handling, saved-policy inference and calculation checks; not independent attack truth or untouched confirmation.'})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();audit(a.run,a.output)
