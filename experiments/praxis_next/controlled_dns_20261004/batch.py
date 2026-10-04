"""PX-111: one frozen batch, all outcomes retained, no external confirmation claim."""
import hashlib,json,math,time
from pathlib import Path
import joblib
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from scipy.stats import binomtest

ROOT=Path(__file__).resolve().parent
DATA=Path('C:/w/px110_controlled_dns_20261004_attempt2')
OUT=DATA/'batch';OUT.mkdir(exist_ok=True)
XAI=['A_positive_mass','B_conflicting_mass','C_timing_attribution_change','D_attribution_disagreement','E_attribution_neighbors','F_fidelity_discrepancy']
def threshold(score,budget):
    values=np.r_[np.unique(score),np.nextafter(np.max(score),np.inf)]
    allowed=[t for t in values if int((score>=t).sum())<=budget]
    return float(min(allowed))
def contrib(model,X):return np.asarray(model.booster_.predict(X,pred_contrib=True,num_threads=2))
def probability(model,X):return np.asarray(model.booster_.predict(X,num_threads=2))
def margin(model,X):return np.asarray(model.booster_.predict(X,raw_score=True,num_threads=2))

def main():
    frozen=json.loads((ROOT/'BATCH_FREEZE.json').read_text())
    assert hashlib.sha256((ROOT/'BATCH_PROTOCOL.txt').read_bytes()).hexdigest()==frozen['sha256']
    rows=json.loads((DATA/'cases.json').read_text())
    data={s:[r for r in rows if r['split']==s] for s in ['train','calibration','development']}
    X={s:np.array([r['x'] for r in rs]) for s,rs in data.items()}
    y={s:np.array([r['y'] for r in rs]) for s,rs in data.items()}
    ids={s:np.array([r['id'] for r in rs]) for s,rs in data.items()}
    base=joblib.load(DATA/'lightgbm.joblib'); logistic=joblib.load(DATA/'logistic.joblib')
    trainphi=contrib(base,X['train'])[:,:-1]
    raw_scaler=StandardScaler().fit(X['train']);phi_scaler=StandardScaler().fit(trainphi)
    raw_knn=KNeighborsClassifier(n_neighbors=15).fit(raw_scaler.transform(X['train']),y['train'])
    phi_knn=KNeighborsClassifier(n_neighbors=15).fit(phi_scaler.transform(trainphi),y['train'])
    anomaly=IsolationForest(n_estimators=100,random_state=11101,n_jobs=2).fit(X['train'][y['train']==0])
    models=[base]
    for seed in [11102,11103]:
        m=LGBMClassifier(n_estimators=100,num_leaves=9,learning_rate=.05,random_state=seed,n_jobs=2,verbosity=-1,subsample=.8,subsample_freq=1,colsample_bytree=.8)
        m.fit(X['train'],y['train']);models.append(m)
    donors=np.random.default_rng(11101).choice(len(X['train']),16,replace=False)
    all_scores={}; checks={}
    for s in ['calibration','development']:
        begin=time.perf_counter(); xx=X[s]; phi_full=contrib(base,xx);phi=phi_full[:,:-1];raw=margin(base,xx);p=probability(base,xx)
        checks[s+'_additivity_max_error']=float(np.max(np.abs(phi_full.sum(axis=1)-raw)))
        assert checks[s+'_additivity_max_error']<1e-8
        scores={'confidence':p,'logistic':logistic.predict_proba(xx)[:,1],
                'raw_neighbors':raw_knn.predict_proba(raw_scaler.transform(xx))[:,1],
                'anomaly':-anomaly.score_samples(xx),
                'A_positive_mass':np.maximum(phi,0).sum(axis=1),
                'B_conflicting_mass':np.minimum(np.maximum(phi,0).sum(axis=1),np.maximum(-phi,0).sum(axis=1)),
                'E_attribution_neighbors':phi_knn.predict_proba(phi_scaler.transform(phi))[:,1]}
        ranks=[]
        for col in [0,3,6,7]:
            reference=np.sort(X['train'][y['train']==0,col])
            ranks.append(np.searchsorted(reference,xx[:,col],side='right')/len(reference))
        scores['composite']=np.mean(ranks,axis=0)
        phi_changes=[];p_changes=[]
        for scale in [.8,1.25]:
            probe=xx.copy();probe[:,8:10]*=scale
            pp=contrib(base,probe)[:,:-1]
            phi_changes.append(np.abs(pp-phi).sum(axis=1)/(1+np.abs(phi).sum(axis=1)))
            p_changes.append(np.abs(probability(base,probe)-p))
        scores['C_timing_attribution_change']=np.mean(phi_changes,axis=0)
        scores['timing_prediction_change']=np.mean(p_changes,axis=0)
        phis=np.stack([contrib(m,xx)[:,:-1] for m in models]);probs=np.stack([probability(m,xx) for m in models])
        scores['D_attribution_disagreement']=phis.var(axis=0).mean(axis=1)
        scores['ensemble_probability_variance']=probs.var(axis=0)
        scores['ensemble_probability_mean']=probs.mean(axis=0)
        discrepancies=[];responses=[]
        for group in [np.arange(8),np.arange(8,10)]:
            probe=np.repeat(xx,16,axis=0)
            probe[:,group]=np.tile(X['train'][donors][:,group],(len(xx),1))
            actual=(margin(base,probe)-np.repeat(raw,16)).reshape(len(xx),16)
            suggested=trainphi[donors][:,group].sum(axis=1)[None,:]-phi[:,group].sum(axis=1)[:,None]
            discrepancies.append((np.abs(actual-suggested)/(1+np.abs(actual))).mean(axis=1))
            responses.append(np.abs(actual).mean(axis=1))
        scores['F_fidelity_discrepancy']=np.mean(discrepancies,axis=0)
        scores['group_prediction_change']=np.mean(responses,axis=0)
        assert all(np.isfinite(v).all() for v in scores.values())
        all_scores[s]=scores
        print(s,'all methods scored',round(time.perf_counter()-begin,2),'seconds',flush=True)
    anchor_tau=threshold(all_scores['calibration']['confidence'],math.ceil(.05*len(y['calibration'])))
    anchor={s:all_scores[s]['confidence']>=anchor_tau for s in all_scores}
    tables=[];gate_tables=[];selection={};gate_selection={};controls=[]
    taus={}
    for s,scores in all_scores.items():
        eligible=np.flatnonzero(~anchor[s]);budget=math.ceil(.05*len(eligible));selection[s]={};gate_selection[s]={}
        for name,score in scores.items():
            chosen=eligible[np.lexsort((ids[s][eligible],-score[eligible]))[:budget]]
            mask=np.zeros(len(score),bool);mask[chosen]=True;selection[s][name]=mask
            common={'split':s,'method':name,'added_capacity':budget,'anchor_transfers':int(y[s][anchor[s]].sum()),'anchor_cases':int(anchor[s].sum()),'eligible_missed_transfers':int(y[s][eligible].sum())}
            tables.append(dict(common,added_transfers=int(y[s][chosen].sum()),added_benign=int((1-y[s][chosen]).sum()),added_reviews=len(chosen)))
            if s=='calibration':taus[name]=threshold(score[eligible],budget)
            candidates=eligible[score[eligible]>=taus[name]];admitted=candidates[:budget]
            mask=np.zeros(len(score),bool);mask[admitted]=True;gate_selection[s][name]=mask
            gate_tables.append(dict(common,added_transfers=int(y[s][admitted].sum()),added_benign=int((1-y[s][admitted]).sum()),added_reviews=len(admitted),overflow=max(0,len(candidates)-budget),threshold=taus[name]))
            if name in XAI:
                shuffled=np.random.default_rng(11199).permutation(score)
                chosen=eligible[np.lexsort((ids[s][eligible],-shuffled[eligible]))[:budget]]
                controls.append({'split':s,'method':name,'shuffled_added_transfers':int(y[s][chosen].sum())})
    stats={}
    for kind,table,selected in [('ranking',tables,selection),('gate',gate_tables,gate_selection)]:
        candidates=[r for r in table if r['split']=='calibration' and r['method'] not in XAI]
        winner=sorted(candidates,key=lambda r:(-r['added_transfers'],r['added_benign'],r['method']))[0]['method']
        reference=selected['development'][winner];comparisons=[]
        for name in XAI:
            mask=selected['development'][name];positive=y['development']==1
            wins=int((mask&~reference&positive).sum());losses=int((~mask&reference&positive).sum())
            pvalue=binomtest(wins,wins+losses,.5,alternative='greater').pvalue if wins+losses else 1.
            comparisons.append({'method':name,'extra_vs_selected_baseline':wins-losses,'discordant_wins':wins,'discordant_losses':losses,'bonferroni_p':min(1.,6*pvalue)})
        stats[kind]={'calibration_selected_baseline':winner,'comparisons':comparisons}
    result={'experiment':'PX-111','status':'EXPLORATORY_BATCH_COMPLETE_EXTERNAL_RECOVERY_NOT_VALIDATED',
            'anchor_threshold':anchor_tau,'ranking':tables,'gates':gate_tables,'shuffled_controls':controls,'comparisons':stats,'checks':checks,
            'external_stage':'AIT_RECORDED_LAB_NO_HEADROOM_FOR_EXISTING_ENDPOINT',
            'no_production_or_human_claim':True,'aws_spend_usd':0}
    (ROOT/'BATCH_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'scores.json').write_text(json.dumps({s:{k:v.tolist() for k,v in d.items()} for s,d in all_scores.items()}))
    (OUT/'thresholds.json').write_text(json.dumps({'anchor':anchor_tau,'referrals':taus},indent=2))
    print(json.dumps({'comparisons':stats,'development_ranking':[r for r in tables if r['split']=='development'],'development_gates':[r for r in gate_tables if r['split']=='development']},indent=2))

if __name__=='__main__':main()
