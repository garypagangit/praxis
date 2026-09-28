"""Post-result descriptive diagnostics; no refitting or decision changes."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
PRED=Path('C:/w/campaign_validation_20260928/predictions')
freeze=json.loads((ROOT/'FREEZE.json').read_text())
out=[]
for seed in freeze['seeds']:
    d=np.load(PRED/f's{seed}_development_oof.npz')
    r={'seed':seed,'development_oof_rows':len(d['y']),'interpretation':'Descriptive diagnostic after fitting; not a threshold change, tuning exercise or causal explanation.'}
    for objective in ['harm','entropy']:
        t=d[objective+'_target']
        r[objective+'_oof_target']={'positive_fraction':float((t>0).mean()),'negative_fraction':float((t<0).mean()),'zero_fraction':float((t==0).mean()),'mean':float(t.mean())}
    r['held_out']={}
    for n in freeze['test_executions']:
        e=np.load(PRED/f's{seed}_{n}.npz')
        y=e['y']; base=e['p0'].argmax(1); full=e['p1'].argmax(1)
        row={'rows':len(y),'history_changes_argmax':int((base!=full).sum()),
             'history_corrects_error':int(((base!=y)&(full==y)).sum()),
             'history_creates_error':int(((base==y)&(full!=y)).sum())}
        for pol in ['entropy','harm']:
            ac=e[pol+'_action']
            beneficial=(base!=y)&(full==y)
            harmful=(base==y)&(full!=y)
            row[pol]={'acquired':int(ac.sum()),'beneficial_history_rows_acquired':int((ac&beneficial).sum()),
                      'beneficial_history_rows_not_acquired':int((~ac&beneficial).sum()),
                      'harmful_history_rows_acquired':int((ac&harmful).sum())}
        r['held_out'][n]=row
    out.append(r)
(ROOT/'SELECTOR_DIAGNOSTIC.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
