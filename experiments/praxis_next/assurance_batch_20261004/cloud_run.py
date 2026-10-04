"""Bounded PX-114/115 GPU allocation using the existing independently stopped worker."""
import hashlib,json,shlex,tarfile,time
from pathlib import Path
from experiments.praxis_next.compute.provics_cloud_control import control
from botocore.config import Config
HERE=Path(__file__).parent
PRIVATE=Path('C:/w/assurance_aws_20261004_attempt5')

def main():
    c=control.Controller(PRIVATE/'settings.json');s=c.settings
    c._clients['s3']=c.session.client('s3',endpoint_url='https://s3.us-east-1.amazonaws.com',config=Config(connect_timeout=5,read_timeout=30,retries={'total_max_attempts':2},s3={'addressing_style':'path'}))
    freeze=json.loads((HERE/'CLOUD_FREEZE.json').read_text())
    assert hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest()==freeze['bundle_sha256']
    for p,h in freeze['runtime_files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    print(json.dumps(c.transfer('upload',PRIVATE/'bundle.tar.gz',s['prefix']+'bundle.tar.gz')),flush=True)
    try:
        print(json.dumps(c.start(HERE/'CLOUD_PROTOCOL.txt',HERE/'CLOUD_FREEZE.json')),flush=True)
        import subprocess,sys
        for _ in range(36):
            if c.instance()['State']['Name']=='running':break
            time.sleep(5)
        else:raise TimeoutError('EC2 did not start')
        time.sleep(25)
        for attempt in range(3):
            recovered=subprocess.run([sys.executable,str(HERE/'recover_ssh.py')])
            if recovered.returncode==0:break
            time.sleep(15)
        else:raise RuntimeError('Disk recovery failed; stop before inference')
        for _ in range(36):
            info=c.client('ssm').describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[s['instance']]}])['InstanceInformationList']
            if c.instance()['State']['Name']=='running' and any(i['PingStatus']=='Online' for i in info):break
            time.sleep(5)
        else:raise TimeoutError('Worker did not become ready')
        active=c.active()
        args=[f"s3://{s['bucket']}/{s['prefix']}bundle.tar.gz",freeze['bundle_sha256'],f"s3://{s['bucket']}/{s['prefix']}outputs",'praxis-assurance-'+active['run_id'][:16]]
        remote='/opt/dlami/nvme/'+args[3]+'-worker.sh'
        script="cat > "+shlex.quote(remote)+" <<'ASSURANCE_WORKER'\n"+(HERE/'cloud.sh').read_text()+"\nASSURANCE_WORKER\n"
        script+='systemd-run --unit='+shlex.quote(args[3])+' --property=RuntimeMaxSec=1500 /bin/bash '+shlex.quote(remote)+' '+' '.join(shlex.quote(x) for x in args)+'\n'
        (PRIVATE/'bootstrap.sh').write_text(script,encoding='utf-8',newline='\n')
        sent=c.send(PRIVATE/'bootstrap.sh',120);command=sent['command_id'];print(json.dumps(sent),flush=True)
        for _ in range(30):
            try:
                receipt=c.poll(command);r=json.loads(Path(receipt['receipt']).read_text())
                if r['status'] in control.TERMINAL_STATES:
                    assert r['status']=='Success',r
                    print('Detached GPU job launched',flush=True);break
            except c.client('ssm').exceptions.InvocationDoesNotExist:pass
            time.sleep(3)
        else:raise TimeoutError('Detached launch timeout')
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
