"""Extract deterministic, normalized examples and exact score contributions.

Use first ID in each outcome category, never hand-pick an attractive example.
Only three command strings are quoted per example; full inputs stay private.
"""
import hashlib,json
from pathlib import Path
import joblib,numpy as np
HERE=Path(__file__).resolve().parent
data=json.loads(Path('C:/w/px118_20261005/records.json').read_text())
lookup={r['id']:r for r in data['rows']+data['external']}
pred=json.loads(Path('C:/w/px118_20261005/collected/outputs/masked_main_predictions.json').read_text())
b=joblib.load('C:/w/px118_20261005/collected/outputs/masked.joblib');m=b['model'];v,lr=list(m.named_steps.values())
examples=[]
for name,label,decision in [('AI correctly identified',1,1),('AI missed',1,0),('Human correctly identified',0,0)]:
    item=sorted([x for x in pred['test'] if x['label']==label and int(x['score']>=b['threshold'])==decision],key=lambda x:x['id'])[0]
    row=lookup[item['id']];text=' '.join(' '.join([c.split()[0]]+['ARG']*(len(c.split())-1)) for c in row['commands'])
    x=v.transform([text]);contrib=x.multiply(lr.coef_[0]).tocsr();names=v.get_feature_names_out()
    pairs=sorted(zip(contrib.indices,contrib.data),key=lambda z:-abs(z[1]))[:5]
    residual=abs(float(contrib.sum()+lr.intercept_[0])-float(m.decision_function([text])[0]));assert residual<1e-10
    examples.append(dict(outcome=name,record_id=item['id'],record_id_short=hashlib.sha256(item['id'].encode()).hexdigest()[:12],
        source=row['source'],first_three_normalized_commands=row['commands'][:3],score=item['score'],threshold=b['threshold'],
        top_contributions=[dict(feature=str(names[i]),signed_score_contribution=float(z)) for i,z in pairs],reconstruction_error=residual))
(HERE/'DATA_EXAMPLES.json').write_text(json.dumps(examples,indent=2))
print(json.dumps(examples,indent=2))
