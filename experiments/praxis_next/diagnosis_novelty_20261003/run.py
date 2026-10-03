import json,hashlib,sys,time,copy
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def arg(v):return max(range(len(v)),key=lambda i:v[i])
def warn(v):return arg(v)>0
def execute(c,proposal='none'):
    if c['kind']=='aggregation':
        if proposal=='restore':return any(warn(v) for v in c['members'])
        return warn([sum(v[j] for v in c['members'])/len(c['members']) for j in range(len(c['members'][0]))])
    deadline=2. if proposal=='extend_deadline' else c['deadline']
    requested=1 if proposal=='restore' else c['requested']
    delivered=requested==1 and c['delay']<=deadline
    return warn(c['experts'][1 if delivered else 0])
def trace(c):
    if c['kind']=='aggregation':return 'aggregation' if any(warn(v) for v in c['members']) else 'all_silent'
    if c.get('delay') is None:return None
    if not any(warn(v) for v in c['experts']):return 'all_silent'
    return 'deadline' if c['requested']==1 and c['delay']>c['deadline'] else 'selection'
def predict_trace(c,proposal):
    if c['kind']=='aggregation':return any(warn(v) for v in c['members']) if proposal=='restore' else warn([sum(v[j] for v in c['members'])/3 for j in range(len(c['members'][0]))])
    if c.get('delay') is None:return None
    if proposal=='extend_deadline':return False # outside original contract, irrespective of numerical outcome
    use_roles=(proposal=='restore' or c['requested']==1) and c['delay']<=c['deadline']
    return warn(c['experts'][int(use_roles)])
def oracle(c,proposal):
    if c['kind']=='aggregation':
        p=np.array(c['members']);return bool((p.argmax(1)>0).any()) if proposal=='restore' else bool(p.mean(0).argmax()>0)
    if proposal=='extend_deadline':return False
    idx=int((proposal=='restore' or c['requested']==1) and c['delay']<=1)
    return bool(np.argmax(np.array(c['experts'])[idx])>0)
def main():
    if sys.argv[1]=='freeze':
        assert not (HERE/'FREEZE.json').exists();paths=[HERE/'run.py',HERE/'PROTOCOL.md',OLD/'evaluation_identity.npz']+[OLD/f'seed_{s}/clean_inputs.npz' for s in [8101,8102,8103]]
        save(HERE/'FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':{str(p):sha(p) for p in paths}});return
    for p,h in json.loads((HERE/'FREEZE.json').read_text())['files'].items():assert sha(Path(p))==h
    assert not (HERE/'RESULTS.json').exists()
    ident=dict(np.load(OLD/'evaluation_identity.npz'));ps=[np.load(OLD/f'seed_{s}/clean_inputs.npz')['probabilities'] for s in [8101,8102,8103]];ensemble=np.array([p[1] for p in ps],float);experts=ps[2][:2];attack=ident['y']>0
    masks={'aggregation':attack&(ensemble.mean(0).argmax(1)==0)&(ensemble.argmax(2)>0).any(0),'selection':attack&(experts[0].argmax(1)==0)&(experts[1].argmax(1)>0),'all_silent':attack&~(experts.argmax(2)>0).any(0)}
    cases=[];truth=[]
    for cause,mask in masks.items():
        ids=np.flatnonzero(mask);ids=ids[np.argsort(ident['event_hash'][ids],kind='stable')][:64]
        for i in ids:
            for actual in (['selection','deadline'] if cause=='selection' else [cause]):
                c={'id':len(cases),'event_hash':str(ident['event_hash'][i]),'kind':'aggregation' if cause=='aggregation' else 'experts'}
                if cause=='aggregation':c['members']=ensemble[:,i].tolist()
                else:c.update(experts=experts[:,i].tolist(),requested=1 if actual in ['deadline','all_silent'] else 0,delay=1.5 if actual=='deadline' else .25,deadline=1.)
                assert not execute(c);cases.append(c);truth.append(actual)
    records=[]
    for c,gold in zip(cases,truth):
        for method in ['final_only','complete_trace','trace_plus_replay']:
            diagnosis=None if method=='final_only' else trace(c)
            # Replay checks trace diagnosis against actual restoration outcomes.
            if method=='trace_plus_replay':
                if diagnosis in ['aggregation','selection']:assert execute(c,'restore')
                if diagnosis=='deadline':assert not execute(c,'restore') and execute(c,'extend_deadline')
                if diagnosis=='all_silent':assert not execute(c,'restore')
            repairs=[]
            for proposal in ['restore','extend_deadline','none']:
                predicted=None if method=='final_only' else predict_trace(c,proposal) if method=='complete_trace' else (False if c['kind']=='experts' and proposal=='extend_deadline' else execute(c,proposal))
                repairs.append({'proposal':proposal,'predicted_feasible_warning':predicted,'observed_feasible_warning':oracle(c,proposal)})
            records.append({'id':c['id'],'cause':gold,'method':method,'diagnosis':diagnosis,'repairs':repairs})
    pairs=[]
    for i,t in enumerate(truth):
        if t=='selection':
            a=cases[i];b=cases[i+1];assert truth[i+1]=='deadline' and a['experts']==b['experts'] and a['event_hash']==b['event_hash'];pairs.append([a['id'],b['id']])
    summary=[]
    for method in ['final_only','complete_trace','trace_plus_replay']:
        rr=[r for r in records if r['method']==method];repair=[p for r in rr for p in r['repairs']]
        summary.append({'method':method,'cases':len(rr),'correct_diagnosis':sum(r['diagnosis']==r['cause'] for r in rr),'diagnostic_abstentions':sum(r['diagnosis'] is None for r in rr),'repair_proposals':len(repair),'correct_feasibility':sum(p['predicted_feasible_warning'] is not None and p['predicted_feasible_warning']==p['observed_feasible_warning'] for p in repair)})
    controls=0
    for c in cases:
        if c['kind']=='experts':
            cc=copy.deepcopy(c);cc['delay']=None;assert trace(cc) is None and predict_trace(cc,'restore') is None;controls+=1
    save(HERE/'CASES.json',cases);save(HERE/'EVALUATION.json',records);save(HERE/'RESULTS.json',{'summary':summary,'cause_counts':{t:truth.count(t) for t in sorted(set(truth))},'paired_indistinguishable_final_model_evidence':len(pairs),'incomplete_trace_abstention_checks':controls,'unique_event_hashes':len(set(c['event_hash'] for c in cases)),'scope':'Injected mechanisms over exposed real scores; no independent-campaign or SHAP-performance claim'})
    print(json.dumps(json.loads((HERE/'RESULTS.json').read_text()),indent=2))
if __name__=='__main__':main()
