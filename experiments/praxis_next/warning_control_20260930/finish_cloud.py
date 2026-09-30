"""Resume the single started allocation, collect evidence, and verify shutdown."""
import hashlib,json,shlex,tarfile,time
from pathlib import Path
from experiments.praxis_next.warning_control_20260930.cloud_control import control

HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/warning_control_20260930')
def main():
    c=control.Controller(PRIVATE/'settings.json');s=c.settings
    from botocore.config import Config
    c._clients['s3']=c.session.client('s3',endpoint_url='https://s3.us-east-1.amazonaws.com',config=Config(connect_timeout=5,read_timeout=20,retries={'total_max_attempts':2},s3={'addressing_style':'path'}))
    f=json.loads((HERE/'FREEZE.json').read_text());active=c.active()
    assert hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest()==f['bundle_sha256']
    for name,digest in f['runtime_files'].items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest,name
    command=None;status=None
    try:
        for _ in range(60):
            uploaded=False
            try:uploaded=c.client('s3').head_object(Bucket=s['bucket'],Key=s['prefix']+'bundle.tar.gz')['ContentLength']==f['bundle_bytes']
            except c.client('s3').exceptions.ClientError as e:
                if e.response['Error']['Code'] not in ['404','NoSuchKey']:raise
            info=c.client('ssm').describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[s['instance']]}])['InstanceInformationList']
            if uploaded and c.instance()['State']['Name']=='running' and any(i['PingStatus']=='Online' for i in info):break
            time.sleep(5)
        else:raise RuntimeError('Upload or worker readiness timed out')
        args=[f"s3://{s['bucket']}/{s['prefix']}bundle.tar.gz",f['bundle_sha256'],f"s3://{s['bucket']}/{s['prefix']}outputs",'praxis-warning-'+active['run_id'][:16]]
        script="bash -s -- "+' '.join(shlex.quote(v) for v in args)+" <<'PRAXIS_WARNING_WORKER'\n"+(HERE/'cloud.sh').read_text()+"\nPRAXIS_WARNING_WORKER\n"
        (PRIVATE/'bootstrap.sh').write_text(script,encoding='utf-8',newline='\n')
        sent=c.send(PRIVATE/'bootstrap.sh',1200);command=sent['command_id'];print(json.dumps(sent),flush=True)
        deadline=time.monotonic()+1260
        while time.monotonic()<deadline:
            try:
                receipt=c.poll(command);status=json.loads(Path(receipt['receipt']).read_text())
                print(json.dumps({k:status.get(k) for k in ['status','response_code']}),flush=True)
                if status.get('status') in control.TERMINAL_STATES:break
            except c.client('ssm').exceptions.InvocationDoesNotExist:pass
            time.sleep(5)
        else:raise RuntimeError('Worker polling deadline exceeded')
    finally:
        print(json.dumps(c.stop()),flush=True)
        for _ in range(60):
            final=c.finalize()
            if final['status']=='CLOSED_VERIFIED_STOPPED':
                print(json.dumps(final),flush=True);break
            time.sleep(5)
    for name in ['result.tar.gz','result.sha256']:
        c.transfer('download',PRIVATE/name,s['prefix']+'outputs/'+name)
    expected=(PRIVATE/'result.sha256').read_text().strip()
    assert hashlib.sha256((PRIVATE/'result.tar.gz').read_bytes()).hexdigest()==expected
    dest=PRIVATE/'collected';dest.mkdir(exist_ok=False)
    with tarfile.open(PRIVATE/'result.tar.gz') as a:
        for m in a.getmembers():
            assert not m.issym() and not m.islnk() and (dest/m.name).resolve().is_relative_to(dest.resolve())
        a.extractall(dest)
    print(json.dumps({'collected':str(dest),'worker_status':status.get('status') if status else None,'sha256':expected}),flush=True)
if __name__=='__main__':main()
