"""Read inert archived logs; publish no raw commands, responses or prompts."""
import argparse, collections, datetime, hashlib, json, math, pathlib, zipfile

HERE = pathlib.Path(__file__).resolve().parent
FAMILIES = {'qwen3:4b':'alibaba','qwen2.5:1.5b':'alibaba',
 'qwen2.5:32b':'alibaba','qwen3:30b':'alibaba','llama3.1:8b':'meta',
 'gemma3:4b':'google','gemma3:27b':'google',
 'deepseek-r1:32b':'deepseek','deepseek-r1:1.5b':'deepseek'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')

def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=pathlib.Path,required=True)
 p.add_argument('--human',type=pathlib.Path);a=p.parse_args()
 rows=[];counts=collections.Counter();cells=collections.Counter();timing=[]
 with zipfile.ZipFile(a.archive) as z:
  for name in sorted(z.namelist()):
   parts=name.split('/')
   if len(parts)!=6 or parts[0]!='Logs_final' or not name.endswith('.json'):continue
   counts['files']+=1;raw=json.loads(z.read(name));turns=[];reason=None
   for i,t in enumerate(raw[1:]):
    if not (isinstance(t,list) and len(t)==3 and all(isinstance(x,list) and len(x)==2 for x in t)):
     reason='malformed_turn';break
    if not isinstance(t[2][1],str) or not t[2][1].strip():reason='missing_command';break
    if not isinstance(t[1][0],str):reason='missing_output';break
    ts=[x[1] if isinstance(x[1],(int,float)) and math.isfinite(x[1]) and x[1]>=0 else None for x in t[:2]]
    turns.append({'i':i,'c':t[2][1].strip(),'o':t[1][0],'t':ts})
   if reason:counts['excluded_'+reason]+=1;continue
   if len(turns)<10:counts['excluded_shorter_than_10']+=1;continue
   model=parts[4];assert model in FAMILIES
   rid=hashlib.sha256(name.encode()).hexdigest()[:24]
   fp=hashlib.sha256('\n'.join(t['c'] for t in turns[:10]).encode()).hexdigest()
   rows.append({'id':rid,'fp':fp,'family':FAMILIES[model],'model':model,'prompt':parts[1],
     'env':parts[3],'budget':parts[2],'turns':turns})
   cells[(model,parts[1],parts[3],parts[2])]+=1;counts['included']+=1
   ts=[t['t'] for t in turns]
   good=all(all(v is not None for v in t) for t in ts)
   timing.append({'id':rid,'n':len(ts),'complete':good,
    'first_clock_strictly_increasing':good and all(ts[i][0]>ts[i-1][0] for i in range(1,len(ts))),
    'second_clock_strictly_increasing':good and all(ts[i][1]>ts[i-1][1] for i in range(1,len(ts))),
    'second_after_first':good and all(t[1]>=t[0] for t in ts)})
 audit={'source_url':'https://zenodo.org/records/20818246','archive_sha256':sha(a.archive),
  'counts':dict(counts),'families':dict(collections.Counter(r['family'] for r in rows)),
  'models':dict(collections.Counter(r['model'] for r in rows)),
  'cells':[{'model':k[0],'prompt':k[1],'env':k[2],'budget':k[3],'n':v} for k,v in sorted(cells.items())],
  'duplicate_first10_excess':len(rows)-len(set(r['fp'] for r in rows)),
  'timing_diagnostics':{k:sum(t[k] for t in timing) for k in timing[0] if k not in {'id','n'}},
  'timing_interpretation':'Monotonicity alone does not establish duration or elapsed-clock semantics. Timing features diagnostic only; no binary operator timing claim.'}
 if a.human:
  h=json.loads(a.human.read_text(encoding='utf-8-sig'));groups=collections.defaultdict(list);bad=0
  for r in h:
   try:t=datetime.datetime.fromisoformat(r['timestamp'].replace('Z','+00:00'))
   except (ValueError,KeyError,TypeError):bad+=1;continue
   groups[(r['participant'],str(t.date()))].append(t)
  gaps=[(b-a).total_seconds() for ts in groups.values() for a,b in zip(sorted(ts),sorted(ts)[1:])]
  audit['human']={'file_sha256':sha(a.human),'rows':len(h),'fields':sorted(h[0]),
    'bad_timestamp_rows':bad,'participant_day_groups':len(groups),'gaps':len(gaps),
    'zero_gaps':sum(g==0 for g in gaps),'integer_second_gaps':sum(g==int(g) for g in gaps),
    'keystrokes_present':False,'output_completion_timestamps_present':False,
    'binary_timing_decision':'Not comparable to AI per-turn internal measurements; no classifier fit.'}
 save(HERE/'cache/records.json',rows);save(HERE/'evidence/DATA_AUDIT.json',audit)
 save(HERE/'evidence/TIMING_AUDIT.json',timing)
 print(json.dumps({k:v for k,v in audit.items() if k!='cells'},indent=2))

if __name__=='__main__':main()
