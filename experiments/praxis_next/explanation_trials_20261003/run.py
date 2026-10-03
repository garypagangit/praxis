import os
os.environ['OMP_NUM_THREADS']='2'
import json, hashlib, itertools, time, platform, sys
from pathlib import Path
import numpy as np
import joblib

HERE=Path(__file__).resolve().parent
OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
AIT=Path('C:/w/campaign_validation_20260928')
SAVED=Path('C:/w/px093_heterogeneous_20260930')
PRIVATE=Path('C:/w/explanation_trials_20261003')
SEEDS=[8101,8102,8103]
CONDS=['clean','delayed_unavailable','wrong_host_history']
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def read(p):return dict(np.load(p,allow_pickle=False))
def freeze():
    assert not (HERE/'FREEZE.json').exists()
    paths=[HERE/'run.py',HERE/'PROTOCOL.md',DATA,OLD/'evaluation_identity.npz']
    for s in SEEDS:
        paths.append(OLD/f'seed_{s}/models.joblib')
        for c in CONDS:
            paths.append(OLD/f'seed_{s}/{c}_inputs.npz')
            paths += [OLD/f'seed_{s}/{c}_b{b}_{p}.npz' for b in [1,2,3] for p in ['entropy','harm']]
        paths += [AIT/f'predictions/s{s}_{e}.npz' for e in ['wilson','harrison']]
    paths += [SAVED/f'{e}_clean_b2_base3.npz' for e in ['UNRAVELED','wilson','harrison']]
    save(HERE/'FREEZE.json',{'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'exposed-data exploratory follow-up','files':{str(p):sha(p) for p in paths}})
def verify():
    for p,h in json.loads((HERE/'FREEZE.json').read_text())['files'].items():assert sha(p)==h,p
def px100():
    ident=read(OLD/'evaluation_identity.npz');y=ident['y'];n=len(y);rows=[]
    for s in SEEDS:
        for c in CONDS:
            inp=read(OLD/f'seed_{s}/{c}_inputs.npz');available=inp['available'];delays=inp['delays'];p=inp['probabilities']
            for b,pol in itertools.product([1,2,3],['entropy','harm']):
                t=read(OLD/f'seed_{s}/{c}_b{b}_{pol}.npz')
                state=np.zeros(n,np.uint8);attempt=np.zeros(n,np.uint8);cost=np.zeros(n,np.float32);elapsed=cost.copy();invalid=0
                for step in range(2):
                    for g in range(2):
                        ix=np.flatnonzero(t['actions'][:,step]==g)
                        valid=((attempt[ix]&(1<<g))==0)&(cost[ix]+[1,2][g]<=b)&(elapsed[ix]+[.25,.75][g]<=1.0000001)
                        invalid+=int((~valid).sum());attempt[ix]|=1<<g;cost[ix]+=[1,2][g];elapsed[ix]+=delays[ix,g]
                        ok=available[ix,g]&(elapsed[ix]<=1.0000001);state[ix[ok]]|=1<<g
                errors={k:int(np.count_nonzero(np.abs(a.astype(float)-t[k])>1e-6)) for k,a in [('state',state),('attempted',attempt),('spent',cost),('elapsed',elapsed)]}
                pred=p[state,np.arange(n)];errors['probabilities']=int(np.count_nonzero(np.abs(pred-t['probabilities'])>1e-7));errors['invalid_actions']=invalid
                assert sum(errors.values())==0,(s,c,b,pol,errors)
                missed=(y>0)&(pred.argmax(1)==0);recover=(p.argmax(2)>0).any(0)
                rows.append({'seed':s,'condition':c,'budget':b,'policy':pol,'rows':n,'mismatches':errors,'missed_attack_rows':int(missed.sum()),'some_expert_warns':int((missed&recover).sum()),'all_experts_silent':int((missed&~recover).sum())})
            print('trace',s,c,flush=True)
    ensembles=[];cases=[]
    for ex in ['UNRAVELED','wilson','harrison']:
        if ex=='UNRAVELED':
            pp=[read(OLD/f'seed_{s}/clean_inputs.npz')['probabilities'][1] for s in SEEDS];yy=y;keys=ident['event_hash']
        else:
            ds=[read(AIT/f'predictions/s{s}_{ex}.npz') for s in SEEDS];yy=ds[0]['y'];keys=ds[0]['key'];pp=[d['p1'] for d in ds]
            assert all(np.array_equal(yy,d['y']) and np.array_equal(keys,d['key']) for d in ds)
        p=np.array(pp,dtype=np.float64);votes=p.argmax(2)>0;ow=votes.any(0);mw=p.mean(0).argmax(1)>0
        stored=read(SAVED/f'{ex}_clean_b2_base3.npz');assert np.array_equal(ow,stored['OR']>0) and np.array_equal(mw,stored['MEAN']>0)
        lost=ow&~mw;exfil=yy==p.shape[2]-1
        r={'execution':ex,'rows':len(yy),'exfil_support':int(exfil.sum()),'OR_exfil_warned':int((exfil&ow).sum()),'mean_exfil_warned':int((exfil&mw).sum()),'OR_benign_alerts':int(((yy==0)&ow).sum()),'mean_benign_alerts':int(((yy==0)&mw).sum()),'mean_suppressed_attack_warnings':int(((yy>0)&lost).sum()),'all_member_attack_misses':int(((yy>0)&~ow).sum()),'unique_contributor_attack_rows':[int(((yy>0)&votes[j]&(votes.sum(0)==1)).sum()) for j in range(3)],'flipped_output_faults_rejected':len(yy),'missing_member_evidence':'ABSTAIN_REQUIRED'}
        # Exhaustive bit-flip challenge checks supplied claim against trusted scores.
        assert np.all((~ow)!=votes.any(0))
        for name,mask in [('suppressed',lost),('retained',ow&mw),('silent',~ow)]:
            ix=np.flatnonzero(mask);ix=ix[np.argsort(keys[ix].astype(str),kind='stable')][:2]
            for i in ix:cases.append({'execution':ex,'key':str(keys[i]),'category':name,'member_probabilities':p[:,i].tolist(),'mean_warns':bool(mw[i]),'OR_warns':bool(ow[i]),'available_warning_discarded':bool(lost[i])})
        ensembles.append(r)
    save(HERE/'PX100_RESULTS.json',{'trace_cells':rows,'ensembles':ensembles,'recorded_action_replays':sum(r['rows'] for r in rows),'limitation':'Trace replay does not verify selector score generation. Some-expert recoverability ignores delivery constraints.'})
    save(PRIVATE/'review_case_pool.json',cases)
def px101():
    d=read(DATA);test=np.flatnonzero(d['split']==2);ident=read(OLD/'evaluation_identity.npz');assert np.array_equal(d['group_sha256'][test],ident['event_hash'])
    p3=read(OLD/'seed_8103/clean_inputs.npz')['probabilities'][1];pred=p3.argmax(1);y=d['y'][test];keys=d['group_sha256'][test]
    masks={'missed_exfil':(y==3)&(pred==0),'warned_exfil':(y==3)&(pred>0),'correct_benign':(y==0)&(pred==0),'false_alert_benign':(y==0)&(pred>0)}
    selected=[];coh=[]
    for name,mask in masks.items():
        ix=np.flatnonzero(mask);ix=ix[np.argsort(keys[ix],kind='stable')][:128];selected.extend(ix);coh.extend([name]*len(ix))
    selected=np.array(selected);coh=np.array(coh);ix=test[selected];x=np.column_stack([d['current'][ix],d['roles'][ix]]).astype(np.float32)
    names=list(d['feature_names'])+[f'{side}_role_{r}' for side in ['src','dst'] for r in ['other','department','public','private']]
    attrs=[];warn=[];checks=[]
    for s in SEEDS:
        m=joblib.load(OLD/f'seed_{s}/models.joblib')['classifiers'][1].booster_
        p=m.predict(x,num_threads=2);ref=read(OLD/f'seed_{s}/clean_inputs.npz')['probabilities'][1,selected]
        pe=float(np.abs(p-ref).max());assert pe<1e-6
        raw=m.predict(x,raw_score=True,num_threads=2);a=m.predict(x,pred_contrib=True,num_threads=2).reshape(len(x),4,x.shape[1]+1)
        ae=float(np.abs(a.sum(2)-raw).max());assert ae<1e-8
        attrs.append(a[:,0,:-1]-a[:,3,:-1]);warn.append(p.argmax(1)>0);checks.append({'seed':s,'max_saved_probability_error':pe,'max_additivity_error':ae})
        print('SHAP',s,len(x),flush=True)
    attrs=np.array(attrs);warn=np.array(warn);top=np.argsort(-np.abs(attrs),axis=2,kind='stable')[:,:,:5];stats=[]
    for name in masks:
        for i,j in itertools.combinations(range(3),2):
            for agreement in ['all','same_warning','changed_warning']:
                mask=coh==name
                if agreement!='all':mask&=(warn[i]==warn[j]) if agreement=='same_warning' else (warn[i]!=warn[j])
                js=[];sign=[]
                for r in np.flatnonzero(mask):
                    a=set(top[i,r]);b=set(top[j,r]);js.append(len(a&b)/len(a|b));u=sorted(a|b);sign.append(float(np.mean(np.sign(attrs[i,r,u])==np.sign(attrs[j,r,u]))))
                stats.append({'cohort':name,'seeds':[SEEDS[i],SEEDS[j]],'stratum':agreement,'n':len(js),'mean_top5_jaccard':float(np.mean(js)) if js else None,'mean_sign_agreement_on_union':float(np.mean(sign)) if sign else None})
    dominant={name:[{'feature':str(names[k]),'mean_abs_margin_contribution':float(v[k])} for k in np.argsort(-v)[:8]] for name in masks for v in [np.abs(attrs[:,coh==name]).mean((0,1))]}
    np.savez_compressed(PRIVATE/'attributions.npz',test_indices=selected,cohort=coh,attrs=attrs,warnings=warn,feature_names=np.array(names))
    save(HERE/'PX101_RESULTS.json',{'rows':len(x),'cohorts':{n:int((coh==n).sum()) for n in masks},'validation':checks,'stability':stats,'dominant_features':dominant,'interpretation_limit':'Fixed benign-minus-exfil raw margin, not a causal explanation or probability effect; additivity is not sufficient fidelity.'})
def px102():
    pool=json.loads((PRIVATE/'review_case_pool.json').read_text());cases=pool[:12];public=[];answers=[]
    for i,c in enumerate(cases):
        p=c['member_probabilities'];answer=c['available_warning_discarded'];expl=f"{sum(np.argmax(v)>0 for v in p)} of 3 members warn. Mean aggregation {'warns' if c['mean_warns'] else 'is silent'}. OR aggregation {'warns' if c['OR_warns'] else 'is silent'}."
        public.append({'case_id':i+1,'source':c['execution'],'member_probabilities':p,'class_order':['benign','other_attack','movement','exfiltration'] if len(p[0])==4 else ['benign','other_attack','exfiltration'],'explanation':expl,'question':'Does mean aggregation discard a warning available from at least one member?'})
        answers.append({'case_id':i+1,'answer':answer})
    save(HERE/'PX102_CASES.json',public);save(PRIVATE/'PX102_ANSWER_KEY.json',answers)
    save(HERE/'PX102_STATUS.json',{'status':'MATERIALS_PREPARED_NO_HUMAN_RESULTS','cases':len(cases),'participants':0,'assignment':'For participant number p and case c, show explanation iff (p+c)%2==0. Use randomized case order seeded by participant ID.','responses_required':['anonymous_participant_id','case_id','arm','answer','elapsed_seconds','confidence_1_to_5'],'answer_key':str(PRIVATE/'PX102_ANSWER_KEY.json')})
if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    else:
        verify();PRIVATE.mkdir(exist_ok=True);start=time.monotonic();px100();px101();px102();save(HERE/'RUN_RECEIPT.json',{'seconds':time.monotonic()-start,'python':platform.python_version(),'new_fits':0,'aws_jobs':0})
