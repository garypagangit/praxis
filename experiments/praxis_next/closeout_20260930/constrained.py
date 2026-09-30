"""PX-090: six matched binary fits with explicit expert-score semantics."""
import time,warnings
import numpy as np
import joblib,lightgbm
from common import *

def scores(p):return (1-p[[0,1],:,0].astype(float)).T
def stage_prediction(p,warn):
    stage=1+np.mean(p[[0,1],:,1:].astype(float),axis=0).argmax(1)
    return np.where(warn,stage,0)
def main():
    verify();dest=OUT/'PX090.json';assert not dest.exists();start=time.monotonic();ci,ti=identities();rows=[];fits=[];checks=0
    all_eval=np.concatenate([ci['event_hash'],ti['event_hash']])
    grid=np.stack(np.meshgrid(np.linspace(0,1,101),np.linspace(0,1,101),indexing='ij'),-1).reshape(-1,2)
    for seed in [8101,8102,8103]:
        oof=np.load(OLD/f'seed_{seed}/oof_training.npz');assert not np.intersect1d(oof['selection_event_hash'],all_eval).size;assert np.max(oof['capture'])<np.min(ci['capture']);checks+=2
        cal,test=inputs(seed);cp=cal['probabilities'];p=test['probabilities'];cx=scores(cp);x=scores(p);tx=scores(oof['probabilities']);ty=(oof['y']>0).astype(int)
        union=(p[[0,1]].argmax(2)>0).any(0);cu=(cp[[0,1]].argmax(2)>0).any(0)
        arms={'current':(cp[0],p[0]),'roles':(cp[1],p[1])}
        arm_pred={'current':p[0].argmax(1),'roles':p[1].argmax(1),'expert_union':stage_prediction(p,union)}
        for name,constraint in [('unconstrained',[0,0]),('monotone',[1,1])]:
            model=lightgbm.LGBMClassifier(n_estimators=150,num_leaves=15,learning_rate=.05,min_child_samples=10,reg_lambda=1.,n_jobs=2,random_state=seed,verbosity=-1,monotone_constraints=constraint)
            model.fit(tx,ty)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');cs=model.predict_proba(cx)[:,1];s=model.predict_proba(x)[:,1];gs=model.predict_proba(grid)[:,1].reshape(101,101)
            violations=int((np.diff(gs,axis=0)<-1e-12).sum()+(np.diff(gs,axis=1)<-1e-12).sum())
            if name=='monotone':assert violations==0;checks+=1
            fits.append({'seed':seed,'model':name,'training_rows':len(ty),'training_counts':np.bincount(ty).tolist(),'grid_monotonicity_violations':violations})
            joblib.dump(model,OUT/f'px090_{seed}_{name}.joblib')
            arm_pred[name]=stage_prediction(p,s>=.5)
            # Risk calibration needs only the binary warning score; stage refinement remains fixed.
            cprob=np.column_stack([1-cs,cs,np.zeros(len(cs)),np.zeros(len(cs))])
            th,_=stage_threshold(cprob,ci['y'],.05,'supported_stages')
            arm_pred[name+'_calibrated05']=stage_prediction(p,(s>=.5)|(s>=th))
            if name=='monotone':arm_pred['monotone_union_veto']=stage_prediction(p,(s>=.5)|union)
        assert np.all(arm_pred['monotone_union_veto'][union]>0);checks+=1
        for name,pred in arm_pred.items():
            rows.append({'seed':seed,'arm':name,'cost':0 if name=='current' else 1,'expert_evaluations':1 if name in ['current','roles'] else 2,'union_warnings_demoted':int((union&(pred==0)).sum()),'union_attack_warnings_demoted':int((union&(pred==0)&(ti['y']>0)).sum()),**wc.metrics(ti['y'],pred),'per_capture':{str(c):wc.metrics(ti['y'][ti['capture']==c],pred[ti['capture']==c]) for c in np.unique(ti['capture'])}})
    assert len(fits)==6
    save(dest,{'rows':rows,'fits':fits,'checks':checks,'seconds':time.monotonic()-start,'lightgbm_version':lightgbm.__version__,'feature_semantics':['current expert attack score','roles expert attack score'],'adaptation':'Monotone expert-score combination; raw traffic monotonicity not asserted.'});print('PX090',len(rows),'rows',len(fits),'fits',flush=True)
if __name__=='__main__':main()
