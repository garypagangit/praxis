"""Frozen, bounded inference; input directory has no outcome labels."""
import argparse, json, os, time, platform, importlib.metadata
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seconds',type=int,default=1200);args=ap.parse_args();args.out.mkdir(exist_ok=True)
    started=time.monotonic()
    import torch
    from PIL import Image
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
    model_id='Qwen/Qwen2.5-VL-7B-Instruct';revision='cc594898137f460bfe9f0759e9844b3ce807cfb5'
    torch.manual_seed(9801)
    model=Qwen2_5_VLForConditionalGeneration.from_pretrained(model_id,revision=revision,torch_dtype=torch.bfloat16,device_map='auto',attn_implementation='sdpa')
    processor=AutoProcessor.from_pretrained(model_id,revision=revision,min_pixels=256*28*28,max_pixels=1024*28*28)
    metadata={'model':model_id,'revision':revision,'device':torch.cuda.get_device_name(0),'python':platform.python_version(),
              'versions':{p:importlib.metadata.version(p) for p in ['torch','transformers','accelerate','pillow']},
              'load_seconds':time.monotonic()-started,'device_map':str(model.hf_device_map)}
    (args.out/'runtime.json').write_text(json.dumps(metadata,indent=2))
    requests=json.loads((args.inputs/'requests.json').read_text())
    # Interleave both studies, then diagnostic and representative windows, preserving pairs.
    requests.sort(key=lambda r:(0 if r['experiment']=='PX-099' else 1 if int(r['id'].split('_')[1])>=16 else 2,r['id']))
    with (args.out/'responses.jsonl').open('w') as handle:
        for r in requests:
            if time.monotonic()-started>args.seconds:break
            began=time.monotonic();record={'id':r['id'],'experiment':r['experiment'],'mode':r['mode']}
            try:
                contents=[];images=None
                if r['mode']=='image':
                    contents.append({'type':'image'});images=[Image.open(args.inputs/r['image']).convert('RGB')]
                contents.append({'type':'text','text':r['prompt']})
                text=processor.apply_chat_template([{'role':'user','content':contents}],tokenize=False,add_generation_prompt=True)
                inputs=processor(text=[text],images=images,padding=True,return_tensors='pt')
                record['input_tokens']=inputs['input_ids'].shape[1]
                if record['input_tokens']>8192:
                    record['status']='SKIPPED_CONTEXT_LIMIT'
                else:
                    inputs=inputs.to(model.device)
                    with torch.inference_mode():
                        output=model.generate(**inputs,max_new_tokens=r['max_new_tokens'],do_sample=False)
                    raw=processor.batch_decode(output[:,inputs['input_ids'].shape[1]:],skip_special_tokens=True)[0]
                    record['raw']=raw;record['output_tokens']=int(output.shape[1]-inputs['input_ids'].shape[1])
                    try:
                        value=json.loads(raw.strip());assert isinstance(value,dict)
                        if r['experiment']=='PX-098':assert value.get('answer') in ['yes','no','insufficient'] and isinstance(value.get('reason'),str)
                        else:assert isinstance(value.get('intervals'),list) and isinstance(value.get('insufficient_evidence'),bool)
                        record['parsed']=value;record['status']='PARSED'
                    except (ValueError,AssertionError,TypeError):record['status']='INVALID_JSON_OR_SCHEMA'
            except Exception as e:
                record['status']='ERROR';record['error']=str(e)[:1000]
                if torch.cuda.is_available():torch.cuda.empty_cache()
            record['seconds']=time.monotonic()-began
            record['peak_gpu_allocated_bytes']=torch.cuda.max_memory_allocated()
            handle.write(json.dumps(record)+'\n');handle.flush();print(json.dumps(record),flush=True)
    metadata['total_seconds']=time.monotonic()-started
    (args.out/'runtime.json').write_text(json.dumps(metadata,indent=2))

if __name__=='__main__':main()
