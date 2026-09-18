"""Prepare answer-disagreement projections without changing historical artifacts."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OLD=REPO/'reports/cti_checker_pilot_20260918'
EXT=REPO/'reports/cti_external_validation_20260918'
ARCHIVE=Path('C:/w/px_final_20260917/final_praxis/papers/20260914/01_cti')
MODELS=['llama','qwen']

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path): return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def dump(path,data):
    with Path(path).open('x',encoding='utf-8') as f: json.dump(data,f,indent=2);f.write('\n')
def jsonl(path,data):
    with Path(path).open('x',encoding='utf-8') as f:
        for r in data:f.write(json.dumps(r,ensure_ascii=False)+'\n')

spec=importlib.util.spec_from_file_location('frozen_parser',EXT/'frozen_inference.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
provenance={r['file']:r for r in json.loads((ARCHIVE/'PROVENANCE.json').read_text())['artifacts']}
cal_ids={r['id'] for r in json.loads((OLD/'SPLITS.json').read_text()) if r['fold']==0}
assert len(cal_ids)==500
old_by={r['id']:r for r in rows(OLD/'data.jsonl')}
cal={i:{'id':i,'source_group':old_by[i]['source_group'],'eligible':old_by[i]['eligible'],'models':{}} for i in cal_ids}
sources={}
for model in MODELS:
    name=f'data/full2500_{model}_query_only.jsonl.gz'
    file=ARCHIVE/name
    assert digest(file)==provenance[name]['sha256']
    raw=gzip.decompress(file.read_bytes())
    assert hashlib.sha256(raw).hexdigest()==provenance[name]['uncompressed_sha256']
    sources[str(file)]={'sha256':digest(file)}
    records=[json.loads(x) for x in raw.decode().splitlines()]
    assert len(records)==5000
    for r in records:
        if r['id'] not in cal_ids:continue
        answer=parser.strict_parse(r['raw_output'])
        assert answer==r['parsed_answer']
        assert (answer==r['expected_output'])==r['correct']
        condition='evidence' if r['condition']=='relationship_evidence' else r['condition']
        assert condition in ['vanilla','evidence']
        current=cal[r['id']]['models'].setdefault(model,{})
        assert condition not in current
        current[condition]={'answer':answer,'correct':bool(r['correct']),'valid':answer in 'ABCD' and len(answer)==1}
        assert old_by[r['id']]['outcomes'][model][condition]==bool(r['correct'])

external_inputs={r['id']:r for r in rows(EXT/'test_inputs.jsonl')}
labels={r['id']:r for r in rows(EXT/'sealed_labels.jsonl')}
external={i:{'id':i,'source_group':labels[i]['source'],'models':{}} for i in external_inputs}
for r in rows(EXT/'execution_outputs/predictions.jsonl'):
    answer=parser.strict_parse(r['raw_output']);assert answer==r['parsed_answer']
    condition='evidence' if r['condition']=='relationship_evidence' else r['condition']
    current=external[r['id']]['models'].setdefault(r['model'],{})
    assert condition not in current
    current[condition]={'answer':answer,'correct':answer==labels[r['id']]['answer'],'valid':bool(r['valid'])}
assert len(external)==1247

counts={}
for name,metadata,inputs in [('calibration',cal,old_by),('external_diagnostic',external,external_inputs)]:
    safe=[]
    per_model={m:0 for m in MODELS}
    for i in sorted(metadata):
        r=metadata[i];required=set()
        for m in MODELS:
            pair=r['models'][m];assert set(pair)=={'vanilla','evidence'}
            if pair['vanilla']['answer']!=pair['evidence']['answer']:
                per_model[m]+=1
                for c in ['vanilla','evidence']:
                    if pair[c]['valid']:required.add(pair[c]['answer'])
        if not required:continue
        original=inputs[i]
        safe.append({'id':i,'question':original['question'],'options':original['options'],
                     'evidence':[{k:v for k,v in fact.items() if k in ['text','kind','score']} for fact in original['evidence']],
                     'required_options':sorted(required)})
    input_file=ROOT/(name+'_inputs.jsonl')
    eval_file=ROOT/(name+'_evaluation.jsonl')
    jsonl(input_file,safe);jsonl(eval_file,[metadata[i] for i in sorted(metadata)])
    counts[name]={'all_questions':len(metadata),'disagreement_union_questions':len(safe),
                  'disagreements_per_model':per_model,'nli_pairs':sum(len(r['required_options'])*len(r['evidence']) for r in safe),
                  'safe_input_sha256':digest(input_file),'evaluation_sha256':digest(eval_file)}

for file in [OLD/'data.jsonl',OLD/'SPLITS.json',EXT/'test_inputs.jsonl',EXT/'sealed_labels.jsonl',EXT/'execution_outputs/predictions.jsonl']:
    sources[str(file)]={'sha256':digest(file)}
dump(ROOT/'INPUT_AUDIT.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS',
    'scope':'EXPOSED_DEVELOPMENT_DATA_ONLY','selection_uses_answer_disagreement_not_correctness':True,
    'verifier_inputs_exclude_gold_and_outcomes':True,'counts':counts,'source_files':sources,'code_sha256':digest(__file__)})
print(json.dumps(counts,indent=2))
