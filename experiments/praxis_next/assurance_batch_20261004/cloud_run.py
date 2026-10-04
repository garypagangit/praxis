"""Bounded PX-114/115 GPU allocation using the existing independently stopped worker."""
import hashlib,json,shlex,tarfile,time
from pathlib import Path
from experiments.praxis_next.compute.provics_cloud_control import control
from botocore.config import Config
HERE=Path(__file__).parent
PRIVATE=Path('C:/w/assurance_aws_20261004')

def main():
    c=control.Controller(PRIVATE/'settings.json');s=c.settings
    c._clients['s3']=c.session.client('s3',endpoint_url='https://s3.us-east-1.amazonaws.com',config=Config(connect_timeout=5,read_timeout=30,retries={'total_max_attempts':2},s3={'addressing_style':'path'}))
    freeze=json.loads((HERE/'CLOUD_FREEZE.json').read_text())
    assert hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest()==freeze['bundle_sha256']
    for p,h in freeze['runtime_files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    print(json.dumps(c.transfer('upload',PRIVATE/'bundle.tar.gz',s['prefix']+'bundle.tar.gz')),flush=True)
    try:
        print(json.dumps(c.start(HERE/'CLOUD_PROTOCOL.txt',HERE/'CLOUD_FREEZE.json')),flush=True)
        for _ in range(36):
            info=c.client('ssm').describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[s['instance']]}])['InstanceInformationList']
            if c.instance()['State']['Name']=='running' and any(i['PingStatus']=='Online' for i in info):break
            time.sleep(5)
        else:raise TimeoutError('Worker did not become ready')
        active=c.active()
        args=[f"s3://{s['bucket']}/{s['prefix']}bundle.tar.gz",freeze['bundle_sha256'],f"s3://{s['bucket']}/{s['prefix']}outputs",'praxis-assurance-'+active['run_id'][:16]]
        script='bash -s -- '+' '.join(shlex.quote(x) for x in args)+" <<'PRAXIS_ASSURANCE'\n"+(HERE/'cloud.sh').read_text()+"\nPRAXIS_ASSURANCE\n"
        (PRIVATE/'bootstrap.sh').write_text(script,encoding='utf-8',newline='\n')
        sent=c.send(PRIVATE/'bootstrap.sh',1380);command=sent['command_id'];print(json.dumps(sent),flush=True)
        for _ in range(280):
            try:
                receipt=c.poll(command);r=json.loads(Path(receipt['receipt']).read_text())
                if r['status'] in control.TERMINAL_STATES:
                    print(json.dumps({'worker_status':r['status'],'response_code':r.get('response_code'),'stderr':r.get('stderr')}),flush=True);break
            except c.client('ssm').exceptions.InvocationDoesNotExist:pass
            time.sleep(5)
        else:raise TimeoutError('Polling deadline')
    finally:
        if c.active_path.exists():
            print(json.dumps(c.stop()),flush=True)
            for _ in range(60):
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
