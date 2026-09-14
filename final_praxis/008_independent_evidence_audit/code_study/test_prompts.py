"""Synthetic interface tests only; no model calls or benchmark outcome data."""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json
import prompts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    results=[]
    def check(name, action):
        try:
            passed=bool(action());results.append({'id':name,'passed':passed})
        except Exception as exc:results.append({'id':name,'passed':False,'exception':type(exc).__name__,'detail':str(exc)})
    def rejected(action):
        try:action()
        except ValueError:return True
        return False
    code='def f(x):\n    return x\n';spec={'entry_point':'f','signature':'x','returns':None,'description':'Return the input.'}
    record=prompts.make_execution_record('case-a',[1],1,'pass',code)
    record_before=copy.deepcopy(record)
    independent=prompts.make_execution_record('case-b',[2],2,'fail',code)
    check('public_spec_accepted',lambda:len(prompts.proposal_messages(spec,code,'honest_repair'))==2)
    check('selected_record_accepted',lambda:len(prompts.review_messages(spec,code,code,[record],[independent]))==2)
    for key in ('reserved_outcomes','canonical_solution','native_bug_label','full_outcome_vector'):
        extra=dict(spec,**{key:'FORBIDDEN_SENTINEL'})
        check('reject_spec_'+key,lambda extra=extra:rejected(lambda:prompts.proposal_messages(extra,code,'honest_repair')))
        check('reject_review_spec_'+key,lambda extra=extra:rejected(lambda:prompts.review_messages(extra,code,code,[],[])))
    for key in ('reserved_outcomes','expected_full','reference_solution','outcome_vector'):
        extra=dict(record,**{key:'FORBIDDEN_SENTINEL'})
        check('reject_record_'+key,lambda extra=extra:rejected(lambda:prompts.review_messages(spec,code,code,[extra],[])))
    missing=dict(record);missing.pop('truncated')
    check('missing_record_field',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[missing],[])))
    bad=dict(record,status='success')
    check('unknown_execution_status',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[bad],[])))
    bad_trunc=dict(record,truncated='false')
    check('truncation_flag_requires_bool',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[bad_trunc],[])))
    bad_hash=dict(record,code_sha256='0'*64)
    check('stale_code_hash',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[bad_hash],[])))
    bad_preview=dict(record,input_preview='[3]')
    check('tampered_untruncated_preview',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[bad_preview],[])))
    check('duplicate_supplier_test',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[record,record],[])))
    check('supplier_independent_overlap',lambda:rejected(lambda:prompts.review_messages(spec,code,code,[record],[record])))
    long_input=['x'*500];long_expected='y'*300
    long_record=prompts.make_execution_record('long',long_input,long_expected,'pass',code)
    check('preview_limits',lambda:len(long_record['input_preview'])==350 and len(long_record['expected_preview'])==150 and long_record['truncated'] is True)
    canonical=json.dumps(long_input,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    check('hash_covers_untruncated_payload',lambda:long_record['input_sha256']==hashlib.sha256(canonical.encode()).hexdigest() and long_record['input_sha256']!=hashlib.sha256(long_record['input_preview'].encode()).hexdigest())
    check('truncation_notice_in_prompt',lambda:'incomplete previews' in prompts.review_messages(spec,code,code,[long_record],[])[1]['content'])
    check('input_structures_unchanged',lambda:record==record_before and set(record)==prompts.RECORD_FIELDS)
    check('valid_review_parse',lambda:prompts.parse_review({'finish_reason':'end_turn','text':'{"decision":"accept","reason":"A reason."}'})['valid'])
    check('truncated_review_abstains',lambda:prompts.parse_review({'finish_reason':'max_tokens','text':'{"decision":"accept","reason":"A reason."}'})['decision']=='abstain')
    check('duplicate_review_key_rejected',lambda:not prompts.parse_review({'finish_reason':'end_turn','text':'{"decision":"keep","decision":"accept","reason":"A reason."}'})['valid'])
    check('extra_review_field_rejected',lambda:not prompts.parse_review({'finish_reason':'end_turn','text':'{"decision":"accept","reason":"A reason.","secret":1}'})['valid'])
    check('valid_proposal_parse',lambda:prompts.parse_proposal({'finish_reason':'end_turn','text':json.dumps({'code':code})})['status']=='parsed')
    check('truncated_proposal_rejected',lambda:prompts.parse_proposal({'finish_reason':'max_tokens','text':json.dumps({'code':code})})['status']=='invalid')
    check('duplicate_proposal_key_rejected',lambda:prompts.parse_proposal({'finish_reason':'end_turn','text':'{"code":"pass","code":"def f(x): return x"}'})['status']=='invalid')
    check('proposer_import_contract_alignment',lambda:'copy, random' not in prompts.PROPOSE_SYSTEM and 'hashlib' in prompts.PROPOSE_SYSTEM and 'cmath' in prompts.PROPOSE_SYSTEM)
    report={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Synthetic prompt schema, binding and parsing tests only; no benchmark outcomes or model calls.','controls':len(results),'passed':sum(r['passed'] for r in results),'results':results,'prompts_sha256':hashlib.sha256(Path(prompts.__file__).read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'controls':report['controls'],'passed':report['passed']}));return 0 if report['passed']==report['controls'] else 1


if __name__=='__main__':raise SystemExit(main())
