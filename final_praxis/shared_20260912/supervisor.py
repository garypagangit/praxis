"""Run a bounded cloud study and checkpoint receipts to S3 independently of a client."""
from __future__ import annotations
import argparse, hashlib, json, os, signal, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import boto3
from botocore.config import Config

def utc():return datetime.now(timezone.utc).isoformat()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path)
    p.add_argument('--run-id',required=True);p.add_argument('--prereg',required=True,type=Path)
    p.add_argument('--prereg-sha256',required=True);p.add_argument('--seconds',type=int,default=25200)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if not 1<=a.seconds<=27000:raise ValueError('Bounded runtime required')
    if not a.run_id.replace('-','').replace('_','').isalnum():raise ValueError('Invalid run ID')
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:raise ValueError('Explicit study command required')
    root=a.root.resolve();root.mkdir(parents=True,exist_ok=True)
    if hashlib.sha256(a.prereg.read_bytes()).hexdigest()!=a.prereg_sha256:raise ValueError('Preregistration hash mismatch')
    status_path=root/'cloud_status.json'
    if status_path.exists():
        previous=json.loads(status_path.read_text())
        if previous.get('state')=='COMPLETED':raise RuntimeError('Completed run is immutable')
    os.environ['PRAXIS_PREREG_PATH']=str(a.prereg.resolve())
    os.environ['PRAXIS_PREREG_SHA256']=a.prereg_sha256
    os.environ['AWS_DEFAULT_REGION']='us-east-1'
    s3=boto3.client('s3',region_name='us-east-1',config=Config(connect_timeout=5,read_timeout=15,retries={'total_max_attempts':1}))
    bucket='praxis-garypagan-272615233626-us-east-1';prefix='final-praxis/20260912/runs/'+a.run_id+'/'
    uploaded={};sync_errors=[]
    def sync():
        count=0
        for path in root.rglob('*'):
            if not path.is_file() or path.is_symlink():continue
            relative=path.relative_to(root)
            if set(relative.parts).intersection({'.git','.venv','venv','__pycache__','models','hf_cache','cache','repositories','repo_cache','source_repos','site-packages'}):continue
            if path.suffix not in {'.json','.jsonl','.md','.txt','.log','.patch','.diff','.csv','.sha256','.safetensors'}:continue
            if path.suffix=='.safetensors' and 'checkpoints' not in relative.parts:continue
            stat=path.stat()
            if stat.st_size>1_000_000_000:continue
            fingerprint=(stat.st_size,stat.st_mtime_ns)
            if uploaded.get(str(relative))==fingerprint:continue
            try:
                s3.upload_file(str(path),bucket,prefix+relative.as_posix());uploaded[str(relative)]=fingerprint;count+=1
            except Exception as e:
                sync_errors.append({'utc':utc(),'file':relative.as_posix(),'type':type(e).__name__})
                break
        return count
    def record(state,**extra):
        value={'run_id':a.run_id,'state':state,'updated_utc':utc(),'started_utc':started,'preregistration_sha256':a.prereg_sha256,
            'command':command,'seconds_limit':a.seconds,'elapsed_seconds':round(time.monotonic()-begin,2),
            's3_prefix':'s3://'+bucket+'/'+prefix,'uploaded_files':len(uploaded),'sync_errors':sync_errors[-10:],**extra}
        tmp=status_path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');os.replace(tmp,status_path)
    started=utc();begin=time.monotonic();stop_requested=False;child=None
    def stop(signum,frame):
        nonlocal stop_requested
        stop_requested=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    record('STARTING');sync()
    with (root/'driver.log').open('ab',buffering=0) as log:
        child=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            if stop_requested or time.monotonic()-begin>=a.seconds:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=20)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                record('STOPPED' if stop_requested else 'TIMED_OUT',returncode=child.returncode);sync();return
            record('RUNNING',pid=child.pid);sync()
            for _ in range(15):
                if child.poll() is not None or stop_requested:break
                time.sleep(2)
        record('COMPLETED' if child.returncode==0 else 'FAILED',returncode=child.returncode);sync()
        # Publish a final status containing the outcome of the final upload.
        record('COMPLETED' if child.returncode==0 else 'FAILED',returncode=child.returncode);sync()
    raise SystemExit(child.returncode)

if __name__=='__main__':main()
