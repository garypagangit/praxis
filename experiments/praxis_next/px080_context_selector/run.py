"""PX-080: forward-fitted, stage-cost context selector. See PROTOCOL.md."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

from experiments.apt_benchmark.host_history_exfil.context import history_features

ROOT = Path(__file__).resolve().parent
DATA_SHA = "b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14"
SEEDS = [20260924, 20260925, 20260926]
CLASSES = ["Benign", "OtherAttackStage", "LateralMovement", "DataExfiltration"]
CONDITIONS = ["clean", "missing_half", "missing_all", "stale_5min", "wrong_host"]
ARMS = ["current_roles", "context", "fixed_fusion", "confidence_gate", "ordinary_gate", "stage_harm_gate", "context_dropout"]
COST = np.asarray([1., 1., 4., 4.])
BASE = dict(n_estimators=180, num_leaves=15, learning_rate=.05, min_child_samples=10, reg_lambda=1.)
GATE = dict(n_estimators=120, num_leaves=7, learning_rate=.05, min_child_samples=30, reg_lambda=5.)

def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as stream:
        for b in iter(lambda: stream.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def write(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=False)+"\n", encoding="utf-8")

def utc(): return datetime.now(timezone.utc).isoformat()

def binding():
    dependency = ROOT.parents[1]/"apt_benchmark"/"host_history_exfil"/"context.py"
    return {"files": {str(p.relative_to(ROOT.parents[2])).replace("\\", "/"):sha(p)
                       for p in [ROOT/"PROTOCOL.md", ROOT/"run.py", ROOT/"test_selector.py", dependency]},
            "data_sha256": DATA_SHA, "seeds": SEEDS, "base_parameters": BASE, "selector_parameters": GATE,
            "stage_costs": COST.tolist(), "conditions": CONDITIONS, "arms": ARMS}

def select_rows(d, pool, seed, caps):
    selected=[]
    for k,cap in enumerate(caps):
        rows=pool[d["y"][pool]==k]
        order=sorted(rows, key=lambda i: hashlib.sha256(f"PX080|{seed}|{d['group_sha256'][i]}".encode()).digest())
        selected.extend(order[:cap])
    return np.asarray(selected, dtype=np.int64)

def missing_mask(keys):
    return np.asarray([int(str(k)[:8],16) % 2 == 0 for k in keys])

def history_age(start, latest):
    # No previous event has a separate sentinel age, never a real timestamp.
    return np.where(latest >= 0, np.log1p(np.maximum(start-latest,0)/1000.), 0.)

def observe(d, rows, condition, stale, stale_latest):
    if condition == "wrong_host": h=d["wrong_history"][rows].copy(); latest=d["latest_wrong_history_end"][rows]
    elif condition == "stale_5min": h=stale[rows].copy(); latest=stale_latest[rows]
    else: h=d["history"][rows].copy(); latest=d["latest_history_end"][rows]
    age=history_age(d["start"][rows],latest)
    present=np.ones(len(rows),dtype=float)
    absent=missing_mask(d["group_sha256"][rows]) if condition=="missing_half" else np.full(len(rows),condition=="missing_all")
    h[absent]=0; age[absent]=0; present[absent]=0
    return np.column_stack([h,age,present]), np.column_stack([age,present])

def selector_features(pc, ph, status):
    def summary(p):
        ordered=np.sort(p,axis=1)
        return np.column_stack([ordered[:,-1], ordered[:,-1]-ordered[:,-2], -(p*np.log(np.maximum(p,1e-12))).sum(axis=1)])
    return np.column_stack([pc,ph,ph-pc,summary(pc),summary(ph),status])

def gate_target(y, pc, ph, costs):
    return costs[y]*((ph.argmax(1)!=y).astype(float)-(pc.argmax(1)!=y).astype(float))

def choose(pc, ph, use): return np.where(use[:,None],ph,pc)

def model(seed, gate=False):
    cls=LGBMRegressor if gate else LGBMClassifier
    return cls(**(GATE if gate else BASE),random_state=seed,n_jobs=4,deterministic=True,force_col_wise=True,verbosity=-1)

def fit_experts(d, rows, seed, stale, latest):
    x=np.column_stack([d["current"][rows],d["roles"][rows]])
    h,_=observe(d,rows,"clean",stale,latest)
    a,b=model(seed),model(seed)
    a.fit(x,d["y"][rows]); b.fit(np.column_stack([x,h]),d["y"][rows])
    if not all(np.array_equal(m.classes_,np.arange(4)) for m in [a,b]): raise ValueError("Missing fit class")
    return a,b

def metric(y,p):
    pred=p.argmax(1)
    pr,re,f,s=precision_recall_fscore_support(y,pred,labels=np.arange(4),zero_division=0)
    return {"rows":len(y),"macro_f1":float(f.mean()),"stage_weighted_error":float(np.mean(COST[y]*(pred!=y))),
        "normal_false_attacks":int(np.sum((y==0)&(pred!=0))),
        "movement_any_attack_recall":float(np.mean(pred[y==2]!=0)) if np.any(y==2) else None,
        "confusion":confusion_matrix(y,pred,labels=np.arange(4)).tolist(),
        "classes":{name:{"support":int(s[k]),"precision":float(pr[k]),"recall":float(re[k]),"f1":float(f[k]),
            "ap":float(average_precision_score(y==k,p[:,k])) if np.any(y==k) else None,
            "roc_auc":float(roc_auc_score(y==k,p[:,k])) if len(np.unique(y==k))==2 else None} for k,name in enumerate(CLASSES)}}

def prepare_stale(d):
    names=list(d["feature_names"])
    forward=d["current"][:,names.index("src2dst_bytes")]
    reverse=d["current"][:,names.index("dst2src_bytes")]
    admin=d["current"][:,names.index("dst_remote_admin_service")]
    h,_,latest,_=history_features(d["start"]-300000.,d["end"],d["src"],d["dst"],forward,reverse,admin)
    if not np.all(latest < d["start"]-300000.): raise ValueError("Stale availability violated")
    return h,latest

def run(data, output, freeze_commit):
    frozen=json.loads((ROOT/"FREEZE.json").read_text(encoding="utf-8"))
    if frozen["binding"]!=binding(): raise ValueError("Source binding mismatch")
    if sha(data)!=DATA_SHA: raise ValueError("Input changed")
    if output.exists() and any(output.iterdir()): raise ValueError("Fresh output required")
    output.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    write(output/"STARTED.json",{"utc":utc(),"freeze_commit":freeze_commit,"freeze_sha256":sha(ROOT/"FREEZE.json"),"binding":binding(),
        "versions":{k:importlib.metadata.version(k) for k in ["numpy","lightgbm","scikit-learn"]},"compute":"local CPU","aws_used":False})
    with np.load(data,allow_pickle=False) as z: d={k:z[k] for k in z.files}
    if not (d["end"][d["split"]==0].max()<d["start"][d["split"]==1].min()<d["start"][d["split"]==2].min()): raise ValueError("Split chronology")
    if not np.all(d["latest_history_end"]<d["start"]): raise ValueError("Input availability")
    stale,latest=prepare_stale(d)
    np.savez_compressed(output/"STALE.npz",history=stale,latest=latest)
    test=np.flatnonzero(d["split"]==2); y=d["y"][test]
    xt=np.column_stack([d["current"][test],d["roles"][test]])
    summaries=[]; folds=[]; fits=0
    for seed in SEEDS:
        print(f"SEED {seed}",flush=True)
        sd=output/str(seed); sd.mkdir()
        features=[]; targets=[]; ordinary=[]; meta_rows=[]; meta_conditions=[]; oof_pc=[]; oof_ph=[]
        for capture in range(1,5):
            train_pool=np.flatnonzero((d["split"]==0)&(d["capture"]<capture))
            valid_pool=np.flatnonzero((d["split"]==0)&(d["capture"]==capture))
            if not d["end"][train_pool].max()<d["start"][valid_pool].min(): raise ValueError("Forward fold overlap")
            train=select_rows(d,train_pool,seed,[20000,5000,5000,5000])
            valid=select_rows(d,valid_pool,seed,[12000,5000,5000,5000])
            a,b=fit_experts(d,train,seed,stale,latest); fits+=2
            joblib.dump(a,sd/f"fold{capture}_current.joblib");joblib.dump(b,sd/f"fold{capture}_context.joblib")
            xv=np.column_stack([d["current"][valid],d["roles"][valid]])
            pc=a.predict_proba(xv)
            for ci,c in enumerate(["clean","missing_half","stale_5min"]):
                h,status=observe(d,valid,c,stale,latest); ph=b.predict_proba(np.column_stack([xv,h]))
                features.append(selector_features(pc,ph,status)); targets.append(gate_target(d["y"][valid],pc,ph,COST))
                ordinary.append(gate_target(d["y"][valid],pc,ph,np.ones(4))); meta_rows.append(valid); meta_conditions.append(np.full(len(valid),ci))
                oof_pc.append(pc);oof_ph.append(ph)
            folds.append({"seed":seed,"capture":capture,"fit_rows":len(train),"meta_rows":len(valid),
                "fit_counts":np.bincount(d["y"][train],minlength=4).tolist(),"meta_counts":np.bincount(d["y"][valid],minlength=4).tolist(),
                "max_fit_end":float(d["end"][train].max()),"min_meta_start":float(d["start"][valid].min())})
            np.savez_compressed(sd/f"fold{capture}_rows.npz",fit=train,validation=valid)
            print(f"FOLD {seed} {capture} fit={len(train)} meta={len(valid)}",flush=True)
        gx=np.concatenate(features);gt=np.concatenate(targets);go=np.concatenate(ordinary)
        og,sg=model(seed,True),model(seed,True); og.fit(gx,go);sg.fit(gx,gt); fits+=2
        joblib.dump(og,sd/"ordinary_gate.joblib");joblib.dump(sg,sd/"stage_harm_gate.joblib")
        np.savez_compressed(sd/"OOF.npz",rows=np.concatenate(meta_rows),conditions=np.concatenate(meta_conditions),features=gx,target=gt,ordinary_target=go,
                            current_p=np.concatenate(oof_pc),context_p=np.concatenate(oof_ph))
        train=select_rows(d,np.flatnonzero(d["split"]==0),seed,[20000,5000,5000,5000])
        a,b=fit_experts(d,train,seed,stale,latest);fits+=2
        xf=np.column_stack([d["current"][train],d["roles"][train]])
        hc,_=observe(d,train,"clean",stale,latest); hm,_=observe(d,train,"missing_half",stale,latest)
        drop=model(seed);drop.fit(np.vstack([np.column_stack([xf,hc]),np.column_stack([xf,hm])]),np.tile(d["y"][train],2),sample_weight=np.full(len(train)*2,.5));fits+=1
        for name,m in [("current",a),("context",b),("context_dropout",drop)]:joblib.dump(m,sd/(name+".joblib"))
        np.savez_compressed(sd/"ROWS.npz",fit=train,test=test,y=y,capture=d["capture"][test],src_role=d["src_role"][test],dst_role=d["dst_role"][test])
        pc=a.predict_proba(xt)
        for condition in CONDITIONS:
            h,status=observe(d,test,condition,stale,latest); ph=b.predict_proba(np.column_stack([xt,h]))
            sx=selector_features(pc,ph,status); os=og.predict(sx);ss=sg.predict(sx)
            masks={"confidence_gate":ph.max(1)>pc.max(1),"ordinary_gate":os<0,"stage_harm_gate":ss<0}
            probs={"current_roles":pc,"context":ph,"fixed_fusion":(pc+ph)/2,
                **{k:choose(pc,ph,v) for k,v in masks.items()},"context_dropout":drop.predict_proba(np.column_stack([xt,h]))}
            saved={k:v for k,v in probs.items()};saved.update(ordinary_score=os,stage_harm_score=ss,status=status)
            np.savez_compressed(sd/(condition+".npz"),**saved)
            for arm,p in probs.items():
                r={"seed":seed,"condition":condition,"arm":arm,**metric(y,p)}
                if arm in masks:
                    use=masks[arm];context_wrong=ph.argmax(1)!=y;current_wrong=pc.argmax(1)!=y
                    r["context_selected_fraction"]=float(use.mean())
                    r["selected_context_harm_count"]=int(np.sum(use&context_wrong&~current_wrong))
                    r["selected_context_help_count"]=int(np.sum(use&~context_wrong&current_wrong))
                r["by_capture"]={str(c):metric(y[d["capture"][test]==c],p[d["capture"][test]==c]) for c in np.unique(d["capture"][test])}
                shifted=(d["src_role"][test]==1)&(d["dst_role"][test]==3)
                r["department_to_private_services"]=metric(y[shifted],p[shifted])
                summaries.append(r)
            print(f"EVAL {seed} {condition}",flush=True)
    write(output/"METRICS.json",summaries);write(output/"FOLDS.json",folds)
    write(output/"COMPLETE.json",{"utc":utc(),"elapsed_seconds":time.perf_counter()-start,"fits":fits,"prediction_tables":len(SEEDS)*len(CONDITIONS)*len(ARMS),
        "rows":len(d["y"]),"test_counts":np.bincount(y,minlength=4).tolist(),"input_sha256":DATA_SHA,"source_binding":binding(),"aws_used":False})

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("command",choices=["freeze","run"]);ap.add_argument("--data",type=Path);ap.add_argument("--output",type=Path);ap.add_argument("--freeze-commit")
    args=ap.parse_args()
    if args.command=="freeze": write(ROOT/"FREEZE.json",{"frozen_utc":utc(),"binding":binding()})
    else:
        if not all([args.data,args.output,args.freeze_commit]):ap.error("run requires data, output and freeze-commit")
        with threadpool_limits(limits=4):run(args.data,args.output,args.freeze_commit)
