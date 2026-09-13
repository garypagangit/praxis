"""Bounded, resumable, paired MiCRo qualification with unmodified routing math."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, platform, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABLATIONS = {'intact':[], 'logic_ablation':['logic'], 'social_ablation':['social']}

def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8'); temporary.replace(path)
def prompt_for(question): return f"Q: {question}\nA: Let's think step by step."
def selected_routes(router_logits):
    import torch
    return torch.topk(torch.softmax(router_logits,dim=-1,dtype=torch.float32),1,dim=-1).indices.squeeze(-1)

def preflight(artifacts):
    from model_loader import verify_bundle
    protocol=json.loads((HERE/'protocol.json').read_text(encoding='utf-8'))
    data=json.loads((HERE/'data.json').read_text(encoding='utf-8'))
    if sha((HERE/'data.json').read_bytes()) != protocol['data_sha256']: raise ValueError('Data hash mismatch')
    if protocol['conditions']!=['raw','chat'] or len(data['pilot'])!=32 or protocol['expected_cells']!=64: raise ValueError('Unexpected pilot protocol')
    if set(data)!= {'pilot'}: raise ValueError('Pilot must not contain test questions')
    if len({r['id'] for r in data['pilot']})!=32: raise ValueError('Duplicate data IDs')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(artifacts/'tokenizer'),local_files_only=True)
    for row in data['pilot']:
        if sha(row['question'].encode())!=row['question_sha256']: raise ValueError('Question hash mismatch')
        raw=prompt_for(row['question'])
        chat=tokenizer.apply_chat_template([{'role':'user','content':raw}],tokenize=False,add_generation_prompt=True,date_string=protocol['chat_date_string'])
        for condition,text in [('raw',raw),('chat',chat)]:
            manifest=row['prompts'][condition]
            ids=tokenizer(text,add_special_tokens=(condition=='raw'))['input_ids']
            if condition=='chat' and ids!=tokenizer.apply_chat_template([{'role':'user','content':raw}],tokenize=True,return_dict=False,add_generation_prompt=True,date_string=protocol['chat_date_string']): raise ValueError('Chat encoding disagreement')
            if manifest['text']!=text or manifest['input_token_ids']!=ids: raise ValueError('Frozen prompt/tokenizer mismatch')
            if manifest['prompt_sha256']!=sha(text.encode()) or manifest['input_token_ids_sha256']!=sha(json.dumps(ids,separators=(',',':')).encode()): raise ValueError('Prompt/token hash mismatch')
            if manifest['prompt_tokens']!=len(ids) or ids[0]!=128000 or ids.count(128000)!=1: raise ValueError('Exactly one BOS required')
    return protocol,data,verify_bundle(artifacts/'source')


def numerical_checks(model, tokenizer, protocol, out):
    import torch
    records=[]
    for text in protocol['numerical_prompts']:
        tokens=tokenizer(text, add_special_tokens=not text.startswith(tokenizer.bos_token), return_tensors='pt')['input_ids'].to('cuda')
        mask=torch.ones_like(tokens)
        with torch.inference_mode():
            full=model(input_ids=tokens, attention_mask=mask, use_cache=False, experts_ablate=[], logits_to_keep=1)
            first=full.logits.clone()
            repeat=model(input_ids=tokens, attention_mask=mask, use_cache=False, experts_ablate=[], logits_to_keep=1).logits
            model(input_ids=tokens, attention_mask=mask, use_cache=False, experts_ablate=['logic'], logits_to_keep=1)
            reset=model(input_ids=tokens, attention_mask=mask, use_cache=False, experts_ablate=[], logits_to_keep=1).logits
            for condition,ablation in ABLATIONS.items():
                prefix=model(input_ids=tokens[:,:-1], attention_mask=mask[:,:-1], use_cache=True, experts_ablate=ablation, logits_to_keep=1)
                cached=model(input_ids=tokens[:,-1:], attention_mask=mask, past_key_values=prefix.past_key_values,
                             use_cache=True, experts_ablate=ablation, logits_to_keep=1)
                complete=model(input_ids=tokens, attention_mask=mask, use_cache=False, experts_ablate=ablation, logits_to_keep=1)
                model.config._attn_implementation='eager'
                try:
                    eager=model(input_ids=tokens, attention_mask=mask, use_cache=False, experts_ablate=ablation, logits_to_keep=1)
                finally: model.config._attn_implementation='sdpa'
                ablated_index={'logic_ablation':0,'social_ablation':1}.get(condition)
                routes_zero=True if ablated_index is None else all(bool((selected_routes(r)!=ablated_index).all()) for r in complete.routing_weights)
                records.append({'prompt_sha256':sha(text.encode()), 'condition':condition,
                    'finite':bool(torch.isfinite(complete.logits).all() and torch.isfinite(cached.logits).all()),
                    'repeat_equal':bool(torch.equal(first,repeat)), 'ablation_reset_equal':bool(torch.equal(first,reset)),
                    'cache_top_token_equal':bool(cached.logits[0,-1].argmax()==complete.logits[0,-1].argmax()),
                    'cache_max_abs':float((cached.logits.float()-complete.logits.float()).abs().max()),
                    'eager_sdpa_top_token_equal':bool(eager.logits[0,-1].argmax()==complete.logits[0,-1].argmax()),
                    'eager_sdpa_max_abs':float((eager.logits.float()-complete.logits.float()).abs().max()),
                    'cache_routing_equal':all(bool(selected_routes(c)[0,-1]==selected_routes(f)[0,-1]) for c,f in zip(cached.routing_weights,complete.routing_weights)),
                    'eager_sdpa_routing_equal':all(bool(selected_routes(e)[0,-1]==selected_routes(f)[0,-1]) for e,f in zip(eager.routing_weights,complete.routing_weights)),
                    'sdpa_next_token_margin':float(complete.logits[0,-1].topk(2).values[0]-complete.logits[0,-1].topk(2).values[1]),
                    'eager_next_token_margin':float(eager.logits[0,-1].topk(2).values[0]-eager.logits[0,-1].topk(2).values[1]),
                    'minimum_router_margin':min(float((r[0,-1].topk(2).values[0]-r[0,-1].topk(2).values[1])) for r in complete.routing_weights),
                    'ablation_routes_zero':routes_zero})
    checks={'pinned_bundle':True,'exact_checkpoint_load':True,
            **{k:all(r[k] for r in records) for k in ['finite','repeat_equal','ablation_reset_equal','cache_top_token_equal','ablation_routes_zero','eager_sdpa_top_token_equal']},
            'eager_sdpa_max_abs_within_tolerance':all(r['eager_sdpa_max_abs']<=protocol['cache_max_abs_tolerance'] for r in records),
            'cache_max_abs_within_tolerance':all(r['cache_max_abs']<=protocol['cache_max_abs_tolerance'] for r in records)}
    receipt={'checks':checks,'details':records,'tolerance':protocol['cache_max_abs_tolerance']}
    write(out/'technical.json',receipt)
    if not all(checks.values()): raise RuntimeError('Numerical preflight failed; no test generation permitted')
    return receipt

def generate(model, tokenizer, prompt, condition, protocol, frozen_ids):
    import torch
    ids=torch.tensor([frozen_ids],dtype=torch.long,device='cuda')
    if int(ids[0,0]) != protocol['bos_token_id']: raise ValueError('BOS encoding mismatch')
    attention=torch.ones_like(ids); cache=None; generated=[]; stop='token_cap'; stop_string=None
    routes=torch.zeros(4, dtype=torch.int64, device='cuda'); prefill_routes=None; start=time.monotonic()
    with torch.inference_mode():
        for step in range(protocol['max_new_tokens']):
            result=model(input_ids=ids if cache is None else next_input,attention_mask=attention,
                         past_key_values=cache,use_cache=True,experts_ablate=ABLATIONS[condition],logits_to_keep=1,return_dict=True)
            if not bool(torch.isfinite(result.logits).all()): raise RuntimeError('Nonfinite generation logits')
            next_input=result.logits[:,-1].argmax(dim=-1,keepdim=True)
            token=int(next_input[0,0]); generated.append(token); cache=result.past_key_values
            selected=torch.cat([selected_routes(r).reshape(-1) for r in result.routing_weights])
            routes += torch.nn.functional.one_hot(selected,num_classes=4).sum(0)
            if step==0: prefill_routes=routes.clone()
            if token in protocol['eos_token_ids']:
                stop='eos'; break
            # Decode every step so a stop spanning token boundaries is detected.
            raw=tokenizer.decode(generated,skip_special_tokens=False,clean_up_tokenization_spaces=False)
            found=[(raw.find(s),s) for s in protocol['stop_strings'] if s in raw]
            if found:
                stop='stop_string';stop_string=min(found)[1];break
            attention=torch.cat([attention,torch.ones((1,1),dtype=attention.dtype,device='cuda')],dim=1)
    raw=tokenizer.decode(generated,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    response=tokenizer.decode(generated[:-1] if stop=='eos' else generated,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    if stop=='stop_string': response=raw[:raw.index(stop_string)]
    counts=routes.tolist(); prefill=prefill_routes.tolist()
    if sum(counts)!=16*(ids.shape[1]+len(generated)-1): raise RuntimeError('Route accounting mismatch')
    blocked={'logic_ablation':0,'social_ablation':1}.get(condition)
    if blocked is not None and counts[blocked]!=0: raise RuntimeError('Ablated expert still selected')
    return {'response':response,'raw_response':raw,'response_sha256':sha(response.encode()),'generated_token_ids':generated,
            'input_token_ids_sha256':sha(json.dumps(ids[0].tolist(),separators=(',',':')).encode()),
            'stop_reason':stop,'stop_string':stop_string,'tokens':len(generated),'prompt_tokens':ids.shape[1],
            'routes':counts,'prefill_routes':prefill,'decode_routes':[a-b for a,b in zip(counts,prefill)],'seconds':time.monotonic()-start}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--artifacts',required=True,type=Path)
    p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    protocol,data,receipt=preflight(a.artifacts.resolve())
    if a.preflight_only:
        print(json.dumps({'status':'OFFLINE_PREFLIGHT_PASSED','pilot_n':32,'expected_cells':64,'all_frozen_prompt_tokens_verified':True,'bundle':receipt}));return
    prereg_sha=sha((HERE/'PREREGISTRATION.md').read_bytes());protocol_sha=sha((HERE/'protocol.json').read_bytes())
    if os.environ.get('PRAXIS_PREREG_SHA256')!=prereg_sha: raise ValueError('Committed preregistration required')
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    identity={'protocol_sha256':protocol_sha,'preregistration_sha256':prereg_sha,'data_sha256':protocol['data_sha256']}
    if (out/'run_receipt.json').exists():
        previous=json.loads((out/'run_receipt.json').read_text(encoding='utf-8'))
        if any(previous.get(k)!=v for k,v in identity.items()): raise ValueError('Cannot resume a different study')
    else:write(out/'run_receipt.json',{**identity,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    import torch
    torch.manual_seed(protocol['seed']);torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    from model_loader import load_model
    settings=json.loads((HERE/'loader_settings.json').read_text(encoding='utf-8'));settings['hf_cache_dir']=os.environ['HF_HUB_CACHE']
    model,tokenizer,loading=load_model(a.artifacts/'source',settings,dtype=protocol['dtype'])
    write(out/'loading_receipt.json',loading)
    write(out/'environment.json',{'python':platform.python_version(),'torch':torch.__version__,'cuda':torch.version.cuda,
        'gpu':torch.cuda.get_device_name(),'memory_free_total_bytes':list(torch.cuda.mem_get_info()),'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'packages':{p:importlib.metadata.version(p) for p in ['transformers','accelerate','huggingface-hub','safetensors','tokenizers','numpy','PyYAML']}})
    numerical_checks(model,tokenizer,protocol,out)
    started=time.monotonic();completed=0
    for position,row in enumerate(data['pilot']):
        order=protocol['conditions'][position%2:]+protocol['conditions'][:position%2]
        for condition in order:
            manifest=row['prompts'][condition]
            identity={'split':'pilot','id':row['id'],'condition':condition,'question_sha256':row['question_sha256'],
                      'prompt_sha256':manifest['prompt_sha256'],'protocol_sha256':protocol_sha,'gold':row['gold']}
            path=out/'cells'/f'pilot-{row["id"]}-{condition}.json'
            if path.exists():
                existing=json.loads(path.read_text(encoding='utf-8'))
                if any(existing.get(k)!=v for k,v in identity.items()) or existing.get('response_sha256')!=sha(existing['response'].encode()) or existing.get('input_token_ids_sha256')!=manifest['input_token_ids_sha256']:raise ValueError('Resume cell integrity mismatch')
                completed+=1;continue
            if time.monotonic()-started>protocol['inference_seconds_limit']:raise TimeoutError('Bounded inference runtime expired')
            result=generate(model,tokenizer,manifest['text'],'intact',protocol,manifest['input_token_ids'])
            if result['input_token_ids_sha256']!=manifest['input_token_ids_sha256'] or result['prompt_tokens']!=manifest['prompt_tokens']:raise ValueError('Generated input identity mismatch')
            write(path,{**identity,**result});completed+=1
            print(json.dumps({'split':'pilot','id':row['id'],'condition':condition,'tokens':result['tokens'],'stop_reason':result['stop_reason'],'seconds':round(result['seconds'],2),'completed':completed}),flush=True)
    write(out/'pilot_completion.json',{'split':'pilot','complete':True,'cells':completed,'protocol_sha256':protocol_sha,'memory_free_total_bytes':list(torch.cuda.mem_get_info()),'peak_allocated_bytes':torch.cuda.max_memory_allocated()})
    write(out/'generation_complete.json',{'status':'GENERATION_COMPLETE','cells':completed,'protocol_sha256':protocol_sha,'heldout_test_cells':0,'automatic_followup':False})

if __name__=='__main__':main()
