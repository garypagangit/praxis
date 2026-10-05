"""Recount every saved prediction and verify group exclusion independently."""
import csv,hashlib,json,os
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
HERE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('PX117_OUTPUT','C:/w/px117_aws_20261005/collected/outputs'))
data=Path('C:/w/px117_aws_20261005/records.json')
rows={r['id']:r for r in json.loads(data.read_text())}
summary=json.loads((OUT/'RESULTS.json').read_text())
checks=[]
def check(name,condition):
    checks.append({'name':name,'pass':bool(condition)})
    assert condition,name
check('worker completed',(OUT/'WORKER_EXIT.txt').read_text().strip()=='0')
check('same frozen records',hashlib.sha256(data.read_bytes()).hexdigest()==summary['records_sha256'])
for r in summary['results']:
    if r['status']!='COMPLETE_DESCRIPTIVE_ONLY':continue
    tag=r['name']+'_'+r['model']
    saved=json.loads((OUT/(tag+'_predictions.json')).read_text())
    y=np.array([p['label'] for p in saved['test']]);scores=np.array([p['score'] for p in saved['test']]);pred=scores>=r['threshold']
    for field,value in [('tn',sum((y==0)&~pred)),('fp',sum((y==0)&pred)),('fn',sum((y==1)&~pred)),('tp',sum((y==1)&pred))]:
        check(tag+' '+field,int(value)==r[field])
    check(tag+' AUROC',abs(roc_auc_score(y,scores)-r['test_auroc'])<1e-10)
    ids=[set(saved['fit_ids']),{p['id'] for p in saved['calibration']},{p['id'] for p in saved['test']}]
    check(tag+' counts',[len(a) for a in ids]==[r['fit_n'],r['cal_n'],r['test_n']])
    fps=[{rows[i]['fingerprint'] for i in group} for group in ids]
    check(tag+' no cross-partition duplicate prefixes',not (fps[0]&fps[1] or fps[0]&fps[2] or fps[1]&fps[2]))
    if r['name'].startswith('family_'):
        family=r['name'][len('family_'):]
        check(tag+' held family absent',all(rows[i]['family']!=family for i in ids[0]|ids[1]))
    if r['name'].startswith('human_task_'):
        task=r['name'][len('human_task_'):].replace('_',' ')
        check(tag+' held human task absent',all(rows[i]['task']!=task for i in ids[0]|ids[1]))
    cal=saved['calibration']; cy=np.array([p['label'] for p in cal]);cs=np.array([p['score'] for p in cal])
    threshold=next(float(t) for t in np.unique(np.r_[0,cs[cy==0],np.nextafter(cs[cy==0],np.inf),np.nextafter(1.,np.inf)]) if np.mean(cs[cy==0]>=t)<=.05)
    check(tag+' calibration-only threshold',threshold==r['threshold'])
    check(tag+' reference labels',all(p['label']==rows[p['id']]['label'] for p in saved['calibration']+saved['test']))
export=json.loads((OUT/'EXPORT_CHECKS.json').read_text())
check('exported CLI verified on both classes',len(export)==2 and all(x['prediction_matches_saved_model'] for x in export))
base=[r for r in summary['results'] if r['name']=='record_holdout']
check('model selection uses calibration',max(base,key=lambda r:(r['calibration_auroc'],r['model']))['model']==summary['selected_model'])
with (HERE/'RESULTS_TABLE.csv').open('w',newline='') as f:
    names=['name','model','status','fit_n','cal_n','test_n','test_auroc','agent_recall','human_fpr','tn','fp','fn','tp','threshold']
    writer=csv.DictWriter(f,fieldnames=names,extrasaction='ignore');writer.writeheader();writer.writerows(summary['results'])
(HERE/'AUDIT_RESULTS.json').write_text(json.dumps({'status':'PASS','checks':checks,
    'scope':'Arithmetic, split and export audit only. Independent operator identity, matched environments and scientific validity are not certified.'},indent=2)+'\n')
print(str(len(checks))+' audit checks passed')
