"""Independent case reconstruction and acquisition ceiling; run before future fitting."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
HERE=Path(__file__).parent
PRIVATE=Path('C:/w/px107_aws_pilot')
checks=0;rows=[]
for path,h in json.loads((HERE/'INPUTS.json').read_text()).items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h;checks+=1
for name in ['wilson','harrison']:
    d=np.load(PRIVATE/f'input/eval_{name}.npz')
    m=np.load(f'C:/w/px094_soc_workload_20261001/{name}_meta.npz')
    assert np.array_equal(d['key'],m['key']);checks+=1
    t=pd.DataFrame({'src':m['src'],'dst':m['dst'],'window':np.floor(d['end']/300).astype(np.int64),'case':d['case'],'y':d['y']})
    reconstructed=t.groupby(['src','dst','window'],sort=False).ngroup().to_numpy()
    pairs=pd.DataFrame({'a':reconstructed,'b':d['case']}).drop_duplicates()
    assert pairs['a'].is_unique and pairs['b'].is_unique; checks+=2
    for seed in [8101,8102,8103]:
        p=np.load(PRIVATE/f'input/pred_{seed}_{name}.npz')
        a=np.argmax(p['p0'],axis=1)!=0; b=np.argmax(p['p1'],axis=1)!=0
        t['base']=a;t['extra']=b;t['exfil']=t.y==2
        haswarning=t.groupby(['src','dst','window'],sort=False)['base'].transform('any').to_numpy()
        relevant=t['exfil'].to_numpy()&~haswarning
        eligible=~haswarning
        ep=d['episode'];original=set(ep[a&(ep>=0)].tolist())
        after=set(ep[(a|(eligible&b))&(ep>=0)].tolist())
        all_after=set(ep[(a|b)&(ep>=0)].tolist())
        row={'execution':name,'seed':seed,'rows':len(t),'exfil_rows':int((d['y']==2).sum()),
             'baseline_missed_exfil_rows':int(np.count_nonzero((d['y']==2)&~a)),
             'exfil_rows_in_unwarned_cases':int(relevant.sum()),
             'exfil_rows_recoverable_by_eligible_history':int(np.count_nonzero(relevant&b)),
             'episode_proxies':len(set(ep[ep>=0].tolist())),'baseline_episodes_warned':len(original),
             'eligible_all_history_episodes_warned':len(after),'unrestricted_all_history_episodes_warned':len(all_after),
             'recoverable_previously_unwarned_episodes':len(after-original)}
        assert row['exfil_rows_in_unwarned_cases']==0;checks+=1
        assert row['recoverable_previously_unwarned_episodes']==0;checks+=1
        rows.append(row)
result={'id':'PX-107A','status':'STOP_NO_PRIMARY_ENDPOINT_HEADROOM','audit_checks':checks,'rows':rows,
        'interpretation':'The evaluated current-only models already warn in every exfil episode proxy and every five-minute case containing exfil flows. Retrieval restricted to unwarned cases cannot recover exfil here. This is a dataset/task qualification result, not an XAI-vs-baseline efficacy result.',
        'compute_note':'Ceiling completed after cloud launch. Cloud pilot cancelled before completion; partial selector outputs not treated as comparative results.'}
(HERE/'HEADROOM_AUDIT.json').write_text(json.dumps(result,indent=2))
pd.DataFrame(rows).to_csv(HERE/'HEADROOM_RESULTS.csv',index=False)
print(json.dumps(result,indent=2))
