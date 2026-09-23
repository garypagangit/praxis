"""Post-fit independent arithmetic and split audit; never fits or selects models."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

HERE=Path(__file__).resolve().parent
NAMES=['Benign','OtherAttackStage','LateralMovement','DataExfiltration']

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def scalar_equal(a,b):
    if b is None: assert a is None
    else: assert np.isclose(a,b,atol=1e-12,rtol=1e-10),(a,b)

def audit(data,run):
    protocol=json.loads((HERE/'protocol.json').read_text(encoding='utf-8'))
    complete=json.loads((run/'COMPLETE.json').read_text(encoding='utf-8'))
    assert sha(data)==protocol['data_sha256']
    for name,h in complete['source'].items():assert sha(HERE/name)==h,name
    for name,h in complete['files'].items():assert sha(run/name)==h,name
    with np.load(data,allow_pickle=False) as z:d={k:z[k] for k in z.files}
    with np.load(run/'DESIGN.npz',allow_pickle=False) as z:design={k:z[k] for k in z.files}
    rows=json.loads((run/'METRICS.json').read_text(encoding='utf-8'))
    assert len(rows)==18
    metrics_checked=0
    fingerprints=[]
    for row in d['current']:
        a=np.array(row,dtype='<f8');a[a==0]=0
        fingerprints.append(hashlib.sha256(a.tobytes()).hexdigest())
    fp=np.asarray(fingerprints)
    for r in rows:
        path=run/f'{r["seed"]}_{r["view"]}_{r["arm"]}.npz'
        with np.load(path,allow_pickle=False) as z: fit=z['fit'];test=z['test'];y=z['y'];p=z['p'];capture=z['capture']
        assert np.array_equal(y,d['y'][test]) and np.array_equal(capture,d['capture'][test])
        assert not np.intersect1d(fit,test).size
        assert np.array_equal(np.bincount(d['y'][fit],minlength=4),design['counts'])
        assert np.isfinite(p).all() and np.all(p>=0) and np.allclose(p.sum(1),1)
        if r['arm']!='conventional_random':
            assert np.array_equal(test,design['anchor'])
            assert not np.isin(fp[fit],fp[test]).any()
        if r['arm']=='past_only_anchor':
            assert np.all(d['split'][fit]==0) and d['end'][fit].max()<d['start'][test].min()
        elif r['arm']=='time_mixed_anchor':assert not np.any(d['split'][fit]==1)
        pred=p.argmax(1);cm=np.zeros((4,4),dtype=np.int64);np.add.at(cm,(y,pred),1)
        assert cm.tolist()==r['confusion']
        den=cm.sum(0)+cm.sum(1);f=np.divide(2*np.diag(cm),den,out=np.zeros(4),where=den>0)
        scalar_equal(float(f.mean()),r['macro_f1']);metrics_checked+=1
        assert int(cm[0,1:].sum())==r['normal_false_attacks']
        scalar_equal(float(cm[0,1:].sum()/cm[0].sum()),r['normal_false_attack_rate'])
        scalar_equal(float(1-cm[2,0]/cm[2].sum()),r['movement_any_attack_recall'])
        for k,name in enumerate(NAMES):
            m=r['per_class'][name];tp=cm[k,k]
            assert m['support']==int(cm[k].sum())
            for key,value in [('precision',float(tp/cm[:,k].sum()) if cm[:,k].sum() else 0.),('recall',float(tp/cm[k].sum()) if cm[k].sum() else 0.),('f1',float(f[k])),('ap',float(average_precision_score(y==k,p[:,k]))),('roc_auc',float(roc_auc_score(y==k,p[:,k])))]:
                scalar_equal(value,m[key]);metrics_checked+=1
        assert int(np.isin(fp[test],fp[fit]).sum())==r['test_rows_with_current_fingerprint_in_training']
        assert int(np.sum(d['end'][fit]>=d['start'][test].min()))==r['training_rows_ending_after_first_test_start']
    summary=[]
    for view in protocol['views']:
        for arm in protocol['arms']:
            selected=[r for r in rows if r['view']==view and r['arm']==arm]
            summary.append({'view':view,'arm':arm,'n_seeds':len(selected),'test_rows':selected[0]['rows'],
                'test_class_counts':[selected[0]['per_class'][n]['support'] for n in NAMES],
                **{key:float(np.mean([r[key] for r in selected])) for key in ['macro_f1','normal_false_attacks','normal_false_attack_rate','movement_any_attack_recall']},
                'movement_f1':float(np.mean([r['per_class']['LateralMovement']['f1'] for r in selected])),
                'movement_recall':float(np.mean([r['per_class']['LateralMovement']['recall'] for r in selected])),
                'exfiltration_f1':float(np.mean([r['per_class']['DataExfiltration']['f1'] for r in selected]))})
    receipt={'status':'PASS','prediction_tables':18,'scalar_metrics_checked':metrics_checked,'input_sha256':sha(data),
             'output_hashes_verified':len(complete['files']),'same_anchor_and_fingerprint_exclusion_verified':True,
             'audit_source_sha256':sha(__file__),'scope':'Arithmetic and split provenance only; does not verify author stage labels or independent campaign generalization.'}
    for name in ['METRICS.json','PAIRED.json','DESIGN.json','COMPLETE.json','STARTED.json']:
        (HERE/name).write_bytes((run/name).read_bytes())
    write(HERE/'SUMMARY.json',summary);write(HERE/'AUDIT.json',receipt)
    lines=['# PX-082: temporal evaluation sensitivity','',
      '**Completed development measurement, not a general verdict on APT benchmark validity.**','',
      'The primary comparison predicts the same later-period anchor rows with the same class-specific fitting budget. One model sees only earlier fitting captures; the other can train on other later-period examples. All training rows whose current-feature fingerprint occurs in the anchor are removed from both pools. This measures sensitivity to training time/composition while holding the evaluation rows fixed.','',
      '| Feature view | Training/test protocol | Macro-F1 | Movement F1 | Exact movement recall | Exfiltration F1 | Normal false-alert rate |',
      '|---|---|---:|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f'| {r["view"]} | {r["arm"]} | {r["macro_f1"]:.4f} | {r["movement_f1"]:.4f} | {100*r["movement_recall"]:.2f}% | {r["exfiltration_f1"]:.4f} | {100*r["normal_false_attack_rate"]:.3f}% |')
    lines+=['','Means are over three fits on the same events, not independent campaigns. Conventional random splitting has a different test population and may contain equal current-feature fingerprints across its boundary; those counts are published in METRICS.json. Its score difference is not a pure estimate of temporal leakage.','',
      '## Same-anchor changes','']
    for view in protocol['views']:
        a=next(r for r in summary if r['view']==view and r['arm']=='past_only_anchor'); b=next(r for r in summary if r['view']==view and r['arm']=='time_mixed_anchor')
        lines.append(f'- {view}: time-mixed minus past-only macro-F1 = **{b["macro_f1"]-a["macro_f1"]:+.4f}**; movement recall change = **{100*(b["movement_recall"]-a["movement_recall"]):+.2f} percentage points**.')
    lines+=['','Per-seed paired capture-bootstrap intervals are in PAIRED.json. With only five later captures from one campaign, they are conditional descriptive intervals, not population-level confidence.','',
      '## Interpretation and limits','',
      'A score increase under time-mixed fitting means these predictions benefit from labeled examples unavailable in a strictly earlier training period. It does not isolate future access from the distributional variety that comes with it. It does not demonstrate deliberate leakage in another paper. A small difference would not certify robustness.','',
      f'The common anchor contains {sum(summary[0]["test_class_counts"]):,} rows, including {summary[0]["test_class_counts"][2]} movement annotations. These are author Remote System Discovery stage labels, not verified successful movement. Full-flow features preclude an early-warning claim. No new independent campaign or novel algorithm is claimed.','',
      '## Evidence','', '[Frozen protocol](protocol.json), [all scores](METRICS.json), [paired comparisons](PAIRED.json), [split audit](DESIGN.json), [independent arithmetic audit](AUDIT.json), [run receipt](COMPLETE.json).','']
    (HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args();audit(a.data,a.run)
