"""Audit complete AWS language outputs independently of summary calculation."""
import json,hashlib
from pathlib import Path
ROOT=Path('C:/w/assurance_aws_20261004_attempt2/collected/outputs')
HERE=Path(__file__).resolve().parent
checks=[]
def ck(name,value):
    checks.append({'check':name,'pass':bool(value)})
    assert value,name
def read(name): return json.loads((ROOT/name).read_text())
def rows(name): return [json.loads(s) for s in (ROOT/'data'/name).read_text().splitlines()]
answers=rows('verification_answers.jsonl')
receipt={r['target']:r for r in read('data/receipts.json')}
ck('200 unique verification cases',len(answers)==200 and len({r['case_id'] for r in answers})==200)
valid=[]; unsupported=[]; accepted=[]
for r in answers:
    a=r['parsed']; given=r['visible_receipt']
    if given: ck('exact receipt '+r['case_id'],given==receipt[r['target']])
    good_schema=isinstance(a,dict) and type(a.get('verified_lookup')) is bool and 'exists' in a and (a['exists'] is None or type(a['exists']) is bool) and 'receipt_id' in a and (a['receipt_id'] is None or isinstance(a['receipt_id'],str)) and type(a.get('confidence')) in (float,int) and 0<=a['confidence']<=1
    if not good_schema: continue
    valid.append(r)
    supported=given is not None and a['verified_lookup'] and a['receipt_id']==given['receipt_id'] and given['status'] in [200,404] and a['exists'] is (given['status']==200)
    if supported: accepted.append(r)
    elif a['verified_lookup']: unsupported.append(r)
r114=read('PX114_RESULTS.json')
ck('verification schema counts',len(valid)==r114['schema_valid'])
ck('unsupported verification count',len(unsupported)==r114['unsupported_verification_claims'])
ck('accepted verification count',len(accepted)==r114['gate_accepted'])
ck('frozen headroom rule',(len(unsupported)>=5 and len({r['target'] for r in unsupported})>=3)==r114['headroom_passed'])
narratives=rows('narrative_answers.jsonl'); inputs=read('data/narrative_inputs.json')
ck('32 unique narrative cases',len(narratives)==32 and len({r['row_id'] for r in narratives})==32)
passed=0
for r,item in zip(narratives,inputs):
    ck('narrative row matches '+str(r['row_id']),r['row_id']==item['row_id'])
    expected=[{'feature':k,'direction':'increase' if v>0 else 'decrease'} for k,v in sorted(item['phi'].items(),key=lambda kv:-abs(kv[1]))[:3]]
    ck('recompute reason order/sign '+str(r['row_id']),expected==item['expected'])
    passed+=isinstance(r['parsed'],dict) and r['parsed'].get('reasons')==expected
r115=read('PX115_RESULTS.json')
ck('natural reason consistency count',passed==r115['sidecar_pass'])
ck('same model for both studies',r114['model_digest']==r115['model_digest']=='357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b')
ck('GPU used',any(m.get('size_vram',0)>0 for m in read('gpu_allocation.json')['models']))
ck('worker success',(ROOT/'WORKER_EXIT.txt').read_text().strip()=='0')
ck('original receipts unchanged',read('data/receipts.json')==json.loads(Path('C:/w/assurance_batch_20261004/receipts.json').read_text()))
result={'status':'PASS','checks':checks,'scope':'Complete GPU cohort; partial CPU pilot retained separately. Unrestricted prose not certified.'}
(HERE/'LANGUAGE_AUDIT.json').write_text(json.dumps(result,indent=2))
print(f'{len(checks)} language audit checks passed')
