"""Independent reconstruction of selected host-hour inputs and native labels."""
import csv,hashlib,json,collections
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/vlm_pilots_20261002')
def main():
    d=dict(np.load('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz'))
    truth=json.loads((PRIVATE/'private_truth.json').read_text());names=list(d['feature_names']);checks=0
    selected=[v for v in truth.values() if 'pilot_name' in v]
    for v in selected:
        actual=np.zeros((12,5));peers=[set() for _ in range(12)]
        ix=np.flatnonzero((d['split']==2)&(d['capture']==v['capture'])&(np.floor(d['end']/3600000)==v['hour'])&((d['src']==v['host'])|(d['dst']==v['host'])))
        for i in ix:
            b=int(d['end'][i]//300000)%12;forward=d['src'][i]==v['host'];x=d['current'][i]
            actual[b,0]+=x[names.index('src2dst_bytes' if forward else 'dst2src_bytes')]
            actual[b,1]+=x[names.index('dst2src_bytes' if forward else 'src2dst_bytes')]
            actual[b,2]+=1;actual[b,3]+=x[names.index('dst_dns_service')]
            peers[b].add(d['dst'][i] if forward else d['src'][i])
            assert v['hour']*3600000<=d['end'][i]<(v['hour']+1)*3600000;checks+=1
        actual[:,4]=[len(p) for p in peers]
        expected=np.array(json.loads((PRIVATE/'inputs'/f"{v['pilot_name']}.json").read_text())['values'])
        assert np.array_equal(actual,expected);checks+=60
    inv=json.loads((HERE.parents[2]/'experiments/apt_benchmark/host_history_exfil/PILOT_INPUTS.json').read_text())
    mapping={'Benign':0,'Reconnaissance':1,'Establish Foothold':1,'Cover up':1,'Lateral Movement':2,'Data Exfiltration':3}
    native=collections.Counter();n=0;label_files={}
    for cap in np.unique(d['capture'][d['split']==2]):
        ix=np.flatnonzero((d['split']==2)&(d['capture']==cap));wanted={int(d['source_row'][i]):i for i in ix}
        item=inv['files'][int(cap)];p=Path(inv['private_raw_root'])/item['source_file']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'];label_files[item['source_file']]=item['sha256']
        with p.open(newline='',encoding='utf-8-sig') as f:
            reader=csv.reader(f);cols={s:i for i,s in enumerate(next(reader))}
            for line,row in enumerate(reader,2):
                if line not in wanted:continue
                i=wanted[line];stage=row[-3]
                assert mapping[stage]==d['y'][i]
                assert row[cols['src_ip']]==d['src'][i] and row[cols['dst_ip']]==d['dst'][i]
                assert float(row[cols['bidirectional_last_seen_ms']])==d['end'][i]
                native[stage]+=1;n+=1
    assert n==int((d['split']==2).sum())
    receipt={'status':'PASS','selected_windows_reconstructed':len(selected),'window_checks':checks,'native_rows_verified':n,
        'native_stage_counts':dict(native),'native_files':label_files,
        'population_host_hours':len(truth),'population_exfil_positive_host_hours':sum(v['exfil'] for v in truth.values()),
        'population_exfil_host_hours_missed_base3':sum(v['exfil'] and not v['base'] for v in truth.values()),
        'population_exfil_host_hours_missed_full5':sum(v['exfil'] and not v['full'] for v in truth.values()),
        'cohorts':{g:{'windows':len(z:=[v for v in selected if v['cohort']==g]),'exfil':sum(v['exfil'] for v in z),
        'base_warned':sum(v['base'] for v in z),'full_warned':sum(v['full'] for v in z)} for g in ['representative','diagnostic']},
        'limitations':['Native labels recovered and aligned, but host-time stage scorer and transition baseline still pending','Host-hour warning coverage differs from individual flow detection']}
    (HERE/'INPUT_AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
