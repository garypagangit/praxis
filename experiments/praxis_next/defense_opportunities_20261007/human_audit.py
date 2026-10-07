"""Measure archived terminal controls; do not confuse input bytes with shell commands."""
import argparse,pathlib,json,gzip,zipfile,io,re,collections
import numpy as np
from screen import HERE,save,sha
def sample(path,human):
 b=pathlib.Path(path).read_bytes();z=zipfile.ZipFile(io.BytesIO(gzip.decompress(b) if human else b))
 return [json.loads(z.read(k)) for k in z.namelist() if k.startswith('samples/') and k.endswith('.json')]
def run(root):
 out=[];source={}
 for f in json.loads((root/'human_manifest.json').read_text()):
  if '/intercode-ctf/' not in f['source'] or '_partial' in f['source']:continue
  sid=re.search(r'session_\d+',f['source'])[0];source[sid]=sha(pathlib.Path(f['local']));s=sample(f['local'],True)[0];logs=s['store'].get('HumanAgentState:logs',{})
  for k,v in logs.items():
   if not k.endswith('.timing'):continue
   stem=k[:-7];inp=logs.get(stem+'.input','').split('\n',1)[-1].encode();output=logs.get(stem+'.output','').split('\n',1)[-1].encode();counts=collections.Counter();gaps=[];sizes=[]
   for line in v.splitlines():
    fields=line.split()
    if len(fields)==3 and fields[0] in {'I','O'}:
     counts[fields[0]]+=int(fields[2])
     if fields[0]=='I':gaps.append(float(fields[1]));sizes.append(int(fields[2]))
   aligned=lambda b,n:len(b)>=n and (not b[n:] or b[n:].startswith(b'\nScript done on '))
   out.append({'session':sid,'input_aligned':aligned(inp,counts['I']),'output_aligned':aligned(output,counts['O']),'input_bytes':counts['I'],'backspace_delete_bytes':inp[:counts['I']].count(b'\x08')+inp[:counts['I']].count(b'\x7f'),'tab_bytes':inp[:counts['I']].count(b'\t'),'escape_bytes':inp[:counts['I']].count(b'\x1b'),'carriage_returns':inp[:counts['I']].count(b'\r'),'input_events':len(gaps),'single_byte_input_events':sum(x==1 for x in sizes),'median_input_event_delta':float(np.median(gaps)) if gaps else None})
 ai=[]
 for f in json.loads((root/'ai_manifest.json').read_text()):
  source[f['source']]=sha(pathlib.Path(f['local']))
  for s in sample(f['local'],False):
   events=s.get('events',[]);tool=[x for x in events if x.get('event')=='tool'];ai.append({'id':str(s['id']),'event_types':dict(collections.Counter(x.get('event') for x in events)),'tool_events':len(tool),'tool_events_with_timestamp':sum(bool(x.get('timestamp')) for x in tool),'terminal_input_logs':any(str(k).endswith('.input') for k in s.get('store',{}))})
 save(HERE/'evidence/HUMAN_MEASUREMENT.json',{'human':out,'ai':ai,'source_hashes':source,'code_sha256':sha(pathlib.Path(__file__)),'interpretation':'Human input controls and script I/O timing exist. They include interactive-program input, editing, autocomplete, paste and terminal navigation, not independently adjudicated typos. AI tool-event timestamps are a different observation layer; missing AI keystrokes are structural missingness, not zero typo behavior. Timing fields give per-event deltas, not necessarily output-to-next-command latency. No new binary timing classifier justified by this audit.'})
 print('human logs',len(out),'sessions',len(set(r['session'] for r in out)),'aligned',sum(r['input_aligned'] and r['output_aligned'] for r in out),'with delete',sum(r['backspace_delete_bytes']>0 for r in out),'AI',len(ai),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=pathlib.Path,required=True);run(p.parse_args().data)
