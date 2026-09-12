"""Freeze public validation data and static upstream demonstrations; no code execution or network."""
import argparse, ast, csv, hashlib, json
from collections import Counter
from pathlib import Path
REVISION='beb92deb932d67a6319cc7ca71d8056ececc47d2'
PINS={
 'val_text.txt':'d969af3d040d2f0342351bd8c76403502e95fef709c5b0ef22ac826bcba0c668',
 'val_labels.txt':'e7457c92d43c7f267cf4f21d0ccb0f83e7ecbbc29793e853a7d71446a902dbfb',
 'micro_empathy.py':'07d3676823964cbb69b9f1ae873ff9f15b762295729ea09221bec8014e54b3d3',
 'socket_prompts_pinned.csv':'2157c7df18b9cdffb929493aefa5d8cb8b0f938f0dc6a1fbb2e4ebdd3aa9db89'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def data(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def freeze(path,x):
 path.parent.mkdir(parents=True,exist_ok=True);raw=data(x)
 if path.exists():
  if path.read_bytes()!=raw:raise ValueError('Frozen artifact differs: '+str(path))
 else:
  with path.open('xb') as f:f.write(raw)
def prepare(source,out):
 receipts=[]
 for name,expected in PINS.items():
  raw=(source/name).read_bytes()
  if sha(raw)!=expected:raise ValueError('Source hash differs: '+name)
  receipts.append({'file':name,'sha256':expected,'bytes':len(raw)})
 tree=ast.parse((source/'micro_empathy.py').read_text(encoding='utf-8-sig'))
 assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fewshot_samples' for t in n.targets))
 demonstrations=ast.literal_eval(assignment.value)
 if [d['role'] for d in demonstrations]!=['user','assistant']*3:raise ValueError('Three source demonstrations required')
 with (source/'socket_prompts_pinned.csv').open(encoding='utf-8-sig',newline='') as f:
  row=next(r for r in csv.DictReader(f) if r['task']=='empathy#empathy_bin')
 question=row['question']
 if question!='For the sentence: "{text}", is it expressing empathy?' or ast.literal_eval(row['options'])!=['No','Yes']:
  raise ValueError('Source prompt differs')
 prompt={'fewshot_messages':demonstrations,'question_template':question,
         'candidates':[{'label':'not empathy','text':'The answer is No.'},{'label':'empathy','text':'The answer is Yes.'}],
         'serialization':'pinned tokenizer.apply_chat_template, add_generation_prompt=True, no extra system message',
         'continuation':'literal full answer string; no extra leading space or chat-end token',
         'source_commit':'275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7',
         'socket_prompt_commit':'2f4fffff01a591346bf823df59a515eabb764b1d'}
 texts=[t.strip() for t in (source/'val_text.txt').read_text(encoding='utf-8').splitlines()]
 labels=[t.strip() for t in (source/'val_labels.txt').read_text(encoding='utf-8').splitlines()]
 if len(texts)!=186 or len(labels)!=186 or Counter(labels)!=Counter({'empathy':87,'not empathy':99}):raise ValueError('Validation source shape differs')
 rows=[]
 for index,(text,label) in enumerate(zip(texts,labels)):
  text_sha=sha(text.encode());key=sha(f'006-empathy-validation-v1:{index}:{text_sha}'.encode())
  rows.append({'id':f'socket-empathy-val-{index:03d}-{text_sha[:12]}','source_row':index,'text':text,'gold':label,'text_sha256':text_sha,'selection_hash':key})
 selected=[]
 for label in ('not empathy','empathy'):
  selected+=sorted([r for r in rows if r['gold']==label],key=lambda r:(r['selection_hash'],r['source_row']))[:32]
 selected.sort(key=lambda r:(r['selection_hash'],r['source_row']))
 if len({r['text'] for r in selected})!=64:raise ValueError('Duplicate selected text')
 fixture={'dataset':'Blablablab/SOCKET','task':'empathy#empathy_bin','revision':REVISION,'split':'validation',
          'qualification_only':True,'items':selected}
 freeze(out/'fixture.json',fixture);freeze(out/'prompt.json',prompt)
 lock={'dataset':fixture['dataset'],'task':fixture['task'],'revision':REVISION,'split':'validation',
       'source_receipts':receipts,'fixture_sha256':sha(data(fixture)),'prompt_sha256':sha(data(prompt)),
       'selected_ids':[r['id'] for r in selected],'label_counts':dict(Counter(r['gold'] for r in selected)),
       'selection':'32 per label by SHA256(006-empathy-validation-v1:{zero_based_row}:{sha256(stripped_text)}); final same hash order',
       'source_validation_label_counts':dict(Counter(labels)),
       'test_files_read':False,'training_files_read':False,'license':'CC-BY-4.0 dataset; see ATTRIBUTION.md'}
 freeze(out/'data_lock.json',lock)
 print(json.dumps({'n':64,'fixture_sha256':lock['fixture_sha256'],'prompt_sha256':lock['prompt_sha256'],'test_files_read':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.source_dir,a.out)
