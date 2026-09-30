"""PX-088: separate selection/calibration and retain unresolved review overflow."""
import json,time
import numpy as np
from common import *

def ledger(requested,capture,start,budget):
    served=np.zeros(len(requested),bool);waiting=requested.copy();parts=[]
    for c in np.unique(capture):
        ix=np.flatnonzero(capture==c);order=ix[np.argsort(start[ix],kind='stable')]
        req=order[requested[order]];capacity=int(len(ix)*budget//100000)
        served[req[:capacity]]=True;waiting[req[:capacity]]=False
        assert int(served[ix].sum())<=capacity
        parts.append({'capture':int(c),'rows':len(ix),'capacity':capacity,'requests':len(req),'served':int(served[ix].sum()),'unresolved':int(waiting[ix].sum())})
    assert not (served&waiting).any() and np.array_equal(served|waiting,requested)
    return served,waiting,parts

def main():
    verify();dest=OUT/'PX088.json';assert not dest.exists();t=time.monotonic()
    ci,ti=identities();cy=ci['y'];y=ti['y'];choose=np.array([int(str(h)[0],16)%2==0 for h in ci['event_hash']]);risk=~choose
    assert choose.any() and risk.any() and not (choose&risk).any();rows=[];checks=1
    for seed in [8101,8102,8103]:
        cal,test=inputs(seed)
        for policy in ['roles_first','harm']:
            cp=policy_prob(cal,policy);p=policy_prob(test,policy);finite(cp);finite(p)
            cg=np.maximum(cp[:,0],1-cp[:,0]);g=np.maximum(p[:,0],1-p[:,0])
            for budget in [100,1000,5000]:
                cut=float(np.sort(cg[choose])[int(np.floor(choose.sum()*budget/100000))])
                ca=risk&(cg>=cut);auto=g>=cut;req=~auto
                served,waiting,parts=ledger(req,ti['capture'],ti['start'],budget)
                assert auto.any();checks+=3
                arms=[('selection_only',None,None)] + [(scope,alpha,stage_threshold(cp[ca],cy[ca],alpha,scope)) for scope in ['supported_stages','all_stages_fail_closed'] for alpha in [.01,.05,.1]]
                for scope,alpha,fit in arms:
                    threshold,counts=fit if fit else (None,np.bincount(cy[ca],minlength=4).tolist())
                    pred=p.argmax(1) if threshold is None else wc.apply_gate(p,threshold)
                    mets=wc.metrics(y[auto],pred[auto]);by_stage={}
                    for k,name in enumerate(STAGES[1:],1):
                        m=y==k
                        by_stage[name]={'total':int(m.sum()),'automatic':int((m&auto).sum()),'automatic_misses':int((m&auto&(pred==0)).sum()),'review_requested':int((m&req).sum()),'review_served':int((m&served).sum()),'review_unresolved':int((m&waiting).sum())}
                        assert by_stage[name]['automatic']+by_stage[name]['review_requested']==by_stage[name]['total'];checks+=1
                    rows.append({'seed':seed,'policy':policy,'budget_per_100k':budget,'scope':scope,'alpha':alpha,'confidence_cutoff':cut,'risk_threshold':threshold,'risk_calibration_counts':counts,'unsupported_stages':[STAGES[k] for k in [1,2,3] if not counts[k]],'automatic_metrics':mets,'stage_disposition':by_stage,'review_requests':int(req.sum()),'review_served':int(served.sum()),'review_unresolved':int(waiting.sum()),'benign_review_requests':int((req&(y==0)).sum()),'warning_plus_review_requests':int(((pred>0)&auto).sum()+req.sum()),'capacity_by_capture':parts,'human_accuracy_assumed':False})
    save(dest,{'rows':rows,'checks':checks,'seconds':time.monotonic()-t,'selection_rows':int(choose.sum()),'risk_rows':int(risk.sum()),'new_fits':0,'scope':'Sample-split selective calibration; no SCRC-I theorem or deployment guarantee claimed.'});print('PX088',len(rows),'rows',checks,'checks',flush=True)
if __name__=='__main__':main()
