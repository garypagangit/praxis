import csv, hashlib, importlib.util, json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATA=Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
META=Path('C:/w/px094_soc_workload_20261001/UNRAVELED_meta.npz')
OLD=Path('C:/w/apt_benchmark_data_20260920/praxis_next/px081')
LR=Path('C:/w/px093_heterogeneous_20260930/lr_UNRAVELED.npz')
INV=ROOT/'experiments/apt_benchmark/host_history_exfil/PILOT_INPUTS.json'
ROLES=['OTHER_ADDRESS','DEPARTMENT','PUBLIC_SERVICES','PRIVATE_SERVICES']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,obj): (HERE/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def writecsv(name,rows):
    with (HERE/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def freeze():
    assert not (HERE/'FREEZE.json').exists()
    files=[DATA,META,LR,LR.parent/'UNRAVELED_training_indices.npy',INV,Path(__file__),HERE/'PROTOCOL.md',HERE.parent/'soc_workload_20261001/PREPARATION.json',HERE.parent/'soc_workload_20261001/RESULTS.json.gz']
    files += [OLD/f'seed_{s}/clean_inputs.npz' for s in [8101,8102,8103]]
    inventory=json.loads(INV.read_text());rawroot=Path(inventory['private_raw_root'])
    for r in inventory['files']:
        p=rawroot/r['source_file'];assert sha(p)==r['sha256'];files.append(p)
    save('FREEZE.json',{'experiment':'PX-095','utc':datetime.now(timezone.utc).isoformat(),'scope':'Exposed-data diagnosis; no fit or efficacy test','files':{str(p):sha(p) for p in files}})
def main():
    assert not (HERE/'EPISODES.csv').exists()
    for p,h in json.loads((HERE/'FREEZE.json').read_text())['files'].items():assert sha(p)==h,p
    d=dict(np.load(DATA));m=dict(np.load(META));ix=np.flatnonzero(d['split']==2);y=d['y'][ix];n=len(ix)
    assert np.array_equal(d['group_sha256'][ix],m['key']) and np.array_equal(y,m['y'])
    prep=json.loads((HERE.parent/'soc_workload_20261001/PREPARATION.json').read_text())[0];assert sha(META)==prep['metadata_sha256']
    seeds=[dict(np.load(OLD/f'seed_{s}/clean_inputs.npz')) for s in [8101,8102,8103]]
    lr=dict(np.load(LR));assert np.array_equal(lr['key'],m['key']) and np.array_equal(lr['y'],y)
    ok=seeds[0]['available'][:,0] & (seeds[0]['delays'][:,0]<=1.0000001)
    ps=np.array([np.where(ok[:,None],z['probabilities'][1],z['probabilities'][0]) for z in seeds]+[seeds[0]['probabilities'][0],np.where(ok[:,None],lr['p'],seeds[0]['probabilities'][0])])
    warns=ps.argmax(2)>0
    assert np.array_equal(warns.any(0),m['full_OR']) and np.array_equal(warns[:3].any(0),m['base_OR'])
    ex=np.flatnonzero(y==3);ordered=sorted(ex,key=lambda i:(m['block'][i],m['src'][i],m['start'][i],m['end'][i],i));eps=[]
    for i in ordered:
        if not eps or m['block'][i]!=m['block'][eps[-1][-1]] or m['src'][i]!=m['src'][eps[-1][-1]] or m['start'][i]-m['start'][eps[-1][-1]]>3600:eps.append([])
        eps[-1].append(i)
    assert len(eps)==18 and sum(not m['full_OR'][e].any() for e in eps)==12
    # Same capped fitting subset as PX-093; validate against saved row indices.
    rng=np.random.default_rng(8101);train=[]
    for k,cap in enumerate([12000,4000,4000,4000]):
        pool=np.flatnonzero((d['split']==0)&(d['y']==k));train.extend(rng.choice(pool,min(cap,len(pool)),replace=False))
    train=np.sort(train);assert np.array_equal(train,np.load(LR.parent/'UNRAVELED_training_indices.npy'))
    names=list(d['feature_names']);cols={k:names.index(k) for k in names};x=d['current'];testx=x[ix]
    sc=['protocol','dst_remote_admin_service','dst_web_service','dst_dns_service']
    strata=np.column_stack([d['src_role'],d['dst_role']]+[x[:,cols[c]] for c in sc])
    training_counts={}
    for mode,idx in [('all_fit',np.flatnonzero(d['split']==0)),('capped_fit',train)]:
        counts={}
        for i in idx:
            key=tuple(strata[i]);counts.setdefault(key,np.zeros(4,int))[d['y'][i]]+=1
        training_counts[mode]=counts
    # Full input equality, not equality of selected display features.
    fullx=np.column_stack([x,d['roles']]);hashes=pd.util.hash_pandas_object(pd.DataFrame(fullx),index=False).to_numpy()
    maps={}
    for name,indices in [('fit',train[d['y'][train]==0]),('test',ix[y==0])]:
        lookup={}
        for i in indices:lookup.setdefault(int(hashes[i]),[]).append(i)
        maps[name]=lookup
    match={}
    missed=np.concatenate([np.array(e) for e in eps if not m['full_OR'][e].any()])
    for i in missed:
        g=ix[i];match[i]={name:sum(np.array_equal(fullx[g],fullx[j],equal_nan=True) for j in lookup.get(int(hashes[g]),[])) for name,lookup in maps.items()}
    # Label-free prior-warning context, same source orientation and capture only.
    context={w:np.zeros(n,bool) for w in [5,30,60]}
    frame=pd.DataFrame({'block':m['block'],'src':m['src']})
    for ids in frame.groupby(['block','src'],sort=False).indices.values():
        times=np.sort(m['end'][ids[m['base_OR'][ids]]]);query=m['start'][ids]
        for w in context:context[w][ids]=np.searchsorted(times,query,side='left')>np.searchsorted(times,query-w*60,side='left')
    records=[];rowdetails=[]
    for j,es in enumerate(eps):
        e=np.array(es);g=ix[e];unwarned=not m['full_OR'][e].any();first=e[np.argmin(m['start'][e])]
        r={'episode':f'E{j+1:02d}','capture':int(d['capture'][g[0]]),'exfil_flows':len(e),'full_OR_warned':not unwarned,'base_OR_warned':bool(m['base_OR'][e].any()),'mean_warned':bool(m['base_mean'][e].any()),'span_seconds':float(m['end'][e].max()-m['start'][e].min()),'destinations':len(np.unique(m['dst'][e])),'src_role':ROLES[int(d['src_role'][g[0]])],'dst_roles':','.join(ROLES[int(k)] for k in np.unique(d['dst_role'][g])),'protocols':','.join(str(int(k)) for k in np.unique(x[g,cols['protocol']])),'forward_bytes_total':float(x[g,cols['src2dst_bytes']].sum()),'reverse_bytes_total':float(x[g,cols['dst2src_bytes']].sum()),'min_member_benign_probability':float(ps[:,e,0].min()),'max_member_attack_probability':float((1-ps[:,e,0]).max()),'fit_benign_exact_match_flows':sum(match.get(int(i),{}).get('fit',0)>0 for i in e) if unwarned else None,'test_benign_exact_match_flows':sum(match.get(int(i),{}).get('test',0)>0 for i in e) if unwarned else None}
        for a,member in enumerate(['roles8101','roles8102','roles8103','current','lr']):r[member+'_warning_flows']=int(warns[a,e].sum())
        for mode,counts in training_counts.items():
            supports=[counts.get(tuple(strata[z]),np.zeros(4,int)) for z in g]
            r[mode+'_exfil_stratum_support_min']=int(min(v[3] for v in supports));r[mode+'_exfil_stratum_support_max']=int(max(v[3] for v in supports))
        for w in context:r[f'prior_warning_{w}min_at_episode_start']=bool(context[w][first])
        records.append(r)
        for i in e:
            if unwarned:rowdetails.append({'episode':r['episode'],'test_row':int(i),'capture':int(d['capture'][ix[i]]),'source_row':int(d['source_row'][ix[i]]),'duration_ms':float(testx[i,cols['bidirectional_duration_ms']]),'packets':float(testx[i,cols['bidirectional_packets']]),'forward_bytes':float(testx[i,cols['src2dst_bytes']]),'reverse_bytes':float(testx[i,cols['dst2src_bytes']]),'fit_benign_exact_matches':match[int(i)]['fit'],'test_benign_exact_matches':match[int(i)]['test'],'min_member_benign_probability':float(ps[:,i,0].min())})
    writecsv('EPISODES.csv',records);writecsv('MISSED_FLOWS.csv',rowdetails)
    profiles=[]
    groups={'missed_episode_exfil':ix[missed],'warned_episode_exfil':ix[np.setdiff1d(ex,missed)],'training_exfil':train[d['y'][train]==3],'test_benign':ix[y==0]}
    for group,ids in groups.items():
        for name in names:
            v=x[ids,cols[name]];q=np.quantile(v,[0,.25,.5,.75,1]);profiles.append({'group':group,'feature':name,'rows':len(ids),'min':q[0],'q25':q[1],'median':q[2],'q75':q[3],'max':q[4]})
    writecsv('FEATURE_PROFILES.csv',profiles)
    # Source-label trace for all test exfiltration flows.
    inv=json.loads(INV.read_text());traced=0
    for cap in np.unique(d['capture'][ix[ex]]):
        wanted={int(d['source_row'][g]):g for g in ix[ex] if d['capture'][g]==cap};item=inv['files'][int(cap)];p=Path(inv['private_raw_root'])/item['source_file']
        with p.open(newline='',encoding='utf-8-sig') as f:
            reader=csv.reader(f);header=next(reader);pos={s:i for i,s in enumerate(header)}
            for rn,row in enumerate(reader,2):
                if rn not in wanted:continue
                g=wanted[rn];assert row[-3]=='Data Exfiltration';assert row[pos['src_ip']]==d['src'][g] and row[pos['dst_ip']]==d['dst'][g];assert float(row[pos['bidirectional_first_seen_ms']])==d['start'][g] and float(row[pos['bidirectional_last_seen_ms']])==d['end'][g];traced+=1
    assert traced==len(ex)
    summary={'experiment':'PX-095','episodes':len(eps),'missed_episodes':12,'exfil_flows':len(ex),'missed_episode_flows':len(missed),'full_OR_unwarned_exfil_flows':int((~m['full_OR'][ex]).sum()),'source_rows_verified':traced,'missed_episode_benign_exact_match_flows':{name:sum(v[name]>0 for v in match.values()) for name in maps},'context':[{'window_minutes':w,'missed_episodes_with_prior_warning':sum(r[f'prior_warning_{w}min_at_episode_start'] for r in records if not r['full_OR_warned']),'benign_test_rows_with_prior_warning':int(context[w][y==0].sum()),'benign_test_rows':int((y==0).sum())} for w in context],'new_fits':0,'cloud_calls':0}
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
    import sys
    freeze() if sys.argv[1]=='freeze' else main()
