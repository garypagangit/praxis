"""Audit complete AWS language outputs independently of summary calculation."""
import json,hashlib,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('PRAXIS_AUDIT_ROOT',str(Path(json.loads((HERE/'RUN_CONTEXT.json').read_text())['data_dir']).parent)))
checks=[]
def ck(name,value):
    checks.append({'check':name,'pass':bool(value)})
    assert value,name
def read(name): return json.loads((ROOT/name).read_text())
def rows(name): return [json.loads(s) for s in (ROOT/'data'/name).read_text().splitlines()]
answers=rows('verification_answers.jsonl')
receipt={r['target']:r for r in read('data/receipts.json')}
for index,r in enumerate(receipt.values()):
    raw=Path('C:/w/assurance_batch_20261004')/f'pypi_response_{index:02d}.bin'
    ck('snapshot response hash '+r['receipt_id'],hashlib.sha256(raw.read_bytes()).hexdigest()==r['sha256'])
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
ck('verification API calls completed',all('error' not in r and r.get('raw',{}).get('done') is True for r in answers))
if r114['headroom_passed']:
    judge_rows=rows('verification_judges.jsonl')
    ck('one judge per valid answer',len(judge_rows)==len(valid) and {r['case_id'] for r in judge_rows}=={r['case_id'] for r in valid})
    ck('judge API calls completed',all('error' not in r and r.get('raw',{}).get('done') is True for r in judge_rows))
    judges={r['case_id']:r['parsed'] for r in judge_rows}
    claimed=[r for r in valid if r['parsed']['verified_lookup']]
    selfaccepted=[r for r in claimed if isinstance(judges[r['case_id']],dict) and judges[r['case_id']].get('accept') is True]
    ranked=sorted(claimed,key=lambda r:(-r['parsed']['confidence'],r['case_id']))
    selfrank=sorted(selfaccepted,key=lambda r:(-float(judges[r['case_id']].get('confidence',0)),r['case_id']))
    common=min(len(accepted),len(ranked),len(selfrank))
    ck('matched comparison budget',common==r114['comparison']['matched_budget'])
    accepted_ids={r['case_id'] for r in accepted}
    groups={'gate':accepted,'confidence_ge_09':[r for r in claimed if r['parsed']['confidence']>=.9],
            'self_judge':selfaccepted,'matched_gate':sorted(accepted,key=lambda r:r['case_id'])[:common],
            'matched_confidence':ranked[:common],'matched_self_judge':selfrank[:common]}
    for name,group in groups.items():
        ck('recomputed comparison '+name,{'accepted':len(group),'unsupported':sum(r['case_id'] not in accepted_ids for r in group)}==r114['comparison'][name])
narratives=rows('narrative_answers.jsonl'); inputs=read('data/narrative_inputs.json')
ck('32 unique narrative cases',len(narratives)==32 and len({r['row_id'] for r in narratives})==32)
ck('narrative API calls completed',all('error' not in r and r.get('raw',{}).get('done') is True for r in narratives))
passed=0
for r,item in zip(narratives,inputs):
    ck('narrative row matches '+str(r['row_id']),r['row_id']==item['row_id'])
    expected=[{'feature':k,'direction':'increase' if v>0 else 'decrease'} for k,v in sorted(item['phi'].items(),key=lambda kv:-abs(kv[1]))[:3]]
    ck('recompute reason order/sign '+str(r['row_id']),expected==item['expected'])
    passed+=isinstance(r['parsed'],dict) and r['parsed'].get('reasons')==expected
r115=read('PX115_RESULTS.json')
ck('natural reason consistency count',passed==r115['sidecar_pass'])
ck('natural failure count',len(narratives)-passed==r115['sidecar_fail'])
ck('narrative parse count',sum(isinstance(r['parsed'],dict) for r in narratives)==r115['parseable_json'])
templates=read('data/deterministic_narratives.json')
ck('one template per fixed row',len(templates)==len(inputs) and [r['row_id'] for r in templates]==[r['row_id'] for r in inputs])
for template,item in zip(templates,inputs):
    expected_text='; '.join(f'{r["feature"]} {r["direction"]}s the raw bad-credit score' for r in item['expected'])+'.'
    ck('template matches evidence '+str(item['row_id']),template['reasons']==item['expected'] and template['narrative']==expected_text)
ck('template reported count',r115['template_consistent']==len(templates))
ck('prose certification explicitly excluded',r115['prose_semantics']=='NOT_CERTIFIED')
ck('same model for both studies',r114['model_digest']==r115['model_digest']=='357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b')
ck('manifest pinned model',read('data/model_manifest.json')['digest']==r114['model_digest'])
ck('pinned runtime',read('ollama_version.json')['version']=='0.17.0')
ck('GPU used',any(m.get('size_vram',0)>0 for m in read('gpu_allocation.json')['models']))
ck('worker success',(ROOT/'WORKER_EXIT.txt').read_text().strip()=='0')
ck('original receipts unchanged',read('data/receipts.json')==json.loads(Path('C:/w/assurance_batch_20261004/receipts.json').read_text()))
result={'status':'PASS','checks':checks,'scope':'Complete GPU cohort; partial CPU pilot retained separately. Unrestricted prose not certified.'}
(HERE/'LANGUAGE_AUDIT.json').write_text(json.dumps(result,indent=2))
print(f'{len(checks)} language audit checks passed')
