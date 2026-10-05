"""Bounded PX-114/115 GPU allocation using the existing independently stopped worker."""
import hashlib,json,shlex,tarfile,time
from pathlib import Path
from experiments.praxis_next.compute.provics_cloud_control import control
from botocore.config import Config
HERE=Path(__file__).parent
PRIVATE=Path('C:\w\px117c_aws_20261005')

def main():
    c=control.Controller(PRIVATE/'settings.json');s=c.settings
    c._clients['s3']=c.session.client('s3',endpoint_url='https://s3.us-east-1.amazonaws.com',config=Config(connect_timeout=5,read_timeout=30,retries={'total_max_attempts':2},s3={'addressing_style':'path'}))
    freeze=json.loads((HERE/'CLOUD_FREEZE.json').read_text())
    assert hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest()==freeze['bundle_sha256']
    for p,h in freeze['runtime_files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    print(json.dumps(c.transfer('upload',PRIVATE/'bundle.tar.gz',s['prefix']+'bundle.tar.gz')),flush=True)
    try:
        print(json.dumps(c.start(HERE/'PROTOCOL.txt',HERE/'CLOUD_FREEZE.json')),flush=True)
        import subprocess,sys,os
        for _ in range(36):
            if c.instance()['State']['Name']=='running':break
            time.sleep(5)
        else:raise TimeoutError('EC2 did not start')
        time.sleep(25)
        active=c.active()
        args=[f"s3://{s['bucket']}/{s['prefix']}bundle.tar.gz",freeze['bundle_sha256'],f"s3://{s['bucket']}/{s['prefix']}outputs",'praxis-gambit-'+active['run_id'][:16]]
        remote='/mnt/praxis-20260912-004/'+args[3]+'-worker.sh'
        script="set -euo pipefail\nmountpoint -q /mnt/praxis-20260912-004\ndf -h /mnt/praxis-20260912-004\nnvidia-smi\ncat > "+shlex.quote(remote)+" <<'ASSURANCE_WORKER'\n"+(HERE/'cloud.sh').read_text()+"\nASSURANCE_WORKER\n"
        script+='systemd-run --unit='+shlex.quote(args[3])+' --property=RuntimeMaxSec=1500 /bin/bash '+shlex.quote(remote)+' '+' '.join(shlex.quote(x) for x in args)+'\n'
        (PRIVATE/'bootstrap.sh').write_text(script,encoding='utf-8',newline='\n')
        env=dict(os.environ,PRAXIS_AWS_PRIVATE=str(PRIVATE),PRAXIS_SSH_SCRIPT=str(PRIVATE/'bootstrap.sh'))
        subprocess.run([sys.executable,str(HERE/'recover_ssh.py')],env=env,check=True)
        print('Detached worker launched through temporary SSH; awaiting development classifier and source-confounding audit',flush=True)
        for _ in range(145):
            try:
                c.client('s3').head_object(Bucket=s['bucket'],Key=s['prefix']+'outputs/result.sha256')
                print('Worker evidence published',flush=True);break
            except Exception as exc:
                if getattr(exc,'response',{}).get('Error',{}).get('Code') not in ['404','NoSuchKey','NotFound']:raise
            time.sleep(10)
        else:raise TimeoutError('No GPU result before deadline')
    finally:
        if c.active_path.exists():
            print(json.dumps(c.stop()),flush=True)
            for _ in range(120):
                final=c.finalize()
                if final['status']=='CLOSED_VERIFIED_STOPPED':
                    report=json.loads(Path(final['receipt']).read_text());(PRIVATE/'COMPUTE.json').write_text(json.dumps(report,indent=2));print(json.dumps(final),flush=True);break
                time.sleep(5)
            else:raise RuntimeError('Stop not yet verified; watchdog retained')
    for name in ['result.tar.gz','result.sha256']:c.transfer('download',PRIVATE/name,s['prefix']+'outputs/'+name)
    assert hashlib.sha256((PRIVATE/'result.tar.gz').read_bytes()).hexdigest()==(PRIVATE/'result.sha256').read_text().strip()
    dest=PRIVATE/'collected';dest.mkdir(exist_ok=False)
    with tarfile.open(PRIVATE/'result.tar.gz') as a:
        for m in a.getmembers():assert not m.issym() and not m.islnk() and (dest/m.name).resolve().is_relative_to(dest.resolve())
        a.extractall(dest)
    print(json.dumps({'collected':str(dest)}),flush=True)
if __name__=='__main__':main()
