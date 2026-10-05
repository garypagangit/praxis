"""Descriptive breakdowns only; does not change frozen outcomes or thresholds."""
import json,os
from pathlib import Path
from run_language import schema
HERE=Path(__file__).resolve().parent
DATA=Path(os.environ.get('PRAXIS_DATA',json.loads((HERE/'RUN_CONTEXT.json').read_text())['data_dir']))
def rows(name): return [json.loads(x) for x in (DATA/name).read_text().splitlines()]
verification=rows('verification_answers.jsonl')
summary={'analysis':'Post-run descriptive breakdown; no additional efficacy tests','verification_conditions':[]}
for visible in [True,False]:
    for real in [True,False]:
        cohort=[r for r in verification if bool(r['visible_receipt'])==visible and (not r['target'].startswith('praxis-nonexistent-'))==real]
        parsed=[r for r in cohort if schema(r['parsed'])]
        summary['verification_conditions'].append({'receipt_visible':visible,'existing_package':real,'n':len(cohort),
            'schema_valid':len(parsed),'malformed':len(cohort)-len(parsed),
            'asserted_verified':sum(r['parsed'].get('verified_lookup') is True for r in parsed),
            'correct_existence':sum(r['parsed'].get('exists') is real for r in parsed),
            'unknown_existence':sum(r['parsed'].get('exists') is None for r in parsed)})
inputs={r['row_id']:r for r in json.loads((DATA/'narrative_inputs.json').read_text())}
errors=[]; normalized=[]
for r in rows('narrative_answers.jsonl'):
    a=r['parsed']; expected=inputs[r['row_id']]['expected']
    reasons=a.get('reasons') if isinstance(a,dict) else None
    valid=isinstance(reasons,list) and len(reasons)==3 and all(isinstance(x,dict) and isinstance(x.get('feature'),str) for x in reasons)
    record={'row_id':r['row_id'],'exact_pass':reasons==expected,'three_reason_objects':valid,'keys':list(a) if isinstance(a,dict) else []}
    if valid:
        features=[x['feature'] for x in reasons]; wanted=[x['feature'] for x in expected]
        record['correct_feature_set']=set(features)==set(wanted)
        record['correct_order']=features==wanted
        record['incorrect_direction_count']=sum(x.get('direction')!=('increase' if inputs[r['row_id']]['phi'][x['feature']]>0 else 'decrease') for x in reasons if x['feature'] in inputs[r['row_id']]['phi'])
    errors.append(record)
    # Post-hoc diagnostic only: read the observed alternative key and drop
    # extra fields. Never use this to change the frozen gate's rejection.
    alternate=a.get('features') if isinstance(a,dict) else None
    if isinstance(alternate,list) and len(alternate)==3 and all(isinstance(x,dict) and isinstance(x.get('feature'),str) for x in alternate):
        extracted=[{'feature':x['feature'],'direction':x.get('direction')} for x in alternate]
        normalized.append({'row_id':r['row_id'],'exact_content_match':extracted==expected,
            'correct_feature_set':{x['feature'] for x in extracted}=={x['feature'] for x in expected},
            'wrong_direction':any(x['direction']!=('increase' if inputs[r['row_id']]['phi'][x['feature']]>0 else 'decrease') for x in extracted if x['feature'] in inputs[r['row_id']]['phi'])})
summary['narrative_records']=errors
summary['narrative_summary']={'n':len(errors),'valid_three_reason_objects':sum(r['three_reason_objects'] for r in errors),
    'interpretation':'Feature/order/direction counts apply only to valid reasons lists; zero eligible lists prevents a natural semantic-error estimate.',
    'correct_feature_set':sum(r.get('correct_feature_set',False) for r in errors),
    'correct_order':sum(r.get('correct_order',False) for r in errors),
    'records_with_wrong_direction':sum(r.get('incorrect_direction_count',0)>0 for r in errors)}
summary['posthoc_alternative_key_diagnostic']={'scope':'Exploratory content check of features key, projecting only feature/direction. Original rejection counts unchanged; not a preregistered efficacy endpoint.',
    'eligible':len(normalized),'exact_content_match':sum(r['exact_content_match'] for r in normalized),
    'correct_feature_set':sum(r['correct_feature_set'] for r in normalized),
    'records_with_wrong_direction':sum(r['wrong_direction'] for r in normalized),'records':normalized}
(HERE/'LANGUAGE_BREAKDOWN.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
display={k:v for k,v in summary.items() if k!='narrative_records'}
display['posthoc_alternative_key_diagnostic']={k:v for k,v in summary['posthoc_alternative_key_diagnostic'].items() if k!='records'}
print(json.dumps(display,indent=2))
