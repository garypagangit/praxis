import json,hashlib,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIVATE=Path('C:/w/assurance_aws_20261004_attempt3')
PRIVATE.mkdir(exist_ok=True)
settings=json.loads(Path('C:/w/px107_aws_pilot/settings.json').read_text())
settings['prefix']='praxis-next/assurance/20261004-attempt3/'
(PRIVATE/'settings.json').write_text(json.dumps(settings,indent=2))
with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
    a.add(HERE/'run_language.py',arcname='run_language.py')
    for name in ['receipts.json','narrative_inputs.json']:
        a.add(Path('C:/w/assurance_batch_20261004')/name,arcname='inputs/'+name)
source=(HERE.parent/'xai_acquisition_20261004/cloud_run.py').read_text()
source=source.replace('Bounded PX-107A allocation','Bounded PX-114/115 GPU allocation')
source=source.replace("C:/w/px107_aws_pilot","C:/w/assurance_aws_20261004_attempt3")
source=source.replace("HERE/'FREEZE.json'","HERE/'CLOUD_FREEZE.json'")
source=source.replace("HERE/'PROTOCOL.txt'","HERE/'CLOUD_PROTOCOL.txt'")
source=source.replace('praxis-px107-','praxis-assurance-').replace('PRAXIS_PX107','PRAXIS_ASSURANCE')
start=source.index("        script='bash -s -- '")
end=source.index('    finally:',start)
source=source[:start]+'''        remote='/opt/dlami/nvme/'+args[3]+'-worker.sh'
        script="cat > "+shlex.quote(remote)+" <<'ASSURANCE_WORKER'\\n"+(HERE/'cloud.sh').read_text()+"\\nASSURANCE_WORKER\\n"
        script+='systemd-run --unit='+shlex.quote(args[3])+' --property=RuntimeMaxSec=1500 /bin/bash '+shlex.quote(remote)+' '+' '.join(shlex.quote(x) for x in args)+'\\n'
        (PRIVATE/'bootstrap.sh').write_text(script,encoding='utf-8',newline='\\n')
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
''' + source[end:]
source=source.replace('for _ in range(60):','for _ in range(120):')
(HERE/'cloud_run.py').write_text(source,encoding='utf-8')
files=['run_language.py','cloud.sh','cloud_run.py','CLOUD_PROTOCOL.txt']
freeze={'bundle_sha256':hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest(),
        'runtime_files':{str((HERE/f).relative_to(ROOT)).replace('\\','/'):hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in files},
        'model_digest':'357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b',
        'ollama_version':'0.17.0','reason':'User authorized preference for faster AWS; full separate GPU run.'}
(HERE/'CLOUD_FREEZE.json').write_text(json.dumps(freeze,indent=2))
print(PRIVATE)
