"""Offline statistical anchors; never executes commands or publishes raw records."""
import argparse, collections, hashlib, json, re, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from experiment import FEATURES, META, validate

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def entropy(values):
    p=np.array(list(collections.Counter(values).values()),float); p/=p.sum()
    return float(-(p*np.log2(p)).sum())

def command_stats(commands):
    # Executable vocabulary only. Raw commands, credentials and outputs never leave memory.
    toks=[]
    for c in commands:
        t=re.findall(r'[A-Za-z0-9_./-]+',str(c).strip())
        if t: toks.append(t[0].split('/')[-1].lower())
    if len(toks)<8: return None
    discovery={'ls','find','cat','whoami','id','pwd','uname','hostname','ip','ifconfig','netstat','ss','ps','nmap','env','getent','dir','systeminfo'}
    tools={'nmap','curl','wget','python','python3','ssh','scp','nc','netcat','sqlmap','msfconsole'}
    return [len(set(toks))/len(toks),entropy(list(zip(toks[:-1],toks[1:]))),
            sum(a==b for a,b in zip(toks[:-1],toks[1:]))/(len(toks)-1),
            len(set(toks)&discovery),sum(t in tools for t in toks)/len(toks)]

def build(args):
    out=Path(args.output); out.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(args.seed); manifest=[]; pools={}; exclusions=collections.Counter()
    def record(p,role): manifest.append({'file':p.name,'role':role,'bytes':p.stat().st_size,'sha256':digest(p)})
    human=Path(args.human); record(human,'GAMBiT normalized command archive')
    groups=collections.defaultdict(list)
    for x in json.loads(human.read_text(encoding='utf-8')):
        if str(x['command']).strip().lower() in {'na','nan','','none'}:
            exclusions['human_placeholder_command']+=1; continue
        groups[(x['participant'],x['timestamp'][:10])].append(x)
    hp=[]; gaps=[]
    for entries in groups.values():
        entries.sort(key=lambda x:x['timestamp'])
        times=pd.to_datetime([e['timestamp'] for e in entries],utc=True,errors='coerce',format='mixed')
        exclusions['human_invalid_timestamps']+=int(times.isna().sum())
        times=times.dropna().sort_values()
        g=np.diff(times.astype('int64'))/1e9; gaps.extend(g[(g>0)&(g<=600)].tolist())
        for start in range(0,len(entries)-19,20):
            s=command_stats([e['command'] for e in entries[start:start+20]])
            if s is not None: hp.append(s)
    pools['gambit']=np.array(hp)
    honey=Path(args.honey); record(honey,'Honey for the Agent session archive'); ap=[]
    with zipfile.ZipFile(honey) as z:
        names=sorted(n for n in z.namelist() if n.endswith('.json'))
        selected=rng.choice(len(names),min(1200,len(names)),replace=False)
        for i in selected:
            try:
                turns=json.loads(z.read(names[i])); cmds=[t[2][1] for t in turns[1:] if len(t)>2 and t[2][0]=='raw_command']
                s=command_stats(cmds)
                if s is not None: ap.append(s)
                else: exclusions['honey_short']+=1
            except (ValueError,TypeError,IndexError,KeyError): exclusions['honey_parse']+=1
    pools['honey']=np.array(ap); cp=[]; seen=set()
    for p in sorted(Path(args.cochise).glob('*.json')):
        record(p,'COCHISE current controller trace'); cmds=[]
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            e=json.loads(line)
            if e.get('event')=='tool_call' and e.get('tool_name')=='execute_command': cmds.append(e.get('params',{}).get('command',''))
        key=hashlib.sha256(json.dumps(cmds).encode()).hexdigest()
        if key in seen: exclusions['cochise_duplicate']+=1; continue
        seen.add(key)
        s=command_stats(cmds)
        if s is not None: cp.append(s)
        else: exclusions['cochise_short']+=1
    pools['cochise']=np.array(cp)
    network=[]
    cols=['Protocol','Dst IP','Dst Port','Total Fwd Packet','Total Bwd packets']
    for p in sorted(Path(args.flows).glob('*.csv')):
        record(p,'DAPT flow archive; no operator-origin labels')
        if not set(cols)<=set(pd.read_csv(p,nrows=0).columns):
            exclusions['flow_file_missing_header']+=1; continue
        f=pd.read_csv(p,usecols=cols,nrows=20000)
        for start in range(0,len(f)-63,64):
            w=f.iloc[start:start+64]; fw=w['Total Fwd Packet'].sum(); bw=w['Total Bwd packets'].sum()
            if fw+bw<=0: continue
            network.append([entropy(w.Protocol.tolist()),len(w[['Dst IP','Dst Port']].drop_duplicates()),float(fw/(fw+bw))])
    net=np.array(network); assert len(net)>20 and all(len(p)>10 for p in pools.values())
    # Each arm draws every source equally in expectation. No source gets a class label.
    # Joint resampling preserves within-anchor associations; cross-modal links remain assumed.
    rows=[]; anchor_use=collections.Counter()
    for arm in ['human','autonomous_ai','scripted_control','benign']:
        control=arm in ['scripted_control','benign']; count=2 if control else 20
        for group in range(count):
            effect=rng.normal(0,.025,5)
            for trial in range(20):
                part='control' if control else ('test_unseen' if group>=16 else 'validation' if group>=12 else 'test_seen' if trial>=16 else 'train')
                source=rng.choice(sorted(pools)); anchor_use[(arm,source)]+=1
                h=pools[source][rng.integers(len(pools[source]))].copy()
                h+=effect+rng.normal(0,[.04,.15,.03,.35,.03])
                # Explicit scenario assumptions, NOT estimated human/AI differences.
                if arm=='autonomous_ai': h+=np.array([.045,.12,.025,.35,.025])
                if arm=='scripted_control': h+=np.array([-.12,-.3,.18,-.5,.12])
                if arm=='benign': h+=np.array([.02,-.2,-.02,-1,-.05])
                h[[0,2,4]]=np.clip(h[[0,2,4]],0,1); h[1]=max(0,h[1]); h[3]=max(0,round(h[3]))
                n=net[rng.integers(len(net))].copy()+rng.normal(0,[.03,.5,.015]); n[0]=max(0,n[0]); n[1]=np.clip(round(n[1]),1,64); n[2]=np.clip(n[2],0,1)
                # Human inter-command gaps calibrate scale for BOTH arms; neither is native sensor time.
                delays=rng.choice(gaps,20)*rng.lognormal(0,.25)
                if arm=='autonomous_ai': delays*=.85 if part!='test_unseen' else 1.1
                if arm=='scripted_control': delays=np.full(20,np.median(delays))
                timing=[60/np.mean(delays),np.std(delays)/np.mean(delays),1+int(rng.poisson(.6))]
                x=list(h[:4])+list(n)+timing+[h[4]]
                rows.append(dict(zip(META+FEATURES,[f'gs-{arm}-{group}-{trial}',f'gs-{arm}-{group}',arm,part,'pooled_grounded_simulation','synthetic']+x)))
    df=pd.DataFrame(rows); validate(df); df.to_csv(out/'trials.csv',index=False)
    # Null control retains the same feature table and partitions, assigning random balanced GROUP labels.
    null=df.copy()
    for group_ids in [[f'gs-{a}-{g}' for a in ['human','autonomous_ai'] for g in rg] for rg in [range(12),range(12,16),range(16,20)]]:
        labels=np.array(['human']*(len(group_ids)//2)+['autonomous_ai']*(len(group_ids)//2)); rng.shuffle(labels)
        for gid,label in zip(group_ids,labels): null.loc[null.group_id==gid,'arm']=label
    validate(null); null.to_csv(out/'null_labels.csv',index=False)
    quality={'rows':len(df),'partitions':df.partition.value_counts().to_dict(),'anchor_vectors':{k:len(v) for k,v in pools.items()},'network_blocks':len(net),'human_gap_count':len(gaps),'human_participant_days':len(groups),'excluded':dict(exclusions),'anchor_draws':{f'{a}/{s}':n for (a,s),n in anchor_use.items()},'missing_values':int(df.isna().sum().sum()),'duplicate_feature_rows':int(df[FEATURES].duplicated().sum()),'synthetic_quantiles':df[FEATURES].quantile([.05,.5,.95]).to_dict(),'anchor_command_quantiles':{k:np.quantile(v,[.05,.5,.95],axis=0).tolist() for k,v in pools.items()},'anchor_network_quantiles':np.quantile(net,[.05,.5,.95],axis=0).tolist(),'seed':args.seed}
    for name,obj in [('quality.json',quality),('source_manifest.json',{'generator_sha256':digest(__file__),'inputs':manifest,'output_sha256':{p.name:digest(p) for p in out.glob('*.csv')}})]:
        (out/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:quality[k] for k in ['rows','partitions','anchor_vectors','network_blocks','excluded']}))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--human',required=True); p.add_argument('--honey',required=True); p.add_argument('--cochise',required=True); p.add_argument('--flows',required=True); p.add_argument('--output',required=True); p.add_argument('--seed',type=int,default=20261019); build(p.parse_args())



