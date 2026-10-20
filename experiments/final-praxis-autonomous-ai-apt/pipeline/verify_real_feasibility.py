"""Verify public aggregate feasibility artifacts; no raw records needed."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from grounded_synthetic import digest
p=Path(__file__).parent
out=p/'real_feasibility_20261020'
d=pd.read_csv(out/'scores.csv');s=pd.read_csv(out/'summary.csv');a=json.loads((out/'audit.json').read_text())
assert len(d)==200 and len(s)==40 and len(a['split_audit'])==25
assert not d.duplicated(['seed','task','representation','model']).any()
np.testing.assert_allclose(d.group_balanced_accuracy,(1-d.human_or_source0_false_positive+d.ai_or_source1_recall)/2)
assert a['script_sha256']==digest(p/'real_archive_feasibility.py')
assert a['helper_sha256']==digest(p/'grounded_synthetic.py')
for _,r in s.iterrows():
    x=d[(d.task==r.task)&(d.representation==r.representation)&(d.model==r.model)]
    np.testing.assert_allclose([r.ba_mean,r.ba_min,r.ba_max,r.f1_mean],[x.group_balanced_accuracy.mean(),x.group_balanced_accuracy.min(),x.group_balanced_accuracy.max(),x.group_weighted_macro_f1.mean()])
(out/'verification.json').write_text(json.dumps({'status':'pass','score_records':200,'summary_records':40,'checks':['score algebra','summary recomputation','unique task/seed/model/representation','runner and helper hashes'],'sha256':{n:digest(out/n) for n in ['scores.csv','summary.csv','audit.json']}},indent=2)+'\n')
print('PASS: 200 score records, 40 recomputed summaries, runner/helper hashes and score algebra')
