import pathlib,json,gzip,zipfile,io,re,sys,hashlib,collections
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'aivh_gambit_20261005'))
from common import command
P=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else None;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
# A line renderer deliberately supports horizontal editing only. Unsupported
# controls invalidate a line; cursor movement across lines is not reconstructed.
ANSI=re.compile(r'\x1b\[([0-9;?]*)([@-~])|\x1b\][^\x07]*(?:\x07)')
PROMPT=re.compile(r'^(?:\([^\r\n]*\) )?[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+:[^\r\n]*?[#$] (.*)$')
def render(raw):
 for source in raw.split('\n'):
  line=[];pos=0;bad=False;i=0
  while i<len(source):
   ch=source[i]
   if ch=='\x1b':
    m=ANSI.match(source,i)
    if not m:bad=True;i+=1;continue
    args,code=m.groups();i=m.end()
    if code is None or code=='m' or (code in 'hl' and args.startswith('?')):continue
    n=int(args) if args.isdigit() else 1
    if code=='C':pos+=n
    elif code=='D':pos=max(0,pos-n)
    elif code=='G':pos=max(0,n-1)
    elif code=='K':
     if args in ('','0'):line=line[:pos]
     elif args=='2':line=[]
     else:bad=True
    elif code in 'HJ' and not ''.join(line).strip():continue
    else:bad=True
    continue
   i+=1
   if ch=='\r':pos=0;continue
   if ch=='\x08':pos=max(0,pos-1);continue
   if ch=='\x07':continue
   if ord(ch)<32 or ord(ch)==127:bad=True;continue
   if pos>10000:bad=True;break
   if pos>=len(line):line.extend(' '*(pos-len(line)+1))
   line[pos]=ch;pos+=1
  yield ''.join(line).rstrip(),bad

def samples(file,human):
 path=pathlib.Path(file);path=path if path.is_absolute() else P/path
 b=path.read_bytes();z=zipfile.ZipFile(io.BytesIO(gzip.decompress(b) if human else b))
 return [json.loads(z.read(k)) for k in z.namelist() if k.startswith('samples/') and k.endswith('.json')]

def main():
 snap=json.loads((P/'data__human__human_snapshot.json').read_text());lookup={x['session_id']:x for x in snap['completions']};rows=[];audit=[];examples=[]
 for f in json.loads((P/'human_manifest.json').read_text()):
  sid=re.search(r'session_\d+',f['source'])[0];meta=lookup.get(sid);a={'source':f['source'],'session':sid,'mapped':bool(meta),'partial':'_partial' in f['source']}
  if not meta or a['partial']:audit.append(a);continue
  ss=samples(f['local'],True)
  if len(ss)!=1:
   a['sample_count']=len(ss);a['exclusion']='expected_one_sample';audit.append(a);continue
  s=ss[0];cs=[];rawcs=[];prompts=0;rejected=0
  for k,v in sorted(s['store'].get('HumanAgentState:logs',{}).items()):
   if not k.endswith('.output'):continue
   for ln,bad in render(v):
    m=PROMPT.match(ln)
    if not m:continue
    prompts+=1
    if bad:rejected+=1;continue
    c=command(m[1])
    if c:cs.append(c);rawcs.append(m[1]);examples.append({'session':sid,'task':meta['task_id'],'log':k,'echo':ln,'normalized':c})
  a.update(task=meta['task_id'],expert=meta['user_id'],prompts=prompts,rejected_editing=rejected,eligible_commands=len(cs));audit.append(a)
  rows.append({'id':sid,'task':meta['task_id'],'group':meta['user_id'],'label':0,'family':'human','commands':cs,'raw_commands':rawcs,'benchmark':f['source'].split('/')[3]})
 for f in json.loads((P/'ai_manifest.json').read_text()):
  for s in samples(f['local'],False):
   cs=[];rawcs=[];functions=collections.Counter()
   for m in s.get('messages',[]):
    for tc in m.get('tool_calls') or []:
     functions[tc.get('function','unknown')]+=1
     args=tc.get('arguments',{});raw=args.get('cmd',args.get('command')) if isinstance(args,dict) else None
     c=command(raw)
     if c:cs.append(c);rawcs.append(raw)
   family={'83d0a1kx':'anthropic','he8g4w75':'openai','pimsdb6k':'google'};fam=next(v for k,v in family.items() if k in f['source']);tid=str(s['id']);rid=fam+':'+tid
   rows.append({'id':rid,'task':tid,'group':rid,'label':1,'family':fam,'commands':cs,'raw_commands':rawcs,'benchmark':'intercode-ctf'})
   audit.append({'source':f['source'],'task':tid,'family':fam,'eligible_commands':len(cs),'tool_functions':dict(functions)})
 (OUT/'records.json').write_text(json.dumps(rows,indent=2));(OUT/'extraction_audit.json').write_text(json.dumps(audit,indent=2));(OUT/'human_command_evidence.json').write_text(json.dumps(examples,indent=2))
 print(json.dumps({'rows':len(rows),'human':sum(r['label']==0 for r in rows),'families':dict(collections.Counter(r['family'] for r in rows)),'human_commands':len(examples),'human_tasks_sample':[r['task'] for r in rows[:3]],'ai_tasks_sample':[r['task'] for r in rows if r['label']==1][:3]},indent=2))
if __name__=='__main__':main()
