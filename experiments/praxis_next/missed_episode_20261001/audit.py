"""Independent post-run verification and explicitly post-hoc source detail."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent
D=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
checks=0
def ck(value):
    global checks
    assert value
    checks+=1
def main():
    for p,h in json.loads((H/'FREEZE.json').read_text())['files'].items():ck(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h)
    d=dict(np.load(D));idx=np.flatnonzero(d['split']==2);m=dict(np.load('C:/w/px094_soc_workload_20261001/UNRAVELED_meta.npz'));y=d['y'][idx]
    ck(np.array_equal(d['group_sha256'][idx],m['key']));ex=np.flatnonzero(y==3)
    f=pd.DataFrame({'block':m['block'][ex],'src':m['src'][ex],'start':m['start'][ex],'end':m['end'][ex],'i':ex}).sort_values(['block','src','start','end','i'])
    boundary=(f.block!=f.block.shift())|(f.src!=f.src.shift())|(f.start.diff()>3600)
    groups=[g.i.to_numpy(int) for _,g in f.groupby(boundary.cumsum(),sort=True)]
    rows=list(csv.DictReader((H/'EPISODES.csv').open()));ck(len(rows)==len(groups)==18)
    detail=list(csv.DictReader((H/'MISSED_FLOWS.csv').open()));miss=[]
    old=D.parents[2]/'praxis_next/px081';inputs=[dict(np.load(old/f'seed_{s}/clean_inputs.npz')) for s in [8101,8102,8103]]
    ok=inputs[0]['available'][:,0]&(inputs[0]['delays'][:,0]<=1.0000001)
    p=[np.where(ok[:,None],z['probabilities'][1],z['probabilities'][0]) for z in inputs];p+=[inputs[0]['probabilities'][0],np.where(ok[:,None],np.load('C:/w/px093_heterogeneous_20260930/lr_UNRAVELED.npz')['p'],inputs[0]['probabilities'][0])]
    members=['roles8101','roles8102','roles8103','current','lr'];cn=list(d['feature_names']);x=d['current'];train=np.load('C:/w/px093_heterogeneous_20260930/UNRAVELED_training_indices.npy')
    prior={'5':0,'30':0,'60':0}
    for r,g in zip(rows,groups):
        ck(int(r['exfil_flows'])==len(g));ck((r['full_OR_warned']=='True')==bool(m['full_OR'][g].any()));ck((r['base_OR_warned']=='True')==bool(m['base_OR'][g].any()));ck((r['mean_warned']=='True')==bool(m['base_mean'][g].any()))
        ck(float(r['forward_bytes_total'])==x[idx[g],cn.index('src2dst_bytes')].sum());ck(float(r['reverse_bytes_total'])==x[idx[g],cn.index('dst2src_bytes')].sum())
        for name,prob in zip(members,p):ck(int(r[name+'_warning_flows'])==int((prob[g].argmax(1)>0).sum()))
        ck(float(r['min_member_benign_probability'])==min(float(v[g,0].min()) for v in p))
        if r['full_OR_warned']=='True':continue
        miss.extend(g);t=g[np.argmin(m['start'][g])]
        for w in prior:
            candidate=(m['block']==m['block'][t])&(m['src']==m['src'][t])&m['base_OR']&(m['end']<m['start'][t])&(m['end']>=m['start'][t]-int(w)*60)
            value=bool(candidate.any());ck(value==(r[f'prior_warning_{w}min_at_episode_start']=='True'));prior[w]+=value
        for mode,ti in [('all_fit',np.flatnonzero(d['split']==0)),('capped_fit',train)]:
            support=[]
            for z in idx[g]:
                match=(d['src_role'][ti]==d['src_role'][z])&(d['dst_role'][ti]==d['dst_role'][z])
                for c in ['protocol','dst_remote_admin_service','dst_web_service','dst_dns_service']:match &= x[ti,cn.index(c)]==x[z,cn.index(c)]
                support.append(int(((d['y'][ti]==3)&match).sum()))
            ck(min(support)==int(r[mode+'_exfil_stratum_support_min']));ck(max(support)==int(r[mode+'_exfil_stratum_support_max']))
    ck(len(miss)==12);ck(set(miss)=={int(r['test_row']) for r in detail})
    # Brute-force exact comparison avoids the runner's hash-based candidate lookup.
    full=np.column_stack([x,d['roles']])
    for r in detail:
        z=idx[int(r['test_row'])]
        for name,ti in [('fit',train[d['y'][train]==0]),('test',idx[y==0])]:
            count=int(np.all(full[ti]==full[z],axis=1).sum());ck(count==int(r[name+'_benign_exact_matches']))
    inv=json.loads((H.parents[2]/'experiments/apt_benchmark/host_history_exfil/PILOT_INPUTS.json').read_text());raw=[]
    for cap in np.unique(d['capture'][idx[miss]]):
        wanted={int(d['source_row'][z]):z for z in idx[miss] if d['capture'][z]==cap}
        with (Path(inv['private_raw_root'])/inv['files'][int(cap)]['source_file']).open(newline='',encoding='utf-8-sig') as f:
            reader=csv.reader(f);names=next(reader);pos={s:i for i,s in enumerate(names)}
            for rn,row in enumerate(reader,2):
                if rn not in wanted:continue
                z=wanted[rn];ck(row[-3]=='Data Exfiltration');ck(float(row[pos['bidirectional_packets']])==x[z,cn.index('bidirectional_packets')]);raw.append({'destination_port':int(row[pos['dst_port']]),'packets':int(float(row[pos['bidirectional_packets']])),'signature':row[-1]})
    z=idx[miss];first=z[0];joint=(d['src_role']==d['src_role'][first])&(d['dst_role']==d['dst_role'][first])
    for c in ['protocol','dst_remote_admin_service','dst_web_service','dst_dns_service']:joint &= x[:,cn.index(c)]==x[first,cn.index(c)]
    ck(joint[z].all())
    supplement={'scope':'Post-hoc descriptive source detail; no new efficacy test','unique_missed_source_hosts':len(np.unique(d['src'][z])),'unique_missed_destination_hosts':len(np.unique(d['dst'][z])),'unique_missed_endpoint_pairs':len(set(zip(d['src'][z],d['dst'][z]))),'destination_ports':sorted(set(v['destination_port'] for v in raw)),'source_signatures':sorted(set(v['signature'] for v in raw)),'two_packet_flows':sum(v['packets']==2 for v in raw),'missed_flows':len(miss),'shared_stratum_all_fit_class_counts':np.bincount(d['y'][(d['split']==0)&joint],minlength=4).tolist(),'shared_stratum_capped_fit_class_counts':np.bincount(d['y'][train[joint[train]]],minlength=4).tolist(),'class_order':['benign','other_attack','movement','exfiltration']}
    (H/'SOURCE_DETAIL.json').write_text(json.dumps(supplement,indent=2)+'\n')
    receipt={'status':'PASS','checks':checks,'episode_count':18,'missed_episodes':12,'missed_episode_flows':12,'prior_warning_counts':prior,'scope':'Independent episode/member/support/exact-match checks and source trace; no analyst or incident ground truth'}
    (H/'AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print(json.dumps(supplement,indent=2))
if __name__=='__main__':main()
