import csv,hashlib,itertools,json,sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from gate import decide
H=Path(__file__).resolve().parent
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
META=Path('C:/w/px094_soc_workload_20261001/UNRAVELED_meta.npz')
INV=H.parents[2]/'experiments/apt_benchmark/host_history_exfil/PILOT_INPUTS.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,v):(H/name).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def freeze():
    assert not (H/'FREEZE.json').exists()
    paths=[DATA,META,INV,H/'run.py',H/'gate.py',H/'PROTOCOL.md']
    inv=json.loads(INV.read_text())
    for f in inv['files']:
        p=Path(inv['private_raw_root'])/f['source_file'];assert sha(p)==f['sha256'];paths.append(p)
    save('FREEZE.json',{'utc':datetime.now(timezone.utc).isoformat(),'scope':'Post-hoc blanket TCP destination-port 22 replay, no production change','files':{str(p):sha(p) for p in paths}})
def run():
    assert not (H/'RESULTS.json').exists()
    checks=0
    for p,h in json.loads((H/'FREEZE.json').read_text())['files'].items():assert sha(p)==h;checks+=1
    for ml,tcp,port,scope,approved in itertools.product([False,True],repeat=5):
        r=decide(ml,6 if tcp else 17,22 if port else 443,scope,approved);v=tcp and port and scope and not approved
        assert r['policy_violation']==v and r['deny_recommended']==v and r['warning']==(ml or v);checks+=1
    d=dict(np.load(DATA));m=dict(np.load(META));ix=np.flatnonzero(d['split']==2);y=d['y'][ix];n=len(ix);assert np.array_equal(d['group_sha256'][ix],m['key']) and np.array_equal(y,m['y']);checks+=1
    inv=json.loads(INV.read_text());dp=np.full(n,-1,int);protocol=np.full(n,-1,int)
    stages={'Benign':0,'Reconnaissance':1,'Establish Foothold':1,'Cover up':1,'Lateral Movement':2,'Data Exfiltration':3}
    for cap in np.unique(d['capture'][ix]):
        rows=np.flatnonzero(d['capture'][ix]==cap);wanted={int(d['source_row'][ix[i]]):i for i in rows};src=inv['files'][int(cap)]
        with (Path(inv['private_raw_root'])/src['source_file']).open(newline='',encoding='utf-8-sig') as f:
            reader=csv.reader(f);header=next(reader);pos={k:i for i,k in enumerate(header)}
            for rn,row in enumerate(reader,2):
                if rn not in wanted:continue
                i=wanted[rn];assert row[pos['src_ip']]==m['src'][i] and row[pos['dst_ip']]==m['dst'][i];assert float(row[pos['bidirectional_first_seen_ms']])==d['start'][ix[i]] and float(row[pos['bidirectional_last_seen_ms']])==d['end'][ix[i]];assert stages[row[-3]]==y[i]
                dp[i]=int(row[pos['dst_port']]);protocol[i]=int(row[pos['protocol']]);checks+=1
    assert (dp>=0).all();rule=(protocol==6)&(dp==22)
    applied=np.array([decide(bool(m['base_OR'][i]),int(protocol[i]),int(dp[i]),True,False)['warning'] for i in range(n)])
    assert np.array_equal(applied,rule|m['base_OR']);checks+=1
    ex=np.flatnonzero(y==3);f=pd.DataFrame({'block':m['block'][ex],'src':m['src'][ex],'start':m['start'][ex],'end':m['end'][ex],'i':ex}).sort_values(['block','src','start','end','i'])
    boundary=(f.block!=f.block.shift())|(f.src!=f.src.shift())|(f.start.diff()>3600);episodes=[g.i.to_numpy(int) for _,g in f.groupby(boundary.cumsum())];assert len(episodes)==18
    keys=list(zip(m['block'],m['src'],m['dst'],np.floor(m['end']/900).astype(int)));uid,_=pd.factorize(pd.MultiIndex.from_tuples(keys),sort=True)
    base=m['base_OR'];basecases=set(uid[base]);results=[]
    for name,w in [('rule_only',rule),('base_OR',base),('base_OR_plus_rule',applied),('full_OR_plus_rule',m['full_OR']|rule)]:
        cases=set(uid[w]);attack_cases=set(uid[w&(y>0)]);caught=sum(bool(w[e].any()) for e in episodes)
        r={'arm':name,'warning_flows':int(w.sum()),'benign_labeled_warning_flows':int(w[y==0].sum()),'benign_labeled_warning_rate':float(w[y==0].mean()),'exfil_warning_flows':int(w[y==3].sum()),'exfil_total':int((y==3).sum()),'exfil_warning_recall':float(w[y==3].mean()),'episodes_warned':caught,'episodes_total':len(episodes),'grouped_cases':len(cases),'benign_only_warning_cases':len(cases-attack_cases),'extra_warning_flows_vs_base':int((w&~base).sum()),'extra_benign_flows_vs_base':int((w&~base&(y==0)).sum()),'extra_exfil_flows_vs_base':int((w&~base&(y==3)).sum()),'extra_grouped_cases_vs_base':len(cases-basecases),'lost_episodes_vs_base':sum(bool(base[e].any() and not w[e].any()) for e in episodes)}
        # Separate loop reconstructs case accounting without the factorized IDs.
        independent={}
        for i in np.flatnonzero(w):independent[keys[i]]=independent.get(keys[i],False) or bool(y[i]>0)
        assert len(independent)==r['grouped_cases'] and sum(not v for v in independent.values())==r['benign_only_warning_cases'];checks+=2
        if 'plus_rule' in name:assert np.all(w[base]) and np.all(w[rule]);checks+=1
        results.append(r)
    output=Path('C:/w/px096_ssh_policy_20261001');output.mkdir(exist_ok=True);p=output/'DECISIONS.npz';assert not p.exists();np.savez_compressed(p,key=m['key'],y=y,protocol=protocol,destination_port=dp,rule=rule,base_OR=base,base_OR_plus_rule=applied,full_OR_plus_rule=m['full_OR']|rule)
    save('RESULTS.json',results)
    with (H/'RESULTS.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    save('VALIDATION.json',{'status':'PASS','checks':checks,'source_rows_verified':n,'gate_truth_table_cases':32,'decision_path':str(p),'decision_sha256':sha(p),'validation_scope':'Full source mapping, gate truth table, per-row gate equality and alternate grouped-case count; not an independent end-to-end audit','new_fits':0,'production_changes':0})
    print(json.dumps(results,indent=2))
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else run()
