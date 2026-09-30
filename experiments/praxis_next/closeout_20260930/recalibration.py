"""PX-089: label-availability-qualified thresholds fixed before each capture."""
import time
import numpy as np
from common import *

def eligible(meta,capture,delay_hours,mode,first_start):
    boundary=float(meta['start'][meta['capture']==capture].min())
    cutoff=first_start if mode=='frozen' else boundary
    mask=(meta['capture']<capture)&(meta['end']+delay_hours*3600000<cutoff)
    if mode=='frozen':mask &=meta['capture']==5
    elif mode=='recent' and mask.any():mask &=meta['capture']==meta['capture'][mask].max()
    assert np.all(meta['end'][mask]+delay_hours*3600000<boundary)
    return mask,boundary

def main():
    verify();dest=OUT/'PX089.json';assert not dest.exists();start=time.monotonic()
    ci,ti=identities();meta={k:np.concatenate([ci[k],ti[k]]) for k in ['y','capture','start','end','event_hash']}
    assert len(np.unique(meta['event_hash']))==len(meta['y'])
    caps=np.unique(ti['capture']);first=float(ti['start'][ti['capture']==caps.min()].min());rows=[];checks=1
    for seed in [8101,8102,8103]:
        cal,test=inputs(seed)
        for policy in ['roles_first','harm']:
            p=np.concatenate([policy_prob(cal,policy),policy_prob(test,policy)]);finite(p)
            for delay in [0,24,72]:
                for mode in ['frozen','cumulative','recent']:
                    for cap in caps:
                        mask,boundary=eligible(meta,cap,delay,mode,first);ev=meta['capture']==cap
                        assert not (mask&ev).any();checks+=1
                        for alpha in [.01,.05,.1]:
                            for scope in ['supported_stages','all_stages_fail_closed']:
                                threshold,counts=stage_threshold(p[mask],meta['y'][mask],alpha,scope)
                                pred=wc.apply_gate(p[ev],threshold)
                                rows.append({'seed':seed,'policy':policy,'delay_hours':delay,'mode':mode,'capture':int(cap),'alpha':alpha,'scope':scope,'threshold':threshold,'calibration_counts':counts,'calibration_captures':np.unique(meta['capture'][mask]).tolist(),'max_calibration_label_available':float(np.max(meta['end'][mask]+delay*3600000)) if mask.any() else None,'threshold_frozen_at':boundary,'unsupported_stages':[STAGES[k] for k in [1,2,3] if not counts[k]],**wc.metrics(meta['y'][ev],pred)})
    save(dest,{'rows':rows,'checks':checks,'seconds':time.monotonic()-start,'new_fits':0,'label_delays':'simulated; no actual analyst label-arrival data','deployment_guarantee':False});print('PX089',len(rows),'rows',checks,'checks',flush=True)
if __name__=='__main__':main()
