"""PX-119 reproducible argument-count diagnostic. Commands remain inert text.

Sections: input validation; representations; fitting/calibration; evaluation;
frozen-model stress test. Run --help for portable input and output paths.
"""
import argparse, collections, hashlib, json, time
from pathlib import Path
import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score

def weights(rows):
    """Give each class equal mass and each group equal mass within class."""
    counts=collections.Counter((r['label'],r['group']) for r in rows)
    groups=collections.Counter(y for y,g in counts)
    return np.array([len(rows)/(2*groups[r['label']]*counts[r['label'],r['group']]) for r in rows])

def features(rows,kind):
    """Remove argument identities; distinguish count and count-free controls."""
    if kind=='one_marker':
        return [' '.join(c.split()[0]+' ARG' for c in r['commands']) for r in rows]
    a=np.array([[len(c.split())-1 for c in r['commands']] for r in rows],dtype=float)
    if kind=='argument_counts':return a
    return np.c_[a.mean(1),a.std(1),a.max(1),(a==0).mean(1)]

def evaluate(rows,scores,threshold):
    """Report window confusion counts and equally weighted human-group error."""
    y=np.array([r['label'] for r in rows]);pred=np.asarray(scores)>=threshold
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    groups=collections.defaultdict(list)
    for r,v in zip(rows,pred):
        if r['label']==0:groups[r['group']].append(float(v))
    return dict(tp=int(tp),fn=int(fn),fp=int(fp),tn=int(tn),
        agent_recall=float(tp/(tp+fn)) if tp+fn else None,
        human_group_mean_fpr=float(np.mean([np.mean(v) for v in groups.values()])) if groups else None,
        human_groups=len(groups),auroc=float(roc_auc_score(y,scores)) if len(set(y))==2 else None)

def main():
    # Inputs use the existing qualified records and original split identities.
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True,help='PX-118 private input folder')
    ap.add_argument('--masked-model',type=Path,required=True,help='Trusted PX-118 masked.joblib only')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();d=json.loads((args.data/'records.json').read_text())
    lookup={r['id']:r for r in d['rows']+d['external']}
    p=json.loads((args.data/'base_predictions.json').read_text())
    f,c,t=[[lookup[r['id']] for r in p[k]] for k in ['fit','calibration','test']]
    for a,b in [(f,c),(f,t),(c,t)]:
        assert not {r['group'] for r in a}&{r['group'] for r in b}
        assert not {r['fingerprint'] for r in a}&{r['fingerprint'] for r in b}
    assert all(len(r['commands'])==10 for r in f+c+t)
    seen={r['fingerprint'] for r in f+c}
    external={k:[r for r in json.loads((args.data/('external_'+k+'.json')).read_text()) if r['fingerprint'] not in seen] for k in ['kypo','rouxii']}
    results=[]
    for kind in ['argument_counts','argument_summary','one_marker']:
        # Fit once, using only original fitting rows; no hyperparameter search.
        transform=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,max_features=20000) if kind=='one_marker' else StandardScaler()
        m=make_pipeline(transform,LogisticRegression(C=1,max_iter=2000,random_state=11703))
        m.fit(features(f,kind),[r['label'] for r in f],logisticregression__sample_weight=weights(f))
        # Freeze a threshold on calibration humans before reading test metrics.
        pc=m.predict_proba(features(c,kind))[:,1];human=np.array([r['label']==0 for r in c]);w=weights(c)
        candidates=np.unique(np.r_[pc.min()-1,pc[human],np.nextafter(pc[human],np.inf),pc.max()+1])
        threshold=next(float(q) for q in candidates if np.average(pc[human]>=q,weights=w[human])<=.05)
        evidence={'fit_ids':[r['id'] for r in f]};result={'model':kind,'threshold':threshold}
        for name,rows in dict(calibration=c,test=t,**external).items():
            scores=m.predict_proba(features(rows,kind))[:,1]
            result[name]=evaluate(rows,scores,threshold)
            evidence[name]=[dict(id=r['id'],label=r['label'],group=r['group'],score=float(s)) for r,s in zip(rows,scores)]
        (args.output/(kind+'_predictions.json')).write_text(json.dumps(evidence,indent=2))
        joblib.dump(dict(model=m,kind=kind,threshold=threshold),args.output/(kind+'.joblib'))
        results.append(result)
    # Apply equalized counts to the original masked model without retraining.
    b=joblib.load(args.masked_model);m=b['model'];threshold=b['threshold']
    original=[' '.join(' '.join([cmd.split()[0]]+['ARG']*(len(cmd.split())-1)) for cmd in r['commands']) for r in t]
    ps=m.predict_proba(original)[:,1];stress=m.predict_proba(features(t,'one_marker'))[:,1]
    families={fam:evaluate([r for r in t if r['family']==fam],[s for r,s in zip(t,ps) if r['family']==fam],threshold) for fam in sorted({r['family'] for r in t if r['label']==1})}
    report=dict(experiment='PX-119',scope='EXPOSED_DATA_DEVELOPMENT_ONLY',results=results,
        frozen_masked_original=evaluate(t,ps,threshold),frozen_masked_equalized=evaluate(t,stress,threshold),
        stress_flip_rate=float(np.mean((ps>=threshold)!=(stress>=threshold))),masked_error_by_family=families,
        seconds=time.monotonic()-start,input_hashes={n:hashlib.sha256((args.data/n).read_bytes()).hexdigest() for n in ['records.json','base_predictions.json','external_kypo.json','external_rouxii.json']})
    (args.output/'RESULTS.json').write_text(json.dumps(report,indent=2))
    (args.output/'stress_predictions.json').write_text(json.dumps([dict(id=r['id'],label=r['label'],group=r['group'],original=float(s),equalized=float(z)) for r,s,z in zip(t,ps,stress)],indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
