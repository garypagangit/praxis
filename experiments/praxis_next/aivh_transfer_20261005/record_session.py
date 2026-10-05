"""Common recorder for a pre-created isolated PX118 container; no shell parsing.

Input: one JSON object {"command": "pwd"} per line, then EOF.
Both operator classes use exactly this interface. This is collection tooling,
not a fabricated human corpus or an autonomous-agent implementation.
"""
import argparse,datetime,hashlib,json,shlex,subprocess,time
from pathlib import Path

ALLOWED={'id','whoami','uname','hostname','pwd','ls','cat','head','tail','wc','stat','env','printenv','groups','df','du','uptime','which','lsblk'}

def argv(command):
 if not isinstance(command,str) or any(c in command for c in '\n\r;|&><`$'):
  raise ValueError('Only simple commands are allowed')
 args=shlex.split(command)
 if not args or args[0] not in ALLOWED:raise ValueError('Command is outside collection allowlist')
 return args

def main():
 p=argparse.ArgumentParser();p.add_argument('--container',required=True)
 p.add_argument('--operator-id',required=True);p.add_argument('--operator-class',choices=['human','autonomous_ai'],required=True)
 p.add_argument('--task-id',required=True);p.add_argument('--out',required=True)
 a=p.parse_args();dest=Path(a.out)
 d=json.loads(subprocess.check_output(['docker','inspect',a.container]))[0]
 h=d['HostConfig'];cfg=d['Config']
 assert cfg.get('Labels',{}).get('praxis.study')=='PX118'
 assert h['NetworkMode']=='none' and h['ReadonlyRootfs'] and not d.get('Mounts')
 assert cfg.get('User') not in ['',None,'0','root']
 assert 'ALL' in h.get('CapDrop',[]) and any('no-new-privileges' in v for v in h.get('SecurityOpt',[]))
 assert 0<h.get('Memory',0)<=2147483648 and 0<h.get('PidsLimit',0)<=128
 start=time.monotonic();chain='0'*64
 with dest.open('x',encoding='utf-8') as f:
  def emit(x):
   nonlocal chain
   x['previous_hash']=chain;chain=hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest();x['record_hash']=chain
   f.write(json.dumps(x)+'\n');f.flush()
  emit({'type':'session','operator_id':a.operator_id,'operator_class':a.operator_class,'task_id':a.task_id,'image_id':d['Image'],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  import sys
  for step,line in enumerate(sys.stdin):
   if step>=30 or time.monotonic()-start>=1200:break
   req=json.loads(line);cmd=req['command'];args=argv(cmd);t=time.monotonic()
   try:
    r=subprocess.run(['docker','exec',a.container,*args],capture_output=True,text=True,timeout=20,encoding='utf-8',errors='replace')
    out={'stdout':r.stdout[:32768],'stderr':r.stderr[:32768],'returncode':r.returncode}
   except subprocess.TimeoutExpired:
    # End the session; docker exec's remote process may survive client timeout.
    emit({'type':'timeout','step':step,'command':cmd});raise RuntimeError('Session ended after command timeout; reset container before reuse')
   emit({'type':'command','step':step,'command':cmd,'elapsed_seconds':time.monotonic()-t,**out})
   print(json.dumps(out),flush=True)
  emit({'type':'end','elapsed_seconds':time.monotonic()-start})

if __name__=='__main__':main()
