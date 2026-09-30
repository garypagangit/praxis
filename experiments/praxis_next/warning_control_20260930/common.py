"""PX-085--087: CPU-only warning replay; no model fitting or model APIs."""
import json
from pathlib import Path
import numpy as np

STAGES = ['benign', 'other_attack', 'movement', 'exfiltration']
ALPHAS = [.01, .02, .05, .10]
COST = np.array([1., 2.])
NOMINAL = np.array([.25, .75])

def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def threshold(scores, alpha):
    """Warning iff attack score >= t. Ties warn. Empty/too-small sets warn all.

    k=floor(alpha*(n+1)); kth smallest score has P(new score < t)<=k/(n+1)
    under exchangeability. Equivalent bounded binary-loss CRC correction.
    This is a marginal expectation claim, not a realized-test upper bound.
    """
    scores=np.asarray(scores, dtype=np.float64)
    assert np.all(np.isfinite(scores)) and np.all((scores>=0)&(scores<=1))
    n=len(scores); k=int(np.floor(alpha*(n+1)))
    if not n or k<1: return 0.
    return float(np.partition(scores, k-1)[k-1])

def metrics(y, pred, spent=None):
    cm=np.bincount(y*4+pred, minlength=16).reshape(4,4)
    support=cm.sum(1); den=support+cm.sum(0)
    result={'n':len(y), 'macro_f1':float(np.divide(2*cm.diagonal(),den,out=np.zeros(4),where=den>0).mean()),
        'false_alerts':int(cm[0,1:].sum()), 'benign_fpr':float(cm[0,1:].sum()/support[0]) if support[0] else None,
        'warnings_per_100k':float((pred>0).mean()*100000), 'confusion':cm.tolist()}
    if spent is not None: result['mean_spend']=float(np.mean(spent))
    for k,name in enumerate(STAGES[1:],1):
        result[name]={'support':int(support[k]),'missed':int(cm[k,0]),
          'miss_rate':float(cm[k,0]/support[k]) if support[k] else None,
          'warning_recall':float(1-cm[k,0]/support[k]) if support[k] else None,
          'exact_recall':float(cm[k,k]/support[k]) if support[k] else None}
    return result

def apply_gate(p,t):
    # Preserve every original warning. Additional warning stages use largest attack probability.
    pred=p.argmax(1)
    warn=(1-p[:,0].astype(np.float64))>=t
    promoted=(pred==0)&warn
    pred[promoted]=1+p[promoted,1:].argmax(1)
    return pred

def gates(cp,cy,p,y,spent,meta,capture):
    rows=[]; score=1-cp[:,0].astype(np.float64)
    for alpha in ALPHAS:
        ts={STAGES[k]:threshold(score[cy==k],alpha) for k in [1,2,3]}
        missing=[STAGES[k] for k in [1,2,3] if not (cy==k).any()]
        for scope in ['pooled_attack','supported_stages','all_stages_fail_closed']:
            if scope=='pooled_attack': t=threshold(score[cy>0],alpha)
            elif scope=='supported_stages': t=min((ts[STAGES[k]] for k in [1,2,3] if (cy==k).any()),default=0.)
            else: t=min(ts.values())
            pred=apply_gate(p,t)
            rows.append({**meta,'alpha':alpha,'scope':scope,'threshold':t,'stage_thresholds':ts,
              'unsupported_calibration_stages':missing,'deployment_guarantee_claimed':False,
              **metrics(y,pred,spent),'per_capture':{str(c):metrics(y[capture==c],pred[capture==c]) for c in np.unique(capture)}})
    return rows

def replay(inp,policy,budget,stop=None):
    probs=inp['probabilities']; n=probs.shape[1]; ar=np.arange(n)
    state=np.zeros(n,np.uint8); attempted=np.zeros(n,np.uint8); spent=np.zeros(n,np.float32); elapsed=np.zeros(n,np.float32)
    stopped=np.zeros(n,bool)
    prior=np.array([.8,.65]) if str(inp['condition'])=='delayed_unavailable' else np.ones(2)
    for step in range(2):
        if stop is not None: stopped |= (1-probs[state,ar,0].astype(np.float64))>=stop
        eligible=np.stack([((attempted&(1<<g))==0)&(spent+COST[g]<=budget)&(elapsed+NOMINAL[g]<=1+1e-7)&~stopped for g in range(2)],axis=1)
        if policy=='none': scores=np.full((n,2),-np.inf)
        elif policy=='roles_first': scores=np.broadcast_to([2.,1.],(n,2)).copy()
        elif policy=='history_first': scores=np.broadcast_to([1.,2.],(n,2)).copy()
        else: scores=inp[policy+'_gains'][state,ar]*prior/COST
        scores=np.where(eligible,scores,-np.inf); ch=scores.argmax(1); best=scores.max(1)
        ids=np.flatnonzero(np.isfinite(best)&(best>0)); g=ch[ids]
        attempted[ids]|=(1<<g).astype(np.uint8); spent[ids]+=COST[g]; elapsed[ids]+=inp['delays'][ids,g]
        arrive=inp['available'][ids,g]&(elapsed[ids]<=1+1e-7)
        state[ids[arrive]]|=(1<<g[arrive]).astype(np.uint8)
    return probs[state,ar],spent,state

def reachable(inp,budget):
    n=inp['probabilities'].shape[1]; result=np.zeros((4,n),bool);result[0]=True
    for plan in [(0,),(1,),(0,1),(1,0)]:
        state=np.zeros(n,np.uint8);spent=np.zeros(n);elapsed=np.zeros(n);alive=np.ones(n,bool)
        for g in plan:
            go=alive&(spent+COST[g]<=budget)&(elapsed+NOMINAL[g]<=1+1e-7);alive &=go
            spent[go]+=COST[g];elapsed[go]+=inp['delays'][go,g]
            arrive=go&inp['available'][:,g]&(elapsed<=1+1e-7);state[arrive]|=1<<g
        result[state,np.arange(n)]=True
    return result
