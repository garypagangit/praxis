"""Locked-source DEDALE stress test; no target fitting or calibration."""
from __future__ import annotations
import argparse
from pathlib import Path
import warnings
import joblib
import numpy as np
from .run import ROOT, SOURCES, read, immutable_json, verify_files, predict
from .selection import alert_metrics
from ..tabular_batch.run_e1 import sha256_file, utc_now, canonical_hash, package_versions

POLICIES = ['reference', 'candidate', 'threshold_only', 'cv_natural_argmax', 'cv_natural_benign_threshold']
SELF = 'experiments/apt_benchmark/lateral_protection_experiment/run_external.py'

def specification(data_path, source_run):
    source = read(source_run / 'PREFIT_RECEIPT.json')
    verify_files(ROOT, source['fixed']['source_hashes'])
    return {'schema_version':1, 'experiment':'DEDALE_LOCKED_SOURCE_STRESS_V1',
            'status':'FROZEN_BEFORE_EXTERNAL_PREDICTIONS', 'source_budget':1024, 'source_seed':20260921,
            'source_execution_binding':source['execution_binding'], 'source_prefit_sha256':sha256_file(source_run/'PREFIT_RECEIPT.json'),
            'data_sha256':sha256_file(data_path), 'manifest_sha256':sha256_file(data_path.with_name('MANIFEST.json')),
            'policy_names':POLICIES, 'cpu_threads':4, 'normal_binary_label':0, 'lateral_binary_label':1,
            'source_hashes':{p:sha256_file(ROOT/p) for p in SOURCES+[SELF]},
            'target_role':'Day17 unique benign-versus-author-TA0008 flow stress; at most100000 benign fingerprints; all surviving lateral fingerprints; no target fit/calibration',
            'infeasibility':'If source selection is infeasible, report missing candidate/reference/ablation and evaluate only frozen natural controls; no fallback invention',
            'interpretation':'One attack execution and at most four lateral rows cannot confirm a 3pp noninferiority margin. Sampled prevalence makes precision/F1 descriptive only. No independent-incident confidence intervals.'}

def run(data_path, source_run, protocol, out):
    if protocol != specification(data_path, source_run):
        raise ValueError('External inputs, source freeze, or code changed')
    if (out/'RESULT.json').exists():
        raise ValueError('External run already exists; use its saved results, do not rescore')
    out.mkdir(parents=True,exist_ok=True)
    with np.load(data_path,allow_pickle=False) as a:
        data={k:a[k] for k in a.files}
    source=read(source_run/'PREFIT_RECEIPT.json'); classes=source['fixed']['classes']
    if data['feature_names'].tolist()!=source['fixed']['feature_names']:
        raise ValueError('Source/target predictor names or order differ')
    X,yb=data['X'],data['y_binary']
    if X.ndim!=2 or X.shape[1]!=len(data['feature_names']) or len(yb)!=len(X) or np.isinf(X).any():
        raise ValueError('Invalid external feature matrix')
    if not np.array_equal(np.unique(yb),[0,1]) or len(np.unique(data['group_sha256']))!=len(X):
        raise ValueError('External labels or unique fingerprints invalid')
    normal=classes.index('NormalTraffic'); lateral=classes.index('LateralMovement'); y=np.where(yb==0,normal,lateral)
    group=source_run/'groups/1024/20260921'; lock=read(group/'SELECTION_LOCK.json')
    if lock['execution_binding']!=source['execution_binding']:
        raise ValueError('Source policy lock binding differs')
    policy_map={**lock['choices'],**lock['controls']}
    if not set(policy_map)<=set(POLICIES):
        raise ValueError('Unexpected source policy roster')
    execution={'created_utc':utc_now(),'protocol_hash':canonical_hash(protocol),'source_lock_sha256':sha256_file(group/'SELECTION_LOCK.json'), 'versions':package_versions(),
               'model_hashes':{},'data_sha256':sha256_file(data_path)}
    for cell_id in sorted({v['cell_id'] for v in policy_map.values()}):
        folder=source_run/'cells/1024/20260921'/cell_id
        receipt=read(folder/'FIT_COMPLETE.json'); verify_files(folder,receipt['files'])
        if sha256_file(folder/'FIT_COMPLETE.json')!=lock['fit_complete_sha256'][cell_id]:
            raise ValueError('Source model differs from selected model')
        execution['model_hashes'][cell_id]=sha256_file(folder/'MODEL.joblib')
    immutable_json(out/'PREFLIGHT.json',execution)
    saved={'y_binary':yb,'group_sha256':data['group_sha256'],'classes':np.asarray(classes)}; predictions={}
    for cell_id in execution['model_hashes']:
        model=joblib.load(source_run/'cells/1024/20260921'/cell_id/'MODEL.joblib')
        p=predict(model['classifier'],model['imputer'],X,classes,protocol['cpu_threads'])
        predictions[cell_id]=p; saved[cell_id.replace('/','__')]=p
    np.savez_compressed(out/'PREDICTIONS.npz',**saved)
    metrics={}
    for name in POLICIES:
        if name not in policy_map: continue
        policy=policy_map[name]; p=predictions[policy['cell_id']]; score=1-p[:,normal]
        flags=p.argmax(1)!=normal if policy.get('rule')=='argmax' else score>policy['threshold']
        metrics[name]=alert_metrics(y,score,flags,classes,normal)
    result={'created_utc':utc_now(),'status':'COMPLETE_LIMITED_EXTERNAL_STRESS','source_selection_status':lock['status'],
            'source_budget':1024,'source_seed':20260921,'rows':len(y),'benign_n':int((yb==0).sum()),'lateral_n':int((yb==1).sum()),
            'source_policies':policy_map,'missing_policies':[p for p in POLICIES if p not in policy_map],
            'metrics':metrics,'protocol':protocol,'preflight_sha256':sha256_file(out/'PREFLIGHT.json'),
            'predictions_sha256':sha256_file(out/'PREDICTIONS.npz'),'interpretation':protocol['interpretation']}
    immutable_json(out/'RESULT.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--source-run',type=Path,required=True); parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--out',type=Path); parser.add_argument('--freeze-only',action='store_true'); args=parser.parse_args()
    warnings.filterwarnings('ignore',message='X does not have valid feature names')
    if args.freeze_only:
        immutable_json(args.protocol,specification(args.data,args.source_run)); print('EXTERNAL_PROTOCOL_FROZEN'); return
    if args.out is None: parser.error('--out is required for evaluation')
    result=run(args.data,args.source_run,read(args.protocol),args.out)
    print(result['status'])

if __name__=='__main__': main()
