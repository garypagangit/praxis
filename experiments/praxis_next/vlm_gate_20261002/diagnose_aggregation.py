"""Posthoc descriptive contribution of missed flows to rendered byte totals."""
import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def main():
    p=Path('C:/w/vlm_pilots_20261002');truth=json.loads((p/'private_truth.json').read_text())
    d=dict(np.load('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz'))
    m=dict(np.load('C:/w/px094_soc_workload_20261001/UNRAVELED_meta.npz'));ix=np.flatnonzero(d['split']==2)
    assert np.array_equal(d['group_sha256'][ix],m['key'])
    out=d['current'][ix,list(d['feature_names']).index('src2dst_bytes')];rows=[]
    for v in truth.values():
        if v.get('cohort')!='diagnostic':continue
        f=(d['capture'][ix]==v['capture'])&(d['src'][ix]==v['host'])&(np.floor(d['end'][ix]/3600000)==v['hour'])&(d['y'][ix]==3)&~m['full_OR']
        a=np.array(json.loads((p/'inputs'/(v['pilot_name']+'.json')).read_text())['values'])
        total=float(a[:,0].sum());missing=float(out[f].sum())
        rows.append({'window':v['pilot_name'],'full_gate_missed_exfil_flows':int(f.sum()),
            'missed_exfil_source_to_destination_bytes':missing,'all_host_outgoing_bytes':total,
            'missed_flow_outgoing_byte_share':missing/total if total else None})
    (HERE/'AGGREGATION_DIAGNOSTIC.json').write_text(json.dumps({'scope':'Posthoc descriptive byte contribution; not a causal explanation or a new efficacy test','windows':rows},indent=2)+'\n')
if __name__=='__main__':main()
