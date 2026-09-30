"""Derive calibration predictions from frozen PX-081 models, without refitting."""
import argparse, importlib.util, hashlib, json, shutil, sys, time
from pathlib import Path
import numpy as np
import joblib
from common import save,replay

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    src=HERE.parent/'px081_evidence_acquisition/run.py'
    spec=importlib.util.spec_from_file_location('px',src);px=importlib.util.module_from_spec(spec);spec.loader.exec_module(px)
    old=px.DEFAULT_OUTPUT; data=dict(np.load(px.DEFAULT_INPUT,allow_pickle=False));sources=[px.DEFAULT_INPUT,src,old/'evaluation_identity.npz']
    assert px.sha(px.DEFAULT_INPUT)==json.loads((src.parent/'FREEZE.json').read_text())['input_sha256']
    checks=0
    for split,code in [('calibration',1),('test',2)]:
        ix=np.flatnonzero(data['split']==code)
        np.savez_compressed(out/(split+'_identity.npz'),y=data['y'][ix],capture=data['capture'][ix],event_hash=data['group_sha256'][ix],start=data['start'][ix],end=data['end'][ix])
    orig=np.load(old/'evaluation_identity.npz'); ti=np.flatnonzero(data['split']==2)
    assert np.array_equal(orig['event_hash'],data['group_sha256'][ti]);checks+=1
    ci=np.flatnonzero(data['split']==1);n=len(ci); t=time.monotonic()
    for seed in px.SEEDS:
        modelpath=old/f'seed_{seed}'/'models.joblib';sources.append(modelpath);models=joblib.load(modelpath)
        for condition in px.CONDITIONS:
            wrong=condition=='wrong_host_history'
            probs=np.stack([px.predict(models['classifiers'][s],px.subset_x(data,ci,s,wrong)) for s in range(4)])
            gains={m:np.full((4,n,2),-np.inf,dtype=np.float32) for m in ['harm','entropy']}
            for state,ch in px.TRANSITIONS:
                x=px.observed_x(data,ci,state,probs[state],wrong)
                for m in gains:gains[m][state,:,ch]=models['selectors'][m,state,ch].predict(x)
            available,delays,order=px.schedule(data['group_sha256'][ci],seed,condition)
            cal=dict(probabilities=probs,available=available,delays=delays,random_order=order,harm_gains=gains['harm'],entropy_gains=gains['entropy'],condition=np.array(condition))
            testpath=old/f'seed_{seed}'/f'{condition}_inputs.npz';sources.append(testpath);test=dict(np.load(testpath));test['condition']=np.array(condition)
            for split,inp in [('calibration',cal),('test',test)]:
                for budget in [1,2,3]:
                    for policy in ['none','roles_first','history_first','entropy','harm']:
                        pp,sp,st=replay(inp,policy,budget)
                        tr=px.replay(policy,{'harm':inp['harm_gains'],'entropy':inp['entropy_gains']},inp['available'],inp['delays'],inp['random_order'],budget,condition)
                        assert np.array_equal(st,tr['state']) and np.array_equal(sp,tr['spent']);checks+=1
                        if split=='test':
                            prevpath=old/f'seed_{seed}'/f'{condition}_b{budget}_{policy}.npz';sources.append(prevpath);prev=np.load(prevpath)
                            assert np.array_equal(pp,prev['probabilities']) and np.array_equal(st,prev['state']);checks+=1
                np.savez_compressed(out/f'{split}_{seed}_{condition}.npz',**inp)
            print('Prepared',seed,condition,flush=True)
    save(out/'PREPARATION.json',{'source_files':[{'name':str(p),'sha256':px.sha(p),'bytes':p.stat().st_size} for p in sorted(set(sources))], 'checks':checks,'new_fits':0,'seconds':time.monotonic()-t,'calibration_counts':np.bincount(data['y'][ci],minlength=4).tolist(),'test_counts':np.bincount(data['y'][ti],minlength=4).tolist()})
    print('PASS',checks,flush=True)
if __name__=='__main__':main()
