"""Verify frozen runs using saved groups, original flow rows and a second aggregation path."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px098_local_followup_20261002')
def main():
    result=json.loads((HERE/'RESULTS.json').read_text());parent=pd.read_pickle(OUT/'parents.pkl')
    d=dict(np.load('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz'))
    meta=dict(np.load('C:/w/px094_soc_workload_20261001/UNRAVELED_meta.npz'))
    receipts=json.loads((HERE/'ARTIFACTS.json').read_text())
    for name,h in receipts.items():assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==h
    assert not any(set(d['capture'][d['split']==a])&set(d['capture'][d['split']==b]) for a,b in [(0,1),(0,2),(1,2)])
    names=list(d['feature_names']);svc=sum(d['current'][:,names.index(s)]*v for s,v in [('dst_dns_service',1),('dst_web_service',2),('dst_remote_admin_service',3)])
    protocol=d['current'][:,names.index('protocol')];fwd=d['current'][:,names.index('src2dst_bytes')];back=d['current'][:,names.index('dst2src_bytes')]
    checks=0;details=[]
    with np.load(OUT/'host_hour.npz') as z:
        pure=parent.benign.to_numpy(dtype=bool)[z['pid'][z['flowgid']]]
    for r in result['rows']:
        view=r['view'];z=dict(np.load(OUT/(view+'.npz')));pid=z['pid'];cut=float(z['threshold'])
        maximum=pd.Series(z['scores']).groupby(pid).max().reindex(parent.index).to_numpy()
        assert np.array_equal(maximum,z['parent_scores']);checks+=len(parent)
        cal=(parent.part==1)&parent.benign;test=parent.part==2;bn=test&parent.benign;ex=test&parent.exfil;pw=maximum>=cut
        assert int((pw&cal).sum())==r['calibration_false_alerts']<=int(np.floor(cal.sum()*.01));checks+=1
        for gate in ['base','full']:
            added=pw&~parent[gate].to_numpy();combined=pw|parent[gate].to_numpy()
            assert int((added&bn).sum())==r[gate]['added_benign']
            assert int((added&ex).sum())==r[gate]['added_exfil']
            assert int((combined&ex).sum())==r[gate]['exfil_after'];checks+=3
        # Independent reconstruction for 26 residual flows and 12 deterministic benign controls.
        testix=np.flatnonzero(d['split']==2);miss=testix[(meta['y']==3)&~meta['full_OR']]
        controls=sorted(np.flatnonzero((d['split']==2)&pure),key=lambda i:str(d['group_sha256'][i]))[:12]
        for i in list(miss)+controls:
            j=int(z['flowgid'][i]);p=parent.iloc[int(pid[j])];fine=view.endswith('5min');isolated=view.startswith('peer')
            binid=int(d['end'][i]//300000);hour=binid//12
            mask=(d['split']==d['split'][i])&(d['capture']==d['capture'][i])
            mask&=(np.floor(d['end']/300000)==binid) if fine else (np.floor(d['end']/3600000)==hour)
            a=mask&(d['src']==d['src'][i]);b=mask&(d['dst']==d['src'][i])&(d['src']!=d['dst'])
            if isolated:
                same=(svc==svc[i])&(protocol==protocol[i]);a&=(d['dst']==d['dst'][i])&same;b&=(d['src']==d['dst'][i])&same
            matrix=np.zeros((1 if fine else 12,5));peers=[set() for _ in matrix]
            for reverse,ii in [(False,np.flatnonzero(a)),(True,np.flatnonzero(b))]:
                for k in ii:
                    pos=0 if fine else int(d['end'][k]//300000)%12
                    matrix[pos,0]+=back[k] if reverse else fwd[k];matrix[pos,1]+=fwd[k] if reverse else back[k]
                    matrix[pos,2]+=1;matrix[pos,3]+=d['current'][k,names.index('dst_dns_service')]
                    peers[pos].add(d['src'][k] if reverse else d['dst'][k])
            matrix[:,4]=[len(x) for x in peers]
            assert np.array_equal(matrix,z['raw'][j]);checks+=matrix.size
            assert z['group_end'][j]>d['end'][i];checks+=1
        delays=z['group_end'][z['flowgid'][miss]]-d['end'][miss];warn=z['scores'][z['flowgid'][miss]]>=cut
        assert int(warn.sum())==r['missed_flows_warned_by_own_group'];checks+=1
        details.append({'view':view,'reconstructed_groups':len(miss)+len(controls),'recovered_missed_flows':int(warn.sum())})
    receipt={'status':'PASS','checks':checks,'details':details,'split_capture_overlap':False,'models_fit_in_audit':0,
        'scope':'Separate feature reconstruction and metric implementation; exposed-data validation, not independent campaign evidence'}
    (HERE/'AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
