"""PX121 inert shell-AST extraction. Never executes downloaded commands."""
import pathlib,json,re,sys,collections,hashlib
import bashlex
from extract import samples,render,PROMPT
P=pathlib.Path(sys.argv[1]);O=pathlib.Path(__file__).resolve().parent/'results';snap=json.loads((P/'data__human__human_snapshot.json').read_text());lookup={x['session_id']:x for x in snap['completions']}
def atoms(raw):
 try:nodes=bashlex.parse(raw)
 except Exception:return [],False
 out=[]
 def walk(n):
  if n.kind=='command':
   ws=[w.word for w in n.parts if w.kind=='word']
   if ws:
    verb=ws[0].split('/')[-1]
    if re.fullmatch(r'[a-zA-Z0-9_.+-]+',verb) and verb not in {'task','clear','exit','history'}:out.append([verb,len(ws)-1])
   return
  for k in ['parts','list']:
   for child in getattr(n,k,[]):
    if hasattr(child,'kind'):walk(child)
 for n in nodes:walk(n)
 return out,True
rows=[];audit=[]
for f in json.loads((P/'human_manifest.json').read_text()):
 if '/intercode-ctf/' not in f['source'] or '_partial' in f['source']:continue
 sid=re.search(r'session_\d+',f['source'])[0];meta=lookup[sid];s=samples(f['local'],True)[0];cmds=[];bad=0
 rawinputs='\n'.join(v for k,v in s['store'].get('HumanAgentState:logs',{}).items() if k.endswith('.input'))
 for k,v in sorted(s['store'].get('HumanAgentState:logs',{}).items()):
  if not k.endswith('.output'):continue
  for ln,invalid in render(v):
   m=PROMPT.match(ln)
   if m:
    if invalid or m[1] not in rawinputs:bad+=1;continue
    cmds.append(m[1])
 rows.append({'id':sid,'task':meta['task_id'],'group':meta['user_id'],'family':'human','label':0,'shell_commands':cmds,'unreconstructed_prompt_lines':bad})
for f in json.loads((P/'ai_manifest.json').read_text()):
 fam=next(v for k,v in {'83d0a1kx':'anthropic','he8g4w75':'openai','pimsdb6k':'google'}.items() if k in f['source'])
 for s in samples(f['local'],False):
  cmds=[];other=collections.Counter()
  for m in s['messages']:
   for t in m.get('tool_calls') or []:
    args=t.get('arguments',{})
    if t.get('function')=='bash' and isinstance(args.get('cmd'),str):cmds.append(args['cmd'])
    else:other[t.get('function','unknown')]+=1
  rid=fam+':'+str(s['id']);rows.append({'id':rid,'task':str(s['id']),'group':rid,'family':fam,'label':1,'shell_commands':cmds,'other_tools':dict(other),'unreconstructed_prompt_lines':0})
for r in rows:
 seq=[];fail=0
 for c in r['shell_commands']:
  a,ok=atoms(c);seq+=a;fail+=not ok
 r['atoms']=seq;r['parse_failures']=fail;r['fingerprint']=hashlib.sha256(json.dumps(seq[:10]).encode()).hexdigest()
(O/'PX121_records.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'total':dict(collections.Counter(r['family'] for r in rows)),'at_least_three':dict(collections.Counter(r['family'] for r in rows if len(r['atoms'])>=3)),'human_experts':sorted(set(r['group'] for r in rows if not r['label']))},indent=2))
