import csv,hashlib,importlib.util,json,sys,zipfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent;A=Path('C:/w/campaign_validation_20260928');E=H.parent/'campaign_validation_20260928/evidence';P=Path('C:/w/px094_soc_workload_20261001')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(H/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def freeze():
    assert not (H/'FREEZE.json').exists()
    paths=[H/'run.py',H/'PROTOCOL.md',H.parent/'ssh_policy_20261001/gate.py',E/'validate.py',E/'acquire_qualify.py',E/'label_info.txt',E/'ACQUISITION.json',E/'FREEZE.json',H.parent/'soc_workload_20261001/PREPARATION.json']
    receipts={v['execution']:v for v in json.loads((H.parent/'soc_workload_20261001/PREPARATION.json').read_text())};acq={v['file']:v['sha256'] for v in json.loads((E/'ACQUISITION.json').read_text())};af=json.loads((E/'FREEZE.json').read_text())
    for ex in ['wilson','harrison']:
        z=A/f'ait/{ex}_netflows.zip';d=A/f'prepared/{ex}.npz';m=P/f'{ex}_meta.npz'
        assert sha(z)==acq[z.name] and sha(d)==af['prepared_files'][ex] and sha(m)==receipts[ex]['metadata_sha256'];paths.extend([z,d,m])
    save('FREEZE.json',{'utc':datetime.now(timezone.utc).isoformat(),'scope':'Fixed-rule exposed-data transfer; no independent confirmation','files':{str(p):sha(p) for p in paths}})
def run():
    assert not (H/'RESULTS.json').exists()
    for p,h in json.loads((H/'FREEZE.json').read_text())['files'].items():assert sha(p)==h
    sys.path.insert(0,str(E));spec=importlib.util.spec_from_file_location('source',E/'validate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    sys.path.insert(0,str(H.parent/'ssh_policy_20261001'));from gate import decide
    results=[];diagnostics=[];checks=0
    out=Path('C:/w/px097_ssh_transfer_20261001');out.mkdir(exist_ok=True)
    for ex in ['wilson','harrison']:
        d=dict(np.load(A/f'prepared/{ex}.npz'));m=dict(np.load(P/f'{ex}_meta.npz'));raw=mod.read_execution(A/f'ait/{ex}_netflows.zip').set_index(['member','source_row'],verify_integrity=True);r=raw.loc[pd.MultiIndex.from_arrays([d['member'],d['source_row']])].reset_index()
        identity=['udp','cli','srv','cport','sport','start','end','cp','sp','cb','sb'];assert np.array_equal(pd.util.hash_pandas_object(r[identity],index=False).to_numpy(np.uint64),d['key']);assert np.array_equal(d['key'],m['key']) and np.array_equal(d['y'],m['y']);assert np.array_equal(r['label'].map(mod.labels()).to_numpy(),m['y']);assert np.array_equal(r['end'].to_numpy()/1000,m['end']) and np.array_equal(r['start'].to_numpy()/1000,m['start']);assert np.array_equal(r['cli'].to_numpy(str),m['src']) and np.array_equal(r['srv'].to_numpy(str),m['dst']);checks+=5
        dp=r['sport'].to_numpy(int);udp=r['udp'].to_numpy(bool);y=m['y'];n=len(y)
        # Independent direct native-column port recovery.
        native=np.full(n,-1,int);nativeudp=np.zeros(n,bool)
        with zipfile.ZipFile(A/f'ait/{ex}_netflows.zip') as z:
            for member in np.unique(d['member']):
                col='s_port:11' if 'udp' in member else 's_port:16'
                with z.open(member) as f:v=pd.read_csv(f,usecols=[col])[col].to_numpy()
                ix=np.flatnonzero(d['member']==member);native[ix]=v[d['source_row'][ix]];nativeudp[ix]='udp' in member
        assert np.array_equal(native,dp) and np.array_equal(nativeudp,udp);checks+=2
        rule=(~udp)&(dp==22);base=m['base_OR'];hybrid=np.array([decide(bool(base[i]),17 if udp[i] else 6,int(dp[i]),True,False)['warning'] for i in range(n)]);assert np.array_equal(hybrid,base|rule);checks+=1
        ids=np.flatnonzero(y==2);f=pd.DataFrame({'src':m['src'][ids],'start':m['start'][ids],'end':m['end'][ids],'i':ids}).sort_values(['src','start','end','i']);boundary=(f.src!=f.src.shift())|(f.start.diff()>3600);eps=[g.i.to_numpy(int) for _,g in f.groupby(boundary.cumsum())]
        keys=list(zip(m['src'],m['dst'],np.floor(m['end']/900).astype(int)));uid,_=pd.factorize(pd.MultiIndex.from_tuples(keys),sort=True);basecases=set(uid[base])
        for name,w in [('rule_only',rule),('base_OR',base),('base_OR_plus_rule',hybrid),('full_OR',m['full_OR']),('full_OR_plus_rule',m['full_OR']|rule)]:
            cases=set(uid[w]);ac=set(uid[w&(y>0)]);res={'execution':ex,'arm':name,'rows':n,'warning_flows':int(w.sum()),'attack_warning_flows':int(w[y>0].sum()),'exfil_warning_flows':int(w[y==2].sum()),'exfil_total':int((y==2).sum()),'exfil_warning_recall':float(w[y==2].mean()),'benign_warning_flows':int(w[y==0].sum()),'benign_warning_rate':float(w[y==0].mean()),'episodes_warned':sum(bool(w[e].any()) for e in eps),'episodes_total':len(eps),'grouped_cases':len(cases),'benign_only_warning_cases':len(cases-ac),'extra_exfil_flows_vs_base':int((w&~base&(y==2)).sum()),'extra_benign_flows_vs_base':int((w&~base&(y==0)).sum()),'extra_cases_vs_base':len(cases-basecases)}
            independent={}
            for i in np.flatnonzero(w):independent[keys[i]]=independent.get(keys[i],False) or bool(y[i]>0)
            assert len(independent)==res['grouped_cases'] and sum(not v for v in independent.values())==res['benign_only_warning_cases'];checks+=2
            if 'plus_rule' in name:assert np.all(w[base]) and np.all(w[rule]);checks+=1
            results.append(res)
        def ports(mask):
            counts={}
            for u,p in zip(udp[mask],dp[mask]):k=f'{"UDP" if u else "TCP"}/{p}';counts[k]=counts.get(k,0)+1
            return counts
        path=out/f'{ex}.npz';assert not path.exists();np.savez_compressed(path,key=m['key'],y=y,udp=udp,destination_port=dp,rule=rule,base_OR=base,base_OR_plus_rule=hybrid)
        diagnostics.append({'execution':ex,'tcp22_label_counts':np.bincount(y[rule],minlength=3).tolist(),'label_order':['benign','other_attack','exfiltration'],'all_exfil_ports':ports(y==2),'base_missed_exfil_ports':ports((y==2)&~base),'hybrid_missed_exfil_ports':ports((y==2)&~hybrid),'decision_path':str(path),'decision_sha256':sha(path)})
        print('COMPLETE',ex,flush=True)
    save('RESULTS.json',results);save('DIAGNOSTICS.json',diagnostics)
    with (H/'RESULTS.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    save('VALIDATION.json',{'status':'PASS','checks':checks,'scope':'Frozen hashes, full identity/label/time/endpoint alignment, independent raw port recovery, gate equality and alternate case accounting','new_fits':0,'production_changes':0});print(json.dumps(results,indent=2));print(json.dumps(diagnostics,indent=2))
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else run()
