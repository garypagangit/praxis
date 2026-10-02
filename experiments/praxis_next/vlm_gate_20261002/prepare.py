"""Build label-free pilot inputs; keep labels and identities outside model bundle."""
import hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = Path('C:/w/vlm_pilots_20261002')
DATA = Path('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz')
METRICS = ['bytes_out', 'bytes_in', 'flows', 'dns_flows', 'peers']
QUESTION = ('Does this host-hour show exfiltration-like behavior? Flow totals are assigned '
            'to their completion bin, not packet times. DNS flows are not DNS queries. '
            'Return only JSON with answer yes, no, or insufficient and a short reason. '
            'There are twelve five-minute bins. Do not assume an anomaly proves exfiltration.')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(p, x):
    Path(p).write_text(json.dumps(x, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def main():
    OUT.mkdir(exist_ok=True)
    bundle = OUT/'inputs'; bundle.mkdir(exist_ok=True)
    d = dict(np.load(DATA)); ix = np.flatnonzero(d['split'] == 2)
    spec = importlib.util.spec_from_file_location('previous', HERE.parent/'heterogeneous_gate_20260930/run.py')
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    v, y, key = previous.inputs('UNRAVELED', 'clean', 2)
    assert np.array_equal(y, d['y'][ix]) and np.array_equal(key, d['group_sha256'][ix])
    warnings = {k: p.argmax(1)>0 for k,p in v.items()}
    base = np.logical_or.reduce([warnings[f'b{s}'] for s in [8101,8102,8103]])
    full = np.logical_or.reduce(list(warnings.values()))
    counts = {k: int(((y==3)&~w).sum()) for k,w in {**warnings,'base3':base,'full5':full}.items()}
    names = list(d['feature_names']); x=d['current'][ix]
    get=lambda name:x[:,names.index(name)]
    frames=[]
    for reverse in [False,True]:
        frames.append(pd.DataFrame({'capture':d['capture'][ix], 'host':d['dst' if reverse else 'src'][ix],
            'peer':d['src' if reverse else 'dst'][ix], 'bin':np.floor(d['end'][ix]/300000).astype(np.int64),
            'bytes_out':get('dst2src_bytes' if reverse else 'src2dst_bytes'),
            'bytes_in':get('src2dst_bytes' if reverse else 'dst2src_bytes'),
            'dns_flows':get('dst_dns_service'), 'flows':1, 'source':not reverse,
            'y':y,'base':base & (not reverse),'full':full & (not reverse),
            'miss':(y==3)&~full & (not reverse)}))
    events=pd.concat(frames,ignore_index=True)
    # Self-loops are represented once; source and destination orientation coincide.
    selfloop=d['src'][ix]==d['dst'][ix]
    if selfloop.any():
        events=events.drop(index=np.flatnonzero(selfloop)+len(ix))
    assert np.isfinite(events[['bytes_out','bytes_in','dns_flows']]).all().all()
    assert (events[['bytes_out','bytes_in','dns_flows']]>=0).all().all()
    agg=events.groupby(['capture','host','bin']).agg(bytes_out=('bytes_out','sum'),bytes_in=('bytes_in','sum'),
        flows=('flows','sum'),dns_flows=('dns_flows','sum'),peers=('peer','nunique')).reset_index()
    events['hour']=events['bin']//12
    candidates=[]; truth={}; arrays={}
    grouped={(int(c),str(h)):g.set_index('bin') for (c,h),g in agg.groupby(['capture','host'])}
    for (cap,host,hour),g in events.groupby(['capture','host','hour']):
        ident=hashlib.sha256(f'PX098:{cap}:{host}:{hour}'.encode()).hexdigest()
        matrix=grouped[int(cap),str(host)].reindex(np.arange(hour*12,hour*12+12))[METRICS].fillna(0).to_numpy()
        arrays[ident]=matrix
        truth[ident]={'capture':int(cap),'host':str(host),'hour':int(hour),
            'exfil':bool(((g.y==3)&g.source).any()),'benign':bool((g.y==0).all()),
            'base':bool(g.base.any()),'full':bool(g.full.any()),'contains_full_miss':bool(g['miss'].any())}
        candidates.append(ident)
    ordered=sorted(candidates)
    representative=ordered[:16]
    diagnostic=[i for i in ordered if truth[i]['contains_full_miss'] and i not in representative][:8]
    requests=[]
    for n,ident in enumerate(representative+diagnostic):
        m=arrays[ident]; name=f'window_{n:03d}'
        fig,axes=plt.subplots(5,1,figsize=(8,8),sharex=True,layout='constrained')
        for j,ax in enumerate(axes):
            ax.bar(np.arange(12)*5+2.5,m[:,j],width=4);ax.set_ylabel(METRICS[j]);ax.set_ylim(bottom=0)
        axes[-1].set_xlabel('Minutes since window start');fig.suptitle('Host traffic: completed-flow totals')
        fig.savefig(bundle/f'{name}.png',dpi=110);plt.close(fig)
        table={'bin_start_minutes':list(range(0,60,5)),'columns':METRICS,'values':m.tolist()}
        save(bundle/f'{name}.json',table)
        for mode in ['image','text']:
            requests.append({'id':name+'_'+mode,'experiment':'PX-098','mode':mode,
                'image':name+'.png' if mode=='image' else None,
                'prompt':QUESTION+ ('\n'+json.dumps(table,separators=(',',':')) if mode=='text' else ''),
                'max_new_tokens':192})
        truth[ident]['pilot_name']=name;truth[ident]['cohort']='representative' if ident in representative else 'diagnostic'
    stage_pages=[]
    for page,cap in enumerate(sorted(agg.capture.unique())[:2]):
        g=agg[agg.capture==cap]
        totals=g.groupby('host').flows.sum().to_dict()
        hosts=sorted(totals,key=lambda h:(-totals[h],hashlib.sha256(h.encode()).hexdigest()))[:8]
        first,last=int(g.bin.min()),int(g.bin.max()); bins=np.arange(first,last+1)
        # Bound smoke-test pages; truncation is explicit, never a whole-campaign claim.
        bins=bins[:144]
        cube=np.stack([grouped[int(cap),str(h)].reindex(bins)[METRICS].fillna(0).to_numpy() for h in hosts])
        name=f'timeline_{page:02d}'
        fig,axes=plt.subplots(5,1,figsize=(12,9),layout='constrained')
        for j,ax in enumerate(axes):
            z=np.log1p(cube[:,:,j])
            im=ax.imshow(z,aspect='auto',interpolation='nearest',origin='lower',cmap='viridis',vmin=0,vmax=max(1.,float(z.max())))
            ax.set_ylabel(METRICS[j]);ax.set_yticks(range(len(hosts)),[f'H{i}' for i in range(len(hosts))]);fig.colorbar(im,ax=ax,label='log(1+value)')
        axes[-1].set_xlabel('Five-minute bin index');fig.suptitle('Traffic timeline: completed-flow totals')
        fig.savefig(bundle/f'{name}.png',dpi=100);plt.close(fig)
        table={'hosts':[f'H{i}' for i in range(len(hosts))],'columns':METRICS,'values':cube.tolist()}
        save(bundle/f'{name}.json',table)
        prompt=('Reconstruct coarse traffic stages from this retrospective timeline. Return JSON with intervals '
                '(host, start_bin, end_bin_exclusive, stage, reason), and an insufficient_evidence boolean. '
                'Supported stages: benign, other_attack, movement, exfiltration. Multiple stages can overlap. '
                f'Only hosts H0 through H{len(hosts)-1} and bins 0 through {len(bins)-1} exist. '
                'Do not force a kill-chain order. Images use log(1+value); text contains raw values. '
                'Each bin is five minutes; DNS flows are not queries. Empty intervals are permitted.')
        for mode in ['image','text']:
            requests.append({'id':name+'_'+mode,'experiment':'PX-099','mode':mode,
                'image':name+'.png' if mode=='image' else None,'prompt':prompt+('\n'+json.dumps(table,separators=(',',':')) if mode=='text' else ''),'max_new_tokens':512})
        stage_pages.append({'page':name,'capture':int(cap),'hosts_displayed':len(hosts),'hosts_total':int(g.host.nunique()),'bins_displayed':len(bins),'bins_total':last-first+1,'native_stage_scoring':'PENDING'})
    save(bundle/'requests.json',requests);save(OUT/'private_truth.json',truth)
    receipt={'status':'INPUTS_PREPARED_NO_INFERENCE','source_sha256':sha(DATA),'test_rows':len(ix),
        'exfil_rows':int((y==3).sum()),'missed_exfil_by_member':counts,'eligible_host_hours':len(candidates),
        'representative_windows':len(representative),'diagnostic_windows':len(diagnostic),'requests':len(requests),
        'representative_exfil_windows':sum(truth[i]['exfil'] for i in representative),
        'stage_pages':stage_pages,'files':{p.name:sha(p) for p in bundle.iterdir() if p.is_file()},
        'checks':['prediction identity and labels aligned','features finite and nonnegative','selection label blind except declared diagnostic cohort',
                  'input windows isolated by capture','all flow completions within assigned window','no raw identities or labels in prompts']}
    save(HERE/'PREPARATION.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='files'},indent=2))

if __name__=='__main__':main()
