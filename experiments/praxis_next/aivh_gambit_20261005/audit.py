"""Independent recount of saved scores and grouping; no refitting."""
import collections,csv,hashlib,json,os
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/px117c_aws_20261005')
OUT=Path(os.environ.get('PX117C_OUTPUT',str(PRIVATE/'collected/outputs')))
data=json.loads((PRIVATE/'records.json').read_text());rows={r['id']:r for r in data['rows']+data['external']}
summary=json.loads((OUT/'RESULTS.json').read_text());checks=[]
def check(name,condition):
    checks.append({'check':name,'pass':bool(condition)});assert condition,name
check('source hash',summary['records_sha256']==hashlib.sha256((PRIVATE/'records.json').read_bytes()).hexdigest())
check('worker exit',(OUT/'WORKER_EXIT.txt').read_text().strip()=='0')
for r in summary['results']:
    if r['status']!='COMPLETE_DESCRIPTIVE_ONLY':continue
    name=r['model']+'_'+r['condition'];e=json.loads((OUT/(name+'_predictions.json')).read_text())
    fit=[rows[x['id']] for x in e['fit']];cal=[rows[x['id']] for x in e['calibration']];test=[rows[x['id']] for x in e['test']]
    for key in ['group','fingerprint']:
        check(name+' fit-cal-test '+key,not ({x[key] for x in fit}&{x[key] for x in cal+test}) and not ({x[key] for x in cal}&{x[key] for x in test}))
    if r['condition'].startswith('family_'):
        f=r['condition'][7:]
        check(name+' held family',all(x['family']!=f for x in fit+cal) and all(x['family']==f for x in test if x['label']==1))
    if r['condition']=='shuffled_fit_labels':
        gl=collections.defaultdict(set)
        for x in e['fit']:gl[rows[x['id']]['group']].add(x['label_used'])
        check(name+' grouped permutation',all(len(v)==1 for v in gl.values()))
    hs=collections.defaultdict(list)
    for x in e['calibration']:
        if rows[x['id']]['label']==0:hs[rows[x['id']]['group']].append(x['score'])
    scores=np.array([v for group in hs.values() for v in group]);candidates=np.unique(np.r_[0,scores,np.nextafter(scores,np.inf),np.nextafter(1.,np.inf)])
    expected=next(float(t) for t in candidates if np.mean([np.mean(np.array(v)>=t) for v in hs.values()])<=.05)
    check(name+' frozen threshold',abs(expected-r['threshold'])<1e-12)
    for key,target in [('test',r),('external',r.get('external_kypo'))]:
        if not target:continue
        y=[rows[x['id']]['label'] for x in e[key]];p=[x['score']>=r['threshold'] for x in e[key]]
        counts={'tp':sum(a==1 and b for a,b in zip(y,p)), 'fn':sum(a==1 and not b for a,b in zip(y,p)),
                'fp':sum(a==0 and b for a,b in zip(y,p)),'tn':sum(a==0 and not b for a,b in zip(y,p))}
        check(name+' '+key+' confusion',all(target[k]==v for k,v in counts.items()))
        rates=collections.defaultdict(list)
        for x,pred in zip(e[key],p):
            if rows[x['id']]['label']==0:rates[rows[x['id']]['group']].append(pred)
        check(name+' '+key+' group FPR',abs(np.mean([np.mean(v) for v in rates.values()])-target['human_group_mean_fpr'])<1e-12)
        if len(set(y))==2:check(name+' AUROC',abs(roc_auc_score(y,[x['score'] for x in e[key]])-target['auroc'])<1e-12)
        if key=='external':check(name+' external exclusion',not ({rows[x['id']]['fingerprint'] for x in e[key]}&{x['fingerprint'] for x in fit+cal}))
base=[r for r in summary['results'] if r['condition']=='participant_holdout' and r['status']=='COMPLETE_DESCRIPTIVE_ONLY']
check('calibration selection',sorted(base,key=lambda r:(-r['calibration_auroc'],r['model']))[0]['model']==summary['selected_model'])
(HERE/'AUDIT.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2)+'\n')
fields=['condition','model','status','auroc','agent_recall','human_window_fpr','human_group_mean_fpr','human_groups','human_groups_with_any_false_alert','tp','fn','fp','tn','meets_numerical_target']
with (HERE/'RESULTS_TABLE.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(summary['results'])
print(json.dumps({'audit_checks_passed':len(checks),'selected_model':summary['selected_model']}))
