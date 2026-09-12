"""Posthoc mechanical citation normalization, with zero inference or label changes.

The original V2 endpoint remains unchanged. Only an exact, overlong source quote
may be shortened. Qualification stays frozen; opposing labels remain unresolved.
"""
import argparse,copy,hashlib,json,re
from collections import Counter
from pathlib import Path
import run_review as frozen

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate key')
        result[key]=value
    return result

def normalize_citation(text,response,finish_reason):
    text=text.strip();match=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',text,re.S)
    if match:text=match.group(1)
    original=json.loads(text,object_pairs_hook=unique)
    if not isinstance(original,dict):raise ValueError('Not a JSON object')
    quote=original.get('evidence')
    if not isinstance(quote,str) or len(quote)<=240 or quote not in response:raise ValueError('Not an exact overlong response quote')
    normalized={**original,'evidence':quote[:240]}
    parsed=frozen.parse_review(json.dumps(normalized),response,finish_reason)
    for field in ('response_harmful','task_fulfillment','confidence','rationale'):
        assert parsed[field]==original[field]
    assert parsed['refusal_raw']==original['refusal']
    return parsed,{'original_characters':len(quote),'normalized_characters':240,'full_quote_exact_in_response':True,'original_quote_sha256':hashlib.sha256(quote.encode()).hexdigest(),'normalized_quote_sha256':hashlib.sha256(quote[:240].encode()).hexdigest(),'reviewer_labels_and_rationale_changed':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--review',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    original=frozen.read(args.review/'automated_review.json');manifest=frozen.read(args.review/'manifest.json')['manifest']
    records,private,hashes=frozen.load_source(args.source);assert hashes==manifest['source_hashes']
    controls=frozen.read(Path(__file__).with_name('controls.json'))
    cells=[];source_cells={};normalizations=[]
    responses={r['id']:r['response'] for r in records+controls}
    for path in sorted((args.review/'cells').glob('*.json')):
        source_cells[path.name]=frozen.sha(path);cell=frozen.read(path);updated=copy.deepcopy(cell)
        if not cell['valid'] and original['qualification'][cell['model_id']]['qualified'] and 'provider_result' in cell:
            provider=cell['provider_result']
            try:parsed,receipt=normalize_citation(provider['text'],responses[cell['item_id']],provider['finish_reason'])
            except (ValueError,AssertionError,KeyError,TypeError):pass
            else:
                updated['valid']=True;updated['review']=parsed
                normalizations.append({'request_id':cell['request_id'],'item_id':cell['item_id'],'model':cell['model_id'],'replicate':cell['replicate'],'source_cell_sha256':source_cells[path.name],**receipt})
        cells.append(updated)
    assert len(cells)==120
    result=frozen.aggregate(cells,records,private,controls)
    assert result['qualification']==original['qualification'],'Reviewer qualification changed'
    for path in (args.review/'cells').glob('*.json'):assert frozen.sha(path)==source_cells[path.name]
    assert frozen.load_source(args.source)[2]==hashes
    comparisons=[]
    for case in result['cases']:
        auto=case['automated']['refusal']['label'];old=case['original_qwen']['refusal']
        if auto in ('yes','no'):comparisons.append(auto!=old.lower())
        case['operational_disposition']='closed_automated_consensus' if case['workflow_state']=='automated_resolved' else 'closed_automated_disagreement'
    unresolved=[{'id':c['id'],'fields':[f for f in frozen.FIELDS if c['automated'][f]['label']=='unresolved'],'votes':{f:c['automated'][f]['votes'] for f in frozen.FIELDS}} for c in result['cases'] if c['workflow_state']!='automated_resolved']
    result.update({'schema':'praxis005-mechanical-citation-completion-v1','workflow_status':'AUTOMATED_QUEUE_CLOSED','cases_processed':28,'strict_v2_resolved_both':original['resolved_both'],'posthoc_supplement':True,'normalizations':normalizations,'remaining_disagreements':unresolved,'new_model_calls':0,'human_review_performed':False,'original_cells_unchanged':True,'source_files_unchanged':True,'strict_v2_endpoint_unchanged':True,'original_refusal_comparable':len(comparisons),'original_refusal_differences':sum(comparisons),'source_lock_sha256':original['source_lock_sha256']})
    args.out.mkdir(parents=True,exist_ok=True);frozen.write(args.out/'COMPLETION.json',result)
    text=f'''# Completed automated review queue

All 28 cases have an automated disposition: **{result['resolved_both']} consensus decisions and {len(unresolved)} recorded disagreements**. No manual task is assigned. Independent human validation remains unperformed.

The strict V2 result remains {original['resolved_both']}/28. This separately labeled posthoc supplement shortened {len(normalizations)} exact overlong citations to 240 characters after verifying the full quotes occur verbatim in their original responses. It changed no reviewer label, rationale, original response or qualification outcome and made zero additional model calls. Every other frozen schema constraint had to pass. Original V1/V2 artifacts remain intact.

Two qualified reviewers participate; Qwen remains disqualified. Where these reviewers oppose each other, the workflow records uncertainty. Consensus is not ground truth. These selected cases cannot replace experiment-wide rates.

Refusal labels are comparable for {len(comparisons)}/28 cases, with {sum(comparisons)} differences from the original Qwen refusal labels. Harmfulness remains unresolved for the explicitly listed disagreements in COMPLETION.json. The operational queue is closed with these limitations; the historical human-adjudication criterion is not fulfilled.

Both model passes together used 240 provider requests and an estimated $0.14245228. This supplement uses only saved artifacts. The primary-Praxis investment recommendation remains unchanged.
'''
    (args.out/'COMPLETION.md').write_text(text,encoding='utf-8')
    print(json.dumps({'workflow_status':result['workflow_status'],'consensus':result['resolved_both'],'disagreements':len(unresolved),'normalized_citations':len(normalizations),'new_model_calls':0,'refusal_differences':sum(comparisons)}))

if __name__=='__main__':main()
