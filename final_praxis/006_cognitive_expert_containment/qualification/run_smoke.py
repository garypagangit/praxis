"""Pinned public MiCRo CPU qualification; no training or new routing defense."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, re, sys, time, urllib.request
from decimal import Decimal
from pathlib import Path

HERE=Path(__file__).resolve().parent

def digest(data):return hashlib.sha256(data).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');temporary.replace(path)
def obtain(url,path,expected=None):
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FinalPraxis006'}),timeout=60) as response:data=response.read(4_000_001)
        if len(data)>4_000_000:raise ValueError('Source file exceeded bound')
        path.write_bytes(data)
    data=path.read_bytes()
    if expected and digest(data)!=expected:raise ValueError('Pinned source hash mismatch: '+str(path))
    return data
def answer(text):
    matches=re.findall(r'####\s*([-+]?\d[\d,]*(?:\.\d+)?)\s*\.?\s*$',text.strip())
    return format(Decimal(matches[-1].replace(',','')).normalize(),'f') if matches else None

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    settings=json.loads((HERE/'settings.json').read_text());receipts=json.loads((HERE/'source_receipts.json').read_text())
    prereg=HERE/'PREREG_SMOKE.md';prereg_sha=digest(prereg.read_bytes())
    if os.environ.get('PRAXIS_PREREG_SHA256')!=prereg_sha:raise ValueError('Frozen qualification preregistration required')
    source=out/'source_repos';source.mkdir(exist_ok=True)
    needed={'models/micro_llama.py','models/modules.py','repo_config.yml'}
    for row in receipts:
        if row['file'] in needed:
            data=obtain(row['url'],out/'source_downloads'/row['file'],row['sha256'])
            target=source/row['file'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    original=(source/'models/micro_llama.py').read_text()
    needle='self.config._attn_implementation = "flash_attention_2"'
    if original.count(needle)!=1:raise ValueError('Unexpected constructor: portability patch not applicable')
    patched=original.replace(needle,'self.config._attn_implementation = "sdpa"')
    (source/'models/micro_llama.py').write_text(patched,encoding='utf-8')
    # Restore the original verified bytes on a future resume before applying patch.
    write(out/'portability.json',{'original_sha256':digest(original.encode()),'patched_sha256':digest(patched.encode()),
        'change':'FlashAttention2 constructor default replaced with SDPA for CPU; no weight or routing-math modification'})
    sys.path.insert(0,str(source))
    import torch
    from transformers import AutoConfig,AutoTokenizer
    from models.micro_llama import MiCRoLlama,MiCRoLlamaConfig
    torch.set_num_threads(4);torch.manual_seed(20260912)
    dependencies=json.loads((HERE/'loader_dependencies.json').read_text())
    base=dependencies['base'];tok=dependencies['tokenizer']
    config_data=AutoConfig.from_pretrained(base['id'],revision=base['revision'],trust_remote_code=False).to_dict()
    config_data['config_path']=str(source/'repo_config.yml');config_data['ablate']=['none']
    config=MiCRoLlamaConfig(**config_data)
    model,info=MiCRoLlama.from_pretrained(settings['model'],revision=settings['model_revision'],config=config,
        torch_dtype=torch.float32,low_cpu_mem_usage=True,use_safetensors=True,output_loading_info=True)
    model=model.float().eval()
    if any(info.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']):
        write(out/'loading_failure.json',info);raise RuntimeError('Checkpoint did not load exactly')
    tokenizer=AutoTokenizer.from_pretrained(tok['id'],revision=tok['revision'],trust_remote_code=False)
    tokenizer.pad_token_id=2
    write(out/'environment.json',{'torch':torch.__version__,'transformers':importlib.metadata.version('transformers'),
        'model':settings['model'],'revision':settings['model_revision'],'parameters':sum(p.numel() for p in model.parameters()),
        'layers':len(model.layers),'expanded_layers':model.config.num_hidden_layers,'device':'cpu','dtype':'float32',
        'preregistration_sha256':prereg_sha,'loading':info})
    prompt=tokenizer('A simple arithmetic question: 2 + 2 =',return_tensors='pt')
    with torch.inference_mode():
        model.config._attn_implementation='sdpa';one=model(**prompt,use_cache=False,experts_ablate=['none']).logits
        repeat=model(**prompt,use_cache=False,experts_ablate=['none']).logits
        model.config._attn_implementation='eager';eager=model(**prompt,use_cache=False,experts_ablate=['none']).logits
        model.config._attn_implementation='sdpa'
    checks={'finite':bool(torch.isfinite(one).all()),'repeat_max_abs':float((one-repeat).abs().max()),
        'eager_sdpa_max_abs':float((one-eager).abs().max()),'last_top_token_equal':bool(one[0,-1].argmax()==eager[0,-1].argmax())}
    write(out/'numerical_checks.json',checks)
    if not checks['finite'] or checks['repeat_max_abs']>1e-6 or checks['eager_sdpa_max_abs']>1e-3 or not checks['last_top_token_equal']:
        raise RuntimeError('Numerical portability qualification failed')
    raw=obtain(settings['gsm8k_url'],out/'gsm8k_test.jsonl',settings['gsm8k_sha256'])
    rows=[json.loads(line) for line in raw.decode().splitlines() if line.strip()][:8]
    outputs=[];start=time.monotonic()
    for index,row in enumerate(rows):
        for condition,ablation in [('baseline',['none']),('social_ablation',['social'])]:
            path=out/'cells'/f'{index:03d}-{condition}.json'
            if path.exists():outputs.append(json.loads(path.read_text()));continue
            if time.monotonic()-start>2400:raise TimeoutError('Bounded CPU study elapsed')
            text=row['question']+'\nSolve the problem. End with #### followed by the final numeric answer.'
            ids=tokenizer.apply_chat_template([{'role':'user','content':text}],add_generation_prompt=True,return_tensors='pt')
            attention=torch.ones_like(ids);cache=None;generated=[];routes=[0,0,0,0];beg=time.monotonic();eos=tokenizer.eos_token_id
            with torch.inference_mode():
                for step in range(128):
                    result=model(input_ids=ids if cache is None else torch.tensor([[generated[-1]]]),attention_mask=attention,
                        past_key_values=cache,use_cache=True,experts_ablate=ablation,logits_to_keep=1,return_dict=True)
                    if not bool(torch.isfinite(result.logits).all()):raise RuntimeError('Nonfinite logits')
                    next_token=int(result.logits[0,-1].argmax());generated.append(next_token);cache=result.past_key_values
                    for routing in result.routing_weights:
                        selected=routing.argmax(dim=-1).flatten()
                        for expert in range(4):routes[expert]+=int((selected==expert).sum())
                    if next_token==eos:break
                    attention=torch.cat([attention,torch.ones((1,1),dtype=attention.dtype)],dim=1)
            decoded=tokenizer.decode(generated,skip_special_tokens=True);predicted=answer(decoded);gold=answer(row['answer'])
            record={'id':index,'condition':condition,'question_sha256':digest(row['question'].encode()),'prompt':text,
                'response':decoded,'answer':predicted,'gold':gold,'correct':predicted is not None and predicted==gold and generated[-1]==eos,
                'tokens':len(generated),'truncated':len(generated)==128 and generated[-1]!=eos,'routes_logic_social_world_language':routes,
                'seconds':time.monotonic()-beg,'preregistration_sha256':prereg_sha}
            if condition=='social_ablation' and routes[1]!=0:raise RuntimeError('Ablated social expert still selected')
            write(path,record);outputs.append(record)
            print(json.dumps({'id':index,'condition':condition,'valid_answer':predicted is not None,'tokens':len(generated),'seconds':record['seconds']}),flush=True)
    paired={i:{r['condition']:r for r in outputs if r['id']==i} for i in range(8)}
    base_correct=sum(x['baseline']['correct'] for x in paired.values())
    summary={'status':'COMPLETED_FEASIBILITY','n':8,'baseline_correct':base_correct,
        'ablation_correct':sum(x['social_ablation']['correct'] for x in paired.values()),
        'correct_to_wrong':sum(x['baseline']['correct'] and not x['social_ablation']['correct'] for x in paired.values()),
        'wrong_to_correct':sum(not x['baseline']['correct'] and x['social_ablation']['correct'] for x in paired.values()),
        'invalid_answers':sum(r['answer'] is None for r in outputs),'truncated':sum(r['truncated'] for r in outputs),
        'capability_gate':2<=base_correct<=6,'novel_method_tested':False,'paper_score_reproduction_claimed':False}
    write(out/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
