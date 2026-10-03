"""Independent reconstruction of selections, warning masks and episode counts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px103_warning_budget_20261003')
rows=json.loads((HERE/'RESULTS.json').read_text());checks=0;explanation_checks=0
for ex in ['UNRAVELED','wilson','harrison']:
    m=dict(np.load(f'C:/w/px094_soc_workload_20261001/{ex}_meta.npz'));y=m['y'];base=m['base_mean'];orr=m['base_OR'];candidate=orr&~base
    keys=list(zip(m['block'],m['src'],m['dst'],np.floor(m['end']/900).astype(int)));unique=sorted(set(keys));lookup={k:i for i,k in enumerate(unique)};gid=np.array([lookup[k] for k in keys]);basecases=set(gid[base])
    for budget in [1,5,20]:
        log=json.loads((OUT/f'{ex}_coverage_b{budget}_s0_explanations.json').read_text());last={};bytime={}
        for c in basecases:
            k=unique[c];bytime.setdefault((k[0],k[-1]),{'baseline':set(),'log':[]})['baseline'].add(k[1])
        for r in log:bytime.setdefault((r['block'],r['bin']),{'baseline':set(),'log':[]})['log'].append(r)
        for (block,binid),batch in sorted(bytime.items()):
            now=(binid+1)*900
            for src in batch['baseline']:last[(block,src)]=now
            for r in batch['log']:
                assert r['release']==now and unique[r['case_id']][1]==r['source']
                assert r['no_warning_preceding_60min']==(now-last.get((block,r['source']),-np.inf)>3600)
                last[(block,r['source'])]=now;explanation_checks+=1
    for r in [a for a in rows if a['execution']==ex]:
        z=np.load(OUT/f"{ex}_{r['method']}_b{r['budget_per_bin']}_s{r['seed']}.npz");chosen=z['chosen'];w=z['warning'];selected=set(chosen)
        expected=base if r['method']=='mean' else orr if r['method']=='OR' else base|(candidate&np.isin(gid,list(basecases|selected)))
        assert np.array_equal(expected,w);assert len(chosen)==r['additional_cases'];assert selected.isdisjoint(basecases)
        if r['method'] not in ['mean','OR']:
            counts={}
            for c in chosen:
                key=(unique[c][0],unique[c][-1]);counts[key]=counts.get(key,0)+1
            assert all(v<=r['budget_per_bin'] for v in counts.values())
        attackcases=set(gid[w&(y>0)]);assert len(selected-attackcases)==r['additional_benign_only_cases']
        exids=sorted(np.flatnonzero(y==y.max()),key=lambda i:(m['block'][i],m['src'][i],m['start'][i],m['end'][i],i))
        groups=[];previous=None
        for i in exids:
            if previous is None or m['block'][i]!=m['block'][previous] or m['src'][i]!=m['src'][previous] or m['start'][i]-m['start'][previous]>r['episode_gap_min']*60:groups.append([])
            groups[-1].append(i);previous=i
        assert len(groups)==r['episodes'];assert sum(bool(w[g].any()) for g in groups)==r['covered'];assert sum(bool(w[g].any() and not base[g].any()) for g in groups)==r['new_episodes'];checks+=1
(HERE/'INDEPENDENT_AUDIT.json').write_text(json.dumps({'status':'PASS','result_cells':checks,'explanation_checks':explanation_checks,'checks':'independent case indexing, saved masks, budget, benign case count, episode coverage, historical source-coverage explanation','scope':'No independent data or actual SOC validation'},indent=2)+'\n')
print('PASS',checks)
